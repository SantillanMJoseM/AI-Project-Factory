# Stage 0.1 Skills Test Report

| Field | Value |
|---|---|
| doc_id | SKILLS-PHASE-0-1-TEST-REPORT-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | REPORTS THE SUPPLIED RUN OUTPUT AND THE COMMITTED TESTS — **115 PASS** from `python3 tests/run_all.py`; this documentation session did not independently re-execute the suite |
| stage | Stage 0.1 — drift detection, V5 license controls, skill task contract, CI validation, independent security review |
| suite under test | `orchestration/skills/` — Stage 0 files (`__init__.py`, `models.py`, `registry.py`, `validator.py`, `security_scan.py`, `cli.py`) plus Stage 0.1 additions (`drift.py`, `license_check.py`, `task_contract.py`) |
| executable tests | `tests/skills/` (7 modules) orchestrated by `tests/run_all.py` (13 module entries) |
| fixtures | `tests/fixtures/skills/registry.json`, `valid-skill/`, `invalid-skill/`, `drift-baseline.json` |
| schema | `schemas/skill-task-contract.schema.json` (2020-12, 11 mandatory fields) |
| external skills installed | **None** in the factory repository; the multimodel experiment used a separate temporary project (companion report) |

---

## 1. Evidence basis and honesty note

This report distinguishes three kinds of evidence, per ADR-003 (evidence over assertion):

1. **Supplied run output:** the Stage 0.1 tasking supplies `tests/run_all.py` output ending in **115 PASS / ALL TESTS PASSED**. That aggregate is reported here verbatim as the authoritative run record available to this task; it has **not** been re-run in this documentation session (no shell execution tool was available).
2. **Committed tests and implementation:** test functions, CLI exit codes, fixture data and module behaviour were verified by reading the files listed in §7. All functions named below exist in the committed code.
3. **Experiment observations:** the drift, license, multimodel and permission observations reported here and in the companion reports were supplied as experiment data; they are labelled as observations, not as gate approvals.

The Stage 0.1 modules are **additive**: each new module docstring states that no existing runtime module was modified, and the imports confirm reuse of `validator.validate_json_schema()` and `models.ValidationReport` rather than replacement. The Stage 0 baseline of 38 skills tests still appears unchanged in `run_all.py`.

## 2. Aggregate result and inventory

| Suite module | Introduced | Test functions | Scope |
|---|---|---:|---|
| `tests/skills/test_registry.py` | Stage 0 | 8 | lifecycle transitions, derived permissions, CLI |
| `tests/skills/test_validation.py` | Stage 0 | 14 | schema, V-1/V-2/V-3, X-1…X-12, hash drift |
| `tests/skills/test_security_scan.py` | Stage 0 | 9 | V-6 offline scanner (see §5 and the independent review) |
| `tests/skills/test_rollback.py` | Stage 0 | 7 | T-3 rollback / kill-switch |
| **Stage 0 skills subtotal** | | **38** | as recorded in `SKILLS_TEST_REPORT.md` |
| `tests/skills/test_license_check.py` | Stage 0.1 | 11 | V5 license identification and controls |
| `tests/skills/test_task_contract.py` | Stage 0.1 | 12 | 11-field contract, safety rules TC-1…TC-6, file IO |
| `tests/skills/test_drift.py` | Stage 0.1 | 12 | six-dimension drift, approvals, fail-closed snapshots, CLI |
| **Stage 0.1 skills subtotal** | | **35** | new modules |
| **Skills total** | | **73** | enumerated from the seven committed test files |
| Six non-skills modules (`contracts/`, `policies/`, `orchestration/`) | prior stages | 42 by aggregate arithmetic | not enumerated in this report |
| **Aggregate (`python3 tests/run_all.py`)** | | **115** | **ALL TESTS PASSED** (supplied run output) |

