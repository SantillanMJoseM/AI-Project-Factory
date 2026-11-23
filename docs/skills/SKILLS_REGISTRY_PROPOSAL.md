# Skills Registry Proposal

- **doc_id**: SKILLS-REGISTRY-PROPOSAL-0001
- **created_at**: 2026-11-19
- **author**: AG-018 Documentation Engineer
- **status**: PROPOSAL — design input for the future skills ADR (≥ ADR-007). **Nothing described here exists or is installed.** A registry structure, metadata schema, and automation targets are *specified*, not *implemented*.
- **inputs**: `docs/skills/AUDIT_CURRENT_SKILLS.md` (AUDIT-0002) · `docs/skills/EXTERNAL_SKILLS_RESEARCH.md` (AG-004) · `docs/skills/SKILLS_COMPATIBILITY_MATRIX.md` (AG-011) · `docs/skills/SKILLS_SECURITY_AUDIT.md` (AG-015) · `docs/skills/SKILLS_COVERAGE_MATRIX.md` (AG-012) · `docs/skills/SKILLS_ADOPTION_PLAN.md` (this initiative's companion plan) · `/tmp/opencode/skills-work/opencode_skills_official.md` (official mechanics, fetched 2026-11-19) · `agents/` + `.opencode/agents/` catalogs (18 agents, verified 2026-11-19)

## 1. Current state and intent

Verified 2026-11-19 (re-check of AUDIT-0002 F-01…F-05): the repository has **no skills registry, no skills directories, no `skills` configuration, and zero vendored skills**; `.opencode/` contains only `agents/`. Therefore everything below is a proposal to be ratified by a future ADR before any of it is created.

Intent: give the factory **one authoritative index** for every skill it may ever enable — provenance, license, security verdict, permissions, and agent assignment — so that adoption is auditable, duplicate-free, and reversible. The registry separates the *library* (canonical, fully described, not all enabled) from the *enablement layer* (what OpenCode actually discovers), because OpenCode itself has no registry concept: it only walks discovery locations and applies registration-order precedence.

## 2. Proposed directory structure

### 2.1 Two layers

```
AI-Project-Factory/
├── skills-library/                    # (proposed) CANONICAL LIBRARY — versioned, described, NOT a
│   ├── README.md                      #   discovery location; OpenCode never sees this directly
│   ├── registry.json                  #   machine-readable index, one entry per skill (§3)
│   ├── global/                        #   tier: baseline for every agent
│   │   └── <skill-id>/SKILL.md        #   (+ references/ assets/ scripts/ LICENSE NOTICE ...)
│   ├── shared/                        #   tier: cross-role, common to a group of agents
│   │   └── <skill-id>/SKILL.md
│   ├── specialty/                     #   tier: domain-specific
│   │   ├── docs-knowledge/…
│   │   ├── testing/…
│   │   ├── security-compliance/…
│   │   ├── code-quality-review/…
│   │   ├── debugging-performance/…
│   │   ├── architecture-design/…
│   │   ├── agent-process/…
│   │   ├── ui-ux-accessibility/…
│   │   ├── backend-api/…
│   │   ├── database-data/…
│   │   ├── devops-delivery/…
│   │   └── git-vcs/…
│   ├── project/                       #   tier: single-project or scope-(b) generated-project skills
│   │   └── <project-or-template>/…
│   └── in-house/                      #   factory-authored (requirements-eng, quality-gate — M-1/M-2)
│       └── <skill-id>/SKILL.md
│
└── .opencode/skills/                  # ENABLEMENT LAYER — official project discovery location
    └── <skill-id>/SKILL.md            #   promotion copies ONLY (byte-identical or adaptation-marked)
                                       #   from skills-library; one directory per skill
```

**Tier definitions** (the four tiers named in the tasking):

| Tier | Audience | Example content | Enablement default |
|---|---|---|---|
| **global** | every agent, every project | `verification-before-completion` | enabled early (Stage 1) once gated |
| **shared** | a role group across the factory | testing/debugging/docs method sets | enabled per stage |
| **specialty** | one domain group | security 5-set, UI/a11y 9-set, devops 7-set | enable only where the consumer group exists |
| **project** | one project or generated-project scope (b) | K8s/Terraform sets for a project that deploys to K8s | never auto-enabled factory-wide |

(`in-house/` is a provenance partition of shared/specialty, kept separate because factory-authored skills face the same gates — AG-012 rec. 6 — but have no upstream pin/hash fields to fill; they record `source.type: in-house` instead.)

### 2.2 Why this shape (mechanics-driven, from official docs)

- **Enablement only at `.opencode/skills`** (project layer): the official registration order is 1 built-ins → 2 `~/.claude/skills` compat → 3 `~/.agents/skills` compat → 4 `~/.config/opencode/skills` → 5 project `.opencode/skills` → 6 explicit `skills` config entries, and **a duplicate ID resolves to whichever source registered later**. AUDIT-0002 R-04 and AG-004 REC-3 both conclude: keep all factory content in the project layer, so nothing uncontrolled in a global or compat path can silently shadow it — or be shadowed by it.
- **Policy: factory content must never be placed in** `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`, `.claude/skills`, or `.agents/skills`. Those five locations are registered *earlier* than (or as noise alongside) the project source; an ID living in two of them creates the silent-override hazard (AG-004 §6.1). The registry (§4.3) asserts their emptiness as a standing invariant.
- **One directory per skill at the enablement layer**: OpenCode treats a directory containing `SKILL.md` as exactly one skill and does not search inside it; nested `skills-library/specialty/<category>/` paths are a human-organization concern that must be **flattened on promotion**, because if nested dirs were ever discovered directly the ID would derive from the `SKILL.md` parent only (`skills/teams/release/SKILL.md → ID release`) — category would vanish from the path and collisions would surprise us.
- **Project-local forms respected**: promotion copies keep the official forms — `skills/<id>/SKILL.md` (directory form, required whenever supporting files exist) with paths inside the skill written **relative to the SKILL.md directory** (supporting files are listed, up to 10 sample paths, but never auto-loaded — the skill prose must say when to read them).
- **Search limits observed**: discovery walks from cwd up to the project root, max **six levels** below a source root, skipping hidden dirs and `node_modules`; library paths are designed to stay well inside that even if a library tier were ever mounted as a source directly (not proposed).
- **`skills` config array and HTTP catalogs:** the proposal does **not** enable any HTTP catalog. If one is ever proposed (e.g., a factory-curated catalog serving `<base-url>/<name>/<file>` with `index.json`, `SKILL.md` or `<name>.md` entry file, cache refresh via version bump), it is a remote supply-chain surface requiring explicit human approval under ADR-002, and its entries would need registry rows and a `source.type: http-catalog` marker. Also note: relative paths in the `skills` array resolve from the **working directory, not the config file** — a trap the validation suite (V-4) must test rather than assume.

## 3. Metadata schema

### 3.1 Two metadata planes — and why both are needed

Official mechanics limit what OpenCode reads: frontmatter `name` (display-only) and `description` (required in practice — no description ⇒ never advertised); `metadata.opencode/autoinvoke` / `disable-model-invocation` (autoinvoke wins if both) to control model-driven loading; V2 *accepts but does not interpret* portability fields `license` and `compatibility`; and **IDs are path-derived and case-sensitive**, with the lowercase-kebab 1–64-char pattern recommended but *not enforced* by V2. Consequently any governance metadata beyond those fields is documentation, not behavior — which is exactly what a registry needs, but it must never be mistaken for enforcement. The registry therefore splits:

**Plane A — SKILL.md frontmatter (interpreted by OpenCode; minimal):**

```yaml
---
name: Architecture Decision Records      # display only
description: >                           # REQUIRED for advertisement
  Write and maintain ADRs following the factory decision workflow.
metadata:
  opencode:
    autoinvoke: false                    # explicit for process-class skills (REC-3)
---
```

**Plane B — `skills-library/registry.json` entry (governance; validated in-house):**

```json
{
  "schema_version": "1.0",
  "skill_id": "architecture-decision-records",
  "tier": "shared",
  "category": "docs-knowledge",
  "library_path": "skills-library/shared/architecture-decision-records",
  "enabled_in": [".opencode/skills/architecture-decision-records"],
  "source": {
    "type": "vendored-upstream",
    "repo": "wshobson/agents",
    "canonical_url": "https://github.com/wshobson/agents",
    "upstream_path": "plugins/.../skills/architecture-decision-records",
    "commit_sha": "4220308",
    "cloned": "2026-11-19"
  },
  "license": {
    "scope": "per-file-verified",
    "spdx": "MIT",
    "notice_files": ["LICENSE"],
    "verified_by": "G3",
    "verified_at": "2026-11-19"
  },
  "integrity": {
    "file_hashes": { "SKILL.md": "sha256:...", "references/template.md": "sha256:..." },
    "complete_directory": true,
    "local_modifications": "none | wording-model-neutral | namespace-rewrite | hardening(...)"
  },
  "verdicts": {
    "compatibility": { "verdict": "COMPATIBLE", "doc": "SKILLS_COMPATIBILITY_MATRIX.md", "row": "adr" },
    "security": { "verdict": "ACCEPT", "risk_class": "A", "doc": "SKILLS_SECURITY_AUDIT.md", "conditions_closed": [] },
    "behavior_review": { "verdict": "PENDING", "gate": "G5" }
  },
  "permissions": {
    "risk_class": "A",
    "rule": "allow",
    "per_agent_overrides": {},
    "autoinvoke": false
  },
  "assignment": { "agents": ["AG-005", "AG-018", "AG-001"], "scope": "factory-agents" },
  "versioning": {
    "upstream_pin": "wshobson@4220308",
    "local_rev": 0,
    "registry_version": "0.1.0+pin.4220308",
    "history": [
      { "event": "adopted-via-ADR", "adr": "ADR-007", "date": "TBD", "gates": ["G1","G2","G3","G4"] }
    ]
  },
  "lifecycle": "APPROVED",
  "reaudit_triggers": ["upstream-drift", "opencode-version-bump", "permission-change", "content-edit"],
  "notes": "Row-level provenance example; values are schema illustration — no registry exists today."
}
```

### 3.2 Field obligations

| Group | MUST | Rationale |
|---|---|---|
| identity | `skill_id` matches the path-derived ID exactly (case-sensitive, lowercase kebab ≤ 64) | V2 does not enforce the pattern — linting (V-1/V-3) must, per AG-012 §4 |
| source | pinned commit SHA + upstream path + clone date; `type` ∈ vendored-upstream / adapted / in-house / http-catalog | skills are mutable prompt content; pinning is the only defense against silent drift (AG-015 rec. 7) |
| license | **per-file** verification status; AGPL ⇒ lifecycle never ACTIVE; Apache-2.0 ⇒ NOTICE listed | AG-015 §3; repo-level license strings of aggregators are claims, not evidence (F-3) |
| integrity | per-file SHA-256; `complete_directory: true` whenever the skill references supporting files | vendored SKILL.md without references was the core obra verdict-degrader (AG-011 Known Issue 1) |
| verdicts | cross-references to the compat and security documents, row-level, not summary-level | OBS-1 showed summary counts can diverge from rows |
| permissions | risk class A/B/C → `allow`/`ask`/`deny`, matching adoption-plan §5 posture | fail-closed alignment with R5.2A |
| assignment | ≥ 1 consumer agent from the 18-agent catalog | orphan-enabled skills advertise dead context |
| lifecycle | one of the §6 states; `TBD`/undated fields stay placeholder until the real gate runs | A-1…A-11 evidence rule: no fabricated PASS |

## 4. Discovery and assignment by agent responsibility

### 4.1 Deterministic discovery algorithm (proposed V-3/V-4 extension)

1. Enumerate enabled sources in official registration order 1→6 for the factory host/user context.
2. Derive each ID from its path (`<id>.md` at a source root → `<id>`; `<id>/SKILL.md` → `<id>`), case-sensitively.
3. Assert: global/compat locations (order 2–4) contain **no** factory content; project layer contains only promoted copies that resolve in `registry.json`.
4. Compute the effective winner per ID under later-source-wins; assert it equals the registry's `enabled_in` — i.e., no shadowing in either direction.
5. Live probe (only after any skill exists): advertised list shows exactly the permitted, described, autoinvoke-eligible set (ID/name/description only, per Loading semantics); `deny` hides; `autoinvoke:false` removes from the model's list yet stays loadable by ID and `@skill-id`.

### 4.2 Assignment model

Assignment is **per-agent `skill` permission** (`agents.<id>.permissions`, ordered rules, last match wins), not directory placement — the discovery layer stays one flat set per skill; the permission layer carves visibility. Default posture: global rule `deny` for `skill`, plus per-agent `allow`/`ask` rows generated from `registry.json` `assignment`, so the registry is the single source of truth and `opencode.json` is a derived artifact (drift between them = G8 trigger).

Consumer mapping uses the 14-category set from `SKILLS_COVERAGE_MATRIX.md` §1.2 (its category→role rows), against the verified 18-agent catalog in `agents/` and `.opencode/agents/`:

| Responsibility area | Agent(s) | Categories they receive | Notes |
|---|---|---|---|
| Coordination | AG-001 | agent-process, git-vcs | process skills `ask`-gated, `autoinvoke:false` |
| Quality gatekeeping | AG-002 | code-quality-review, agent-process | review-dispatch skills |
| Security/risk management | AG-003 | security-compliance, quality-gate (in-house) | LEVEL C domains stay human-gated |
| Business analysis | AG-004 | requirements-engineering (in-house only — zero external candidates) | M-1 gap |
| Architecture | AG-005 | architecture-design, docs-knowledge, agent-process | ADR skill is a Stage-1 anchor |
| UX/UI design | AG-006 | ui-ux-accessibility | mostly Stage 5 scope-(b) |
| Database architecture | AG-007 | database-data | fit-check vs SQLite (M-5) |
| Backend development | AG-008 | backend-api, git-vcs | |
| Frontend development | AG-009 | ui-ux-accessibility, testing | |
| Database development | AG-010 | database-data | |
| Integration | AG-011 | backend-api, devops-delivery | |
| QA automation | AG-012 | testing, debugging-performance | owns the harness that enforces §4.1 |
| Code review | AG-013 | code-quality-review | |
| Performance | AG-014 | debugging-performance | |
| Security audit | AG-015 | security-compliance, quality-gate (in-house) | audits, never consumes un-vetted security content blindly |
| DevOps | AG-016 | devops-delivery, git-vcs | LEVEL B classes ⇒ `ask` |
| Deployment | AG-017 | devops-delivery | `gitops-workflow` only with conditions closed |
| Documentation | AG-018 | docs-knowledge | `grounded-vault`/`avoid-ai-writing` align with AG-018 limits ("reflect real state") |

Assignment rules: (a) an agent gets a skill only if its category matches a responsibility area above **and** the skill's risk class is compatible with the agent's permission posture; (b) in-house governance skills (M-1/M-2) are assigned to exactly their owner group (e.g., quality-gate runbook → AG-002/003/013/015); (c) scope-(b) skills are assigned to generated-project agent sets, never factory agents; (d) any deviation is an ADR amendment, not an ad-hoc permission edit.

### 4.3 Standing invariants (proposed, checkable)

- I-1: `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`, `.claude/skills`, `.agents/skills` contain no factory-managed content (AUDIT-0002 baseline is empty; check it stays that way).
- I-2: every ID in `.opencode/skills/` has exactly one registry entry, and vice versa.
- I-3: `opencode.json` `skill` rules are byte-derived from `registry.json` (regenerate, don't hand-edit).
- I-4: no HTTP catalog configured without a registry entry carrying human-approval evidence.

## 5. Deduplication detection

Three detection layers, all offline, run at G2 before any promotion and re-run by V-8 on any change:

1. **Exact ID collision (hard fail).** Derive IDs from paths across *all* enabled sources + configured `skills` array entries; assert global uniqueness, case-sensitive. Also flag case-insensitive near-collisions (`TDD` vs `tdd`) since IDs are case-sensitive but humans are not. The 11 known cross-repo collision pairs (AG-004 §6.1: `architecture-decision-records`, `microservices-patterns`, `code-review-excellence`, `api-design-principles`, `auth-implementation-patterns`, `secrets-management`, `sql-optimization-patterns`, `database-migration`, `e2e-testing-patterns`, `git-advanced-workflows`, `systematic-debugging`) are a seeded block-list: second copy of any pair ⇒ automatic FAIL.
2. **Content duplication (review trigger).** SHA-256 of normalized SKILL.md across the library: identical hashes in two entries ⇒ merge decision. Fuzzy fingerprint of `description` text catches re-hosted content — the byte-identical obra/sickn33 `systematic-debugging` description (AG-004 §6.1) is the worked example that proves metadata-level copying occurs in the wild.
3. **Concept duplication (policy).** A maintained concept register derived from AG-004 §6.2 near-duplicate clusters (debugging method, TDD, code review, Postgres, a11y audit, threat modeling, CI/CD design, Kubernetes, API docs, design systems, git worktrees). Policy: **one ID per concept workspace-wide** (REC-3); adding a second skill on a registered concept requires retiring or explicitly scoping the first in the ADR. Aggregator internal-bundle duplication (same skill at 6 paths inside sickn33, §6.3) is why library ingest runs layers 1–2 before anything is stored, not after enablement.

Output of each run: `tests/skills/` report attached to the PR; a FAIL anywhere in 1–2 blocks promotion absolutely; layer-3 conflicts block until a decision row is recorded.

## 6. Update controls

**Lifecycle states (registry `lifecycle` field):**

```
CANDIDATE → REVIEWED(compat+security rows cross-refed) → APPROVED(ADR+G0–G4)
    → STAGED(pilot agents only, `ask`) → ACTIVE
ANY state → SUSPENDED (kill-switch: permission deny, adoption plan §6) → RETIRED (dir removed, row kept)
SUSPENDED → (re-entry) full G1–G7 as new
```

**Change classes and required re-runs** (V-8 trigger matrix):

| Change | Example | Re-run |
|---|---|---|
| C1 upstream re-pin (new commit) | wshobson moves past `4220308` | V-6,V-7 diff + G3–G6 — treated as a **new supply-chain change** (AG-015 rec. 7), not a routine bump |
| C2 local modification | `hads` Claude-wording neutralization; `superpowers:` namespace rewrite | re-grade compat (AG-011), V-1–V-3, G5 |
| C3 permission/assignment edit | AG-016 gains `gitops-workflow` | regenerate `opencode.json` from registry, V-4 discovery probe, G4 if class ≥ B |
| C4 OpenCode version bump | runtime upgrade | full V-1–V-8 regression; **OQ-4 re-verified every time** (docs summary ≠ installed behavior; ADR-003) |
| C5 docs/config drift | hand-edited `opencode.json` | invariant I-3 check fails ⇒ revert-to-registry, G8 log entry |
| C6 security reclassification | AG-003 downgrades a verdict | immediate SUSPENDED pending review |

**Cadence and controls:** upstream-drift probe runs on a schedule *fixed by the ADR* (this proposal deliberately does not invent an SLA); each probe diffs hashes in `integrity.file_hashes` against the pinned commit; a positive drift opens a C1 ticket, it does not auto-update anything. All state transitions require the responsible owner (AG-012 harness, AG-015/AG-003 security, AG-018/AG-012 provenance rows, AG-002/AG-013 gate closure) and leave an append-only `history` entry; registry rows are never deleted, only RETIRED, so evidence chains survive.

## 7. Acceptance criteria (this registry, and the docs that define them)

The registry proposal itself is acceptable for ADR review when every row below has a produced artifact — **all are "not started" as of 2026-11-19**:

| # | Criterion | Status today | Defining document |
|---|---|---|---|
| R-1 | Directory layout (§2.1) exists with `registry.json` schema validated by V-1/V-2-style lint | Not started (no dirs exist) | this doc |
| R-2 | Every promoted skill resolves to exactly one registry entry; invariants I-1…I-4 machine-checked in CI | Not started | this doc §4.3 |
| R-3 | Metadata Plane A limited to OpenCode-interpreted fields; Plane B carries governance without pretending to enforce | Not started | official docs summary (fetched 2026-11-19) |
| R-4 | Per-skill acceptance passes **A-1…A-11** of `SKILLS_COVERAGE_MATRIX.md` §5 (structure, frontmatter, uniqueness, provenance, safety, compatibility, functional G6, permissions, maintainability, docs) | 0 of 93 — no candidate satisfies A-8/A-9 (nothing vendored or runtime-tested) | coverage matrix §5 |
| R-5 | Dedup layers 1–3 run green over the full enabled set incl. the seeded 11-pair block-list | Not started | this doc §5 + AG-004 §6 |
| R-6 | Update-control state machine wired to V-8 triggers; every transition evidenced | Not started | this doc §6 + adoption plan §5 |
| R-7 | Rollback path per skill matches adoption plan §6 (kill-switch → removal → precedence re-check → records) | Not started | adoption plan §6 |
| R-8 | Documentation obligations closed: `integrations/opencode/opencode-integration.md` updated at first enablement; `PROJECT_MAP.md:19` corrected (AUDIT-0002 F-07/F-09); ADR ≥ 007 filed | Not started (log first reconciles duplicate ADR-005 per F-12/R-05) | AUDIT-0002 R-01/R-05 |

Acceptance of *individual skills* is governed by coverage matrix §5 (fail-closed: any unmet MUST ⇒ NOT-USABLE); acceptance of the *governance pipeline* is AG-012's gates G0–G8 (coverage matrix §6), sequenced for execution by `docs/skills/SKILLS_ADOPTION_PLAN.md`.

## 8. Limitations and compliance

- No OpenCode Skills system, registry, directory, schema file, or permission rule described in this document exists today; this document does not implement one. All mechanisms are specified, not executed, and nothing here claims a PASS for work not performed.
- The OpenCode mechanics relied on (discovery locations, path-derived case-sensitive IDs, registration-order precedence with later-source-wins, non-auto-loaded supporting files, permission effects, catalog shape) come from the fetched official summary dated 2026-11-19 and must be re-verified against the installed build at design time per ADR-003 (OQ-4).
- The category taxonomy (14 areas) is still the analyst construction pending OQ-1; the ADR must ratify it or issue an authoritative list before `registry.json` `category` values are frozen.
- Sole files written by this tasking: `docs/skills/SKILLS_ADOPTION_PLAN.md` and this file. No commits, publications, configuration changes, or agent-definition changes were made.
