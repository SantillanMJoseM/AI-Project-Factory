# AI_START_HERE

Universal entry point for any AI model or session joining AI-Project-Factory.

## Mandatory bootstrap

1. Read `PROJECT_CONTEXT.md`.
2. Read `PROJECT_STATUS.md`.
3. Read `PROJECT_HANDOFF.md`.
4. Consult `PROJECT_DECISIONS.md` when the task touches existing decisions.
5. Consult `PROJECT_MAP.md` to locate required files.
6. Read only the documentation specific to the assigned task.
7. Verify Git state before modifying files.
8. Continue from the last confirmed point.

## Do not

- Restart completed phases.
- Repeat completed analysis.
- Modify previous decisions without documenting the reason and creating a new decision.
- Assume documentation is correct when it conflicts with code; investigate and record the discrepancy.

## Git verification

Before changes:

```bash
git status --short --branch
git log --oneline -5
```

## Continuity rule

The repository is the source of truth. Conversation memory is not authoritative.