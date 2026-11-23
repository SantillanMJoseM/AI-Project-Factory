# Skills Stage 0 Test Report

| Field | Value |
|---|---|
| doc_id | SKILLS-TEST-REPORT-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | REPORTS THE COMMITTED TEST SUITE — offline stdlib tests for the Stage 0 runtime. No live OpenCode V-4/V-5/G6 execution is claimed. |
| suite under test | `orchestration/skills/` (models, registry, validator, security_scan, cli) |
| executable tests | `tests/skills/test_validation.py`, `test_registry.py`, `test_rollback.py`, `test_security_scan.py` |
| fixtures | `tests/fixtures/skills/registry.json`, `valid-skill/`, `invalid-skill/` |
| runner | `python3 tests/run_all.py` (lists the four skills modules at lines 13–16) |
| external skills installed | **None** — no external skill was downloaded, installed or enabled for this work |

---

## 1. Scope and evidence basis

This report covers the **10 required Stage 0 validation scenarios** derived from the normative acceptance set — V-1…V-8 (`SKILLS_COVERAGE_MATRIX.md` §4), X-1…X-12 (`SKILLS_REGISTRY_SCHEMA.md` §5), and the permission/lifecycle/rollback requirements (`SKILLS_GOVERNANCE.md` §4–§7). Each scenario is executed by named test functions in the four modules.

Result convention used below:

- **PASS** — the behaviour is asserted by the named, committed test function(s) and the fixture data is constructed to satisfy them. The repository's documented aggregate record is `python3 tests/run_all.py → ALL TESTS PASSED` (PROJECT_STATUS.md / PROJECT_HANDOFF.md; `run_all.py` includes the four skills modules).
- **NOT EXECUTED** — live checks that require an installed OpenCode build; no PASS is claimed (OQ-4, A-1/A-8/A-9, G6).
- Honesty note: this documentation task did not itself re-run the suite; the authoritative result is a fresh `python3 tests/run_all.py`. Re-execution is required at G6 per ADR-003.

Suite inventory: **38 test functions** — `test_validation.py` (14), `test_registry.py` (8), `test_rollback.py` (7), `test_security_scan.py` (9). All are pure stdlib/pytest-compatible and runnable via `python3 <file>` (each file has an `if __name__ == "__main__"` runner).

## 2. Ten required scenarios and results