CLI exit-code contracts asserted by the committed tests: `validate` 0/1, `scan` 0/2, `check-permissions` 0/1, `permissions` 0, `transition` 0/3, `rollback` 0/3 (Stage 0), and `python -m orchestration.skills.drift` **0 = PASS, 2 = BLOCKED, 1 = FAIL** (Stage 0.1, `test_cli_exit_codes_for_clean_and_drifted_snapshots`).

## 3. Stage 0.1 test coverage

### 3.1 Drift detection — `orchestration/skills/drift.py` / `test_drift.py` (12 tests)

| Test | Behaviour asserted | Outcome |
|---|---|---|
| `test_snapshot_is_deterministic_and_complete` | `snapshot_dir()` is byte-stable and emits exactly the six dimensions `version`, `files`, `content`, `permissions`, `metadata`, `dependencies`; hashes are `sha256:`-prefixed | PASS |
| `test_checked_in_ci_baseline_matches_fixture_skill` | `tests/fixtures/skills/drift-baseline.json` compared with `valid-skill` yields `PASS` — this is the baseline consumed by the CI workflow | PASS |
| `test_clean_snapshot_passes` | identical snapshots ⇒ `PASS`, no findings, `ok=True`, `blocked=False` | PASS |
| `test_unapproved_version_change_blocks` | version change with no approval ⇒ `BLOCKED`, finding kind `version`, `ok=False` | PASS |
| `test_approved_version_change_is_an_observation` | explicit approval (mapping or `version:...->...` string) ⇒ `PASS_WITH_OBSERVATIONS`, `approved_by` recorded | PASS |
| `test_all_six_dimensions_are_detected` | version/hash/content/permission/metadata/dependency changes all reported; dependency drift is order-insensitive | PASS |
| `test_content_edit_on_disk_blocks_then_approves` | appended line to `SKILL.md` on disk ⇒ `BLOCKED` with hash+content findings; explicit `hash:*`/`content:*` approvals ⇒ `PASS_WITH_OBSERVATIONS` | PASS |
| `test_permission_metadata_and_dependency_drift` | sidecar/list vs mapping normalization; no false dependency finding | PASS |
| `test_baseline_from_registry_entry` | baseline derived from registry row: `0.1.0#0`, file hashes, `CANDIDATE` lifecycle, empty dependencies | PASS |
| `test_classify_precedence` | no findings ⇒ `PASS`; all approved ⇒ `PASS_WITH_OBSERVATIONS`; any unapproved ⇒ `BLOCKED` | PASS |
| `test_invalid_snapshot_fails_closed` | non-object snapshot and missing directory raise `DriftError` | PASS |
| `test_cli_exit_codes_for_clean_and_drifted_snapshots` | CLI: clean ⇒ 0/`PASS`, changed ⇒ 2/`BLOCKED`, malformed ⇒ 1/`FAIL` | PASS |

**Drift experiment result (as supplied):** clean → **PASS**; unapproved change → **BLOCKED**; malformed baseline → **FAIL** (exit 1). Approvals are supplied explicitly and never inferred from the changed artifact (matches ADR-002). Note that `drift.py` excludes hidden directories and `node_modules` from its file walk (`_SKIP_DIRS`); this is a separate control from the V-6 scanner gap F-01 recorded in the security review.

### 3.2 V5 license controls — `orchestration/skills/license_check.py` / `test_license_check.py` (11 tests)

