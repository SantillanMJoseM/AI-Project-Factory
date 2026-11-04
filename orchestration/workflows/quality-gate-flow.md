# Quality Gate Flow

## Flow

Requirement -> QG-01 -> Architecture -> QG-02 -> Development -> QG-03 -> Security -> QG-04 -> Release prep -> QG-05 -> Production -> QG-06.

## Verdicts

PASS, PASS_WITH_OBSERVATIONS, FAIL, BLOCKED.

## Rules

- FAIL or BLOCKED stops progression.
- Production requires human approval and QG-06 PASS.