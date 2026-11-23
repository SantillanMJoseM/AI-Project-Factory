"""Data models for the Task Orchestration Engine (Stage 2B).

Pure stdlib. Encodes the task lifecycle mandated by
``contracts/task-contract.md`` (states, allowed transitions, required
fields, and rules 1-4) plus the planning artifacts owned by this package:

* ``Task``              - one unit of assigned work with acceptance criteria
  and quality-gate results;
* ``TaskGraph``         - tasks + dependency edges, cycle-checked, with
  deterministic topological order and parallel wave grouping;
* ``DelegationRecord``  - append-only history of one parent→child work
  delegation between agents;
* ``OrchestrationPlan`` - goal, analysis, graph, and per-task skill bindings;
* ``CoordinationState`` - consolidated point-in-time view for
  ``AgentCoordinationManager``.

Design posture (inherited from Stage 2A / ADR-002): fail-closed — illegal
transitions, cycles, self-review, unsatisfied criteria, or non-PASS gates
refuse completion and are never silently repaired. Task ids follow
``orchestration/task-management/task-management.md`` (``TASK-0001``); agent
ids follow the catalog (``AG-NNN``).

Boundary: this module authorizes nothing and touches no agent/runtime/config
files. It is data + state machine only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Controlled vocabularies and id formats
# ---------------------------------------------------------------------------

TASK_ID_RE = re.compile(r"^TASK-[0-9]{4}$")
PLAN_ID_RE = re.compile(r"^PLAN-PROJECT-[0-9]{3}-[0-9]{4}$")
DELEG_ID_RE = re.compile(r"^DELEG-[0-9]{4}$")
PROJECT_ID_RE = re.compile(r"^PROJECT-[0-9]{3}$")
AGENT_ID_RE = re.compile(r"^AG-[0-9]{3}$")

#: The 18-agent catalog (``agents/``), used for fail-closed agent validation
#: without importing the agent definitions themselves.
KNOWN_AGENTS: Tuple[str, ...] = tuple(f"AG-{i:03d}" for i in range(1, 19))


def utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskError(ValueError):
    """Base error for task-orchestration data violations (fail-closed)."""


class CycleError(TaskError):
    """A dependency cycle makes the graph unplannable."""


class TaskState(str, Enum):
    """Task Contract §States, verbatim."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset({TaskState.COMPLETED, TaskState.CANCELLED})

#: Task Contract §Allowed transitions, verbatim, including the fan-in of
#: "Any non-terminal -> CANCELLED" and the FAILED -> PENDING retry arc.
ALLOWED_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
    TaskState.PENDING: {TaskState.ASSIGNED, TaskState.CANCELLED},
    TaskState.ASSIGNED: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.BLOCKED,
        TaskState.REVIEW_REQUIRED,
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.BLOCKED: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.REVIEW_REQUIRED: {
        TaskState.COMPLETED,
        TaskState.REJECTED,
        TaskState.CANCELLED,
    },
    TaskState.REJECTED: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.PENDING, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.CANCELLED: set(),
}


def can_transition(current: Any, target: Any) -> bool:
    """Pure state-machine legality (Task Contract §Allowed transitions)."""
    current = TaskState(current)
    target = TaskState(target)
    return target in ALLOWED_TRANSITIONS[current]


class Priority(str, Enum):
    """Task Contract requires ``priority``; vocabulary is this package's."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateVerdict(str, Enum):
    """Quality-gate verdicts the completion guard understands.

    The Task Contract forbids COMPLETED while a required gate is FAIL or
    BLOCKED (§rule 2). This package is stricter than the minimum: a gate in
    PENDING (never evaluated) also refuses completion — fail-closed posture
    inherited from Stage 2A.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


#: Verdicts that satisfy the completion guard (stricter than contract minimum).
PASSING_GATE_VERDICTS = frozenset({GateVerdict.PASS, GateVerdict.NOT_APPLICABLE})


