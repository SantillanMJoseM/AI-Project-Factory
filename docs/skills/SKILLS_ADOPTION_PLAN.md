# Skills Adoption Plan

- **doc_id**: SKILLS-ADOPTION-PLAN-0001
- **created_at**: 2026-11-19
- **author**: AG-018 Documentation Engineer
- **status**: PROPOSAL — planning only. **Nothing is installed, enabled, vendored, committed, or published by this document.**
- **inputs**:
  - `docs/skills/AUDIT_CURRENT_SKILLS.md` (AUDIT-0002, AG-005, PASS_WITH_OBSERVATIONS)
  - `docs/skills/EXTERNAL_SKILLS_RESEARCH.md` (AG-004, 93 candidates, REC-1…REC-6, OQ-1…OQ-4)
  - `docs/skills/SKILLS_COMPATIBILITY_MATRIX.md` (AG-011, verdicts 47 COMPATIBLE / 13 NEEDS_ADAPTATION / 1 INCOMPATIBLE / 32 UNKNOWN)
  - `docs/skills/SKILLS_SECURITY_AUDIT.md` (AG-015; note row-level vs summary count discrepancy OBS-1)
  - `docs/skills/SKILLS_COVERAGE_MATRIX.md` (AG-012, adoption buckets and gates G0–G8, acceptance criteria A-1…A-11)
  - `/tmp/opencode/skills-work/opencode_skills_official.md` (official OpenCode Skills mechanics, fetched 2026-11-19)
  - `PROJECT_DECISIONS.md` (ADR-001…ADR-006; next free ADR ID ≥ 007 due to the duplicate-ADR-005 defect recorded as F-12)

## 1. Purpose and scope

### 1.1 Purpose

Define a prioritized, gated sequence for eventually adopting OpenCode Skills into AI-Project-Factory, so that the future initiative has a ready-made execution order, candidate groups, risk register, governance gates, and rollback procedures before any skill is vendored. This plan converts the four completed assessments (audit, research, compatibility, security) plus the QA coverage matrix into one staged adoption path.

### 1.2 Current state (verified, not assumed)

- **Zero skills exist today.** Re-verified 2026-11-19 for this plan: `.opencode/` contains only `agents/` (18 executable agent files); no `.opencode/skills`, `.claude/skills`, or `.agents/skills` at project or user level; `opencode.json` contains no `skills` key and no `skill` permission rules. This matches AUDIT-0002 findings F-01…F-06. The baseline is greenfield.
- **No approved requirement mandates skills** (AUDIT-0002 F-10). Every stage below is therefore contingent on Stage 0 producing the missing governance artifacts.
- The only skills advertised in current sessions (`opencode`, `report`) are OpenCode runtime built-ins, not repository artifacts.

### 1.3 Scope in / out

**In scope:** prioritized stages 0–5 with candidate groups; a top-20 ranked shortlist with expected benefits; risks and dependencies; governance gates; rollback procedures; documentation obligations.

**Out of scope (explicit prohibitions for this plan and its execution):**

- **No installation or enablement** of any skill at any stage described here; staging only happens inside a future approved initiative.
- **No commits:** adoption-stage work must not create Git commits, tags, or pushes. Committing staged artifacts remains a human/AG-001 decision under the factory rule "keep Git clean at stage closure" and ADR-002 (supervised autonomy).
- **No publication:** no releases, no external posting, no HTTP-catalog publication. HTTP skill catalogs are remote supply-chain surfaces and require explicit human approval per ADR-002; none is proposed here.
- **No bulk installs** of upstream marketplaces (AG-015 rec. 5; wshobson non-candidate plugins execute `npx` packages and rewrite `AGENTS.md` — outside any approval on file).
- Selecting consumption scope (a) factory agents vs (b) generated projects is a Stage-0 decision, not assumed here (AG-004 OQ-1/REC-1).

### 1.4 Candidate population and buckets (reconciled)

All counts below come from `SKILLS_COVERAGE_MATRIX.md` §2 (cross-tab of AG-011 compatibility × AG-015 security, reconciled to 93):

