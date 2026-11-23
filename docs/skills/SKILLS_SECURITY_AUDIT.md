<!-- Generated from the final response of AG-015 Security Auditor (session ses_e0c5cba02ffe4YZmt7FvJ2RIjL). -->
<!-- Coordinator wrote this file because AG-015 has write: deny. Audit results were not modified. -->

# Security Audit Report — Candidate Skills (93)

**Auditor:** AG-015 Security Auditor · **Date:** 2026-11-19 · **Classification:** Internal
**Method constraint:** Static file review only. No shell execution, no network requests (per tasking).

---

## 1. Scope and Method

**Scope:** 93 candidate skills from 4 repositories, as listed in `/tmp/opencode/candidates.json`:

| Repo | Candidates | Local evidence available |
|---|---|---|
| wshobson/agents | 45 | Full clone at `/tmp/opencode/wshobson` (commit `4220308`, cloned 2026-11-19 per `.git/logs/HEAD`) |
| obra/superpowers | 15 | Partial snapshot at `/tmp/opencode/sp` — 15 `SKILL.md` files only |
| sickn33/antigravity-awesome-skills | 32 | **None** — frontmatter/risk labels in `candidates.json` only |
| vercel-labs/skills | 1 | Local copy found at `/tmp/opencode/vercel-skills` (used to verify `find-skills`; MIT LICENSE present) |

**Method:**
1. Full file inventory of all candidate directories (glob), confirming which candidates ship executable assets vs. Markdown only.
2. Full reads of high-signal files: all executable assets in candidate paths, `using-superpowers`, `using-git-worktrees`, `finishing-a-development-branch`, `diagnosing-superpowers`, `writing-skills`, `secrets-management`, `sast-configuration`, `hads`, `grounded-vault`, `find-skills`, repo LICENSE/README files.
3. Pattern scans across all locally available candidate content for: remote-fetch-and-execute (`curl|sh`, `wget|sh`), network URLs, `base64`, `/dev/tcp`, destructive commands (`rm -rf`, `reset --hard`, `push --force`, `branch -D`), privilege escalation (`sudo`), hardcoded credentials (AKIA/sk- patterns), CI secret misuse (`pull_request_target`), and prompt-injection markers ("ignore previous instructions", "secretly", "do not tell the user", exfiltration).
4. Frontmatter check for permission/autoinvoke manipulation (`allowed-tools`, `disable-model-invocation`, `metadata.opencode/autoinvoke`).
5. License review against project context (AI-Project-Factory has **no LICENSE file** — internal/unlicensed project).

**OpenCode loading model** (per `opencode_skills_official.md`): skills inject Markdown into the conversation on invocation; supporting files are not auto-loaded; no candidate code executes on load. Risk therefore materializes only when the agent *follows* skill instructions. All findings below are assessed on that basis.

---

## 2. Repository-Level Findings

### wshobson/agents — LOW repository risk, curated subset required
- **License:** MIT, verified (`LICENSE`, © 2024 Seth Hobson).
- **Maintainer:** single primary maintainer (Seth Hobson); bus-factor risk, no institutional backing.
- **Activity:** snapshot freshly cloned 2026-11-19; README documents CI validation, multi-harness adapters, and a `plugin-eval` static checker — signs of active maintenance. Commit history not inspectable without git commands (see Limitations).
- **Scale/attack surface:** 93 plugins, 199 agents, 185 skills, 103 commands. The repo contains components **outside** the candidate set that execute third-party code via hooks (`protect-mcp`, `review-agent-governance` hooks run `npx protect-mcp@0.32.4` / `npx @veritasacta/verify@0.11.1`) and instruct global CLI installs (`superself`: `npm install -g superself@0.6.1`, writes managed blocks into `AGENTS.md`/`CLAUDE.md`). **Do not install the whole marketplace; adopt only the audited candidate files.**
- All 45 candidate frontmatters contain only `name`/`description`; no tool-permission or autoinvoke manipulation found.

### obra/superpowers — LOW content risk, MEDIUM snapshot-integrity risk
- **License:** MIT per gathered metadata; **no LICENSE file in the local snapshot** — must be vendored with the upstream license text before adoption.
- **Maintainer:** obra (Jesse Vincent), well-known project; activity not verifiable locally (no `.git` in snapshot).
- **Integrity gap:** the snapshot contains only 15 `SKILL.md` files. Multiple skills reference supporting files that are **absent**: `using-superpowers` → `references/*-tools.md`; `diagnosing-superpowers` → `references/session-discovery.md`, `prompts/scrub.md`, `prompts/scrub-audit.md`, `templates/*`; `writing-skills` → `references/anthropic-best-practices.md`, cross-skill references. The privacy-scrubbing and session-discovery logic of `diagnosing-superpowers` **cannot be audited** until those files are obtained.
- Content is process documentation with strong human-consent gates (see §4).

