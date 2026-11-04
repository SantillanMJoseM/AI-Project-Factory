# AGENTS.md

Rules for AI agents operating in this repository.

## Primary operational agent

- `build` (OpenCode built-in): full development work.
- `plan` (OpenCode built-in): analysis and planning without changes.

## Project agents

The 18 project agents are defined normatively in `agents/` and executably in `.opencode/agents/`. Use the executable agents for OpenCode delegation. Consult the normative definitions for responsibilities, limits, inputs, outputs, permissions, dependencies, acceptance criteria, and escalation.

## Context protocol

Follow `AI_START_HERE.md`, then `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `PROJECT_HANDOFF.md`.

## Change rules

- Inspect before modifying.
- Keep Git clean at stage closure.
- Run relevant tests.
- Update context documents when relevant information changes.
- Record decisions in `PROJECT_DECISIONS.md`.