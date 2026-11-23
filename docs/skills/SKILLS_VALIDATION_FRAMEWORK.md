# Skills Validation Framework (Stage 0 Runtime)

| Field | Value |
|---|---|
| doc_id | SKILLS-VALIDATION-FRAMEWORK-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | DESCRIBES IMPLEMENTED CODE — Stage 0 governance runtime present in the working tree. Offline checks implemented; live checks (V-4/V-5) and CI/drift wiring are not. |
| scope | `orchestration/skills/`, `tests/skills/`, `tests/fixtures/skills/`, `schemas/skill-registry.schema.json` |
| normative inputs | `SKILLS_GOVERNANCE.md` (SKILLS-GOVERNANCE-0001) §7 · `SKILLS_REGISTRY_SCHEMA.md` (SKILLS-REGISTRY-SCHEMA-0001) §5/§9 · `SKILLS_COVERAGE_MATRIX.md` (SKILLS-COVERAGE-MATRIX-0001) §4/§6 · `SKILLS_SECURITY_POLICY.md` (AG-003) |
| enforcement boundary | Plane B metadata is validated offline in-house. OpenCode V2 interprets none of it; derived rules take effect only after generation and live G6 verification (OQ-4). |

---

## 1. Purpose

Document the validation framework that is **actually implemented** for skills governance at Stage 0. The framework is a stdlib-only Python runtime that validates registry metadata, skill-directory structure, SKILL.md frontmatter, content safety and derived configuration — before any skill is vendored or enabled.

The earlier planning documents (`SKILLS_GOVERNANCE.md`, `SKILLS_REGISTRY_SCHEMA.md`, `SKILLS_COVERAGE_MATRIX.md`) were written when "nothing was implemented." This document records the code that now exists; where a planned mechanism is still absent, it is marked NOT IMPLEMENTED rather than described as working.

## 2. Implemented modules

Located under `orchestration/skills/` (`__init__.py` exports the public API; `__version__ = "0.1.0"`):

| Module | File | Responsibility |
|---|---|---|
| Controlled vocabularies & models | `models.py` | Enums (`Tier`, `Category`, `SourceType`, `LicenseScope`, `CompatVerdict`, `SecurityVerdict`, `RiskClass`, `Rule`, `BehaviorVerdict`, `Lifecycle`, `ReauditTrigger`, `HistoryEvent`), dataclasses (`SkillEntry`, `Source`, `License`, `Integrity`, `Verdicts`, `Permissions`, `Assignment`, `Versioning`, `HistoryEntry`, `Issue`, `ValidationReport`), constants (`AGENT_IDS`, `KNOWN_COLLISION_IDS`, `DEFAULT_RULE_BY_RISK`, `RULE_STRICTNESS`, `ALLOWED_TRANSITIONS`, `EVENT_BY_LIFECYCLE`). |
| Registry & lifecycle | `registry.py` | Load/save, guarded transitions, rollback, effective-rule resolution, derived permission rendering (`Registry`, `RegistryError`, `render_permissions`). |
| Validation & lint | `validator.py` | Minimal JSON Schema 2020-12 subset evaluator, YAML-frontmatter reader, V-1/V-2/V-3 checks, X-1…X-11 row lint, I-3/X-12 derived-config diff. |
| Content safety | `security_scan.py` | Offline fail-closed V-6 scanner (`PATTERNS`, `scan_text`, `scan_skill_dir`, `classify`). |
| CLI | `cli.py` | `python -m orchestration.skills.cli <command>`; JSON on stdout, non-zero status on gate failure. |

No external packages are installed or required by this runtime: "No installation of external skills" and no third-party Python dependencies apply.

## 3. Enforcement boundary (two planes)

| Plane | Artifact | Interpreted by | Enforced by |
|---|---|---|---|
| A | SKILL.md YAML frontmatter | OpenCode V2 (only `name`, `description`, `metadata.opencode.*`) | OpenCode runtime; factory lint limits Plane A to the allow-list |
| B | `skills-library/registry.json` envelope + rows | nothing external | in-house lint + gates (this runtime) |

`validator.py` hard-codes the Plane A allow-list: `PLANE_A_TOP_LEVEL = {"name", "description", "metadata"}`, `PLANE_A_METADATA = {"opencode"}`, `PLANE_A_OPENCODE = {"autoinvoke", "disable-model-invocation"}`. Governance fields in frontmatter are rejected (V-2). A registry `deny` is metadata until `render_permissions()` writes the derived config and G6 verifies the live effect (OQ-4, ADR-003). This is decision D-3 in `SKILLS_GOVERNANCE.md`.

## 4. V-1…V-8: what is implemented