### sickn33/antigravity-awesome-skills — HIGH provenance risk (aggregator)
- **License:** repo-level MIT, but per-skill licenses are heterogeneous and explicitly unverified ("MIT (repo; check individual)"); one candidate is **AGPL-3.0-only**, one **Apache-2.0**. Aggregated third-party content with unclear upstream attribution.
- **No local content provided for any of the 32 candidates.** The `risk` labels (`critical` ×20, `safe` ×10, `offensive` ×1, `unknown` ×1) are third-party metadata, **not audit results**; they appear topic-based (e.g., `systematic-debugging` labeled `critical` while the near-identical superpowers skill is benign). They cannot be relied on in either direction.
- Maintainer/activity: not verifiable from provided inputs.

### vercel-labs/skills — LOW repository risk, HIGH behavioral risk in the candidate
- **License:** MIT verified (`LICENSE`, © 2026 Vercel, Inc.). Reputable organization.
- The single candidate `find-skills` is a skill *installer/discoverer* — a supply-chain amplifier (see §6, H-1).

---

## 3. License Compatibility Table

Project baseline: AI-Project-Factory is internal, **no LICENSE declared** (treat as proprietary/internal-use; no outbound copyleft obligations currently, but distribution posture must be decided before any external release).

| Candidate license | Candidates | Compatibility | Conditions / action |
|---|---|---|---|
| MIT (wshobson repo) | 45 | ✅ Compatible | Retain copyright + license notice in vendored copies |
| MIT (superpowers, per metadata) | 15 | ✅ Compatible | **Obtain and vendor upstream LICENSE** (absent from snapshot) |
| MIT (sickn33 repo-level, per-skill unverified) | 30 | ⚠️ Conditional | Per-skill upstream license must be confirmed before adoption; aggregator relicensing is not authoritative |
| Apache-2.0 (`deep-research`, sickn33) | 1 | ✅ Compatible | Retain NOTICE/attribution; patent-grant terms acceptable for internal use |
| AGPL-3.0-only (`architecture-review`, sickn33) | 1 | ❌ Incompatible with proprietary/network distribution | AGPL network-use copyleft would attach to any service incorporating it. **Reject** or route to legal review (AG-003 LEVEL C security/policy exception) |
| MIT (vercel-labs) | 1 | ✅ Compatible | Retain notice |

---

## 4. Dependency / Script / Access / Network / Credential / Prompt-Injection Analysis

### 4.1 Executable assets inside candidate paths (complete inventory)
Only 3 of the 60 locally available candidates ship non-Markdown assets:

