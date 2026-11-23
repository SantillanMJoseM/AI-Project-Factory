"""Delegation manager — create delegated tasks, track status, verify
completion (Stage 2B).

A *delegation* is one coordinator-owned parent task spawning a child task
assigned to a delegatee agent, recorded in an append-only
:class:`DelegationRecord`. All child status movement goes through the single
guarded transition entry point (:func:`orchestration.task_orchestration.models.transition_task`),
so the Task Contract state machine and rules 1-4 are enforced here:

* **create** — child inherits the parent as a dependency (a delegation
  never escapes its parent's slice of the graph), starts ASSIGNED;
* **track**  — status transitions mirrored onto the record with history;
* **verify** — completion is fail-closed: the delegated work is only
  VERIFIED when every acceptance criterion is satisfied (rule 1), every
  required quality gate is PASS/NOT_APPLICABLE (rule 2, stricter than the
  contract minimum), and the verifier is *independent* of both the
  delegatee and the delegator (rule 3 + "the independent auditor cannot be
  the developer"). Otherwise the child moves to REJECTED for rework.

Boundary: this module manages delegation bookkeeping inside a plan; it
starts no agents, changes no contracts/schemas/config.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .engine import delegations_file_path, task_orchestration_dir
from .models import (
    AGENT_ID_RE,
    DelegationRecord,
    DelegationStatus,
    GateVerdict,
    OrchestrationPlan,
    Priority,
    Task,
    TaskError,
    TaskState,
    VerificationReport,
    transition_task,
    utc_now_stamp,
)

#: Child-task states a delegation may be moved to through this manager.
TRACKABLE_STATES = {
    TaskState.RUNNING,
    TaskState.BLOCKED,
    TaskState.REVIEW_REQUIRED,
    TaskState.COMPLETED,
    TaskState.FAILED,
    TaskState.CANCELLED,
}


class DelegationError(TaskError):
    """Refusal in the delegation lifecycle (fail-closed)."""


class DelegationManager:
    """Owns the delegation records of one :class:`OrchestrationPlan`."""

    def __init__(self, plan: OrchestrationPlan, delegator_agent: str = "AG-001") -> None:
        if not AGENT_ID_RE.match(delegator_agent or ""):
            raise DelegationError(f"delegator must be a catalog agent id, got {delegator_agent!r}")
        self.plan = plan
        self.delegator_agent = delegator_agent
        self.records: Dict[str, DelegationRecord] = {}

    # -- lookup --------------------------------------------------------------

    def require(self, delegation_id: str) -> DelegationRecord:
        record = self.records.get(delegation_id)
        if record is None:
            raise DelegationError(f"unknown delegation_id: {delegation_id}")
        return record

    def record_for_task(self, task_id: str) -> Optional[DelegationRecord]:
        for record in self.records.values():
            if record.task_id == task_id:
                return record
        return None

    def active_delegations(self) -> List[DelegationRecord]:
        open_states = {DelegationStatus.DELEGATED, DelegationStatus.ACTIVE, DelegationStatus.SUBMITTED}
        return [r for r in sorted(self.records.values(), key=lambda r: r.delegation_id) if r.status in open_states]

    # -- create ----------------------------------------------------------------

    def create_delegation(
        self,
        parent_task_id: str,
        title: str,
        description: str,
        delegatee_agent: str,
        *,
        priority: Any = Priority.MEDIUM,
        inputs: Sequence[str] = (),
        outputs: Sequence[str] = (),
        acceptance_criteria: Iterable[Any] = (),
        quality_gates: Iterable[Any] = (),
        stamp: Optional[str] = None,
    ) -> DelegationRecord:
        """Create the delegated child task (ASSIGNED) plus its record.

        Child task ids continue the plan's TASK-NNNN sequence; the child
        depends on its parent so no wave can schedule it before the parent
        completes. Acceptance criteria/gates default to two generic ones so
        verification is always meaningful (rule 1 needs something to check).
        """
        graph = self.plan.graph
        parent = graph.require(parent_task_id)  # raises TaskError if unknown
        if not AGENT_ID_RE.match(delegatee_agent or ""):
            raise DelegationError(f"delegatee must be a catalog agent id, got {delegatee_agent!r}")
        if delegatee_agent not in {f"AG-{i:03d}" for i in range(1, 19)}:
            raise DelegationError(f"delegatee {delegatee_agent!r} not in agent catalog")
        if not title.strip():
            raise DelegationError("delegated task requires a title")
        if parent.is_terminal:
            raise DelegationError(f"cannot delegate from terminal parent {parent_task_id}")

        from .models import AcceptanceCriterion

        stamp = stamp or utc_now_stamp()
        criteria: List[Any] = []
        for i, item in enumerate(acceptance_criteria):
            if isinstance(item, AcceptanceCriterion):
                criteria.append(item)
            else:
                criteria.append(AcceptanceCriterion(f"AC-{i + 1}", str(item)))
        if not criteria:
            criteria = [
                AcceptanceCriterion("AC-1", "Delegated deliverable matches the delegation brief"),
                AcceptanceCriterion("AC-2", "Tests or evidence for the deliverable are recorded"),
            ]

        gates: List[Any] = []
        for i, item in enumerate(quality_gates):
            if isinstance(item, GateVerdict):
                raise DelegationError("quality_gates must be gate ids or QualityGateResult rows")
            gates.append(item)
        if gates and all(isinstance(g, str) for g in gates):
            from .models import QualityGateResult

            gates = [QualityGateResult(str(g), GateVerdict.PENDING) for g in gates]

        task_id = f"TASK-{graph.next_task_number():04d}"
        child = Task(
            task_id=task_id,
            title=title.strip(),
            description=description.strip() or f"Delegated from {parent_task_id}: {title.strip()}",
            status=TaskState.PENDING,
            priority=Priority(priority),
            assigned_agent=delegatee_agent,
            inputs=[str(x) for x in inputs] or [f"delegation brief from {parent_task_id}"],
            outputs=[str(x) for x in outputs] or ["delegated deliverable"],
            acceptance_criteria=criteria,
            quality_gates=list(gates),
            created_at=stamp,
            updated_at=stamp,
        )
        graph.add_task(child, depends_on=[parent_task_id])
        # ASSIGNED immediately: delegation is an assignment, not a queue.
        transition_task(child, TaskState.ASSIGNED, actor=self.delegator_agent, reason=f"delegated by {self.delegator_agent}", at=stamp)

        self.plan.delegation_counter += 1
        record = DelegationRecord(
            delegation_id=f"DELEG-{self.plan.delegation_counter:04d}",
            plan_id=self.plan.plan_id,
            parent_task_id=parent_task_id,
            task_id=task_id,
            delegator_agent=self.delegator_agent,
            delegatee_agent=delegatee_agent,
            status=DelegationStatus.DELEGATED,
            created_at=stamp,
            updated_at=stamp,
        )
        record.note("DELEGATED", self.delegator_agent, f"child {task_id} assigned to {delegatee_agent}", at=stamp)
        self.records[record.delegation_id] = record
        return record

    # -- track -------------------------------------------------------------------

    def track_status(
        self,
        delegation_id: str,
        new_state: Any,
        actor: str,
        reason: str = "",
        *,
        criteria_results: Optional[Dict[str, bool]] = None,
        gate_results: Optional[Dict[str, Any]] = None,
        at: Optional[str] = None,
    ) -> DelegationRecord:
        """Move the delegated child task through the guarded transition.

        COMPLETED is refused here on purpose: completion must go through
        :meth:`verify_completion` so rules 1-3 are evaluated by a verifier,
        not asserted by the worker.
        """
        record = self.require(delegation_id)
        new_state = TaskState(new_state)
        if new_state not in TRACKABLE_STATES:
            raise DelegationError(f"state {new_state.value} is not trackable via delegation")
        if new_state is TaskState.COMPLETED:
            raise DelegationError("COMPLETED requires verify_completion() (Task Contract §rules 1-3)")
        task = self.plan.graph.require(record.task_id)
        transition_task(
            task,
            new_state,
            actor=actor,
            reason=reason,
            criteria_results=criteria_results,
            gate_results=gate_results,
            at=at,
        )
        record.status = _MIRRORED_DELEGATION_STATE[new_state]
        record.note(new_state.value, actor, reason, at=at)
        return record

    def start(self, delegation_id: str, actor: str, reason: str = "work started", at: Optional[str] = None) -> DelegationRecord:
        return self.track_status(delegation_id, TaskState.RUNNING, actor or self.require(delegation_id).delegatee_agent, reason, at=at)

    def block(self, delegation_id: str, reason: str, actor: str = "", at: Optional[str] = None) -> DelegationRecord:
        record = self.require(delegation_id)
        return self.track_status(delegation_id, TaskState.BLOCKED, actor or record.delegatee_agent, reason, at=at)

    def unblock(self, delegation_id: str, actor: str = "", reason: str = "dependency resolved", at: Optional[str] = None) -> DelegationRecord:
        record = self.require(delegation_id)
        return self.track_status(delegation_id, TaskState.RUNNING, actor or record.delegatee_agent, reason, at=at)

    def submit_for_review(self, delegation_id: str, actor: str = "", at: Optional[str] = None) -> DelegationRecord:
        """Delegatee declares the work done: RUNNING -> REVIEW_REQUIRED (§rule 3 entry)."""
        record = self.require(delegation_id)
        return self.track_status(delegation_id, TaskState.REVIEW_REQUIRED, actor or record.delegatee_agent, "submitted for independent verification", at=at)

    # -- verify ---------------------------------------------------------------------

    def verify_completion(
        self,
        delegation_id: str,
        verifier_agent: str,
        criteria_results: Optional[Dict[str, bool]] = None,
        gate_results: Optional[Dict[str, Any]] = None,
        *,
        at: Optional[str] = None,
    ) -> VerificationReport:
        """Fail-closed independent verification of a SUBMITTED delegation.

        Preconditions (all refusals produce ``ok=False`` reports and move
        the child to REJECTED where the state machine allows it):

        * delegation exists and is SUBMITTED (child in REVIEW_REQUIRED);
        * verifier is a catalog agent, independent of the delegatee and of
          the delegator ("independent auditor cannot be the developer");
        * every acceptance criterion satisfied (rule 1);
        * every required quality gate PASS/NOT_APPLICABLE (rule 2);
        * then REVIEW_REQUIRED -> COMPLETED through the guarded transition.
        """
        record = self.require(delegation_id)
        task = self.plan.graph.require(record.task_id)
        at = at or utc_now_stamp()
        reasons: List[str] = []

        if TaskState(task.status) is not TaskState.REVIEW_REQUIRED or record.status is not DelegationStatus.SUBMITTED:
            raise DelegationError(
                f"delegation {delegation_id} is {record.status.value}; verification requires SUBMITTED"
            )
        if not AGENT_ID_RE.match(verifier_agent or ""):
            raise DelegationError(f"verifier must be a catalog agent id, got {verifier_agent!r}")
        if verifier_agent == record.delegatee_agent:
            reasons.append(
                f"§rule 3: verifier {verifier_agent} is the delegatee (self-review forbidden)"
            )
        if verifier_agent == record.delegator_agent:
            reasons.append(
                f"§rule 3: verifier {verifier_agent} is the delegator (independence forbidden)"
            )

        effective_criteria = {c.criterion_id: c.satisfied for c in task.acceptance_criteria}
        if criteria_results:
            unknown = set(criteria_results) - set(effective_criteria)
            if unknown:
                raise DelegationError(f"criteria_results for unknown ids: {sorted(unknown)}")
            effective_criteria.update({k: bool(v) for k, v in criteria_results.items()})
        unsatisfied = sorted(cid for cid, ok in effective_criteria.items() if not ok)
        if unsatisfied:
            reasons.append(f"§rule 1: unsatisfied criteria: {unsatisfied}")

        effective_gates = {g.gate_id: g.verdict.value for g in task.quality_gates}
        if gate_results:
            unknown = set(gate_results) - set(effective_gates)
            if unknown:
                raise DelegationError(f"gate_results for unknown ids: {sorted(unknown)}")
            effective_gates.update({k: str(v) for k, v in gate_results.items()})
        failing = sorted(
            gid for gid, verdict in effective_gates.items()
            if GateVerdict(verdict) not in {GateVerdict.PASS, GateVerdict.NOT_APPLICABLE}
        )
        if failing:
            reasons.append(f"§rule 2: gates not PASS: {failing}")

        report = VerificationReport(
            delegation_id=record.delegation_id,
            task_id=record.task_id,
            ok=not reasons,
            verifier_agent=verifier_agent,
            reasons=reasons,
            criteria_results=effective_criteria,
            gate_results=effective_gates,
            verified_at=at,
        )
        record.verification = report.to_dict()

        if report.ok:
            transition_task(
                task,
                TaskState.COMPLETED,
                actor=verifier_agent,
                reason="independent verification passed",
                criteria_results=effective_criteria,
                gate_results=effective_gates,
                at=at,
            )
            record.status = DelegationStatus.COMPLETED
            record.note("VERIFIED", verifier_agent, "independent verification passed", at=at)
        else:
            transition_task(
                task,
                TaskState.REJECTED,
                actor=verifier_agent,
                reason="; ".join(reasons),
                criteria_results=effective_criteria,
                gate_results=effective_gates,
                at=at,
            )
            record.status = DelegationStatus.REJECTED
            record.note("REJECTED", verifier_agent, "; ".join(reasons), at=at)
        return report

    def retry_rejected(self, delegation_id: str, actor: str = "", reason: str = "rework started", at: Optional[str] = None) -> DelegationRecord:
        """REJECTED -> RUNNING rework arc (Task Contract allows it)."""
        record = self.require(delegation_id)
        result = self.track_status(delegation_id, TaskState.RUNNING, actor or record.delegatee_agent, reason, at=at)
        return result

    def revoke(self, delegation_id: str, actor: str = "", reason: str = "", at: Optional[str] = None) -> DelegationRecord:
        """Cancel the delegated task (rule 4: reason mandatory)."""
        record = self.require(delegation_id)
        task = self.plan.graph.require(record.task_id)
        if task.is_terminal:
            raise DelegationError(f"cannot revoke {delegation_id}: child task already terminal")
        self.track_status(delegation_id, TaskState.CANCELLED, actor or self.delegator_agent, reason, at=at)
        record.status = DelegationStatus.REVOKED
        return record

    # -- persistence ---------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan.plan_id,
            "delegator_agent": self.delegator_agent,
            "delegations": [r.to_dict() for _, r in sorted(self.records.items())],
        }

    def load_dict(self, data: Dict[str, Any]) -> "DelegationManager":
        if str(data.get("plan_id", self.plan.plan_id)) != self.plan.plan_id:
            raise DelegationError("delegation file belongs to a different plan")
        self.delegator_agent = str(data.get("delegator_agent", self.delegator_agent))
        for row in data.get("delegations", []):
            record = DelegationRecord.from_dict(row)
            self.records[record.delegation_id] = record
        # Counter never rewinds: ids are append-only within the plan.
        used = [int(r.delegation_id.split("-")[1]) for r in self.records.values()]
        self.plan.delegation_counter = max([self.plan.delegation_counter] + used)
        return self

    def save(self, repo_root: Path, project_id: Optional[str] = None) -> Path:
        project_id = project_id or self.plan.project_id
        directory = task_orchestration_dir(repo_root, project_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = delegations_file_path(repo_root, project_id)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, plan: OrchestrationPlan, repo_root: Path, project_id: Optional[str] = None, delegator_agent: str = "AG-001") -> "DelegationManager":
        project_id = project_id or plan.project_id
        manager = cls(plan, delegator_agent=delegator_agent)
        path = delegations_file_path(repo_root, project_id)
        if not path.is_file():
            return manager
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise DelegationError(f"{path}: corrupt delegations JSON: {exc}") from exc
        manager.load_dict(data)
        return manager


#: Child task state → delegation record state (bookkeeping mirror).
_MIRRORED_DELEGATION_STATE: Dict[TaskState, DelegationStatus] = {
    TaskState.RUNNING: DelegationStatus.ACTIVE,
    TaskState.BLOCKED: DelegationStatus.ACTIVE,
    TaskState.REVIEW_REQUIRED: DelegationStatus.SUBMITTED,
    TaskState.FAILED: DelegationStatus.FAILED,
    TaskState.CANCELLED: DelegationStatus.REVOKED,
}


__all__ = [
    "DelegationError",
    "DelegationManager",
    "TRACKABLE_STATES",
]
