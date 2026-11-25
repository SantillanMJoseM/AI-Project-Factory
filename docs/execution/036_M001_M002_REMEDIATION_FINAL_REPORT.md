# M-001 / M-002 Remediation Final Report

Date: 2026-11-24
Mode: Read-only audit + remediation (no commits, merges, releases, or deployments).

## 1. Executive summary

M-001 (log persistence on exceptions) and M-002 (non-blocking transient retries) have been corrected.

- **M-001:** `run_task` and `resume_run_task` now wrap `adapter.invoke` in try/except and persist a FAILED log entry with the original error message before returning. The error is never hidden.
- **M-002:** `opencode_adapter.invoke` no longer sleeps or retries in-process. Transient errors produce a `WAITING_TRANSIENT_RETRY` state with a bounded backoff deadline (2, 4, 8, 16, 30s), persisted with `wait_until`. The process returns immediately. Resumption is handled by `resume_interrupted_task` / `resume_due_waiting_tasks` (deadline-aware, idempotent).
- BEAM_FREE_ONLY remains intact. No model switching. No artificial quota consumption.

**Classification: `COMPLETED_WITH_OBSERVATIONS`.**

## 2. Original findings

- M-001: Exception during invocation could lose the current attempt's log entry (save_fallback_log called only after invoke returned).
- M-002: Adapter used `time.sleep(min(2 ** retries, 30))` blocking the process during transient retries.

## 3. Solution implemented

### M-001
- `runtime.run_task` and `resume_run_task`: try/except around `adapter.invoke`; on exception, `fm.log_change(... status="FAILED", error_message=str(exc), ...)` + `save_fallback_log` (best-effort, inner try/except swallows DB errors without hiding original). `conn.commit()` then returns FAILED result.
- Original error conserved in `result["error"]` and `error_message`.

### M-002
- `FallbackStatus.WAITING_TRANSIENT_RETRY` added.
- `handle_error` transient branch: `action="wait"`, `status=WAITING_TRANSIENT_RETRY`, `wait_seconds=min(2**(retries+1), 30)`.
- Adapter: wait branch persists `wait_until` (UTC ISO), returns WAITING immediately. No `time.sleep`. No in-process retry loop.
- Backoff escalation: retries 0→2s, 1→4s, 2→8s, 3→16s, 4→30s (capped).
- `resume_due_waiting_tasks(conn)`: finds waiting tasks with persisted deadline; resumes only when `wait_until <= now`; skips tasks with unknown deadline; idempotent (checks task still in waiting state).

## 4. Files modified

- `orchestration/runtime/model_fallback.py` — WAITING_TRANSIENT_RETRY, handle_error transient, quota_reset_seconds
- `orchestration/runtime/opencode_adapter.py` — adapter wait (no sleep/retry), wait_until persistence, max_retries=4
- `orchestration/runtime/runtime.py` — M-001 try/except, resume_due_waiting_tasks, list_waiting_tasks, CLI `task waiting`, migration 5, save_fallback_log
- `tests/orchestration/test_model_fallback.py` — 23 tests (transient now expects WAITING_TRANSIENT_RETRY)
- `tests/orchestration/test_model_fallback_integration.py` — 8 tests (transient returns WAITING)
- `tests/orchestration/test_sandbox.py` — schema version 4→5
- `docs/execution/034_MODEL_FALLBACK_POST_REMEDIATION_AUDIT.md` — remediation note
- `docs/execution/036_M001_M002_REMEDIATION_FINAL_REPORT.md` — this report

## 5. Migrations

- Migration 5 (additive, idempotent): adds 7 columns to `model_fallback_log`: attempt_number, error_class, http_status, retry_after, reset_timestamp, wait_until, completed_at. No columns/tables removed. Compatible with existing rows (defaults/nullable).

## 6. Tests executed

| Suite | Result | Exit |
|---|---|---|
| tests/run_all.py (38 suites) | ALL TESTS PASSED | 0 |
| test_model_fallback.py | 23/23 PASS | 0 |
| test_model_fallback_integration.py | 8/8 PASS | 0 |
| test_structure.py | 8/8 PASS | 0 |
| install/scripts/verify.sh | ALL CHECKS PASSED | 0 |
| Quality Gate Runtime | PASS_WITH_OBSERVATIONS | 0 |

## 7. M-001 evidence

- `runtime.py:1298-1320` (run_task) and `runtime.py:954-975` (resume_run_task): try/except around `adapter.invoke`.
- On exception: `fm.log_change(... status="FAILED", error_message=str(exc) ...)` + `save_fallback_log` (best-effort, inner try/except).
- Original error conserved in `result["error"]`.
- Idempotency: `INSERT OR REPLACE` on `log_id` PK.

