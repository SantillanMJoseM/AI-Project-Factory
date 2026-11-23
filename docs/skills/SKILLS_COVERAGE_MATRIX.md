# Skills Coverage Matrix

- **doc_id**: SKILLS-COVERAGE-MATRIX-0001
- **created_at**: 2026-11-19
- **author**: AG-012 QA Automation Engineer
- **inputs**: `/tmp/opencode/candidates.json` (93 candidates) · `docs/skills/AUDIT_CURRENT_SKILLS.md` (AUDIT-0002) · `docs/skills/EXTERNAL_SKILLS_RESEARCH.md` (AG-004) · `docs/skills/SKILLS_COMPATIBILITY_MATRIX.md` (AG-011) · `docs/skills/SKILLS_SECURITY_AUDIT.md` (AG-015) · `/tmp/opencode/skills-work/opencode_skills_official.md` (official docs summary, fetched 2026-11-19)
- **scope**: Planning and QA-design deliverable. **Nothing was installed, enabled, or configured. No test suites were executed — none exist yet to execute** (the repository has zero skills; baseline is greenfield per AUDIT-0002 F-06). All mechanisms in §4 are specified, not run. This document declares no PASS verdict for tests it has not run.

## 1. Coverage baseline: current vs required

### 1.1 Current coverage — zero, everywhere

Per AUDIT-0002 (findings F-01…F-06): no skills directories at any of the six official discovery locations, no `skills` config array, no `skill` permission rules, no skills references in any agent or runtime artifact. The repository contributes **0 skills**. Skills advertised in current sessions (`opencode`, `report`) are OpenCode runtime built-ins, not repository artifacts.

**Deployed coverage today: 0 of 14 capability areas (0%).** That is a measured fact, not an estimate.

### 1.2 Required capability categories

The required category set is the 12-category taxonomy assigned by AG-004 (derived from the candidate population and mapped to factory roles), plus the two factory-governance areas AG-004 identified as candidate-free (REC-5). Two caveats carried forward:

- Every registry row arrived with `category: "TBD"`; the taxonomy is an analyst construction pending an authoritative list (**OQ-1**). Coverage statements below are therefore "against the current working taxonomy," not against an approved requirements baseline.
- No approved requirement mandates a Skills system at all (AUDIT-0002 F-10). Category "requirements" here are planning targets for a future initiative (ADR ≥ 007), not committed scope.

| # | Category | Primary factory consumers | Required capability (summary) |
|---|---|---|---|
| 1 | agent-process | AG-001, AG-005 | Planning, orchestration, skill authoring/discovery meta-skills |
| 2 | architecture-design | AG-005 | System/architecture patterns and review |
| 3 | docs-knowledge | AG-018, AG-005 | ADRs, changelogs, API specs, doc standards/provenance, prose quality |
| 4 | code-quality-review | AG-013, AG-002 | Review practice, clean code, error handling, completion verification |
| 5 | debugging-performance | AG-012, AG-014 | Debugging method; profiling/optimization |
| 6 | testing | AG-012 | TDD, unit/E2E/shell testing practices |
| 7 | security-compliance | AG-003, AG-015 | Threat modeling, SAST, auth, secrets, security audit |
| 8 | ui-ux-accessibility | AG-006, AG-009 | Design systems, responsive, visual/interaction design, WCAG |
| 9 | backend-api | AG-008, AG-011 | API design patterns, Node.js backends |
| 10 | database-data | AG-007, AG-010 | Schema design, SQL/Postgres optimization, migrations, ORMs |
| 11 | devops-delivery | AG-016, AG-017 | CI/CD, IaC, Kubernetes, Docker, deployment, Linux admin |
| 12 | git-vcs | all dev agents | Advanced Git workflows, worktrees |
| 13 | requirements-engineering (BA) | AG-004 | Elicitation, user stories, acceptance criteria, traceability |
| 14 | quality-gate / audit governance | AG-002/003/013/015 | Gate approval, independent-audit separation, evidence policy |

## 2. Capability matrix by category

