# PROJECT_HANDOFF

## Current state

Stage 2G continuation completed on branch `feature/model-fallback-manager`. All agents restricted to `opencode-go/beam-free` (BEAM_FREE_ONLY). Real delegation, QA and independent audit demonstrated and persisted in SQLite.

## What was being done

Recovered project state, enforced beam-free-only model policy across config, agents, runtime and fallback manager, and executed one controlled live delegation (AG-018) with independent QA (AG-002) and audit (AG-015).

## Completed

- opencode.json: model set to opencode-go/beam-free; Ollama provider removed.
- All 19 executable agent definitions: model set to opencode-go/beam-free.
- model_hierarchies.py: fallback alternatives removed; authorized set = {beam-free}.
- model_fallback.py: single-model availability management; no model switching.
- opencode_adapter.py: rejects non-authorized models; tags results with effective model.
- runtime.py: run_task/run_workflow enforce BEAM_FREE_ONLY; records model in decisions.
- tests/task_orchestration/test_coordination.py: adapted to beam-free-only policy.
- Real live test: PROJECT-001 / TASK-0001 (AG-018) / EXEC-0001 COMPLETED, model_effective=beam-free.
- QA: AV-0001 by AG-002; task COMPLETED.
- Audit: AUDIT-0001 by AG-015, verdict PASS.
- Documentation: ADR-007 recorded.

## Pending

- Independent AG-013 code review of Stage 2G changes (quota permitting).
- Fresh LXC install on a second container when available.
- Reconcile normative `agents/` permissions with `.opencode/agents/`.

## Modified files

See Git diff on `feature/model-fallback-manager`.

## Decisions taken

- ADR-001 to ADR-007 in force. ADR-007 establishes BEAM_FREE_ONLY.
- No fallback to other models under any circumstance.

## Problems found

- None blocking; quota respected (single controlled live test).

## Tests executed and results

- Factory: `python3 tests/run_all.py` — ALL TESTS PASSED.
- install/scripts/verify.sh — ALL CHECKS PASSED.
- SQLite integrity_check — ok.

## Last valid commit

f676d7116dcbf252dd5da0bb19c42e0b657a6e14 (feature/model-fallback-manager)

## Instructions to continue

Review changes, decide on commit/merge. Keep beam-free-only policy.