class DelegationStatus(str, Enum):
    """Lifecycle of one delegation record (mirrors the child task posture)."""

    DELEGATED = "DELEGATED"        # child created, not yet running
    ACTIVE = "ACTIVE"              # child RUNNING under delegation
    SUBMITTED = "SUBMITTED"        # child REVIEW_REQUIRED, awaiting verification
    VERIFIED = "VERIFIED"          # independent verification passed
    REJECTED = "REJECTED"          # verification failed; work returned
    REVOKED = "REVOKED"            # delegation cancelled by the delegator
    COMPLETED = "COMPLETED"        # child COMPLETED post-verification
    FAILED = "FAILED"              # child FAILED


# ---------------------------------------------------------------------------
# Task and its sub-records
# ---------------------------------------------------------------------------


@dataclass
class AcceptanceCriterion:
    """One acceptance criterion (Task Contract §Rules 1: mandatory gate to COMPLETED)."""

    criterion_id: str
    description: str
    satisfied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "description": self.description,
            "satisfied": self.satisfied,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcceptanceCriterion":
        return cls(
            criterion_id=str(data["criterion_id"]),
            description=str(data.get("description", "")),
            satisfied=bool(data.get("satisfied", False)),
        )


@dataclass
class QualityGateResult:
    """Latest recorded verdict for one required quality gate."""

    gate_id: str
    verdict: GateVerdict = GateVerdict.PENDING
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"gate_id": self.gate_id, "verdict": self.verdict.value, "notes": self.notes}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityGateResult":
        return cls(
            gate_id=str(data["gate_id"]),
            verdict=GateVerdict(str(data.get("verdict", GateVerdict.PENDING.value))),
            notes=str(data.get("notes", "")),
        )


@dataclass
class StatusHistoryEntry:
    """Append-only transition record; the audit trail of one task."""

    from_state: str
    to_state: str
    actor: str
    reason: str
    at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "reason": self.reason,
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusHistoryEntry":
        return cls(
            from_state=str(data["from_state"]),
            to_state=str(data["to_state"]),
            actor=str(data.get("actor", "")),
            reason=str(data.get("reason", "")),
            at=str(data.get("at", "")),
        )


@dataclass
class Task:
    """One unit of assigned work. Required fields per ``contracts/task-contract.md``.

    The state machine here enforces *legality of transitions* only. The
    Task Contract completion rules (1: acceptance criteria, 2: quality
    gates, 3: independent review, 4: cancellation reason) are enforced by
    :func:`transition_task`, the single guarded transition entry point.
    """

    task_id: str
    title: str
    description: str = ""
    status: TaskState = TaskState.PENDING
    priority: Priority = Priority.MEDIUM
    assigned_agent: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    quality_gates: List[QualityGateResult] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_stamp)
    updated_at: str = field(default_factory=utc_now_stamp)
    #: Last explanatory note for BLOCKED / CANCELLED / REJECTED transitions.
    status_note: str = ""
    #: Independent reviewer recorded when entering REVIEW_REQUIRED (§rule 3).
    submitted_by: str = ""
    reviewed_by: str = ""
    history: List[StatusHistoryEntry] = field(default_factory=list)

    # -- validation ---------------------------------------------------------

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not TASK_ID_RE.match(self.task_id):
            issues.append(f"bad task_id: {self.task_id!r} (expected TASK-NNNN)")
        if not self.title.strip():
            issues.append("title is required")
        if not self.description.strip():
            issues.append("description is required")
        if not AGENT_ID_RE.match(self.assigned_agent or ""):
            issues.append(f"bad assigned_agent: {self.assigned_agent!r} (expected AG-NNN)")
        if self.assigned_agent and self.assigned_agent not in KNOWN_AGENTS:
            issues.append(f"assigned_agent {self.assigned_agent!r} not in catalog AG-001..AG-018")
        try:
            TaskState(self.status)
        except ValueError:
            issues.append(f"unknown status: {self.status!r}")
        try:
            Priority(self.priority)
        except ValueError:
            issues.append(f"unknown priority: {self.priority!r}")
        seen: Set[str] = set()
        for criterion in self.acceptance_criteria:
            if criterion.criterion_id in seen:
                issues.append(f"duplicate criterion_id: {criterion.criterion_id}")
            seen.add(criterion.criterion_id)
        seen_gates: Set[str] = set()
        for gate in self.quality_gates:
            if gate.gate_id in seen_gates:
                issues.append(f"duplicate gate_id: {gate.gate_id}")
            seen_gates.add(gate.gate_id)
        return issues

    # -- queries ------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        return TaskState(self.status) in TERMINAL_STATES

    def criterion_ids(self) -> List[str]:
        return [c.criterion_id for c in self.acceptance_criteria]

    def gate_ids(self) -> List[str]:
        return [g.gate_id for g in self.quality_gates]

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": TaskState(self.status).value,
            "priority": Priority(self.priority).value,
            "assigned_agent": self.assigned_agent,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "quality_gates": [g.to_dict() for g in self.quality_gates],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status_note": self.status_note,
            "submitted_by": self.submitted_by,
            "reviewed_by": self.reviewed_by,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task = cls(
            task_id=str(data["id"]),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            status=TaskState(str(data.get("status", TaskState.PENDING.value))),
            priority=Priority(str(data.get("priority", Priority.MEDIUM.value))),
            assigned_agent=str(data.get("assigned_agent", "")),
            inputs=[str(x) for x in data.get("inputs", [])],
            outputs=[str(x) for x in data.get("outputs", [])],
            acceptance_criteria=[
                AcceptanceCriterion.from_dict(c) for c in data.get("acceptance_criteria", [])
            ],
            quality_gates=[QualityGateResult.from_dict(g) for g in data.get("quality_gates", [])],
            created_at=str(data.get("created_at", utc_now_stamp())),
            updated_at=str(data.get("updated_at", utc_now_stamp())),
            status_note=str(data.get("status_note", "")),
            submitted_by=str(data.get("submitted_by", "")),
            reviewed_by=str(data.get("reviewed_by", "")),
            history=[StatusHistoryEntry.from_dict(h) for h in data.get("history", [])],
        )
        issues = task.validate()
        if issues:
            raise TaskError("invalid task: " + "; ".join(issues))
        return task


