# Skills Phase 0.3 — Subagent Isolation

**Date:** 2026-11-19

## Finding
OpenCode documentation states: "A custom subagent uses its own configured permissions, not a subset of its parent’s permissions."

This means:
- Subagent permissions are independent of the parent.
- A parent with restrictive permissions does not automatically constrain a subagent.
- Each subagent must have explicitly configured, restrictive permissions.
- Governance must ensure no subagent is granted broader permissions than intended.

## Implication for AI-Project-Factory
- The factory's 18 agents must not be modified (current restriction).
- Any future subagent used for Skill execution must have its own permission matrix.
- The task contract (skill, version, executor, authorized files, allowed tools) must be enforced before delegation.
- Parent agents should only be allowed to invoke explicitly authorized subagents via `subagent` permission rules.

## Test evidence
- `child-agent` with `external_directory: deny` blocked reading `/etc/hostname` even though `read: allow`.
- `skill-controlled` allowed `echo *` but rejected `whoami` via last-match precedence.
- `skill-deny` blocked skill loading entirely with `Permission denied: skill`.

## Residual risk
- No live test of parent→child delegation was possible in this environment (task tool not exposed in the invoked session).
- Subagent permission inheritance is not restrictive by default; must be enforced by configuration.