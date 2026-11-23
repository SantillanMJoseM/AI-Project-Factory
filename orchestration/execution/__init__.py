"""Execution continuity plane (Stage 2A).

Stdlib-only implementation of the components specified in
``docs/execution/EXECUTION_ARCHITECTURE.md`` (EXEC-ARCHITECTURE-0001):

Modules:
  models     - §6 artifact dataclasses (TaskSnapshot, LedgerEntry,
               ContextManifest), controlled vocabularies, and the single
               integrity contract of §7 (SHA-256, canonical JSON, self-hash
               exclusion, flat file-set root)
  snapshot   - §4.2 Execution Snapshot Manager: create / verify / list
               checkpoint snapshots, append-only with supersede pointers
  ledger     - §4.4 Execution Ledger: append-only JSONL, genesis-linked
               hash chain, full-chain verification
  resume     - §4.3 Resume Engine: fail-closed eligibility evaluation and
               the forward-only resume transaction (duplicate-execution
               prevention, resume budget, never-re-apply journal)
  context    - §4.1 Dynamic Context Manager: tiered context assembly
               (T0-T3), token budgeting, staleness checks, resume rebuild
  documents  - §5 numbered EXEC_000N.md system: two scopes, gapless index
               allocation, immutability by supersede, latest consolidated
               state
  cli        - command-line entry point (``python -m orchestration.execution.cli``)

Design posture (non-negotiable, inherited): fail-closed — an unverifiable
snapshot, ledger, or recovery path is BLOCKED, not best-effort; forward-only
recovery — history is never rewritten; destructive repair is LEVEL C and this
package only *prepares* such dossiers, never executes them.

Boundary: this package touches no agent definitions, no runtime DB, no
schemas, policies, or config. It exchanges artifacts with the repository
plane only (conversation/session state is disposable; these files are the
continuity record).
"""

from .context import (
    ContextError,
    StalenessReport,
    assemble_context,
    check_staleness,
    find_manifest_by_hash,
    load_manifest,
    rebuild_for_resume,
)
from .documents import (
    DocumentError,
    ExecDocument,
    consolidated_state,
    create_document,
    latest_document,
    verify_document,
    verify_index,
    write_state_document,
)
from .ledger import (
    Ledger,
    LedgerError,
    LedgerVerifyReport,
    ledger_path,
    read_records,
    verify_chain_head,
    verify_ledger,
)
from .models import (
    ContextManifest,
    Effect,
    EventType,
    ExecutionError,
    LedgerEntry,
    ResumeVerdict,
    SnapshotReason,
    Staleness,
    TaskSnapshot,
)
from .resume import (
    DuplicateResumeError,
    ResumeBlocked,
    ResumeDecision,
    ResumeError,
    ResumeNeedsIntervention,
    evaluate_resume,
    start_resume,
)
from .snapshot import (
    SnapshotError,
    SnapshotVerifyReport,
    create_snapshot,
    latest_snapshot,
    list_snapshots,
    load_snapshot,
    verify_snapshot,
)

__version__ = "0.1.0"

__all__ = [
    "ContextError",
    "ContextManifest",
    "DocumentError",
    "DuplicateResumeError",
    "Effect",
    "EventType",
    "ExecDocument",
    "ExecutionError",
    "Ledger",
    "LedgerEntry",
    "LedgerError",
    "LedgerVerifyReport",
    "ResumeBlocked",
    "ResumeDecision",
    "ResumeError",
    "ResumeNeedsIntervention",
    "ResumeVerdict",
    "SnapshotError",
    "SnapshotReason",
    "SnapshotVerifyReport",
    "Staleness",
    "StalenessReport",
    "TaskSnapshot",
    "assemble_context",
    "check_staleness",
    "consolidated_state",
    "create_document",
    "create_snapshot",
    "evaluate_resume",
    "find_manifest_by_hash",
    "latest_document",
    "latest_snapshot",
    "ledger_path",
    "list_snapshots",
    "load_manifest",
    "load_snapshot",
    "read_records",
    "rebuild_for_resume",
    "start_resume",
    "verify_chain_head",
    "verify_document",
    "verify_index",
    "verify_ledger",
    "verify_snapshot",
    "write_state_document",
]
