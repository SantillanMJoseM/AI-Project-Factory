# Skills Phase 0.4 — Pilot Report

**Date:** 2026-11-19  
**Pilot agent:** V2 clone of AG-008 (`ag-008-v2-pilot`) in isolated project `/tmp/opencode/pilot-v2`.

## Results
- Read inside workspace: PASS.
- Skill load (`@valid-skill`): PASS.
- Reference read: PASS.
- Network fetch: denied (permission rejected).
- External directory read: not tested in pilot but proven in Phase 0.3.
- Shell command with ask: rejected in non-interactive mode.

## Conclusion
V2 migration preserves functional capabilities while maintaining restrictions. The pilot demonstrates that migration is feasible without permission expansion.