# ---------------------------------------------------------------------------
# Guarded transition (the single place Task Contract rules are enforced)
# ---------------------------------------------------------------------------


def transition_task(
    task: Task,
    target: Any,
    *,
    actor: str,
    reason: str = "",
    criteria_results: Optional[Dict[str, bool]] = None,
    gate_results: Optional[Dict[str, Any]] = None,
    at: Optional[str] = None,
) -> StatusHistoryEntry:
    """Apply one guarded transition to ``task`` in place; returns the history entry.

    Enforces, fail-closed (all refusals raise :class:`TaskError` and leave
    the task untouched):

    * §Allowed transitions state machine (via :func:`can_transition`);
    * §rule 1 — COMPLETED requires every acceptance criterion satisfied
      (``criteria_results`` overrides the stored flags when provided);
    * §rule 2 — COMPLETED requires every quality gate PASS/NOT_APPLICABLE
      (``gate_results`` overrides the stored verdicts when provided;
      PENDING/absent also refuses — stricter than the contract minimum);
    * §rule 3 — REVIEW_REQUIRED → COMPLETED requires an *independent*
      reviewer: ``actor`` must differ from ``assigned_agent`` (mirrors
      "the independent auditor cannot be the developer");
    * §rule 4 — CANCELLED requires a reason.
    """
    current = TaskState(task.status)
    target = TaskState(target)
    if not AGENT_ID_RE.match(actor or ""):
        raise TaskError(f"transition actor must be an agent id (AG-NNN), got {actor!r}")
    if not can_transition(current, target):
        raise TaskError(f"illegal task transition: {current.value} -> {target.value} for {task.task_id}")

    # Materialize prospective criterion/gate state (never mutate before checks pass).
    new_criteria = list(task.acceptance_criteria)
    if criteria_results:
        unknown = set(criteria_results) - set(task.criterion_ids())
        if unknown:
            raise TaskError(f"criteria_results for unknown criterion ids: {sorted(unknown)}")
        new_criteria = [
            AcceptanceCriterion(c.criterion_id, c.description, bool(criteria_results.get(c.criterion_id, c.satisfied)))
            for c in task.acceptance_criteria
        ]
    new_gates = list(task.quality_gates)
    if gate_results:
        unknown = set(gate_results) - set(task.gate_ids())
        if unknown:
            raise TaskError(f"gate_results for unknown gate ids: {sorted(unknown)}")
        new_gates = [
            QualityGateResult(g.gate_id, GateVerdict(str(gate_results.get(g.gate_id, g.verdict.value))), g.notes)
            for g in task.quality_gates
        ]

    if target is TaskState.COMPLETED:
        unsatisfied = [c.criterion_id for c in new_criteria if not c.satisfied]
        if unsatisfied:
            raise TaskError(
                f"§rule 1: {task.task_id} cannot COMPLETE; unsatisfied criteria: {unsatisfied}"
            )
        failing = [g.gate_id for g in new_gates if g.verdict not in PASSING_GATE_VERDICTS]
        if failing:
            raise TaskError(
                f"§rule 2: {task.task_id} cannot COMPLETE; gates not PASS: {failing}"
            )
        if current is TaskState.REVIEW_REQUIRED and actor == task.assigned_agent:
            raise TaskError(
                f"§rule 3: {task.task_id} REVIEW_REQUIRED->COMPLETED requires an "
                f"independent reviewer (actor {actor} == assigned_agent)"
            )

    if target is TaskState.CANCELLED and not reason.strip():
        raise TaskError(f"§rule 4: cancelling {task.task_id} requires a reason")

    stamp = at or utc_now_stamp()
    entry = StatusHistoryEntry(current.value, target.value, actor, reason, stamp)
    task.status = target
    task.updated_at = stamp
    task.history.append(entry)
    if criteria_results:
        task.acceptance_criteria = new_criteria
    if gate_results:
        task.quality_gates = new_gates
    if target in (TaskState.BLOCKED, TaskState.REJECTED, TaskState.CANCELLED, TaskState.FAILED):
        task.status_note = reason
    if target is TaskState.REVIEW_REQUIRED:
        task.submitted_by = actor
    if target is TaskState.COMPLETED and current is TaskState.REVIEW_REQUIRED:
        task.reviewed_by = actor
    return entry


