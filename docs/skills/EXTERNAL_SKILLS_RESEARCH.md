# EXTERNAL_SKILLS_RESEARCH

- `doc_id`: EXTERNAL-SKILLS-RESEARCH-0001 (revision 2 — restructured to tasking format)
- `created_at`: 2026-11-19 · `author`: AG-004 Business Analyst
- Scope: **planning only.** Nothing installed, enabled, configured, or modified. No web access; sources are the candidate registry, the fetched OpenCode docs summary, and repo metadata supplied with the tasking.
- Inputs: `/tmp/opencode/candidates.json` (93 candidates, 4 repos, all `category: "TBD"`); `/tmp/opencode/skills-work/opencode_skills_official.md` (docs summary fetched 2026-11-19); tasking-provided repo metadata (see §2 footnote).
- Related: `docs/skills/AUDIT_CURRENT_SKILLS.md` (AUDIT-0002), ADR-002 (supervised autonomy), ADR-003 (verified OpenCode syntax).

## 1. Executive summary

- **93 candidates across 4 repositories**, assigned by AG-004 to 12 categories. Coverage is strong for testing, security analysis, UI/accessibility, databases, CI/CD, and documentation; **zero candidates** for requirements engineering (AG-004's own domain) or quality-gate/audit governance — those must be authored in-house.
- **`wshobson/agents` is the lowest-friction source**: uniform MIT, explicit multi-harness OpenCode adapter, guidance-only bodies. **`obra/superpowers`** has valuable technique skills, but its meta-skills inject mandatory behavior ("invoke before ANY response") that conflicts with the factory's per-agent, fail-closed permission model, and its skills depend on supporting files OpenCode does not auto-load.
- **`sickn33/antigravity-awesome-skills` is an unverified aggregator**: per-file licenses and provenance cannot be checked offline, content is duplicated across internal bundles, one candidate is **AGPL-3.0-only**, one is labeled **offensive** (security-audit). Do not adopt any of its 32 candidates without per-file review.
- **`vercel-labs/skills` find-skills is an installer**, not guidance: it runs global, confirmation-skipping installs. Directly contradicts ADR-002. **Do not install.**
- **Adoption posture: none now.** Feed the Tier-1 shortlist (§7) into a future approved initiative requiring an ADR, selectively vendored pinned copies in project-local `.opencode/skills`, and fail-closed `skill` permissions. Registry `risk` labels are only present on sickn33 rows with undefined semantics — carry them through, but do not use them for gating.

## 2. Repository inventory

| Repo | Author (GitHub owner) | License | Stars¹ | Last push¹ | Skills count¹ | OpenCode support |
|---|---|---|---|---|---|---|
| `wshobson/agents` | wshobson (Seth Hobson, per repo LICENSE) | MIT (repo-wide) | 42,684 | 2026-11-18 | 185 SKILL.md in repo; **45** in candidate set | **Yes — first-class.** README documents an OpenCode adapter (`make install-opencode`) generating skills/agents/commands, regenerated and validated in CI. |
| `obra/superpowers` | obra | MIT | 321,614 ⚠ outlier¹ | 2026-11-03 | 15 SKILL.md; **15** in candidate set | **Partial / compat-only.** Claude-oriented; loadable via `.claude/skills` / `.agents/skills` compat locations; per-harness `references/` mappings do not list OpenCode; supporting files are not auto-loaded. |
| `sickn33/antigravity-awesome-skills` | sickn33 (canonical name possibly `agentic-awesome-skills` — rename suspected) | MIT (repo) **but** `LICENSE-CONTENT` + per-skill licenses unverified; AGPL-3.0-only ×1; Apache-2.0 ×1 | 49,977 | 2026-11-19 (same-day churn) | ~3,049 unique SKILL.md (identities, not instances); **32** in candidate set | **Unverified.** Claude-bundle packaging; only reachable via compat discovery locations. Not documented in inputs. |
| `vercel-labs/skills` | Vercel, Inc. (vercel-labs) | MIT | 40,034 | 2026-11-17 | 1 (find-skills); **1** in candidate set | **Unverified / moot.** Multi-harness installer; not a candidate for adoption (§7). |

¹ **Star counts, push dates, and repo-wide skill counts are tasking-provided metadata** (as recorded by a previous revision of this document and its captures). They cannot be re-verified offline in this session; obra's star figure is a 7.5× outlier vs. the runner-up (open question OQ-2). Candidate-level license strings are taken **verbatim** from `candidates.json`.

## 3. Methodology and categories

**Method.** (a) Parsed all 93 registry rows (id, repo, path, license, description, risk where present). (b) Classified each candidate into one of 12 categories derived from the candidate population and mapped to factory roles — the registry arrived with `category: "TBD"` for every row and no authoritative list reached this session, so **the taxonomy is an analyst construction** (OQ-1). (c) Cross-referenced descriptions for name/topic collisions across and within repos. (d) Assessed adoption risk against the official OpenCode docs mechanics (IDs path-derived and case-sensitive; duplicate IDs resolved by registration order, later source wins; `description` required for advertisement; supporting files not auto-loaded; per-agent `skill` permissions allow/ask/deny) and against factory governance (ADR-002 supervised autonomy, AUDIT-0002 fail-closed R-04). (e) Planning output only — no install, no config change.

**Categories (12):**

| Key | Meaning | Primary factory consumers |
|---|---|---|
| agent-process | Agent workflow, planning, orchestration, skill authoring/discovery meta-skills | AG-001, AG-005 |
| architecture-design | System/architecture patterns and review | AG-005 |
| docs-knowledge | ADRs, changelogs, API specs, doc standards/provenance, prose quality | AG-018, AG-005 |
| code-quality-review | Review practice, clean code, error handling, completion verification | AG-013, AG-002 |
| debugging-performance | Debugging method; performance profiling/optimization | AG-012, AG-014 |
| testing | TDD, unit/E2E/shell testing practices | AG-012 |
| security-compliance | Threat modeling, SAST, auth, secrets, security audit | AG-003, AG-015 |
| ui-ux-accessibility | Design systems, responsive, visual/interaction design, WCAG | AG-006, AG-009 |
| backend-api | API design patterns, Node.js backends | AG-008, AG-011 |
| database-data | Schema design, SQL/Postgres optimization, migrations, ORMs | AG-007, AG-010 |
| devops-delivery | CI/CD, IaC, Kubernetes, Docker, deployment, Linux admin | AG-016, AG-017 |
| git-vcs | Advanced Git workflows, worktrees | all dev agents |

Repo shorthand used in §4: **w** = wshobson/agents · **o** = obra/superpowers · **s** = sickn33/antigravity-awesome-skills · **v** = vercel-labs/skills. Cross-repo ID collisions are marked "(s/o)" in the ID column; registry paths remain authoritative in `candidates.json`. Registry `Risk` values are **as recorded** (semantics undefined, present only on s rows); "—" = unlabeled.

## 4. Candidate skills table (93)

### agent-process (11)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| using-superpowers | o | agent-process | Meta: mandates skill invocation before ANY response, incl. clarifying questions | MIT | — |
| brainstorming | o | agent-process | MUST use before any creative/design work, software or not | MIT | — |
| writing-plans | o | agent-process | Write implementation plans from a spec before touching code | MIT | — |
| executing-plans | o | agent-process | Execute an implementation plan inline (no subagents available) | MIT | — |
| subagent-driven-development | o | agent-process | Execute plan tasks via subagents when independent | MIT | — |
| dispatching-parallel-agents | o | agent-process | Dispatch 2+ independent tasks to parallel agents | MIT | — |
| finishing-a-development-branch | o | agent-process | Decide integration once implementation is complete | MIT | — |
| writing-skills | o | agent-process | Create/edit/verify skills before deployment | MIT | — |
| diagnosing-superpowers | o | agent-process | Debug a misbehaving superpowers session; build bug reports | MIT | — |
| find-skills | v | agent-process | Discover and install skills (`npx skills`, global, `-y` auto-confirm) | MIT | — |
| deep-research (s) | s | agent-process | Autonomous research: plan, search, read, synthesize reports | Apache-2.0 | critical |

### architecture-design (5)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| architecture-patterns | w | architecture-design | Clean/Hexagonal/DDD backend architecture patterns | MIT (repo) | — |
| microservices-patterns | w | architecture-design | Service boundaries, event-driven comms, resilience | MIT (repo) | — |
| microservices-patterns (s) | s | architecture-design | Same scope, aggregator copy | MIT (repo; check individual) | safe |
| software-architecture (s) | s | architecture-design | Broad quality-focused architecture guidance for coding sessions | MIT (repo; check individual) | critical |
| architecture-review (s) | s | architecture-design | Review repo architecture via Ontoly graph + MCP (external dep) | **AGPL-3.0-only** | unknown |

### docs-knowledge (9)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| architecture-decision-records | w | docs-knowledge | Write/maintain ADRs per best practice | MIT (repo) | — |
| changelog-automation | w | docs-knowledge | Auto changelogs from commits/PRs (Keep a Changelog) | MIT (repo) | — |
| openapi-spec-generation | w | docs-knowledge | OpenAPI 3.1 specs: code-first, design-first, validation | MIT (repo) | — |
| hads | w | docs-knowledge | Human+AI-readable doc format; token-efficient docs | MIT (repo) | — |
| grounded-vault | w | docs-knowledge | Markdown knowledge store; per-claim provenance + drift checks | MIT (repo) | — |
| avoid-ai-writing | w | docs-knowledge | Detect/rewrite AI-isms in prose (audit/rewrite/in-place) | MIT (repo) | — |
| architecture-decision-records (s) | s | docs-knowledge | ADR creation/mgmt patterns, aggregator copy | MIT (repo; check individual) | critical |
| documentation (s) | s | docs-knowledge | Doc generation workflow: API/arch docs, README, comments | MIT (repo; check individual) | safe |
| api-documentation (s) | s | docs-knowledge | OpenAPI specs + developer guides workflow | MIT (repo; check individual) | safe |

### code-quality-review (7)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| code-review-excellence | w | code-quality-review | Review practices: feedback, bug capture, mentoring | MIT (repo) | — |
| error-handling-patterns | w | code-quality-review | Exceptions/Result types/propagation across languages | MIT (repo) | — |
| requesting-code-review | o | code-quality-review | Request review when tasks/features complete | MIT | — |
| receiving-code-review | o | code-quality-review | Verify feedback with rigor; no performative agreement | MIT | — |
| verification-before-completion | o | code-quality-review | No completion claims without fresh verification evidence | MIT | — |
| clean-code (s) | s | code-quality-review | Apply "Clean Code" (R.C. Martin) principles | MIT (repo; check individual) | safe |
| code-review-excellence (s) | s | code-quality-review | Diff review: correctness/security/perf; severity findings | MIT (repo; check individual) | safe |

### debugging-performance (5)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| debugging-strategies | w | debugging-performance | Systematic debugging, profiling, root cause analysis | MIT (repo) | — |
| python-performance-optimization | w | debugging-performance | cProfile/memory profiling for Python | MIT (repo) | — |
| systematic-debugging | o | debugging-performance | Use on any bug/test failure before proposing fixes | MIT | — |
| systematic-debugging (s) | s | debugging-performance | Description **byte-identical to obra copy** (provenance signal) | MIT (repo; check individual) | critical |
| performance-optimization (s) | s | debugging-performance | Core Web Vitals, regression suspicion, profiling | MIT | critical |

### testing (7)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| e2e-testing-patterns | w | testing | Playwright/Cypress E2E; flaky-test debugging | MIT (repo) | — |
| javascript-testing-patterns | w | testing | Jest/Vitest/Testing Library; TDD/BDD | MIT (repo) | — |
| python-testing-patterns | w | testing | pytest, fixtures, mocking, TDD | MIT (repo) | — |
| bats-testing-patterns | w | testing | Bats shell-script testing | MIT (repo) | — |
| test-driven-development | o | testing | TDD before any feature/bugfix implementation | MIT | — |
| tdd (s) | s | testing | Red-green-refactor feature/bugfix work | `"MIT"` (quoted scalar) | `"safe"` (quoted) |
| e2e-testing-patterns (s) | s | testing | Reliable, fast E2E suites, aggregator copy | MIT (repo; check individual) | safe |

### security-compliance (11)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| attack-tree-construction | w | security-compliance | Attack trees; defense gaps; risk comms | MIT (repo) | — |
| sast-configuration | w | security-compliance | SAST tool setup for automated vuln detection | MIT (repo) | — |
| security-requirement-extraction | w | security-compliance | Threats → security requirements/stories/tests | MIT (repo) | — |
| stride-analysis-patterns | w | security-compliance | STRIDE threat identification | MIT (repo) | — |
| threat-mitigation-mapping | w | security-compliance | Threats → controls; remediation priorities | MIT (repo) | — |
| auth-implementation-patterns | w | security-compliance | JWT/OAuth2/session/RBAC access control | MIT (repo) | — |
| secrets-management | w | security-compliance | Vault/ASM/native secrets for CI/CD | MIT (repo) | — |
| auth-implementation-patterns (s) | s | security-compliance | Token/session/access-boundary auth, aggregator copy | MIT (repo; check individual) | critical |
| secrets-management (s) | s | security-compliance | Secrets practices for CI/CD, aggregator copy | MIT (repo; check individual) | critical |
| security-audit (s) | s | security-compliance | Web/API/pentest/vuln-scan audit workflow | MIT (repo; check individual) | **offensive** |
| threat-modeling (s) | s | security-compliance | STRIDE threat modeling (registry description truncated) | MIT | critical |

### ui-ux-accessibility (11)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| design-system-patterns | w | ui-ux-accessibility | Tokens, theming, component architecture | MIT (repo) | — |
| responsive-design | w | ui-ux-accessibility | Container queries, fluid type, CSS Grid, mobile-first | MIT (repo) | — |
| accessibility-compliance | w | ui-ux-accessibility | WCAG 2.2 implementation, ARIA, screen readers | MIT (repo) | — |
| interaction-design | w | ui-ux-accessibility | Microinteractions, motion, feedback patterns | MIT (repo) | — |
| visual-design-foundations | w | ui-ux-accessibility | Typography, color theory, spacing, iconography | MIT (repo) | — |
| web-component-design | w | ui-ux-accessibility | React/Vue/Svelte component architecture | MIT (repo) | — |
| tailwind-design-system | w | ui-ux-accessibility | Tailwind v4 tokens, component libraries | MIT (repo) | — |
| wcag-audit-patterns | w | ui-ux-accessibility | WCAG 2.2 audits: automated + manual + remediation | MIT (repo) | — |
| screen-reader-testing | w | ui-ux-accessibility | VoiceOver/NVDA/JAWS testing | MIT (repo) | — |
| design-system (s) | s | ui-ux-accessibility | Mechanical design invariants: tokens, hierarchy, FOUT | MIT | critical |
| accessibility-compliance-accessibility-audit (s) | s | ui-ux-accessibility | Audit pages/journeys vs declared WCAG scope | MIT (repo; check individual) | safe |

### backend-api (3)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| api-design-principles | w | backend-api | REST/GraphQL design principles and standards | MIT (repo) | — |
| nodejs-backend-patterns | w | backend-api | Express/Fastify services; middleware; DB integration | MIT (repo) | — |
| api-design-principles (s) | s | backend-api | Same scope, aggregator copy | MIT (repo; check individual) | safe |

### database-data (8)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| postgresql-table-design | w | database-data | PG schema design: types, indexing, constraints | MIT (repo) | — |
| sql-optimization-patterns | w | database-data | Query optimization, EXPLAIN, indexing | MIT (repo) | — |
| database-migration | w | database-data | Cross-ORM migrations; zero-downtime; rollback | MIT (repo) | — |
| postgres-best-practices (s) | s | database-data | Postgres optimization, self-attributed "from Supabase" | MIT (repo; check individual) | critical |
| sql-optimization-patterns (s) | s | database-data | Diagnose slow SQL; verified indexing changes | MIT (repo; check individual) | critical |
| prisma-expert (s) | s | database-data | Prisma schema/migrations/query optimization | MIT (repo; check individual) | critical |
| database-design (s) | s | database-data | Schema design, indexing, ORM selection decisions | MIT (repo; check individual) | safe |
| database-migration (s) | s | database-data | Sequelize/TypeORM/Prisma migrations + rollback | MIT (repo; check individual) | critical |

### devops-delivery (13)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| github-actions-templates | w | devops-delivery | Production-ready GitHub Actions workflows | MIT (repo) | — |
| gitlab-ci-patterns | w | devops-delivery | GitLab multi-stage pipelines, caching, runners | MIT (repo) | — |
| deployment-pipeline-design | w | devops-delivery | Multi-stage pipelines; canary; approval gates | MIT (repo) | — |
| terraform-module-library | w | devops-delivery | Reusable IaC modules AWS/Azure/GCP/OCI | MIT (repo) | — |
| k8s-manifest-generator | w | devops-delivery | Production K8s manifests, security standards | MIT (repo) | — |
| helm-chart-scaffolding | w | devops-delivery | Helm chart design/packaging | MIT (repo) | — |
| gitops-workflow | w | devops-delivery | ArgoCD/Flux declarative deployments | MIT (repo) | — |
| docker-expert (s) | s | devops-delivery | Container optimization, hardening, multi-stage builds | MIT (repo; check individual) | critical |
| docker-compose (s) | s | devops-delivery | Multi-container Compose apps (registry description truncated) | MIT | critical |
| kubernetes-deployment (s) | s | devops-delivery | K8s orchestration, Helm, service mesh workflow | MIT (repo; check individual) | critical |
| ci-cd-and-automation (s) | s | devops-delivery | CI/CD pipeline setup; quality gates; runners | MIT | critical |
| deployment-engineer (s) | s | devops-delivery | CI/CD + GitOps deployment persona | MIT (repo; check individual) | critical |
| linux-administration (s) | s | devops-delivery | Linux sysadmin: packages, services (registry description truncated) | MIT | critical |

### git-vcs (3)

| ID | Repo | Category | Description (condensed) | License | Risk |
|---|---|---|---|---|---|
| git-advanced-workflows | w | git-vcs | Rebase, cherry-pick, bisect, worktrees, reflog | MIT (repo) | — |
| using-git-worktrees | o | git-vcs | Isolated workspace via native tools or worktree fallback | MIT | — |
| git-advanced-workflows (s) | s | git-vcs | Clean history/recovery techniques, aggregator copy | MIT (repo; check individual) | critical |

**Row counts:** w 45 · o 15 · s 32 · v 1 = **93** ✓. **Registry risk totals:** critical 20 · safe 10 · unknown 1 · offensive 1 · unlabeled 61 (risk appears only on sickn33 rows).

## 5. Coverage by category

| Category | Candidates | Repo mix (w/o/s/v) | Coverage assessment |
|---|---|---|---|
| agent-process | 11 | 0/9/1/1 | **GAP in practice.** Highest volume, lowest adoptability: dominated by behavior-injecting obra meta-skills, one installer, one autonomous-research skill. Nothing implements factory contracts, quality gates, or ADR-style governance. |
| architecture-design | 5 | 2/0/3/0 | Adequate; prefer the two wshobson copies; the third AGPL copy excluded pending review. |
| docs-knowledge | 9 | 6/0/3/0 | **Strong.** wshobson subset (ADRs, changelog, OpenAPI, HADS, grounded-vault, avoid-ai-writing) maps directly to factory documentation practice. |
| code-quality-review | 7 | 2/3/2/0 | Strong. obra requesting/receiving/verification trio complements wshobson review practice. |
| debugging-performance | 5 | 2/1/2/0 | Adequate; one method skill per concept after dedupe. |
| testing | 7 | 4/1/2/0 | Strong: unit/E2E/shell/TDD spread across languages. |
| security-compliance | 11 | 7/0/4/0 | **Strongest method coverage** (STRIDE → requirements → mitigation → SAST → auth/secrets). Gate: content review by AG-003 before enablement. |
| ui-ux-accessibility | 11 | 9/0/2/0 | Strong; wshobson covers the design → implement → audit → assistive-tech loop. |
| backend-api | 3 | 2/0/1/0 | **Thin** but pattern-sufficient; no contract-testing or webhook-design candidates. |
| database-data | 8 | 3/0/5/0 | Adequate volume, **partial factory fit**: mostly Postgres-centric while factory projects are SQLite-stdlib oriented (ADR-005). |
| devops-delivery | 13 | 7/0/6/0 | Strong breadth, **partial fit**: factory deploys via OpenCode/LXC + install scripts, not K8s/cloud; better suited to generated projects (scope b). |
| git-vcs | 3 | 1/1/1/0 | Adequate after dedupe (worktree isolation + one git-workflows copy). |
| **Requirements engineering / BA** | **0** | — | **GAP — no candidates.** Elicitation, user stories, acceptance criteria, traceability, ambiguity detection must be authored in-house (REC-5). |
| **Quality-gate / audit governance** | **0** | — | **GAP — no candidates.** Gate approval, independent-audit separation, evidence-policy workflows must be authored in-house. |

## 6. Duplicates and overlap notes

**6.1 Exact-ID collisions (11 IDs in >1 repo).** Under OpenCode precedence rules, duplicate path-derived IDs resolve by registration order — the **later-registered source silently overrides** the earlier one. Installing any colliding pair in one workspace is an operational hazard; at most one copy per ID may ever be adopted.

| Colliding ID | Repos | Note |
|---|---|---|
| architecture-decision-records | w, s | Different texts; keep one |
| microservices-patterns | w, s | Near-identical scope |
| code-review-excellence | w, s | Same name, different framing |
| api-design-principles | w, s | Near-duplicate |
| auth-implementation-patterns | w, s | Security-critical — never both |
| secrets-management | w, s | Security-critical — never both |
| sql-optimization-patterns | w, s | Keep w |
| database-migration | w, s | Keep w |
| e2e-testing-patterns | w, s | Keep w |
| git-advanced-workflows | w, s | Keep w |
| systematic-debugging | **o, s** | Registry descriptions **byte-identical** → strong evidence s re-hosts o's content verbatim (provenance red flag, F-3) |

**6.2 Near-duplicate topic clusters (different IDs, overlapping scope).** Debugging method (w `debugging-strategies` / o+s `systematic-debugging`); TDD (o `test-driven-development` / s `tdd` / w testing-patterns overlap); code review (o requesting+receiving / w+s excellence / s `clean-code` partial); Postgres (w `postgresql-table-design` / s `postgres-best-practices`); accessibility audit (w 3-skill loop / s audit copy); threat modeling (w 3-skill set / s `threat-modeling`); CI/CD design (w 3-skill set / s `ci-cd-and-automation` + `deployment-engineer`, which also overlap each other **within** sickn33); Kubernetes (w 3-skill set / s `kubernetes-deployment`); API docs/spec (w `openapi-spec-generation` / s `api-documentation` ⊂ s `documentation`); design systems (w patterns + Tailwind / s `design-system`); Git history/worktrees (w / o / s as in 6.1).

**6.3 Within-sickn33 duplication.** The same skills are replicated across the aggregator's internal bundle plugins (e.g., the accessibility-audit skill appears at 6 distinct paths; systematic-debugging at ≥2). Consequences: "~3,049 unique SKILL.md" counts identities not instances; adopting from this repo multiplies ID collisions and namespace noise.

## 7. Findings and recommendations (planning only)

**Findings.**
- **F-1 License profile.** 91/93 candidates are MIT-family. Exceptions: `architecture-review` (s) **AGPL-3.0-only** — copyleft analysis required before any copying/vendoring; `deep-research` (s) Apache-2.0 — notice-retention obligations. Most s rows say "MIT (repo; check individual)": per-file license is **unverified offline**; the repo also ships a `LICENSE-CONTENT` file of unknown terms.
- **F-2 Registry risk labels are unusable as gates.** `risk` appears on sickn33 rows only (critical 20 / safe 10 / unknown 1 / offensive 1) with no collector definition; pattern suggests topic-capability sensitivity, with counterexamples. Carried through as-recorded; AG-003 must re-adjudicate content risk (license, provenance, capability, behavior-injection, operational fit).
- **F-3 Aggregator provenance risk (sickn33).** Verbatim cross-repo description copy, explicit third-party attribution ("from Supabase") inside one skill, quoted-string metadata scalars (`"MIT"`, `"safe"`) suggesting scraped ingest, three truncated registry descriptions, same-day push churn, intra-repo duplication. Treat the repo as a **discovery index, never a source of truth**; no candidate adoptable without per-file provenance + license + content review.
- **F-4 Behavior-injection conflict (obra).** Meta-skills (`using-superpowers`, `brainstorming`) demand invocation before any response — incompatible with per-agent contracts and fail-closed permissions. Technique skills (`verification-before-completion`, review/debugging/planning set) align strongly with existing factory audit rules and are the highest-value external inputs, but depend on `references/` supporting files that OpenCode does not auto-load and that map other harnesses, not OpenCode.
- **F-5 Installer risk (vercel).** `find-skills` instructs agents to install skills globally with confirmation skipped (`-g -y`) — a supply-chain vector contradicting ADR-002 and AUDIT-0002 R-04. Recommend: **do not install**; discovery must remain a human-run workflow.
- **F-6 Integration-fit ranking.** `wshobson/agents` best: uniform MIT, OpenCode adapter documented and CI-generated, sampled bodies guidance-only with clean `name`/`description` frontmatter. Caveat: its adapter imports ~185 artifacts wholesale — factory policy favors selective vendoring instead.
- **F-7 Coverage gaps.** Zero candidates for requirements engineering (AG-004 domain) and quality-gate/audit governance (AG-002/003/013/015); backend-api thin; database/devops candidates skewed to Postgres/K8s/cloud with limited factory fit (better fit: generated projects).
- **F-8 Data-quality caveats.** Categories were absent ("TBD") in 100% of registry rows and are analyst-assigned here; stars/push dates/skill counts are tasking-provided and unverifiable offline (obra figure an outlier); s repo name discrepancy (antigravity↔agentic) suggests a rename — pin canonical identity + commit SHA if ever adopted.

**Recommendations (planning input; no approval implied).**
- **REC-1 (AG-001).** Adopt nothing now. Route a future skills initiative through a task contract using this document + AUDIT-0002 as inputs; resolve category authority (OQ-1) and the two consumption scopes — (a) factory agents vs (b) generated projects — before design.
- **REC-2 (tiering).** Tier 1 preferred: selected wshobson MIT skills — docs set (`architecture-decision-records`, `changelog-automation`, `openapi-spec-generation`, `hads`, `grounded-vault`, `avoid-ai-writing`), quality set (`code-review-excellence`, `error-handling-patterns`, `debugging-strategies`), testing set (4 `*-testing-patterns`), security-scanning 5-set, plus `api-design-principles`, `postgresql-table-design`, `sql-optimization-patterns`, `git-advanced-workflows`; plus obra technique skills (`verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `systematic-debugging`, `writing-plans`, `executing-plans`, `using-git-worktrees`, `writing-skills`) **only as complete directories incl. references**. Tier 2 conditional/project-scope: wshobson UI/a11y and devops/K8s/Terraform sets. Tier 3 do-not-adopt: all 32 sickn33 pending review; `find-skills`; obra meta-skills (`using-superpowers`, `brainstorming`, delegation set, `diagnosing-superpowers`).
- **REC-3 (integration pattern).** If adopted: selectively vendor into project-local `.opencode/skills` from pinned commits with LICENSE/NOTICE per skill; never HTTP catalogs or whole-repo adapters without explicit human approval; enforce **one ID per concept workspace-wide** to avoid precedence overrides (§6.1); set per-agent `skill` permissions fail-closed (`deny` default; `autoinvoke:false` for process skills so model-driven loading cannot preempt agent contracts). New ADR required (≥ ADR-007); OpenCode mechanics re-verified live per ADR-003 at design time.
- **REC-4 (AG-003).** Content-level risk re-adjudication before any enablement — mandatory for the six security-critical collisions (§6.1), `security-audit` (offensive), `architecture-review` (AGPL + external MCP dependency), `deep-research` (autonomous network behavior), and all sickn33 candidates.
- **REC-5 (in-house authoring).** Commission factory-authored skills for the two zero-coverage gaps: requirements elicitation / acceptance criteria / traceability, and quality-gate runbook — using adopted technique skills (e.g., `writing-skills`) as methodology references only.
- **REC-6 (future sweep).** wshobson plugins observed but not in this registry (`startup-business-analyst`, `business-analytics`, governance/audit-adjacent) are candidate inputs for the next collection round; run them through the same tier framework.

**Open questions (escalation to AG-001 where critical).** OQ-1: is the §3 taxonomy acceptable or is an authoritative category list owed? OQ-2: re-verify tasking-provided stars/push/counts when web access exists. OQ-3: obtain collector definition of registry risk labels or formally retire them. OQ-4: confirm the installed OpenCode build honors `autoinvoke` metadata and per-agent skill permissions as per the fetched docs summary.

---
*Compliance: research-only deliverable. No skills installed or enabled; no configuration or agent definitions modified. Sole file written: `docs/skills/EXTERNAL_SKILLS_RESEARCH.md`. Descriptions condensed from `/tmp/opencode/candidates.json`, which remains authoritative for full text and paths.*