| Test | Behaviour asserted | Outcome |
|---|---|---|
| `test_identify_license_recognizes_spdx_license_text_and_expression` | SPDX identifiers, Apache/GPL prose, `MIT OR Apache-2.0` expression | PASS |
| `test_missing_license_is_blocked_not_pass` | absent/`UNKNOWN`/blank `spdx` ⇒ `BLOCKED` (`V5-MISSING`); file-derived license does not silently cure a missing declaration | PASS |
| `test_in_house_tbd_is_an_observation_not_a_block` | in-house `TBD` ⇒ `PASS_WITH_OBSERVATIONS` (`V5-PROVENANCE`), reflecting the still-undefined in-house license policy (ES-8) | PASS |
| `test_clean_mit_license_passes` | declared MIT with evidence ⇒ `PASS`, no findings | PASS |
| `test_apache_requires_notice_file` | Apache-2.0 without NOTICE ⇒ `FAIL` (`V5-ATTRIBUTION`); complete notice set ⇒ `PASS` | PASS |
| `test_incompatible_copyleft_license_fails` | AGPL/GPL ⇒ `FAIL` (`V5-INCOMPATIBLE`) | PASS |
| `test_mixed_licenses_fail` | two distinct licenses ⇒ `V5-MIXED`/`FAIL`; SPDX `OR` expression is one choice | PASS |
| `test_redistribution_restrictions_fail` | CC-BY-NC, PROPRIETARY ⇒ `V5-REDISTRIBUTION`/`FAIL` | PASS |
| `test_provenance_controls` | repo-level claim ⇒ observation; `unverified` ⇒ `FAIL`; unpinned upstream ⇒ observation; in-house claim on external source ⇒ `FAIL` | PASS |
| `test_check_skill_dir_corroborates_declared_license` | no declaration + on-disk LICENSE ⇒ `BLOCKED`; with registry record ⇒ `PASS` | PASS |
| `test_classify_precedence_and_report_serialization` | `BLOCKED > FAIL > PASS_WITH_OBSERVATIONS > PASS`; JSON-serializable report | PASS |

**License experiment result (as supplied):** controls are implemented; **missing license ⇒ BLOCKED**. This is a metadata/directory control — it does not by itself define the factory's in-house license policy (ES-8 remains open).

### 3.3 Skill task contract — `orchestration/skills/task_contract.py` / `test_task_contract.py` (12 tests)

| Test | Behaviour asserted | Outcome |
|---|---|---|
| `test_schema_declares_all_formal_fields` | schema is 2020-12, `additionalProperties: false`, 11 required fields in order, `$ref`s for skill/agent IDs | PASS |
| `test_valid_contract_passes_and_roundtrips` | valid contract ⇒ `ok=True`, no issues; `TaskContract.from_dict().to_dict()` round-trips | PASS |
| `test_missing_required_fields_are_reported` | `SCHEMA` errors name `evidence` and `authorized_files` | PASS |
| `test_unknown_field_is_rejected` | extra property ⇒ "unexpected property" `SCHEMA` error | PASS |
| `test_tc1_executor_agent_must_be_verified_factory_agent` | `AG-999` ⇒ `TC-1` | PASS |
| `test_tc2_authorized_files_must_be_safe_relative_paths` | absolute, `..`, `.env`, Windows drive paths ⇒ `TC-2`; safe repo-relative path accepted | PASS |
| `test_tc3_restricted_tool_requires_approval_restriction` | `shell` without approval restriction ⇒ `TC-3`; explicit approval restriction clears it | PASS |
| `test_tc4_placeholders_and_blank_entries_are_rejected` | `TBD`/blank prose and list entries ⇒ `TC-4` | PASS |
| `test_tc5_skill_id_and_pinned_version_are_required` | `Bad ID!` and `latest` ⇒ `SCHEMA` + `TC-5` | PASS |
| `test_tc6_acceptance_criteria_required_evidence_is_observation` | no acceptance criteria ⇒ `TC-6` error; empty evidence ⇒ `TC-6` warning only | PASS |
| `test_load_contract_from_file` | `TaskContract.load()` materializes and validates | PASS |
| `test_from_dict_rejects_unmaterializable_payload` | non-list `inputs` raises `TaskContractError` | PASS |

**Task-contract experiment result (as supplied):** implemented (schema + dataclass + TC-1…TC-6); no execution of a contract against a live skill was claimed.

### 3.4 CI — `.github/workflows/skills-validation.yml`

