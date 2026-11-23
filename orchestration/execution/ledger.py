"""Execution Ledger — append-only, chain-hashed JSONL journal (Stage 2A).

Implements §4.4 and §6.3 of ``docs/execution/EXECUTION_ARCHITECTURE.md``:
the repository-visible bridge between the in-progress DB and committed
evidence. One JSONL record per event, hash-chained with the same canonical
contract as the runtime ``events`` table (§7):

* ``payload_hash``  = canonical hash of the payload;
* ``record_hash``   = canonical hash of the record with ``record_hash`` removed;
* ``prev_hash``     = previous record's ``record_hash``; the first record's
  ``prev_hash`` = hash of its own ``EXECUTION_OPENED`` genesis payload;
* verification = recompute each ``record_hash``, confirm ``prev_hash`` links,
  confirm the head. Mismatch ⇒ ``TAMPERED`` ⇒ escalate; no automatic repair,
  ever (fail-closed).

Chain order, not wall-clock, defines sequence (§4.4). Files live at
``projects/<PROJECT_ID>/execution/ledger/LEDGER-<EXEC_000N>.jsonl`` (§5).

The write path is append-only: an existing ledger is only ever opened in
append mode; there is no rewrite, no truncate, no delete in this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Effect,
    EventType,
    ExecutionError,
    LedgerEntry,
    canonical_json,
    sha256_text,
    utc_now_stamp,
)


class LedgerError(ExecutionError):
    """Structural or integrity failure in a ledger (fail-closed)."""


def ledger_file_name(execution_id: str) -> str:
    """Map execution id ``EXEC-0042`` to file ``LEDGER-EXEC_0042.jsonl`` (§5)."""
    if "-" not in execution_id:
        raise LedgerError(f"bad execution_id: {execution_id!r}")
    return "LEDGER-" + execution_id.replace("-", "_") + ".jsonl"


def ledger_path(repo_root: Path, project_id: str, execution_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "execution" / "ledger" / ledger_file_name(
        execution_id
    )


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    return sha256_text(canonical_json(dict(payload or {})))


@dataclass
class LedgerVerifyReport:
    """Outcome of a full-chain verification. ``ok`` is the only PASS verdict;
    anything else means TAMPERED/CORRUPT and must escalate (§4.4)."""

    path: str = ""
    ok: bool = True
    count: int = 0
    head_hash: str = ""
    execution_id: str = ""
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "count": self.count,
            "head_hash": self.head_hash,
            "execution_id": self.execution_id,
            "issues": list(self.issues),
        }


class Ledger:
    """Append-only handle over one execution's JSONL ledger."""

    def __init__(self, path: Path, execution_id: str, entries: Optional[List[LedgerEntry]] = None):
        self.path = Path(path)
        self.execution_id = execution_id
        self.entries: List[LedgerEntry] = list(entries or [])

    # -- construction ------------------------------------------------------

    @classmethod
    def create(
        cls,
        path: Path,
        execution_id: str,
        *,
        actor_agent: str,
        payload: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> "Ledger":
        """Create a new ledger file. First record is ``EXECUTION_OPENED``.

        Fails closed if a ledger already exists at ``path`` (append-only:
        history is never restarted).
        """
        path = Path(path)
        if path.exists():
            raise LedgerError(f"ledger already exists (append-only): {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        ledger = cls(path, execution_id)
        body = {"effect": Effect.NONE.value, **(payload or {})}
        record = ledger._make_entry(
            seq=1,
            event_type=EventType.EXECUTION_OPENED,
            actor_agent=actor_agent,
            payload=body,
            timestamp=timestamp or utc_now_stamp(),
        )
        # Genesis link: prev_hash = hash of the EXECUTION_OPENED genesis payload (§7).
        record.prev_hash = record.payload_hash
        record.record_hash = record.compute_record_hash()
        issues = record.validate()
        if issues:
            raise LedgerError("invalid genesis record: " + "; ".join(issues))
        ledger.entries.append(record)
        ledger._append_bytes(record)
        return ledger

    @classmethod
    def open(cls, path: Path, execution_id: Optional[str] = None) -> "Ledger":
        """Load an existing ledger, verifying its chain (fail-closed)."""
        path = Path(path)
        if not path.exists():
            raise LedgerError(f"ledger not found: {path}")
        entries = read_records(path)
        report = _verify_entries(entries, path=str(path))
        if not report.ok:
            raise LedgerError(f"ledger chain verification failed: {report.issues}")
        if execution_id is None:
            execution_id = entries[0].execution_id
        for entry in entries:
            if entry.execution_id != execution_id:
                raise LedgerError(
                    f"ledger {path.name} mixes executions: {execution_id!r} vs {entry.execution_id!r}"
                )
        return cls(path, execution_id, entries)

    # -- append ------------------------------------------------------------

    def append(
        self,
        event_type: Any,
        actor_agent: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        effect: Any = Effect.NONE,
        timestamp: Optional[str] = None,
    ) -> LedgerEntry:
        """Append one chained record. Unknown event types are rejected (§4.4)."""
        event_type = _as_event(event_type)
        body = {"effect": _as_effect(effect).value, **(payload or {})}
        stamp = timestamp or utc_now_stamp()
        seq = (self.entries[-1].seq if self.entries else 0) + 1
        record = self._make_entry(
            seq=seq,
            event_type=event_type,
            actor_agent=actor_agent,
            payload=body,
            timestamp=stamp,
        )
        record.prev_hash = self.entries[-1].record_hash if self.entries else record.payload_hash
        record.record_hash = record.compute_record_hash()
        issues = record.validate()
        if issues:
            raise LedgerError("invalid ledger record: " + "; ".join(issues))
        self.entries.append(record)
        self._append_bytes(record)
        return record

    def mark_terminal(
        self, actor_agent: str, *, status: str, reason: str = "", timestamp: Optional[str] = None
    ) -> LedgerEntry:
        """Journal the stop of an execution (§4.3: forward-only, never rewritten)."""
        return self.append(
            EventType.EXECUTION_TERMINAL,
            actor_agent,
            {"status": status, "reason": reason},
            effect=Effect.NONE,
            timestamp=timestamp,
        )

    # -- queries -----------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def head_hash(self) -> str:
        """Chain head = last record's ``record_hash`` ("" for an empty ledger)."""
        return self.entries[-1].record_hash if self.entries else ""

    def window(self, seq_from: int = 1, seq_to: Optional[int] = None):
        """The ``LedgerWindow`` covering [seq_from..seq_to] ending at a head (§6.1)."""
        from .models import LedgerWindow

        if not self.entries:
            raise LedgerError("cannot window an empty ledger")
        seq_to = self.count if seq_to is None else seq_to
        subset = [e for e in self.entries if seq_from <= e.seq <= seq_to]
        if not subset:
            raise LedgerError(f"empty ledger window [{seq_from}..{seq_to}]")
        return LedgerWindow(
            path=self.path.name,
            seq_from=seq_from,
            seq_to=seq_to,
            chain_head_hash=subset[-1].record_hash,
        )

    def has_event(self, event_type: Any) -> bool:
        name = _as_event(event_type).value
        return any(e.event_type == name for e in self.entries)

    def is_terminal(self) -> bool:
        return self.has_event(EventType.EXECUTION_TERMINAL)

    def events_of(self, event_type: Any) -> List[LedgerEntry]:
        name = _as_event(event_type).value
        return [e for e in self.entries if e.event_type == name]

    # -- internals ---------------------------------------------------------

    def _make_entry(
        self,
        seq: int,
        event_type: EventType,
        actor_agent: str,
        payload: Dict[str, Any],
        timestamp: str,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            seq=seq,
            execution_id=self.execution_id,
            event_type=event_type.value,
            timestamp=timestamp,
            actor_agent=actor_agent,
            payload=payload,
        )
        entry.payload_hash = compute_payload_hash(entry.payload)
        return entry

    def _append_bytes(self, record: LedgerEntry) -> None:
        # Append-only physical write: never rewrite existing lines. One JSON
        # object per line, key-sorted, no trailing whitespace inside the line.
        line = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


# ---------------------------------------------------------------------------
# Module-level read / verify
# ---------------------------------------------------------------------------


def read_records(path: Path) -> List[LedgerEntry]:
    """Parse a JSONL ledger file into entries without verifying the chain."""
    path = Path(path)
    entries: List[LedgerEntry] = []
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(LedgerEntry.from_dict(json.loads(raw)))
            except (ValueError, KeyError, TypeError) as exc:
                raise LedgerError(f"{path.name}:{lineno}: malformed record: {exc}") from exc
    return entries


def verify_ledger(path: Path) -> LedgerVerifyReport:
    """Full-chain recompute (§7). Mismatch ⇒ not ok; caller escalates (§4.4)."""
    path = Path(path)
    if not path.exists():
        report = LedgerVerifyReport(path=str(path))
        report.ok = False
        report.issues.append("ledger file not found")
        return report
    try:
        entries = read_records(path)
    except LedgerError as exc:
        report = LedgerVerifyReport(path=str(path))
        report.ok = False
        report.issues.append(str(exc))
        return report
    return _verify_entries(entries, path=str(path))


def verify_chain_head(path: Path, expected_head: str, seq_to: int) -> List[str]:
    """Verify the chain up to ``seq_to`` ends exactly at ``expected_head``.

    Used by snapshot verification (§4.3 clause 2: the recorded
    ``chain_head_hash`` must match the ledger recomputed independently).
    """
    report = verify_ledger(path)
    issues = list(report.issues)
    if not report.ok:
        return issues or ["ledger chain verification failed"]
    entries = read_records(Path(path))
    subset = [e for e in entries if e.seq <= seq_to]
    if len(subset) != seq_to:
        issues.append(f"ledger has {len(subset)} records up to seq {seq_to}, expected {seq_to}")
    elif subset and subset[-1].record_hash != expected_head:
        issues.append("chain head does not match snapshot ledger window")
    return issues


def _verify_entries(entries: List[LedgerEntry], path: str = "") -> LedgerVerifyReport:
    report = LedgerVerifyReport(path=path, count=len(entries))
    if not entries:
        report.ok = False
        report.issues.append("ledger is empty")
        return report
    prev_record_hash = ""
    for position, entry in enumerate(entries, start=1):
        structural = entry.validate()
        for issue in structural:
            report.issues.append(f"seq {entry.seq}: {issue}")
        if entry.seq != position:
            report.issues.append(f"record at position {position} carries seq {entry.seq}")
        expected_payload = compute_payload_hash(entry.payload)
        if entry.payload_hash != expected_payload:
            report.issues.append(f"seq {entry.seq}: payload_hash mismatch")
        expected_prev = prev_record_hash or entry.payload_hash
        if entry.prev_hash != expected_prev:
            report.issues.append(f"seq {entry.seq}: prev_hash does not link")
        if entry.record_hash != entry.compute_record_hash():
            report.issues.append(f"seq {entry.seq}: record_hash mismatch")
        if entry.execution_id != entries[0].execution_id:
            report.issues.append(f"seq {entry.seq}: execution_id differs from ledger owner")
        prev_record_hash = entry.record_hash
    first = entries[0]
    if first.event_type != EventType.EXECUTION_OPENED.value:
        report.issues.append("first record must be EXECUTION_OPENED (genesis)")
    if len(entries) != len(set(e.seq for e in entries)):
        report.issues.append("duplicate seq values")
    report.ok = not report.issues
    if report.ok:
        report.head_hash = entries[-1].record_hash
        report.execution_id = entries[0].execution_id
    return report


def _as_event(value: Any) -> EventType:
    if isinstance(value, EventType):
        return value
    try:
        return EventType(str(value))
    except ValueError as exc:
        raise LedgerError(f"unknown ledger event_type: {value!r}") from exc


def _as_effect(value: Any) -> Effect:
    if isinstance(value, Effect):
        return value
    try:
        return Effect(str(value))
    except ValueError as exc:
        raise LedgerError(f"unknown payload.effect: {value!r}") from exc


__all__ = [
    "Effect",
    "EventType",
    "Ledger",
    "LedgerError",
    "LedgerVerifyReport",
    "compute_payload_hash",
    "ledger_file_name",
    "ledger_path",
    "read_records",
    "verify_chain_head",
    "verify_ledger",
]
