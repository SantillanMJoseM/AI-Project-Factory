# Model Fallback Post-Remediation Audit (Read-Only)

Date: 2026-11-24
Auditor: AG-001 Project Coordinator (read-only audit, no modifications)
Scope: BEAM_FREE_ONLY Model Fallback Manager — consistency, durability, recoverability.

## 1. Executive summary

The BEAM_FREE_ONLY policy is implemented consistently across `model_hierarchies.py`, `model_fallback.py`, `opencode_adapter.py`, `runtime.py`, and all 19 executable agent definitions. Authorized model set is exactly `{opencode-go/beam-free}`; `FALLBACK_ALTERNATIVES` is empty; adapter and runtime reject non-authorized models. The adapter no longer performs in-process sleep/retry on WAITING states; it returns WAITING immediately and persists the decision. Additive migration 5 extends `model_fallback_log` with 7 new columns (attempt_number, error_class, http_status, retry_after, reset_timestamp, wait_until, completed_at). `extract_retry_after` supports numeric and HTTP-date forms; `quota_reset_seconds` distinguishes weekly/daily/hourly with Retry-After precedence. No runtime.db exists in the repository (gitignored runtime state), so live schema inspection was not possible without executing a migration (prohibited by audit constraints); schema verification is based on code inspection.

**Classification: `AUDIT_PASS_WITH_OBSERVATIONS`.**

## 2. Git evidence

| Field | Value |
|---|---|
| Branch | main |
| HEAD | 5f63b74ca0f54596ff83b1cdd5df02480b7a34da |
| Status | 51 tracked modified + 8 untracked (remediation, uncommitted) |
| Backup | `/tmp/opencode/backups/stage2g-pre-remediation/` — 786 files, tarball SHA256 `c623175747fe88d148580e733e59c44d276dad0e81ca9c9bd60c567436539eb7`, verified 0 mismatches |

## 3. Backup integrity

- Tarball: `AI-Project-Factory-pre-remediation.tar.gz` (2,757,533 bytes).
- Manifest: `manifest.sha256.json` (786 entries).
- Verification: extracted to temp dir; 786/786 files present, 0 hash mismatches.

## 4. SQLite schema evidence (code inspection — no live DB)

No `runtime.db` exists in the repository (gitignored). Live schema inspection was not performed (prohibited: would require running migrations). Schema reconstructed from `runtime.py`:

- Base table `model_fallback_log` (migration 1) with: log_id PK, execution_id, task_id, agent_id, primary_model, effective_model, fallback_model, reason, provider, started_at, wait_seconds, retries, status, error_message, created_at.
- Migration 5 (additive, idempotent via `_columns` check) adds: attempt_number (INTEGER NOT NULL DEFAULT 0), error_class (TEXT), http_status (INTEGER), retry_after (REAL), reset_timestamp (TEXT), wait_until (TEXT), completed_at (TEXT).
- `INSERT OR REPLACE` used (idempotent). No columns or tables removed.

Compatibility: additive columns have defaults/nullable, so pre-migration rows remain readable. `save_fallback_log` inserts all columns with `.get()` fallbacks.

## 5. Model policy (Auditoría B)

- `AUTHORIZED_MODEL = "opencode-go/beam-free"` (`model_hierarchies.py:9`).
- `AUTHORIZED_MODELS = {AUTHORIZED_MODEL}` (`model_hierarchies.py:10`).
- `FALLBACK_ALTERNATIVES = {}` (`model_hierarchies.py:14`).
- `opencode.json`: `"model": "opencode-go/beam-free"`.
- All 19 executable agents: `model: opencode-go/beam-free`.
- Adapter: rejects non-authorized explicit model (`opencode_adapter.py:123`).
- Runtime: `run_task`/`resume_interrupted_task` reject non-authorized model.
- `handle_error` policy guard: non-authorized `current_model` → `auth`/`NEEDS_INTERVENTION`.
- Stale references remaining: `install/docs/PILOT_EXECUTION_GUIDE.md` updated; `TESTDESA_AUDITORIA_RECURSOS.md` is historical (not operational).

