# Model Fallback Contract

> **SUPERSEDED in part by ADR-007 (BEAM_FREE_ONLY).** This contract describes an ordered multi-model fallback hierarchy that is no longer permitted. Under ADR-007 the only authorized model is `opencode-go/beam-free` and `FALLBACK_ALTERNATIVES` is empty. See `docs/architecture/MODEL_FALLBACK_DESIGN.md` and `orchestration/runtime/model_hierarchies.py`. Retained for historical reference.

## Purpose

Define the contract for centralized model selection, fallback, and recovery for AI-Project-Factory agents.

## Provider Constraint

All models MUST belong to `opencode-go` (OpenCode Go subscription). No external providers, no paid models, no extra usage.

## Agent Hierarchy

Each agent AG-001..AG-018 MUST have an ordered list of models:
1. Primary model (from agent front-matter `model:`).
2. Second best alternative compatible with specialty.
3. Third best alternative.
4. Additional available alternatives.

## Error Classification

The fallback manager MUST classify errors into:
- `quota_exhausted`: model quota depleted → select next alternative.
- `rate_limit`: temporary hourly/window limit → wait Retry-After, retry same model.
- `transient`: network/timeout/5xx → exponential backoff, retry same model.
- `auth`: authentication/configuration error → NEEDS_INTERVENTION, no automatic change.
- `ambiguous`: unclassifiable → log, controlled check, no automatic change.

## Task Continuity

When switching models:
- Preserve task_id, context, previous results, artifacts.
- Do not restart completed phases.
- Do not duplicate operations.
- Operations MUST be idempotent or verify state before repeating.

## Recovery

When primary model recovers:
- Detect recovery.
- Do not interrupt critical operation.
- Prioritize primary in next task or safe continuation point.
- Avoid constant model switching.

## Audit

Every execution MUST log: agent, task_id, primary_model, effective_model, fallback_model, reason, provider, started_at, wait_seconds, retries, status, error_message.

## States

RUNNING, WAITING_RATE_LIMIT, WAITING_QUOTA_RESET, FALLBACK_ACTIVE, COMPLETED, FAILED, NEEDS_INTERVENTION.
