"""Coordination manager tests: consolidated read model, wave/blocker views,
per-agent workload, and the model-fallback integration probe (read-only,
degradable)."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.task_orchestration.coordination import (  # noqa: E402
    AgentCoordinationManager,
)
from orchestration.task_orchestration.model_fallback_integration import (  # noqa: E402
    agent_model_status,
    bind_task_model,
    make_manager,
    on_task_model_error,
    recover_primary_model,
)
from orchestration.task_orchestration.delegation import DelegationManager  # noqa: E402
from orchestration.task_orchestration.models import (  # noqa: E402
    CoordinationState,
    DelegationStatus,
    GoalAnalysis,
    OrchestrationPlan,
    Task,
    TaskGraph,
    TaskState,
    transition_task,
)


def make_plan():
    """A: AG-001 -> {B: AG-008, C: AG-012}; D: AG-008 fan-in from B and C."""
    graph = TaskGraph()
    rows = [
        ("TASK-0001", "AG-001", []),
        ("TASK-0002", "AG-008", ["TASK-0001"]),
        ("TASK-0003", "AG-012", ["TASK-0001"]),
        ("TASK-0004", "AG-008", ["TASK-0002", "TASK-0003"]),
    ]
    for task_id, agent, deps in rows:
        graph.add_task(
            Task(
                task_id=task_id,
                title=f"step {task_id}",
                description="coordination fixture task",
                assigned_agent=agent,
            ),
            depends_on=deps,
        )
    return OrchestrationPlan(
        plan_id="PLAN-PROJECT-001-0001",
        project_id="PROJECT-001",
        analysis=GoalAnalysis(goal="coordinate me"),
        graph=graph,
    )


def complete(plan, task_id, actor):
    task = plan.graph.require(task_id)
    transition_task(task, TaskState.ASSIGNED, actor="AG-001")
    transition_task(task, TaskState.RUNNING, actor=actor)
    transition_task(task, TaskState.COMPLETED, actor=actor)


# -- views --------------------------------------------------------------------


def test_ready_in_flight_and_current_wave():
    plan = make_plan()
    coord = AgentCoordinationManager(plan)
    state = coord.consolidated_state(include_model_status=False)
    assert state.ready_tasks == ["TASK-0001"]
    assert state.in_flight == []
    assert state.current_wave == 0
    assert state.total_tasks == 4 and state.completed_tasks == 0
    assert state.done is False
    assert state.task_counts == {"PENDING": 4}

    complete(plan, "TASK-0001", "AG-001")
    transition_task(plan.graph.require("TASK-0002"), TaskState.ASSIGNED, actor="AG-001")
    state = coord.consolidated_state(include_model_status=False)
    assert state.current_wave == 1
    # ASSIGNED is assigned-but-not-started: still schedulable (ready), and
    # in flight; the module is deliberate that only RUNNING/REVIEW/BLOCKED
    # drop out of the ready set.
    assert state.ready_tasks == ["TASK-0002", "TASK-0003"]
    assert state.in_flight == ["TASK-0002"]


def test_agent_view_and_workload():
    plan = make_plan()
    coord = AgentCoordinationManager(plan)
    view = coord.agent_view("AG-008")
    assert view["assigned"] == 2
    assert set(view["tasks"]["PENDING"]) == {"TASK-0002", "TASK-0004"}
    complete(plan, "TASK-0002", "AG-008")
    state = coord.consolidated_state(include_model_status=False)
    assert state.agent_workload["AG-008"] == {"assigned": 2, "completed": 1, "in_flight": 0}
    assert state.agent_workload["AG-012"] == {"assigned": 1, "completed": 0, "in_flight": 0}


def test_blockers_include_states_and_pending_gates():
    plan = make_plan()
    blocked = plan.graph.require("TASK-0001")
    transition_task(blocked, TaskState.ASSIGNED, actor="AG-001")
    transition_task(blocked, TaskState.RUNNING, actor="AG-001")
    transition_task(blocked, TaskState.BLOCKED, actor="AG-001", reason="awaiting contract sign-off")
    coord = AgentCoordinationManager(plan)
    rows = coord.blockers()
    assert any(r["task_id"] == "TASK-0001" and "contract" in r["reason"] for r in rows)

    # a SUBMITTED delegation with never-evaluated gates is a GATES_PENDING blocker
    dm = DelegationManager(plan)
    rec = dm.create_delegation("TASK-0002", "child", "d", "AG-009", quality_gates=["QG-CODE"])
    dm.start(rec.delegation_id, "AG-009")
    dm.submit_for_review(rec.delegation_id)
    coord = AgentCoordinationManager(plan, list(dm.records.values()))
    rows = coord.blockers()
    gate_row = next(r for r in rows if r["state"] == "GATES_PENDING")
    assert gate_row["task_id"] == rec.task_id and "QG-CODE" in gate_row["reason"]

    state = coord.consolidated_state(include_model_status=False)
    assert state.blockers == rows
    assert state.delegations[0]["status"] == DelegationStatus.SUBMITTED.value


def test_done_when_everything_terminal():
    plan = make_plan()
    coord = AgentCoordinationManager(plan)
    complete(plan, "TASK-0001", "AG-001")
    complete(plan, "TASK-0002", "AG-008")
    complete(plan, "TASK-0003", "AG-012")
    complete(plan, "TASK-0004", "AG-008")
    state = coord.consolidated_state(include_model_status=False)
    assert state.done and state.completed_tasks == 4
    assert state.current_wave == len(state.waves)


def test_state_serialization_roundtrip():
    plan = make_plan()
    state = AgentCoordinationManager(plan).consolidated_state(include_model_status=False)
    data = state.to_dict()
    restored = CoordinationState.from_dict(data)
    assert restored.to_dict() == data
    assert restored.plan_id == plan.plan_id and restored.goal == "coordinate me"


# -- model fallback integration -------------------------------------------------


class StubManager:
    """Duck-typed stand-in for the runtime ModelFallbackManager."""

    def __init__(self, available=None):
        self.hierarchies = {
            "AG-001": ["opencode-go/model-a", "opencode-go/model-b"],
            "AG-008": ["opencode-go/model-a", "opencode-go/model-b"],
            "AG-012": ["opencode-go/model-b"],
        }
        self.available = available if available is not None else set(sum(self.hierarchies.values(), []))
        self.changes = []

    def get_hierarchy(self, agent_id):
        return list(self.hierarchies.get(agent_id, []))

    def get_primary(self, agent_id):
        return self.get_hierarchy(agent_id)[0]

    def select_model(self, agent_id):
        for model in self.get_hierarchy(agent_id):
            if model in self.available:
                return model
        return None

    def log_change(self, **kwargs):
        self.changes.append(kwargs)
        return kwargs


class ExplodingManager(StubManager):
    def select_model(self, agent_id):
        raise RuntimeError("runtime unreachable")


def test_model_status_degrades_without_manager():
    plan = make_plan()
    coord = AgentCoordinationManager(plan)
    state = coord.consolidated_state(include_model_status=True)
    assert state.model_status == {}  # no manager: empty, never crash


def test_model_status_probe_per_agent():
    plan = make_plan()
    coord = AgentCoordinationManager(plan, fallback_manager=StubManager())
    status = coord.model_status()
    assert set(status) == {"AG-001", "AG-008", "AG-012"}
    assert status["AG-008"] == {
        "selectable": True,
        "model": "opencode-go/model-a",
        "primary": "opencode-go/model-a",
        "on_fallback": False,
        "hierarchy_size": 2,
    }
    # primary unavailable -> reported on fallback, still selectable
    degraded = StubManager(available={"opencode-go/model-b"})
    status = AgentCoordinationManager(plan, fallback_manager=degraded).model_status()
    assert status["AG-008"]["selectable"] and status["AG-008"]["on_fallback"]
    # nothing selectable -> flagged, not fabricated
    empty = StubManager(available=set())
    status = AgentCoordinationManager(plan, fallback_manager=empty).model_status()
    assert status["AG-008"]["selectable"] is False and status["AG-008"]["model"] is None
    # a crashing probe must never take the status view down
    status = AgentCoordinationManager(plan, fallback_manager=ExplodingManager()).model_status()
    assert status == {}


def test_bind_and_error_routing_without_manager_load():
    stub = StubManager()
    result = bind_task_model(stub, "AG-008", "TASK-0002")
    assert result["bound"] and result["model"] == "opencode-go/model-a"
    assert result["fallback"] is False and result["status"] == "RUNNING"
    exhausted = StubManager(available=set())
    result = bind_task_model(exhausted, "AG-008", "TASK-0002")
    assert result["bound"] is False and result["status"] == "NEEDS_INTERVENTION"


def test_runtime_manager_bridge_over_repo_root():
    """The real runtime manager loads from the repository root."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".opencode" / "agents").mkdir(parents=True)
        (root / ".opencode" / "agents" / "ag-008-backend.md").write_text(
            "---\nmodel: opencode-go/beam-free\n---\nbody\n", encoding="utf-8"
        )
        manager = make_manager(root)
        assert manager is not None
        assert manager.get_primary("AG-008") == "opencode-go/beam-free"
        status = agent_model_status(manager, "AG-008")
        assert status["selectable"] and status["primary"] == "opencode-go/beam-free"
        # quota error on the only authorized model => wait for reset, no fallback
        decision = on_task_model_error(manager, "AG-008", "TASK-0002", "opencode-go/beam-free", "free usage limit reached")
        assert decision["action"] == "wait"
        # Under BEAM_FREE_ONLY there is no alternate model to recover from:
        # the primary is the only model, so recovery is a no-op when already on it.
        manager.mark_unavailable("opencode-go/beam-free", seconds=-1)
        assert manager.is_available("opencode-go/beam-free") is True
        recovered = recover_primary_model(manager, "AG-008", "TASK-0002", "opencode-go/beam-free")
        assert recovered["recovered"] is False


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