Current column is **None** for every category (no skill is deployed). Candidate columns classify the 93 registry entries by the two independent verdict axes already on file: AG-011 compatibility (COMPATIBLE / NEEDS_ADAPTATION / INCOMPATIBLE / UNKNOWN) crossed with AG-015 security (ACCEPT / ACCEPT-CONDITIONAL / HOLD / REJECT), read at the per-row level.

**Adoption buckets used below** (derived cross-tab; totals reconcile to 93):

- **Ready-now** = COMPATIBLE × ACCEPT — passes both existing assessments with no recorded change required: **42** (39 wshobson + 3 obra).
- **Ready-after-conditions** = COMPATIBLE × ACCEPT-CONDITIONAL — security conditions (§7 of the audit) must be closed first: **5** (all wshobson: `api-design-principles`, `sast-configuration`, `secrets-management`, `github-actions-templates`, `gitops-workflow`).
- **Adapt-then-review** = NEEDS_ADAPTATION × ACCEPT — vendor/adapt per AG-011, then smoke-test: **9** (1 wshobson `hads` + 8 obra).
- **Adapt + conditions** = NEEDS_ADAPTATION × ACCEPT-CONDITIONAL: **4** (obra `writing-skills`, `using-superpowers`, `using-git-worktrees`, `diagnosing-superpowers`).
- **Blocked**: HOLD (30 sickn33, no content available) + REJECT (3: sickn33 `architecture-review` AGPL/MCP, sickn33 `security-audit` offensive, `find-skills` installer).

### 2.1 Matrix (candidates: repo mix w/o/s/v)

| Category | Current deployed | Candidates (w/o/s/v) | Ready-now | After-cond. | Adapt-then-review | Adapt+cond. | Blocked (HOLD/REJ) | Representative ready-now skills |
|---|---|---|---|---|---|---|---|---|
| agent-process | None | 11 (0/9/1/1) | **1** | 0 | 5 | 3 | 1 HOLD + 1 REJ | `finishing-a-development-branch` (o) |
| architecture-design | None | 5 (2/0/3/0) | **2** | 0 | 0 | 0 | 2 HOLD + 1 REJ | `architecture-patterns`, `microservices-patterns` (w) |
| docs-knowledge | None | 9 (6/0/3/0) | **5** | 0 | 1 (`hads`) | 0 | 3 HOLD | `architecture-decision-records`, `changelog-automation`, `openapi-spec-generation`, `grounded-vault`, `avoid-ai-writing` (w) |
| code-quality-review | None | 7 (2/3/2/0) | **4** | 0 | 1 | 0 | 2 HOLD | `code-review-excellence`, `error-handling-patterns` (w); `verification-before-completion`, `receiving-code-review` (o) |
| debugging-performance | None | 5 (2/1/2/0) | **2** | 0 | 1 | 0 | 2 HOLD | `debugging-strategies`, `python-performance-optimization` (w) |
| testing | None | 7 (4/1/2/0) | **4** | 0 | 1 | 0 | 2 HOLD | `e2e/javascript/python/bats-testing-patterns` (w) |
| security-compliance | None | 11 (7/0/4/0) | **5** | 2 | 0 | 0 | 3 HOLD + 1 REJ | `stride-analysis-patterns`, `attack-tree-construction`, `security-requirement-extraction`, `threat-mitigation-mapping`, `auth-implementation-patterns` (w) |
| ui-ux-accessibility | None | 11 (9/0/2/0) | **9** | 0 | 0 | 0 | 2 HOLD | design/responsive/visual/interaction/component/tailwind + WCAG/screen-reader set (w) |
| backend-api | None | 3 (2/0/1/0) | **1** | 1 | 0 | 0 | 1 HOLD | `nodejs-backend-patterns` (w) |
| database-data | None | 8 (3/0/5/0) | **3** | 0 | 0 | 0 | 5 HOLD | `postgresql-table-design`, `sql-optimization-patterns`, `database-migration` (w) |
| devops-delivery | None | 13 (7/0/6/0) | **5** | 2 | 0 | 0 | 6 HOLD | `gitlab-ci-patterns`, `deployment-pipeline-design`, `terraform-module-library`, `k8s-manifest-generator`, `helm-chart-scaffolding` (w) |
| git-vcs | None | 3 (1/1/1/0) | **1** | 0 | 0 | 1 | 1 HOLD | `git-advanced-workflows` (w) |
| requirements-engineering | None | **0** | 0 | 0 | 0 | 0 | — | **No candidates — in-house only (REC-5)** |
| quality-gate / audit governance | None | **0** | 0 | 0 | 0 | 0 | — | **No candidates — in-house only (REC-5)** |
| **Total** | **0 deployed** | **93 (45/15/32/1)** | **42** | **5** | **9** | **4** | **33** | |

