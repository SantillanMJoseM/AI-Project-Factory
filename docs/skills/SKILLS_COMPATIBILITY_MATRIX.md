# Skills Compatibility Matrix

- **doc_id**: SKILLS-COMPATIBILITY-MATRIX-0001
- **created_at**: 2026-11-19
- **author**: AG-011 Integration Engineer
- **inputs**: `/tmp/opencode/skills-work/opencode_skills_official.md`, `/tmp/opencode/candidates.json`, cloned repos under `/tmp/opencode`
- **scope**: Assess each candidate skill for native OpenCode Skills compatibility. No installation, enablement, or configuration changes performed.

## Executive summary

- **93 candidates** across 4 repositories were assessed against the official OpenCode Skills mechanics (discovery locations, `SKILL.md` form, path-derived case-sensitive IDs, frontmatter `name`/`description`, supporting-file handling, skill permissions, and HTTP catalog rules).
- **wshobson/agents** is the most compatible source: 44/45 candidates are **COMPATIBLE** as native OpenCode skills; one (`hads`) needs minor model-neutral wording changes.
- **obra/superpowers** provides valuable technique skills: 3 are **COMPATIBLE** as self-contained guidance, while **12 need adaptation** due to subagent workflows, platform-specific (`superpowers:`, Claude/Codex/Pi/Hermes/Muse) references, and supporting files missing from the local clone.
- **sickn33/antigravity-awesome-skills** candidates cannot be verified locally (repo not cloned). Verdict is **UNKNOWN** for all 32; several have high-risk signals (AGPL license, offensive risk label, MCP/autonomous-research dependencies).
- **vercel-labs/skills/find-skills** is **INCOMPATIBLE** as a native OpenCode skill because it is an installer for a different skills ecosystem (`npx skills`).

## Compatibility criteria

Assessment is based on the official OpenCode Skills documentation summary fetched 2026-11-19:

1. **Skill form**: Flat `skills/<id>.md` or directory `skills/<id>/SKILL.md`. One skill per `SKILL.md` directory; nested directories derive ID from the `SKILL.md` parent.
2. **Frontmatter**: Optional, but a `description` is required for advertisement to the model. `name` is display-only; the ID is path-derived and case-sensitive. `metadata.opencode/autoinvoke` / `disable-model-invocation` control model-driven loading.
3. **Supporting files**: Referenced via paths relative to the `SKILL.md` directory. OpenCode lists up to 10 sample supporting file paths but does **not** auto-load their contents; the skill prose must tell the model when to read them.
4. **Tool references / model independence**: Native skills should not depend on a single model/harness (Claude Code-only tools, `.claude/settings.json`, PreToolUse hooks, MCP servers unavailable in OpenCode, etc.).
5. **Scripts / dependencies**: Bundled scripts are supported if invoked through an interpreter (`bash scripts/x.sh`, `node scripts/x.js`, `python3 scripts/x.py`). External installs (brew/pip/npm) are acceptable as guidance only, not as skill runtime dependencies.
6. **HTTP catalog feasibility**: A skill is catalog-feasible if all files use safe relative paths and an `index.json` can list `SKILL.md` plus supporting files under `<base-url>/<name>/<file>`.

## Verdict summary

| Verdict | Count |
|---|---|
| COMPATIBLE | 47 |
| NEEDS_ADAPTATION | 13 |
| INCOMPATIBLE | 1 |
| UNKNOWN | 32 |

## wshobson/agents

