"""Parallel/sequential execution grouping tests: waves semantics,
topological consistency, fan-out/fan-in pipelines, readiness propagation,
and cycle protection."""

import sys
import tempfile
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.task_orchestration.engine import TaskOrchestrationEngine  # noqa: E402
from orchestration.task_orchestration.models import (  # noqa: E402
    AcceptanceCriterion,
    CycleError,
    GoalAnalysis,
    OrchestrationPlan,
    Task,
    TaskGraph,
    TaskState,
    transition_task,
)

STAMP = "2026-11-20T10:00:00Z"


def task(task_id, agent="AG-008", ready=True):
    return Task(
        task_id=task_id,
        title=f"task {task_id}",
        description="parallel fixture task",
        assigned_agent=agent,
        acceptance_criteria=[AcceptanceCriterion("AC-1", "done", satisfied=ready)],
    )


def complete(graph, task_id, actor):
    node = graph.require(task_id)
    transition_task(node, TaskState.ASSIGNED, actor="AG-001")
    transition_task(node, TaskState.RUNNING, actor=actor)
    transition_task(node, TaskState.COMPLETED, actor=actor)


# -- wave structure -------------------------------------------------------------


def test_diamond_waves_and_internal_independence():
    graph = TaskGraph()
    graph.add_task(task("TASK-0001"))
    graph.add_task(task("TASK-0002"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0003"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0004"), depends_on=["TASK-0002", "TASK-0003"])
    waves = graph.waves()
    assert waves == [["TASK-0001"], ["TASK-0002", "TASK-0003"], ["TASK-0004"]]
    # tasks inside a wave are mutually independent
    for wave in waves:
        for a, b in combinations(wave, 2):
            assert b not in graph.dependencies[a] and a not in graph.dependencies[b]
    # every dependency lands in a strictly earlier wave
    index = {t: i for i, wave in enumerate(waves) for t in wave}
    for t, deps in graph.dependencies.items():
        for d in deps:
            assert index[d] < index[t], (d, t)


def test_topological_order_respects_every_edge():
    graph = TaskGraph()
    graph.add_task(task("TASK-0001"))
    graph.add_task(task("TASK-0002"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0003"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0004"), depends_on=["TASK-0002", "TASK-0003"])
    order = graph.topological_order()
    assert order == ["TASK-0001", "TASK-0002", "TASK-0003", "TASK-0004"]
    pos = {t: i for i, t in enumerate(order)}
    for t, deps in graph.dependencies.items():
        for d in deps:
            assert pos[d] < pos[t]
    # waves are prefix-consistent with the order
    seen = []
    for wave in graph.waves():
        seen = sorted(seen + wave)
        assert order[: len(seen)] == seen


def test_disconnected_components_stay_parallel():
    graph = TaskGraph()
    graph.add_task(task("TASK-0001"))
    graph.add_task(task("TASK-0002"))  # independent chain
    graph.add_task(task("TASK-0003"), depends_on=["TASK-0002"])
    waves = graph.waves()
    assert waves[0] == ["TASK-0001", "TASK-0002"]
    assert waves[1] == ["TASK-0003"]


# -- readiness propagation -------------------------------------------------------