# ---------------------------------------------------------------------------
# TaskGraph
# ---------------------------------------------------------------------------


class TaskGraph:
    """Tasks + dependency edges ("task B depends on A"), cycle-checked.

    Every mutation is validated in full (ids, agents, dangling edges,
    self-edges, cycles): an edit that would corrupt the graph raises and
    leaves the graph untouched — fail-closed, no partial plans.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}
        #: task_id -> ids that must COMPLETE before this task may start.
        self.dependencies: Dict[str, Set[str]] = {}

    # -- mutation -----------------------------------------------------------

    def add_task(self, task: Task, depends_on: Iterable[str] = ()) -> Task:
        if task.task_id in self.tasks:
            raise TaskError(f"duplicate task_id: {task.task_id}")
        issues = task.validate()
        if issues:
            raise TaskError("invalid task: " + "; ".join(issues))
        deps = {str(d) for d in depends_on}
        if task.task_id in deps:
            raise TaskError(f"task {task.task_id} cannot depend on itself")
        dangling = sorted(d for d in deps if d not in self.tasks)
        if dangling:
            raise TaskError(f"dependencies not in graph: {dangling}")
        candidate_deps = dict(self.dependencies)
        candidate_deps[task.task_id] = deps
        graph = self._candidate(tasks=dict(self.tasks, **{task.task_id: task}), dependencies=candidate_deps)
        cycle = graph.find_cycle()
        if cycle:
            raise CycleError("dependency cycle introduced: " + " -> ".join(cycle))
        self.tasks[task.task_id] = task
        self.dependencies[task.task_id] = deps
        return task

    def remove_task(self, task_id: str) -> None:
        """Remove a task and its edges. Refuses if it has dependents."""
        if task_id not in self.tasks:
            raise TaskError(f"unknown task_id: {task_id}")
        dependents = sorted(t for t, deps in self.dependencies.items() if task_id in deps)
        if dependents:
            raise TaskError(f"cannot remove {task_id}; it is a dependency of {dependents}")
        del self.tasks[task_id]
        self.dependencies.pop(task_id, None)

    def add_dependency(self, task_id: str, depends_on_id: str) -> None:
        if task_id not in self.tasks or depends_on_id not in self.tasks:
            raise TaskError(f"add_dependency: unknown endpoint(s): {task_id!r}, {depends_on_id!r}")
        if task_id == depends_on_id:
            raise TaskError(f"task {task_id} cannot depend on itself")
        if depends_on_id in self.dependencies.get(task_id, set()):
            return
        candidate = self._candidate(
            dependencies={**self.dependencies, task_id: set(self.dependencies.get(task_id, set())) | {depends_on_id}}
        )
        cycle = candidate.find_cycle()
        if cycle:
            raise CycleError("dependency cycle introduced: " + " -> ".join(cycle))
        self.dependencies.setdefault(task_id, set()).add(depends_on_id)

    def _candidate(self, tasks: Optional[Dict[str, Task]] = None, dependencies: Optional[Dict[str, Set[str]]] = None) -> "TaskGraph":
        probe = TaskGraph()
        probe.tasks = dict(self.tasks if tasks is None else tasks)
        probe.dependencies = {k: set(v) for k, v in (self.dependencies if dependencies is None else dependencies).items()}
        return probe

    # -- queries --------------------------------------------------------------

    def require(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if task is None:
            raise TaskError(f"unknown task_id: {task_id}")
        return task

    def dependents_of(self, task_id: str) -> List[str]:
        return sorted(t for t, deps in self.dependencies.items() if task_id in deps)

    def missing_dependencies(self, task_id: str) -> List[str]:
        """Dependencies of ``task_id`` that are not COMPLETED yet."""
        self.require(task_id)
        return sorted(
            d for d in self.dependencies.get(task_id, set())
            if TaskState(self.tasks[d].status) is not TaskState.COMPLETED
        )

    def is_ready(self, task_id: str) -> bool:
        """Executable next: not terminal, dependencies all COMPLETED."""
        try:
            task = self.require(task_id)
        except TaskError:
            return False
        if task.is_terminal or TaskState(task.status) in (
            TaskState.RUNNING,
            TaskState.REVIEW_REQUIRED,
            TaskState.BLOCKED,
        ):
            return False
        return not self.missing_dependencies(task_id)

    def completed_ids(self) -> List[str]:
        return sorted(
            t for t, task in self.tasks.items() if TaskState(task.status) is TaskState.COMPLETED
        )

    def find_cycle(self) -> Optional[List[str]]:
        """First cycle found (DFS, deterministic id order), or None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {t: WHITE for t in self.tasks}
        stack: List[str] = []

        def visit(node: str) -> Optional[List[str]]:
            color[node] = GRAY
            stack.append(node)
            for nxt in sorted(self.dependencies.get(node, set()) & set(self.tasks)):
                if color.get(nxt) == GRAY:
                    idx = stack.index(nxt)
                    return stack[idx:] + [nxt]
                if color.get(nxt) == WHITE:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            color[node] = BLACK
            return None

        for task_id in sorted(self.tasks):
            if color[task_id] == WHITE:
                found = visit(task_id)
                if found:
                    return found
        return None

    def topological_order(self) -> List[str]:
        """Kahn's algorithm, deterministic (ids ascending within a level).

        Raises :class:`CycleError` if the graph is not a DAG (fail-closed).
        """
        indegree = {t: len(self.dependencies.get(t, set()) & set(self.tasks)) for t in self.tasks}
        order: List[str] = []
        ready = sorted(t for t, d in indegree.items() if d == 0)
        while ready:
            node = ready.pop(0)
            order.append(node)
            for child in self.dependents_of(node):
                indegree[child] -= 1
                if indegree[child] == 0:
                    # re-insert keeping the frontier sorted
                    ready.append(child)
                    ready.sort()
        if len(order) != len(self.tasks):
            unplanned = sorted(set(self.tasks) - set(order))
            raise CycleError(f"graph has a cycle covering/unreachable: {unplanned}")
        return order

    def waves(self) -> List[List[str]]:
        """Parallel execution groups: wave k holds tasks whose every
        dependency lands in an earlier wave. Tasks inside a wave are
        mutually independent and may run in parallel; waves run sequentially.
        """
        wave_of: Dict[str, int] = {}
        for task_id in self.topological_order():
            deps = self.dependencies.get(task_id, set()) & set(self.tasks)
            level = 0 if not deps else max(wave_of[d] + 1 for d in deps)
            wave_of[task_id] = level
        buckets: Dict[int, List[str]] = {}
        for task_id, level in wave_of.items():
            buckets.setdefault(level, []).append(task_id)
        return [sorted(buckets[level]) for level in sorted(buckets)]

    def ready_tasks(self) -> List[str]:
        return sorted(t for t in self.tasks if self.is_ready(t))

    def state_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for task in self.tasks.values():
            key = TaskState(task.status).value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def next_task_number(self) -> int:
        used = [int(t.split("-")[1]) for t in self.tasks if TASK_ID_RE.match(t)]
        return (max(used) + 1) if used else 1

    # -- validation / serialization -------------------------------------------

    def validate(self) -> List[str]:
        issues: List[str] = []
        for task in self.tasks.values():
            for issue in task.validate():
                issues.append(f"{task.task_id}: {issue}")
        for task_id, deps in self.dependencies.items():
            if task_id not in self.tasks:
                issues.append(f"dependency row for unknown task: {task_id}")
                continue
            for dep in sorted(deps):
                if dep not in self.tasks:
                    issues.append(f"{task_id}: dangling dependency {dep}")
                if dep == task_id:
                    issues.append(f"{task_id}: self-dependency")
        cycle = self.find_cycle()
        if cycle:
            issues.append("cycle: " + " -> ".join(cycle))
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": [self.tasks[t].to_dict() for t in sorted(self.tasks)],
            "dependencies": {t: sorted(self.dependencies.get(t, set())) for t in sorted(self.dependencies)},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskGraph":
        graph = cls()
        for row in data.get("tasks", []):
            graph.tasks[str(row["id"])] = Task.from_dict(row)
        for task_id, deps in (data.get("dependencies") or {}).items():
            graph.dependencies[str(task_id)] = {str(d) for d in deps}
        issues = graph.validate()
        if issues:
            raise TaskError("invalid task graph: " + "; ".join(issues))
        return graph


