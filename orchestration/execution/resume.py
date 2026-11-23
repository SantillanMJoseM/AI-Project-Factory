"""Resume Engine — fail-closed recovery, duplicate-execution prevention (Stage 2A).

Implements §4.3, §8 and §9.4 of ``docs/execution/EXECUTION_ARCHITECTURE.md``.

Detection is out of scope here (leases / model_fallback signal elsewhere);
this module owns the decision and the transaction:

* :func:`evaluate_resume` checks all six eligibility clauses (§4.3) and
  returns a ``ResumeDecision``. Anything unverifiable ⇒ ``BLOCKED``
  (fail-closed; never best-effort).
* :func:`start_resume` performs the forward-only recovery transaction:
  journal the dead execution (``STATE_CHANGED`` + ``RESUME_REQUESTED`` in
  its ledger), open a **new** execution ledger with
  ``EXECUTION_OPENED(resumed_from=…)`` + ``RESUME_STARTED``, and register
  the resume in ``projects/<ID>/execution/resume/resume-index.json``.
  Duplicate resumes for the same source execution — or for an already-taken
  target id — are refused (§9.4 single-writer invariant, formalized without
  touching the runtime DB).
* Resume budget: a third consecutive auto-resume attempt under the same
  failure signature is refused as ``NEEDS_INTERVENTION`` (§4.3).
* Applied ``applied-irreversible`` operations are collected from the ledger
  and surfaced as ``never_reapply`` — the journal that makes the
  never-re-apply rule mechanically checkable (§4.3 clause 4).

Destructive repairs (discard divergence, rebuild over modified files) are
LEVEL C per ``risk-matrix.md``: this module prepares a divergence report but
never performs them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import rebuild_for_resume
from .ledger import Ledger, LedgerError, ledger_path, read_records
from .models import (
    Effect,
    EventType,
    ExecutionError,
    ResumeVerdict,
    TaskSnapshot,
    is_governed,
    utc_now_stamp,
)
from .snapshot import SnapshotError, load_snapshot, verify_snapshot


class ResumeError(ExecutionError):
    """Base error for resume refusals."""


class ResumeBlocked(ResumeError):
    """Raised by ``start_resume`` when the decision is not READY."""

    def __init__(self, decision: "ResumeDecision"):
        super().__init__("resume blocked: " + "; ".join(decision.reasons))
        self.decision = decision


class ResumeNeedsIntervention(ResumeError):
    """Resume budget exhausted for an identical failure signature (§4.3)."""


class DuplicateResumeError(ResumeError):
    """An execution may be resumed at most once; targets must be unique."""


# ---------------------------------------------------------------------------
# Resume index (file-plane registry; the DB path stays runtime-owned)
# ---------------------------------------------------------------------------


def resume_index_path(repo_root: Path, project_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "execution" / "resume" / "resume-index.json"


def load_resume_index(repo_root: Path, project_id: str) -> Dict[str, Any]:
    path = resume_index_path(repo_root, project_id)
    if not path.exists():
        return {"project_id": project_id, "resumes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ResumeError(f"{path}: corrupt resume index: {exc}") from exc


def _save_resume_index(repo_root: Path, index: Dict[str, Any]) -> None:
    path = resume_index_path(repo_root, index["project_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def resume_history(repo_root: Path, project_id: str, execution_id: str) -> List[Dict[str, Any]]:
    """All resume entries whose chain includes ``execution_id`` (as source or target)."""
    index = load_resume_index(repo_root, project_id)
    by_target = {r["to_execution"]: r for r in index.get("resumes", [])}
    by_source = {r["from_execution"]: r for r in index.get("resumes", [])}
    chain_ids = {execution_id}
    # walk forward
    cursor = execution_id
    while cursor in by_source:
        cursor = by_source[cursor]["to_execution"]
        chain_ids.add(cursor)
    # walk backward
    cursor = execution_id
    while cursor in by_target:
        cursor = by_target[cursor]["from_execution"]
        chain_ids.add(cursor)
    return [r for r in index.get("resumes", []) if r["from_execution"] in chain_ids or r["to_execution"] in chain_ids]


def consecutive_resumes_with_signature(
    repo_root: Path, project_id: str, execution_id: str, failure_signature: str
) -> int:
    """Count prior auto-resumes on the execution chain with the same signature."""
    chain = resume_history(repo_root, project_id, execution_id)
    return sum(1 for r in chain if r.get("failure_signature") == failure_signature and failure_signature)


# ---------------------------------------------------------------------------
# Decision model (§4.3)
# ---------------------------------------------------------------------------


@dataclass
class ResumeDecision:
    """Verdict of the fail-closed eligibility evaluation (§4.3)."""

    snapshot_id: str = ""
    execution_id: str = ""
    verdict: ResumeVerdict = ResumeVerdict.BLOCKED
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    never_reapply: List[int] = field(default_factory=list)
    divergence_missing: List[str] = field(default_factory=list)
    divergence_modified: List[str] = field(default_factory=list)
    staleness: Optional[Dict[str, Any]] = None

    @property
    def eligible(self) -> bool:
        return self.verdict is ResumeVerdict.READY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "execution_id": self.execution_id,
            "verdict": self.verdict.value,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "never_reapply": list(self.never_reapply),
            "divergence_missing": list(self.divergence_missing),
            "divergence_modified": list(self.divergence_modified),
            "staleness": self.staleness,
        }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def git_available() -> bool:
    return shutil.which("git") is not None


def commit_exists(repo_root: Path, commit: str) -> bool:
    """True if the commit object exists in the repository (anchor check)."""
    if not commit or not git_available():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", commit + "^{commit}"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def evaluate_resume(
    repo_root: Path,
    snapshot_path: Path,
    *,
    check_git: bool = True,
    context_project_id: Optional[str] = None,
) -> ResumeDecision:
    """Run the six fail-closed eligibility clauses (§4.3) over a snapshot.

    Returns a ``ResumeDecision``; never raises for blocked causes (only for
    unreadable files). ``check_git=False`` skips clause 2's git-anchor probe
    for environments without a repository (callers must then anchor
    elsewhere before production resume).
    """
    repo_root = Path(repo_root)
    snapshot_path = Path(snapshot_path)
    try:
        snapshot = load_snapshot(snapshot_path)
    except SnapshotError as exc:
        return ResumeDecision(
            execution_id="?",
            verdict=ResumeVerdict.BLOCKED,
            reasons=[f"snapshot unreadable: {exc}"],
        )

    decision = ResumeDecision(
        snapshot_id=snapshot.snapshot_id, execution_id=snapshot.execution_id
    )

    # Clause 1 — committed snapshot marked eligible; approval is human territory.
    if not snapshot.resume_eligibility.eligible:
        decision.reasons.append("snapshot not resume-eligible (resume_eligibility.eligible=false)")
    if snapshot.resume_eligibility.requires_approval:
        decision.reasons.append("resume requires LEVEL C human approval (prepare, do not execute)")

    # Clauses 2a/2b — snapshot self-hash, file-set root, and ledger chain.
    report = verify_snapshot(repo_root, snapshot_path, check_files=False, check_ledger=True)
    for issue in report.integrity_issues:
        decision.reasons.append(f"snapshot integrity: {issue}")
    for issue in report.ledger_issues:
        decision.reasons.append(f"ledger chain: {issue}")

    # Clause 2c — git anchors exist in the repository (trust anchors, §7).
    if check_git:
        for label, commit in (("before_commit", snapshot.git.before_commit), ("after_commit", snapshot.git.after_commit)):
            if not commit:
                continue
            if not commit_exists(repo_root, commit):
                decision.reasons.append(f"git anchor unverifiable: {label}={commit!r}")

    # Clause 3 — working tree vs snapshot file set. Divergence must be
    # additive (new files are not in file_set and pass implicitly); missing
    # or modified file_set members break the clause. Governed-file
    # divergence is called out separately (§4.3) but any unexplained
    # divergence blocks under the fail-closed posture.
    tree = verify_snapshot(repo_root, snapshot_path, check_files=True, check_ledger=False)
    decision.divergence_missing = list(tree.missing_files)
    decision.divergence_modified = list(tree.modified_files)
    governed_divergence = sorted(
        {p for p in decision.divergence_missing + decision.divergence_modified if is_governed(p)}
    )
    other_divergence = sorted(
        {p for p in decision.divergence_missing + decision.divergence_modified if not is_governed(p)}
    )
    if governed_divergence:
        decision.reasons.append(
            "governed-file divergence: " + ", ".join(governed_divergence)
        )
    if other_divergence:
        decision.reasons.append(
            "working-tree divergence from file_set (not additive): "
            + ", ".join(other_divergence)
        )

    # Clause 4 — journalled effects: collect applied-irreversible operations.
    if snapshot.ledger is not None:
        ledger_file = _ledger_file_for(repo_root, snapshot)
        if ledger_file is not None:
            try:
                for entry in read_records(ledger_file):
                    if (
                        entry.seq <= snapshot.ledger.seq_to
                        and entry.payload.get("effect") == Effect.APPLIED_IRREVERSIBLE.value
                    ):
                        decision.never_reapply.append(entry.seq)
            except LedgerError as exc:
                decision.reasons.append(f"ledger unreadable for effect scan: {exc}")

    # Clause 1b/5/6 support — no resume of a terminal execution, and no
    # second RUNNING: the source must not already have a successor, and the
    # source ledger must not hold a successor RESUME_STARTED.
    if _execution_terminal(repo_root, snapshot):
        decision.warnings.append("source execution is journalled terminal; resume opens a successor record")
    existing = [r for r in resume_history(repo_root, snapshot.project_id, snapshot.execution_id) if r["from_execution"] == snapshot.execution_id]
    if existing:
        decision.reasons.append(
            f"duplicate resume: execution already resumed as {existing[0]['to_execution']}"
        )

    # Staleness of the pinned context manifest (§4.1; needed for clause-2
    # "rebuild context" feasibility and governed-content freshness).
    project_id = context_project_id or snapshot.project_id
    if snapshot.context_manifest_hash:
        try:
            _manifest, staleness = rebuild_for_resume(repo_root, project_id, snapshot)
            decision.staleness = staleness.to_dict()
            if not staleness.ok:
                decision.reasons.append(
                    "context manifest stale on governed files: "
                    + ", ".join(staleness.governed_stale_refs)
                )
            elif staleness.staleness.value == "STALE":
                decision.warnings.append("context manifest STALE; re-assemble before continuing")
        except ExecutionError as exc:
            decision.reasons.append(f"context rebuild infeasible: {exc}")
    else:
        decision.reasons.append("snapshot carries no context_manifest_hash (§4.1: not resume-eligible)")

    if decision.reasons:
        decision.verdict = ResumeVerdict.BLOCKED
    else:
        decision.verdict = ResumeVerdict.READY
    return decision


def _ledger_file_for(repo_root: Path, snapshot: TaskSnapshot) -> Optional[Path]:
    candidates: List[Path] = []
    if snapshot.ledger is not None:
        candidates.append(repo_root / snapshot.ledger.path)
    candidates.append(ledger_path(repo_root, snapshot.project_id, snapshot.execution_id))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _execution_terminal(repo_root: Path, snapshot: TaskSnapshot) -> bool:
    ledger_file = _ledger_file_for(repo_root, snapshot)
    if ledger_file is None:
        return False
    try:
        return any(e.event_type == EventType.EXECUTION_TERMINAL.value for e in read_records(ledger_file))
    except LedgerError:
        return False


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def start_resume(
    repo_root: Path,
    snapshot_path: Path,
    *,
    new_execution_id: str,
    actor_agent: str,
    failure_signature: str = "",
    model_binding: Optional[Dict[str, Any]] = None,
    check_git: bool = True,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the forward-only resume transaction (§4.3 procedure).

    Preconditions enforced here: ``evaluate_resume`` READY; resume budget
    (≤ ``MAX_AUTO_RESUMES_PER_SIGNATURE`` prior attempts per failure
    signature); target execution id unused (new ledger must not exist);
    source not already resumed. The dead execution's record is never
    mutated — a new execution opens with ``resumed_from``.
    """
    from .models import MAX_AUTO_RESUMES_PER_SIGNATURE

    repo_root = Path(repo_root)
    stamp = stamp or utc_now_stamp()
    decision = evaluate_resume(repo_root, snapshot_path, check_git=check_git)
    if not decision.eligible:
        raise ResumeBlocked(decision)
    snapshot = load_snapshot(snapshot_path)

    if consecutive_resumes_with_signature(
        repo_root, snapshot.project_id, snapshot.execution_id, failure_signature
    ) >= MAX_AUTO_RESUMES_PER_SIGNATURE:
        raise ResumeNeedsIntervention(
            f"resume budget exhausted for failure signature {failure_signature!r} "
            f"(>= {MAX_AUTO_RESUMES_PER_SIGNATURE} prior attempts); escalate as NEEDS_INTERVENTION"
        )

    index = load_resume_index(repo_root, snapshot.project_id)
    known_sources = {r["from_execution"] for r in index.get("resumes", [])}
    known_targets = {r["to_execution"] for r in index.get("resumes", [])}
    if snapshot.execution_id in known_sources:
        raise DuplicateResumeError(
            f"execution {snapshot.execution_id} already resumed; each execution is resumed at most once"
        )
    if new_execution_id in known_targets or new_execution_id == snapshot.execution_id:
        raise DuplicateResumeError(f"execution id {new_execution_id} already in use")

    new_ledger_file = ledger_path(repo_root, snapshot.project_id, new_execution_id)
    if new_ledger_file.exists():
        raise DuplicateResumeError(f"ledger for {new_execution_id} already exists: {new_ledger_file}")

    # 1. Journal the source: STATE_CHANGED (RUNNING -> FAILED as recorded stop
    #    so the single-writer invariant is never raced, §9.4) then
    #    RESUME_REQUESTED. Append-only via Ledger.open (chain-verified).
    source_ledger_file = _ledger_file_for(repo_root, snapshot)
    if source_ledger_file is None:
        raise ResumeError("source execution ledger file not found for journaling")
    source = Ledger.open(source_ledger_file, snapshot.execution_id)
    if not source.is_terminal():
        source.append(
            EventType.STATE_CHANGED,
            actor_agent,
            {"from": "RUNNING", "to": "FAILED", "reason": "lease-expired/unattended-stop"},
            effect=Effect.IDEMPOTENT,
            timestamp=stamp,
        )
    requested = source.append(
        EventType.RESUME_REQUESTED,
        actor_agent,
        {"snapshot_ref": snapshot.snapshot_id, "failure_signature": failure_signature},
        effect=Effect.NONE,
        timestamp=stamp,
    )

    # 2. Open the successor execution (new record; the dead one is untouched).
    try:
        snapshot_ref = str(Path(snapshot_path).resolve().relative_to(repo_root.resolve()))
    except ValueError:
        snapshot_ref = Path(snapshot_path).name
    successor = Ledger.create(
        new_ledger_file,
        new_execution_id,
        actor_agent=actor_agent,
        payload={
            "resumed_from": snapshot.execution_id,
            "snapshot_ref": snapshot_ref,
            "task_id": snapshot.task_id,
        },
        timestamp=stamp,
    )
    opened = successor.entries[0]
    successor.append(
        EventType.RESUME_STARTED,
        actor_agent,
        {"from_execution": snapshot.execution_id, "snapshot_id": snapshot.snapshot_id},
        effect=Effect.IDEMPOTENT,
        timestamp=stamp,
    )
    if model_binding:
        successor.append(
            EventType.MODEL_BOUND,
            actor_agent,
            {"model_binding": dict(model_binding)},
            effect=Effect.NONE,
            timestamp=stamp,
        )

    # 3. Register in the file-plane resume index (duplicate prevention anchor).
    index.setdefault("resumes", []).append(
        {
            "resume_id": f"RES-{snapshot.project_id}-{new_execution_id}",
            "from_execution": snapshot.execution_id,
            "to_execution": new_execution_id,
            "snapshot_ref": snapshot.snapshot_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "failure_signature": failure_signature,
            "actor_agent": actor_agent,
            "at": stamp,
            "requested_seq": requested.seq,
            "opened_seq": opened.seq,
        }
    )
    _save_resume_index(repo_root, index)

    return {
        "ok": True,
        "from_execution": snapshot.execution_id,
        "to_execution": new_execution_id,
        "ledger": str(new_ledger_file.relative_to(repo_root)),
        "source_ledger": str(source_ledger_file.relative_to(repo_root)),
        "decision": decision.to_dict(),
    }


__all__ = [
    "DuplicateResumeError",
    "ResumeBlocked",
    "ResumeDecision",
    "ResumeError",
    "ResumeNeedsIntervention",
    "commit_exists",
    "consecutive_resumes_with_signature",
    "evaluate_resume",
    "git_available",
    "load_resume_index",
    "resume_history",
    "resume_index_path",
    "start_resume",
]