| Check | Normative definition (coverage matrix §4) | Stage 0 implementation | Status |
|---|---|---|---|
| **V-1** Structural | `<id>/SKILL.md` form, path-derived ID, ≤6 depth, no hidden/`node_modules`, relative refs resolve | `validate_skill_directory()` — directory form, kebab ID ≤64 (`SKILL_ID_RE`), path basename check, depth/ hidden-dir walk, reference resolution from SKILL.md dir | **IMPLEMENTED** (offline) |
| **V-2** Frontmatter | YAML parses, non-empty `description`, booleans, autoinvoke wins, ID-pattern lint, Plane A only | `parse_frontmatter()` / `_parse_simple_yaml()`, `validate_frontmatter()`, `validate_plane_a()`, `effective_autoinvoke()`, X-10 cross-check | **IMPLEMENTED** (offline) |
| **V-3** Uniqueness & precedence | No duplicate ID across sources/config; 11-pair collision list; one ID per concept | `check_uniqueness()` — duplicate `skill_id` (error), duplicate `enabled_in` path = "silent resurrection" (error), known-collision IDs with enablement = `COLLISION-WATCH` warning; `KNOWN_COLLISION_IDS` holds 11 IDs; `Registry.add()` rejects duplicates | **IMPLEMENTED** (registry scope; full six-source filesystem/config walk is NOT IMPLEMENTED) |
| **V-4** Discovery smoke | advertised list, `deny` hides, `autoinvoke:false`, config paths from cwd, catalog shape (I-4) | No live OpenCode probe exists. `validate_plane_a()` checks the autoinvoke cross-check offline only | **NOT IMPLEMENTED** (live; G6/OQ-4) |
| **V-5** Invocation smoke | `skill` tool load, permission effect per class, body without frontmatter, `@skill-id` | No live invocation harness exists | **NOT IMPLEMENTED** (live; G6/OQ-4) |
| **V-6** Content safety | AG-015 pattern set over SKILL.md + all supporting files; unknown ⇒ HOLD | `security_scan.py` — 11 pattern categories, executable-asset inventory, binary/unreadable ⇒ HOLD, deterministic, CLI exit 0/ACCEPT vs 2/non-ACCEPT | **IMPLEMENTED** (offline) |
| **V-7** License/provenance | per-file license, AGPL/NOTICE rules, pinned SHA + hashes, complete directory | Enforced as metadata lint only: X-3 (license), X-6 (SKILL.md hash + complete_directory + on-disk hash diff when `repo_root` supplied), X-7 (provenance/pins). No upstream-drift probe against a live commit | **PARTIALLY IMPLEMENTED** (offline metadata; live drift probe NOT IMPLEMENTED) |
| **V-8** Regression | re-run V-1…V-7 on version bump, re-pin, config change, dir edit; scheduled probe | Triggers declared as `reaudit_triggers` enums and change classes C1…C6 documented; no CI `skills-validation` job or scheduled drift probe in the runtime | **DECLARED, NOT WIRED** |

## 5. JSON Schema subset evaluator

`validate_json_schema()` / `load_schema()` implement the 2020-12 constructs used by `schemas/skill-registry.schema.json`: `$ref` (local `#/` pointers), `type`, `const`, `enum`, `minLength`/`maxLength`/`pattern`, `minimum`, `minItems`, `uniqueItems`, `items`, `required`, `properties`, `additionalProperties` (false or schema), `minProperties`, `allOf`, `anyOf`, `oneOf`, `if`/`then`/`else`, with a depth guard of 64. The evaluator returns human-readable violations; an empty list means schema-valid. `DEFAULT_SCHEMA_PATH` resolves to `schemas/skill-registry.schema.json` relative to the package.

`validate_registry()` runs, in order: JSON Schema validation (`SCHEMA` issues), typed materialization (`MODEL` issues), `check_uniqueness()` (V-3), `lint_entry()` per row (X-1…X-11), and — when `repo_root` is supplied — on-disk hash verification and Plane A validation against each `library_path`.

## 6. X-rules (in-house lint of Plane B)

Implemented in `lint_entry()` unless noted:

| Rule | Enforcement in code |
|---|---|
| X-1 | `library_path` and every `enabled_in` basename == `skill_id` |
| X-2 | lifecycle × enablement × permission guards (CANDIDATE/REVIEWED/APPROVED/RETIRED empty; STAGED/ACTIVE need a promotion copy; STAGED=ask; SUSPENDED=deny with no relaxation) |
| X-3 | AGPL never STAGED/ACTIVE; unverified/repo-level-claim license never APPROVED+; Apache-2.0 needs NOTICE listed |
| X-4 | APPROVED+ requires compatible verdicts, closed conditions, G5 PASS; HOLD/REJECT blocks APPROVED/STAGED/ACTIVE |
| X-5 | `verdicts.*.doc` must be `SKILLS_COMPATIBILITY_MATRIX.md` / `SKILLS_SECURITY_AUDIT.md`; advanced lifecycle requires non-TBD row |
| X-6 | `file_hashes` must include SKILL.md; supporting files require `complete_directory`; `validate_registry(repo_root=...)` verifies real SHA-256 bytes |
| X-7 | in-house rows carry no upstream pins; non-in-house rows require all pins + `upstream_pin=<repo>@<sha>` + sha256 hashes; `adapted` needs local modifications and `local_rev ≥ 1` |
| X-8 | `permissions.risk_class` == `verdicts.security.risk_class`; loosening beyond class default needs human-approval evidence in history (`_has_human_approval()`) |
| X-9 | every `enabled_in` path is exactly `.opencode/skills/<skill_id>` |
| X-10 | `validate_plane_a()` — Plane A effective autoinvoke == `permissions.autoinvoke`; both flags present produce a warning (autoinvoke wins) |
| X-11 | assignment agents within `AGENT_IDS` (AG-001…AG-018) for `factory-agents`; generated-project scope excludes factory IDs; ≥1 consumer when STAGED/ACTIVE |
| X-12 | `check_derived_config()` — regenerate-and-diff derived config (I-3); byte-drift and semantic drift are both errors |

