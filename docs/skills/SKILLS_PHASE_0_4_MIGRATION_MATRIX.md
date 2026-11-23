# Skills Phase 0.4 — V1→V2 Migration Matrix

**Date:** 2026-11-19  
**Scope:** Inventory of the 18 executable agents and their V1 permission maps, with proposed V2 equivalents. No productive agents were modified.

## V1→V2 action mapping
| V1 | V2 |
|---|---|
| read | read |
| glob | glob |
| grep | grep |
| bash | shell |
| edit | edit |
| write | write |
| task | subagent |
| execute | execute |
| webfetch | webfetch |
| websearch | websearch |

## Agent matrix (summary)
| Agent | V1 profile | V2 migration notes |
|---|---|---|
| AG-001 | read allow; edit/write/bash ask; task ag-* allow, * deny; execute/webfetch/websearch deny | `subagent: ag-* allow, * deny`; keep ask for edit/write/shell; deny network/execute |
| AG-002 | read/glob/grep allow; bash ask; edit/write deny; task/execute/webfetch/websearch deny | Read-only reviewer; no write/edit; shell ask |
| AG-003 | read/glob/grep allow; bash ask; edit/write deny; task/execute/webfetch/websearch deny | Security/risk; read-only; shell ask |
| AG-004..007 | read/glob/grep allow; bash deny; edit/write allow; task/execute/webfetch/websearch deny | Development-capable; bash denied by default; network denied |
| AG-008..011 | read/glob/grep allow; bash ask; edit/write allow; task/execute/webfetch/websearch deny | Backend/integration; shell ask; network denied |
| AG-012 | read/glob/grep allow; bash ask; edit/write allow; task/execute/webfetch/websearch deny | QA; shell ask |
| AG-013..015 | read/glob/grep allow; bash ask; edit/write deny; task/execute/webfetch/websearch deny | Review/audit; read-only; shell ask |
| AG-016..017 | read/glob/grep allow; bash ask; edit/write allow; task/execute/webfetch/websearch deny | DevOps/deployment; shell ask |
| AG-018 | read/glob/grep allow; bash deny; edit/write allow; task/execute/webfetch/websearch deny | Documentation; bash denied |

## Principles
- Minimum privilege preserved.
- No permission expansion during migration.
- `external_directory: deny` should be added to all agents to confine file access.
- `skill` permissions should be derived from the registry assignment matrix.
- Task/subagent permissions remain restricted to explicitly authorized agents.