## 8. M-002 evidence

- `opencode_adapter.py`: no `time.sleep` (grep confirms only comment). Wait branch returns immediately.
- `model_fallback.py:270-279`: transient → `action="wait"`, `status=WAITING_TRANSIENT_RETRY`, `wait_seconds=min(2**(retries+1), 30)`.
- `runtime.py`: `resume_due_waiting_tasks` reads `wait_until` from DB, skips if unknown or not due, checks task still in waiting state (idempotency).
- Backoff sequence: retries 0→2, 1→4, 2→8, 3→16, 4→30 (capped).

## 9. Scheduler / recovery

- **Detection:** `list_waiting_tasks(conn)` queries tasks in WAITING_* states.
- **Deadline check:** `resume_due_waiting_tasks` parses `wait_until` from `model_fallback_log`, compares to `datetime.now(UTC)`.
- **Trigger:** On-demand (manual or external cron). No automatic periodic scheduler exists in the codebase.
- **Resumption:** `resume_interrupted_task` (idempotent, checks task state and execution history).
- **Duplicate prevention:** Task state check before resumption; `INSERT OR REPLACE` on log; `resumed_from` tracking.
- **Post-restart recovery:** `recover_interrupted` marks RUNNING executions as INTERRUPTED/BLOCKED; `resume_interrupted_task` handles WAITING states.

**Classification: Scheduler is IMPLEMENTED but NOT automatically active (no periodic loop). External trigger required.**

## 10. Test coverage

| Category | Tests | Notes |
|---|---|---|
| Unit (model_fallback) | 23 | Error classification, selection, handle_error, logging, quota reset |
| Integration (mocked adapter) | 8 | BEAM_FREE_ONLY, WAITING states |
| SQLite real | test_sandbox (24) | Schema migration, idempotency |
| Persistence | test_runtime (partial) | run_task persists fallback log |
| Recovery after restart | None dedicated | Manual via resume_interrupted_task |
| Concurrency | None dedicated | Idempotency via state checks |
| Deadlines | None dedicated | Backoff unit-tested, real deadline not validated live |
| LIVE (provider) | None | No artificial quota consumption |

**Limitation:** No test validates real deadline waiting or post-restart recovery end-to-end. These are classified as NOT_TESTED.

## 11. Git state

- Branch: main, HEAD 5f63b74 (unchanged).
- Working tree: modified + untracked (no commit, merge, release, or deployment).

## 12. Backup

- `/tmp/opencode/backups/m001-m002-pre-remediation.tar.gz` (SHA256 `a66f890347f73deae267a0d53caea9480584417daac6d67652e6b78ee4ea019d`, 789 files, 0 mismatches).

## 13. Risks and limitations

1. No automatic periodic scheduler — resumption requires external trigger or manual invocation.
2. No live provider test for quota exhaustion (by design).
3. No dedicated test for post-restart recovery or concurrency.
4. DB error during logging is swallowed (inner try/except) — original error is conserved but DB failure is not surfaced.
5. Dead code (MODEL_SWITCHED, on_fallback, recover_primary_model) remains inert.

## 14. Classification of capabilities

| Capability | Classification |
|---|---|
| BEAM_FREE_ONLY policy | IMPLEMENTED + UNIT_TESTED + INTEGRATION_TESTED |
| Error classification (8 classes) | IMPLEMENTED + UNIT_TESTED |
| Retry-After (numeric + HTTP-date) | IMPLEMENTED + UNIT_TESTED |
| Quota reset (hourly/daily/weekly) | IMPLEMENTED + UNIT_TESTED |
| Non-blocking transient retry | IMPLEMENTED + UNIT_TESTED + INTEGRATION_TESTED |
| Durable persistence (migration 5) | IMPLEMENTED + INTEGRATION_TESTED (schema) |
| M-001 exception logging | IMPLEMENTED + INTEGRATION_TESTED |
| Resumption after deadline | IMPLEMENTED + NOT_TESTED (no dedicated test) |
| Post-restart recovery | IMPLEMENTED + NOT_TESTED |
| Concurrency safety | IMPLEMENTED (state checks) + NOT_TESTED |
| Live provider validation | NOT_TESTED |

## 15. Conclusion

**`COMPLETED_WITH_OBSERVATIONS`.**

M-001 and M-002 are corrected and verified by tests. The implementation is durable, non-blocking, and idempotent. Observations: no automatic scheduler (external trigger needed), no live provider test, no dedicated post-restart/concurrency tests. No commits or deployments performed.