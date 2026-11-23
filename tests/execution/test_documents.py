"""Numbered document system tests: EXEC_000N allocation, immutability, supersede, state."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.execution.documents import (  # noqa: E402
    SCOPE_NORMATIVE,
    SCOPE_OPERATIONAL,
    DocumentError,
    consolidated_state,
    create_document,
    latest_document,
    list_documents,
    parse_document,
    rebuild_index,
    verify_document,
    verify_index,
    write_state_document,
)
from orchestration.execution.ledger import Ledger, ledger_path  # noqa: E402


def mk(root, kind="report", agent_id="AG-008", body="## Summary\n\ndone\n", **overrides):
    kwargs = dict(
        kind=kind, agent_id=agent_id, body=body, project_id="PROJECT-001",
        execution_id="EXEC-0001", task_id="TASK-0001",
    )
    kwargs.update(overrides)
    return create_document(root, SCOPE_OPERATIONAL, **kwargs)


def test_gapless_numbering_and_index():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        first = mk(root, title="One")
        second = mk(root, kind="recovery", title="Two")
        assert first.doc_id == "EXEC_0001"
        assert second.doc_id == "EXEC_0002"
        assert (root / "projects/PROJECT-001/execution/EXEC_0001.md").is_file()
        index = json.loads((root / "projects/PROJECT-001/execution/index.json").read_text())
        assert index["next_number"] == 3
        assert set(index["documents"]) == {"EXEC_0001", "EXEC_0002"}
        assert verify_index(root, SCOPE_OPERATIONAL, "PROJECT-001") == []


def test_scopes_number_separately():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        operational = mk(root)
        normative = create_document(
            root, SCOPE_NORMATIVE, kind="runbook", agent_id="AG-008", body="steps\n"
        )
        assert operational.doc_id == "EXEC_0001"
        assert normative.doc_id == "EXEC_0001"  # independent series
        assert (root / "docs/execution/EXEC_0001.md").is_file()
        assert verify_index(root, SCOPE_NORMATIVE) == []


def test_metadata_roundtrip_and_hash():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        doc = mk(root, title="Report", snapshot_refs=["SNAP-PROJECT-001-EXEC-0001-0001"],
                 ledger_range=(1, 7), status="FINAL")
        text = (root / "projects/PROJECT-001/execution/EXEC_0001.md").read_text(encoding="utf-8")
        parsed = parse_document(text)
        assert parsed.doc_id == "EXEC_0001"
        assert parsed.execution_id == "EXEC-0001"
        assert parsed.task_id == "TASK-0001"
        assert parsed.snapshot_refs == ["SNAP-PROJECT-001-EXEC-0001-0001"]
        assert parsed.ledger_range == (1, 7)
        assert parsed.status == "FINAL"
        assert verify_document(root / "projects/PROJECT-001/execution/EXEC_0001.md") == []
        # body-only mutation is detected (tamper)
        path = root / "projects/PROJECT-001/execution/EXEC_0001.md"
        path.write_text(text + "injected finding\n", encoding="utf-8")
        issues = verify_document(path)
        assert any("content_sha256" in i for i in issues)


def test_bad_identifiers_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        try:
            mk(root, execution_id="EXEC-1")
        except DocumentError:
            pass
        else:
            raise AssertionError("malformed execution_id accepted")
        try:
            mk(root, kind="fan-fiction")
        except DocumentError:
            pass
        else:
            raise AssertionError("unknown kind accepted")


def test_supersede_flow():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = mk(root, body="## Summary\n\nwrong number\n", status="FINAL")
        corrected = mk(root, body="## Summary\n\nright number\n", supersedes=original.doc_id,
                       status="FINAL")
        assert corrected.supersedes == "EXEC_0001"
        old_text = (root / "projects/PROJECT-001/execution/EXEC_0001.md").read_text()
        assert "Superseded by EXEC_0002.md" in old_text
        assert verify_document(root / "projects/PROJECT-001/execution/EXEC_0001.md") == []
        latest = latest_document(root, SCOPE_OPERATIONAL, project_id="PROJECT-001")
        assert latest.doc_id == "EXEC_0002"  # superseded doc is not the latest state
        # linear chains only: EXEC_0001 may not be superseded twice
        try:
            mk(root, supersedes="EXEC_0001")
        except DocumentError as exc:
            assert "already superseded" in str(exc)
        else:
            raise AssertionError("double supersede accepted")
        index = rebuild_index(root, SCOPE_OPERATIONAL, "PROJECT-001")
        assert index["documents"]["EXEC_0001"]["superseded_by"] == "EXEC_0002"
        assert verify_index(root, SCOPE_OPERATIONAL, "PROJECT-001") == []


def test_supersede_journals_to_ledger():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ledger = Ledger.create(
            ledger_path(root, "PROJECT-001", "EXEC-0001"), "EXEC-0001", actor_agent="AG-008"
        )
        original = mk(root)
        mk(root, supersedes=original.doc_id, ledger=ledger)
        event = ledger.entries[-1]
        assert event.event_type == "DOC_SUPERSEDED"
        assert event.payload == {
            "effect": "idempotent",
            "superseded": "EXEC_0001",
            "by": "EXEC_0002",
        }


def test_latest_queries():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mk(root, kind="report", execution_id="EXEC-0001")
        mk(root, kind="recovery", execution_id="EXEC-0002")
        docs = list_documents(root, SCOPE_OPERATIONAL, "PROJECT-001")
        assert [d.doc_id for d in docs] == ["EXEC_0001", "EXEC_0002"]
        assert latest_document(root, SCOPE_OPERATIONAL, project_id="PROJECT-001",
                               execution_id="EXEC-0002").kind == "recovery"
        assert latest_document(root, SCOPE_OPERATIONAL, project_id="PROJECT-001",
                               kind="report").doc_id == "EXEC_0001"
        assert latest_document(root, SCOPE_OPERATIONAL, project_id="PROJECT-001",
                               kind="runbook") is None


def test_consolidated_state_and_state_document():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mk(root, body="## Outcome\n\nfinished\n", status="FINAL")
        ledger = Ledger.create(
            ledger_path(root, "PROJECT-001", "EXEC-0001"), "EXEC-0001", actor_agent="AG-008"
        )
        ledger.mark_terminal("AG-008", status="COMPLETED")
        state = consolidated_state(root, "PROJECT-001")
        exec_row = state["executions"]["EXEC-0001"]
        assert exec_row["terminal"] is True
        assert exec_row["ledger"]["count"] == 2
        assert "EXEC_0001" in exec_row["documents"]

        doc = write_state_document(root, "PROJECT-001", agent_id="AG-008")
        assert doc.kind == "state"
        assert doc.doc_id == "EXEC_0002"
        again = write_state_document(root, "PROJECT-001", agent_id="AG-008")
        assert again.doc_id == doc.doc_id  # idempotent while state is stable
        # a new execution changes state: next write supersedes the state doc
        other = Ledger.create(
            ledger_path(root, "PROJECT-001", "EXEC-0002"), "EXEC-0002", actor_agent="AG-008"
        )
        other.append("TOOL_USED", "AG-008")
        doc2 = write_state_document(root, "PROJECT-001", agent_id="AG-008")
        assert doc2.doc_id == "EXEC_0003"
        assert doc2.supersedes == "EXEC_0002"
        assert latest_document(root, SCOPE_OPERATIONAL, project_id="PROJECT-001",
                               kind="state").doc_id == "EXEC_0003"
        assert verify_index(root, SCOPE_OPERATIONAL, "PROJECT-001") == []


def test_index_divergence_detected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mk(root)
        mk(root)
        index_file = root / "projects/PROJECT-001/execution/index.json"
        data = json.loads(index_file.read_text(encoding="utf-8"))
        del data["documents"]["EXEC_0002"]
        index_file.write_text(json.dumps(data), encoding="utf-8")
        issues = verify_index(root, SCOPE_OPERATIONAL, "PROJECT-001")
        assert any("EXEC_0002" in i for i in issues)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
