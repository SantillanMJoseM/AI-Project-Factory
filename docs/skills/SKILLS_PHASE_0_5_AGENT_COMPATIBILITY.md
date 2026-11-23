# Skills Phase 0.5 — Agent Compatibility

**Date:** 2026-11-19

## Classification of 18 agents
- **Direct migration (V1→V2 structural):** all 18 (action names map cleanly).
- **Migration with adaptation:** all 18 (rule ordering must be corrected; `external_directory: deny` should be added; `skill` permissions derived from registry).
- **Human review required:** all agents with `bash: ask` (AG-001, AG-002, AG-003, AG-008–AG-017) for command-level allowlists.
- **Blocked by incompatibility:** none.

## Notes
- No agent modified.
- V1 syntax remains functional but deprecated.
- `task` (V1) → `subagent` (V2) mapping requires verification of tool name vs. action name.