"""Execution Ledger tests: genesis chain, append-only, verification, tamper detection."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.execution.ledger import (  # noqa: E402
    Ledger,
    LedgerError,
    ledger_file_name,
    ledger_path,
    read_records,
    verify_chain_head,
    verify_ledger,
)


def make_ledger(root, execution_id="EXEC-0001"):
    path = ledger_path(Path(root), "PROJECT-001", execution_id)
    return Ledger.create(path, execution_id, actor_agent="AG-008")


def test_ledger_file_naming():
    assert ledger_file_name("EXEC-0042") == "LEDGER-EXEC_0042.jsonl"


def test_genesis_chain():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        first = ledger.entries[0]
        assert first.event_type == "EXECUTION_OPENED"
        assert first.seq == 1
        # Genesis link rule (§7): prev_hash = hash of the EXECUTION_OPENED payload.
        assert first.prev_hash == first.payload_hash
        report = verify_ledger(ledger.path)
        assert report.ok, report.issues
        assert report.count == 1
        assert report.head_hash == first.record_hash


def test_append_extends_chain():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        e2 = ledger.append("STATE_CHANGED", "AG-008", {"from": "PENDING", "to": "RUNNING"})
        e3 = ledger.append("TOOL_USED", "AG-008", {"tool": "shell"}, effect="idempotent")
        assert (e2.seq, e3.seq) == (2, 3)
        assert e3.prev_hash == e2.record_hash
        assert ledger.head_hash == e3.record_hash
        reloaded = Ledger.open(ledger.path)
        assert reloaded.count == 3
        report = verify_ledger(ledger.path)
        assert report.ok, report.issues
        assert report.head_hash == e3.record_hash
        # effect tag recorded in payload (§6.3)
        assert e3.payload["effect"] == "idempotent"


def test_append_only_physical():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        ledger.append("TOOL_USED", "AG-008")
        lines_before = ledger.path.read_text(encoding="utf-8").splitlines()
        second = Ledger.open(ledger.path)
        second.append("TOOL_USED", "AG-008")
        lines_after = ledger.path.read_text(encoding="utf-8").splitlines()
        assert lines_after[: len(lines_before)] == lines_before  # history untouched
        # reopening a fresh ledger over an existing file is refused
        try:
            make_ledger(td)
        except LedgerError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("Ledger.create overwrote an existing ledger")


def test_unknown_event_type_rejected():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        try:
            ledger.append("NOT_AN_EVENT", "AG-008")
        except LedgerError as exc:
            assert "event_type" in str(exc)
        else:
            raise AssertionError("unknown event_type was accepted")


def test_bad_effect_and_actor_rejected():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        try:
            ledger.append("TOOL_USED", "AG-008", effect="maybe")
        except LedgerError:
            pass
        else:
            raise AssertionError("unknown effect was accepted")
        try:
            ledger.append("TOOL_USED", "AG-99X")
        except LedgerError:
            pass
        else:
            raise AssertionError("bad actor_agent was accepted")


def test_payload_tamper_detected():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        ledger.append("FILE_CHANGED", "AG-008", {"path": "src/a.py"}, effect="applied-irreversible")
        ledger.append("TOOL_USED", "AG-008", {"tool": "edit"})
        lines = ledger.path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        record["payload"]["path"] = "src/evil.py"  # silent content edit
        lines[1] = json.dumps(record, sort_keys=True)
        ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = verify_ledger(ledger.path)
        assert not report.ok
        assert any("seq 2" in i for i in report.issues)
        # Ledger.open must refuse to hand out a corrupt chain (fail-closed)
        try:
            Ledger.open(ledger.path)
        except LedgerError:
            pass
        else:
            raise AssertionError("Ledger.open accepted a tampered chain")


def test_record_deletion_detected():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        ledger.append("TOOL_USED", "AG-008")
        ledger.append("TOOL_USED", "AG-008")
        ledger.append("EXECUTION_TERMINAL", "AG-008", {"status": "COMPLETED"})
        assert ledger.is_terminal()
        lines = ledger.path.read_text(encoding="utf-8").splitlines()
        del lines[2]  # remove one middle record
        ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = verify_ledger(ledger.path)
        assert not report.ok
        assert any("seq" in i for i in report.issues)


def test_window_and_chain_head():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td)
        e2 = ledger.append("TOOL_USED", "AG-008")
        ledger.append("TOOL_USED", "AG-008")
        window = ledger.window(seq_from=1)
        assert window.seq_to == 3
        assert window.chain_head_hash == ledger.entries[-1].record_hash
        head2 = ledger.window(seq_from=1, seq_to=2)
        assert head2.chain_head_hash == e2.record_hash
        assert verify_chain_head(ledger.path, e2.record_hash, 2) == []
        issues = verify_chain_head(ledger.path, e2.record_hash, 3)
        assert issues  # head at seq 3 is not e2's hash


def test_missing_and_empty_ledger_fail_closed():
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "nope.jsonl"
        report = verify_ledger(missing)
        assert not report.ok and "not found" in " ".join(report.issues)
        empty = Path(td) / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        assert not verify_ledger(empty).ok
        junk = Path(td) / "junk.jsonl"
        junk.write_text("{not json}\n", encoding="utf-8")
        assert not verify_ledger(junk).ok


def test_execution_id_pinning():
    with tempfile.TemporaryDirectory() as td:
        ledger = make_ledger(td, "EXEC-0007")
        ledger.append("TOOL_USED", "AG-008")
        # opening with the wrong execution must refuse (no cross-ledger mixes)
        try:
            Ledger.open(ledger.path, "EXEC-0009")
        except LedgerError:
            pass
        else:
            raise AssertionError("ledger accepted a foreign execution_id")
        assert read_records(ledger.path)[0].execution_id == "EXEC-0007"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