Reconciliation: 42+5+9+4+30+3 = 93 ✓. Ready-now by source: wshobson 39/45, obra 3/15, sickn33 0/32, vercel 0/1.

### 2.2 Practical coverage reading

- **Best real coverage (≥4 ready-now)**: ui-ux-accessibility (9), docs-knowledge (5), security-compliance (5), devops-delivery (5), testing (4), code-quality-review (4).
- **Thin coverage (≤2 ready-now)**: agent-process (1), architecture-design (2), debugging-performance (2), backend-api (1), database-data (3, Postgres-skewed), git-vcs (1).
- **Zero coverage**: requirements-engineering, quality-gate/audit governance — no candidate exists; must be authored in-house.
- **agent-process paradox**: highest candidate volume (11), lowest adoptable fraction — the category that matters most to factory orchestration (AG-001/AG-005 process) is dominated by behavior-injecting obra meta-skills that conflict with the fail-closed per-agent permission model (AG-004 F-4, AG-015 M-2).

## 3. Missing areas not covered by candidates

| # | Gap | Evidence | Consequence for QA |
|---|---|---|---|
| M-1 | **Requirements engineering / BA** (elicitation, user stories, acceptance criteria, traceability, ambiguity detection) | 0 candidates (AG-004 §5, REC-5) | In-house authoring; the §4/§5 validation regime applies to these authored skills from day one. |
| M-2 | **Quality-gate / audit governance** (gate approval, independent-audit separation per audit-contract, evidence policy) | 0 candidates (AG-004 §5, REC-5) | Factory gate runbook cannot be outsourced; must encode `contracts/audit-contract.md` rules. |
| M-3 | **Factory-contract-aware process skills** — nothing implements task contracts, ADR workflow (next ID ≥ 007), or the context protocol (AI_START_HERE → PROJECT_* docs) | AG-004 §5 ("Nothing implements factory contracts, quality gates, or ADR-style governance") | agent-process remains effectively uncovered externally. |
| M-4 | **Backend API depth**: no contract-testing or webhook-design candidates | AG-004 §5 ("backend-api thin") | Category coverage is single-topic; do not report it as "strong." |
| M-5 | **SQLite/data-layer fit for this factory**: database candidates are Postgres-centric while factory runtime is SQLite-stdlib (ADR-005) | AG-004 F-7 | Ready-now DB skills need fit re-validation per project before being called useful. |
| M-6 | **Deployment-topology fit**: devops candidates skew K8s/cloud/IaC; factory deploys via OpenCode/LXC + install scripts | AG-004 F-7 | Most devops coverage is scope-(b) (generated projects), not scope-(a) (factory agents). |
| M-7 | **Skills QA tooling for OpenCode itself**: the only skill-authoring/validation candidate (`writing-skills`) is Claude/subagent-oriented, references `~/.claude/skills`, and its supporting files are missing from the snapshot (NEEDS_ADAPTATION + conditions) | AG-011 line 93; AG-015 line 186 | The validation harness in §4 must be **built in-house**; no candidate provides a runnable OpenCode-native skills test suite. |
| M-8 | **Verified runtime behavior baseline**: whether the installed OpenCode build honors `autoinvoke` metadata and per-agent `skill` permissions as the fetched docs summary states (OQ-4); permission enforcement was never runtime-tested (AG-015 Limitation 8) | AG-004 OQ-4; AG-015 §8.8 | Discovery/permission smoke tests (§4.4–4.5) are prerequisites for any gate, not already-passed checks. |
| M-9 | **sickn33 bulk (32 candidates)**: content, per-file license, provenance entirely unavailable — all blocked | AG-015 §2/§7.3, H-4; AG-011 Known Issue 2 | 32 potential capability entries are unusable until cloned + reviewed; coverage must not count them. |
| M-10 | **Registry data quality**: 100% `category: "TBD"` at intake; `risk` labels exist only on sickn33 rows with undefined semantics and are explicitly not gate-usable; repo metadata (stars/dates/counts) unverifiable offline; suspected repo rename | AG-004 F-2/F-8/OQ-2/OQ-3 | Any future coverage metric derived from registry fields must be re-collected with defined semantics. |

