"""Execution Snapshot Manager tests: hashing, file-set integrity, supersede, verification."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.execution.ledger import Ledger, ledger_path  # noqa: E402
from orchestration.execution.models import compute_file_set_root, sha256_file  # noqa: E402
from orchestration.execution.snapshot import (  # noqa: E402
    SnapshotError,
    create_snapshot,
    latest_snapshot,
    list_snapshots,
    load_snapshot,
    snapshot_id_for,
    verify_snapshot,
)


def make_repo(td):
    root = Path(td)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('app')\n", encoding="utf-8")
    (root / "src" / "util.py").write_text("X = 1\n", encoding="utf-8")
    ledger = Ledger.create(ledger_path(root, "PROJECT-001", "EXEC-0001"), "EXEC-0001", actor_agent="AG-008")
    return root, ledger


def snap(root, ledger, **overrides):
    kwargs = dict(
        project_id="PROJECT-001",
        execution_id="EXEC-0001",
        task_id="TASK-0001",
        agent_id="AG-008",
        reason="periodic",
        files=["src/app.py", "src/util.py"],
        stamp="2026-11-19T10:00:00Z",
    )
    kwargs.update(overrides)
    return create_snapshot(root, ledger=ledger, **kwargs)


def test_snapshot_paths_and_hashes():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        snapshot = snap(root, ledger)
        assert snapshot.snapshot_id == snapshot_id_for("PROJECT-001", "EXEC-0001", 1)
        stored = root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")
        assert stored.is_file()
        # Canonical bytes: parse to the same object; self-hash excludes the field (§7).
        data = json.loads(stored.read_text(encoding="utf-8"))
        assert data["snapshot_hash"] == snapshot.snapshot_hash
        parsed = load_snapshot(stored)
        assert parsed.compute_hash() == parsed.snapshot_hash
        # File-set root recomputes from per-file hashes.
        assert parsed.file_set_root_hash == compute_file_set_root(
            [f.to_dict() for f in parsed.file_set]
        )
        assert {f.path: f.sha256 for f in parsed.file_set} == {
            "src/app.py": sha256_file(root / "src" / "app.py"),
            "src/util.py": sha256_file(root / "src" / "util.py"),
        }
        report = verify_snapshot(root, stored)
        assert report.ok and report.tree_matches


def test_snapshot_certifies_ledger_window_and_journals():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        ledger.append("TOOL_USED", "AG-008")
        before_head = ledger.head_hash
        before_count = ledger.count
        snapshot = snap(root, ledger)
        assert snapshot.ledger is not None
        assert snapshot.ledger.seq_from == 1
        assert snapshot.ledger.seq_to == before_count
        assert snapshot.ledger.chain_head_hash == before_head
        assert snapshot.ledger.path.endswith("LEDGER-EXEC_0001.jsonl")
        # CHECKPOINT_WRITTEN lands after the window (append-only journal).
        assert ledger.count == before_count + 1
        event = ledger.entries[-1]
        assert event.event_type == "CHECKPOINT_WRITTEN"
        assert event.payload["snapshot_hash"] == snapshot.snapshot_hash
        assert verify_snapshot(root, root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")).ok


def test_snapshot_supersede_chain_and_listing():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        first = snap(root, ledger)
        second = snap(root, ledger, reason="state-transition", stamp="2026-11-19T10:05:00Z")
        assert second.snapshot_id.endswith("-0002")
        assert second.supersedes == first.snapshot_id
        assert first.supersedes is None
        rows = list_snapshots(root, "PROJECT-001", "EXEC-0001")
        assert [r.snapshot_id for r in rows] == [first.snapshot_id, second.snapshot_id]
        assert latest_snapshot(root, "PROJECT-001", "EXEC-0001").snapshot_id == second.snapshot_id
        # older snapshots are never deleted by supersede (§4.2 retention)
        assert (root / "projects/PROJECT-001/execution/snapshots" / (first.snapshot_id + ".json")).is_file()


def test_snapshot_detects_file_divergence():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        snapshot = snap(root, ledger)
        stored = root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")
        (root / "src" / "app.py").write_text("print('mutated')\n", encoding="utf-8")
        (root / "src" / "util.py").unlink()
        report = verify_snapshot(root, stored)
        assert report.missing_files == ["src/util.py"]
        assert report.modified_files == ["src/app.py"]
        assert not report.tree_matches
        # integrity itself is intact: divergence is a resume-policy question,
        # not a snapshot-tamper verdict
        assert report.ok and not report.integrity_issues


def test_snapshot_detects_tampering():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        snapshot = snap(root, ledger)
        stored = root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")
        data = json.loads(stored.read_text(encoding="utf-8"))
        data["task_id"] = "TASK-9999"
        stored.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        report = verify_snapshot(root, stored)
        assert not report.ok
        assert any("snapshot_hash" in i for i in report.integrity_issues)


def test_snapshot_detects_broken_ledger_chain():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        snapshot = snap(root, ledger)
        stored = root / "projects/PROJECT-001/execution/snapshots" / (snapshot.snapshot_id + ".json")
        lines = ledger.path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[0])
        record["actor_agent"] = "AG-000"
        lines[0] = json.dumps(record, sort_keys=True)
        ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = verify_snapshot(root, stored)
        assert not report.ok
        assert report.ledger_issues


def test_snapshot_rejects_missing_files_and_escape():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        try:
            snap(root, ledger, files=["src/nope.py"])
        except SnapshotError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("missing file_set member was accepted")
        try:
            snap(root, ledger, files=["../outside_secret.txt"])
        except SnapshotError as exc:
            assert "escapes" in str(exc)
        else:
            raise AssertionError("path escape was accepted")
        try:
            snap(root, ledger, reason="not-a-trigger")
        except ValueError:
            pass
        else:
            raise AssertionError("unknown checkpoint reason was accepted")


def test_snapshot_pins_skills_and_model_binding():
    with tempfile.TemporaryDirectory() as td:
        root, ledger = make_repo(td)
        skill = root / "skill.md"
        skill.write_text("# skill\n", encoding="utf-8")
        snapshot = snap(
            root,
            ledger,
            skills=[("hads", str(skill))],
            model_binding={"provider": "opencode-go", "model": "m1", "fallback_status": "RUNNING"},
        )
        assert snapshot.skill_set[0].skill_id == "hads"
        assert snapshot.skill_set[0].content_hash == sha256_file(skill)
        assert snapshot.model_binding["model"] == "m1"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
