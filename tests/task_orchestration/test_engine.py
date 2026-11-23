"""Task Orchestration engine tests: goal analysis, decomposition, validated
planning, guarded transitions, serialization, and workspace persistence."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.task_orchestration.engine import (  # noqa: E402
    CAPABILITY_AGENTS,
    PlanningError,
    TaskOrchestrationEngine,
    load_plan,
    next_plan_id,
    plan_file_path,
    save_plan,
)
from orchestration.task_orchestration.models import (  # noqa: E402
    AcceptanceCriterion,
    CycleError,
    GateVerdict,
    KNOWN_AGENTS,
    OrchestrationPlan,
    Priority,
    QualityGateResult,
    Task,
    TaskError,
    TaskGraph,
    TaskState,
    transition_task,
)

GOAL = "Build a backend orchestration engine with database persistence, tests, and docs"

STAMP = "2026-11-20T09:00:00Z"


def scratch_engine():
    """Engine over an empty scratch root: no skills registry -> advisory bindings empty."""
    tmp = Path(tempfile.mkdtemp())
    return TaskOrchestrationEngine(tmp), tmp


def build(engine, root, **kw):
    kwargs = dict(project_id="PROJECT-001", plan_id="PLAN-PROJECT-001-0001", created_at=STAMP)
    kwargs.update(kw)
    return engine.build_plan(GOAL, **kwargs)


# -- goal analysis ----------------------------------------------------------


def test_analyze_goal_baseline_and_order():
    engine, _ = scratch_engine()
    analysis = engine.analyze_goal("Analyze requirements and build a backend service")
    for baseline in ("coordination", "business-analysis", "architecture", "qa-testing", "code-review"):
        assert baseline in analysis.capabilities, baseline
    assert "backend" in analysis.capabilities
    # pipeline order is deterministic, not goal-word order
    assert analysis.capabilities.index("coordination") < analysis.capabilities.index("backend")
    assert len(set(analysis.capabilities)) == len(analysis.capabilities)


def test_analyze_goal_empty_refused():
    engine, _ = scratch_engine()
    try:
        engine.analyze_goal("   ")
    except PlanningError:
        pass
    else:
        raise AssertionError("empty goal accepted")


def test_analyze_goal_risk_hints():
    engine, _ = scratch_engine()
    analysis = engine.analyze_goal("Deploy the payment backend to production; rotate credentials")
    text = " ".join(analysis.risks)
    assert "production" in text.lower() or "LEVEL C" in text, analysis.risks
    assert any("credentials" in r for r in analysis.risks)


def test_select_agent_catalog():
    engine, _ = scratch_engine()
    assert engine.select_agent("backend") in KNOWN_AGENTS
    assert CAPABILITY_AGENTS["coordination"] == "AG-001"
    try:
        engine.select_agent("telepathy")
    except PlanningError:
        pass
    else:
        raise AssertionError("unknown capability accepted")


# -- plan construction ------------------------------------------------------


def test_build_plan_shape_and_invariants():
    engine, root = scratch_engine()
    plan = build(engine, root)
    issues = plan.validate()
    assert not issues, issues
    ids = set(plan.graph.tasks)
    assert ids == {f"TASK-{i:04d}" for i in range(1, len(ids) + 1)}
    for task in plan.graph.tasks.values():
        assert task.assigned_agent in KNOWN_AGENTS
        assert task.acceptance_criteria, task.task_id
        assert task.created_at == STAMP
    # skills registry absent in scratch root: advisory bindings stay empty
    assert all(rows == [] for rows in plan.skills_by_task.values())
    # waves cover exactly the task set
    flat = [t for wave in plan.graph.waves() for t in wave]
    assert sorted(flat) == sorted(ids)


def test_build_plan_bad_plan_id_refused():
    engine, root = scratch_engine()
    try:
        build(engine, root, plan_id="PLAN-7")
    except PlanningError as exc:
        assert "plan_id" in str(exc)
    else:
        raise AssertionError("malformed plan_id accepted")


def test_build_plan_deterministic():
    engine, root = scratch_engine()
    first = build(engine, root).to_dict()
    second = build(engine, root).to_dict()
    assert first == second


def test_decompose_dependencies_reference_known_keys():
    engine, _ = scratch_engine()
    analysis = engine.analyze_goal(GOAL)
    specs = engine.decompose(analysis)
    keys = {s.key for s in specs}
    for spec in specs:
        for dep in spec.depends_on:
            assert dep in keys, (spec.key, dep)


# -- graph validation ---------------------------------------------------------


def test_graph_cycle_and_edge_guards():
    graph = TaskGraph()
    a = Task("TASK-0001", "A", "task a", assigned_agent="AG-001")
    b = Task("TASK-0002", "B", "task b", assigned_agent="AG-008")
    graph.add_task(a)
    graph.add_task(b, depends_on=["TASK-0001"])
    try:
        graph.add_dependency("TASK-0001", "TASK-0002")
    except CycleError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("cycle introduced")
    assert graph.dependencies["TASK-0001"] == set()  # fail-closed: untouched
    try:
        graph.add_dependency("TASK-0001", "TASK-0001")
    except TaskError:
        pass
    else:
        raise AssertionError("self-dependency accepted")
    try:
        graph.add_task(Task("TASK-0003", "C", "c", assigned_agent="AG-008"), depends_on=["TASK-9999"])
    except TaskError:
        pass
    else:
        raise AssertionError("dangling dependency accepted")


def test_graph_task_validation():
    graph = TaskGraph()
    try:
        graph.add_task(Task("TASK-0001", "X", "d", assigned_agent="AG-404"))
    except TaskError as exc:
        assert "catalog" in str(exc)
    else:
        raise AssertionError("non-catalog agent accepted")
    try:
        graph.add_task(Task("TASK-001", "X", "d", assigned_agent="AG-008"))
    except TaskError:
        pass
    else:
        raise AssertionError("malformed task_id accepted")
    graph.add_task(Task("TASK-0001", "X", "d", assigned_agent="AG-008"))
    try:
        graph.add_task(Task("TASK-0001", "dup", "d", assigned_agent="AG-008"))
    except TaskError:
        pass
    else:
        raise AssertionError("duplicate task_id accepted")


def test_graph_remove_refuses_with_dependents():
    graph = TaskGraph()
    graph.add_task(Task("TASK-0001", "A", "a", assigned_agent="AG-001"))
    graph.add_task(Task("TASK-0002", "B", "b", assigned_agent="AG-008"), depends_on=["TASK-0001"])
    try:
        graph.remove_task("TASK-0001")
    except TaskError as exc:
        assert "dependency of" in str(exc)
    else:
        raise AssertionError("removed a depended-upon task")
    graph.remove_task("TASK-0002")
    assert set(graph.tasks) == {"TASK-0001"}


# -- guarded transitions (Task Contract rules 1-4) ----------------------------


def _runnable_task():
    task = Task(
        "TASK-0001",
        "Worker",
        "guarded transition subject",
        status=TaskState.PENDING,
        assigned_agent="AG-008",
        acceptance_criteria=[AcceptanceCriterion("AC-1", "criterion")],
        quality_gates=[QualityGateResult("QG-CODE", GateVerdict.PENDING)],
    )
    transition_task(task, TaskState.ASSIGNED, actor="AG-001")
    transition_task(task, TaskState.RUNNING, actor="AG-008")
    return task


def test_transition_illegal_arc_refused():
    task = _runnable_task()
    task.status = TaskState.PENDING  # bypass history, keep semantics simple
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-001")
    except TaskError as exc:
        assert "illegal" in str(exc)
    else:
        raise AssertionError("PENDING->COMPLETED allowed")


def test_transition_completion_rules():
    task = _runnable_task()
    # rule 1: unsatisfied criterion
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-013")
    except TaskError as exc:
        assert "rule 1" in str(exc)
    else:
        raise AssertionError("completed with unsatisfied criteria")
    # rule 2: gate still PENDING (stricter than contract minimum)
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-013", criteria_results={"AC-1": True})
    except TaskError as exc:
        assert "rule 2" in str(exc)
    else:
        raise AssertionError("completed with PENDING gate")
    entry = transition_task(
        task,
        TaskState.COMPLETED,
        actor="AG-013",
        criteria_results={"AC-1": True},
        gate_results={"QG-CODE": "PASS"},
    )
    assert task.status is TaskState.COMPLETED
    assert entry.to_state == "COMPLETED"
    assert task.history[-1].actor == "AG-013"


def test_transition_review_requires_independent_reviewer():
    task = Task(
        "TASK-0002",
        "Submitted",
        "review arc subject",
        status=TaskState.PENDING,
        assigned_agent="AG-008",
        acceptance_criteria=[AcceptanceCriterion("AC-1", "criterion")],
    )
    transition_task(task, TaskState.ASSIGNED, actor="AG-001")
    transition_task(task, TaskState.RUNNING, actor="AG-008")
    transition_task(task, TaskState.REVIEW_REQUIRED, actor="AG-008")
    assert task.submitted_by == "AG-008"
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-008", criteria_results={"AC-1": True})
    except TaskError as exc:
        assert "rule 3" in str(exc)
    else:
        raise AssertionError("self-review completion allowed")
    transition_task(task, TaskState.COMPLETED, actor="AG-013", criteria_results={"AC-1": True})
    assert task.reviewed_by == "AG-013"


def test_transition_cancel_requires_reason_and_bad_actor_refused():
    task = _runnable_task()
    try:
        transition_task(task, TaskState.CANCELLED, actor="AG-001")
    except TaskError as exc:
        assert "rule 4" in str(exc)
    else:
        raise AssertionError("cancelled without reason")
    try:
        transition_task(task, TaskState.CANCELLED, actor="worker-9", reason="dropped")
    except TaskError as exc:
        assert "actor" in str(exc)
    else:
        raise AssertionError("non-agent actor accepted")
    transition_task(task, TaskState.CANCELLED, actor="AG-001", reason="scope dropped")
    assert task.status_note == "scope dropped"


def test_transition_unknown_ids_refused():
    task = _runnable_task()
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-013", criteria_results={"AC-404": True})
    except TaskError:
        pass
    else:
        raise AssertionError("unknown criterion id accepted")
    try:
        transition_task(task, TaskState.COMPLETED, actor="AG-013", gate_results={"QG-GHOST": "PASS"})
    except TaskError:
        pass
    else:
        raise AssertionError("unknown gate id accepted")


# -- serialization / persistence ------------------------------------------------


def test_plan_roundtrip_and_reject_bad_dict():
    engine, root = scratch_engine()
    plan = build(engine, root)
    data = json.loads(json.dumps(plan.to_dict()))
    restored = OrchestrationPlan.from_dict(data)
    assert restored.to_dict() == data
    broken = dict(data)
    broken["project_id"] = "P-1"
    try:
        OrchestrationPlan.from_dict(broken)
    except TaskError:
        pass
    else:
        raise AssertionError("invalid plan dict accepted")


def test_save_load_and_next_plan_id():
    engine, root = scratch_engine()
    plan = build(engine, root)
    saved = save_plan(plan, root)
    assert saved == plan_file_path(root, "PROJECT-001")
    loaded = load_plan(root, "PROJECT-001")
    assert loaded.to_dict() == plan.to_dict()
    assert next_plan_id(root, "PROJECT-001") == "PLAN-PROJECT-001-0002"
    try:
        load_plan(root, "PROJECT-777")
    except PlanningError:
        pass
    else:
        raise AssertionError("missing plan loaded")


def test_save_archive_append_only_and_corrupt_refused():
    engine, root = scratch_engine()
    plan = build(engine, root)
    save_plan(plan, root, archive=True)
    try:
        save_plan(plan, root, archive=True)
    except PlanningError as exc:
        assert "append-only" in str(exc)
    else:
        raise AssertionError("plan archive overwritten")
    plan_file_path(root, "PROJECT-001").write_text("{not json", encoding="utf-8")
    try:
        load_plan(root, "PROJECT-001")
    except PlanningError as exc:
        assert "corrupt" in str(exc)
    else:
        raise AssertionError("corrupt plan loaded")


# -- CLI smoke (package entry point) ----------------------------------------------


def test_cli_plan_build_groups_status_delegate():
    engine, root = scratch_engine()
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    base = [sys.executable, "-m", "orchestration.task_orchestration.cli", "--root", str(root)]

    def run(*args):
        proc = subprocess.run(base + list(args), capture_output=True, text=True, env=env, cwd=str(ROOT))
        assert proc.returncode == 0, (args, proc.returncode, proc.stderr[-400:])
        return json.loads(proc.stdout)

    out = run("plan-build", "--project", "PROJECT-001", "--goal", GOAL, "--plan-id", "PLAN-PROJECT-001-0001", "--save")
    assert out["ok"] and out["plan_id"] == "PLAN-PROJECT-001-0001"
    assert plan_file_path(root, "PROJECT-001").is_file()

    groups = run("groups", "--project", "PROJECT-001")
    assert groups["parallel_groups"][0] == ["TASK-0001"]
    assert groups["ready_tasks"] == ["TASK-0001"]

    # assign + start TASK-0001 through the CLI, then verify readiness moved on
    run("task-set", "--project", "PROJECT-001", "--task", "TASK-0001", "--state", "ASSIGNED", "--actor", "AG-001")
    run("task-set", "--project", "PROJECT-001", "--task", "TASK-0001", "--state", "RUNNING", "--actor", "AG-001")
    groups = run("groups", "--project", "PROJECT-001")
    assert "TASK-0001" not in groups["ready_tasks"]

    delegated = run(
        "delegate", "--project", "PROJECT-001", "--parent", "TASK-0002",
        "--delegatee", "AG-008", "--title", "CLI child", "--description", "made by cli",
    )
    assert delegated["delegation"]["delegation_id"] == "DELEG-0001"
    child = delegated["delegation"]["task_id"]

    refused = subprocess.run(
        base + ["task-set", "--project", "PROJECT-001", "--task", child,
                "--state", "COMPLETED", "--actor", "AG-013"],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    assert refused.returncode == 3, refused.stdout  # ASSIGNED->COMPLETED is an illegal arc
    # legal move, then coordination status must show it in flight
    run("task-set", "--project", "PROJECT-001", "--task", child, "--state", "RUNNING", "--actor", "AG-008")
    status = run("status", "--project", "PROJECT-001")
    assert status["state"]["total_tasks"] == len(load_plan(root, "PROJECT-001").graph.tasks)
    assert child in status["state"]["in_flight"]


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