## 4. Testing / validation mechanisms for skills in OpenCode

Anchored to the official mechanics (`opencode_skills_official.md`): skills are **injected Markdown on invocation** — no code executes at load; risk materializes only when an agent follows instructions (§4 of AG-015). Supporting files are listed (max 10 sample paths) but **not auto-loaded**. Duplicate IDs resolve by registration order, **later source wins**. IDs are path-derived and case-sensitive; V2 does not enforce the recommended pattern — so **linting must enforce it in-house**.

**Execution status for every mechanism: NOT YET EXECUTED.** There are zero deployed skills to test; §6 defines the gates that will run them. No coverage percentage is claimed for any of these.

| # | Mechanism | What it checks | Method / OpenCode hook | Automation target in this repo |
|---|---|---|---|---|
| V-1 | **Structural validation** | Form is `skills/<id>.md` or `skills/<id>/SKILL.md`; one skill per SKILL.md dir (OpenCode does not search inside it); relative paths resolve from the SKILL.md dir; discovery-location layout (6 official paths); hidden dirs / node_modules skipped; ≤6 levels below source root | Filesystem walk; path→ID derivation | `scripts/validate_skills.py` or pytest in `tests/skills/test_structure.py`; CI on any change under skill dirs |
| V-2 | **Frontmatter validation** | YAML parses; `description` present and non-empty (no description ⇒ never advertised ⇒ dead weight); `name` display-only; `metadata.opencode/autoinvoke` / `disable-model-invocation` boolean, `autoinvoke` wins if both; portability fields (`license`, `compatibility`) accepted but uninterpreted — do not rely on them for gating | YAML parse + schema assertion | Same suite, `test_frontmatter.py` |
| V-3 | **ID uniqueness & precedence audit** | No duplicate path-derived ID across all enabled sources **and** `skills` config array (later registration silently overrides); IDs lowercase kebab-case 1–64 chars, case-sensitive-normalized; known 11 cross-repo collision pairs (§6.1 of AG-004) and within-sickn33 duplication must never co-reside; one ID per concept workspace-wide (REC-3) | Enumerate sources in documented registration order 1→6; assert global ID set uniqueness; flag case-insensitive near-collisions | `test_id_uniqueness.py`; runs before any adoption merges |
| V-4 | **Discovery smoke test** | Vendored skill appears in the advertised list with correct ID/name/description only; `deny` hides it; `autoinvoke:false` hides from model list yet remains loadable by ID and `@skill-id`; config sources resolve from **working directory, not config file**; HTTP catalog (if ever used): `index.json`, safe relative same-origin paths, `SKILL.md` or `<name>.md` entry, version bump refresh | Live OpenCode session probe against an allow-listed agent; scripted prompt inspection of the available-skills list | `test_discovery.py` (skipped until a skill exists); catalog shape check offline |
| V-5 | **Invocation smoke test** | Model can select the skill via the `skill` tool with the exact ID; permission effect verified per class (`allow` loads silently, `ask` prompts, `deny` rejects); body injected **without frontmatter**; skill base dir + ≤10 supporting-file paths surfaced; supporting contents not auto-loaded — skill prose must state when to read them, and every referenced relative file must exist; `@skill-id` manual load works | Prompt a trigger scenario per skill's description; assert observable load effect; fixture transcript | `test_invocation_<id>.py` per vendored skill + shared harness |
| V-6 | **Content safety scan** | AG-015 pattern set over SKILL.md **and all supporting files**: remote-fetch-and-execute (`curl\|sh`, `wget\|sh`), URLs/network egress, `base64`, `/dev/tcp`, destructive commands (`rm -rf`, `reset --hard`, `push --force`, `branch -D`), `sudo`, credential shapes (AKIA/sk-), `pull_request_target`, injection markers ("ignore previous instructions", "secretly", "do not tell the user", concealment/permission-bypass directives); frontmatter permission/autoinvoke manipulation; executable-asset inventory (scripts allowed only if interpreter-invoked, e.g. `bash scripts/validate-chart.sh`) | Static scanner reusing §1-method-3 patterns of AG-015; fail-closed: unknown content ⇒ HOLD | `test_content_scan.py`; mandatory on every vendored byte change; negative results recorded explicitly |
| V-7 | **License / provenance check** | Per-file (not repo-level) license evidence; MIT notice retention; Apache-2.0 NOTICE attribution; AGPL-3.0 ⇒ reject for internal posture; upstream **commit SHA pinned** (e.g. `wshobson@4220308`) with recorded file hashes; aggregator metadata and third-party `risk` labels treated as claims, never evidence; complete skill directory vendored (obra `references/`/`prompts/`/`templates/`/`scripts/` — SKILL.md alone degrades verdicts) | Manifest per vendored skill: repo, path, SHA, license, hash; diff against upstream at re-pin | `test_provenance.py` + `docs/skills/ADOPTION_MANIFEST.md` (or machine-readable equivalent) |
| V-8 | **Regression checks** | Re-run V-1…V-7 on: any OpenCode version/upgrade (docs summary is a snapshot; runtime behavior never verified — OQ-4), any upstream re-pin (skills are mutable prompt content — AG-015 rec. 7), any change to `opencode.json` `skills` array or `skill` permission rules (last-match-wins ordering regressions), any skills-directory edit. Snapshot/expected-output fixtures for advertised lists | CI job `skills-validation` triggered by path filters; version-bump checklist | Suite wiring + scheduled upstream-drift probe once adoption begins |

