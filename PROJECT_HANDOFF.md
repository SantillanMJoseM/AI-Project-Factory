# PROJECT_HANDOFF

## Current state

R5.2A implementation and ProjectDesk pilot completed on branch `feature/r5.2a-implementation`.

## What was being done

Resolved security blockers B-01 to B-04, prepared clean installation scripts and docs, executed a real ProjectDesk pilot using 18 agents, and produced the pilot report.

## Completed

- Removed `--auto` from OpenCode adapter and preflight.
- Implemented fail-closed permission model with env allowlist and explicit PWD.
- Implemented `OpenCodeSandbox` with private `opencode serve` inside `unshare -Urm`.
- Restricted AG-001 delegation to `ag-*` and denied `execute` for all factory agents.
- Made migration 4 atomic, idempotent, and transactional.
- Fixed test plan traceability (AC-027, AC-028, AC-to-test mapping).
- Created installation scripts and documentation under `install/`.
- Created private pilot repository `AI-Project-Factory-Pilot`.
- Registered ProjectDesk (`PROJECT-001`) and executed all 10 pilot tasks.
- ProjectDesk has 30 passing pytest tests and review reports.
- Generated `docs/pilot/FACTORY_FIRST_INSTALL_AND_PROJECTDESK_REPORT.md`.
- Pushed Factory branch and ProjectDesk branch to pilot repo.

## Pending

- Execute fresh LXC install on a second container when available.
- Reconcile normative `agents/` permissions (pilot used `write: allow` for development agents; normative files may still say `ask`).

## Modified files

See Git history on `feature/r5.2a-implementation`.

## Decisions taken

- ADR-001 to ADR-005 remain in force.
- Development agents received `write: allow` for the non-interactive pilot; this must be reconciled with normative definitions before production use.
- ProjectDesk backend was manually completed after AG-008 timeout; documented honestly.

## Problems found

- AG-008 backend and AG-013 first review timed out due to model quota/response time; mitigated with smaller prompts and manual completion.
- Fresh LXC not executed due to no second container being provisioned.
- Sandbox does not use a network namespace; documented as a limitation.

## Tests executed and results

- Factory: `python3 tests/run_all.py` — ALL TESTS PASSED.
- ProjectDesk: `pytest tests/ -v` — 30 passed.

## Last valid commit

6b28655 (feature/r5.2a-implementation)

## Instructions to continue

Review pilot report and decide whether to merge `feature/r5.2a-implementation` to main.