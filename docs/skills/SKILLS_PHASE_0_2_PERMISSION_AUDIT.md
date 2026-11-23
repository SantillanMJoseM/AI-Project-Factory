# Skills Phase 0.2 — Permission Audit (OQ-4)

**Date:** 2026-11-19  
**Scope:** Investigate whether Skills can expand the effective permissions of an agent in OpenCode.  
**Status:** Partially resolved — see limitations and open risks.

## 1. Key distinction: loading a Skill ≠ executing tools
Loading a Skill (via model `skill` tool or `@skill-id`) injects the Markdown body into the conversation and exposes the skill's base directory plus a sample of up to 10 supporting file paths. It does **not** by itself execute code, read files, or call tools. Execution only happens when the agent subsequently invokes tools (read, bash, edit, etc.), which remain subject to the agent's effective permissions.

Therefore, `skill: deny` in our derived registry controls **advertisement/discovery and loading authorization**, not the underlying tool permissions. A Skill cannot grant itself `bash`, `read`, `edit`, `webfetch`, or `execute` capabilities that the agent does not already have.

## 2. OpenCode permission model (official docs)
- V2 permissions are ordered rules `{action, resource, effect}` with `allow/deny/ask`; last matching rule wins.
- Agent-level rules are appended after global rules; a subagent uses its own configured permissions.
- Built-in actions include `read`, `edit`, `glob`, `grep`, `shell`, `skill`, `webfetch`, `websearch`, `execute`, `subagent`, etc.
- V1 frontmatter fields (`permission:` map with `bash`/`task`) are deprecated; V2 uses `permissions:` array with `shell`/`subagent`. Files using V1 fields are still read for compatibility.
- If no rule matches, OpenCode defaults to `ask`.

## 3. Factory agents
The 18 executable agents under `.opencode/agents/` use the V1-style `permission:` map (e.g. `bash: deny`, `task: "ag-*": allow`). This is supported as deprecated syntax, but enforcement consistency should be verified under V2. The factory's derived permission model (`effective_rule`, `derive_permissions`) generates V2-style rules conceptually; mapping to agent frontmatter remains V1-style in the current implementation.

## 4. Experiments performed
### 4.1 Discovery/load (prior runs, same isolated project)
- Project: `/tmp/opencode/perm-test` with `.opencode/skills/valid-skill/SKILL.md` (+ `references/guide.md`).
- Three providers loaded and interpreted the skill: `opencode-go/hy4-flash-free`, `opencode/inkling-2-small-free`, `opencode-go/longcat-2.5-free`.
- Reference file was read only when present; no external requests observed.

### 4.2 Permission-denial experiment (inconclusive)
- Agent configured with V1-style `permission: {read: deny, bash: deny, skill: deny, execute: deny}`.
- Observed: explicit `@valid-skill` still loaded the skill body in this environment, and read/bash denial was not demonstrably enforced (the model used alternative tools or hallucinated).
- Interpretation: either V1 frontmatter permissions are not fully enforced in this OpenCode build, or explicit `@skill-id` loading bypasses the availability filter. **This is an open observation, not proof of a bypass of tool execution.**
- A follow-up with V2 `permissions:` array syntax was prepared but could not be executed due to free-usage quota exhaustion during this session.

## 5. Control separation (what OpenCode provides vs. our runtime)
| Level | OpenCode provides | Our runtime provides |
|---|---|---|
| Discovery | Directory scan + description advertisement | Registry + duplicate detection + provenance |
| Loading authorization | `skill` permission rules (allow/ask/deny) | Permission model + assignment matrix |
| Tool execution | `read/edit/shell/execute/...` permission rules | Risk classification LEVEL A/B/C + task contract |
| File access | `read`/`edit` resource rules | Authorized files list in task contract |
| Network | `webfetch`/`websearch` rules | Security scan for URLs/downloads |
| Policy protection | N/A | Governance docs + validators |

Our runtime does not replace OpenCode's enforcement; it complements it with registry, validation, and audit evidence.

## 6. Conclusion
- Skills cannot expand tool permissions by themselves; they are instructions, not capability grants.
- The OQ-4 observation is **not closed**: enforcement of V1-style `permission:` maps in this environment is inconsistent and must be verified with V2 `permissions:` arrays before claiming resolution.
- Recommendation: migrate test agents (and, with authorization, factory agents) to V2 `permissions:` arrays for a clean experiment; meanwhile treat permission enforcement as an open risk.

## 7. Residual risk
- R-OQ4-1: V1→V2 migration not performed (out of scope; requires authorization).
- R-OQ4-2: No live proof that `skill: deny` blocks explicit `@skill-id` load.
- R-OQ4-3: Agent frontmatter permission semantics depend on OpenCode version.