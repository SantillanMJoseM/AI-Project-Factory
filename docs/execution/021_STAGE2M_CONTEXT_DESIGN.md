# Stage 2M — Context Design

Date: 2026-11-23
Branch: feature/model-fallback-manager

## 1. Mecanismo existente

El sistema de continuidad operativa ya existe en `orchestration/execution/` (Stage 2A). No se duplica; se documenta y valida.

### 1.1 Snapshots (orchestration/execution/snapshot.py)

- Ubicación: `projects/<PROJECT_ID>/execution/snapshots/SNAP-<PROJECT_ID>-<EXEC-NNNN>-<seq>.json`
- Contenido: identidad de ejecución, anchors Git, hash de context manifest, file set con SHA-256 por archivo, file-set root hash, skill set pinned, model binding, ledger window, resume eligibility, snapshot hash.
- Append-only: snapshots superseded se marcan vía `supersedes`, nunca se eliminan.
- Hash: canonical JSON con campo `snapshot_hash` excluido (§7).

### 1.2 Context manifests (orchestration/execution/context.py)

- Ubicación: `projects/<PROJECT_ID>/execution/context/CTX-<EXEC-NNNN>-<seq>.json`
- Tiers: T0 (bootstrap), T1 (task), T2 (skills), T3 (working set).
- Budgeting: trim T3 then T2 under token budget; trimmed items recorded in `excluded_for_budget`.
- Staleness: re-fingerprint at consumption; governed-file divergence blocks execution.

### 1.3 Ledger (orchestration/execution/ledger.py)

- Ubicación: `projects/<PROJECT_ID>/execution/ledger/LEDGER-<EXEC_NNNN>.jsonl`
- Append-only JSONL, hash-chained (payload_hash, prev_hash, record_hash).
- Eventos: EXECUTION_OPENED, STATE_CHANGED, CONTEXT_ASSEMBLED, SKILL_INVOKED, TOOL_USED, FILE_CHANGED, CHECKPOINT_WRITTEN, COMMIT_ANCHOR, MODEL_BOUND, MODEL_SWITCHED, LEASE_EXPIRED, FAILURE_CLASSIFIED, RESUME_REQUESTED, RESUME_STARTED, RECOVERY_BLOCKED, APPROVAL_REQUESTED, EXECUTION_TERMINAL, DOC_SUPERSEDED, SKILL_DRIFT.

### 1.4 Resume (orchestration/execution/resume.py)

- Evaluación fail-closed (6 cláusulas de elegibilidad §4.3).
- start_resume: journal source, open successor, register in resume index.
- Duplicate prevention: each execution resumed at most once.
- Resume budget: ≤2 auto-resumes per failure signature.

## 2. Estructura de snapshots

Cada snapshot contiene:
- snapshot_id, project_id, execution_id, task_id, agent_id, created_at
- reason (SnapshotReason)
- git (branch, before_commit, after_commit)
- working_directory
- context_manifest_hash
- file_set (path + sha256 per file)
- file_set_root_hash
- skill_set (skill_id, content_hash, registry_version)
- model_binding
- ledger (path, seq_from, seq_to, chain_head_hash)
- resume_eligibility (eligible, requires_approval, notes)
- supersedes
- snapshot_hash

## 3. Diferenciación de estados

- COMPLETED: tarea completada con evidencia.
- IN_PROGRESS: en ejecución.
- PENDING: pendiente.
- BLOCKED: bloqueada (dependencias, cuota, permisos).
- FAILED: fallida.
- NOT_TESTED: no probada.

## 4. Historial inmutable

- Snapshots: append-only, superseded via `supersedes`.
- Ledger: append-only JSONL, never rewritten.
- Resume index: append-only.
- SQLite: events table immutable (triggers prevent update/delete).

## 5. Integración con runtime

- El runtime (orchestration/runtime/runtime.py) persiste en SQLite (projects, tasks, executions, events, audits).
- El sistema de ejecución (orchestration/execution/) persiste snapshots, ledgers, context manifests en el filesystem.
- La integración entre ambos es manual (no automática en run_task).
- Gap identificado: run_task no crea snapshots/ledgers automáticamente.

## 6. Conclusión

La infraestructura de continuidad existe y está probada (tests pass). La integración automática con runtime es el gap principal, documentado para futura implementación.