## 5. Acceptance criteria for a skill to be considered usable

A skill is **USABLE** only when every MUST below has recorded evidence (artifact, hash, or test output — per audit-contract rule 5 and AG-004's own evidence discipline). Statuses: **USABLE** / **CONDITIONALLY-USABLE** (conditions open, `ask`-gated, not advertised to agents outside the pilot) / **NOT-USABLE**.

| # | Criterion | Evidence required |
|---|---|---|
| A-1 | Governance: adoption covered by an approved requirement and a new ADR (≥ ADR-007); consumption scope declared — (a) factory agents vs (b) generated projects | ADR entry in `PROJECT_DECISIONS.md`; requirement ref |
| A-2 | Structure: valid form at a sanctioned discovery location (project-local `.opencode/skills` preferred per AUDIT-0002 R-04 / REC-3); all relative paths resolve | V-1 pass output |
| A-3 | Frontmatter: non-empty `description`; kebab-case path-derived ID ≤64 chars; autoinvoke policy explicit for process skills (`autoinvoke:false` unless model-driven loading is intended) | V-2 pass output |
| A-4 | Uniqueness: ID unique across every enabled source; no collision with the 11 known cross-repo pairs; one ID per concept | V-3 pass output |
| A-5 | Provenance: vendored from a pinned commit; per-file license verified; LICENSE/NOTICE retained in the vendored copy; file hashes recorded; AGPL excluded; full directory (incl. supporting files) present | V-7 manifest row |
| A-6 | Safety: content scan clean; AG-015 verdict ACCEPT, or ACCEPT-CONDITIONAL with **each stated condition closed and re-attested**; no unverified third-party risk label used as a substitute | V-6 output + audit verdict cross-ref |
| A-7 | Compatibility: AG-011 verdict COMPATIBLE, or adaptations from the matrix applied and the skill re-graded | Cross-ref to compatibility matrix (updated) |
| A-8 | Functional: discovery smoke test passes for each target agent; invocation smoke test passes; `@skill-id` manual load verified for gated skills | V-4/V-5 test reports **executed**, not planned |
| A-9 | Permissions: `skill` rule assigned per risk class — LEVEL A knowledge-only ⇒ `allow`; LEVEL B instructs command execution (worktrees, gitops, CI/CD, migrations) ⇒ `ask`; LEVEL C credential/privileged/offensive domains ⇒ deny-by-default with human approval per rule; per-agent overrides consistent with the R5.2A fail-closed model | `opencode.json` diff + permission matrix entry |
| A-10 | Maintainability: supporting-file references beyond the 10-path sample limit explicitly enumerated in prose; regression test registered; re-audit trigger (upstream drift, OpenCode version) recorded | V-8 CI wiring |
| A-11 | Docs: `integrations/opencode/opencode-integration.md` updated (AUDIT-0002 F-09); `PROJECT_MAP.md` claim corrected to reality either way (F-07 / R-01) | Doc diff |

Any unmet MUST ⇒ NOT-USABLE (fail-closed). **No currently existing candidate satisfies A-8 or A-9**, because no skill is vendored and no runtime test has been executed — the 42 "ready-now" skills are *ready to onboard*, not *usable*, under this definition.

## 6. Recommendations for QA gates

Gate pipeline for the future skills initiative (G-gates run in order; any FAIL blocks promotion; evidence attached to each gate):

| Gate | Contents | Blocks on | Owner |
|---|---|---|---|
| **G0 — Governance entry** | Requirement approved; ADR ≥ 007 filed; scope (a)/(b) chosen; fail-closed permission model drafted and reconciled with R5.2A | Missing ADR/requirement; HTTP catalog or bulk-install proposals without explicit human approval (ADR-002) | AG-001 + AG-005 |
| **G1 — Static validation (CI)** | V-1 + V-2 on every PR touching skill dirs | Any structural/frontmatter violation; missing `description` | AG-012 (suite author) |
| **G2 — Uniqueness/precedence** | V-3 across all sources incl. config arrays | Any duplicate ID; adoption of the second copy of a known collision pair | AG-012 |
| **G3 — License/provenance** | V-7 manifest completeness; per-file license; pinned SHA + hashes | AGPL; unverifiable per-file license (all sickn33 today); SKILL.md vendored without supporting files | AG-018/AG-012, sign-off AG-003 |
| **G4 — Security** | V-6 scan + AG-015 verdict cross-check; ACCEPT-CONDITIONAL conditions closed item-by-item | REJECT rows (`architecture-review`, `security-audit`, `find-skills`); any HOLD row (all 32 sickn33); open conditions | AG-015/AG-003 (LEVEL C = human) |
| **G5 — Behavioral compatibility** | Review of process/behavior-injecting wording against agent contracts (no "invoke before ANY response"-class override survives review); model-neutral wording (`hads` class) | Behavior-injection conflicting with per-agent contracts | AG-005 + AG-012 |
| **G6 — Functional acceptance (live)** | V-4 + V-5 executed on the installed OpenCode build for each target agent; **also resolves OQ-4** — first run must verify the build honors `autoinvoke` and per-agent `skill` permissions as documented; results recorded against build version | Any advertised-list mismatch, permission leak (allow where ask), failed load, unverifiable permission semantics | AG-012 |
| **G7 — Release/quality gate** | All prior gates green + §5 A-1…A-11 evidenced; adoption manifest updated; docs (F-07/F-09 items) corrected; decision logged | Any missing evidence; PASS declared without executed G6 tests | AG-013/AG-015 per audit-contract |
| **G8 — Regression cadence (post-adoption)** | V-8 triggers: OpenCode version bump, upstream re-pin, `skills`/`skill`-permission config change, skills-dir edit | Skipped re-run on any trigger | AG-012 |

Additional QA recommendations:

1. **Build the harness before the inventory.** G1–G4 are fully implementable offline (filesystem + static analysis) with zero skills present; land `tests/skills/` + `scripts/validate_skills.py` now as initiative-readiness work, so the first adoption PR is gated on day one rather than retrofitted.
2. **Report counts, never invented percentages.** Use this matrix's reconciled buckets (42/5/9/4/30/3 of 93). Percentage coverage claims against 14 categories would imply executed capability validation that has not occurred.
3. **Registry labels are not gates.** Sickn33 `risk` values (critical/safe/unknown/offensive) have undefined semantics and counterexamples (AG-004 F-2, AG-015 §2) — G2/G4 must ignore them and rely on AG-015 verdicts only.
4. **Observation OBS-1 (traceability defect to fix before adoption counting):** `SKILLS_SECURITY_AUDIT.md` summary line reports "49 ACCEPT, 11 ACCEPT-CONDITIONAL" with per-repo breakdowns 39/6 and 10/5, but its own per-row tables contain **51 ACCEPT and 9 ACCEPT-CONDITIONAL** (40/5 wshobson; 11/4 superpowers). Combined ACCEPT+CONDITIONAL agrees (60), and no bucket used in §2 changes (HOLD 30 / REJECT 3 verified against rows), but the misclassification boundary matters because Ready-now counts require strict ACCEPT. This matrix uses **row-level** data as primary evidence; AG-015 should reconcile and re-state.
5. **Pinning discipline:** record upstream commit SHAs and per-file hashes at adoption; skills are mutable prompt content — treat any upstream drift as a new supply-chain change requiring G3–G6 re-runs (AG-015 rec. 7).
6. **Two-category in-house track:** requirements-engineering and quality-gate skills (M-1/M-2) should enter the pipeline at G1 on authoring day — factory-authored ≠ exempt; they face the same V-1…V-8 and §5 gates.
7. **Permission defaults:** deny default; allow-list only LEVEL A vendored skills; `ask` for the LEVEL B set (worktree/gitops/CI/CD/migration classes); never enable sickn33 credential-adjacent topics under HOLD without LEVEL C human approval path.

## 7. Assumptions, observations, limitations

- **A1** Taxonomy authority pending OQ-1; matrix will need re-baselining if AG-004/AG-001 issue an authoritative category list.
- **A2** All cross-tab counts in §2 are derived by joining AG-011 and AG-015 per-row verdicts on skill ID; both source documents remain authoritative for the individual verdicts.
- **OBS-1** See recommendation 4 (ACCEPT/ACCEPT-CONDITIONAL count discrepancy inside the security audit; totals unaffected).
- **OBS-2** Sickn33 showed same-day push churn (2026-11-19) and suspected rename (antigravity↔agentic); any future re-collection must re-pin canonical identity + SHA before adding to this matrix (AG-004 F-8).
- **OBS-3** Official docs baseline is a fetched summary, not live-verified behavior (AUDIT-0002 Limitation 2; ADR-003 requires re-verification against the installed build at design time — folded into G6).
- **L1** No tests executed in producing this document (none exist to run; none could pass meaningfully against 0 skills). No production code, config, or agent definitions modified. Sole file written: this one.
- **L2** Repo-level metadata (stars, push dates, skill totals) carried from tasking-provided values; unverifiable offline; excluded from all gating logic.

## 8. Traceability

- Current-state facts ← `AUDIT_CURRENT_SKILLS.md` F-01…F-06 (AUDIT-0002, PASS_WITH_OBSERVATIONS).
- Categories, roles, gaps, dedupe ← `EXTERNAL_SKILLS_RESEARCH.md` §3–§7 (REC-1…REC-6, OQ-1…OQ-4).
- Compatibility verdicts ← `SKILLS_COMPATIBILITY_MATRIX.md` per-row tables (47/13/1/32 summary verified against rows).
- Security verdicts ← `SKILLS_SECURITY_AUDIT.md` §5 per-row tables + §6 (H-1…H-4, M-1…M-4, L-1…L-3) + §7 gating recommendations.
- OpenCode mechanics (discovery, forms, IDs, precedence, loading, permissions, frontmatter semantics) ← `opencode_skills_official.md` fetched 2026-11-19; live re-verification owed at G6 per ADR-003.
- Governance references: ADR-002 (supervised autonomy), ADR-003 (verified syntax), ADR-004 (independent audit), ADR-005 (SQLite runtime), audit-contract evidence rule 5, R5.2A fail-closed permission model.
