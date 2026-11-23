"""Offline validation and in-house lint for the skills registry (V-1..V-3, X-rules).

No external dependencies: a small JSON Schema (2020-12 subset) evaluator and a
minimal YAML-frontmatter reader cover exactly the constructs used by
``schemas/skill-registry.schema.json`` and OpenCode Plane A.

Enforcement boundary (D-3): Plane B is never mistaken for runtime enforcement.
A registry ``deny`` only takes effect once the derived config is generated and
G6 verifies it on the installed build (OQ-4).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import (
    AGENT_IDS,
    AGENT_ID_RE,
    KNOWN_COLLISION_IDS,
    RULE_STRICTNESS,
    SHA256_RE,
    SKILL_ID_RE,
    CompatVerdict,
    LicenseScope,
    Lifecycle,
    Rule,
    SecurityVerdict,
    SkillEntry,
    ValidationReport,
)
from .registry import Registry, render_permissions

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "skill-registry.schema.json"

# Plane A: the only frontmatter fields OpenCode V2 interprets. Governance
# fields are forbidden here (R-3 / D-3) and belong in Plane B.
PLANE_A_TOP_LEVEL = frozenset({"name", "description", "metadata"})
PLANE_A_METADATA = frozenset({"opencode"})
PLANE_A_OPENCODE = frozenset({"autoinvoke", "disable-model-invocation"})

ALLOWED_COMPAT_DOCS = frozenset({"SKILLS_COMPATIBILITY_MATRIX.md"})
ALLOWED_SECURITY_DOCS = frozenset({"SKILLS_SECURITY_AUDIT.md"})
ADVANCED_LIFECYCLES = frozenset({Lifecycle.APPROVED, Lifecycle.STAGED, Lifecycle.ACTIVE})

_RELATIVE_PATH_RE = re.compile(r"(?:/|\.[a-z0-9]{1,8}(?:$|\s))", re.IGNORECASE)
_MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//")


# ---------------------------------------------------------------------------
# Minimal JSON Schema (2020-12 subset) evaluator
# ---------------------------------------------------------------------------


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError("only local $ref pointers are supported: %s" % ref)
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError("$ref does not point to a schema object: %s" % ref)
    return node


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _schema_errors(
    instance: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str = "$",
    errors: Optional[List[str]] = None,
    depth: int = 0,
) -> List[str]:
    if errors is None:
        errors = []
    if depth > 64:
        errors.append("%s: schema evaluation too deep" % path)
        return errors

    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], root)
        _schema_errors(instance, resolved, root, path, errors, depth + 1)
        # 2020-12 allows siblings of $ref; validate them too (if any).
        siblings = {k: v for k, v in schema.items() if k != "$ref"}
        if siblings:
            _schema_errors(instance, siblings, root, path, errors, depth + 1)
        return errors

    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, t) for t in allowed):
            errors.append("%s: expected type %s, got %s" % (path, "/".join(allowed), type(instance).__name__))
            return errors  # further keyword checks would be meaningless

    if "const" in schema and instance != schema["const"]:
        errors.append("%s: expected const %r" % (path, schema["const"]))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r not in enum %s" % (path, instance, schema["enum"]))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: string shorter than minLength %s" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: string longer than maxLength %s" % (path, schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: %r fails pattern %s" % (path, instance, schema["pattern"]))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum %s" % (path, schema["minimum"]))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("%s: array shorter than minItems %s" % (path, schema["minItems"]))
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in instance}) != len(instance):
            errors.append("%s: array items are not unique" % path)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                _schema_errors(item, item_schema, root, "%s[%d]" % (path, i), errors, depth + 1)

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append("%s: missing required property %r" % (path, req))
        props = schema.get("properties", {})
        for key, value in instance.items():
            child = "%s.%s" % (path, key)
            if key in props:
                _schema_errors(value, props[key], root, child, errors, depth + 1)
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append("%s: unexpected property %r" % (child, key))
                elif isinstance(extra, dict):
                    _schema_errors(value, extra, root, child, errors, depth + 1)
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append("%s: object has fewer than %s properties" % (path, schema["minProperties"]))

    for sub in schema.get("allOf", []):
        _schema_errors(instance, sub, root, path, errors, depth + 1)

    if "anyOf" in schema:
        if not any(_is_valid(instance, sub, root) for sub in schema["anyOf"]):
            errors.append("%s: does not match any anyOf branch" % path)

    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if _is_valid(instance, sub, root))
        if matches != 1:
            errors.append("%s: matches %d oneOf branches (expected 1)" % (path, matches))

    if "if" in schema:
        if _is_valid(instance, schema["if"], root):
            if "then" in schema:
                _schema_errors(instance, schema["then"], root, path, errors, depth + 1)
        elif "else" in schema:
            _schema_errors(instance, schema["else"], root, path, errors, depth + 1)

    return errors


def _is_valid(instance: Any, schema: Dict[str, Any], root: Dict[str, Any]) -> bool:
    return not _schema_errors(instance, schema, root)


def validate_json_schema(instance: Any, schema: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable schema violations (empty == valid)."""
    return _schema_errors(instance, schema, schema)


