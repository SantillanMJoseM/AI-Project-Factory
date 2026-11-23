"""Execution Snapshot Manager — hashed, commit-anchored checkpoints (Stage 2A).

Implements §4.2, §6.1 and §7 of ``docs/execution/EXECUTION_ARCHITECTURE.md``:

* one canonical JSON document per checkpoint at
  ``projects/<PROJECT_ID>/execution/snapshots/SNAP-<PROJECT_ID>-<EXEC-NNNN>-<seq>.json``;
* content = execution identity, git anchors, DCM context-manifest hash,
  working file set with per-file SHA-256 and a flat file-set root hash,
  pinned skill set, model binding, and the ledger window ending at the
  recorded chain head;
* ``snapshot_hash`` = canonical hash with the hash field itself excluded;
* snapshots are append-only: superseded snapshots are never deleted, only
  pointed to via ``supersedes`` by the newer snapshot (deletion is LEVEL C);
* every accepted checkpoint journals ``CHECKPOINT_WRITTEN`` to the ledger
  after the window it certifies — so the repo holds the ledger up to the
  last snapshot (§4.4).

Verification here is integrity + working-tree match; the *policy* of what
divergence tolerates resume lives in :mod:`orchestration.execution.resume`
(fail-closed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .ledger import Ledger, LedgerError, ledger_path, verify_chain_head
from .models import (
    ExecutionError,
    FileRef,
    GitAnchor,
    LedgerWindow,
    ResumeEligibility,
    SkillPin,
    SnapshotReason,
    TaskSnapshot,
    canonical_json,
    compute_file_set_root,
    hash_without,
    sha256_file,
    utc_now_stamp,
)


class SnapshotError(ExecutionError):
    """Structural or integrity failure in a snapshot (fail-closed)."""


# ---------------------------------------------------------------------------
# Paths and naming
# ---------------------------------------------------------------------------


def snapshots_dir(repo_root: Path, project_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "execution" / "snapshots"


def snapshot_id_for(project_id: str, execution_id: str, seq: int) -> str:
    return f"SNAP-{project_id}-{execution_id}-{seq:04d}"


def snapshot_file_name(sid: str) -> str:
    return sid + ".json"


# ---------------------------------------------------------------------------
# Verification report
# ---------------------------------------------------------------------------


@dataclass
class SnapshotVerifyReport:
    """Integrity verdict for one snapshot. ``ok`` only when every check passes;
    a mismatch means TAMPERED/CORRUPT ⇒ BLOCKED + escalation (§7)."""

    snapshot_id: str = ""
    path: str = ""
    ok: bool = True
    integrity_issues: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    extra_files: List[str] = field(default_factory=list)
    ledger_issues: List[str] = field(default_factory=list)

    @property
    def tree_matches(self) -> bool:
        return not (self.missing_files or self.modified_files)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "path": self.path,
            "ok": self.ok,
            "integrity_issues": list(self.integrity_issues),
            "missing_files": list(self.missing_files),
            "modified_files": list(self.modified_files),
            "extra_files": list(self.extra_files),
            "ledger_issues": list(self.ledger_issues),
        }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def create_snapshot(
    repo_root: Path,
    *,
    project_id: str,
    execution_id: str,
    task_id: str,
    agent_id: str,
    reason: Any,
    files: Sequence[str] = (),
    working_directory: str = ".",
    context_manifest_hash: Optional[str] = None,
    skills: Iterable[Tuple[str, str]] = (),
    model_binding: Optional[Dict[str, Any]] = None,
    ledger: Optional[Ledger] = None,
    seq_from: int = 1,
    resume_eligible: bool = True,
    requires_approval: bool = False,
    eligibility_notes: str = "",
    git_branch: str = "",
    before_commit: str = "",
    after_commit: str = "",
    supersedes: Optional[str] = None,
    stamp: Optional[str] = None,
) -> TaskSnapshot:
    """Freeze one resumable point and commit it to the repository plane.

    ``files`` are repository-relative paths hashed from disk (aligns with
    ``executions.file_hashes``). ``skills`` yields ``(skill_id, path)`` pairs
    pinned by content hash (§10). ``ledger``, when given, is the in-memory
    :class:`~orchestration.execution.ledger.Ledger` for this execution: the
    snapshot certifies the window ``[seq_from..head]`` and then journals
    ``CHECKPOINT_WRITTEN``.
    """
    repo_root = Path(repo_root)
    stamp = stamp or utc_now_stamp()
    directory = snapshots_dir(repo_root, project_id)
    directory.mkdir(parents=True, exist_ok=True)

    existing = list_snapshots(repo_root, project_id, execution_id)
    next_seq = (existing[-1].seq_number if existing else 0) + 1
    sid = snapshot_id_for(project_id, execution_id, next_seq)

    file_refs: List[FileRef] = []
    for rel in files:
        target = (repo_root / rel).resolve()
        root_resolved = repo_root.resolve()
        if root_resolved not in target.parents and target != root_resolved:
            raise SnapshotError(f"file {rel!r} escapes repository root")
        if not target.is_file():
            raise SnapshotError(f"snapshot file_set member missing: {rel!r}")
        file_refs.append(FileRef(path=str(rel).replace("\\", "/"), sha256=sha256_file(target)))
    file_set_root = compute_file_set_root([f.to_dict() for f in file_refs])

    skill_pins: List[SkillPin] = []
    for skill_id, skill_path in skills:
        target = Path(skill_path)
        if not target.is_absolute():
            target = repo_root / target
        if not target.is_file():
            raise SnapshotError(f"pinned skill content missing: {skill_path!r}")
        skill_pins.append(
            SkillPin(
                skill_id=skill_id,
                content_hash=sha256_file(target),
                registry_version=(model_binding or {}).get("registry_version", "0.1.0"),
            )
        )

    window: Optional[LedgerWindow] = None
    if ledger is not None:
        if ledger.execution_id != execution_id:
            raise SnapshotError("ledger belongs to a different execution")
        if ledger.count < seq_from:
            raise SnapshotError("ledger shorter than requested window")
        window = ledger.window(seq_from=seq_from)
        # Record the repository-relative ledger path (§6.1 example).
        try:
            window.path = str(Path(ledger.path).resolve().relative_to(repo_root.resolve()))
        except ValueError:
            window.path = Path(ledger.path).name

    snapshot = TaskSnapshot(
        snapshot_id=sid,
        project_id=project_id,
        execution_id=execution_id,
        task_id=task_id,
        agent_id=agent_id,
        created_at=stamp,
        reason=SnapshotReason(str(reason)),
        git=GitAnchor(branch=git_branch, before_commit=before_commit, after_commit=after_commit),
        working_directory=working_directory,
        context_manifest_hash=context_manifest_hash,
        file_set=file_refs,
        file_set_root_hash=file_set_root,
        skill_set=skill_pins,
        model_binding=dict(model_binding or {}),
        ledger=window,
        resume_eligibility=ResumeEligibility(
            eligible=resume_eligible,
            requires_approval=requires_approval,
            notes=eligibility_notes,
        ),
        supersedes=supersedes if supersedes is not None else (existing[-1].snapshot_id if existing else None),
        snapshot_hash="",
    )
    snapshot.snapshot_hash = snapshot.compute_hash()
    issues = snapshot.validate()
    if issues:
        raise SnapshotError("invalid snapshot: " + "; ".join(issues))

    target = directory / snapshot_file_name(sid)
    if target.exists():
        raise SnapshotError(f"snapshot already exists (append-only): {target}")
    # Canonical bytes + trailing newline; hash is over the canonical JSON
    # (no trailing newline), recomputed from parsed content at verify time.
    target.write_text(canonical_json(snapshot.to_dict()) + "\n", encoding="utf-8")

    if ledger is not None:
        ledger.append(
            "CHECKPOINT_WRITTEN",
            agent_id,
            {
                "snapshot_ref": str(target.relative_to(repo_root)),
                "snapshot_hash": snapshot.snapshot_hash,
            },
            effect="idempotent",
            timestamp=stamp,
        )
    return snapshot


# ---------------------------------------------------------------------------
# Load / list
# ---------------------------------------------------------------------------


def load_snapshot(path: Path) -> TaskSnapshot:
    """Parse one snapshot file (structure only; use :func:`verify_snapshot`)."""
    path = Path(path)
    if not path.exists():
        raise SnapshotError(f"snapshot not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SnapshotError(f"{path}: malformed JSON: {exc}") from exc
    try:
        return TaskSnapshot.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotError(f"{path}: bad snapshot shape: {exc}") from exc


@dataclass
class SnapshotIndex:
    """One row of :func:`list_snapshots` — cheap, parse-only listing."""

    snapshot_id: str
    seq_number: int
    execution_id: str
    path: Path


def list_snapshots(
    repo_root: Path, project_id: str, execution_id: Optional[str] = None
) -> List[SnapshotIndex]:
    """List snapshots for a project (optionally one execution), in order.

    Snapshots are append-only; listing never mutates anything.
    """
    directory = snapshots_dir(Path(repo_root), project_id)
    rows: List[SnapshotIndex] = []
    if not directory.is_dir():
        return rows
    for candidate in sorted(directory.glob("SNAP-*.json")):
        if execution_id is not None and f"-{execution_id}-" not in candidate.stem:
            continue
        try:
            snap = load_snapshot(candidate)
        except SnapshotError:
            # A file we cannot parse is still listed (integrity review will
            # catch it); fabricate an index row from the name.
            stem = candidate.stem.split("-")
            try:
                seq = int(stem[-1])
            except ValueError:
                seq = -1
            rows.append(SnapshotIndex(candidate.stem, seq, stem[3] + "-" + stem[4] if len(stem) > 4 else "?", candidate))
            continue
        rows.append(
            SnapshotIndex(snap.snapshot_id, int(snap.snapshot_id.rsplit("-", 1)[-1]), snap.execution_id, candidate)
        )
    rows.sort(key=lambda r: (r.execution_id, r.seq_number))
    return rows


def latest_snapshot(
    repo_root: Path, project_id: str, execution_id: str
) -> Optional[TaskSnapshot]:
    """Most recent snapshot for an execution, or ``None`` (never raises)."""
    rows = list_snapshots(repo_root, project_id, execution_id)
    return load_snapshot(rows[-1].path) if rows else None


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_snapshot(
    repo_root: Path,
    snapshot_path: Path,
    *,
    check_files: bool = True,
    check_ledger: bool = True,
) -> SnapshotVerifyReport:
    """Re-verify a snapshot against committed bytes and the live repository.

    Checks, fail-closed (§4.3 clause 2, §7):
      1. structural validity and self-hash of the parsed document;
      2. file-set root hash consistency;
      3. every ``file_set`` member present on disk with a matching hash
         (missing/modified are reported separately — divergence *policy* is
         applied by the Resume Engine);
      4. the recorded ledger window's chain head recomputes from the ledger
         file itself.
    """
    repo_root = Path(repo_root)
    snapshot_path = Path(snapshot_path)
    snapshot = load_snapshot(snapshot_path)
    report = SnapshotVerifyReport(snapshot_id=snapshot.snapshot_id, path=str(snapshot_path))

    report.integrity_issues.extend(snapshot.validate())
    if snapshot.snapshot_hash and hash_without(snapshot.to_dict(), "snapshot_hash") != snapshot.snapshot_hash:
        report.integrity_issues.append("snapshot_hash does not match committed bytes")

    if check_files:
        for ref in snapshot.file_set:
            target = repo_root / ref.path
            if not target.is_file():
                report.missing_files.append(ref.path)
            elif sha256_file(target) != ref.sha256:
                report.modified_files.append(ref.path)

    if check_ledger and snapshot.ledger is not None:
        ledger_file = _resolve_ledger_file(repo_root, snapshot)
        if ledger_file is None:
            report.ledger_issues.append("ledger file for snapshot window not found")
        else:
            try:
                report.ledger_issues.extend(
                    verify_chain_head(ledger_file, snapshot.ledger.chain_head_hash, snapshot.ledger.seq_to)
                )
            except LedgerError as exc:
                report.ledger_issues.append(str(exc))

    report.ok = not (report.integrity_issues or report.ledger_issues)
    return report


def _resolve_ledger_file(repo_root: Path, snapshot: TaskSnapshot) -> Optional[Path]:
    assert snapshot.ledger is not None
    candidates = [repo_root / snapshot.ledger.path]
    candidates.append(ledger_path(repo_root, snapshot.project_id, snapshot.execution_id))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


__all__ = [
    "SnapshotError",
    "SnapshotIndex",
    "SnapshotVerifyReport",
    "create_snapshot",
    "latest_snapshot",
    "list_snapshots",
    "load_snapshot",
    "snapshot_file_name",
    "snapshot_id_for",
    "snapshots_dir",
    "verify_snapshot",
]