`check_uniqueness()` emits `V-3` errors for duplicate IDs/paths and `COLLISION-WATCH` warnings for the seeded collision IDs. `Registry.add()` is fail-closed on duplicate `skill_id`.

## 7. Content-safety scanner (V-6)

`security_scan.py` applies fail-closed pattern matching to every non-hidden, non-`node_modules` file:

- Categories: `injection-marker`, `remote-fetch-execute`, `dev-tcp`, `destructive-command`, `credential-shape`, `frontmatter-permission-manipulation` (critical); `egress-url` (medium); `encoded-payload`, `privilege-escalation`, `credential-path`, `ci-hooks` (high); plus `executable-asset`, `unknown-content`, `scan-error` (high).
- `EXECUTABLE_EXTENSIONS` flags `.sh/.py/.js/...` assets for inventory.
- `classify()`: critical finding ⇒ `REJECT`/C; any high ⇒ `HOLD`/C; any other finding ⇒ `HOLD`/B; no findings ⇒ `ACCEPT`/A.
- Missing directory, missing SKILL.md, non-UTF-8/binary or unreadable content ⇒ `HOLD` (never ACCEPT). Skills are treated as data and are never executed by the scanner (security policy §17).

## 8. CLI and exit codes

Run from the repository root: `python -m orchestration.skills.cli <command>`.

| Command | Purpose | Exit codes |
|---|---|---|
| `validate --registry PATH [--schema PATH] [--repo-root DIR] [--skill-dir DIR]...` | Full registry validation (+ optional structural skill-dir checks) | 0 ok, 1 issues |
| `scan PATH` | Offline V-6 scan | 0 ACCEPT, 2 non-ACCEPT |
| `permissions --registry PATH [--output FILE]` | Render canonical derived config (I-3) | 0 |
| `check-permissions --registry PATH --config FILE` | Regenerate-and-diff (X-12) | 0 ok, 1 drift |
| `transition --registry PATH --skill-id ID --to STATE [--gates ... --adr ... --actor ... --evidence ... --output FILE]` | Guarded lifecycle transition | 0 ok, 3 illegal transition |
| `rollback --registry PATH --skill-id ID [--actor ... --reason ... --output FILE]` | Kill-switch rollback (T-3) | 0 ok, 3 error |

`render_permissions()` emits canonical bytes (`json.dumps(..., indent=2, sort_keys=True) + "\n"`) so CI can regenerate-and-diff instead of trusting hand edits.

## 9. Evidence index

- `orchestration/skills/__init__.py` — module list, `__version__`, exported API, enforcement note.
- `orchestration/skills/models.py` — vocabularies, constants, entry dataclasses.
- `orchestration/skills/registry.py` — transitions, rollback, effective rules, derived config.
- `orchestration/skills/validator.py` — schema subset, frontmatter reader, V-1/V-2/V-3, X-1…X-11, X-12.
- `orchestration/skills/security_scan.py` — V-6 scanner and fail-closed classifier.
- `orchestration/skills/cli.py` — commands and exit codes.
- `schemas/skill-registry.schema.json` — registry envelope/entry schema (const `schema_version: "1.0"`).
- `tests/skills/` and `tests/fixtures/skills/` — executable evidence (see `SKILLS_TEST_REPORT.md`).

## 10. Limitations (honest status)

1. No skill is installed or enabled; no external skill was downloaded or installed to produce or exercise this framework.
2. V-4/V-5 live discovery/invocation and the G6 resolution of OQ-4 are not implemented; no permission-dependent claim is therefore evidence (P-5).
3. The V-3 check is registry-scoped; the full official six-discovery-location plus `skills` config-array walk described in the coverage matrix is not implemented.
4. V-7 is metadata-level only; no scheduled upstream-drift probe or cadence (ES-4) exists.
5. V-8 triggers are declared, not wired to a CI job or scheduler.
6. The schema evaluator is a deliberately narrow subset covering exactly the constructs in the registry schema — it is not a general JSON Schema implementation.
