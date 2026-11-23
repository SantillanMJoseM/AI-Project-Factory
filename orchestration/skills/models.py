"""Data models for the AI-Project-Factory Skills governance runtime (Plane B).

This module is pure stdlib. It encodes the field groups, controlled
vocabularies and append-only history defined by
``docs/skills/SKILLS_REGISTRY_SCHEMA.md`` (SKILLS-REGISTRY-SCHEMA-0001) and
``docs/skills/SKILLS_GOVERNANCE.md`` (SKILLS-GOVERNANCE-0001).

Enforcement boundary: these objects are *governance metadata*. OpenCode V2
interprets none of them; in-house lint and gates G0-G8 enforce them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------


class Tier(str, Enum):
    GLOBAL = "global"
    SHARED = "shared"
    SPECIALTY = "specialty"
    PROJECT = "project"


class Category(str, Enum):
    AGENT_PROCESS = "agent-process"
    ARCHITECTURE_DESIGN = "architecture-design"
    BACKEND_API = "backend-api"
    CODE_QUALITY_REVIEW = "code-quality-review"
    DATABASE_DATA = "database-data"
    DEBUGGING_PERFORMANCE = "debugging-performance"
    DEVOPS_DELIVERY = "devops-delivery"
    DOCS_KNOWLEDGE = "docs-knowledge"
    GIT_VCS = "git-vcs"
    QUALITY_GATE = "quality-gate"
    REQUIREMENTS_ENGINEERING = "requirements-engineering"
    SECURITY_COMPLIANCE = "security-compliance"
    TESTING = "testing"
    UI_UX_ACCESSIBILITY = "ui-ux-accessibility"


class SourceType(str, Enum):
    VENDORED = "vendored-upstream"
    ADAPTED = "adapted"
    IN_HOUSE = "in-house"
    HTTP_CATALOG = "http-catalog"


class LicenseScope(str, Enum):
    PER_FILE = "per-file-verified"
    REPO_CLAIM = "repo-level-claim"
    UNVERIFIED = "unverified"
    IN_HOUSE = "in-house"


class CompatVerdict(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_AFTER_ADAPTATION = "COMPATIBLE-AFTER-ADAPTATION"
    INCOMPATIBLE = "INCOMPATIBLE"
    PENDING = "PENDING"


class SecurityVerdict(str, Enum):
    ACCEPT = "ACCEPT"
    ACCEPT_CONDITIONAL = "ACCEPT-CONDITIONAL"
    HOLD = "HOLD"
    REJECT = "REJECT"
    PENDING = "PENDING"


class RiskClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class Rule(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class BehaviorVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class Lifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class ReauditTrigger(str, Enum):
    UPSTREAM_DRIFT = "upstream-drift"
    OPENCODE_BUMP = "opencode-version-bump"
    PERMISSION_CHANGE = "permission-change"
    CONTENT_EDIT = "content-edit"
    SECURITY_RECLASSIFICATION = "security-reclassification"
    CONFIG_DRIFT = "config-drift"


class HistoryEvent(str, Enum):
    REGISTERED = "registered"
    ADOPTED_VIA_ADR = "adopted-via-ADR"
    PROMOTED = "promoted"
    STAGED = "staged"
    ACTIVATED = "activated"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    RE_PINNED = "re-pinned"
    ADAPTED = "adapted"
    PERMISSION_CHANGE = "permission-change"
    VERDICT_CHANGE = "verdict-change"
    RE_AUDITED = "re-audited"


# ---------------------------------------------------------------------------
# Standing constants (from the registry proposal / architecture)
# ---------------------------------------------------------------------------

SKILL_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
AGENT_ID_RE = re.compile(r"^AG-[0-9]{3}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")

#: Verified 18-agent catalog (agents/ + .opencode/agents/).
AGENT_IDS = frozenset("AG-%03d" % i for i in range(1, 19))

#: The 11 known cross-repo collision pairs (registry proposal §5). A second
#: copy of any of these IDs is an automatic G2 hard fail.
KNOWN_COLLISION_IDS = frozenset(
    {
        "architecture-decision-records",
        "microservices-patterns",
        "code-review-excellence",
        "api-design-principles",
        "auth-implementation-patterns",
        "secrets-management",
        "sql-optimization-patterns",
        "database-migration",
        "e2e-testing-patterns",
        "git-advanced-workflows",
        "systematic-debugging",
    }
)

DEFAULT_RULE_BY_RISK = {"A": Rule.ALLOW, "B": Rule.ASK, "C": Rule.DENY}
RULE_STRICTNESS = {Rule.ALLOW: 0, Rule.ASK: 1, Rule.DENY: 2}

ALLOWED_TRANSITIONS = {
    Lifecycle.CANDIDATE: {Lifecycle.REVIEWED, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.REVIEWED: {Lifecycle.APPROVED, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.APPROVED: {Lifecycle.STAGED, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.STAGED: {Lifecycle.ACTIVE, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.ACTIVE: {Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    # Suspension is not a pause button: re-entry is CANDIDATE (full G1-G7).
    Lifecycle.SUSPENDED: {Lifecycle.CANDIDATE, Lifecycle.RETIRED},
    Lifecycle.RETIRED: set(),
}

EVENT_BY_LIFECYCLE = {
    Lifecycle.CANDIDATE: HistoryEvent.REGISTERED,
    Lifecycle.REVIEWED: HistoryEvent.RE_AUDITED,
    Lifecycle.APPROVED: HistoryEvent.ADOPTED_VIA_ADR,
    Lifecycle.STAGED: HistoryEvent.STAGED,
    Lifecycle.ACTIVE: HistoryEvent.ACTIVATED,
    Lifecycle.SUSPENDED: HistoryEvent.SUSPENDED,
    Lifecycle.RETIRED: HistoryEvent.RETIRED,
}


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


# ---------------------------------------------------------------------------
# Validation result containers
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    code: str
    message: str
    path: str = ""
    severity: str = "error"

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class ValidationReport:
    issues: List[Issue] = field(default_factory=list)
    target: str = ""

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str, path: str = "") -> None:
        self.issues.append(Issue(code, message, path, "error"))

    def warn(self, code: str, message: str, path: str = "") -> None:
        self.issues.append(Issue(code, message, path, "warning"))

    def extend(self, other: "ValidationReport") -> "ValidationReport":
        self.issues.extend(other.issues)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "ok": self.ok,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Registry entry sub-objects
# ---------------------------------------------------------------------------


@dataclass
class Source:
    type: SourceType
    repo: Optional[str] = None
    canonical_url: Optional[str] = None
    upstream_path: Optional[str] = None
    commit_sha: Optional[str] = None
    cloned: str = "TBD"
    approval: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Source":
        return cls(
            type=_as(d["type"], SourceType),
            repo=d.get("repo"),
            canonical_url=d.get("canonical_url"),
            upstream_path=d.get("upstream_path"),
            commit_sha=d.get("commit_sha"),
            cloned=d.get("cloned", "TBD"),
            approval=dict(d["approval"]) if d.get("approval") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"type": _plain(self.type)}
        for key in ("repo", "canonical_url", "upstream_path", "commit_sha"):
            if getattr(self, key) is not None:
                out[key] = getattr(self, key)
        out["cloned"] = self.cloned
        if self.approval is not None:
            out["approval"] = dict(self.approval)
        return out


@dataclass
class License:
    scope: LicenseScope
    spdx: str
    notice_files: List[str] = field(default_factory=list)
    verified_by: str = "G3"
    verified_at: str = "TBD"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "License":
        return cls(
            scope=_as(d["scope"], LicenseScope),
            spdx=d["spdx"],
            notice_files=list(d.get("notice_files", [])),
            verified_by=d.get("verified_by", "G3"),
            verified_at=d.get("verified_at", "TBD"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": _plain(self.scope),
            "spdx": self.spdx,
            "notice_files": list(self.notice_files),
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
        }


@dataclass
class Integrity:
    file_hashes: Dict[str, str] = field(default_factory=dict)
    complete_directory: bool = False
    local_modifications: str = "none"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Integrity":
        return cls(
            file_hashes=dict(d.get("file_hashes", {})),
            complete_directory=bool(d.get("complete_directory", False)),
            local_modifications=d.get("local_modifications", "none"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_hashes": dict(self.file_hashes),
            "complete_directory": self.complete_directory,
            "local_modifications": self.local_modifications,
        }


@dataclass
class Compatibility:
    verdict: CompatVerdict
    doc: str
    row: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Compatibility":
        return cls(_as(d["verdict"], CompatVerdict), d["doc"], d["row"])

    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": _plain(self.verdict), "doc": self.doc, "row": self.row}


@dataclass
class Security:
    verdict: SecurityVerdict
    risk_class: RiskClass
    doc: str
    conditions_closed: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Security":
        return cls(
            _as(d["verdict"], SecurityVerdict),
            _as(d["risk_class"], RiskClass),
            d["doc"],
            list(d.get("conditions_closed", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": _plain(self.verdict),
            "risk_class": _plain(self.risk_class),
            "doc": self.doc,
            "conditions_closed": list(self.conditions_closed),
        }


@dataclass
class BehaviorReview:
    verdict: BehaviorVerdict
    gate: str = "G5"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BehaviorReview":
        return cls(_as(d["verdict"], BehaviorVerdict), d.get("gate", "G5"))

    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": _plain(self.verdict), "gate": self.gate}


@dataclass
class Verdicts:
    compatibility: Compatibility
    security: Security
    behavior_review: BehaviorReview

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Verdicts":
        return cls(
            Compatibility.from_dict(d["compatibility"]),
            Security.from_dict(d["security"]),
            BehaviorReview.from_dict(d["behavior_review"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatibility": self.compatibility.to_dict(),
            "security": self.security.to_dict(),
            "behavior_review": self.behavior_review.to_dict(),
        }


@dataclass
class Permissions:
    risk_class: RiskClass
    rule: Rule
    per_agent_overrides: Dict[str, Rule] = field(default_factory=dict)
    autoinvoke: bool = False

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Permissions":
        return cls(
            risk_class=_as(d["risk_class"], RiskClass),
            rule=_as(d["rule"], Rule),
            per_agent_overrides={k: _as(v, Rule) for k, v in d.get("per_agent_overrides", {}).items()},
            autoinvoke=bool(d.get("autoinvoke", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_class": _plain(self.risk_class),
            "rule": _plain(self.rule),
            "per_agent_overrides": {k: _plain(v) for k, v in self.per_agent_overrides.items()},
            "autoinvoke": self.autoinvoke,
        }


@dataclass
class Assignment:
    agents: List[str]
    scope: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Assignment":
        return cls(list(d.get("agents", [])), d["scope"])

    def to_dict(self) -> Dict[str, Any]:
        return {"agents": list(self.agents), "scope": self.scope}


@dataclass
class HistoryEntry:
    event: HistoryEvent
    date: str = "TBD"
    gates: List[str] = field(default_factory=list)
    adr: Optional[str] = None
    actor: Optional[str] = None
    evidence: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HistoryEntry":
        return cls(
            event=_as(d["event"], HistoryEvent),
            date=d.get("date", "TBD"),
            gates=list(d.get("gates", [])),
            adr=d.get("adr"),
            actor=d.get("actor"),
            evidence=d.get("evidence"),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"event": _plain(self.event), "date": self.date}
        if self.gates:
            out["gates"] = list(self.gates)
        for key in ("adr", "actor", "evidence"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


@dataclass
class Versioning:
    upstream_pin: Optional[str]
    local_rev: int
    registry_version: str
    history: List[HistoryEntry]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Versioning":
        return cls(
            upstream_pin=d.get("upstream_pin"),
            local_rev=int(d.get("local_rev", 0)),
            registry_version=d.get("registry_version", "0.1.0"),
            history=[HistoryEntry.from_dict(h) for h in d.get("history", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "upstream_pin": self.upstream_pin,
            "local_rev": self.local_rev,
            "registry_version": self.registry_version,
            "history": [h.to_dict() for h in self.history],
        }


@dataclass
class SkillEntry:
    skill_id: str
    tier: Tier
    category: Category
    library_path: str
    enabled_in: List[str]
    source: Source
    license: License
    integrity: Integrity
    verdicts: Verdicts
    permissions: Permissions
    assignment: Assignment
    versioning: Versioning
    lifecycle: Lifecycle
    reaudit_triggers: List[ReauditTrigger]
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SkillEntry":
        return cls(
            skill_id=d["skill_id"],
            tier=_as(d["tier"], Tier),
            category=_as(d["category"], Category),
            library_path=d["library_path"],
            enabled_in=list(d.get("enabled_in", [])),
            source=Source.from_dict(d["source"]),
            license=License.from_dict(d["license"]),
            integrity=Integrity.from_dict(d["integrity"]),
            verdicts=Verdicts.from_dict(d["verdicts"]),
            permissions=Permissions.from_dict(d["permissions"]),
            assignment=Assignment.from_dict(d["assignment"]),
            versioning=Versioning.from_dict(d["versioning"]),
            lifecycle=_as(d["lifecycle"], Lifecycle),
            reaudit_triggers=[_as(t, ReauditTrigger) for t in d.get("reaudit_triggers", [])],
            notes=d.get("notes"),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "skill_id": self.skill_id,
            "tier": _plain(self.tier),
            "category": _plain(self.category),
            "library_path": self.library_path,
            "enabled_in": list(self.enabled_in),
            "source": self.source.to_dict(),
            "license": self.license.to_dict(),
            "integrity": self.integrity.to_dict(),
            "verdicts": self.verdicts.to_dict(),
            "permissions": self.permissions.to_dict(),
            "assignment": self.assignment.to_dict(),
            "versioning": self.versioning.to_dict(),
            "lifecycle": _plain(self.lifecycle),
            "reaudit_triggers": _plain(self.reaudit_triggers),
        }
        if self.notes is not None:
            out["notes"] = self.notes
        return out


__all__ = [
    "Category",
    "CompatVerdict",
    "AGENT_IDS",
    "AGENT_ID_RE",
    "ALLOWED_TRANSITIONS",
    "Assignment",
    "BehaviorVerdict",
    "DEFAULT_RULE_BY_RISK",
    "EVENT_BY_LIFECYCLE",
    "HistoryEntry",
    "HistoryEvent",
    "Integrity",
    "Issue",
    "KNOWN_COLLISION_IDS",
    "License",
    "LicenseScope",
    "Lifecycle",
    "Permissions",
    "ReauditTrigger",
    "RiskClass",
    "Rule",
    "RULE_STRICTNESS",
    "SHA256_RE",
    "SKILL_ID_RE",
    "Security",
    "SecurityVerdict",
    "SkillEntry",
    "Source",
    "SourceType",
    "Tier",
    "ValidationReport",
    "Verdicts",
    "Versioning",
]