| ID | Category | Verdict | Frontmatter / Form | Assessment (supporting files, scripts, tools, model independence, HTTP catalog) | Required Adaptations |
|---|---|---|---|---|---|
| `architecture-decision-records` | docs-knowledge | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `architecture-patterns` | architecture-design | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `code-review-excellence` | code-quality-review | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `debugging-strategies` | debugging-performance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `error-handling-patterns` | code-quality-review | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `python-performance-optimization` | debugging-performance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `design-system-patterns` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `responsive-design` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `accessibility-compliance` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `interaction-design` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `visual-design-foundations` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `web-component-design` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `tailwind-design-system` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `wcag-audit-patterns` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `screen-reader-testing` | ui-ux-accessibility | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `api-design-principles` | backend-api | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `auth-implementation-patterns` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `microservices-patterns` | architecture-design | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `openapi-spec-generation` | docs-knowledge | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `nodejs-backend-patterns` | backend-api | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `database-migration` | database-data | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `sql-optimization-patterns` | database-data | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `postgresql-table-design` | database-data | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `e2e-testing-patterns` | testing | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `javascript-testing-patterns` | testing | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `python-testing-patterns` | testing | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `bats-testing-patterns` | testing | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `attack-tree-construction` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `sast-configuration` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `security-requirement-extraction` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `stride-analysis-patterns` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `threat-mitigation-mapping` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `secrets-management` | security-compliance | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `git-advanced-workflows` | git-vcs | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `github-actions-templates` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `gitlab-ci-patterns` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `deployment-pipeline-design` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `terraform-module-library` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `k8s-manifest-generator` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `helm-chart-scaffolding` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | SKILL.md + references/ + scripts/validate-chart.sh. Script must be invoked via interpreter (`bash scripts/validate-chart.sh`). No Claude-specific references. HTTP catalog feasible. | None |
| `gitops-workflow` | devops-delivery | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `changelog-automation` | docs-knowledge | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `hads` | docs-knowledge | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Clean frontmatter/SKILL.md form; guidance-only. Body contains "HADS Claude Skill" and "teaches Claude" — model-specific language. HTTP catalog feasible. | Remove/replace Claude-specific references with model-neutral terms ("assistant", "AI model"). |
| `grounded-vault` | docs-knowledge | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |
| `avoid-ai-writing` | docs-knowledge | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Guidance-only markdown; clean frontmatter; relative references/assets. No Claude-specific tool references. HTTP catalog feasible. | None |

## obra/superpowers

**Note:** The local clone under `/tmp/opencode/sp` contains only `SKILL.md` files. The upstream source repo contains additional `references/`, `scripts/`, `prompts/`, and `templates/` directories. Compatibility ratings below assume the **complete upstream directory** is vendored; if only the local clone is used, supporting files will be missing and verdicts degrade to **NEEDS_ADAPTATION**.

| ID | Category | Verdict | Frontmatter / Form | Assessment (supporting files, scripts, tools, model independence, HTTP catalog) | Required Adaptations |
|---|---|---|---|---|---|
| `writing-skills` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. References `~/.claude/skills`, `codex-tools.md`, `gemini-tools.md`, and subagent-based skill testing. Source has references/ and render-graphs.js. HTTP catalog feasible if complete. | Add OpenCode discovery paths and tool references; replace platform-specific install paths; include all supporting files; adapt subagent test methodology to OpenCode agents. |
| `writing-plans` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK; guidance references subagent-driven planning and platform-specific artifact paths. HTTP catalog feasible. | Replace subagent instructions with OpenCode agent/skill tool patterns; adapt artifact path conventions. |
| `verification-before-completion` | code-quality-review | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Self-contained guidance skill; clean frontmatter; no subagent/platform references. HTTP catalog feasible. | None |
| `using-superpowers` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK; lists Claude Code, Codex, Pi, Antigravity, Hermes, Muse reference files. No OpenCode reference. Mentions subagent stop tags. HTTP catalog feasible if references included. | Add `references/opencode-tools.md`; map skill invocation to OpenCode `skill` tool; remove or generalize harness-specific tags. |
| `using-git-worktrees` | git-vcs | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Self-contained SKILL.md; generic git-based instructions. Local clone lacks source `references/` if any. Does not mention OpenCode native worktree tools. HTTP catalog feasible. | Add OpenCode worktree tool (`opencode_worktree_create`) as preferred native path before git fallback; verify no missing supporting files. |
| `test-driven-development` | testing | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK; SKILL.md references `writing-good-tests.md` which exists in source but not in local clone. Uses `dot` graphviz (unrendered in OpenCode). HTTP catalog feasible if complete directory vendored. | Vendor complete skill directory including `writing-good-tests.md`; replace or render graphviz diagrams; ensure relative paths resolve. |
| `systematic-debugging` | debugging-performance | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source repo has supporting files (examples, references, shell script) missing locally. References other skills with `superpowers:` namespace. HTTP catalog feasible if complete. | Vendor complete directory; replace `superpowers:<id>` references with plain OpenCode skill IDs; test shell script paths. |
| `subagent-driven-development` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source has implementer-prompt.md, re-review-prompt.md, references/, scripts/. Core workflow depends on subagent dispatch and model selection. HTTP catalog feasible if complete. | Map subagent dispatch to OpenCode agent tools; replace model-selection instructions with OpenCode model configuration; vendor all supporting files and scripts. |
| `requesting-code-review` | code-quality-review | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source has code-reviewer.md; skill references subagent dispatch for reviewer. HTTP catalog feasible if complete. | Vendor code-reviewer.md; replace subagent dispatch with OpenCode agent/skill tool invocation. |
| `receiving-code-review` | code-quality-review | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Self-contained guidance; clean frontmatter. Optional GitHub CLI `gh api` reference at end is tool-specific, not a blocker. HTTP catalog feasible. | Optional: replace `gh api` reply instructions with generic forge guidance if target audience lacks gh CLI. |
| `finishing-a-development-branch` | agent-process | COMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Self-contained; uses standard git commands and worktree detection. Mentions "Superpowers" worktree paths in prose only. HTTP catalog feasible. | Optional: rename Superpowers-specific worktree directory references to project-neutral names. |
| `executing-plans` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source has scripts/task-start and scripts/task-done. Heavily references superpowers: namespace skills, subagents, and ledger files. HTTP catalog feasible if complete. | Vendor scripts; replace `superpowers:<id>` with OpenCode IDs; adapt subagent final review to OpenCode agents; ensure script paths are relative and executable via `bash ...`. |
| `dispatching-parallel-agents` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK; self-contained SKILL.md but instructions assume a subagent dispatch mechanism. HTTP catalog feasible. | Add OpenCode-specific parallel agent dispatch instructions or fall back to sequential task execution with clear caveats. |
| `diagnosing-superpowers` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source has prompts/, references/, templates/ missing locally. Uses subagent analysts and scrub audits. HTTP catalog feasible if complete. | Vendor all supporting directories; map subagent analysts to OpenCode agents; adapt scrub-audit workflow to available tools. |
| `brainstorming` | agent-process | NEEDS_ADAPTATION | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK. Source has scripts/ (Node server, start/stop), visual-companion.md, builder-check-prompt.md. Uses subagents and a browser visual companion server. HTTP catalog feasible if complete. | Decide whether visual companion server is supported in OpenCode; replace subagent builder-check with OpenCode agent dispatch or self-review; vendor all scripts/assets; invoke scripts via interpreter. |

