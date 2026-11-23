# Stage 2M — Baseline Report

Date: 2026-11-23
Branch: feature/model-fallback-manager
HEAD: f676d7116dcbf252dd5da0bb19c42e0b657a6e14

## 1. Inventario de mecanismos de continuidad existentes

### 1.1 Ejecución continua (orchestration/execution/)

| Componente | Archivo | Estado | Descripción |
|---|---|---|---|
| Modelos | models.py | IMPLEMENTED | TaskSnapshot, ContextManifest, LedgerEntry, ResumeEligibility, GitAnchor, FileRef, SkillPin, LedgerWindow |
| Ledger | ledger.py | IMPLEMENTED | Append-only JSONL, hash-chained, verify_ledger, verify_chain_head |
| Snapshots | snapshot.py | IMPLEMENTED | create_snapshot, load_snapshot, verify_snapshot, list_snapshots, latest_snapshot |
| Contexto | context.py | IMPLEMENTED | assemble_context, load_manifest, check_staleness, rebuild_for_resume, find_manifest_by_hash |
| Resume | resume.py | IMPLEMENTED | evaluate_resume, start_resume, ResumeDecision, resume index, duplicate prevention |
| Documentos | documents.py | IMPLEMENTED | Execution document management |
| CLI | cli.py | IMPLEMENTED | CLI for execution continuity |
| Context integration | context_integration.py | IMPLEMENTED | Bridge to runtime |

### 1.2 Runtime (orchestration/runtime/)

| Componente | Archivo | Estado | Descripción |
|---|---|---|---|
| Runtime DB | runtime.py | IMPLEMENTED | SQLite, projects, tasks, executions, events, audits, delegations, leases |
| Model fallback | model_fallback.py | IMPLEMENTED | BEAM_FREE_ONLY availability manager |
| OpenCode adapter | opencode_adapter.py | IMPLEMENTED | Sandbox + direct invocation, model enforcement |
| Sandbox | sandbox.py | IMPLEMENTED | Private opencode serve inside unshare |

### 1.3 Task orchestration (orchestration/task_orchestration/)

| Componente | Archivo | Estado | Descripción |
|---|---|---|---|
| Engine | engine.py | IMPLEMENTED | Plan analysis, task graph, waves, delegation |
| Delegation | delegation.py | IMPLEMENTED | DelegationManager, create/track/verify/revoke |
| Models | models.py | IMPLEMENTED | Task, TaskGraph, DelegationRecord, OrchestrationPlan, CoordinationState |
| Coordination | coordination.py | IMPLEMENTED | Read model, state consolidation |
| Model fallback integration | model_fallback_integration.py | IMPLEMENTED | Bridge to runtime fallback manager |

## 2. Qué funciona realmente

- **Ledger**: Append-only, hash-chained JSONL. Verified by tests (test_ledger.py PASS).
- **Snapshots**: Hashed, commit-anchored checkpoints. Verified by tests (test_snapshot.py PASS).
- **Context manifests**: Tiered context (T0-T3), staleness detection. Verified by tests (test_context.py PASS).
- **Resume engine**: Fail-closed eligibility, duplicate prevention, resume index. Verified by tests (test_resume.py PASS).
- **Runtime DB**: SQLite with 14 tables, integrity ok. Projects, tasks, executions, audits persisted.
- **Delegation**: DelegationManager with create/track/verify/revoke. Verified by tests (test_delegation.py PASS).
- **Task graph**: Dependency-aware, wave-based parallelism. Verified by tests (test_parallel.py PASS).

## 3. Qué es solamente documentación

- Context snapshots (`.ai/context/` or `projects/<ID>/execution/snapshots/`) are NOT automatically created during runtime.run_task. They exist as infrastructure but are not wired into the runtime execution path.
- Resume between sessions requires manual invocation of evaluate_resume/start_resume.
- Context manifests are assembled manually, not automatically during task execution.

## 4. Qué información se pierde ante una interrupción

- Runtime.run_task persists execution results to SQLite (executions table) and model_fallback_log.
- But snapshots, ledgers, and context manifests are NOT created automatically during run_task.
- Session-level context (conversation) is lost; only persisted DB records survive.
- Partial results from interrupted agents may be lost if not persisted before interruption.

## 5. Mecanismo de último estado consistente

- SQLite executions table records status (RUNNING/COMPLETED/FAILED/BLOCKED).
- model_fallback_log records model effective.
- Task status in tasks table.
- But no automatic snapshot/checkpoint is created during execution.

## 6. Cómo se evita repetir tareas completadas

- run_task has idempotency: if task is COMPLETED/REVIEW_REQUIRED, returns existing execution.
- DelegationManager prevents duplicate resumes (resume index).
- Task graph prevents duplicate task IDs.

## 7. Modificaciones mínimas necesarias

- Wire snapshot creation into run_task (optional, for continuity).
- Wire context manifest assembly into run_task (optional).
- The existing infrastructure is sufficient; integration is the gap.

## 8. Estado Git

- Branch: feature/model-fallback-manager. No commits/merges.
- Tracked modifications + untracked artifacts.

## 9. Backups

- Latest: backups/AI-Project-Factory-pre-2j-20261123123555.tar.gz (SHA256: 0f5dc478...)
- Copies (not moves). Integrity verified.

## 10. Gate A

- Inventario completado. Mecanismos existentes documentados. Proceder a Fase B (diseño).