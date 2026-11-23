"""Agent coordination manager — consolidated state view (Stage 2B).

Owns the *read model* of a plan: a single :class:`CoordinationState` that
answers, for the coordinator (AG-001) and for status reporting:

* how every task stands per state, per agent, and per wave;
* which tasks are ready to run *now* (dependencies COMPLETED, task not
  terminal/in-flight) and which form the current parallel wave;
* what is blocked and why (blockers);
* how every open delegation stands;
* per participating agent, whether a model is currently selectable through
  the runtime Model Fallback Manager (readiness, never mutation).

Boundary: coordination observes and reports. It mutates nothing — state
changes arrive only through ``DelegationManager`` / guarded task transitions.
Model probing uses :mod:`.model_fallback_integration` and degrades to
``{}`` when the runtime manager cannot load (e.g. no agent definitions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import (
    CoordinationState,
    DelegationRecord,
    DelegationStatus,
    OrchestrationPlan,
    Task,
    TaskGraph,
    TaskState,
    utc_now_stamp,
)

#: States in which a task is "being worked": neither ready-to-start nor done.
IN_FLIGHT_STATES = frozenset(
    {TaskState.ASSIGNED, TaskState.RUNNING, TaskState.REVIEW_REQUIRED, TaskState.BLOCKED}
)
#: States that make a task a scheduling blocker for downstream work.
BLOCKER_STATES = frozenset({TaskState.BLOCKED, TaskState.REJECTED, TaskState.FAILED})


class AgentCoordinationManager:
    """Consolidated coordination view for one plan (+ optional delegations)."""

    def __init__(
        self,
        plan: OrchestrationPlan,
        delegations: Optional[List[DelegationRecord]] = None,
        fallback_manager: Any = None,
    ) -> None:
        self.plan = plan
        self.delegations: List[DelegationRecord] = list(delegations or [])
        self.fallback_manager = fallback_manager

    # -- building blocks -------------------------------------------------------

    @property
    def graph(self) -> TaskGraph:
        return self.plan.graph

    def tasks_of_agent(self, agent_id: str) -> List[Task]:
        return [t for t in sorted(self.graph.tasks.values(), key=lambda t: t.task_id) if t.assigned_agent == agent_id]

    def agent_view(self, agent_id: str) -> Dict[str, Any]:
        """Per-agent workload: counts by state plus task ids."""
        counts: Dict[str, int] = {}
        ids_by_state: Dict[str, List[str]] = {}
        for task in self.tasks_of_agent(agent_id):
            state = TaskState(task.status).value
            counts[state] = counts.get(state, 0) + 1
            ids_by_state.setdefault(state, []).append(task.task_id)
        return {"assigned": len(self.tasks_of_agent(agent_id)), "states": counts, "tasks": ids_by_state}

    def current_wave(self) -> int:
        """0-based index of the first wave that still holds non-terminal work."""
        for index, wave in enumerate(self.graph.waves()):
            if any(not self.graph.tasks[t].is_terminal for t in wave):
                return index
        return len(self.graph.waves())

    def ready_tasks(self) -> List[str]:
        return self.graph.ready_tasks()

    def in_flight_tasks(self) -> List[str]:
        return sorted(
            t.task_id
            for t in self.graph.tasks.values()
            if TaskState(t.status) in IN_FLIGHT_STATES
        )

    def blockers(self) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for task_id in sorted(self.graph.tasks):
            task = self.graph.tasks[task_id]
            state = TaskState(task.status)
            if state in BLOCKER_STATES:
                reason = task.status_note or "no reason recorded"
                rows.append({"task_id": task_id, "state": state.value, "reason": reason, "agent": task.assigned_agent})
        # Unsatisfied (never-evaluated) gates on submitted work are coordination
        # blockers too: they will refuse completion until recorded.
        for record in self.delegations:
            if record.status is DelegationStatus.SUBMITTED:
                task = self.graph.tasks.get(record.task_id)
                if task is not None:
                    pending = [g.gate_id for g in task.quality_gates if g.verdict.value == "PENDING"]
                    if pending:
                        rows.append(
                            {
                                "task_id": task.task_id,
                                "state": "GATES_PENDING",
                                "reason": f"quality gates not evaluated: {pending}",
                                "agent": task.assigned_agent,
                            }
                        )
        return rows

    def delegation_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "delegation_id": r.delegation_id,
                "parent_task_id": r.parent_task_id,
                "task_id": r.task_id,
                "delegatee_agent": r.delegatee_agent,
                "delegator_agent": r.delegator_agent,
                "status": DelegationStatus(r.status).value,
                "updated_at": r.updated_at,
            }
            for r in sorted(self.delegations, key=lambda r: r.delegation_id)
        ]

    def model_status(self) -> Dict[str, Dict[str, Any]]:
        """Per participating agent: is a model selectable right now?

        Read-only probe through the runtime Model Fallback Manager; any
        loading failure degrades to an empty map (status must never crash).
        """
        manager = self.fallback_manager
        if manager is None:
            return {}
        from .model_fallback_integration import agent_model_status

        status: Dict[str, Dict[str, Any]] = {}
        agents = {t.assigned_agent for t in self.graph.tasks.values() if t.assigned_agent}
        for agent_id in sorted(agents):
            try:
                status[agent_id] = agent_model_status(manager, agent_id)
            except Exception:
                continue
        return status

    # -- consolidated view ---------------------------------------------------------

    def consolidated_state(self, include_model_status: bool = True) -> CoordinationState:
        waves = self.graph.waves()
        completed = self.graph.completed_ids()
        workload: Dict[str, Dict[str, int]] = {}
        for task in self.graph.tasks.values():
            if not task.assigned_agent:
                continue
            row = workload.setdefault(task.assigned_agent, {"assigned": 0, "completed": 0, "in_flight": 0})
            row["assigned"] += 1
            if TaskState(task.status) is TaskState.COMPLETED:
                row["completed"] += 1
            elif TaskState(task.status) in IN_FLIGHT_STATES:
                row["in_flight"] += 1
        return CoordinationState(
            plan_id=self.plan.plan_id,
            project_id=self.plan.project_id,
            goal=self.plan.analysis.goal,
            generated_at=utc_now_stamp(),
            task_counts=self.graph.state_counts(),
            total_tasks=len(self.graph.tasks),
            completed_tasks=len(completed),
            ready_tasks=self.ready_tasks(),
            in_flight=self.in_flight_tasks(),
            blockers=self.blockers(),
            waves=waves,
            current_wave=self.current_wave(),
            agent_workload=workload,
            delegations=self.delegation_summary(),
            model_status=self.model_status() if include_model_status else {},
            done=bool(self.graph.tasks) and all(t.is_terminal for t in self.graph.tasks.values()),
        )


__all__ = [
    "BLOCKER_STATES",
    "IN_FLIGHT_STATES",
    "AgentCoordinationManager",
]