# ---------------------------------------------------------------------------
# DelegationRecord
# ---------------------------------------------------------------------------


@dataclass
class DelegationRecord:
    """One parent→child work delegation, with append-only history.

    ``parent_task_id`` is the delegating (coordinator-owned) task;
    ``task_id`` is the delegated child task created inside the graph and
    assigned to ``delegatee_agent``.
    """

    delegation_id: str
    plan_id: str
    parent_task_id: str
    task_id: str
    delegator_agent: str
    delegatee_agent: str
    status: DelegationStatus = DelegationStatus.DELEGATED
    created_at: str = field(default_factory=utc_now_stamp)
    updated_at: str = field(default_factory=utc_now_stamp)
    verification: Optional[Dict[str, Any]] = None
    history: List[StatusHistoryEntry] = field(default_factory=list)

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not DELEG_ID_RE.match(self.delegation_id):
            issues.append(f"bad delegation_id: {self.delegation_id!r} (expected DELEG-NNNN)")
        if not PLAN_ID_RE.match(self.plan_id):
            issues.append(f"bad plan_id: {self.plan_id!r}")
        for label, value in (
            ("parent_task_id", self.parent_task_id),
            ("task_id", self.task_id),
        ):
            if not TASK_ID_RE.match(value):
                issues.append(f"bad {label}: {value!r}")
        for label, value in (
            ("delegator_agent", self.delegator_agent),
            ("delegatee_agent", self.delegatee_agent),
        ):
            if not AGENT_ID_RE.match(value or ""):
                issues.append(f"bad {label}: {value!r}")
        try:
            DelegationStatus(self.status)
        except ValueError:
            issues.append(f"unknown delegation status: {self.status!r}")
        return issues

    def note(self, event: str, actor: str, reason: str = "", at: Optional[str] = None) -> StatusHistoryEntry:
        entry = StatusHistoryEntry(
            self.status.value if isinstance(self.status, Enum) else str(self.status),
            event,
            actor,
            reason,
            at or utc_now_stamp(),
        )
        self.history.append(entry)
        self.updated_at = entry.at
        return entry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "plan_id": self.plan_id,
            "parent_task_id": self.parent_task_id,
            "task_id": self.task_id,
            "delegator_agent": self.delegator_agent,
            "delegatee_agent": self.delegatee_agent,
            "status": DelegationStatus(self.status).value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "verification": self.verification,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelegationRecord":
        record = cls(
            delegation_id=str(data["delegation_id"]),
            plan_id=str(data["plan_id"]),
            parent_task_id=str(data["parent_task_id"]),
            task_id=str(data["task_id"]),
            delegator_agent=str(data["delegator_agent"]),
            delegatee_agent=str(data["delegatee_agent"]),
            status=DelegationStatus(str(data.get("status", DelegationStatus.DELEGATED.value))),
            created_at=str(data.get("created_at", utc_now_stamp())),
            updated_at=str(data.get("updated_at", utc_now_stamp())),
            verification=data.get("verification"),
            history=[StatusHistoryEntry.from_dict(h) for h in data.get("history", [])],
        )
        issues = record.validate()
        if issues:
            raise TaskError("invalid delegation record: " + "; ".join(issues))
        return record


