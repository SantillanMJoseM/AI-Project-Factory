"""Skills governance runtime (Stage 0).

Stdlib-only implementation of the governance plane specified in
``docs/skills/SKILLS_GOVERNANCE.md`` and ``docs/skills/SKILLS_REGISTRY_SCHEMA.md``.

Modules:
  models         - controlled vocabularies, entry objects, issue/report types
  registry       - registry envelope, lifecycle guards, rollback, derived config
  validator      - JSON Schema subset, Plane A lint, V-1/V-3, X-1..X-12, I-3
  security_scan  - offline V-6 content-safety scanner (fail-closed)
  cli            - command-line entry point (``python -m orchestration.skills.cli``)

Enforcement note: this runtime validates governance metadata. OpenCode V2
interprets none of Plane B; the derived permission config must be verified live
at G6 (OQ-4).
"""

from .models import Issue, Lifecycle, Rule, SecurityVerdict, SkillEntry, ValidationReport
from .registry import Registry, RegistryError, render_permissions
from .security_scan import Finding, ScanResult, classify, scan_skill_dir, scan_text
from .validator import (
    check_derived_config,
    effective_autoinvoke,
    parse_frontmatter,
    split_skill,
    validate_frontmatter,
    validate_json_schema,
    validate_plane_a,
    validate_registry,
    validate_skill_directory,
)

__version__ = "0.1.0"

__all__ = [
    "Finding",
    "Issue",
    "Lifecycle",
    "Registry",
    "RegistryError",
    "Rule",
    "ScanResult",
    "SecurityVerdict",
    "SkillEntry",
    "ValidationReport",
    "__version__",
    "check_derived_config",
    "classify",
    "effective_autoinvoke",
    "parse_frontmatter",
    "render_permissions",
    "scan_skill_dir",
    "scan_text",
    "split_skill",
    "validate_frontmatter",
    "validate_json_schema",
    "validate_plane_a",
    "validate_registry",
    "validate_skill_directory",
]
