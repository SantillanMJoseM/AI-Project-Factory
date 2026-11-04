# Coordination Contract

## Purpose

Defines how AG-001 coordinates tasks, delegation, state tracking, correction loops, and final reporting.

## Task record fields

- task_id
- project
- assigned_agent
- objective
- context
- dependencies
- priority
- acceptance_criteria
- deliverables
- status
- retry_count
- max_retries
- created_at
- updated_at

## Delegation record fields

- delegation_id
- task_id
- from_agent
- to_agent
- requested_at
- completed_at
- result
- evidence

## Rules

1. Every task has one owner.
2. Dependencies must be COMPLETED before dependent task starts.
3. Retry count cannot exceed max_retries (default 3).
4. Rejected tasks return to RUNNING with a correction assignment.
5. No automatic advancement after FAIL or BLOCKED.