@dataclass
class VerificationReport:
    """Outcome of :meth:`DelegationManager.verify_completion` (fail-closed)."""

    delegation_id: str
    task_id: str
    ok: bool
    verifier_agent: str
    reasons: List[str] = field(default_factory=list)
    criteria_results: Dict[str, bool] = field(default_factory=dict)
    gate_results: Dict[str, str] = field(default_factory=dict)
    verified_at: str = field(default_factory=utc_now_stamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "task_id": self.task_id,
            "ok": self.ok,
            "verifier_agent": self.verifier_agent,
            "reasons": list(self.reasons),
            "criteria_results": dict(self.criteria_results),
            "gate_results": dict(self.gate_results),
            "verified_at": self.verified_at,
        }


# ---------------------------------------------------------------------------
# OrchestrationPlan
# ---------------------------------------------------------------------------


@dataclass
class GoalAnalysis:
    """Result of :meth:`TaskOrchestrationEngine.analyze_goal`."""

    goal: str
    capabilities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    analyzed_at: str = field(default_factory=utc_now_stamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "capabilities": list(self.capabilities),
            "constraints": list(self.constraints),
            "risks": list(self.risks),
            "analyzed_at": self.analyzed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalAnalysis":
        return cls(
            goal=str(data.get("goal", "")),
            capabilities=[str(c) for c in data.get("capabilities", [])],
            constraints=[str(c) for c in data.get("constraints", [])],
            risks=[str(r) for r in data.get("risks", [])],
            analyzed_at=str(data.get("analyzed_at", utc_now_stamp())),
        )


@dataclass
class OrchestrationPlan:
    """One planned goal: analysis + task graph + per-task skill bindings."""

    plan_id: str
    project_id: str
    analysis: GoalAnalysis
    graph: TaskGraph
    skills_by_task: Dict[str, List[str]] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_stamp)
    #: Monotonic counters so redelegation/resume reuse ids without collision.
    delegation_counter: int = 0

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not PLAN_ID_RE.match(self.plan_id):
            issues.append(f"bad plan_id: {self.plan_id!r}")
        if not PROJECT_ID_RE.match(self.project_id):
            issues.append(f"bad project_id: {self.project_id!r} (expected PROJECT-NNN)")
        issues.extend(self.graph.validate())
        for task_id in self.skills_by_task:
            if task_id not in self.graph.tasks:
                issues.append(f"skill binding for unknown task: {task_id}")
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "analysis": self.analysis.to_dict(),
            "graph": self.graph.to_dict(),
            "skills_by_task": {t: list(s) for t, s in sorted(self.skills_by_task.items())},
            "created_at": self.created_at,
            "delegation_counter": self.delegation_counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestrationPlan":
        plan = cls(
            plan_id=str(data["plan_id"]),
            project_id=str(data["project_id"]),
            analysis=GoalAnalysis.from_dict(data.get("analysis", {"goal": ""})),
            graph=TaskGraph.from_dict(data.get("graph", {})),
            skills_by_task={str(t): [str(s) for s in rows] for t, rows in (data.get("skills_by_task") or {}).items()},
            created_at=str(data.get("created_at", utc_now_stamp())),
            delegation_counter=int(data.get("delegation_counter", 0)),
        )
        issues = plan.validate()
        if issues:
            raise TaskError("invalid orchestration plan: " + "; ".join(issues))
        return plan