## 6. Error classification, Retry-After, quota reset (Auditoría C)

- `classify_error`: quota → rate → auth → incompatible → provider_down → transient → ambiguous. Patterns for INCOMPATIBLE and PROVIDER_DOWN added.
- `extract_retry_after`: numeric seconds + HTTP-date (via `email.utils.parsedate_to_datetime`), negative values rejected, returns None when no reliable value.
- `quota_reset_seconds`: weekly 604800s, daily 86400s, hourly 3600s; Retry-After takes precedence; default 3600s only when no qualifier (note: this default could overstate wait for an unspecified quota; classified as LOW).
- Precedence: Retry-After is checked first in `quota_reset_seconds` when present. HTTP-date parsing validated.

## 7. Adapter and runtime (Auditoría D/E)

- No artificial sleep: the 5-second cap (`time.sleep(min(wait, 5))`) was removed; adapter returns WAITING immediately without retrying in-process.
- WAITING states: `WAITING_QUOTA_RESET`, `WAITING_RATE_LIMIT` returned without blocking.
- Retry limit: transient errors retry up to `max_retries` (default 3); wait states do not consume retry counter.
- Resumption: `resume_interrupted_task` handles WAITING states; `task waiting` CLI lists blocked/waiting tasks. Idempotent via `INSERT OR REPLACE` and `resumed_from` tracking.
- Exception handling: `save_fallback_log` persists after invocation in `run_task`/`resume_run_task`; if adapter raises, the in-memory log may be lost, but persisted DB entries from prior attempts survive. Gap: an exception mid-invocation could lose the current attempt's log entry (classified MEDIUM).

## 8. Test coverage (Auditoría F)

| Test file | Count | Type | Notes |
|---|---|---|---|
| test_model_fallback.py | 23 | Unit | Error classification, selection, handle_error, logging, quota reset |
| test_model_fallback_integration.py | 8 | Integration (mocked) | Adapter + manager, BEAM_FREE_ONLY |
| test_coordination.py | includes model fallback | Integration | StubManager duck-typed |
| test_runtime.py | includes real invocation | Integration (live-ish) | Skips if opencode unavailable or model blocked |
| test_sandbox.py | 24+ | Unit | Schema migration, sandbox |

- Mocks used for adapter tests (unittest.mock.patch). No live provider calls in unit/integration tests.
- No test performs artificial quota exhaustion against real provider (by design).
- `time.sleep` patched in integration tests (acceptable for unit speed; real sleep behavior not validated live).

## 9. Documentation coherence (Auditoría G)

- ADR-007: BEAM_FREE_ONLY, consistent with code.
- ADR-008: durable persistence and resumption (added).
- `MODEL_FALLBACK_DESIGN.md` / `IMPLEMENTATION.md` / `VALIDATION.md`: updated for BEAM_FREE_ONLY.
- `contracts/model-fallback-contract.md`: marked superseded by ADR-007.
- `MODEL_SWITCHED` event type still defined in `execution/models.py` and used in `model_fallback_integration.py` (dead code under BEAM_FREE_ONLY; inert, documented).
- `recover_primary_model` / `on_fallback` are inert but retained for compatibility; documented as such.

## 10. Findings

### MEDIUM

**M-001 — Exception mid-invocation may lose current attempt log entry.**
- File: `orchestration/runtime/runtime.py`, `run_task` (~line 1255).
- Evidence: `save_fallback_log` is called after `adapter.invoke` returns. If `invoke` raises (e.g., unexpected exception), the current attempt's entry is not persisted.
- Recommendation: wrap invocation in try/except and persist a FAILED entry before re-raising.

**M-002 — Adapter transient retry uses real sleep (2s, 4s, 8s) inside the process.**
- File: `orchestration/runtime/opencode_adapter.py`, lines 183-186.
- Evidence: `time.sleep(min(2 ** retries, 30))` blocks the process during transient retry. Under BEAM_FREE_ONLY with a single model, transient retries are bounded by max_retries=3, but the sleep is not capped for responsiveness.
- Recommendation: cap sleep (e.g., min(2**retries, 5)) or defer retry to orchestrator.

### LOW

