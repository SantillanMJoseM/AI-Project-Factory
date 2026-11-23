"""Data models and integrity primitives for execution continuity (Stage 2A).

Pure stdlib. Encodes the artifacts specified by
``docs/execution/EXECUTION_ARCHITECTURE.md`` (EXEC-ARCHITECTURE-0001), §6:

* ``TaskSnapshot``     - §6.1 resumable checkpoint for one execution
* ``ContextManifest``  - §6.2 Dynamic Context Manager output (tiers T0-T3)
* ``LedgerEntry``      - §6.3 one append-only, chain-hashed journal record

plus the controlled vocabularies (§4.4 event names, §6.3 ``effect`` tags,
§4.2 checkpoint reasons) and the single integrity contract (§7):

* SHA-256 rendered ``sha256:<64-hex>``;
* canonical JSON: UTF-8, key-sorted, compact separators, no trailing newline;
* self-hash exclusion: ``*_hash`` fields are computed over the artifact with
  that field removed (same convention as the runtime ``row_hash``);
* file-set root: ``sha256(sorted("path:hex\\n" entries))`` — flat digest.

Enforcement boundary: these are continuity artifacts. This module authorizes
nothing; permission and approval state is enforced elsewhere (fail-closed
posture inherited from R5.2A / ADR-002).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Ledger event vocabulary (EXECUTION_ARCHITECTURE §4.4 + §5/§10 additions)."""

    EXECUTION_OPENED = "EXECUTION_OPENED"
    STATE_CHANGED = "STATE_CHANGED"
    CONTEXT_ASSEMBLED = "CONTEXT_ASSEMBLED"
    SKILL_INVOKED = "SKILL_INVOKED"
    TOOL_USED = "TOOL_USED"
    FILE_CHANGED = "FILE_CHANGED"
    CHECKPOINT_WRITTEN = "CHECKPOINT_WRITTEN"
    COMMIT_ANCHOR = "COMMIT_ANCHOR"
    MODEL_BOUND = "MODEL_BOUND"
    MODEL_SWITCHED = "MODEL_SWITCHED"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    FAILURE_CLASSIFIED = "FAILURE_CLASSIFIED"
    RESUME_REQUESTED = "RESUME_REQUESTED"
    RESUME_STARTED = "RESUME_STARTED"
    RECOVERY_BLOCKED = "RECOVERY_BLOCKED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    EXECUTION_TERMINAL = "EXECUTION_TERMINAL"
    DOC_SUPERSEDED = "DOC_SUPERSEDED"
    SKILL_DRIFT = "SKILL_DRIFT"


TERMINAL_EVENTS = frozenset({EventType.EXECUTION_TERMINAL.value})


class Effect(str, Enum):
    """Resume-relevant side-effect tag (§6.3). ``applied-irreversible``
    operations recorded as applied are never re-applied on resume (§4.3)."""

    NONE = "none"
    IDEMPOTENT = "idempotent"
    APPLIED_IRREVERSIBLE = "applied-irreversible"


class SnapshotReason(str, Enum):
    """Checkpoint triggers (§4.2)."""

    PRE_OPERATION = "pre-operation"
    STATE_TRANSITION = "state-transition"
    PERIODIC = "periodic"
    DEGRADED_MODEL = "degraded-model"
    STAGE_CLOSURE = "stage-closure"


class Staleness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class ResumeVerdict(str, Enum):
    """Outcome of the fail-closed eligibility evaluation (§4.3)."""

    READY = "READY"
    BLOCKED = "BLOCKED"
    NEEDS_INTERVENTION = "NEEDS_INTERVENTION"


# ---------------------------------------------------------------------------
# Standing constants (§5, §6, §7)
# ---------------------------------------------------------------------------