| Asset | Analysis | Severity |
|---|---|---|
| `api-design-principles/assets/rest-api-template.py` (wshobson) | FastAPI mock template. `CORSMiddleware allow_origins=["*"]`, `TrustedHostMiddleware allowed_hosts=["*"]`, `uvicorn.run(host="0.0.0.0")`. All flagged with `# TODO` production-hardening comments; mock endpoints only, no real auth/data. Not auto-executed. | **Low** — insecure defaults if copied verbatim to production |
| `helm-chart-scaffolding/scripts/validate-chart.sh` (wshobson) | Read-only validation: `helm lint`, `helm template`, `helm install --dry-run`, `jq empty`. No cluster mutation, no destructive commands, `set -e`, quoted paths. `helm dependency list` may touch chart-repo indexes (network). | **Info/Low** — safe |
| `k8s-manifest-generator/assets/*.yaml` (wshobson) | Deployment template enforces `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, seccomp `RuntimeDefault`, resource limits, probes; secrets via `secretRef` (no inline values). | **Positive finding** — security-hardened |

All other 57 local candidates are Markdown-only (`SKILL.md` + `references/*.md`). **No candidate auto-executes anything on load.**

### 4.2 Dependencies & supply chain
- **No `curl | sh` / `wget | sh` remote-code-execution patterns in any candidate.** (The repo's non-candidate `dependency-upgrade` command fetches remote codemods via `npx jscodeshift -t <URL>` — outside candidate set; do not adopt.)
- Unpinned tool invocations instructed by candidates (standard tooling, but version-drift/typosquat surface): `npx playwright` (e2e-testing-patterns), `npx @axe-core/cli`, `npx pa11y` (wcag-audit-patterns), `npx sequelize-cli` / `npx prisma` (database-migration), `pip install semgrep` (sast-configuration). **Low.**
- `github-actions-templates`, `changelog-automation`, `secrets-management`: actions pinned by mutable tag (`actions/checkout@v4`, `hashicorp/vault-action@v2`) rather than commit SHA. **Low** — recommend SHA pinning in generated workflows.
- `sast-configuration`: pre-commit hook repo pinned (`rev: v1.45.0` — good); `semgrep --config=auto` fetches rules from the Semgrep registry and emits usage metrics (code-structure telemetry). **Low** — disclose/allow `--metrics=off` where policy requires.
- **superpowers `using-git-worktrees`** auto-runs `npm install` / `pip install -r requirements.txt` / `poetry install` / `cargo build` / `go mod download` in Step 2. Dependency install scripts execute arbitrary code from package registries. Gated by worktree consent, but the install itself is not separately gated. **Medium.**
- **`find-skills`** instructs `npx skills add <owner/repo@skill> -g -y` — global, confirmation-skipped installation of arbitrary third-party skill content that becomes prompt-injected context in all future sessions. Trust heuristics are popularity-based (install counts/stars — gameable). **High** (H-1).

### 4.3 Filesystem / git access
- `using-git-worktrees`: creates worktrees, **auto-commits a `.gitignore` change** without separate approval; verifies `git check-ignore` first (good); sandbox-failure fallback is disclosed. **Low/Medium.**
- `finishing-a-development-branch`: merge/push/`git branch -D`/`git worktree remove` — all behind an explicit user menu; destructive discard requires the typed word `discard`; **never `--force` on own initiative**; force-push only on explicit request. **Exemplary consent design.** Low.
- `git-advanced-workflows` (wshobson): teaches `reset --hard`, `push --force-with-lease` as recovery techniques with backup-branch precautions; documentation, not autonomous action. **Low.**
- `avoid-ai-writing` edit mode: refuses source code/config/data files, minimal targeted edits, preserves quotes/frontmatter. **Low.**
- `diagnosing-superpowers`: reads session transcripts (potentially containing secrets/PII), writes case files under `~/.superpowers/`; hard rules: read-only on sessions, no bundle without request, redaction + scrub-audit loop, explicit approval before archive/GitHub issue. **Design is sound, but the scrub/discovery supporting files are missing from the snapshot — unverifiable.** Medium (integrity).

### 4.4 Network behavior
- **`gitops-workflow` (wshobson), SKILL.md:39:** `kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml` — applies a **mutable branch** manifest cluster-wide. Compromise or drift of that branch = cluster compromise. **Medium** (M-1). Pin to a release tag/digest.
- `receiving-code-review` (superpowers): `gh api .../comments/{id}/replies` — network write to GitHub, normal review workflow, user-directed. Low.
- `diagnosing-superpowers`: GitHub issue search/creation via `gh` — **approval-gated, exact text shown first**. Low.
- `deep-research` (sickn33, metadata only): "autonomous research tasks that plan, search, read" — autonomous network access; content unverified. Hold.
- `architecture-review` (sickn33, metadata only): depends on external "Ontoly Software Graph and MCP capabilities" — unknown third-party service; potential code/graph data egress. Hold/Reject.
- All other URLs in candidates are documentation links or `example.com` placeholders. **No exfiltration endpoints, no beaconing, no `/dev/tcp`, no encoded payloads found.**

### 4.5 Credentials
- **No hardcoded real credentials in any candidate** (AKIA/sk- scans clean; `sk_test_...` hits are in non-candidate payment plugins).
- CI templates correctly use `${{ secrets.* }}` references; **no `pull_request_target` secret-exposure pattern found** in candidates.
- `gitops-workflow` SKILL.md:42: `kubectl get secret argocd-initial-admin-secret ... | base64 -d` — prints the initial admin password to stdout/logs. Standard ArgoCD bootstrap step, but leaks into session transcripts/CI logs. **Low** — add rotation/log-hygiene note.
- `secrets-management` (wshobson): dev-server example `vault server -dev`, `VAULT_TOKEN='root'`, `password=secret`. Clearly labeled dev setup, but copy-paste risk into production. **Low** — add explicit "never in production" warning.
- `secrets-management` / `threat-modeling` / `auth-implementation-patterns` (sickn33): credential-adjacent topics, content unverified → LEVEL C handling if adopted.

### 4.6 Prompt injection & behavioral override
- **No malicious injection payloads found** in any locally available candidate (no "ignore previous instructions", no concealment directives, no permission-bypass instructions).
- **`using-superpowers` (superpowers):** coercive framing — *"even a 1% chance… ABSOLUTELY MUST invoke… YOU DO NOT HAVE A CHOICE… not negotiable"*, skill invocation before any response including clarifying questions. Mitigants: explicit precedence clause (user instructions > skills), `<SUBAGENT-STOP>` guard, no instruction to bypass safety/permissions. Risk is workflow distortion and reduced agent judgment, not compromise. **Medium-Low** (M-2).
- `brainstorming`: "You MUST use this before any creative work" — same class, narrower scope. Low.
- `writing-skills`: teaches pressure-testing and persuasion-resistant wording for skill authors — legitimate dual-use methodology; no attack content.
- **Positive:** `avoid-ai-writing` contains an explicit injection defense: a document telling its editor to "ignore the rules above" gets *flagged rather than followed*; instructions come only from the invoking user.
- **`find-skills`:** indirect-injection amplifier — any installed third-party skill becomes trusted context; `-y` removes the human checkpoint. See H-1.

---

## 5. Per-Candidate Verdict Table (93)

Verdicts: **ACCEPT** / **ACCEPT-CONDITIONAL** (conditions in §7) / **HOLD** (insufficient evidence) / **REJECT**.
Risk = audited risk for locally reviewed candidates; sickn33 risk = provided label (unverified metadata, marked †).

### 5.1 wshobson/agents — 45 candidates (all MIT, content reviewed)

| ID | Repo | Risk | Verdict | Rationale |
|---|---|---|---|---|
| architecture-decision-records | wshobson/agents | Low | ACCEPT | Markdown-only documentation guidance; no scripts/network/creds |
| architecture-patterns | wshobson/agents | Low | ACCEPT | Patterns doc; only `pip install pydeps` suggestion in reference |
| code-review-excellence | wshobson/agents | Low | ACCEPT | Review process doc; benign |
| debugging-strategies | wshobson/agents | Low | ACCEPT | Methodology doc; benign |
| error-handling-patterns | wshobson/agents | Low | ACCEPT | Patterns doc; benign |
| python-performance-optimization | wshobson/agents | Low | ACCEPT | Profiling guidance; benign |
| design-system-patterns | wshobson/agents | Low | ACCEPT | UI patterns doc; benign |
| responsive-design | wshobson/agents | Low | ACCEPT | CSS/layout doc; benign |
| accessibility-compliance | wshobson/agents | Low | ACCEPT | WCAG doc; benign |
| interaction-design | wshobson/agents | Low | ACCEPT | Motion/UX doc; benign |
| visual-design-foundations | wshobson/agents | Low | ACCEPT | Design doc; benign |
| web-component-design | wshobson/agents | Low | ACCEPT | Component patterns doc; benign |
| tailwind-design-system | wshobson/agents | Low | ACCEPT | Tailwind v4 doc; benign |
| wcag-audit-patterns | wshobson/agents | Low | ACCEPT | Audit doc; unpinned `npx @axe-core/cli`/`pa11y` (pin recommended) |
| screen-reader-testing | wshobson/agents | Low | ACCEPT | AT testing doc; benign |
| api-design-principles | wshobson/agents | Low | ACCEPT-CONDITIONAL | Ships FastAPI template with wildcard CORS/TrustedHost + `0.0.0.0` bind (TODO-marked); harden before production reuse |
| auth-implementation-patterns | wshobson/agents | Low | ACCEPT | Defensive auth guidance (JWT/OAuth2/RBAC); no insecure shortcuts found |
| microservices-patterns | wshobson/agents | Low | ACCEPT | Architecture doc; benign |
| openapi-spec-generation | wshobson/agents | Low | ACCEPT | Spec/doc tooling guidance; benign |
| nodejs-backend-patterns | wshobson/agents | Low | ACCEPT | Backend patterns doc; benign |
| database-migration | wshobson/agents | Low | ACCEPT | Migration doc; `npx sequelize-cli`/`prisma` are user-run dev commands; destructive ops are the user's decision |
| sql-optimization-patterns | wshobson/agents | Low | ACCEPT | Query-tuning doc; benign |
| postgresql-table-design | wshobson/agents | Low | ACCEPT | Schema design doc; benign |
| e2e-testing-patterns | wshobson/agents | Low | ACCEPT | Playwright/Cypress doc; unpinned npx (pin recommended) |
| javascript-testing-patterns | wshobson/agents | Low | ACCEPT | Jest/Vitest doc; benign |
| python-testing-patterns | wshobson/agents | Low | ACCEPT | pytest doc; benign |
| bats-testing-patterns | wshobson/agents | Low | ACCEPT | Bats doc; benign |
| attack-tree-construction | wshobson/agents | Low | ACCEPT | Defensive threat-modeling doc; no exploit content |
| sast-configuration | wshobson/agents | Low | ACCEPT-CONDITIONAL | `semgrep --config=auto` registry fetch + telemetry; pinned pre-commit rev (good); disclose telemetry, prefer `--metrics=off` per policy |
| security-requirement-extraction | wshobson/agents | Low | ACCEPT | Defensive requirements doc; benign |
| stride-analysis-patterns | wshobson/agents | Low | ACCEPT | STRIDE methodology; benign |
| threat-mitigation-mapping | wshobson/agents | Low | ACCEPT | Controls mapping doc; benign |
| secrets-management | wshobson/agents | Low | ACCEPT-CONDITIONAL | Correct `${{ secrets.* }}` patterns; dev Vault root-token example needs "never in production" warning |
| git-advanced-workflows | wshobson/agents | Low | ACCEPT | Teaches `reset --hard`/`--force-with-lease` with backup precautions; documentation only |
| github-actions-templates | wshobson/agents | Low | ACCEPT-CONDITIONAL | No `pull_request_target` misuse; tag-pinned actions → recommend SHA pinning |
| gitlab-ci-patterns | wshobson/agents | Low | ACCEPT | CI patterns doc; benign |
| deployment-pipeline-design | wshobson/agents | Low | ACCEPT | Pipeline design doc; Slack webhook via secrets ref (correct) |
| terraform-module-library | wshobson/agents | Low | ACCEPT | IaC patterns doc; no embedded credentials |
| k8s-manifest-generator | wshobson/agents | Low | ACCEPT | Templates are security-hardened (non-root, drop ALL, RO rootfs, seccomp) — positive |
| helm-chart-scaffolding | wshobson/agents | Low | ACCEPT | `validate-chart.sh` reviewed: read-only lint/template/dry-run; safe |
| gitops-workflow | wshobson/agents | **Medium** | ACCEPT-CONDITIONAL | `kubectl apply` from mutable `stable` branch URL (M-1) + admin-secret stdout decode; pin manifest to release tag, add secret-rotation note |
| changelog-automation | wshobson/agents | Low | ACCEPT | Keep-a-Changelog doc; secrets refs correct |
| hads | wshobson/agents | Low | ACCEPT | Documentation-format spec; "AI READING INSTRUCTION" blocks are format conventions, not overrides |
| grounded-vault | wshobson/agents | Low | ACCEPT | Provenance/drift pattern; append-only, never-delete rules; benign |
| avoid-ai-writing | wshobson/agents | Low | ACCEPT | Explicit prompt-injection defense; edit mode refuses code/config; benign |

### 5.2 obra/superpowers — 15 candidates (MIT per metadata; snapshot incomplete)

| ID | Repo | Risk | Verdict | Rationale |
|---|---|---|---|---|
| writing-skills | obra/superpowers | Low | ACCEPT-CONDITIONAL | Skill-authoring TDD methodology; referenced supporting files missing from snapshot — obtain before adoption |
| writing-plans | obra/superpowers | Low | ACCEPT | Plan-writing process; commit examples only; human review gate |
| verification-before-completion | obra/superpowers | Low | ACCEPT | Evidence-before-claims discipline; security-positive |
| using-superpowers | obra/superpowers | **Medium-Low** | ACCEPT-CONDITIONAL | Coercive "1% chance / NO CHOICE" invocation framing (M-2); user-instruction precedence preserved; soften wording or gate per-agent; missing platform reference files |
| using-git-worktrees | obra/superpowers | **Medium** | ACCEPT-CONDITIONAL | Auto-runs dependency installs (npm/pip/cargo/go) and auto-commits `.gitignore`; consent gate exists for worktree only; gate installs separately |
| test-driven-development | obra/superpowers | Low | ACCEPT | TDD process; runs project test commands only |
| systematic-debugging | obra/superpowers | Low | ACCEPT | Phase-gated debugging method; benign |
| subagent-driven-development | obra/superpowers | Low | ACCEPT | Orchestration process; review gates; no direct dangerous commands |
| requesting-code-review | obra/superpowers | Low | ACCEPT | Read-only git diff/SHA inspection for review dispatch |
| receiving-code-review | obra/superpowers | Low | ACCEPT | Verification-first feedback handling; `gh api` PR replies are user-directed network writes |
| finishing-a-development-branch | obra/superpowers | Low | ACCEPT | Merge/push/delete behind explicit menu; typed `discard` confirmation; never autonomous `--force` — exemplary |
| executing-plans | obra/superpowers | Low | ACCEPT | Inline plan execution with review gates; benign |
| dispatching-parallel-agents | obra/superpowers | Low | ACCEPT | Parallelization guidance for independent tasks; benign |
| diagnosing-superpowers | obra/superpowers | **Medium** | ACCEPT-CONDITIONAL | Reads sensitive session transcripts; strong approval/scrub gates in SKILL.md, but scrub/discovery/template files **absent** — cannot verify privacy logic; obtain full upstream set first |
| brainstorming | obra/superpowers | Low | ACCEPT | Design-gate process; "MUST" framing narrow; benign |

### 5.3 sickn33/antigravity-awesome-skills — 32 candidates (metadata only; † = provided label, unverified)

| ID | Repo | Risk† | Verdict | Rationale |
|---|---|---|---|---|
| architecture-decision-records (sickn33) | sickn33 | critical† | HOLD | No content provided; aggregator provenance; duplicate of audited wshobson ADR skill — prefer wshobson version |
| software-architecture (sickn33) | sickn33 | critical† | HOLD | No content; broad "any code" trigger description warrants review |
| architecture-review (sickn33) | sickn33 | unknown† | **REJECT** | AGPL-3.0-only incompatible with internal/proprietary posture; external "Ontoly Software Graph" MCP = unknown third-party data egress; content unverified |
| clean-code (sickn33) | sickn33 | safe† | HOLD | Label unverified; no content; per-skill license unconfirmed |
| tdd (sickn33) | sickn33 | safe† | HOLD | No content; overlaps audited superpowers TDD — prefer superpowers |
| systematic-debugging (sickn33) | sickn33 | critical† | HOLD | No content; likely superpowers derivative — provenance/license chain unverified; prefer superpowers original |
| code-review-excellence (sickn33) | sickn33 | safe† | HOLD | No content; overlaps audited wshobson skill — prefer wshobson |
| performance-optimization (sickn33) | sickn33 | critical† | HOLD | No content provided |
| design-system (sickn33) | sickn33 | critical† | HOLD | No content; different path (`skills/` vs plugin) suggests different upstream |
| accessibility-compliance-accessibility-audit (sickn33) | sickn33 | safe† | HOLD | No content; overlaps audited wshobson accessibility skills |
| api-design-principles (sickn33) | sickn33 | safe† | HOLD | No content; prefer audited wshobson version |
| auth-implementation-patterns (sickn33) | sickn33 | critical† | HOLD | Credential-adjacent; content unverified; LEVEL C if adopted |
| microservices-patterns (sickn33) | sickn33 | safe† | HOLD | No content; prefer audited wshobson version |
| postgres-best-practices (sickn33) | sickn33 | critical† | HOLD | Supabase-derived content claimed; upstream license/attribution unverified |
| sql-optimization-patterns (sickn33) | sickn33 | critical† | HOLD | No content; prefer audited wshobson version |
| prisma-expert (sickn33) | sickn33 | critical† | HOLD | No content; DB migration operations = sensitive |
| database-design (sickn33) | sickn33 | safe† | HOLD | No content provided |
| database-migration (sickn33) | sickn33 | critical† | HOLD | No content; destructive-operation potential; prefer audited wshobson version |
| e2e-testing-patterns (sickn33) | sickn33 | safe† | HOLD | No content; prefer audited wshobson version |
| security-audit (sickn33) | sickn33 | offensive† | **REJECT** (as-is) | Pentest/vuln-scanning workflow labeled offensive; content unverified; dual-use tooling requires authorization scoping + AG-003 LEVEL C; do not adopt without full review and rules of engagement |
| secrets-management (sickn33) | sickn33 | critical† | HOLD | Credential handling; content unverified; prefer audited wshobson version |
| docker-expert (sickn33) | sickn33 | critical† | HOLD | Container/privileged ops; content unverified |
| linux-administration (sickn33) | sickn33 | critical† | HOLD | System administration (packages/services) = privileged ops; content unverified |
| ci-cd-and-automation (sickn33) | sickn33 | critical† | HOLD | Pipeline mutation; content unverified |
| deployment-engineer (sickn33) | sickn33 | critical† | HOLD | Deployment automation; content unverified |
| git-advanced-workflows (sickn33) | sickn33 | critical† | HOLD | History-rewrite potential; prefer audited wshobson version |
| deep-research (sickn33) | sickn33 | critical† | HOLD | Apache-2.0 (compatible) but autonomous web research = uncontrolled network access; content unverified |
| documentation (sickn33) | sickn33 | safe† | HOLD | No content provided |
| api-documentation (sickn33) | sickn33 | safe† | HOLD | No content; overlaps audited wshobson openapi skill |
| threat-modeling (sickn33) | sickn33 | critical† | HOLD | No content; prefer audited wshobson STRIDE skill |
| docker-compose (sickn33) | sickn33 | critical† | HOLD | No content provided |
| kubernetes-deployment (sickn33) | sickn33 | critical† | HOLD | Cluster mutation; content unverified; prefer audited wshobson K8s skills |

### 5.4 vercel-labs/skills — 1 candidate (content reviewed)

| ID | Repo | Risk | Verdict | Rationale |
|---|---|---|---|---|
| find-skills | vercel-labs/skills | **High** | **REJECT** (as-is) / ACCEPT-CONDITIONAL after patch | Instructs `npx skills add <pkg> -g -y`: global, confirmation-skipped install of arbitrary third-party prompt content (H-1); popularity-based trust heuristics are gameable. Adopt only with `-y`/`-g` removed, explicit per-install human approval, and AG-015 review of each installed skill |

**Totals:** 93 = 45 wshobson (40 ACCEPT, 5 ACCEPT-CONDITIONAL) + 15 superpowers (11 ACCEPT, 4 ACCEPT-CONDITIONAL) + 32 sickn33 (30 HOLD, 2 REJECT) + 1 vercel-labs (1 REJECT as-is).  
**Net: 51 ACCEPT, 9 ACCEPT-CONDITIONAL, 30 HOLD, 3 REJECT (as-is).**

---

## 6. High-Risk Findings

| # | Severity | Finding | Evidence | Disposition |
|---|---|---|---|---|
| H-1 | **High** | `find-skills` silent global skill installation: `npx skills add <owner/repo@skill> -g -y` installs unvetted third-party Markdown into global skill dirs (auto-advertised in every future session); `-y` removes the confirmation checkpoint. Indirect prompt-injection / supply-chain amplifier. Trust advice relies on install counts and stars (gameable). | `/tmp/opencode/vercel-skills/skills/find-skills/SKILL.md:99-103` | Reject as-is; patch to remove `-g -y`, require per-install human approval + AG-015 audit of installed content |
| H-2 | **High** | `security-audit` (sickn33): offensive-labeled penetration-testing/vulnerability-scanning workflow; **no content available to verify** authorization scoping or safety boundaries. | `candidates.json` risk=`offensive`; description | Reject as-is; any future adoption = AG-003 LEVEL C with written rules of engagement |
| H-3 | **High** | `architecture-review` (sickn33): AGPL-3.0-only + dependency on unknown external "Ontoly Software Graph and MCP capabilities" (unverified third-party service; potential codebase data egress). | `candidates.json` license/risk fields | Reject (license + unverified external dependency) |
| H-4 | **High (process)** | 30 sickn33 candidates are metadata-only; 20 carry `critical` labels. Bulk adoption without content review would import unverified instructions into privileged domains (auth, secrets, Docker, Linux admin, CI/CD, K8s, DB migration). Labels are unverified third-party metadata. | `candidates.json`; no local sickn33 files | HOLD all; obtain content + per-skill upstream license before any decision |
| M-1 | Medium | `gitops-workflow`: `kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml` — cluster-wide apply from a **mutable branch**; also decodes ArgoCD initial admin password to stdout. | `wshobson/plugins/kubernetes-operations/skills/gitops-workflow/SKILL.md:39,42` | Condition: pin to release tag/digest; add secret rotation + log-hygiene note |
| M-2 | Medium | `using-git-worktrees` auto-executes dependency installs (`npm install`, `pip install`, `cargo build`, `go mod download`) — arbitrary registry install-scripts run without a separate gate; auto-commits `.gitignore` change. | `sp/skills/using-git-worktrees/SKILL.md:86,104-119` | Condition: separate approval for install step in factory config |
| M-3 | Medium | `diagnosing-superpowers` privacy-critical supporting files (scrub prompts, session discovery, templates) missing from snapshot; SKILL.md gates are well-designed but the actual redaction logic is unauditable. | `sp/skills/diagnosing-superpowers/SKILL.md:29-66`; glob shows only SKILL.md | Condition: obtain complete upstream skill directory and re-audit |
| M-4 | Medium-Low | `using-superpowers` coercive override framing ("1% chance… ABSOLUTELY MUST… YOU DO NOT HAVE A CHOICE") pressures invocation before any response; mitigated by explicit user-instruction precedence and subagent stop-guard. | `sp/skills/using-superpowers/SKILL.md:10-16,63-65` | Condition: soften wording on vendoring or restrict to opt-in agents |
| L-1 | Low | `rest-api-template.py`: wildcard CORS + TrustedHost `["*"]`, `0.0.0.0` bind (TODO-marked template defaults). | `api-design-principles/assets/rest-api-template.py:25,31,185` | Harden before production reuse |
| L-2 | Low | `secrets-management`: Vault dev-mode root-token example (`VAULT_TOKEN='root'`, `password=secret`). | `cicd-automation/skills/secrets-management/SKILL.md:56-68` | Add "dev only — never production" warning |
| L-3 | Low | Unpinned tooling: tag-pinned GH Actions; unpinned `npx`/`pip install` invocations; `semgrep --config=auto` telemetry. | multiple (§4.2) | Pin versions/SHAs; disclose telemetry |

**Negative results (explicitly checked, not found):** remote-fetch-and-execute one-liners, exfiltration endpoints, encoded payloads, hardcoded live credentials, `pull_request_target` secret exposure, concealment directives ("secretly", "do not tell the user"), permission-bypass or safety-override instructions, frontmatter autoinvoke/permission manipulation — in all 61 locally available candidates.

---

## 7. Recommendations and Gating (AG-003)

1. **Adopt the 49 ACCEPT candidates** (wshobson Markdown-only skills + superpowers process skills) as vendored copies under project skill dirs, retaining MIT license notices. Register with OpenCode `skill` permission **`allow`** for these; they are knowledge-only (LEVEL A).
2. **11 ACCEPT-CONDITIONAL:** apply the stated conditions before adoption (pin gitops manifest; gate dependency installs; obtain missing superpowers supporting files + LICENSE; soften `using-superpowers`; harden template defaults; SHA-pin actions; secrets warnings). Classify skills that instruct command execution (worktrees, gitops, CI/CD, migrations) as **LEVEL B** — context-dependent authorization; keep OpenCode `skill` permission `ask` for them.
3. **30 HOLD (sickn33):** AG-003 to block adoption until (a) full SKILL.md + supporting files obtained, (b) per-skill upstream license/provenance confirmed, (c) AG-015 re-audit performed. Where an audited wshobson/superpowers equivalent exists (12+ overlaps), **prefer the audited original** and drop the sickn33 duplicate.
4. **3 REJECT as-is:** `architecture-review` (AGPL + unknown MCP), `security-audit` (offensive, unverified), `find-skills` (silent global installs). Any exception is a **LEVEL C** decision requiring explicit human approval; AG-003 cannot self-approve. If `find-skills` is patched, each skill it proposes to install must itself pass AG-015 review before installation (treat installs as LEVEL C supply-chain changes).
5. **Do not bulk-install** the wshobson marketplace or sickn33 aggregator. The wshobson repo contains non-candidate hook plugins that execute `npx` packages and CLIs that rewrite `AGENTS.md` — outside this audit's approval.
6. **Credential/privileged domains** (secrets-management, auth patterns, docker/linux/k8s administration if ever adopted from sickn33): LEVEL C handling — human approval for any credential change or privileged operation they trigger.
7. **Re-audit triggers:** any upstream version change of vendored skills (skills are mutable prompt content); pin vendored copies to the audited commit (`wshobson@4220308`) and record hashes in the project decision log.
8. Record all verdicts and the license determination in `PROJECT_DECISIONS.md`; escalate H-1…H-4 to AG-001/AG-003 per AG-015 escalation rules.

---

## 8. Limitations

1. **No execution or network access** (per tasking): static review only; no dynamic testing of scripts, no verification of upstream repository activity, stars, maintainer identity, or current HEAD vs. snapshot.
2. **sickn33: zero content reviewed.** All 32 verdicts rest on `candidates.json` metadata; risk labels are unverified third-party annotations and were treated as claims, not evidence.
3. **superpowers snapshot incomplete:** only 15 SKILL.md files; no LICENSE, no `.git`, and referenced `references/`, `prompts/`, `templates/` files absent. Privacy-scrub and platform-adaptation logic is unaudited (M-3).
4. **wshobson history unavailable:** `.git/logs/HEAD` contains only the clone entry (2026-11-19, commit `4220308`); commit cadence and authorship history could not be inspected without git commands.
5. **Coverage depth:** all candidate directories were inventoried and pattern-scanned, and high-risk files read in full; not every line of every `references/*.md` was manually read. Obfuscated or semantically subtle injection could evade pattern scans.
6. `find-skills` was verified against a local copy at `/tmp/opencode/vercel-skills` found in the workspace (not in the enumerated input list); its repo-level activity metadata remains unverified.
7. License compatibility assumes internal/proprietary use (project has no LICENSE); any future external distribution requires re-evaluation, especially of the AGPL candidate.
8. OpenCode behavior assessed per the provided official-docs summary (fetched 2026-11-19); runtime permission enforcement was not tested.

---
*End of report — AG-015 Security Auditor. No systems were modified or exploited during this audit.*