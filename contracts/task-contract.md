# Task Contract

## States

PENDING, ASSIGNED, RUNNING, BLOCKED, REVIEW_REQUIRED, REJECTED, COMPLETED, FAILED, CANCELLED.

## Allowed transitions

- PENDING -> ASSIGNED
- ASSIGNED -> RUNNING
- RUNNING -> BLOCKED
- RUNNING -> REVIEW_REQUIRED
- RUNNING -> COMPLETED
- RUNNING -> FAILED
- BLOCKED -> RUNNING
- BLOCKED -> CANCELLED
- REVIEW_REQUIRED -> COMPLETED
- REVIEW_REQUIRED -> REJECTED
- REJECTED -> RUNNING
- FAILED -> PENDING
- Any non-terminal -> CANCELLED

No other transitions are allowed.

## Required fields

- `id`
- `title`
- `description`
- `status`
- `priority`
- `assigned_agent`
- `inputs`
- `outputs`
- `acceptance_criteria`
- `quality_gates`
- `created_at`
- `updated_at`

## Rules

1. A task cannot move to COMPLETED without satisfying acceptance criteria.
2. A task cannot move to COMPLETED if a required Quality Gate is FAIL or BLOCKED.
3. A task in REVIEW_REQUIRED requires an independent review.
4. Cancellation requires a reason.