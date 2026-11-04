# Task Lifecycle Workflow

## States

PENDING -> ASSIGNED -> RUNNING -> REVIEW_REQUIRED -> COMPLETED.

Alternative paths: BLOCKED, REJECTED, FAILED, CANCELLED per Task Contract.

## Rules

- Tasks are assigned to one agent.
- Status changes must follow allowed transitions.
- Completion requires acceptance criteria and Quality Gates.