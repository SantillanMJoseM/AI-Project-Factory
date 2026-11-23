# Skills Phase 0.4 — Parent-Child Isolation

**Date:** 2026-11-19

## Finding
OpenCode docs: "A custom subagent uses its own configured permissions, not a subset of its parent’s permissions."

## Implications
- Subagent permissions are independent.
- Parent restrictions do not automatically constrain subagents.
- Each subagent must have explicitly restrictive permissions.
- Governance must validate subagent permission matrices before assignment.

## Pilot evidence
- `child-agent` with `external_directory: deny` blocked `/etc/hostname` read.
- `skill-controlled` allowed only `echo *` and denied other shell commands.
- No live parent→child delegation test was possible in this environment (task tool not exposed in the invoked session).

## Residual risk
- No live delegation proof; subagent isolation relies on configuration discipline.