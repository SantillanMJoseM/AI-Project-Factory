# RECON-018-DOCS-003 — Technical Documentation Reconciliation

Date: 2026-11-23
Task ID: RECON-018-DOCS-003
Agent: AG-018 Documentation Engineer
Branch: main
Published commit: 5f63b74ca0f54596ff83b1cdd5df02480b7a34da

## 1. Purpose

Update technical documentation to reflect the verified reconciliation results after the
permissions reconciliation phase. No source code or tests were modified by this task.

## 2. Verification basis

- `python3 tests/run_all.py`: ALL TESTS PASSED (31 suites).
- `tests/orchestration/test_structure.py`: PASS (8 tests).
- Quality Gate Runtime: PASS_WITH_OBSERVATIONS.
- SQLite integrity: ok (where applicable; no DB changes in this task).
- No commits, merges, releases, or deployments performed.

## 3. AG-003 identity model

- Normative catalog: 18 unique agent identities (AG-001..AG-018) under `agents/`.
  - AG-003 normative definition: `agents/management/ag-003-security-risk-manager.md`.
- Executable catalog: 19 files under `.opencode/agents/`.
  - The extra file is `ag-003-security-risk-assessor.md`, a documented specialization
    under the same AG-003 identity (vulnerability assessment, compliance, security
    requirements).
- No file rename, no ID change, no deletion. The normative AG-003 file references the
  assessor specialization at `.opencode/agents/ag-003-security-risk-assessor.md`.
- Proposal reference: `docs/execution/032_STAGE2O_AG003_IDENTITY_PROPOSAL.md`.
- Tests: `test_eighteen_agents_normative`, `test_nineteen_agents_executable`,
  `test_ag003_specialization_preserved` (all PASS).
- Further identity changes remain pending explicit user authorization.

## 4. Fallback design (BEAM_FREE_ONLY)

- Policy: BEAM_FREE_ONLY (`opencode-go/beam-free`) for all agents, sessions, workflows,
  and subprocesses (ADR-007).
- Authorized model set: `{opencode-go/beam-free}` (`AUTHORIZED_MODEL` /
  `AUTHORIZED_MODELS` in `orchestration/runtime/model_hierarchies.py`).
- `FALLBACK_ALTERNATIVES` is empty. There are no alternate models.
- Available models are discovered from the provider catalog via `opencode models`; the
  factory does not embed a hard-coded alternate model list and does not switch models.
- On quota exhaustion: the authorized model is marked unavailable and the manager waits
  for recovery (`WAITING_QUOTA_RESET`, default 3600s). No model switching occurs.
- On rate limit: wait `Retry-After` (default 60s) and retry the same model.
- On transient error: retry the same model.
- On auth error: `NEEDS_INTERVENTION`, no automatic change.
- On ambiguous error: abort, no automatic change.
- Recovery is detected by timestamp; there is no active provider quota query API.
- Future escape hatch (any alternate model or provider) requires explicit user
  authorization and a new ADR. It is not implemented.
- Investigation/ownership reference: AG-005 (Software Architect) fallback design
  investigation; ADR-007 records the policy decision.
- Current implementation files:
  - `orchestration/runtime/model_hierarchies.py`
  - `orchestration/runtime/model_fallback.py`
  - `orchestration/runtime/opencode_adapter.py`
  - `orchestration/runtime/runtime.py`

## 5. Version reconciliation

- Current development version: 0.6.6 (R5.2A + Stage 2G continuation, in progress).
- Published commit: `5f63b74ca0f54596ff83b1cdd5df02480b7a34da` (branch `main`).
- Tags through: `v0.6.5-r5.1` (at `e2c17d4`). No new tag created for 0.6.6; no
  release performed.
- Version strings updated by AG-001 in `README.md`, `PROJECT_CONTEXT.md`, and
  `PROJECT_STATUS.md`.
- `CHANGELOG.md` contains the 0.6.6 reconciliation-phase entry.

## 6. Reconciliation summary

### 6.1 Defects found

1. D1 — Executable agent count expectation.
   - Symptom: structure test expected 18 executable agents; repository has 19.
   - Root cause: AG-003 ships two documented specializations (manager + assessor)
     under one identity.
   - Correction: `tests/orchestration/test_structure.py` expectation updated to 19
     with documented rationale; no agent files changed.

2. D2 — Hard-coded absolute path in end-to-end test.
   - Symptom: `/home/developer/AI-Project-Factory` path broke portability.
   - Root cause: environment-specific path in test fixture.
   - Correction: replaced with repository-root derivation.

3. D3 — Version drift across context documents.
   - Symptom: mixed references to 0.6.5-r5.1 tags and published commit.
   - Root cause: reconciliation phase not yet reflected in all context docs.
   - Correction: version strings and CHANGELOG updated to 0.6.6 by AG-001; this task
     documents the reconciliation.

4. D4 — Stale fallback documentation.
   - Symptom: `MODEL_FALLBACK_*` docs described multi-model fallback and alternate
     models that are no longer implemented.
   - Root cause: docs predated BEAM_FREE_ONLY policy.
   - Correction: fallback design/implementation/validation docs updated in this task
     to reflect the single-model reality.

5. D5 — Normative permission reconciliation pending.
   - Symptom: normative `agents/` markdown has no executable permissions; executable
     `.opencode/agents/` hold V2 permissions.
   - Root cause: drift documented, reconciliation requires user authorization.
   - Correction: none in this task; remains pending authorization.

### 6.2 Corrections applied in this task

- Created/updated technical documentation (see section 7).
- No source code, tests, contracts, schemas, or configuration changed.
- No commits, merges, releases, or deployments.

### 6.3 Test results

| Check | Result |
|---|---|
| `python3 tests/run_all.py` | ALL TESTS PASSED (31 suites) |
| `tests/orchestration/test_structure.py` | PASS (8 tests) |
| Quality Gate Runtime | PASS_WITH_OBSERVATIONS |
| SQLite integrity | ok (no DB changes in this task) |

### 6.4 Limitations

- Normative `agents/` permissions are not reconciled (pending authorization).
- LXC fresh install is blocked (no container available); procedure documented.
- 47 Skills remain pending individual LIVE verification (quota).
- `tests/orchestration/test_model_fallback.py` and
  `tests/orchestration/test_model_fallback_integration.py` retain legacy multi-model
  assertions that predate BEAM_FREE_ONLY; they are not part of `tests/run_all.py` and
  were not modified by this task.
- No new tag or release created; version 0.6.6 remains a development version.

## 7. Files created/updated

Created:
- `docs/execution/RECON-018-DOCS-003.md` (this document).

Updated:
- `docs/architecture/MODEL_FALLBACK_DESIGN.md`
- `docs/architecture/MODEL_FALLBACK_IMPLEMENTATION.md`
- `docs/architecture/MODEL_FALLBACK_VALIDATION.md`
- `PROJECT_STATUS.md` (documentation reconciliation note)

## 8. Related references

- `docs/execution/032_STAGE2O_AG003_IDENTITY_PROPOSAL.md`
- `PROJECT_DECISIONS.md` (ADR-007 — BEAM_FREE_ONLY)
- `CHANGELOG.md` (0.6.6 entry)
- `tests/orchestration/test_structure.py`
- `orchestration/runtime/model_hierarchies.py`
- `orchestration/runtime/model_fallback.py`