| # | Requirement | Scenario | Executing test(s) | Expected / observed result |
|---|---|---|---|---|
| **S-01** | Schema + evidence rule | Registry envelope conforms to `skill-registry.schema.json`; malformed ID or missing required field is rejected; `TBD` placeholders preserved | `test_validation.py::test_schema_file_is_valid_and_has_expected_defs`, `::test_valid_fixture_registry_passes_all_checks`, `::test_schema_rejects_bad_id_and_missing_field` | **PASS** — valid fixture yields zero issues; `Bad ID!` ⇒ `SCHEMA`; missing `permissions` ⇒ error mentioning `permissions` |
| **S-02** | V-1 structural | `<id>/SKILL.md` directory form, path-derived kebab ID, depth/hidden-dir walk, referenced supporting files resolve | `test_validation.py::test_validate_skill_directory_structure_and_references` | **PASS** — valid-skill OK; invalid-skill emits `V-2`; wrong expected id emits `V-1` |
| **S-03** | V-2 + X-10 frontmatter | Plane A allow-list, non-empty description, boolean controls, autoinvoke-wins, autoinvoke cross-checked against Plane B | `test_validation.py::test_frontmatter_valid_and_invalid_fixtures`, `::test_plane_a_autoinvoke_crosscheck_and_both_flags`, `::test_validate_skill_directory_structure_and_references` | **PASS** — valid fixture effective autoinvoke `False`; `allowed_tools` rejected; mismatch ⇒ `X-10`; both flags ⇒ warning with autoinvoke winning |
| **S-04** | V-3 uniqueness / GOV-2 | Duplicate `skill_id`, duplicate enablement path ("silent resurrection"), seeded collision-ID watch | `test_validation.py::test_v3_detects_silent_resurrection`, `test_registry.py::test_duplicate_id_rejected`, `test_rollback.py::test_rollback_resolves_duplicate_enablement_without_resurrection` | **PASS** — duplicate path ⇒ `V-3` with "silent resurrection"; `Registry.add()` raises on duplicate id; rollback clears the V-3 error |
| **S-05** | X-2/X-3/X-4/X-7/X-8/X-9/X-11 row guards | Lifecycle/enablement/license/verdict/provenance/permission/assignment consistency blocks unsafe rows | `test_validation.py::test_x3_license_exposure_blocks_activation`, `::test_x2_lifecycle_enablement_and_permission_guards`, `::test_x4_verdict_guards`, `::test_x7_provenance_guards`, `::test_x8_risk_class_and_loosening_guards`, `::test_x9_and_x11_guards` | **PASS** — each mutated fixture emits its expected X-code (AGPL/verified-scope blocks, STAGED ask, SUSPENDED deny, HOLD blocks, pin fields, risk mismatch/loosening, path/agent scope) |
| **S-06** | T-1/T-2 transitions | Guarded transitions apply correct posture, illegal and SUSPENDED-re-entry transitions blocked without mutation, history append-only | `test_registry.py::test_transition_happy_path`, `::test_invalid_transition_is_blocked_without_mutation`, `::test_history_is_append_only`, `::test_save_load_roundtrip` | **PASS** — CANDIDATE→REVIEWED→APPROVED→STAGED→ACTIVE gives deny/deny/ask/allow; SUSPENDED→REVIEWED rejected; history prefix unchanged; save/load round-trips |
| **S-07** | P-1…P-5 / I-3 / X-12 | Derived permissions are fail-closed per class, STAGED=ask, SUSPENDED=deny sorted last, loose overrides ignored; regenerate-and-diff detects drift | `test_registry.py::test_derive_permissions_is_fail_closed`, `::test_cli_validate_permissions_and_check` | **PASS** — global default deny; skill-a/b/c/d/e → allow/ask/deny/ask/deny; deny rule last; class-C override cannot loosen; canonical bytes reproduced; edited config ⇒ exit 1 |
| **S-08** | V-6 content safety | AG-015 pattern set over all files; fail-closed classification; deterministic; CLI exit codes | `test_security_scan.py` (all 9: `test_scan_valid_fixture_is_accept`, `::test_scan_invalid_fixture_rejects_with_layered_findings`, `::test_scan_text_detects_encoded_payload_and_egress`, `::test_classify_fail_closed_matrix`, `::test_unknown_binary_content_is_hold_not_accept`, `::test_executable_asset_inventory`, `::test_missing_skill_dir_holds_closed`, `::test_scan_is_deterministic`, `::test_cli_scan_exit_codes`) | **PASS** — valid ⇒ ACCEPT/A; invalid ⇒ REJECT/C with all 7 expected finding categories; classify matrix exact; binary/executable/missing ⇒ HOLD; deterministic; scan CLI 0 vs 2 |
| **S-09** | X-6 integrity drift | Real SHA-256 verification against an on-disk library root detects content drift | `test_validation.py::test_validate_registry_with_repo_root_detects_hash_drift` | **PASS** — copied fixture validates clean; appending a drifted line ⇒ "hash mismatch" error |
| **S-10** | T-3 rollback / kill-switch | Rollback sets SUSPENDED + deny, clears artifacts/overrides, retains row, works from all pre-RETIRED states, refuses RETIRED, CLI writes updated copy | `test_rollback.py` (all 7: `test_rollback_sets_suspended_deny_and_clears_artifact`, `::test_rollback_keeps_row_and_appends_history_only`, `::test_rollback_derives_deny_even_with_hidden_overrides`, `::test_rollback_from_every_pre_retired_state`, `::test_rollback_of_retired_row_is_rejected`, `::test_rollback_resolves_duplicate_enablement_without_resurrection`, `::test_cli_rollback_writes_updated_registry`) | **PASS** — SUSPENDED/deny/empty enabled_in; row retained with +1 history entry; deny survives hidden override; all five states roll back; RETIRED refused; input untouched with `--output` |

