"""Formal execution contract for a single skill invocation (Stage 0.1 addition).

The schema ``schemas/skill-task-contract.schema.json`` fixes the eleven
mandatory fields; this module materializes them as a dataclass and adds the
cross-field safety rules TC-1..TC-6 that a pure JSON Schema cannot express.

No existing runtime module is modified: the JSON Schema subset evaluator and
the ``ValidationReport`` container are reused from ``validator`` / ``models``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from .models import AGENT_ID_RE, AGENT_IDS, SKILL_ID_RE, ValidationReport
from .validator import validate_json_schema

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "skill-task-contract.schema.json"

REQUIRED_FIELDS = (
    "skill",
    "version",
    "executor_agent",
    "objective",
    "inputs",
    "authorized_files",
    "allowed_tools",
    "restrictions",
    "expected_result",
    "acceptance_criteria",
    "evidence",
)

#: Tools that can change state or cross a trust boundary. Allowing one is
#: legal only with an explicit approval restriction (ADR-002 supervised
#: autonomy).
RESTRICTED_TOOLS = frozenset(
    {"shell", "bash", "execute", "exec", "delete", "network", "deploy", "sudo"}
)
APPROVAL_MARKERS = ("approval", "approved")

_SENSITIVE_PATH_PARTS = frozenset(
    {".git", ".env", ".ssh", ".aws", ".npmrc", ".git-credentials", "id_rsa", "credentials", "keychain"}
)
_PLACEHOLDERS = frozenset({"", "tbd", "n/a", "none", "unknown", "todo", "-"})
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


class TaskContractError(ValueError):
    """Raised when a contract cannot be materialized from a mapping/file."""


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDERS


def _is_safe_relative_path(value: str) -> bool:
    """Authorized files must be repo-relative, non-traversing, non-sensitive."""
    candidate = value.strip().replace("\\", "/")
    if not candidate or candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        return False
    parts = [part for part in candidate.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        return False
    if any(part.lower() in _SENSITIVE_PATH_PARTS for part in parts):
        return False
    return True


@dataclass
class TaskContract:
    """One auditable execution contract for a skill invocation."""

    skill: str
    version: str
    executor_agent: str
    objective: str
    inputs: List[str] = field(default_factory=list)
    authorized_files: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    expected_result: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    contract_id: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskContract":
        """Materialize a contract; unknown keys are ignored (schema rejects them)."""
        try:
            return cls(
                skill=str(data.get("skill", "")),
                version=str(data.get("version", "")),
                executor_agent=str(data.get("executor_agent", "")),
                objective=str(data.get("objective", "")),
                inputs=list(data.get("inputs") or []),
                authorized_files=list(data.get("authorized_files") or []),
                allowed_tools=list(data.get("allowed_tools") or []),
                restrictions=list(data.get("restrictions") or []),
                expected_result=str(data.get("expected_result", "")),
                acceptance_criteria=list(data.get("acceptance_criteria") or []),
                evidence=list(data.get("evidence") or []),
                contract_id=str(data.get("contract_id", "") or ""),
            )
        except (TypeError, ValueError) as exc:
            raise TaskContractError("cannot materialize TaskContract: %s" % exc) from exc

    @classmethod
    def load(cls, path: Union[str, Path]) -> "TaskContract":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "skill": self.skill,
            "version": self.version,
            "executor_agent": self.executor_agent,
            "objective": self.objective,
            "inputs": list(self.inputs),
            "authorized_files": list(self.authorized_files),
            "allowed_tools": list(self.allowed_tools),
            "restrictions": list(self.restrictions),
            "expected_result": self.expected_result,
            "acceptance_criteria": list(self.acceptance_criteria),
            "evidence": list(self.evidence),
        }
        if self.contract_id:
            out["contract_id"] = self.contract_id
        return out

    def validate(self, schema_path: Optional[Union[str, Path]] = None) -> ValidationReport:
        """Validate this contract (JSON Schema + TC-1..TC-6)."""
        return validate_contract(self.to_dict(), schema_path=schema_path)


def validate_contract(
    data: Mapping[str, Any],
    *,
    schema_path: Optional[Union[str, Path]] = None,
) -> ValidationReport:
    """Validate a contract mapping and return an append-only-style report."""
    report = ValidationReport(target=str(data.get("contract_id") or data.get("skill") or "contract"))

    # A dataclass always emits every key, so check the *raw* mapping first to
    # keep missing-field detection honest.
    for key in REQUIRED_FIELDS:
        if key not in data:
            report.error("SCHEMA", "missing required property %r" % key, "$.%s" % key)

    schema_file = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    for message in validate_json_schema(dict(data), schema):
        report.error("SCHEMA", message)

    try:
        contract = TaskContract.from_dict(data)
    except TaskContractError as exc:
        report.error("MODEL", str(exc))
        return report

    # TC-1 - executor must be a known factory agent.
    if not AGENT_ID_RE.match(contract.executor_agent) or contract.executor_agent not in AGENT_IDS:
        report.error("TC-1", "executor_agent %r is not a verified factory agent" % contract.executor_agent, "$.executor_agent")

    # TC-2 - authorized files are safe repo-relative paths.
    for path in contract.authorized_files:
        if not isinstance(path, str) or not _is_safe_relative_path(path):
            report.error("TC-2", "unsafe authorized file path %r" % path, "$.authorized_files")

    # TC-3 - state-changing tools need an explicit approval restriction.
    has_approval = any(
        marker in r.lower()
        for r in contract.restrictions
        if isinstance(r, str)
        for marker in APPROVAL_MARKERS
    )
    for tool in contract.allowed_tools:
        if isinstance(tool, str) and tool.lower() in RESTRICTED_TOOLS and not has_approval:
            report.error(
                "TC-3",
                "restricted tool %r requires an explicit approval restriction" % tool,
                "$.allowed_tools",
            )

    # TC-4 - no blank/placeholder prose or restriction entries.
    for key in ("objective", "expected_result"):
        value = getattr(contract, key)
        if not isinstance(value, str) or _is_placeholder(value):
            report.error("TC-4", "%s must be a non-placeholder statement" % key, "$.%s" % key)
    for key in ("inputs", "restrictions", "evidence", "acceptance_criteria"):
        for item in getattr(contract, key):
            if not isinstance(item, str) or _is_placeholder(item):
                report.error("TC-4", "%s contains a blank/placeholder entry" % key, "$.%s" % key)

    # TC-5 - the skill reference and version must be well formed and pinned.
    if not SKILL_ID_RE.match(contract.skill):
        report.error("TC-5", "skill %r is not a lowercase-kebab skill id" % contract.skill, "$.skill")
    if not _VERSION_RE.match(contract.version):
        report.error("TC-5", "version %r is not a pinned semantic version" % contract.version, "$.version")

    # TC-6 - acceptance criteria are the auditable proof of completion; an
    # empty evidence list is allowed at drafting time and becomes an
    # observation rather than a hard failure.
    if not contract.acceptance_criteria:
        report.error("TC-6", "at least one acceptance criterion is required", "$.acceptance_criteria")
    if not contract.evidence:
        report.warn("TC-6", "no evidence artifacts declared yet; fill before execution", "$.evidence")

    return report


__all__ = [
    "APPROVAL_MARKERS",
    "DEFAULT_SCHEMA_PATH",
    "REQUIRED_FIELDS",
    "RESTRICTED_TOOLS",
    "TaskContract",
    "TaskContractError",
    "validate_contract",
]
