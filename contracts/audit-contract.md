# Audit Contract

## Purpose

Defines independent audit structure and verdicts.

## Verdicts

- PASS
- PASS_WITH_OBSERVATIONS
- FAIL
- BLOCKED

## Required fields

- `audit_id`
- `scope`
- `auditor`
- `audited_artifacts`
- `findings`
- `verdict`
- `evidence`
- `created_at`

## Rules

1. Auditor must be independent from developer.
2. Audit results cannot be modified by audited agents.
3. FAIL or BLOCKED prevents release.
4. Observations must be documented.
5. Evidence must reference files or test output.