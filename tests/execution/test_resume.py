"""Resume Engine tests: fail-closed eligibility, forward-only transaction, duplicate prevention."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.execution.context import assemble_context  # noqa: E402
from orchestration.execution.ledger import Ledger, ledger_path, verify_ledger  # noqa: E402
from orchestration.execution.models import ResumeVerdict, T0_BOOTSTRAP_FILES  # noqa: E402
from orchestration.execution.resume import (  # noqa: E402
    DuplicateResumeError,
    ResumeBlocked,
    ResumeNeedsIntervention,
    evaluate_resume,
    load_resume_index,
    start_resume,
)
from orchestration.execution.snapshot import create_snapshot  # noqa: E402


def make_repo(td):
    root = Path(td)
    for name in T0_BOOTSTRAP_FILES:
        (root / name).write_text(name + "\n", encoding="utf-8")
    (root / "contracts").mkdir()
    (root / "contracts" / "api.md").write_text("contract\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("v1\n", encoding="utf-8")
    return root


def checkpoint(root, execution_id="EXEC-0001", task_id="TASK-0001", seq_stamp=None, **snap_kw):
    """Open ledger -> context -> ops -> snapshot; returns (ledger, snapshot_path).

    The ledger for a resumed successor already exists (opened by the resume
    transaction); checkpoints then continue its chain (append-only).
    """
    path = ledger_path(root, "PROJECT-001", execution_id)
    if path.exists():
        ledger = Ledger.open(path, execution_id)
    else:
        ledger = Ledger.create(path, execution_id, actor_agent="AG-008")
    manifest = assemble_context(
        root,
        project_id="PROJECT-001",
        execution_id=execution_id,
        task_refs=["contracts/api.md"],
        working_refs=["src/app.py"],
        stamp=seq_stamp or "2026-11-19T10:00:00Z",
    )
    ledger.append(
        "CONTEXT_ASSEMBLED", "AG-008", {"manifest": manifest.manifest_hash},
        timestamp="2026-11-19T10:00:10Z",
    )
    ledger.append(
        "FILE_CHANGED", "AG-008", {"path": "src/app.py"},
        effect="applied-irreversible", timestamp="2026-11-19T10:00:20Z",
    )
    kwargs = dict(
        project_id="PROJECT-001",
        execution_id=execution_id,
        task_id=task_id,
        agent_id="AG-008",
        reason="degraded-model",
        files=["src/app.py"],
        context_manifest_hash=manifest.manifest_hash,
        stamp="2026-11-19T10:00:30Z",
    )
    kwargs.update(snap_kw)
    snapshot = create_snapshot(root, ledger=ledger, **kwargs)
    path = root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")
    return ledger, path


def test_happy_path_ready():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(root)
        decision = evaluate_resume(root, snap_path, check_git=False)
        assert decision.verdict is ResumeVerdict.READY, decision.reasons
        # The applied-irreversible FILE_CHANGED (seq 3) must be journalled
        # as never-re-apply material (§4.3 clause 4).
        assert 3 in decision.never_reapply


def test_ineligible_or_unapproved_snapshot_blocked():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _l1, snap1 = checkpoint(root, resume_eligible=False)
        d1 = evaluate_resume(root, snap1, check_git=False)
        assert d1.verdict is ResumeVerdict.BLOCKED
        assert any("not resume-eligible" in r for r in d1.reasons)

        _l2, snap2 = checkpoint(root, execution_id="EXEC-0002", requires_approval=True,
                                eligibility_notes="LEVEL C repair")
        d2 = evaluate_resume(root, snap2, check_git=False)
        assert d2.verdict is ResumeVerdict.BLOCKED
        assert any("approval" in r for r in d2.reasons)
        try:
            start_resume(root, snap2, new_execution_id="EXEC-0009", actor_agent="AG-008",
                         check_git=False)
        except ResumeBlocked as exc:
            assert exc.decision.verdict is ResumeVerdict.BLOCKED
        else:
            raise AssertionError("approval-required resume auto-executed")


def test_tampered_snapshot_and_broken_chain_blocked():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        ledger, snap_path = checkpoint(root)
        data = snap_path.read_text(encoding="utf-8")
        snap_path.write_text(data.replace('"degraded-model"', '"pre-operation"'), encoding="utf-8")
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("integrity" in r for r in d.reasons)

        # fresh case: break the ledger after the snapshot certified its head
        ledger2, snap2 = checkpoint(root, execution_id="EXEC-0002")
        lines = ledger2.path.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"EXECUTION_OPENED"', '"STATE_CHANGED"')
        ledger2.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        d2 = evaluate_resume(root, snap2, check_git=False)
        assert d2.verdict is ResumeVerdict.BLOCKED
        assert any("ledger chain" in r for r in d2.reasons)


def test_divergence_policy():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(root)
        # additive divergence (new untracked files) passes (§4.3 clause 3)
        (root / "src" / "build_output.log").write_text("noise\n", encoding="utf-8")
        assert evaluate_resume(root, snap_path, check_git=False).verdict is ResumeVerdict.READY
        # divergence of tracked, non-governed files blocks
        (root / "src" / "app.py").write_text("v2 silent edit\n", encoding="utf-8")
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("divergence" in r for r in d.reasons)
        assert d.divergence_modified == ["src/app.py"]

    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(root, files=["src/app.py", "contracts/api.md"])
        # governed-file divergence always blocks, explicitly
        (root / "contracts" / "api.md").write_text("contract MUTATED\n", encoding="utf-8")
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("governed-file divergence" in r for r in d.reasons)
        assert any("context manifest stale on governed files" in r for r in d.reasons)


def test_missing_context_manifest_blocked():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(root, context_manifest_hash=None)
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("context_manifest_hash" in r for r in d.reasons)


def test_git_anchor_check():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(
            root,
            before_commit="0000000000000000000000000000000000000000",
            after_commit="1111111111111111111111111111111111111111",
        )
        d = evaluate_resume(root, snap_path, check_git=True)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert sum(1 for r in d.reasons if "git anchor unverifiable" in r) == 2


def test_resume_transaction_is_forward_only():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        ledger, snap_path = checkpoint(root)
        source_records_before = ledger.path.read_text(encoding="utf-8")
        result = start_resume(
            root, snap_path, new_execution_id="EXEC-0002", actor_agent="AG-008",
            failure_signature="timeout:AG-008",
            model_binding={"provider": "opencode-go", "model": "m2", "fallback_status": "FALLBACK_ACTIVE"},
            check_git=False,
        )
        assert result["ok"] and result["to_execution"] == "EXEC-0002"
        # source ledger: only appended (dead execution journalled, never rewritten)
        source_now = ledger.path.read_text(encoding="utf-8")
        assert source_now.startswith(source_records_before)
        tail = source_now[len(source_records_before):]
        assert "STATE_CHANGED" in tail and "RESUME_REQUESTED" in tail
        successor_file = ledger_path(root, "PROJECT-001", "EXEC-0002")
        assert verify_ledger(successor_file).ok
        from orchestration.execution.ledger import read_records

        events = [e.event_type for e in read_records(successor_file)]
        assert events == ["EXECUTION_OPENED", "RESUME_STARTED", "MODEL_BOUND"]
        opened = read_records(successor_file)[0]
        assert opened.payload["resumed_from"] == "EXEC-0001"  # first-class resume accounting
        index = load_resume_index(root, "PROJECT-001")
        assert index["resumes"][0]["from_execution"] == "EXEC-0001"
        assert index["resumes"][0]["snapshot_ref"].endswith("-0001")


def test_duplicate_execution_prevented():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _ledger, snap_path = checkpoint(root)
        start_resume(root, snap_path, new_execution_id="EXEC-0002", actor_agent="AG-008",
                     check_git=False)
        # same source again: evaluation already knows (single-writer invariant)
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("duplicate resume" in r for r in d.reasons)
        # forcing start anyway: refused
        try:
            start_resume(root, snap_path, new_execution_id="EXEC-0003", actor_agent="AG-008",
                         check_git=False)
        except ResumeBlocked:
            pass
        else:
            raise AssertionError("source execution resumed twice")
        # a *different* snapshot resuming onto the taken target id is refused too
        _l2, snap2 = checkpoint(root, execution_id="EXEC-0004", task_id="TASK-0004")
        try:
            start_resume(root, snap2, new_execution_id="EXEC-0002", actor_agent="AG-008",
                         check_git=False)
        except (ResumeBlocked, DuplicateResumeError) as exc:
            assert "already" in str(exc)
        else:
            raise AssertionError("duplicate successor execution id accepted")


def test_resume_budget_escalates_on_repeated_signature():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        _l0, snap1 = checkpoint(root, execution_id="EXEC-0001")
        start_resume(root, snap1, new_execution_id="EXEC-0002", actor_agent="AG-008",
                     failure_signature="quota_exhausted", check_git=False)
        # EXEC-0002 runs, dies the same way: checkpoint it, resume again
        _l1, snap2 = checkpoint(root, execution_id="EXEC-0002")
        start_resume(root, snap2, new_execution_id="EXEC-0003", actor_agent="AG-008",
                     failure_signature="quota_exhausted", check_git=False)
        # third identical-signature attempt must NOT auto-proceed (§4.3 budget)
        _l2, snap3 = checkpoint(root, execution_id="EXEC-0003")
        try:
            start_resume(root, snap3, new_execution_id="EXEC-0004", actor_agent="AG-008",
                         failure_signature="quota_exhausted", check_git=False)
        except ResumeNeedsIntervention as exc:
            assert "NEEDS_INTERVENTION" in str(exc)
        else:
            raise AssertionError("resume budget not enforced")
        # a *different* signature is not charged against that budget
        start_resume(root, snap3, new_execution_id="EXEC-0004", actor_agent="AG-008",
                     failure_signature="container-death", check_git=False)


def test_terminal_execution_still_resumable_forward_only():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        ledger, snap_path = checkpoint(root)
        ledger.mark_terminal("AG-008", status="FAILED", reason="crash")
        d = evaluate_resume(root, snap_path, check_git=False)
        assert d.verdict is ResumeVerdict.READY  # forward-only: successor record opens
        assert any("terminal" in w for w in d.warnings)


def test_unreadable_snapshot_blocked_not_fatal():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        d = evaluate_resume(root, Path(td) / "ghost.json", check_git=False)
        assert d.verdict is ResumeVerdict.BLOCKED
        assert any("unreadable" in r for r in d.reasons)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