The workflow is **added** (additive; no existing workflow replaced). It triggers on PRs touching `orchestration/skills/**`, `tests/skills/**`, `tests/run_all.py`, `tests/fixtures/skills/**`, `schemas/skill-task-contract.schema.json` and the workflow itself; uses `contents: read`; checks out with `actions/checkout@v4`, sets up Python 3.11 with `actions/setup-python@v5`, runs `python tests/run_all.py`, then runs:

```
python -m orchestration.skills.drift \
  --dir tests/fixtures/skills/valid-skill \
  --baseline tests/fixtures/skills/drift-baseline.json
```

This matches `drift.py`'s CLI (`--baseline` required; `--dir` or `--current` supplies the other snapshot) and the checked-in baseline verified by `test_checked_in_ci_baseline_matches_fixture_skill`. **The workflow run itself was not executed in this documentation session; no CI-green claim is made.**

## 4. Regression of Stage 0 scenarios

The ten Stage 0 scenarios S-01…S-10 in `SKILLS_TEST_REPORT.md` remain covered by the unchanged Stage 0 test modules (schema/envelope, V-1/V-2/V-3, frontmatter, uniqueness, X-rules, transitions, derived permissions, V-6 scanner, X-6 hash drift, T-3 rollback). Stage 0.1 adds three new controls without removing those assertions; the aggregate 115 PASS includes them.

## 5. Limits on what these PASSes mean

- The V-6 scanner's **9/9 PASS is a happy-path result only**. AG-015's independent review (session `ses_e0bfce0b8ffemcG0O03RIKN11Z`, verdict **PASS WITH OBSERVATIONS / CONDITIONAL**) found 25 of 40 adversarial probes evading or only partially detected, a hidden-directory silent ACCEPT (F-01), no guard-file/policy tampering detection (F-03), and no wiring of the scanner into `validate`/`transition` (F-04). An ACCEPT/A verdict is **not** evidence that a skill is safe; human final approval remains mandatory.
- No permission-dependent claim is proven by this suite; OQ-4 remains an open observation (companion multimodel report).
- No skill is vendored into the factory repository; no G0–G8 gate is declared passed by this report.
- Tests are stdlib-only and offline; they assert governance metadata logic and local snapshots, not installed-OpenCode runtime behaviour.

## 6. Limitations

1. The 115 PASS aggregate is the supplied run output; this session could not re-execute `python3 tests/run_all.py` (no shell tool). Re-execution is required at stage/gate closure (ADR-003; AGENTS.md run-tests rule).
2. Git state was not verifiable in this session; the gate owner should confirm `git status --short --branch` before closure.
3. Per-module counts for the six non-skills modules were not enumerated; the figure 42 is aggregate arithmetic (115 − 73), not an independently counted inventory.
4. Experiment outcomes for drift/license/task contract/multimodel/permissions are supplied data, reproduced faithfully; they are not new tests authored by this documentation task.

## 7. Evidence index

- Runner: `tests/run_all.py` (13 entries, ending `ALL TESTS PASSED`).
- Stage 0.1 tests: `tests/skills/test_drift.py`, `test_license_check.py`, `test_task_contract.py`.
- Stage 0 tests: `tests/skills/test_validation.py`, `test_registry.py`, `test_security_scan.py`, `test_rollback.py`.
- Implementation: `orchestration/skills/drift.py`, `license_check.py`, `task_contract.py`; Stage 0 modules unchanged.
- Schema/fixtures: `schemas/skill-task-contract.schema.json`; `tests/fixtures/skills/drift-baseline.json`, `registry.json`, `valid-skill/`, `invalid-skill/`.
- CI: `.github/workflows/skills-validation.yml`.
- Companions: `SKILLS_PHASE_0_1_MULTIMODEL_REPORT.md`, `SKILLS_PHASE_0_1_COMPLETION.md`, `SKILLS_PHASE_0_1_SECURITY_REVIEW.md`, `SKILLS_TEST_REPORT.md`.