EXEC_ID_RE = re.compile(r"^EXEC-[0-9]{4}$")
DOC_ID_RE = re.compile(r"^EXEC_[0-9]{4}$")
PROJECT_ID_RE = re.compile(r"^PROJECT-[0-9]{3}$")
AGENT_ID_RE = re.compile(r"^AG-[0-9]{3}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SNAPSHOT_ID_RE = re.compile(r"^SNAP-PROJECT-[0-9]{3}-EXEC-[0-9]{4}-[0-9]{4}$")
MANIFEST_ID_RE = re.compile(r"^CTX-EXEC-[0-9]{4}-[0-9]{4}$")
SKILL_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: Assembly tiers in priority order (§4.1). T0 always, T1 required, T2/T3
#: trimmable under budget with trimmed items recorded as excluded.
TIER_T0 = "T0_bootstrap"
TIER_T1 = "T1_task"
TIER_T2 = "T2_skills"
TIER_T3 = "T3_working"
TIER_ORDER = (TIER_T0, TIER_T1, TIER_T2, TIER_T3)

#: Mandatory read order from ``orchestration/policies/context-policy.md``.
T0_BOOTSTRAP_FILES = (
    "AI_START_HERE.md",
    "PROJECT_CONTEXT.md",
    "PROJECT_STATUS.md",
    "PROJECT_HANDOFF.md",
    "PROJECT_MAP.md",
)

#: Paths whose divergence or staleness blocks automatic resume (§4.3 clause 3,
#: §4.1 staleness rule): contracts, schemas, policies, gates, agents, config.
GOVERNED_PREFIXES = (
    "contracts/",
    "schemas/",
    "quality-gates/",
    "orchestration/policies/",
    "agents/",
    ".opencode/",
    "opencode.json",
)

#: Consecutive auto-resumes allowed per identical failure signature (§4.3).
MAX_AUTO_RESUMES_PER_SIGNATURE = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plain(value: Any) -> Any:
    """Convert Enums / nested containers to JSON-serializable primitives."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _as(value: Any, enum: type) -> Any:
    """Coerce a string into an enum member while tolerating already-enums."""
    if isinstance(value, enum):
        return value
    return enum(value)


class ExecutionError(Exception):
    """Base error for the continuity plane. Fail-closed: raise, never warn."""


def utc_now_stamp() -> str:
    """ISO-8601 UTC second-precision stamp, e.g. ``2026-11-19T10:15:00Z``."""
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_governed(rel_path: str) -> bool:
    """True if a repository-relative path is governed content (§4.3 clause 3)."""
    normalized = rel_path.replace("\\", "/").lstrip("./")
    return normalized.startswith(GOVERNED_PREFIXES)


# ---------------------------------------------------------------------------
# Integrity primitives (§7) — one rule, one toolchain
# ---------------------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    """Canonical JSON: key-sorted, compact separators, no trailing newline."""
    return json.dumps(_plain(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def hash_without(obj: Any, *fields_to_drop: str) -> str:
    """Self-hash of an artifact with the named hash field(s) removed (§7)."""
    if not isinstance(obj, dict):
        raise ExecutionError("hash_without expects a mapping artifact")
    stripped = {k: v for k, v in obj.items() if k not in fields_to_drop}
    return sha256_text(canonical_json(stripped))


def compute_file_set_root(file_set: List[Dict[str, Any]]) -> str:
    """Flat ordered digest over the file set (§7).

    ``sha256(sorted(path + ":" + sha256hex(file) + "\\n"))`` where ``sha256hex``
    is the bare hex digest (the ``sha256:`` rendering prefix is stripped).
    """
    entries = []
    for item in file_set:
        path = item["path"]
        digest = str(item["sha256"])
        if digest.startswith("sha256:"):
            digest = digest[len("sha256:"):]
        entries.append(f"{path}:{digest}\n")
    return sha256_bytes("".join(sorted(entries)).encode("utf-8"))


def hash_file_set(files: List[Tuple[str, Path]]) -> List[Dict[str, str]]:
    """Build ``[{path, sha256}]`` from (rel_path, absolute_path) pairs."""
    return [{"path": rel, "sha256": sha256_file(abs_path)} for rel, abs_path in files]


# ---------------------------------------------------------------------------
# Snapshot sub-objects (§6.1)
# ---------------------------------------------------------------------------


@dataclass
class FileRef:
    path: str
    sha256: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FileRef":
        return cls(path=d["path"], sha256=d["sha256"])

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256}


@dataclass
class SkillPin:
    skill_id: str
    content_hash: str
    registry_version: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SkillPin":
        return cls(
            skill_id=d["skill_id"],
            content_hash=d["content_hash"],
            registry_version=d.get("registry_version", "0.1.0"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "content_hash": self.content_hash,
            "registry_version": self.registry_version,
        }


@dataclass
class GitAnchor:
    branch: str
    before_commit: str
    after_commit: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GitAnchor":
        return cls(
            branch=d.get("branch", ""),
            before_commit=d.get("before_commit", ""),
            after_commit=d.get("after_commit", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch": self.branch,
            "before_commit": self.before_commit,
            "after_commit": self.after_commit,
        }


@dataclass
class LedgerWindow:
    path: str
    seq_from: int
    seq_to: int
    chain_head_hash: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LedgerWindow":
        return cls(
            path=d["path"],
            seq_from=int(d["seq_from"]),
            seq_to=int(d["seq_to"]),
            chain_head_hash=d["chain_head_hash"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "seq_from": self.seq_from,
            "seq_to": self.seq_to,
            "chain_head_hash": self.chain_head_hash,
        }


@dataclass
class ResumeEligibility:
    eligible: bool
    requires_approval: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResumeEligibility":
        return cls(
            eligible=bool(d.get("eligible", False)),
            requires_approval=bool(d.get("requires_approval", False)),
            notes=d.get("notes", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eligible": self.eligible,
            "requires_approval": self.requires_approval,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# TaskSnapshot (§6.1)
# ---------------------------------------------------------------------------


@dataclass
class TaskSnapshot:
    """A hashed, commit-anchored resumable point for one execution."""

    snapshot_id: str
    project_id: str
    execution_id: str
    task_id: str
    agent_id: str
    created_at: str
    reason: SnapshotReason
    git: GitAnchor
    working_directory: str
    context_manifest_hash: Optional[str]
    file_set: List[FileRef] = field(default_factory=list)
    file_set_root_hash: str = ""
    skill_set: List[SkillPin] = field(default_factory=list)
    model_binding: Dict[str, Any] = field(default_factory=dict)
    ledger: Optional[LedgerWindow] = None
    resume_eligibility: ResumeEligibility = field(
        default_factory=lambda: ResumeEligibility(eligible=True)
    )
    supersedes: Optional[str] = None
    snapshot_hash: str = ""

    SNAPSHOT_HASH_FIELD = "snapshot_hash"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TaskSnapshot":
        return cls(
            snapshot_id=d["snapshot_id"],
            project_id=d["project_id"],
            execution_id=d["execution_id"],
            task_id=d["task_id"],
            agent_id=d["agent_id"],
            created_at=d["created_at"],
            reason=_as(d["reason"], SnapshotReason),
            git=GitAnchor.from_dict(d.get("git", {})),
            working_directory=d.get("working_directory", "."),
            context_manifest_hash=d.get("context_manifest_hash"),
            file_set=[FileRef.from_dict(f) for f in d.get("file_set", [])],
            file_set_root_hash=d.get("file_set_root_hash", ""),
            skill_set=[SkillPin.from_dict(s) for s in d.get("skill_set", [])],
            model_binding=dict(d.get("model_binding", {})),
            ledger=LedgerWindow.from_dict(d["ledger"]) if d.get("ledger") else None,
            resume_eligibility=ResumeEligibility.from_dict(
                d.get("resume_eligibility", {"eligible": False})
            ),
            supersedes=d.get("supersedes"),
            snapshot_hash=d.get("snapshot_hash", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "project_id": self.project_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "reason": _plain(self.reason),
            "git": self.git.to_dict(),
            "working_directory": self.working_directory,
            "context_manifest_hash": self.context_manifest_hash,
            "file_set": [f.to_dict() for f in self.file_set],
            "file_set_root_hash": self.file_set_root_hash,
            "skill_set": [s.to_dict() for s in self.skill_set],
            "model_binding": dict(self.model_binding),
            "ledger": self.ledger.to_dict() if self.ledger else None,
            "resume_eligibility": self.resume_eligibility.to_dict(),
            "supersedes": self.supersedes,
            "snapshot_hash": self.snapshot_hash,
        }

    def compute_hash(self) -> str:
        """Self-hash: canonical body with ``snapshot_hash`` excluded (§7)."""
        return hash_without(self.to_dict(), "snapshot_hash")

    def validate(self) -> List[str]:
        """Structural validation; returns a list of issues (empty = valid)."""
        issues: List[str] = []
        if not SNAPSHOT_ID_RE.match(self.snapshot_id):
            issues.append(f"bad snapshot_id: {self.snapshot_id!r}")
        if not PROJECT_ID_RE.match(self.project_id):
            issues.append(f"bad project_id: {self.project_id!r}")
        if not EXEC_ID_RE.match(self.execution_id):
            issues.append(f"bad execution_id: {self.execution_id!r}")
        if not AGENT_ID_RE.match(self.agent_id):
            issues.append(f"bad agent_id: {self.agent_id!r}")
        if _plain(self.reason) not in [r.value for r in SnapshotReason]:
            issues.append(f"bad reason: {self.reason!r}")
        if self.context_manifest_hash is not None and not SHA256_RE.match(
            str(self.context_manifest_hash)
        ):
            issues.append("context_manifest_hash must be sha256:<64-hex>")
        if self.snapshot_hash and not SHA256_RE.match(self.snapshot_hash):
            issues.append("snapshot_hash must be sha256:<64-hex>")
        if self.file_set_root_hash and not SHA256_RE.match(self.file_set_root_hash):
            issues.append("file_set_root_hash must be sha256:<64-hex>")
        for f in self.file_set:
            if not SHA256_RE.match(f.sha256):
                issues.append(f"file_set entry {f.path!r} has bad sha256")
        root = compute_file_set_root([f.to_dict() for f in self.file_set])
        if self.file_set_root_hash and root != self.file_set_root_hash:
            issues.append("file_set_root_hash does not match file_set contents")
        if self.ledger is not None:
            if not (1 <= self.ledger.seq_from <= self.ledger.seq_to):
                issues.append("bad ledger window")
            if self.ledger.chain_head_hash and not SHA256_RE.match(
                self.ledger.chain_head_hash
            ):
                issues.append("ledger.chain_head_hash must be sha256:<64-hex>")
        return issues


# ---------------------------------------------------------------------------
# ContextManifest (§6.2)
# ---------------------------------------------------------------------------


@dataclass
class ContextRef:
    """One tier entry: a reference plus its content fingerprint (§4.1)."""

    ref: str
    sha256: str
    skill_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContextRef":
        return cls(ref=d["ref"], sha256=d["sha256"], skill_id=d.get("skill_id"))

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"ref": self.ref, "sha256": self.sha256}
        if self.skill_id is not None:
            out["skill_id"] = self.skill_id
        return out


@dataclass
class ExcludedRef:
    """A trimmed item, recorded as excluded — never silently dropped (§4.1)."""

    ref: str
    reason: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExcludedRef":
        return cls(ref=d["ref"], reason=d["reason"])

    def to_dict(self) -> Dict[str, Any]:
        return {"ref": self.ref, "reason": self.reason}


@dataclass
class ContextManifest:
    manifest_id: str
    execution_id: str
    assembled_at: str
    tiers: Dict[str, List[ContextRef]] = field(default_factory=dict)
    excluded_for_budget: List[ExcludedRef] = field(default_factory=list)
    staleness: Staleness = Staleness.CURRENT
    manifest_hash: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContextManifest":
        tiers = {
            tier: [ContextRef.from_dict(r) for r in d.get("tiers", {}).get(tier, [])]
            for tier in TIER_ORDER
        }
        return cls(
            manifest_id=d["manifest_id"],
            execution_id=d["execution_id"],
            assembled_at=d["assembled_at"],
            tiers=tiers,
            excluded_for_budget=[
                ExcludedRef.from_dict(x) for x in d.get("excluded_for_budget", [])
            ],
            staleness=_as(d.get("staleness", Staleness.CURRENT), Staleness),
            manifest_hash=d.get("manifest_hash", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "execution_id": self.execution_id,
            "assembled_at": self.assembled_at,
            "tiers": {tier: [r.to_dict() for r in self.tiers.get(tier, [])] for tier in TIER_ORDER},
            "excluded_for_budget": [x.to_dict() for x in self.excluded_for_budget],
            "staleness": _plain(self.staleness),
            "manifest_hash": self.manifest_hash,
        }

    def compute_hash(self) -> str:
        """Self-hash: canonical body with ``manifest_hash`` excluded (§7)."""
        return hash_without(self.to_dict(), "manifest_hash")

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not MANIFEST_ID_RE.match(self.manifest_id):
            issues.append(f"bad manifest_id: {self.manifest_id!r}")
        if not EXEC_ID_RE.match(self.execution_id):
            issues.append(f"bad execution_id: {self.execution_id!r}")
        for tier in self.tiers:
            if tier not in TIER_ORDER:
                issues.append(f"unknown tier: {tier!r}")
        for tier, refs in sorted(self.tiers.items()):
            for r in refs:
                if not SHA256_RE.match(r.sha256):
                    issues.append(f"{tier} entry {r.ref!r} has bad sha256")
        if self.manifest_hash and not SHA256_RE.match(self.manifest_hash):
            issues.append("manifest_hash must be sha256:<64-hex>")
        return issues


# ---------------------------------------------------------------------------
# LedgerEntry (§6.3)
# ---------------------------------------------------------------------------


@dataclass
class LedgerEntry:
    """One JSONL ledger record with chain hashes (§6.3)."""

    seq: int
    execution_id: str
    event_type: str
    timestamp: str
    actor_agent: str
    payload: Dict[str, Any] = field(default_factory=dict)
    payload_hash: str = ""
    prev_hash: str = ""
    record_hash: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LedgerEntry":
        return cls(
            seq=int(d["seq"]),
            execution_id=d["execution_id"],
            event_type=d["event_type"],
            timestamp=d["timestamp"],
            actor_agent=d["actor_agent"],
            payload=dict(d.get("payload", {})),
            payload_hash=d.get("payload_hash", ""),
            prev_hash=d.get("prev_hash", ""),
            record_hash=d.get("record_hash", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "execution_id": self.execution_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "actor_agent": self.actor_agent,
            "payload": _plain(self.payload),
            "payload_hash": self.payload_hash,
            "prev_hash": self.prev_hash,
            "record_hash": self.record_hash,
        }

    def body_dict(self) -> Dict[str, Any]:
        """Record content covered by ``record_hash`` (hash field excluded)."""
        out = self.to_dict()
        out.pop("record_hash", None)
        return out

    def compute_record_hash(self) -> str:
        return sha256_text(canonical_json(self.body_dict()))

    def validate(self) -> List[str]:
        issues: List[str] = []
        if self.seq < 1:
            issues.append("seq must be >= 1")
        if not EXEC_ID_RE.match(self.execution_id):
            issues.append(f"bad execution_id: {self.execution_id!r}")
        if self.event_type not in [e.value for e in EventType]:
            issues.append(f"unknown event_type: {self.event_type!r}")
        if not AGENT_ID_RE.match(self.actor_agent):
            issues.append(f"bad actor_agent: {self.actor_agent!r}")
        effect = self.payload.get("effect")
        if effect is not None and effect not in [e.value for e in Effect]:
            issues.append(f"bad payload.effect: {effect!r}")
        if self.payload_hash and not SHA256_RE.match(self.payload_hash):
            issues.append("payload_hash must be sha256:<64-hex>")
        if self.prev_hash and not SHA256_RE.match(self.prev_hash):
            issues.append("prev_hash must be sha256:<64-hex>")
        if self.record_hash and not SHA256_RE.match(self.record_hash):
            issues.append("record_hash must be sha256:<64-hex>")
        return issues


__all__ = [
    "AGENT_ID_RE",
    "ContextManifest",
    "ContextRef",
    "DOC_ID_RE",
    "EXEC_ID_RE",
    "Effect",
    "EventType",
    "ExecutionError",
    "ExcludedRef",
    "FileRef",
    "GOVERNED_PREFIXES",
    "GitAnchor",
    "LedgerEntry",
    "LedgerWindow",
    "MANIFEST_ID_RE",
    "MAX_AUTO_RESUMES_PER_SIGNATURE",
    "PROJECT_ID_RE",
    "ResumeEligibility",
    "ResumeVerdict",
    "SHA256_RE",
    "SKILL_ID_RE",
    "SNAPSHOT_ID_RE",
    "SnapshotReason",
    "Staleness",
    "T0_BOOTSTRAP_FILES",
    "TIER_ORDER",
    "TIER_T0",
    "TIER_T1",
    "TIER_T2",
    "TIER_T3",
    "TERMINAL_EVENTS",
    "TaskSnapshot",
    "canonical_json",
    "compute_file_set_root",
    "hash_file_set",
    "hash_without",
    "is_governed",
    "sha256_bytes",
    "sha256_file",
    "sha256_text",
    "utc_now_stamp",
]