## sickn33/antigravity-awesome-skills

**Note:** This repository was not cloned locally. Assessment is based on `candidates.json` metadata, the git tree snapshot at `/tmp/opencode/sickn33_antigravity-awesome-skills_tree.json`, and the repository layout (`.claude-plugin/`, `.opencode/plugins/`, apps with MCP-like servers).

| ID | Category | Verdict | Frontmatter / Form | Assessment (supporting files, scripts, tools, model independence, HTTP catalog) | Required Adaptations |
|---|---|---|---|---|---|
| `architecture-decision-records (sickn33)` | docs-knowledge | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `software-architecture (sickn33)` | architecture-design | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `architecture-review (sickn33)` | architecture-design | UNKNOWN / INCOMPATIBLE (tentative) | Not cloned; form unknown | No local SKILL.md content available. Description references Ontoly Software Graph + MCP capabilities; license AGPL-3.0-only. Cannot verify frontmatter or tool references. HTTP catalog feasibility unknown. | Clone/repo review required. If adopted, replace MCP/Ontoly dependencies with OpenCode-native tools or document them as unavailable; resolve AGPL copyleft implications. |
| `clean-code (sickn33)` | code-quality-review | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `tdd (sickn33)` | testing | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `systematic-debugging (sickn33)` | debugging-performance | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `code-review-excellence (sickn33)` | code-quality-review | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `performance-optimization (sickn33)` | debugging-performance | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `design-system (sickn33)` | ui-ux-accessibility | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `accessibility-compliance-accessibility-audit (sickn33)` | ui-ux-accessibility | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `api-design-principles (sickn33)` | backend-api | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `auth-implementation-patterns (sickn33)` | security-compliance | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `microservices-patterns (sickn33)` | architecture-design | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `postgres-best-practices (sickn33)` | database-data | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `sql-optimization-patterns (sickn33)` | database-data | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `prisma-expert (sickn33)` | database-data | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `database-design (sickn33)` | database-data | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `database-migration (sickn33)` | database-data | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `e2e-testing-patterns (sickn33)` | testing | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `security-audit (sickn33)` | security-compliance | UNKNOWN / INCOMPATIBLE (tentative) | Not cloned; form unknown | No local content. Registry labels risk=offensive (penetration testing workflow). Cannot verify frontmatter, scripts, or tool references. HTTP catalog feasibility unknown. | Per-file content review by AG-003; do not enable without explicit risk approval. Likely requires external security tooling not in OpenCode base. |
| `secrets-management (sickn33)` | security-compliance | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `docker-expert (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `linux-administration (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `ci-cd-and-automation (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `deployment-engineer (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `git-advanced-workflows (sickn33)` | git-vcs | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `deep-research (sickn33)` | agent-process | UNKNOWN / NEEDS_ADAPTATION (tentative) | Not cloned; form unknown | No local content. Autonomous research implies web search/read tools. License Apache-2.0. HTTP catalog feasibility unknown. | Verify required tools (web search, fetch) against OpenCode availability; add attribution/NOTICE for Apache-2.0; review for autonomous behavior constraints. |
| `documentation (sickn33)` | docs-knowledge | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `api-documentation (sickn33)` | docs-knowledge | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `threat-modeling (sickn33)` | security-compliance | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `docker-compose (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |
| `kubernetes-deployment (sickn33)` | devops-delivery | UNKNOWN | Not cloned; form unknown | No local SKILL.md content cloned; assessment based on registry path and description only. Repo path `plugins/agentic-awesome-skills-claude/` suggests Claude-bundle packaging. HTTP catalog feasibility unknown. | Clone and inspect SKILL.md, supporting files, and frontmatter. Likely NEEDS_ADAPTATION if content is Claude-specific or references external tools/MCP. |

## vercel-labs/skills

| ID | Category | Verdict | Frontmatter / Form | Assessment (supporting files, scripts, tools, model independence, HTTP catalog) | Required Adaptations |
|---|---|---|---|---|---|
| `find-skills` | agent-process | INCOMPATIBLE | FM OK (name=True, desc=True); SKILL.md form | Frontmatter OK; SKILL.md form valid. Skill is an installer for the `npx skills` / skills.sh ecosystem, not guidance content. Instructs global auto-confirm installs (`-g -y`). Not a native OpenCode skill. | Do not adopt as native OpenCode skill. If skill discovery is needed, implement a separate OpenCode-aware helper that uses `opencode.json` skills config and human-approved installs. |

## Repository-level compatibility notes

### wshobson/agents
- Uniform MIT licensing (repo-wide).
- All candidate skills use directory/`SKILL.md` form with clean `name` + `description` frontmatter.
- Bodies are guidance-only markdown; most supporting files are in `references/` or `assets/` and use relative paths.
- No `.opencode/` adapter present in the local clone; skills are packaged for Claude via `.claude-plugin/marketplace.json`. Native OpenCode compatibility comes from the generic `SKILL.md` form.
- `hads` is the only candidate with model-specific wording ("Claude"); a minor text replacement makes it fully model-independent.
- HTTP catalog packaging is straightforward: include `SKILL.md` and all relative `references/` / `assets/` / `scripts/` files in the catalog `index.json`.

### obra/superpowers
- MIT licensed; high-quality technique/process skills.
- Local clone is **incomplete**: only `SKILL.md` files are present. Upstream source has rich supporting directories for `brainstorming`, `diagnosing-superpowers`, `executing-plans`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `using-superpowers`, and `writing-skills`.
- Skill IDs in prose are often prefixed with `superpowers:` (e.g., `superpowers:systematic-debugging`). OpenCode IDs are path-derived and case-sensitive; these references must be rewritten to plain IDs.
- Several skills assume a subagent dispatch primitive and explicit model selection, which may not map 1:1 to OpenCode agent tooling.
- The repo already ships plugins for Claude, Codex, Cursor, Devin, Gemini, Hermes, Kimi, Muse, Pi, and OpenCode (`.opencode/plugins/superpowers.js`), indicating a packaging layer is needed; raw `SKILL.md` directories are not sufficient.
- HTTP catalog is feasible only after completing the local directory and adapting harness-specific references.

### sickn33/antigravity-awesome-skills
- Not cloned; no local `SKILL.md` content inspected.
- Repo layout includes `.claude-plugin/`, `.agents/`, `.codex-plugin`, `.cursor-plugin`, `.devin-plugin`, `.kimi-plugin`, `.muse-plugin`, `.pi/`, and `.opencode/plugins/`. Skills are packaged per harness.
- Candidate paths are mostly under `plugins/agentic-awesome-skills-claude/`, suggesting the content may be Claude-bundle specific.
- Registry risk labels (`critical`, `safe`, `unknown`, `offensive`) are present but undefined; they cannot be used as gating criteria.
- `architecture-review (sickn33)` is AGPL-3.0-only and references external MCP/Ontoly dependencies.
- `security-audit (sickn33)` carries an `offensive` risk label (penetration testing workflow).
- `deep-research (sickn33)` is Apache-2.0 and implies autonomous web search.
- HTTP catalog feasibility is **unknown** pending content review.

### vercel-labs/skills
- Single candidate: `find-skills`.
- Valid `SKILL.md` form and frontmatter, but content is an installer for the `skills.sh`/`npx skills` ecosystem.
- Instructs agents to run global, confirmation-skipping installs (`npx skills add ... -g -y`), which conflicts with supervised-autonomy governance.
- Not a candidate for native OpenCode adoption.

## Required adaptations summary

| Repo | Adaptation theme | Action |
|---|---|---|
| wshobson/agents | Model-neutral wording | In `hads`, replace "Claude" references with model-neutral terms. |
| wshobson/agents | Script invocation | For skills with `scripts/` (`helm-chart-scaffolding`), ensure scripts are invoked via interpreter and executable bits are not assumed. |
| wshobson/agents | Supporting file packaging | Include `references/`, `assets/`, and `scripts/` in any HTTP catalog or vendored copy. |
| obra/superpowers | Complete local directories | Re-clone or vendor with `references/`, `scripts/`, `prompts/`, and `templates/`. |
| obra/superpowers | Namespace normalization | Replace `superpowers:<id>` references with plain OpenCode skill IDs. |
| obra/superpowers | Platform mapping | Add OpenCode-specific tool/reference files; replace Claude/Codex/Pi/Hermes/Muse-specific instructions. |
| obra/superpowers | Subagent adaptation | Map subagent dispatch/model-selection instructions to OpenCode agent/skill tooling or provide sequential fallbacks. |
| sickn33 | Content review | Clone and inspect every `SKILL.md` and supporting file before any verdict can be finalized. |
| sickn33 | License review | Resolve AGPL-3.0-only (`architecture-review`) and Apache-2.0 (`deep-research`) obligations. |
| sickn33 | Risk review | Re-adjudicate `critical`/`offensive`/`unknown` risk labels with AG-003 before enablement. |
| vercel-labs | Do not adopt | Treat `find-skills` as ecosystem documentation, not a native OpenCode skill. |

## Known issues

1. **Incomplete local clone for obra/superpowers.** `/tmp/opencode/sp` contains only `SKILL.md` files. Supporting directories from the upstream repo were not present in the working tree used for this assessment. Any adoption must vendor the full skill directory, not just `SKILL.md`.
2. **sickn33 not cloned.** No `SKILL.md` content was available for the 32 sickn33 candidates. Verdicts are therefore **UNKNOWN** and based on registry metadata only.
3. **ID collisions.** Eleven IDs exist in more than one repo (e.g., `architecture-decision-records` in wshobson and sickn33; `systematic-debugging` in obra and sickn33). OpenCode resolves duplicates by registration order (later source wins). Only one copy per ID may be enabled in a workspace.
4. **No OpenCode skill system is currently deployed** in AI-Project-Factory per `docs/skills/AUDIT_CURRENT_SKILLS.md`. Any adoption requires an approved requirement, a new ADR, and fail-closed `skill` permissions.
5. **Graphviz in SKILL.md.** Several obra skills embed `dot` diagrams; OpenCode does not render these. Provide rendered images or plain-text alternatives if visual fidelity matters.

## References

- `/tmp/opencode/skills-work/opencode_skills_official.md` — official OpenCode Skills mechanics summary.
- `/tmp/opencode/candidates.json` — candidate registry (93 rows).
- `docs/skills/EXTERNAL_SKILLS_RESEARCH.md` — prior business analysis and category assignment.
- `docs/skills/AUDIT_CURRENT_SKILLS.md` — current-state audit of OpenCode Skills in this repository.
