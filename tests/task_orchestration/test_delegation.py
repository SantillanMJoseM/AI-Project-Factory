"""Delegation manager tests: create, track, fail-closed independent
verification (Task Contract rules 1-3), rework, revocation, persistence."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.task_orchestration.delegation import (  # noqa: E402
    DelegationError,
    DelegationManager,
    TRACKABLE_STATES,
)
from orchestration.task_orchestration.models import (  # noqa: E402
    AcceptanceCriterion,
    DelegationStatus,
    GoalAnalysis,
    OrchestrationPlan,
    Task,
    TaskError,
    TaskGraph,
    TaskState,
    transition_task,
)


def make_plan(n=3):
    graph = TaskGraph()
    agents = ["AG-001", "AG-008", "AG-012", "AG-002", "AG-013"]
    for i in range(n):
        task = Task(
            task_id=f"TASK-{i + 1:04d}",
            title=f"Step {i + 1}",
            description=f"manual plan task {i + 1}",
            assigned_agent=agents[i % len(agents)],
            acceptance_criteria=[AcceptanceCriterion("AC-1", "objective met")],
        )
        graph.add_task(task, depends_on=[f"TASK-{i:04d}"] if i else [])
    return OrchestrationPlan(
        plan_id="PLAN-PROJECT-001-0001",
        project_id="PROJECT-001",
        analysis=GoalAnalysis(goal="manual delegation plan"),
        graph=graph,
    )


def manager(plan=None, delegator="AG-001"):
    return DelegationManager(plan or make_plan(), delegator_agent=delegator)


# -- creation ------------------------------------------------------------------


def test_create_delegation_child_task_and_record():
    plan = make_plan()
    dm = manager(plan)
    record = dm.create_delegation("TASK-0001", "Backend slice", "Implement module", "AG-008")
    assert record.delegation_id == "DELEG-0001"
    assert record.status is DelegationStatus.DELEGATED
    assert record.plan_id == plan.plan_id and record.parent_task_id == "TASK-0001"
    child = plan.graph.require(record.task_id)
    assert child.status is TaskState.ASSIGNED
    assert child.assigned_agent == "AG-008"
    assert "TASK-0001" in plan.graph.dependencies[child.task_id]
    assert child.acceptance_criteria, "defaults required for meaningful verification"
    assert [h.to_state for h in record.history] == ["DELEGATED"]
    # ids continue monotonically, no collision
    second = dm.create_delegation("TASK-0001", "Second", "d", "AG-009")
    assert second.delegation_id == "DELEG-0002"
    assert second.task_id != record.task_id


def test_create_delegation_refusals():
    plan = make_plan()
    dm = manager(plan)
    try:
        dm.create_delegation("TASK-0001", "T", "d", "AG-404")
    except DelegationError as exc:
        assert "catalog" in str(exc)
    else:
        raise AssertionError("non-catalog delegatee accepted")
    try:
        dm.create_delegation("TASK-0001", "  ", "d", "AG-008")
    except DelegationError:
        pass
    else:
        raise AssertionError("blank title accepted")
    try:
        dm.create_delegation("TASK-7777", "T", "d", "AG-008")
    except TaskError:
        pass
    else:
        raise AssertionError("unknown parent accepted")
    # terminal parent refuses
    parent = plan.graph.require("TASK-0001")
    transition_task(parent, TaskState.ASSIGNED, actor="AG-001")
    transition_task(parent, TaskState.RUNNING, actor="AG-001")
    transition_task(parent, TaskState.CANCELLED, actor="AG-001", reason="dropped")
    try:
        dm.create_delegation("TASK-0001", "T", "d", "AG-008")
    except DelegationError as exc:
        assert "terminal" in str(exc)
    else:
        raise AssertionError("delegation from terminal parent accepted")


def test_manager_rejects_bad_delegator():
    try:
        DelegationManager(make_plan(), delegator_agent="coordinator")
    except DelegationError:
        pass
    else:
        raise AssertionError("non-agent delegator accepted")


# -- tracking -------------------------------------------------------------------


def test_track_lifecycle_and_completed_guard():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008")
    dm.start(record.delegation_id, "AG-008")
    assert record.status is DelegationStatus.ACTIVE
    dm.block(record.delegation_id, "waiting on contract")
    task = dm.plan.graph.require(record.task_id)
    assert task.status is TaskState.BLOCKED and record.status is DelegationStatus.ACTIVE
    dm.unblock(record.delegation_id)
    assert task.status is TaskState.RUNNING
    dm.submit_for_review(record.delegation_id)
    assert task.status is TaskState.REVIEW_REQUIRED
    assert record.status is DelegationStatus.SUBMITTED
    # COMPLETED is refused through tracking: verification owns it
    try:
        dm.track_status(record.delegation_id, TaskState.COMPLETED, "AG-013")
    except DelegationError as exc:
        assert "verify_completion" in str(exc)
    else:
        raise AssertionError("completion asserted without verification")
    try:
        dm.track_status(record.delegation_id, TaskState.ASSIGNED, "AG-013")
    except DelegationError as exc:
        assert "not trackable" in str(exc)
    else:
        raise AssertionError("untrackable state accepted")
    assert TaskState.ASSIGNED not in TRACKABLE_STATES


# -- verification -----------------------------------------------------------------


def test_verify_happy_path_independent():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008", quality_gates=["QG-CODE"])
    dm.start(record.delegation_id, "AG-008")
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(
        record.delegation_id,
        "AG-013",
        criteria_results={"AC-1": True, "AC-2": True},
        gate_results={"QG-CODE": "PASS"},
    )
    assert report.ok, report.reasons
    task = dm.plan.graph.require(record.task_id)
    assert task.status is TaskState.COMPLETED
    assert record.status is DelegationStatus.COMPLETED
    assert task.reviewed_by == "AG-013"
    assert task.history[-1].to_state == "COMPLETED"
    assert record.verification["ok"] is True


def test_verify_self_review_and_delegator_refused():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008")
    dm.start(record.delegation_id, "AG-008")
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(record.delegation_id, "AG-008", criteria_results={"AC-1": True, "AC-2": True})
    assert not report.ok and any("rule 3" in r for r in report.reasons)
    assert dm.plan.graph.require(record.task_id).status is TaskState.REJECTED
    assert record.status is DelegationStatus.REJECTED
    # rework arc, then delegator-as-verifier also refused
    dm.retry_rejected(record.delegation_id)
    assert dm.plan.graph.require(record.task_id).status is TaskState.RUNNING
    assert record.status is DelegationStatus.ACTIVE
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(record.delegation_id, "AG-001", criteria_results={"AC-1": True, "AC-2": True})
    assert not report.ok and any("delegator" in r for r in report.reasons)


def test_verify_unsatisfied_criteria_and_failing_gates():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008", quality_gates=["QG-TEST"])
    dm.start(record.delegation_id, "AG-008")
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(record.delegation_id, "AG-013", criteria_results={"AC-1": False, "AC-2": True})
    assert not report.ok and any("rule 1" in r for r in report.reasons)
    dm.retry_rejected(record.delegation_id)
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(
        record.delegation_id,
        "AG-013",
        criteria_results={"AC-1": True, "AC-2": True},
        gate_results={"QG-TEST": "FAIL"},
    )
    assert not report.ok and any("rule 2" in r for r in report.reasons)
    dm.retry_rejected(record.delegation_id)
    dm.submit_for_review(record.delegation_id)
    report = dm.verify_completion(
        record.delegation_id,
        "AG-013",
        criteria_results={"AC-1": True, "AC-2": True},
        gate_results={"QG-TEST": "NOT_APPLICABLE"},
    )
    assert report.ok, report.reasons


def test_verify_preconditions():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008")
    try:
        dm.verify_completion(record.delegation_id, "AG-013")
    except DelegationError as exc:
        assert "SUBMITTED" in str(exc)
    else:
        raise AssertionError("verified an unsubmitted delegation")
    dm.start(record.delegation_id, "AG-008")
    dm.submit_for_review(record.delegation_id)
    try:
        dm.verify_completion(record.delegation_id, "AG-013", criteria_results={"AC-99": True})
    except DelegationError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("unknown criterion id accepted")
    try:
        dm.verify_completion(record.delegation_id, "not-an-agent")
    except DelegationError:
        pass
    else:
        raise AssertionError("non-agent verifier accepted")
    # the bad-result attempts must not have mutated the child
    assert dm.plan.graph.require(record.task_id).status is TaskState.REVIEW_REQUIRED


# -- revocation --------------------------------------------------------------------


def test_revoke_requires_reason_and_open_child():
    dm = manager()
    record = dm.create_delegation("TASK-0001", "T", "d", "AG-008")
    try:
        dm.revoke(record.delegation_id)
    except TaskError as exc:
        assert "reason" in str(exc)
    else:
        raise AssertionError("revoked without reason")
    dm.revoke(record.delegation_id, reason="superseded by plan change")
    assert record.status is DelegationStatus.REVOKED
    assert dm.plan.graph.require(record.task_id).status is TaskState.CANCELLED
    try:
        dm.revoke(record.delegation_id, reason="again")
    except DelegationError as exc:
        assert "terminal" in str(exc)
    else:
        raise AssertionError("revoked a terminal child")


def test_active_delegations_lists_open_only():
    dm = manager()
    a = dm.create_delegation("TASK-0001", "A", "d", "AG-008")
    b = dm.create_delegation("TASK-0001", "B", "d", "AG-009")
    dm.revoke(b.delegation_id, reason="merged")
    assert [r.delegation_id for r in dm.active_delegations()] == [a.delegation_id]


# -- persistence ----------------------------------------------------------------------


def test_save_load_roundtrip_and_counter():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        plan = make_plan()
        dm = manager(plan)
        record = dm.create_delegation("TASK-0001", "T", "d", "AG-008")
        dm.start(record.delegation_id, "AG-008")
        dm.save(root)
        from orchestration.task_orchestration.engine import save_plan

        save_plan(plan, root)

        loaded_plan = OrchestrationPlan.from_dict(plan.to_dict())
        dm2 = DelegationManager.load(loaded_plan, root)
        assert set(dm2.records) == {record.delegation_id}
        restored = dm2.records[record.delegation_id]
        assert restored.status is DelegationStatus.ACTIVE
        assert restored.task_id == record.task_id
        assert loaded_plan.delegation_counter == 1
        # ids never rewind: next delegation continues the sequence
        again = dm2.create_delegation("TASK-0001", "More", "d", "AG-010")
        assert again.delegation_id == "DELEG-0002"
        # child task id continues the reloaded graph sequence, no collision
        assert again.task_id not in {t for t in loaded_plan.graph.tasks if t != again.task_id}

        # foreign plan file refused
        dm2.save(root)
        other = make_plan()
        other.plan_id = "PLAN-PROJECT-002-0001"
        other.project_id = "PROJECT-002"
        try:
            DelegationManager(other).load_dict(dm2.to_dict())
        except DelegationError as exc:
            assert "different plan" in str(exc)
        else:
            raise AssertionError("foreign delegation file loaded")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