# ---------------------------------------------------------------------------
# CoordinationState
# ---------------------------------------------------------------------------


@dataclass
class CoordinationState:
    """Consolidated point-in-time view of one plan (read model, no authority)."""

    plan_id: str
    project_id: str
    goal: str
    generated_at: str = field(default_factory=utc_now_stamp)
    task_counts: Dict[str, int] = field(default_factory=dict)
    total_tasks: int = 0
    completed_tasks: int = 0
    ready_tasks: List[str] = field(default_factory=list)
    in_flight: List[str] = field(default_factory=list)
    blockers: List[Dict[str, str]] = field(default_factory=list)
    waves: List[List[str]] = field(default_factory=list)
    current_wave: int = 0
    agent_workload: Dict[str, Dict[str, int]] = field(default_factory=dict)
    delegations: List[Dict[str, Any]] = field(default_factory=list)
    model_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    done: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "goal": self.goal,
            "generated_at": self.generated_at,
            "task_counts": dict(self.task_counts),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "ready_tasks": list(self.ready_tasks),
            "in_flight": list(self.in_flight),
            "blockers": list(self.blockers),
            "waves": [list(w) for w in self.waves],
            "current_wave": self.current_wave,
            "agent_workload": {a: dict(v) for a, v in sorted(self.agent_workload.items())},
            "delegations": list(self.delegations),
            "model_status": {a: dict(v) for a, v in sorted(self.model_status.items())},
            "done": self.done,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoordinationState":
        return cls(
            plan_id=str(data["plan_id"]),
            project_id=str(data["project_id"]),
            goal=str(data.get("goal", "")),
            generated_at=str(data.get("generated_at", utc_now_stamp())),
            task_counts={str(k): int(v) for k, v in (data.get("task_counts") or {}).items()},
            total_tasks=int(data.get("total_tasks", 0)),
            completed_tasks=int(data.get("completed_tasks", 0)),
            ready_tasks=[str(t) for t in data.get("ready_tasks", [])],
            in_flight=[str(t) for t in data.get("in_flight", [])],
            blockers=[dict(b) for b in data.get("blockers", [])],
            waves=[list(w) for w in data.get("waves", [])],
            current_wave=int(data.get("current_wave", 0)),
            agent_workload={str(a): {str(k): int(v) for k, v in rows.items()} for a, rows in (data.get("agent_workload") or {}).items()},
            delegations=[dict(r) for r in data.get("delegations", [])],
            model_status={str(a): dict(v) for a, v in (data.get("model_status") or {}).items()},
            done=bool(data.get("done", False)),
        )


__all__ = [
    "ACCEPTED_GATE_VERDICTS",
    "ALLOWED_TRANSITIONS",
    "AcceptanceCriterion",
    "AGENT_ID_RE",
    "CoordinationState",
    "CycleError",
    "DelegationRecord",
    "DelegationStatus",
    "GoalAnalysis",
    "KNOWN_AGENTS",
    "OrchestrationPlan",
    "PASSING_GATE_VERDICTS",
    "PLAN_ID_RE",
    "Priority",
    "PROJECT_ID_RE",
    "QualityGateResult",
    "StatusHistoryEntry",
    "TERMINAL_STATES",
    "Task",
    "TaskError",
    "TaskGraph",
    "TaskState",
    "VerificationReport",
    "can_transition",
    "transition_task",
    "utc_now_stamp",
]

# Kept for export symmetry; the canonical constant is PASSING_GATE_VERDICTS.
ACCEPTED_GATE_VERDICTS = PASSING_GATE_VERDICTS
