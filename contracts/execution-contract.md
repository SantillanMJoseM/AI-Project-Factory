# Execution Contract

## Purpose

Defines how an agent execution is recorded and controlled.

## Required fields

- `execution_id`
- `task_id`
- `agent_id`
- `started_at`
- `status`
- `inputs`
- `outputs`
- `tools_used`
- `decisions`
- `errors`
- `completed_at`

## Statuses

Uses task states: PENDING, ASSIGNED, RUNNING, BLOCKED, REVIEW_REQUIRED, REJECTED, COMPLETED, FAILED, CANCELLED.

## Rules

1. Every execution must reference a valid task.
2. Every execution must record tools used.
3. Failed executions must include errors.
4. Executions requiring review must set REVIEW_REQUIRED.
5. No execution may alter audit results.