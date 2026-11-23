"""Six-dimension skill drift detection with unapproved-version blocking.

Detects CONTENT, HASH, PERMISSION, METADATA, DEPENDENCY and VERSION drift by
comparing an approved baseline snapshot with the current on-disk state. Any
unapproved difference is BLOCKED; approved differences are reported as
PASS_WITH_OBSERVATIONS; an identical state is PASS.

The module is stdlib-only, does not execute skill content, and leaves every
existing runtime module untouched. Approval evidence is supplied explicitly
(never inferred from the changed artifact itself), matching ADR-002.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

from .validator import split_skill

_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__"})
_SIDECAR_FILES = frozenset({"permissions.json", "dependencies.json"})
_PERMISSIONS_FILE = "permissions.json"
_DEPENDENCIES_FILE = "dependencies.json"


class DriftKind(str, Enum):
    CONTENT = "content"
    HASH = "hash"
    PERMISSION = "permission"
    METADATA = "metadata"
    DEPENDENCY = "dependency"
    VERSION = "version"


class DriftVerdict(str, Enum):
    PASS = "PASS"
    PASS_WITH_OBSERVATIONS = "PASS_WITH_OBSERVATIONS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class DriftError(ValueError):
    """Raised when a baseline/current snapshot is structurally unusable."""


@dataclass
class DriftFinding:
    kind: str
    path: str
    expected: str
    actual: str
    approved_by: Optional[str] = None

    @property
    def approved(self) -> bool:
        return self.approved_by is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "expected": self.expected,
            "actual": self.actual,
            "approved": self.approved,
            "approved_by": self.approved_by,
        }


@dataclass
class DriftReport:
    target: str = ""
    findings: List[DriftFinding] = field(default_factory=list)
    verdict: str = DriftVerdict.PASS.value

    @property
    def ok(self) -> bool:
        return self.verdict in (DriftVerdict.PASS.value, DriftVerdict.PASS_WITH_OBSERVATIONS.value)

    @property
    def blocked(self) -> bool:
        return self.verdict == DriftVerdict.BLOCKED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "verdict": self.verdict,
            "ok": self.ok,
            "blocked": self.blocked,
            "findings": [f.to_dict() for f in self.findings],
        }


def classify(findings: Iterable[DriftFinding]) -> str:
    """Fail closed: one unapproved change blocks, approved changes are observed."""
    findings = list(findings)
    if any(not f.approved for f in findings):
        return DriftVerdict.BLOCKED.value
    if findings:
        return DriftVerdict.PASS_WITH_OBSERVATIONS.value
    return DriftVerdict.PASS.value


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------


def _iter_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for child in sorted(root.rglob("*")):
        rel = child.relative_to(root)
        if any(part.startswith(".") or part in _SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if child.is_file() and child.name not in _SIDECAR_FILES:
            files.append(child)
    return files


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def snapshot_dir(path: Union[str, Path]) -> Dict[str, Any]:
    """Build a deterministic, non-executing snapshot of a skill directory."""
    root = Path(path)
    snapshot: Dict[str, Any] = {
        "version": "0.0.0",
        "files": {},
        "content": {},
        "permissions": {},
        "metadata": {},
        "dependencies": [],
    }
    if not root.is_dir():
        raise DriftError("skill directory not found: %s" % root)

    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        try:
            frontmatter, _body = split_skill(skill_md.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            frontmatter = {"parse-error": str(exc)}
        metadata = dict(frontmatter)
        nested = dict(metadata.get("metadata") or {})
        opencode = dict(nested.get("opencode") or {})
        version = metadata.get("version") or opencode.get("version") or "0.0.0"
        snapshot["version"] = str(version)
        snapshot["metadata"] = metadata

    version_file = root / "VERSION"
    if version_file.is_file():
        snapshot["version"] = version_file.read_text(encoding="utf-8").strip() or "0.0.0"

    for child in _iter_files(root):
        rel = child.relative_to(root).as_posix()
        raw = child.read_bytes()
        snapshot["files"][rel] = _sha256(raw)
        try:
            snapshot["content"][rel] = raw.decode("utf-8")
        except UnicodeDecodeError:
            snapshot["content"][rel] = "<binary:%s>" % _sha256(raw)

    permissions = _read_json(root / _PERMISSIONS_FILE, {})
    snapshot["permissions"] = permissions if isinstance(permissions, dict) else {"value": permissions}
    dependencies = _read_json(root / _DEPENDENCIES_FILE, [])
    snapshot["dependencies"] = dependencies
    return snapshot


def baseline_from_entry(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive an approved baseline from a registry row (no on-disk access)."""
    versioning = dict(row.get("versioning") or {})
    integrity = dict(row.get("integrity") or {})
    license_info = dict(row.get("license") or {})
    source = dict(row.get("source") or {})
    return {
        "version": "%s#%s" % (
            versioning.get("registry_version", "0.0.0"),
            versioning.get("local_rev", 0),
        ),
        "files": dict(integrity.get("file_hashes") or {}),
        "content": {},
        "permissions": dict(row.get("permissions") or {}),
        "metadata": {
            "lifecycle": row.get("lifecycle", ""),
            "license": {
                "scope": license_info.get("scope", ""),
                "spdx": license_info.get("spdx", ""),
            },
            "source": {
                "type": source.get("type", ""),
                "commit_sha": source.get("commit_sha"),
            },
        },
        "dependencies": row.get("dependencies") or [],
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _require_snapshot(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DriftError("%s snapshot must be a JSON object" % name)
    return value


def _display(value: Any) -> str:
    if value is None:
        return "<absent>"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def _diff_mapping(
    kind: DriftKind,
    expected_map: Mapping[str, Any],
    actual_map: Mapping[str, Any],
    approvals: Sequence[Any],
) -> List[DriftFinding]:
    findings: List[DriftFinding] = []
    for key in sorted(set(expected_map) | set(actual_map)):
        in_expected = key in expected_map
        in_actual = key in actual_map
        if in_expected and in_actual and expected_map[key] == actual_map[key]:
            continue
        expected = expected_map[key] if in_expected else None
        actual = actual_map[key] if in_actual else None
        findings.append(
            _finding(kind, key, _display(expected), _display(actual), approvals)
        )
    return findings


def _dependencies(values: Any) -> Dict[str, str]:
    """Normalize a dependency list or mapping to comparable name -> version."""
    if isinstance(values, Mapping):
        return {str(k): _display(v) for k, v in values.items()}
    if isinstance(values, (list, tuple)):
        out: Dict[str, str] = {}
        for item in values:
            text = str(item)
            name, sep, version = text.partition("==")
            out[name] = version if sep else _display(text)
        return out
    return {}


def _finding(
    kind: DriftKind,
    path: str,
    expected: str,
    actual: str,
    approvals: Sequence[Any],
) -> DriftFinding:
    return DriftFinding(
        kind=kind.value,
        path=path,
        expected=expected,
        actual=actual,
        approved_by=_match_approval(kind.value, path, expected, actual, approvals),
    )


def _match_approval(
    kind: str,
    path: str,
    expected: str,
    actual: str,
    approvals: Sequence[Any],
) -> Optional[str]:
    """Match an explicit approval record; wildcards are allowed, never inferred."""
    for approval in approvals:
        if isinstance(approval, str):
            parts = approval.split(":", 2)
            if parts[0] not in ("*", kind):
                continue
            if len(parts) < 2 or parts[1] in ("*", ""):
                return approval
            if parts[1] != path:
                continue
            if len(parts) == 3:
                source, arrow, target = parts[2].partition("->")
                if arrow and source and source != expected:
                    continue
                if arrow and target and target != actual:
                    continue
            return approval
        if isinstance(approval, Mapping):
            if approval.get("kind") not in (None, "*", kind):
                continue
            if approval.get("path") not in (None, "*", path):
                continue
            if approval.get("from") is not None and str(approval["from"]) != expected:
                continue
            if approval.get("to") is not None and str(approval["to"]) != actual:
                continue
            return str(approval.get("approved_by") or approval.get("adr") or "approval-record")
    return None


def detect_drift(
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    approvals: Optional[Sequence[Any]] = None,
    target: str = "",
) -> DriftReport:
    """Compare two snapshots across all six dimensions."""
    expected = _require_snapshot(baseline, "baseline")
    actual = _require_snapshot(current, "current")
    approvals = list(approvals or [])
    findings: List[DriftFinding] = []

    # VERSION - an unapproved version change is the hardest block.
    if str(expected.get("version", "")) != str(actual.get("version", "")):
        findings.append(
            _finding(
                DriftKind.VERSION,
                "version",
                _display(expected.get("version")),
                _display(actual.get("version")),
                approvals,
            )
        )

    # HASH and CONTENT - both a digest change and a byte-level change are
    # reported so a reviewer sees corroboration rather than a single signal.
    findings.extend(_diff_mapping(DriftKind.HASH, expected.get("files") or {}, actual.get("files") or {}, approvals))
    findings.extend(_diff_mapping(DriftKind.CONTENT, expected.get("content") or {}, actual.get("content") or {}, approvals))

    # PERMISSION and METADATA.
    findings.extend(
        _diff_mapping(DriftKind.PERMISSION, expected.get("permissions") or {}, actual.get("permissions") or {}, approvals)
    )
    findings.extend(_diff_mapping(DriftKind.METADATA, expected.get("metadata") or {}, actual.get("metadata") or {}, approvals))

    # DEPENDENCY - order-insensitive, version-aware.
    findings.extend(
        _diff_mapping(
            DriftKind.DEPENDENCY,
            _dependencies(expected.get("dependencies")),
            _dependencies(actual.get("dependencies")),
            approvals,
        )
    )

    return DriftReport(target=target, findings=findings, verdict=classify(findings))


def check_directory(
    path: Union[str, Path],
    baseline: Mapping[str, Any],
    *,
    approvals: Optional[Sequence[Any]] = None,
) -> DriftReport:
    """Snapshot ``path`` and compare it against an approved baseline."""
    return detect_drift(baseline, snapshot_dir(path), approvals=approvals, target=str(path))


# ---------------------------------------------------------------------------
# CLI: ``python -m orchestration.skills.drift``
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skills-drift", description="Six-dimension skill drift check")
    parser.add_argument("--dir", help="skill directory to snapshot")
    parser.add_argument("--baseline", required=True, help="approved baseline snapshot (JSON object)")
    parser.add_argument("--current", help="current snapshot (JSON object); skips --dir snapshot")
    parser.add_argument("--approvals", help="JSON array of explicit approval records")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        approvals = json.loads(Path(args.approvals).read_text(encoding="utf-8")) if args.approvals else []
        if args.current:
            current = json.loads(Path(args.current).read_text(encoding="utf-8"))
            target = str(args.current)
        elif args.dir:
            current = snapshot_dir(args.dir)
            target = str(args.dir)
        else:
            build_parser().error("one of --dir or --current is required")
            return 1
        report = detect_drift(baseline, current, approvals=approvals, target=target)
    except (OSError, ValueError, DriftError) as exc:
        print(json.dumps({"verdict": DriftVerdict.FAIL.value, "ok": False, "error": str(exc)}, sort_keys=True))
        return 1

    exit_code = 0 if report.ok else (2 if report.blocked else 1)
    payload = report.to_dict()
    payload["exit_code"] = exit_code
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