def load_schema(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    target = Path(path) if path else DEFAULT_SCHEMA_PATH
    return json.loads(target.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Minimal YAML frontmatter reader (Plane A subset)
# ---------------------------------------------------------------------------


def _scalar(text: str) -> Any:
    text = text.strip()
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if text in ("null", "~", ""):
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _parse_simple_yaml(lines: List[str]) -> Dict[str, Any]:
    """Parse the indentation-based YAML subset used by SKILL.md frontmatter."""
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        if text.startswith("- "):
            if isinstance(parent, list):
                item = text[2:].strip()
                if ":" in item and not item.startswith(("'", '"')):
                    key, _, value = item.partition(":")
                    parent.append({key.strip(): _scalar(value)})
                else:
                    parent.append(_scalar(item))
            i += 1
            continue

        if ":" not in text:
            raise ValueError("invalid frontmatter line: %r" % raw)
        key, _, value = text.partition(":")
        key, value = key.strip(), value.strip()

        if value in (">", "|", ">-", "|-"):
            block: List[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip():
                    block.append("")
                    j += 1
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt_indent <= indent:
                    break
                block.append(nxt.strip())
                j += 1
            if value.startswith(">"):
                parent[key] = " ".join(p for p in block if p)
            else:
                parent[key] = "\n".join(block).strip()
            i = j
            continue

        if value == "":
            # Look ahead: a "- " child means a list, otherwise a nested map.
            child: Any = {}
            for nxt in lines[i + 1 :]:
                if not nxt.strip() or nxt.strip().startswith("#"):
                    continue
                if nxt.strip().startswith("- ") and (len(nxt) - len(nxt.lstrip(" "))) > indent:
                    child = []
                break
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value)
        i += 1
    return root


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse a SKILL.md frontmatter block; raise ValueError if malformed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md is missing its frontmatter opening '---'")
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        raise ValueError("SKILL.md frontmatter is not terminated by '---'")
    return _parse_simple_yaml(lines[1:end])


def split_skill(text: str) -> Tuple[Dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return parse_frontmatter(text), "\n".join(lines[idx + 1 :])
    return {}, text


def effective_autoinvoke(frontmatter: Dict[str, Any]) -> bool:
    """OpenCode V2: autoinvoke wins if both controls are present."""
    oc = (frontmatter.get("metadata") or {}).get("opencode") or {}
    if "autoinvoke" in oc:
        return bool(oc["autoinvoke"])
    if "disable-model-invocation" in oc:
        return not bool(oc["disable-model-invocation"])
    return True


def validate_frontmatter(frontmatter: Dict[str, Any], report: Optional[ValidationReport] = None) -> ValidationReport:
    """V-2: Plane A must contain only OpenCode-interpreted fields."""
    report = report or ValidationReport(target="frontmatter")
    for key in frontmatter:
        if key not in PLANE_A_TOP_LEVEL:
            report.error(
                "V-2",
                "Plane A forbids governance field %r; keep governance in Plane B (registry)" % key,
                "$.%s" % key,
            )
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        report.error("V-2", "description is required and must be non-empty (else never advertised)", "$.description")
    name = frontmatter.get("name")
    if name is not None and not isinstance(name, str):
        report.error("V-2", "name is display-only and must be a string", "$.name")

    metadata = frontmatter.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            report.error("V-2", "metadata must be a mapping", "$.metadata")
        else:
            for key in metadata:
                if key not in PLANE_A_METADATA:
                    report.error("V-2", "unknown metadata namespace %r" % key, "$.metadata.%s" % key)
            oc = metadata.get("opencode")
            if oc is not None:
                if not isinstance(oc, dict):
                    report.error("V-2", "metadata.opencode must be a mapping", "$.metadata.opencode")
                else:
                    for key in oc:
                        if key not in PLANE_A_OPENCODE:
                            report.error("V-2", "unsupported metadata.opencode field %r" % key, "$.metadata.opencode.%s" % key)
                    for key in PLANE_A_OPENCODE:
                        if key in oc and not isinstance(oc[key], bool):
                            report.error("V-2", "%s must be boolean" % key, "$.metadata.opencode.%s" % key)
                    if "autoinvoke" in oc and "disable-model-invocation" in oc:
                        report.warn("V-2", "both autoinvoke and disable-model-invocation present; autoinvoke wins", "$.metadata.opencode")
    return report


def validate_plane_a(skill_path: Union[str, Path], expected_autoinvoke: bool) -> ValidationReport:
    """V-2 + X-10: parse a SKILL.md and cross-check Plane A against Plane B."""
    path = Path(skill_path)
    report = ValidationReport(target=str(path))
    if not path.is_file():
        report.error("V-1", "SKILL.md not found", str(path))
        return report
    try:
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        report.error("V-2", "frontmatter parse failed: %s" % exc, str(path))
        return report
    validate_frontmatter(frontmatter, report)
    if effective_autoinvoke(frontmatter) != bool(expected_autoinvoke):
        report.error(
            "X-10",
            "Plane A effective autoinvoke %s != Plane B permissions.autoinvoke %s"
            % (effective_autoinvoke(frontmatter), bool(expected_autoinvoke)),
            str(path),
        )
    return report


# ---------------------------------------------------------------------------
# V-1 structural validation
# ---------------------------------------------------------------------------


def find_references(body: str) -> List[str]:
    """Collect relative supporting-file paths referenced by a skill body."""
    candidates: List[str] = []
    for regex in (_MD_LINK_RE, _CODE_SPAN_RE):
        candidates.extend(regex.findall(body))
    refs: List[str] = []
    for raw in candidates:
        token = raw.strip().split("#", 1)[0].split("?", 1)[0]
        if not token or _URL_RE.match(token) or token.startswith("@"):
            continue
        if "/" in token or _RELATIVE_PATH_RE.search(token):
            if token not in refs:
                refs.append(token)
    return refs


def validate_skill_directory(path: Union[str, Path], expected_id: Optional[str] = None) -> ValidationReport:
    """V-1: directory form, path-derived ID, layout limits, referenced files."""
    root = Path(path)
    report = ValidationReport(target=str(root))
    if not root.is_dir():
        report.error("V-1", "skill path is not a directory", str(root))
        return report
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        report.error("V-1", "directory form '<id>/SKILL.md' is mandatory", str(skill_md))
        return report

    skill_id = root.name
    if not SKILL_ID_RE.match(skill_id) or len(skill_id) > 64:
        report.error("V-1", "path-derived ID %r is not lowercase-kebab 1-64" % skill_id, str(root))
    if expected_id and skill_id != expected_id:
        report.error("V-1", "path-derived ID %r != expected %r" % (skill_id, expected_id), str(root))

    for child in root.rglob("*"):
        rel = child.relative_to(root)
        if len(rel.parts) > 6:
            report.error("V-1", "discovery depth exceeds 6 levels: %s" % rel, str(root))
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts[:-1]):
            report.error("V-1", "hidden dir / node_modules in skill tree: %s" % rel, str(root))

    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        report.error("V-1", "SKILL.md is not UTF-8: %s" % exc, str(skill_md))
        return report
    frontmatter, body = split_skill(text)
    report.extend(validate_frontmatter(frontmatter))
    for ref in find_references(body):
        target = (root / ref).resolve()
        if not target.is_file():
            report.error("V-1", "referenced supporting file does not exist: %s" % ref, str(skill_md))
    return report


# ---------------------------------------------------------------------------
# X-rules (in-house lint of Plane B)
# ---------------------------------------------------------------------------


def _has_human_approval(entry: SkillEntry) -> bool:
    for item in entry.versioning.history:
        evidence = (item.evidence or "").lower()
        if item.event == "permission-change" and ("human" in evidence or "approval" in evidence or "approved" in evidence):
            return True
        if item.adr and evidence and "human" in evidence:
            return True
    return False


def lint_entry(entry: SkillEntry, report: Optional[ValidationReport] = None) -> ValidationReport:
    """Apply cross-field consistency rules X-1..X-11 to one registry row."""
    report = report or ValidationReport(target=entry.skill_id)
    sid = entry.skill_id
    lifecycle = entry.lifecycle
    enabled = entry.enabled_in
    advanced = lifecycle in ADVANCED_LIFECYCLES

    # X-1 - ID equals basename of library + enablement paths.
    if Path(entry.library_path).name != sid:
        report.error("X-1", "library_path basename != skill_id", "$.skills.%s.library_path" % sid)
    for path in enabled:
        if Path(path).name != sid:
            report.error("X-1", "enabled_in basename != skill_id: %s" % path, "$.skills.%s.enabled_in" % sid)

    # X-2 - lifecycle x enablement x permission guards.
    if lifecycle in (Lifecycle.CANDIDATE, Lifecycle.REVIEWED, Lifecycle.APPROVED, Lifecycle.RETIRED) and enabled:
        report.error("X-2", "%s rows must have empty enabled_in" % lifecycle.value, "$.skills.%s.enabled_in" % sid)
    if lifecycle in (Lifecycle.STAGED, Lifecycle.ACTIVE) and not enabled:
        report.error("X-2", "%s rows must have a promotion copy" % lifecycle.value, "$.skills.%s.enabled_in" % sid)
    if lifecycle == Lifecycle.STAGED and entry.permissions.rule != Rule.ASK:
        report.error("X-2", "STAGED requires ask for all agents", "$.skills.%s.permissions.rule" % sid)
    if lifecycle == Lifecycle.SUSPENDED:
        if entry.permissions.rule != Rule.DENY:
            report.error("X-2", "SUSPENDED kill-switch requires deny everywhere", "$.skills.%s.permissions.rule" % sid)
        if entry.permissions.per_agent_overrides:
            report.error("X-2", "no override may relax a SUSPENDED deny", "$.skills.%s.permissions.per_agent_overrides" % sid)

    # X-3 - license exposure.
    spdx = (entry.license.spdx or "").upper()
    if spdx.startswith("AGPL") and lifecycle in (Lifecycle.STAGED, Lifecycle.ACTIVE):
        report.error("X-3", "AGPL-licensed skill must never be STAGED/ACTIVE", "$.skills.%s.license.spdx" % sid)
    if entry.license.scope in (LicenseScope.UNVERIFIED, LicenseScope.REPO_CLAIM) and advanced:
        report.error("X-3", "unverified / repo-level-claim license cannot be APPROVED+", "$.skills.%s.license.scope" % sid)
    if spdx.startswith("APACHE") and not any("NOTICE" in n.upper() for n in entry.license.notice_files):
        report.error("X-3", "Apache-2.0 requires a NOTICE file to be listed", "$.skills.%s.license.notice_files" % sid)

    # X-4 - verdict to lifecycle guards.
    compat = entry.verdicts.compatibility.verdict
    security = entry.verdicts.security.verdict
    behavior = entry.verdicts.behavior_review.verdict
    if advanced:
        if compat not in (CompatVerdict.COMPATIBLE, CompatVerdict.COMPATIBLE_AFTER_ADAPTATION):
            report.error("X-4", "APPROVED+ requires a COMPATIBLE compatibility verdict", "$.skills.%s.verdicts.compatibility" % sid)
        if security == SecurityVerdict.ACCEPT:
            pass
        elif security == SecurityVerdict.ACCEPT_CONDITIONAL:
            if not entry.verdicts.security.conditions_closed:
                report.error("X-4", "ACCEPT-CONDITIONAL requires closed conditions for APPROVED+", "$.skills.%s.verdicts.security" % sid)
        else:
            report.error("X-4", "APPROVED+ requires ACCEPT / ACCEPT-CONDITIONAL security verdict", "$.skills.%s.verdicts.security" % sid)
        if behavior != "PASS":
            report.error("X-4", "APPROVED+ requires G5 behavior_review PASS", "$.skills.%s.verdicts.behavior_review" % sid)
    if security in (SecurityVerdict.HOLD, SecurityVerdict.REJECT) and lifecycle not in (
        Lifecycle.CANDIDATE, Lifecycle.REVIEWED, Lifecycle.SUSPENDED, Lifecycle.RETIRED
    ):
        report.error("X-4", "HOLD/REJECT verdict blocks APPROVED/STAGED/ACTIVE", "$.skills.%s.lifecycle" % sid)

    # X-5 - row-level cross-references (OBS-1).
    cdoc = entry.verdicts.compatibility.doc
    sdoc = entry.verdicts.security.doc
    if cdoc not in ALLOWED_COMPAT_DOCS:
        report.error("X-5", "compatibility doc cross-ref must resolve to SKILLS_COMPATIBILITY_MATRIX.md", "$.skills.%s.verdicts.compatibility.doc" % sid)
    if sdoc not in ALLOWED_SECURITY_DOCS:
        report.error("X-5", "security doc cross-ref must resolve to SKILLS_SECURITY_AUDIT.md", "$.skills.%s.verdicts.security.doc" % sid)
    if advanced and entry.verdicts.compatibility.row == "TBD":
        report.error("X-5", "row-level compatibility cross-ref is still TBD", "$.skills.%s.verdicts.compatibility.row" % sid)

    # X-6 - integrity of the complete vendored directory.
    if "SKILL.md" not in entry.integrity.file_hashes:
        report.error("X-6", "file_hashes must include SKILL.md", "$.skills.%s.integrity.file_hashes" % sid)
    if not entry.integrity.complete_directory and len(entry.integrity.file_hashes) > 1:
        report.error("X-6", "supporting files exist but complete_directory is false", "$.skills.%s.integrity.complete_directory" % sid)

    # X-7 - source provenance / pin consistency.
    source = entry.source
    pin_fields = (source.repo, source.canonical_url, source.upstream_path, source.commit_sha)
    if source.type == "in-house":
        if any(field is not None for field in pin_fields) or entry.versioning.upstream_pin is not None:
            report.error("X-7", "in-house rows must not carry upstream pin fields", "$.skills.%s.source" % sid)
    else:
        if any(field is None for field in pin_fields):
            report.error("X-7", "non-in-house rows require all upstream pin fields", "$.skills.%s.source" % sid)
        if not entry.versioning.upstream_pin or "@" not in entry.versioning.upstream_pin:
            report.error("X-7", "upstream_pin must be <repo>@<sha>", "$.skills.%s.versioning.upstream_pin" % sid)
        if not all(SHA256_RE.match(v) for v in entry.integrity.file_hashes.values()):
            report.error("X-7", "every file hash must be sha256:<64 lowercase hex>", "$.skills.%s.integrity.file_hashes" % sid)
    if source.type == "adapted":
        if entry.integrity.local_modifications == "none" or entry.versioning.local_rev < 1:
            report.error("X-7", "adapted rows require local_modifications and local_rev >= 1", "$.skills.%s.versioning" % sid)

    # X-8 - permissions vs verdicts.
    if entry.permissions.risk_class != entry.verdicts.security.risk_class:
        report.error("X-8", "permissions.risk_class != verdicts.security.risk_class", "$.skills.%s.permissions.risk_class" % sid)
    default = {"A": Rule.ALLOW, "B": Rule.ASK, "C": Rule.DENY}[entry.permissions.risk_class.value]
    rule = entry.permissions.rule
    if rule != default and RULE_STRICTNESS[rule] < RULE_STRICTNESS[default] and not _has_human_approval(entry):
        report.error("X-8", "loosening rule beyond class default needs human-approved history evidence", "$.skills.%s.permissions.rule" % sid)
    for agent, override in entry.permissions.per_agent_overrides.items():
        if RULE_STRICTNESS[override] < RULE_STRICTNESS[default] and not _has_human_approval(entry):
            report.error("X-8", "per-agent override loosens class default without approval: %s" % agent, "$.skills.%s.permissions.per_agent_overrides" % sid)

    # X-9 - enablement is project layer only.
    for path in enabled:
        if path != ".opencode/skills/%s" % sid:
            report.error("X-9", "enabled_in must be exactly .opencode/skills/<skill_id>: %s" % path, "$.skills.%s.enabled_in" % sid)

    # X-11 - assignment to the verified catalog / orphan rule.
    for agent in entry.assignment.agents:
        if entry.assignment.scope == "factory-agents":
            if not AGENT_ID_RE.match(agent) or agent not in AGENT_IDS:
                report.error("X-11", "unknown factory agent id: %s" % agent, "$.skills.%s.assignment.agents" % sid)
        elif AGENT_ID_RE.match(agent):
            report.error("X-11", "generated-project scope must not list factory agents: %s" % agent, "$.skills.%s.assignment.agents" % sid)
    if lifecycle in (Lifecycle.STAGED, Lifecycle.ACTIVE) and not entry.assignment.agents:
        report.error("X-11", "enabled skill has no consumer agent", "$.skills.%s.assignment.agents" % sid)

    return report


def check_uniqueness(registry: Registry, report: Optional[ValidationReport] = None) -> ValidationReport:
    """V-3: ID uniqueness and silent-resurrection guard across enablement paths."""
    report = report or ValidationReport(target="uniqueness")
    seen_ids: Dict[str, str] = {}
    seen_paths: Dict[str, str] = {}
    for entry in registry:
        sid = entry.skill_id
        if sid in seen_ids:
            report.error("V-3", "duplicate skill_id across registry: %s" % sid, "$.skills.%s" % sid)
        seen_ids[sid] = sid
        for path in entry.enabled_in:
            if path in seen_paths and seen_paths[path] != sid:
                report.error(
                    "V-3",
                    "enablement path %s claimed by both %s and %s (silent resurrection)"
                    % (path, seen_paths[path], sid),
                    "$.skills.%s.enabled_in" % sid,
                )
            seen_paths[path] = sid
        if sid in KNOWN_COLLISION_IDS and entry.enabled_in:
            report.warn(
                "COLLISION-WATCH",
                "%s is a known cross-repo collision ID; prove no second copy at V-3" % sid,
                "$.skills.%s" % sid,
            )
    return report


def check_derived_config(registry: Union[Registry, Dict[str, Any]], config_path: Union[str, Path]) -> ValidationReport:
    """I-3 / X-12: regenerate-and-diff the derived skill permissions."""
    path = Path(config_path)
    report = ValidationReport(target=str(path))
    expected = render_permissions(registry)
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error("X-12", "cannot read derived config: %s" % exc, str(path))
        return report
    if actual != expected:
        try:
            semantically_equal = json.loads(actual) == json.loads(expected)
        except (ValueError, TypeError):
            semantically_equal = False
        if semantically_equal:
            report.error("X-12", "derived config drift: bytes differ from registry regeneration", str(path))
        else:
            report.error("X-12", "derived config differs from registry regeneration", str(path))
    return report


def validate_registry(
    registry: Union[Registry, Dict[str, Any]],
    schema_path: Optional[Union[str, Path]] = None,
    repo_root: Optional[Union[str, Path]] = None,
) -> ValidationReport:
    """Full offline validation: JSON Schema + X-rules + V-3 uniqueness."""
    data = registry.to_dict() if isinstance(registry, Registry) else dict(registry)
    report = ValidationReport(target="registry")

    schema = load_schema(schema_path)
    for message in validate_json_schema(data, schema):
        report.error("SCHEMA", message)

    try:
        typed = registry if isinstance(registry, Registry) else Registry.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        report.error("MODEL", "cannot materialize typed registry: %s" % exc)
        return report

    report.extend(check_uniqueness(typed))
    for entry in typed:
        lint_entry(entry, report)

    if repo_root is not None:
        root = Path(repo_root)
        for entry in typed:
            skill_dir = root / entry.library_path
            if not skill_dir.is_dir():
                report.error("X-6", "library_path missing on disk: %s" % entry.library_path, entry.skill_id)
                continue
            for ref, digest in entry.integrity.file_hashes.items():
                target = skill_dir / ref
                if not target.is_file():
                    report.error("X-6", "hashed file missing: %s" % ref, entry.skill_id)
                elif "sha256:" in digest:
                    import hashlib

                    actual = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
                    if actual != digest:
                        report.error("X-6", "hash mismatch for %s" % ref, entry.skill_id)
            report.extend(validate_plane_a(skill_dir / "SKILL.md", entry.permissions.autoinvoke))
    return report


__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "check_derived_config",
    "check_uniqueness",
    "effective_autoinvoke",
    "find_references",
    "lint_entry",
    "load_schema",
    "parse_frontmatter",
    "split_skill",
    "validate_frontmatter",
    "validate_json_schema",
    "validate_plane_a",
    "validate_registry",
    "validate_skill_directory",
]
