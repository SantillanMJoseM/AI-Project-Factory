"""Context integration — bridge from task orchestration to the execution
continuity plane (Stage 2B → Stage 2A components).

Uses, without modifying, ``orchestration/execution/``:

* **Ledger** (§4.4): every task/delegation state change is journalled as
  ``STATE_CHANGED``; plan publications as ``FILE_CHANGED``; checkpoints come
  free from the snapshot API (``CHECKPOINT_WRITTEN``). Only the existing
  event vocabulary is used — this package must never extend the ledger.
* **Dynamic Context Manager** (§4.1): :func:`assemble_task_context` freezes
  the governed inputs (task contract + persisted plan) as a T1-tier manifest
  so a snapshot can pin ``context_manifest_hash``.
* **Snapshot Manager** (§4.2): :func:`checkpoint_plan` commits the current
  plan/delegations files and captures one resumable checkpoint.
* **Resume Engine** (§4.3): :func:`resume_view` reports the fail-closed
  verdict for the latest checkpoint and the recomputed ready-wave.

All functions take an explicit ``repo_root`` so tests run against a scratch
repository. The plan must already be saved to the file plane (the ledger
and snapshots reference repository-relative paths only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from orchestration.execution.context import assemble_context
from orchestration.execution.ledger import Ledger, ledger_path
from orchestration.execution.models import Effect, EventType
from orchestration.execution.resume import evaluate_resume
from orchestration.execution.snapshot import (
    SnapshotError,
    create_snapshot,
    latest_snapshot,
    list_snapshots,
    verify_snapshot,
)

from .coordination import AgentCoordinationManager
from .delegation import DelegationManager
from .engine import delegations_file_path, load_plan, plan_file_path, save_plan
from .models import (
    DelegationRecord,
    OrchestrationPlan,
    Task,
    TaskError,
    TaskState,
    utc_now_stamp,
)


class ContextIntegrationError(TaskError):
    """Refusal while integrating with the execution plane (fail-closed)."""


# ---------------------------------------------------------------------------
# Relative-path helpers
# ---------------------------------------------------------------------------


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(repo_root).resolve())).replace("\\", "/")
    except ValueError:
        raise ContextIntegrationError(f"path outside repository root: {path}") from None


def plan_rel_path(repo_root: Path, project_id: str) -> str:
    return _rel(repo_root, plan_file_path(repo_root, project_id))


def delegations_rel_path(repo_root: Path, project_id: str) -> str:
    return _rel(repo_root, delegations_file_path(repo_root, project_id))


#: Governed input every task context must reference (T1 tier).
GOVERNED_TASK_REF = "contracts/task-contract.md"


# ---------------------------------------------------------------------------
# Ledger journalling
# ---------------------------------------------------------------------------


def journal_task_change(
    ledger: Ledger,
    task: Task,
    previous_state: TaskState,
    current_state: TaskState,
    actor: str,
    reason: str = "",
    *,
    timestamp: Optional[str] = None,
) -> Any:
    """Journal one task transition as ``STATE_CHANGED`` (existing vocabulary)."""
    return ledger.append(
        EventType.STATE_CHANGED,
        actor,
        {
            "subject": "task",
            "task_id": task.task_id,
            "from": TaskState(previous_state).value,
            "to": TaskState(current_state).value,
            "reason": reason,
            "agent": task.assigned_agent,
        },
        effect=Effect.IDEMPOTENT,
        timestamp=timestamp,
    )


def journal_delegation_change(
    ledger: Ledger,
    record: DelegationRecord,
    previous_status: str,
    actor: str,
    reason: str = "",
    *,
    timestamp: Optional[str] = None,
) -> Any:
    """Journal one delegation status change as ``STATE_CHANGED``."""
    return ledger.append(
        EventType.STATE_CHANGED,
        actor,
        {
            "subject": "delegation",
            "delegation_id": record.delegation_id,
            "task_id": record.task_id,
            "parent_task_id": record.parent_task_id,
            "from": str(previous_status),
            "to": record.status.value if hasattr(record.status, "value") else str(record.status),
            "reason": reason,
        },
        effect=Effect.IDEMPOTENT,
        timestamp=timestamp,
    )


def journal_plan_published(ledger: Ledger, plan: OrchestrationPlan, actor: str, *, timestamp: Optional[str] = None) -> Any:
    """Journal the repository-visible publication of the plan/delegation files."""
    return ledger.append(
        EventType.FILE_CHANGED,
        actor,
        {
            "subject": "task_plan",
            "plan_id": plan.plan_id,
            "plan_ref": plan_rel_path(plan_repo_root_from(ledger), plan.project_id),
        },
        effect=Effect.IDEMPOTENT,
        timestamp=timestamp,
    )


def plan_repo_root_from(ledger: Ledger) -> Path:
    """``projects/<ID>/execution/ledger/<file>`` → repository root."""
    return Path(ledger.path).resolve().parents[3]


# ---------------------------------------------------------------------------
# Publication / checkpointing
# ---------------------------------------------------------------------------


def publish_workspace(
    repo_root: Path,
    plan: OrchestrationPlan,
    delegation_manager: Optional[DelegationManager] = None,
) -> List[str]:
    """Persist plan (+ delegations) to the file plane; returns rel paths."""
    repo_root = Path(repo_root)
    save_plan(plan, repo_root)
    paths = [plan_rel_path(repo_root, plan.project_id)]
    if delegation_manager is not None:
        delegation_manager.save(repo_root)
        paths.append(delegations_rel_path(repo_root, plan.project_id))
    return paths


def assemble_task_context(
    repo_root: Path,
    plan: OrchestrationPlan,
    *,
    execution_id: str,
    actor_agent: str = "AG-001",
    task_refs: Sequence[str] = (),
    token_budget: Optional[int] = None,
    persist: bool = True,
) -> Any:
    """Assemble a DCM manifest whose T1 tier is the governed task contract
    plus the persisted plan file. Raises if neither is present (fail-closed).
    """
    repo_root = Path(repo_root)
    plan_path = plan_file_path(repo_root, plan.project_id)
    if not plan_path.is_file():
        raise ContextIntegrationError("plan must be published before its context can be assembled")
    refs = [GOVERNED_TASK_REF, *task_refs, str(plan_path.relative_to(repo_root))]
    skills: List[Tuple[str, str]] = []
    registry_path = repo_root / "orchestration" / "skills" / "registry.json"
    if registry_path.is_file():
        try:
            from orchestration.skills.registry import Registry

            registry = Registry.load(registry_path)
            bound = sorted({s for rows in plan.skills_by_task.values() for s in rows})
            for skill_id in bound:
                entry = registry.get(skill_id)
                if entry is not None and entry.library_path:
                    skills.append((skill_id, entry.library_path))
        except Exception:
            skills = []  # advisory tier only; assembly must not fail on registry drift
    return assemble_context(
        repo_root,
        project_id=plan.project_id,
        execution_id=execution_id,
        task_refs=refs,
        skills=skills,
        working_refs=[str(p) for p in refs],
        token_budget=token_budget,
        persist=persist,
    )


def checkpoint_plan(
    repo_root: Path,
    plan: OrchestrationPlan,
    delegation_manager: Optional[DelegationManager],
    *,
    execution_id: str,
    task_id: str,
    actor_agent: str = "AG-001",
    reason: str = "state-transition",
    ledger: Optional[Ledger] = None,
    context_manifest: Optional[Any] = None,
    git_branch: str = "",
    before_commit: str = "",
    after_commit: str = "",
    stamp: Optional[str] = None,
) -> Any:
    """Publish the workspace, then capture one resumable execution snapshot.

    ``files`` certified: the plan and (if present) delegations JSON.
    ``context_manifest_hash`` pins the DCM manifest when provided. When a
    ledger is supplied the snapshot journals ``CHECKPOINT_WRITTEN`` against
    it (Stage 2A contract).
    """
    repo_root = Path(repo_root)
    plan.graph.require(task_id)  # fail-closed: checkpoint must name a real task
    rel_paths = publish_workspace(repo_root, plan, delegation_manager)
    manifest_hash = context_manifest.manifest_hash if context_manifest is not None else None
    if ledger is not None and ledger.execution_id != execution_id:
        raise ContextIntegrationError("ledger belongs to a different execution")
    return create_snapshot(
        repo_root,
        project_id=plan.project_id,
        execution_id=execution_id,
        task_id=task_id,
        agent_id=actor_agent,
        reason=reason,
        files=rel_paths,
        context_manifest_hash=manifest_hash,
        ledger=ledger,
        git_branch=git_branch,
        before_commit=before_commit,
        after_commit=after_commit,
        stamp=stamp,
    )


# ---------------------------------------------------------------------------
# Restore / resume views
# ---------------------------------------------------------------------------


def restore_workspace(repo_root: Path, project_id: str) -> Tuple[OrchestrationPlan, List[DelegationRecord]]:
    """Reload the persisted plan and delegation records for a project."""
    plan = load_plan(repo_root, project_id)
    manager = DelegationManager.load(plan, repo_root)
    return plan, [manager.records[k] for k in sorted(manager.records)]


def checkpoint_integrity(repo_root: Path, project_id: str, execution_id: str) -> Dict[str, Any]:
    """Verify the latest checkpoint of an execution; never raises for issues."""
    repo_root = Path(repo_root)
    snapshot = latest_snapshot(repo_root, project_id, execution_id)
    if snapshot is None:
        return {"ok": False, "issues": ["no checkpoint exists for this execution"], "snapshot_id": ""}
    report = verify_snapshot(repo_root, plan_snapshot_path(repo_root, snapshot.snapshot_id, project_id))
    return {
        "ok": report.ok and report.tree_matches,
        "snapshot_id": snapshot.snapshot_id,
        "issues": list(report.integrity_issues) + list(report.ledger_issues),
        "divergence_missing": list(report.missing_files),
        "divergence_modified": list(report.modified_files),
    }


def plan_snapshot_path(repo_root: Path, snapshot_id: str, project_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "execution" / "snapshots" / (snapshot_id + ".json")


def resume_view(
    repo_root: Path,
    project_id: str,
    execution_id: str,
    *,
    check_git: bool = True,
) -> Dict[str, Any]:
    """Consolidated resume picture for one execution of a project.

    Layers, fail-closed:
      1. the execution checkpoint inventory (``list_snapshots``);
      2. the Resume Engine eligibility verdict for the latest checkpoint
         (:func:`evaluate_resume`, §4.3 — READY / BLOCKED with reasons);
      3. the recomputed coordination state (ready wave, blockers) from the
         persisted workspace.
    Never performs the resume transaction; that stays with the Resume
    Engine's ``start_resume``.
    """
    repo_root = Path(repo_root)
    rows = list_snapshots(repo_root, project_id, execution_id)
    result: Dict[str, Any] = {
        "project_id": project_id,
        "execution_id": execution_id,
        "checkpoints": [r.snapshot_id for r in rows],
        "resume_decision": None,
        "coordination": None,
    }
    if rows:
        decision = evaluate_resume(repo_root, rows[-1].path, check_git=check_git)
        result["resume_decision"] = decision.to_dict()
    try:
        plan, records = restore_workspace(repo_root, project_id)
    except TaskError as exc:
        result["workspace_error"] = str(exc)
        return result
    coordination = AgentCoordinationManager(plan, records).consolidated_state(include_model_status=False)
    result["coordination"] = coordination.to_dict()
    return result


__all__ = [
    "ContextIntegrationError",
    "GOVERNED_TASK_REF",
    "assemble_task_context",
    "checkpoint_integrity",
    "checkpoint_plan",
    "delegations_rel_path",
    "journal_delegation_change",
    "journal_plan_published",
    "journal_task_change",
    "plan_rel_path",
    "plan_repo_root_from",
    "plan_snapshot_path",
    "restore_workspace",
    "resume_view",
]