| Bucket | Definition | Count |
|---|---|---|
| Ready-now | COMPATIBLE × ACCEPT, no recorded change required | 42 (39 wshobson + 3 obra) |
| Ready-after-conditions | COMPATIBLE × ACCEPT-CONDITIONAL | 5 (all wshobson) |
| Adapt-then-review | NEEDS_ADAPTATION × ACCEPT | 9 (1 wshobson + 8 obra) |
| Adapt + conditions | NEEDS_ADAPTATION × ACCEPT-CONDITIONAL | 4 (all obra) |
| Blocked — HOLD | sickn33 rows with no available content | 30 |
| Blocked — REJECT | `architecture-review` (AGPL/MCP), `security-audit` (offensive), `find-skills` (installer) | 3 |

Total 42+5+9+4+30+3 = 93 ✓. Traceability note (OBS-1): the security audit's summary line (49 ACCEPT / 11 ACCEPT-CONDITIONAL) disagrees with its own per-row tables (51/9); this plan follows the coverage matrix's row-level reconciliation. AG-015 owns the restatement.

"Ready" here means *ready to onboard* — **no skill currently satisfies acceptance criteria A-8/A-9** (live discovery/invocation tests + permission assignment) because nothing is vendored and no runtime test has been executed.

## 2. Prioritized adoption stages (0–5)

