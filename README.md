# AI-Project-Factory

AI-Project-Factory is a universal, multi-agent software factory foundation. It defines persistent project context, agent contracts, task and execution contracts, audit contracts, Quality Gates, orchestration policies, OpenCode integration, and F0 foundation deliverables.

## Version

0.6.5 (R5.1 remediation)

## Status

F0 - Foundation: implemented and audited.

## Entry points for AI agents

1. `AI_START_HERE.md`
2. `PROJECT_CONTEXT.md`
3. `PROJECT_STATUS.md`
4. `PROJECT_HANDOFF.md`
5. `PROJECT_MAP.md`

## Repository layout

See `PROJECT_MAP.md` for the full navigation map.

## Core principles

- Repository files are the source of truth.
- No dependence on a single model, session, or conversation.
- Supervised autonomy; human approval for critical operations and production deployment.
- Independent audit before release.
- Verifiable contracts and JSON Schemas.

## Validation

Run:

```bash
python3 tests/run_all.py
```

See `docs/audits/F0_FINAL_AUDIT.md` for the final F0 audit.