## 3. Aggregate result

| Suite | Test functions | Result |
|---|---|---|
| `tests/skills/test_validation.py` | 14 | PASS (per committed assertions; aggregate `run_all.py` record) |
| `tests/skills/test_registry.py` | 8 | PASS |
| `tests/skills/test_rollback.py` | 7 | PASS |
| `tests/skills/test_security_scan.py` | 9 | PASS |
| **Total** | **38** | **ALL TESTS PASSED** (documented aggregate; re-run at G6) |

CLI exit-code matrix exercised by the suite: `validate` 0/1, `scan` 0/2, `check-permissions` 0/1, `permissions` 0, `transition` 0/3, `rollback` 0/3.

## 4. Scenarios explicitly NOT executed (no PASS claimed)

| Check | Reason | Gate owed |
|---|---|---|
| V-4 discovery smoke | requires installed OpenCode build; no advertised-list probe implemented | G6 (OQ-4) |
| V-5 invocation smoke | requires live `skill` tool + per-agent permission effects | G6 (OQ-4) |
| Full six-source V-3 filesystem/config walk | runtime checks registry scope only | G2/G6 |
| Live upstream-drift probe (C1/G8) | no scheduled probe or cadence (ES-4) | G3/G8 |
| Multimodel matrix MM-1…MM-7 | no approved model matrix (ES-3) | G5/G6/G7 |

Per `SKILLS_COVERAGE_MATRIX.md` §5, acceptance criteria **A-8 (functional) and A-9 (permissions)** cannot be satisfied by offline tests alone; no skill is vendored and no runtime test has been executed, so no skill is USABLE at Stage 0.

## 5. Fixtures used (traceability)

- `tests/fixtures/skills/registry.json` — single in-house CANDIDATE row `valid-skill` (risk A, rule deny, autoinvoke false, real SHA-256 hashes of the fixture files, `history: [registered, TBD]`).
- `tests/fixtures/skills/valid-skill/SKILL.md` + `references/guide.md` — clean guidance-only skill; effective autoinvoke `False`; referenced guide exists.
- `tests/fixtures/skills/invalid-skill/SKILL.md` — intentionally unsafe: `allowed_tools` in frontmatter, injection marker, `curl … | sh`, `rm -rf`, `sudo`, `/dev/tcp`, `AKIA…` credential shape, `pull_request_target`. Used to prove V-2 and V-6 fail closed.

## 6. Limitations

1. Tests are offline and stdlib-only; they prove governance-metadata logic, not OpenCode runtime behaviour.
2. Results are reported from the committed test suite and the repository's aggregate PASS record; this documentation task performed no execution. Run `python3 tests/run_all.py` for authoritative confirmation.
3. Some tests use `copy.deepcopy` of a single fixture row and mutate fields; they validate guard logic, not real vendored skills.
4. No external skill was installed at any point; the fixtures are local test data only.

## 7. Evidence index

- `tests/skills/test_validation.py` — V-1/V-2/V-3, X-2/X-3/X-4/X-7/X-8/X-9/X-11, hash drift.
- `tests/skills/test_registry.py` — transitions, derived permissions, CLI validate/permissions/check-permissions.
- `tests/skills/test_rollback.py` — rollback semantics and CLI rollback.
- `tests/skills/test_security_scan.py` — V-6 pattern set, classify matrix, CLI scan.
- `tests/run_all.py` — aggregate runner including the four skills modules.
- Companion documents: `SKILLS_VALIDATION_FRAMEWORK.md`, `SKILLS_PERMISSION_MODEL.md`, `SKILLS_VERSIONING_AND_ROLLBACK.md`.