def test_wave_completion_unlocks_next_wave():
    graph = TaskGraph()
    graph.add_task(task("TASK-0001"))
    graph.add_task(task("TASK-0002"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0003"), depends_on=["TASK-0001"])
    graph.add_task(task("TASK-0004"), depends_on=["TASK-0002", "TASK-0003"])
    assert graph.ready_tasks() == ["TASK-0001"]
    complete(graph, "TASK-0001", "AG-008")
    assert graph.ready_tasks() == ["TASK-0002", "TASK-0003"]
    assert graph.missing_dependencies("TASK-0004") == ["TASK-0002", "TASK-0003"]
    # fan-in: one completed branch still blocks the join
    complete(graph, "TASK-0002", "AG-008")
    assert "TASK-0004" not in graph.ready_tasks()
    assert graph.missing_dependencies("TASK-0004") == ["TASK-0003"]
    complete(graph, "TASK-0003", "AG-008")
    assert graph.ready_tasks() == ["TASK-0004"]
    assert not graph.missing_dependencies("TASK-0004")


def test_in_flight_states_leave_ready_set():
    graph = TaskGraph()
    graph.add_task(task("TASK-0001"))
    node = graph.require("TASK-0001")
    transition_task(node, TaskState.ASSIGNED, actor="AG-001")
    assert graph.is_ready("TASK-0001")  # assigned, not started: still schedulable
    transition_task(node, TaskState.RUNNING, actor="AG-008")
    assert not graph.is_ready("TASK-0001")
    transition_task(node, TaskState.BLOCKED, actor="AG-008", reason="waiting")
    assert not graph.is_ready("TASK-0001")
    transition_task(node, TaskState.RUNNING, actor="AG-008")
    transition_task(node, TaskState.FAILED, actor="AG-008", reason="boom")
    # FAILED is not terminal and not an in-flight state: the contract's
    # FAILED -> PENDING retry arc keeps it schedulable in the ready set.
    assert graph.is_ready("TASK-0001")


# -- engine-level parallelism ------------------------------------------------------


def build(goal, root, plan_id="PLAN-PROJECT-001-0001"):
    engine = TaskOrchestrationEngine(root)
    return engine.build_plan(goal, project_id="PROJECT-001", plan_id=plan_id, created_at=STAMP)


def test_engine_fanout_fanin_pipeline():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        plan = build(
            "Implement backend, frontend, and database modules, integrate them, "
            "add a pipeline, and write documentation",
            root,
        )
        waves = plan.graph.waves()
        flat = [t for wave in waves for t in wave]
        assert sorted(flat) == sorted(plan.graph.tasks)
        # implementation fan-out: at least one wave with 3+ parallel members
        assert max(len(wave) for wave in waves) >= 3
        # integration joins the implemented slices (fan-in)
        integration = [
            t for t in plan.graph.tasks
            if plan.graph.tasks[t].assigned_agent == "AG-011"
        ]
        assert integration
        for join in integration:
            deps = plan.graph.dependencies[join]
            assert len(deps) >= 2, deps
            join_wave = next(i for i, w in enumerate(waves) if join in w)
            for dep in deps:
                dep_wave = next(i for i, w in enumerate(waves) if dep in w)
                assert dep_wave < join_wave
        # no edge inside any wave
        from itertools import combinations as _comb

        for wave in waves:
            for a, b in _comb(wave, 2):
                assert b not in plan.graph.dependencies[a]


def test_engine_grouping_queries_deterministic():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        first = build("Build a backend service engine with frontend client and docs", root)
        second = build("Build a backend service engine with frontend client and docs", root, plan_id="PLAN-PROJECT-001-0002")
        assert TaskOrchestrationEngine.parallel_groups(first) == TaskOrchestrationEngine.parallel_groups(second)
        assert TaskOrchestrationEngine.sequential_order(first) == TaskOrchestrationEngine.sequential_order(second)
        order = TaskOrchestrationEngine.sequential_order(first)
        groups = TaskOrchestrationEngine.parallel_groups(first)
        assert sum(len(g) for g in groups) == len(order)


def test_waves_refuse_on_cycle_and_carry_over_after_fix():
    """A corrupted graph never yields a partial parallel plan (fail-closed)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        plan = build("Backend orchestration engine", root)
        graph = plan.graph
        before = graph.waves()
        a, b = graph.topological_order()[0], graph.topological_order()[1]
        try:
            graph.add_dependency(a, b)
        except CycleError:
            pass
        else:
            raise AssertionError("cycle accepted into the plan graph")
        # untouched: waves still computable and unchanged
        assert graph.find_cycle() is None
        assert graph.waves() == before
        assert OrchestrationPlan.from_dict(plan.to_dict()).plan_id == plan.plan_id


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