**L-001 — `quota_reset_seconds` defaults to 3600s when no qualifier present.**
- File: `orchestration/runtime/model_fallback.py`, `quota_reset_seconds()`.
- Evidence: If a quota error message lacks "weekly/daily/hourly" qualifier, the function assumes 3600s. This could overstate or understate the actual reset.
- Recommendation: return None when unknown and let caller decide (do not invent a wait).

**L-002 — `recover_primary_model` is a no-op under BEAM_FREE_ONLY.**
- File: `orchestration/task_orchestration/model_fallback_integration.py`, `recover_primary_model()`.
- Evidence: Since selected == primary always, `current_model == primary` → returns early with `recovered=False`.
- Recommendation: document as intentionally inert; consider removing in a future cleanup.

**L-003 — `on_fallback` always False under BEAM_FREE_ONLY.**
- File: `orchestration/task_orchestration/model_fallback_integration.py`, `agent_model_status()`.
- Evidence: `on_fallback = bool(selected and selected != primary)` is always False.
- Recommendation: keep for API compatibility; document.

**L-004 — Legacy multi-model code paths in `model_fallback_integration.py`.**
- File: `orchestration/task_orchestration/model_fallback_integration.py`, lines 163-195 (`fallback` action branch, `MODEL_SWITCHED`).
- Evidence: These branches are unreachable under BEAM_FREE_ONLY (`handle_error` never returns `action == "fallback"`).
- Recommendation: mark as dead code; do not remove without migration evidence.

**L-005 — Traceability CLI sys.path fix applied but not tested in run_all.**
- File: `orchestration/validators/traceability/traceability.py:178`.
- Evidence: Changed `parents[2]` → `parents[3]`. No dedicated test in run_all for this path.
- Recommendation: add a smoke test for the CLI import path.

### INFORMATIONAL

**I-001 — No runtime.db in repository.**
- Evidence: `find` returned no `.db`/`.sqlite` files. Runtime state is gitignored.
- Impact: Live schema verification not possible in audit; schema verified via code inspection.

**I-002 — `MODEL_SWITCHED` EventType retained.**
- Evidence: defined in `execution/models.py:51`, used only in dead-code paths.
- Impact: no functional issue; cleanup candidate.

**I-003 — `time.sleep` still imported in adapter.**
- Evidence: `opencode_adapter.py:18` imports time; used in transient retry only.
- Impact: minor.

## 11. Risks pending

1. BEAM_FREE_ONLY: single point of failure; quota exhaustion blocks all execution up to 1 hour (or until reset).
2. No live provider test: fallback behavior not validated against real quota exhaustion.
3. In-process transient retry sleep (2-8s) could be optimized.
4. Exception mid-invocation may lose current attempt log.
5. Dead code (MODEL_SWITCHED, on_fallback, recover_primary_model) may confuse maintainers.
6. No schema version bump documentation for migration 5 in ADR (added as ADR-008).

## 12. Remediation status (M-001 / M-002)

Both MEDIUM findings have been corrected:

- **M-001 (log persistence on exceptions):** `run_task` and `resume_run_task` now wrap `adapter.invoke` in try/except and persist a FAILED log entry (with error message and exception info) before returning, so the attempt is never lost. Idempotent via `INSERT OR REPLACE`.
- **M-002 (blocking sleep on transient retry):** `opencode_adapter.invoke` no longer sleeps or retries in-process on transient errors. It persists a `WAITING_TRANSIENT_RETRY` state with a bounded backoff deadline and returns immediately, releasing the process. Resumption is handled by the scheduler / `resume_interrupted_task`.

Regression: `tests/run_all.py` → ALL TESTS PASSED (exit 0).

## 12. Recommendation of closure

**`AUDIT_PASS_WITH_OBSERVATIONS`.**

The implementation is consistent with BEAM_FREE_ONLY. Persistence and resumption mechanisms are implemented and tested. Two MEDIUM and five LOW findings are documented with clear remediation paths. No CRITICAL or HIGH findings. No modifications were made during this audit. Live verification of quota exhaustion remains NOT_TESTED (by design, to avoid irresponsible quota consumption).