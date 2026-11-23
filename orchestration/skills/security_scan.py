"""Static content-safety scanner for skill packages (V-6, fail-closed).

Implements the AG-015 pattern set from ``docs/skills/SKILLS_SECURITY_POLICY.md``:
remote fetch-and-execute, egress URLs, encoded payloads, ``/dev/tcp``,
destructive commands, sudo/privilege use, credential shapes/paths, CI hooks,
prompt-injection markers, frontmatter permission manipulation and an
executable-asset inventory.

Skills are data, never code (policy §17). This scanner never executes what it
reads. Unknown/unreadable content is HOLD, never ACCEPT.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# (category, compiled pattern, severity)
Pattern = Tuple[str, "re.Pattern[str]", str]

PATTERNS: List[Pattern] = [
    (
        "injection-marker",
        re.compile(
            r"(?i)ignore (?:all |any )?(?:your |the )?(?:previous|prior|system|developer) instructions"
            r"|disregard (?:your |the )?(?:AGENTS\.md|security policy|guidelines)"
            r"|you are now (?:an? )?(?:unrestricted|DAN)"
            r"|developer mode"
            r"|do not tell the user|keep this (?:action )?secret"
            r"|bypass the (?:normal )?rules|this is a test"
        ),
        "critical",
    ),
    (
        "remote-fetch-execute",
        re.compile(
            r"(?i)(?:curl|wget)[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)"
            r"|fetch\s+and\s+(?:execute|run)|download\s+and\s+(?:execute|run)"
            r"|npx\s+skills\s+add|install\s+from\s+(?:this\s+)?url"
        ),
        "critical",
    ),
    ("dev-tcp", re.compile(r"/dev/tcp/"), "critical"),
    (
        "destructive-command",
        re.compile(
            r"(?i)\brm\s+-r[f]?\b|\bgit\s+push\s+(?:-f|--force)|\breset\s+--hard\b"
            r"|\b(?:DROP|TRUNCATE)\s+TABLE\b|\bmkfs\b|\bchmod\s+-R\s+777\b|\bdel\s+/[fqs]\b"
        ),
        "critical",
    ),
    (
        "credential-shape",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b"
            r"|\bghp_[A-Za-z0-9]{20,}\b|\bsk-[A-Za-z0-9]{16,}\b"
            r"|\bxox[baprs]-[A-Za-z0-9-]{10,}\b"
        ),
        "critical",
    ),
    (
        "frontmatter-permission-manipulation",
        re.compile(
            r"(?i)allowed[_-]?tools|auto[- ]?approve|skip[- ]?permissions"
            r"|dangerously[- ]?skip|permissions\s*:\s*\[|grant\s+full\s+access"
        ),
        "critical",
    ),
    ("egress-url", re.compile(r"https?://[^\s)\"']+"), "medium"),
    (
        "encoded-payload",
        re.compile(
            r"(?i)base64\s+(?:-d|--decode|-D)|atob\s*\(|frombase64string"
            r"|decode\s+and\s+(?:execute|run)|hex\s+decode"
        ),
        "high",
    ),
    (
        "privilege-escalation",
        re.compile(r"(?i)(?:^|\s)sudo(?:\s|$)|su\s+-\s+root|chmod\s+4755|setuid"),
        "high",
    ),
    (
        "credential-path",
        re.compile(r"(?i)(?:^|[^\w])\.env(?:\b|$)|~/\.aws|~/\.ssh|id_rsa|\.npmrc|keychain"),
        "high",
    ),
    ("ci-hooks", re.compile(r"(?i)pull_request_target|workflow_run\s*:"), "high"),
]

EXECUTABLE_EXTENSIONS = frozenset(
    {
        ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".exe", ".bin",
        ".so", ".dll", ".py", ".js", ".mjs", ".cjs", ".rb", ".pl", ".php",
    }
)


@dataclass
class Finding:
    category: str
    severity: str
    source: str
    line: int
    excerpt: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "source": self.source,
            "line": self.line,
            "excerpt": self.excerpt,
        }


@dataclass
class ScanResult:
    target: str
    files_scanned: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    verdict: str = "ACCEPT"
    risk_class: str = "A"

    @property
    def ok(self) -> bool:
        return self.verdict == "ACCEPT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "files_scanned": list(self.files_scanned),
            "findings": [f.to_dict() for f in self.findings],
            "verdict": self.verdict,
            "risk_class": self.risk_class,
            "ok": self.ok,
        }


def classify(findings: List[Finding]) -> Tuple[str, str]:
    """Fail-closed verdict: critical => REJECT, any finding => HOLD."""
    severities = {f.severity for f in findings}
    if "critical" in severities:
        return "REJECT", "C"
    if findings:
        return ("HOLD", "C") if "high" in severities else ("HOLD", "B")
    return "ACCEPT", "A"


def scan_text(text: str, source: str = "<text>") -> List[Finding]:
    """Apply the pattern set to a single text blob (no execution)."""
    findings: List[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for category, regex, severity in PATTERNS:
            match = regex.search(line)
            if match:
                excerpt = match.group(0).strip()[:160]
                findings.append(Finding(category, severity, source, lineno, excerpt))
    return findings


def _iter_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for child in sorted(root.rglob("*")):
        rel = child.relative_to(root)
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts[:-1]):
            continue
        if child.is_file():
            files.append(child)
    return files


def scan_skill_dir(path: Any, *, require_skill_md: bool = True) -> ScanResult:
    """Scan SKILL.md and every supporting file of a skill directory."""
    root = Path(path)
    result = ScanResult(target=str(root))
    if not root.is_dir():
        result.findings.append(Finding("scan-error", "high", str(root), 0, "skill directory not found"))
        result.verdict, result.risk_class = classify(result.findings)
        return result

    files = _iter_files(root)
    if require_skill_md and not any(f.name == "SKILL.md" and f.parent == root for f in files):
        result.findings.append(Finding("scan-error", "high", str(root / "SKILL.md"), 0, "missing SKILL.md"))

    for file in files:
        rel = str(file.relative_to(root))
        result.files_scanned.append(rel)
        if file.suffix.lower() in EXECUTABLE_EXTENSIONS:
            result.findings.append(
                Finding("executable-asset", "high", rel, 0, "executable asset: %s" % file.suffix)
            )
        try:
            text = file.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            # Unreadable / binary content cannot be reviewed statically.
            result.findings.append(Finding("unknown-content", "high", rel, 0, "non-UTF-8 content; fail closed"))
            continue
        except OSError as exc:
            result.findings.append(Finding("scan-error", "high", rel, 0, str(exc)))
            continue
        result.findings.extend(scan_text(text, rel))

    result.verdict, result.risk_class = classify(result.findings)
    return result


__all__ = [
    "EXECUTABLE_EXTENSIONS",
    "PATTERNS",
    "Finding",
    "ScanResult",
    "classify",
    "scan_skill_dir",
    "scan_text",
]
