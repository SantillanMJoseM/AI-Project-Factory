"""V5 license-compliance controls for skills (std-only, offline, fail-closed).

This module adds the *license governance plane* to the Stage 0 skills runtime.
It does not change any existing runtime module; it consumes the same registry
row shape documented in ``docs/skills/SKILLS_REGISTRY_SCHEMA.md`` and returns
the factory audit vocabulary (``PASS`` / ``PASS_WITH_OBSERVATIONS`` /
``FAIL`` / ``BLOCKED``) used by the quality gates.

V5 controls
-----------
V5-IDENTIFY       identify the governing SPDX license (and corroborate with files)
V5-MISSING        no declared license => BLOCKED
V5-INCOMPATIBLE   copyleft / copyleft-like license incompatible with the factory
V5-MIXED          more than one distinct license governs one skill
V5-ATTRIBUTION    required copyright/license/NOTICE evidence is absent
V5-REDISTRIBUTION license restricts redistribution of the vendored skill
V5-PROVENANCE     license scope / upstream pin cannot substantiate the claim

Verdict precedence: BLOCKED > FAIL > PASS_WITH_OBSERVATIONS > PASS.
Only V5-MISSING produces BLOCKED; an absent or untrustworthy declaration is
never silently treated as a permissive license.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------


class LicenseVerdict(str, Enum):
    PASS = "PASS"
    PASS_WITH_OBSERVATIONS = "PASS_WITH_OBSERVATIONS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


#: Licenses the factory can identify. Anything else is an observation, never
#: an automatic PASS (fail-closed identification).
KNOWN_LICENSES = frozenset(
    {
        "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
        "0BSD", "Unlicense", "CC0-1.0", "MPL-2.0",
        "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
        "AGPL-3.0-only", "AGPL-3.0-or-later", "LGPL-2.1-only", "LGPL-3.0-only",
        "LGPL-3.0-or-later", "SSPL-1.0", "BUSL-1.1",
        "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0",
        "CC-BY-ND-4.0", "PROPRIETARY", "UNLICENSED",
    }
)

#: Values that mean "there is no license declaration" (V5-MISSING).
MISSING_LICENSE_TOKENS = frozenset({"", "TBD", "UNKNOWN", "N/A", "NONE", "NO LICENSE", "UNLICENSED"})

#: Licenses whose terms are incompatible with an internal/unlicensed factory
#: posture (the repository ships no LICENSE file of its own).
INCOMPATIBLE_LICENSES = frozenset(
    {
        "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
        "AGPL-3.0-only", "AGPL-3.0-or-later", "LGPL-2.1-only", "LGPL-3.0-only",
        "LGPL-3.0-or-later", "SSPL-1.0", "BUSL-1.1", "CC-BY-SA-4.0",
    }
)

#: Licenses that forbid or condition redistribution of a vendored copy.
REDISTRIBUTION_RESTRICTED = frozenset(
    {
        "PROPRIETARY", "UNLICENSED", "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0",
        "CC-BY-ND-4.0", "SSPL-1.0", "BUSL-1.1",
    }
)

#: Licenses that require retaining copyright and license/NOTICE text.
ATTRIBUTION_REQUIRED = frozenset(
    {
        "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
        "MPL-2.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-4.0",
        "CC-BY-NC-SA-4.0", "CC-BY-ND-4.0",
    }
)

_ALIASES = {
    "mit license": "MIT",
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "gpl v3": "GPL-3.0-only",
    "gpl v2": "GPL-2.0-only",
    "agpl v3": "AGPL-3.0-only",
    "cc by 4.0": "CC-BY-4.0",
}

_ALIAS_RE = re.compile(r"(?i)SPDX-License-Identifier\s*:\s*\(?([A-Za-z0-9.+-]+(?:\s+(?:OR|AND)\s+[A-Za-z0-9.+-]+)*)\)?")
_KNOWN_RE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(name) for name in sorted(KNOWN_LICENSES, key=len, reverse=True)) + r")\b"
)
_APACHE_RE = re.compile(r"(?i)Apache\s+License[, ]+Version\s*2\.0")
_GPL_RE = re.compile(
    r"(?i)GNU\s+(?:GENERAL\s+PUBLIC\s+LICENSE|AFFERO\s+GENERAL\s+PUBLIC\s+LICENSE)"
    r"(?:\s+Version\s*([23](?:\.\d)?))?"
)

_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__"})


def _normalize(token: str) -> str:
    """Normalize one SPDX token (alias resolution, no semantic weakening)."""
    token = token.strip().strip("()").rstrip(".,;")
    return _ALIASES.get(token.lower(), token)


def _split_expression(expression: str) -> List[str]:
    """Return the individual SPDX tokens of an expression (``OR`` kept sane)."""
    parts = re.split(r"\s+(?:OR|AND)\s+|\s*[,;]\s*", expression, flags=re.IGNORECASE)
    return [_normalize(p) for p in parts if p.strip()]


def identify_license(text: str) -> List[str]:
    """Identify SPDX licenses in a text blob without executing it.

    An explicit ``SPDX-License-Identifier: MIT OR Apache-2.0`` expression is
    returned as one identity (a dual-license choice), whereas two separate
    identifiers are returned as two identities (V5-MIXED).
    """
    found: List[str] = []

    for match in _ALIAS_RE.finditer(text):
        expression = " ".join(_normalize(part) for part in match.group(1).split())
        if expression not in found:
            found.append(expression)

    for match in _APACHE_RE.finditer(text):
        if "Apache-2.0" not in found:
            found.append("Apache-2.0")

    for match in _GPL_RE.finditer(text):
        version = (match.group(1) or "3").strip()
        name = "AGPL-3.0-only" if "AFFERO" in match.group(0).upper() else "GPL-%s-only" % version
        if name not in found:
            found.append(name)

    for match in _KNOWN_RE.finditer(text):
        name = _normalize(match.group(1))
        # Do not add a bare token that is already covered by an expression.
        if any(name in _split_expression(expr) for expr in found):
            continue
        if name not in found:
            found.append(name)

    return sorted(found)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    code: str
    message: str
    severity: str = "error"  # blocker | error | warning | info
    source: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "severity": self.severity, "source": self.source, "message": self.message}


@dataclass
class LicenseReport:
    target: str = ""
    license_id: Optional[str] = None
    scope: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)
    verdict: str = LicenseVerdict.PASS.value

    @property
    def ok(self) -> bool:
        return self.verdict in (LicenseVerdict.PASS.value, LicenseVerdict.PASS_WITH_OBSERVATIONS.value)

    @property
    def observations(self) -> List[str]:
        return [f.code for f in self.findings if f.severity == "warning"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "license_id": self.license_id,
            "scope": self.scope,
            "verdict": self.verdict,
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "observations": list(self.observations),
        }


def classify(findings: Iterable[Finding]) -> str:
    """Fail-closed verdict: blocker => BLOCKED, error => FAIL, warning => OBS."""
    severities = {f.severity for f in findings}
    if "blocker" in severities:
        return LicenseVerdict.BLOCKED.value
    if "error" in severities:
        return LicenseVerdict.FAIL.value
    if "warning" in severities:
        return LicenseVerdict.PASS_WITH_OBSERVATIONS.value
    return LicenseVerdict.PASS.value


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def _license_files(root: Path) -> List[str]:
    names: List[str] = []
    for child in sorted(root.rglob("*")):
        rel = child.relative_to(root)
        if any(part.startswith(".") or part in _SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if child.is_file():
            names.append(rel.as_posix())
    return names


def _evidence_from_dir(root: Path) -> List[str]:
    """Read every UTF-8 file once and collect identified licenses."""
    detected: List[str] = []
    for rel in _license_files(root):
        try:
            text = (root / rel).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            # Unreadable bytes cannot corroborate a license; fail closed by
            # simply not counting them as evidence.
            continue
        for name in identify_license(text):
            if name not in detected:
                detected.append(name)
    return sorted(detected)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return []


def check_license(
    record: Mapping[str, Any],
    *,
    target: str = "",
    redistributable: bool = False,
    skill_dir: Optional[Union[str, Path]] = None,
) -> LicenseReport:
    """Apply the seven V5 controls to one registry row (or license record).

    ``record`` may be a whole registry row (``license``, ``source`` keys) or a
    partial mapping containing just those keys. Optional ``detected_licenses``
    supplies on-disk corroboration; when ``skill_dir`` is given and no such
    list exists, the directory is scanned offline for SPDX identifiers.
    """
    lic = dict(record.get("license") or {})
    source = dict(record.get("source") or {})
    scope = str(lic.get("scope") or "").strip()
    declared = _normalize(str(lic.get("spdx") or ""))

    detected = _as_list(record.get("detected_licenses"))
    if not detected and skill_dir is not None:
        detected = _evidence_from_dir(Path(skill_dir))
    detected = [_normalize(x) for x in detected if x and x.upper() not in MISSING_LICENSE_TOKENS]

    report = LicenseReport(target=target or str(record.get("skill_id", "")), license_id=declared or None, scope=scope or None)

    # V5-MISSING: an absent/unknown declaration is never a permissive default.
    is_missing = declared.upper() in MISSING_LICENSE_TOKENS
    in_house_policy_gap = is_missing and scope == "in-house"
    if is_missing:
        if in_house_policy_gap:
            report.findings.append(
                Finding(
                    "V5-PROVENANCE",
                    "in-house license policy is undefined (ES-8); spdx=%s is not an identified license" % (declared or "<empty>"),
                    "warning",
                    "license.spdx",
                )
            )
        else:
            report.findings.append(
                Finding(
                    "V5-MISSING",
                    "no license declared (spdx=%s); adoption is BLOCKED" % (declared or "<empty>"),
                    "blocker",
                    "license.spdx",
                )
            )
            if detected:
                report.license_id = detected[0]
                report.findings.append(
                    Finding(
                        "V5-IDENTIFY",
                        "license identified from files (%s) but not declared in governance metadata" % ", ".join(detected),
                        "warning",
                        "license.spdx",
                    )
                )
            report.verdict = classify(report.findings)
            return report

    # Collapse identities: an SPDX expression counts as a single choice.
    identities: List[str] = [declared] + [d for d in detected if d != declared]
    tokens: List[str] = []
    for identity in identities:
        for token in _split_expression(identity):
            if token and token not in tokens:
                tokens.append(token)

    # V5-IDENTIFY
    for identity in identities:
        parts = _split_expression(identity)
        unknown = [
            p for p in parts
            if p not in KNOWN_LICENSES and p.upper() not in MISSING_LICENSE_TOKENS
        ]
        if unknown:
            report.findings.append(
                Finding(
                    "V5-IDENTIFY",
                    "unrecognized SPDX identifier(s): %s" % ", ".join(unknown),
                    "warning",
                    "license.spdx",
                )
            )
    if detected and declared not in detected and not any(
        set(_split_expression(declared)) & set(_split_expression(d)) for d in detected
    ):
        report.findings.append(
            Finding(
                "V5-IDENTIFY",
                "declared license %s is not corroborated by on-disk evidence (%s)" % (declared, ", ".join(detected)),
                "warning",
                "license.spdx",
            )
        )
    if scope == "per-file-verified" and detected and declared in detected:
        pass  # corroborated: no observation

    # V5-MIXED
    if len(identities) > 1:
        report.findings.append(
            Finding(
                "V5-MIXED",
                "mixed licenses govern one skill: %s" % ", ".join(identities),
                "error",
                "license.spdx",
            )
        )

    # V5-INCOMPATIBLE
    for token in tokens:
        if token in INCOMPATIBLE_LICENSES:
            report.findings.append(
                Finding(
                    "V5-INCOMPATIBLE",
                    "license %s is incompatible with the factory posture" % token,
                    "error",
                    "license.spdx",
                )
            )

    # V5-ATTRIBUTION
    notice_files = _as_list(lic.get("notice_files"))
    has_notice = any(
        name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "LICENCE")) for name in notice_files
    )
    for token in tokens:
        if token in ATTRIBUTION_REQUIRED:
            if not has_notice:
                report.findings.append(
                    Finding(
                        "V5-ATTRIBUTION",
                        "license %s requires a LICENSE/NOTICE file; notice_files=%s" % (token, notice_files or []),
                        "error",
                        "license.notice_files",
                    )
                )
            if token == "Apache-2.0" and not any("NOTICE" in n.upper() for n in notice_files):
                report.findings.append(
                    Finding(
                        "V5-ATTRIBUTION",
                        "Apache-2.0 requires a NOTICE file to be retained",
                        "error",
                        "license.notice_files",
                    )
                )
    if has_notice and not record.get("attribution"):
        report.findings.append(
            Finding(
                "V5-ATTRIBUTION",
                "copyright/attribution holder is not recorded explicitly",
                "warning",
                "attribution",
            )
        )

    # V5-REDISTRIBUTION
    for token in tokens:
        if token in REDISTRIBUTION_RESTRICTED:
            report.findings.append(
                Finding(
                    "V5-REDISTRIBUTION",
                    "license %s restricts redistribution of a vendored copy" % token,
                    "error",
                    "license.spdx",
                )
            )
        elif redistributable and token in INCOMPATIBLE_LICENSES:
            report.findings.append(
                Finding(
                    "V5-REDISTRIBUTION",
                    "redistribution requested but license %s imposes copyleft obligations" % token,
                    "error",
                    "license.spdx",
                )
            )

    # V5-PROVENANCE
    if scope == "unverified":
        report.findings.append(
            Finding("V5-PROVENANCE", "license scope is unverified; claim cannot be trusted", "error", "license.scope")
        )
    elif scope == "repo-level-claim":
        report.findings.append(
            Finding(
                "V5-PROVENANCE",
                "repo-level license claim is not per-file evidence",
                "warning",
                "license.scope",
            )
        )
    elif scope == "per-file-verified":
        if not lic.get("verified_by") or str(lic.get("verified_at") or "TBD") == "TBD":
            report.findings.append(
                Finding(
                    "V5-PROVENANCE",
                    "per-file license claim lacks verified_by / verified_at evidence",
                    "warning",
                    "license.verified_by",
                )
            )

    source_type = str(source.get("type") or "")
    pin_fields = ("repo", "canonical_url", "upstream_path", "commit_sha")
    if source_type in ("vendored-upstream", "adapted", "http-catalog"):
        missing_pin = [name for name in pin_fields if not source.get(name)]
        if missing_pin:
            report.findings.append(
                Finding(
                    "V5-PROVENANCE",
                    "upstream provenance pin incomplete: %s" % ", ".join(missing_pin),
                    "warning",
                    "source",
                )
            )
    if scope == "in-house" and source_type in ("vendored-upstream", "adapted", "http-catalog"):
        report.findings.append(
            Finding(
                "V5-PROVENANCE",
                "in-house license scope claimed for an externally sourced skill",
                "error",
                "license.scope",
            )
        )

    report.verdict = classify(report.findings)
    return report


def check_skill_dir(
    path: Union[str, Path],
    *,
    record: Optional[Mapping[str, Any]] = None,
    redistributable: bool = False,
) -> LicenseReport:
    """Check a skill directory: on-disk SPDX evidence + optional registry row."""
    root = Path(path)
    merged: Dict[str, Any] = dict(record or {})
    merged["detected_licenses"] = _evidence_from_dir(root)
    return check_license(merged, target=str(root), redistributable=redistributable)


__all__ = [
    "ATTRIBUTION_REQUIRED",
    "INCOMPATIBLE_LICENSES",
    "KNOWN_LICENSES",
    "MISSING_LICENSE_TOKENS",
    "REDISTRIBUTION_RESTRICTED",
    "Finding",
    "LicenseReport",
    "LicenseVerdict",
    "check_license",
    "check_skill_dir",
    "classify",
    "identify_license",
]