Stages run in order. Entry to stage N requires exit criteria of stage N-1 met **with recorded evidence** (audit-contract rule 5). Gates G0–G8 are defined in §5 (mapping to AG-012's pipeline). Any FAIL blocks promotion.

### Stage 0 — Governance and harness prerequisites (zero skills)

**Candidate group:** none. This stage produces the artifacts that AUDIT-0002 and AG-004 REC-1 identify as missing.

| Item | Owner | Exit evidence |
|---|---|---|
| Requirement for a skills system raised and approved (closes F-10 gap via AG-004) | AG-004 → AG-001 | Approved requirement artifact |
| New ADR filed (ID ≥ ADR-007; log first reconciled per F-12/R-05) covering adoption posture, consumption scope (a)/(b), taxonomy authority (OQ-1) | AG-005, coordinator AG-001 | ADR entry in `PROJECT_DECISIONS.md` |
| `skill` permission model drafted, fail-closed (`deny` default), reconciled with the R5.2A model (AUDIT-0002 R-04) | AG-005 + AG-003 | Permission matrix proposal |
| Validation harness built **before the inventory** (AG-012 rec. 1): `tests/skills/` + `scripts/validate_skills.py` implementing V-1/V-2/V-3/V-6/V-7 offline checks | AG-012 | Green CI job on an empty fixture set |
| Documentation-drift fix: correct `PROJECT_MAP.md:19` skills/commands claim (F-07 / R-01) | AG-018 | Doc diff |

**Rationale:** G1–G4 are fully implementable with zero skills present; landing them first means the first adoption PR is gated on day one, not retrofitted.

### Stage 1 — Core governance-aligned knowledge set (LEVEL A, lowest risk, highest reuse)

**Candidate group:** the docs-knowledge + code-quality-review + a11y-independent Ready-now subset that directly encodes practices the factory already mandates — first 17 rows of the Top-20 shortlist (§3): e.g. `verification-before-completion`, `architecture-decision-records`, `code-review-excellence`, `receiving-code-review`, `error-handling-patterns`, `changelog-automation`, `openapi-spec-generation`, `grounded-vault`, `avoid-ai-writing`, `debugging-strategies`, `stride-analysis-patterns`, `security-requirement-extraction`, `python-testing-patterns`, `javascript-testing-patterns`, `e2e-testing-patterns`, `bats-testing-patterns`, plus one git-vcs entry (`git-advanced-workflows`, flagged B-candidate in §3).

- **Why first:** all are Markdown-only, guidance-only, MIT, AG-011 COMPATIBLE, AG-015 ACCEPT (LEVEL A knowledge-only → `allow` class); they reinforce (not override) agent contracts; `hads` and other adaptation items are deliberately excluded.
- **Entry:** G0–G4 green for each vendored directory. **Exit:** G5 review + G6 live smoke tests executed on the installed OpenCode build (first execution also resolves OQ-4) + G7 gate pass; `integrations/opencode/opencode-integration.md` updated (F-09).
- **Pilot cap:** ≤ 12 skills live per agent in the first increment to keep advertised lists reviewable; remainder staged on the same evidence path.

### Stage 2 — Testing and debugging method set (mix of Ready-now + Adapt-then-review)

**Candidate group:** remaining wshobson testing/debugging Ready-now (`python-performance-optimization`) plus the obra technique trio that needs complete-directory vendoring and adaptation: `systematic-debugging`, `test-driven-development`, `requesting-code-review`.

- **Adaptation debt paid here (AG-011):** vendor **complete** skill directories (references/scripts/templates — SKILL.md alone degrades verdicts), rewrite `superpowers:<id>` references to plain OpenCode IDs, replace `dot`/graphviz blocks, map any subagent instructions to OpenCode agent patterns, vendor the missing upstream LICENSE.
- **Entry:** Stage 1 exit + per-skill re-grade to COMPATIBLE after adaptation. **Exit:** same as Stage 1 plus V-5 invocation tests per adapted skill.

### Stage 3 — Security and compliance set (conditions closed first)

**Candidate group:** Ready-now wshobson security set — `attack-tree-construction`, `threat-mitigation-mapping`, `auth-implementation-patterns`, plus Stage-1 `stride-analysis-patterns`/`security-requirement-extraction` already live; Ready-after-conditions here: `sast-configuration` (disclose/disable Semgrep telemetry, keep pinned pre-commit rev) and `secrets-management` (add "dev only — never production" warning; never co-resident with the sickn33 same-ID copy).

- **Gate emphasis:** six security-critical ID collisions with sickn33 rows (AG-004 §6.1) must be proven absent from the enabled source set at G2; AG-003 re-adjudication (REC-4) precedes enablement; these remain defensive/methodology skills only — the offensive `security-audit (sickn33)` stays REJECT.
- **Entry:** Stage 2 exit. **Exit:** G4 condition-closure attestations item-by-item + G6/G7.

### Stage 4 — Process, planning, and workspace skills (adapt + conditions; behavior-sensitive)

**Candidate group:** the 4 Adapt+conditions rows — `writing-skills`, `writing-plans`, `executing-plans`, `using-git-worktrees`, `diagnosing-superpowers` (subset, see deferrals below) — plus remaining Ready-after-conditions: `api-design-principles` (harden template CORS/`0.0.0.0` defaults L-1), `github-actions-templates` (SHA-pin actions), `gitops-workflow` (pin ArgoCD manifest to release tag M-1 + secret-rotation note).

- **Permission posture:** these instruct command execution → LEVEL B (`ask`), not `allow` (AG-012 A-9).
- **Conflict handling (documented, not hidden):** AG-004 Tier-3 says do-not-adopt `using-superpowers`/`brainstorming`/delegation meta-skills (behavior injection); AG-015 rated `using-superpowers` ACCEPT-CONDITIONAL (M-2 soften wording); AG-011 rated both NEEDS_ADAPTATION. Fail-closed resolution: **excluded by default**; re-entry only via explicit Stage-4 decision in the ADR with softened wording, per-agent opt-in, and `autoinvoke:false`. `diagnosing-superpowers` stays deferred until the full upstream directory exists so its privacy-scrub logic can be audited (M-3). `executing-plans`/`subagent-driven-development`/`dispatching-parallel-agents` require mapping subagent dispatch to real OpenCode agent tooling or they are dropped.
- **Entry:** Stages 1–3 exits; G5 contract-conflict review run strictly. **Exit:** G6 live evidence per `ask`-gated skill; pilot scope limited to AG-001/AG-005/AG-012 before general enablement.

### Stage 5 — Specialty expansion, in-house authoring, and hygiene sweep

**Candidate groups:**

1. **Scope-(b) sets for generated projects** (only if the Stage-0 ADR opens scope (b)): wshobson ui-ux-accessibility 9-set and devops-delivery 7-set (K8s/Terraform/GitOps), which AG-004 F-7 rates poor fit for factory agents but good fit for generated projects.
2. **In-house authored skills** for the two zero-candidate gaps (AG-004 REC-5; AG-012 M-1/M-2): requirements engineering / acceptance-criteria / traceability (AG-004) and quality-gate/audit runbook (AG-002/003/013/015). Factory-authored ≠ exempt: same V-1…V-8 and A-1…A-11 path (AG-012 rec. 6).
3. **sickn33 unblock track (conditional, 30 HOLD):** only per-file — full content obtained, upstream per-skill license confirmed, AG-015 re-audit, prefer-the-audited-original for the 12+ overlaps. Repo treated as discovery index only (F-3); re-pin canonical identity given suspected rename (OBS-2).
4. **Hygiene cadence:** scheduled upstream-drift probe and re-pin window per skill (AG-012 rec. 5, V-8); next-round collection of wshobson non-candidate plugins observed by AG-004 (REC-6) run through the same tier framework.

## 3. Top-20 candidate shortlist (planning shortlist, not an approval list)

Ranked by factory-fit × low-friction (bucket, contract alignment, consumer breadth, risk class). Permission class per AG-012 A-9. "Bucket": RN = ready-now, AR = adapt-then-review.

| # | Skill | Repo | Bucket | Target stage | Primary consumers | Expected benefit |
|---|---|---|---|---|---|---|
| 1 | `verification-before-completion` | obra | RN | 1 | AG-013, AG-012, all builders | Codifies "no completion claims without fresh evidence" — matches audit-contract rule 5; strongest behavioral alignment found in any candidate |
| 2 | `architecture-decision-records` | wshobson | RN | 1 | AG-005, AG-001 | Standardizes ADR authoring; directly supports the ADR workflow the factory depends on (incl. the ≥ 007 decision this plan needs) |
| 3 | `code-review-excellence` | wshobson | RN | 1 | AG-013, AG-002 | Structured review practice: feedback quality, defect capture, severity framing |
| 4 | `receiving-code-review` | obra | RN | 1 | AG-013, all developers | Verifies feedback with rigor instead of performative agreement; self-contained, security-clean |
| 5 | `requesting-code-review` | obra | AR | 1–2 | AG-002, AG-013 | Disciplined review dispatch on task/feature completion; needs OpenCode agent mapping |
| 6 | `error-handling-patterns` | wshobson | RN | 1 | AG-008, AG-009, AG-011 | Consistent exception/Result-type handling across factory languages |
| 7 | `debugging-strategies` | wshobson | RN | 1 | AG-012, AG-014 | Systematic root-cause discipline; complements the factory's evidence-first audits |
| 8 | `systematic-debugging` | obra | AR | 2 | AG-012, AG-014 | Phase-gated bug method; requires full-directory vendoring + namespace rewrite |
| 9 | `test-driven-development` | obra | AR | 2 | AG-012, all builders | Red-green-refactor gate before implementation work; must vendor `writing-good-tests.md` |
| 10 | `python-testing-patterns` | wshobson | RN | 1 | AG-012 | pytest/fixtures/mocking — matches the factory's Python test stack (`tests/contracts/`) |
| 11 | `javascript-testing-patterns` | wshobson | RN | 1 | AG-012, AG-009 | Jest/Vitest/Testing-Library patterns for JS artifacts |
| 12 | `e2e-testing-patterns` | wshobson | RN | 1 | AG-012, AG-009 | Playwright/Cypress structure + flake debugging (pin `npx` versions per L-3) |
| 13 | `bats-testing-patterns` | wshobson | RN | 1 | AG-012, AG-016 | Shell-script testing for `install/` scripts — a real factory surface |
| 14 | `changelog-automation` | wshobson | RN | 1 | AG-018 | Keep-a-Changelog discipline; automates release-note upkeep AG-018 owns |
| 15 | `openapi-spec-generation` | wshobson | RN | 1 | AG-018, AG-008 | OpenAPI 3.1 authoring/validation for API docs obligations |
| 16 | `grounded-vault` | wshobson | RN | 1 | AG-018, AG-005 | Per-claim provenance + drift checks — operationalizes "document real state, flag discrepancies" |
| 17 | `avoid-ai-writing` | wshobson | RN | 1 | AG-018 | Prose quality control; contains an explicit prompt-injection defense (positive security finding) |
| 18 | `stride-analysis-patterns` | wshobson | RN | 1/3 | AG-003, AG-015 | Threat identification methodology feeding security requirements work |
| 19 | `security-requirement-extraction` | wshobson | RN | 1/3 | AG-003, AG-004 | Converts threats into requirements/tests — bridges AG-003 and AG-004 workflows |
| 20 | `git-advanced-workflows` | wshobson | RN | 1 | all dev agents | Rebase/bisect/worktree/reflog recovery technique; teaches destructive commands as **documentation** — pilot as `allow` under the fail-closed bash gate, or class B (`ask`) if the ADR prefers caution |

Composition: 17 Ready-now + 3 Adapt-then-review; 14 wshobson + 6 obra; no sickn33 or vercel-labs rows (all blocked); none is behavior-injecting; all fall in AG-015 ACCEPT or ACCEPT (rows 5/8/9) classes. Next-in-line alternates (also Ready-now): `python-performance-optimization`, `attack-tree-construction`, `threat-mitigation-mapping`, `auth-implementation-patterns`, `finishing-a-development-branch` (o), `architecture-patterns`, `microservices-patterns` (w).

## 4. Risks and dependencies

### 4.1 Risk register

| ID | Risk | Source evidence | Mitigation in this plan |
|---|---|---|---|
| K-1 | **Mutable prompt content / supply chain** — vendored skills are instructions, not code; upstream drift silently changes agent behavior | AG-015 §1 loading model, rec. 7 | Pin every vendored skill to an audited commit (e.g. `wshobson@4220308`); record per-file hashes; upstream re-pin = new supply-chain change ⇒ G3–G6 re-run (V-8) |
| K-2 | **ID collision precedence** — duplicate path-derived IDs resolve by registration order, **later source wins silently**; 11 known cross-repo collision pairs | AG-004 §6.1; AG-011 Known Issue 3; official docs Precedence | V-3 uniqueness gate before every merge; one-ID-per-concept workspace-wide (REC-3); project-local `.opencode/skills` only; keep global/compat dirs empty of factory content |
| K-3 | **Behavior injection vs per-agent contracts** — meta-skills demanding invocation before any response conflict with fail-closed permissions | AG-004 F-4; AG-015 M-2 | Exclude by default (Stage 4 conflict handling); `autoinvoke:false` for process skills; G5 review kills override-class wording |
| K-4 | **License exposure** — 1 AGPL-3.0-only (rejected), 1 Apache-2.0 (NOTICE obligations), 30 sickn33 per-file licenses unverifiable, obra snapshot lacks LICENSE | AG-015 §3 | Vendored copies carry LICENSE/NOTICE (G3); AGPL rejected; sickn33 gated on per-file evidence; obra full-clone requirement |
| K-5 | **Aggregator provenance** — sickn33 shows verbatim re-hosting (byte-identical description of `systematic-debugging`), scraped-looking quoted scalars, same-day churn, suspected rename | AG-004 F-3/F-8; OBS-2 | 30 HOLD + 2 REJECT excluded from Stages 0–4; discovery-index-only status; unblock track is per-file with re-audit |
| K-6 | **Installer class skills** — `find-skills` instructs `npx skills add -g -y` (silent global installs) | AG-015 H-1; AG-004 F-5 | REJECT upheld; skill discovery stays a human-run workflow; no HTTP catalogs without explicit human approval |
| K-7 | **Unverified runtime semantics (OQ-4)** — docs summary never tested against the installed build; `autoinvoke`/per-agent `skill` permissions unproven | AG-004 OQ-4; AG-015 Limitation 8; AG-012 M-8 | G6 live verification is a hard exit of Stage 1; ADR-003 requires re-verification at design time; no gate claims PASS on planned-but-unrun tests |
| K-8 | **Fit gaps** — DB candidates Postgres-centric vs SQLite runtime (ADR-005); devops candidates K8s/cloud vs OpenCode/LXC+install-scripts | AG-004 F-7; AG-012 M-5/M-6 | Those groups land only in Stage 5, mostly scope-(b); DB/devops Ready-now rows not promoted on bucket alone |
| K-9 | **Data-quality of inputs** — 100% registry categories were "TBD" (analyst construction, OQ-1); `risk` labels undefined and **not gate-usable**; repo metadata unverifiable offline | AG-004 F-2/F-8; AG-012 M-10, rec. 3 | No stage uses registry labels as gates; G2/G4 rely on AG-015 verdicts only; taxonomy ratified in the Stage-0 ADR |
| K-10 | **Snapshot incompleteness** — obra local clone is SKILL.md-only; supporting logic (privacy scrub, prompts, scripts) unauditable | AG-011 Known Issue 1; AG-015 M-3 | Any obra adoption requires complete upstream directory + re-grade before G5 |
| K-11 | **Documentation drift** — `PROJECT_MAP.md` already overstates skills presence; adoption docs must not compound it | AUDIT-0002 F-07 | Stage 0 correction; A-11 doc obligations per stage; this plan documents only what exists |

### 4.2 Dependencies

- **Governance:** ADR-002 (human approval for catalogs/critical ops), ADR-003 (verify against installed OpenCode, not fetched summaries), ADR-004 (independent audit — consumers may not self-approve), ADR-005/ADR-006 precedent (LEVEL C blocks), R5.2A fail-closed permission model.
- **Artifacts:** new ADR ≥ ADR-007; approved requirement (AG-004); `tests/skills/` + `scripts/validate_skills.py` (AG-012); AG-015 re-audit records per vendored byte change (V-6 "mandatory on every vendored byte change"); adoption manifest (V-7).
- **Roles:** AG-001 coordination; AG-002 gate chair; AG-003 risk adjudication (LEVEL C = human); AG-005 architecture/ADR; AG-012 harness + G6 execution; AG-013/AG-015 independent audit; AG-018 documentation obligations.
- **Ordering:** Stage 1 cannot start without Stage 0 exits; each later stage requires the prior stage's G7 evidence. The top-20 shortlist presupposes nothing about scope (b) — scope-(b) material is exclusively Stage 5.

## 5. Governance and gates

Gate pipeline verbatim from `SKILLS_COVERAGE_MATRIX.md` §6 (AG-012); any FAIL blocks promotion; evidence attached per gate; no PASS is declared for tests that have not run.

| Gate | Contents | Blocks on | Owner |
|---|---|---|---|
| G0 | Governance entry: requirement approved; ADR ≥ 007; scope (a)/(b); fail-closed permission model reconciled with R5.2A | Missing ADR/requirement; catalog/bulk-install proposals without human approval (ADR-002) | AG-001 + AG-005 |
| G1 | Static validation V-1 + V-2 on every change touching skill dirs | Structure/frontmatter violation; missing `description` | AG-012 |
| G2 | Uniqueness/precedence V-3 across all enabled sources | Any duplicate ID; second copy of a known collision pair | AG-012 |
| G3 | License/provenance V-7 manifest: pinned SHA, per-file license, hashes, complete directory | AGPL; unverifiable per-file license; SKILL.md without supporting files | AG-018/AG-012, sign-off AG-003 |
| G4 | Security V-6 scan + AG-015 verdict cross-check; ACCEPT-CONDITIONAL conditions closed item-by-item | REJECT rows; any HOLD row; open conditions | AG-015/AG-003 (LEVEL C = human) |
| G5 | Behavioral compatibility: no override-class wording survives; model-neutral prose | Behavior-injection conflicting with agent contracts | AG-005 + AG-012 |
| G6 | Functional acceptance on the **installed** OpenCode build: V-4 discovery + V-5 invocation per target agent; first run resolves OQ-4 | Advertised-list mismatch; permission leak; unverifiable permission semantics | AG-012 |
| G7 | Release/quality gate: §5 criteria A-1…A-11 (coverage matrix) evidenced; manifest + docs updated; decision logged | Any missing evidence; PASS without executed G6 | AG-013/AG-015 per audit-contract |
| G8 | Regression cadence V-8 triggers: OpenCode version bump, upstream re-pin, `skills`/`skill` config change, skills-dir edit | Skipped re-run on any trigger | AG-012 |

Additional governance rules binding this plan:

1. **Permission posture:** `deny` default; `allow` only LEVEL A vendored knowledge skills; `ask` for LEVEL B (worktree/gitops/CI/CD/migration command-executing class); LEVEL C domains (credentials, privileged ops, anything offensive) never enabled without a human-approval path per rule (AG-012 rec. 7; ADR-005/006 precedent).
2. **Fail-closed acceptance:** any unmet A-criterion ⇒ NOT-USABLE (coverage matrix §5). "Ready-now" = ready to onboard, never = usable.
3. **No registry labels as gates** (AG-012 rec. 3); only AG-015 verdicts and executed evidence count.
4. **Counts, never invented percentages** (AG-012 rec. 2); this plan reports 0 deployed skills, which is the only executed measurement available.
5. **Every stage closure updates docs** (A-11): `integrations/opencode/opencode-integration.md`, the adoption manifest, and a decision entry in `PROJECT_DECISIONS.md`.

## 6. Rollback

Skills inject Markdown only; nothing executes at load and no skill mutates persistent state, so rollback is configuration + file removal, with one honest residual: **a skill body already injected into an active conversation cannot be retracted** — no OpenCode control for that is documented. Rollback therefore prevents future loading; in-flight sessions are ended/restarted.

**Triggers:** any G8 regression failure; upstream drift discovered after pinning; new AG-015/AG-003 adverse finding; observed contract conflict in production use; scope creep into LEVEL C behavior; failure of OQ-4 verification at G6.

**Procedure (per skill, kill-switch first):**

1. **Disable fast:** set the `skill` permission rule for the affected ID to `deny` (per-agent or global) in `opencode.json` — deny hides/rejects immediately for new loads; restart affected sessions to bound the residual-injection window.
2. **Remove the artifact:** delete the vendored directory from `.opencode/skills/<id>/` (adoption must keep one directory per skill, staged as one reviewable unit, precisely so removal is atomic).
3. **Revert staging changes:** adoption work is expected to arrive as separate, skill-scoped staged changes; revert/restore the affected paths only. **Commit and push of any revert remains a human/AG-001 action** (this plan authorizes no Git operations; §1.3).
4. **Check collateral:** re-run V-3 to confirm no now-orphaned duplicate gains precedence in an unexpected direction (later-source-wins means removing the winner can resurrect an earlier-registered copy — the removal step must target **all** sources for that ID).
5. **Update records:** manifest row → `SUSPENDED`/`RETIRED` with reason and evidence; decision logged in `PROJECT_DECISIONS.md`; `integrations/opencode/opencode-integration.md` re-aligned; escalation to AG-001 (and AG-003 if security-driven).
6. **Re-admission:** a rolled-back ID returns only through the full G1–G7 path as if new.

**Batch rollback:** if a stage's pilot group misbehaves systemically, deny the stage's ID list in one permission-rule pass, then remove directories stage-by-stage; Stage 0 artifacts (harness, ADR) are never rollback targets — they stay regardless of adoption outcome.

**No-data caveat:** because skills hold no state, there is no data migration, secret rotation, or DB recovery step in rollback — unless a skill previously *instructed* an agent to perform an operation, in which case that operation's own recovery procedures (per-agent runbooks) apply; the rollback here only stops recurrence.

## 7. Explicit non-actions and compliance

- This document performed **no installation, enablement, vendoring, configuration change, commit, publication, or external posting**. No files under `.opencode/`, `opencode.json`, `agents/`, or `install/` were created or modified.
- Sole files written by this tasking: `docs/skills/SKILLS_ADOPTION_PLAN.md` and `docs/skills/SKILLS_REGISTRY_PROPOSAL.md`.
- All stage, gate, and bucket statements cite the five input documents; where inputs disagree (OBS-1 count discrepancy; Tier-3 vs ACCEPT-CONDITIONAL on `using-superpowers`), the disagreement is recorded rather than resolved unilaterally, and the fail-closed reading is taken as the default.
- Ownership of open items: OQ-1 taxonomy and scope decision → AG-001/AG-004 via the Stage-0 ADR; OBS-1 restatement → AG-015; PROJECT_MAP correction → AG-018 (Stage 0); permission enforcement proof → AG-012 at G6.
