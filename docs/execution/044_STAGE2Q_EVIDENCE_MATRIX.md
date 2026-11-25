# Stage 2Q — Evidence Matrix

Date: 2026-11-23
Branch: feature/model-fallback-manager

## Matriz de afirmaciones vs evidencia

| Afirmación | Código | Test | Evidencia LIVE | Resultado |
|---|---|---|---|---|
| Snapshots automáticos | runtime.py:_continuity_pre | tests/execution/test_snapshot.py | EXEC-0012 (2 snapshots verified) | LIVE_VERIFIED |
| Context assembly | runtime.py:_continuity_pre | tests/execution/test_context.py | EXEC-0012 (1 manifest verified) | LIVE_VERIFIED |
| Ledger automático | runtime.py:_continuity_pre | tests/execution/test_ledger.py | EXEC-0012 (1 ledger verified) | LIVE_VERIFIED |
| Recuperación entre sesiones | runtime.py:resume_interrupted_task | tests/execution/test_resume.py | EXEC-0016→EXEC-0017 (no duplication) | LIVE_VERIFIED |
| Prevención de duplicados | run_task idempotency + resume index | tests/execution/test_resume.py | EXEC-0016 (INTERRUPTED) + EXEC-0017 (COMPLETED) | LIVE_VERIFIED |
| Auditoría independiente | runtime.py:record_audit | tests/orchestration/test_runtime.py | 9 audits (AUDIT-0001..0009) | LIVE_VERIFIED |
| Permisos V2 | .opencode/agents/*.md | install/scripts/verify.sh | 19/19 load in OpenCode | LIVE_VERIFIED |
| Skills (5) | .opencode/skills/ | tests/skills/* | EXEC-0002/0007/0008/0009/0010 | LIVE_VERIFIED |
| BEAM_FREE_ONLY | opencode.json + runtime + adapter | tests/* | 17/17 executions beam-free | LIVE_VERIFIED |
| Delegación multiagente | runtime.py:run_task | tests/task_orchestration/* | EXEC-0003+0004, EXEC-0005+0006 | LIVE_VERIFIED |
| QA independiente | runtime.py:verify_acceptance | tests/* | 9 AV by AG-002 | LIVE_VERIFIED |
| SQLite persistencia | runtime.py | tests/orchestration/test_runtime.py | integrity ok, 17 execs | LIVE_VERIFIED |

## Afirmaciones NO verificadas (honestas)

| Afirmación | Estado | Razón |
|---|---|---|
| 54 Skills LIVE | NOT_TESTED (51) | Cuota. Solo 5 LIVE_VERIFIED. |
| LXC install | BLOCKED | No segundo contenedor disponible. |
| AG-003 formalización | REQUIRES_USER_APPROVAL | Pendiente autorización. |
| Permisos normativos reconciliados | NOT_TESTED | agents/ vs .opencode/agents/ drift documentado. |
| Automatic resume (sin intervención manual) | IMPLEMENTED | resume_interrupted_task existe pero requiere invocación manual. |
| Automatic snapshot during run_task | LIVE_VERIFIED | EXEC-0012 verified. |