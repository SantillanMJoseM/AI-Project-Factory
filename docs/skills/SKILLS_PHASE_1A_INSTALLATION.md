# Skills Phase 1A — Installation

**Date:** 2026-11-19

## Location
Skills installed under `.opencode/skills/<skill-id>/` (OpenCode native project discovery).

## Method
- Vendored complete skill directories (SKILL.md + references) from pinned upstream commits.
- No scripts executed.
- No dependencies installed.
- No agent files modified.

## Validation
- OpenCode discovered all 17 skills (confirmed by runtime skill list).
- `@skill-id` loading verified for representative skills.
- Registry saved to `orchestration/skills/registry.json` (17 entries, lifecycle ACTIVE).
- Security scan: all ACCEPT.