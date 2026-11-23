# AUDIT_CURRENT_SKILLS

Current-state audit of the OpenCode Skills system in AI-Project-Factory.

## Audit metadata

- `audit_id`: AUDIT-0002
  - ID rationale: `AUDIT-0001` is used by the schema test fixture (`tests/contracts/test_schemas.py:142`). No other `AUDIT-NNNN` identifier was found in repository text or in `orchestration/runtime/runtime.db` (text scan). ID conforms to `schemas/audit.schema.json` pattern `^AUDIT-[0-9]{4}$`.
- `created_at`: 2026-11-19T00:00:00Z (date precision; exact clock time not available to the audit session)
- `auditor`: AG-005
- `verdict`: PASS_WITH_OBSERVATIONS
- Audit type: read-only architectural baseline audit (not a release Quality Gate).
- Template: `templates/audits/audit-template.md`; required fields per `contracts/audit-contract.md` and `schemas/audit.schema.json`.
- Re-verification: 2026-11-19, second independent AG-005 pass (read-only). All findings F-01…F-13 and the verdict re-confirmed against the live repository, config, agent catalog, model catalog, and audit schema/contract/template. Evidence precision updated (E-05 scope, E-07 commit hash); no finding or verdict changed.

## Scope

- Verify whether any OpenCode Skills system is currently deployed for this repository, across all official discovery locations (project, global, and compatibility paths).
- Verify skills-related configuration (`skills` sources array, skill permissions) in project and global OpenCode config.
- Verify whether any normative or executable agent definition references skills.
- Compare documentation claims about skills against repository reality.
- Establish the baseline for any future skills architecture work, using the official documentation summary at `/tmp/opencode/skills-work/opencode_skills_official.md` (fetched 2026-11-19 from https://opencode.ai/docs/skills/).
- Explicitly out of scope: modifying agents, runtime, configuration, or install artifacts; designing or implementing skills; release gating. This audit writes only this deliverable.

## Auditor

- AG-005 Software Architect (normative definition: `agents/analysis/ag-005-software-architect.md`, executable: `.opencode/agents/ag-005-software-architect.md`).
- Independence (audit-contract rule 1, ADR-004): no Skills implementation exists in this repository, and AG-005 has authored no skills artifact; there is no developer role to be independent from for this subject. This is an architectural baseline audit; formal independent release audits remain the responsibility of AG-013 / AG-015.
- Session constraints honored: AG-005 normative permissions deny `bash`/`execute`; no shell commands were run and no runtime state was altered.

## Artifacts

Audited artifacts (`audited_artifacts`):

Context and governance:
- `AI_START_HERE.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_HANDOFF.md`
- `PROJECT_MAP.md`
- `AGENTS.md`
- `PROJECT_DECISIONS.md`
- `contracts/audit-contract.md`
- `schemas/audit.schema.json`
- `templates/audits/audit-template.md`
- `agents/analysis/ag-005-software-architect.md`

Integration and configuration:
- `integrations/opencode/opencode-integration.md`
- `opencode.json` (project; only `opencode.json*` file at root)
- `~/.config/opencode/` directory listing (contains only `service.json`; no global `opencode.json`/`opencode.jsonc`)

Skills discovery locations (existence checks):
- `.opencode/skills` (project)
- `.claude/skills` (project compatibility)
- `.agents/skills` (project compatibility)
- `~/.config/opencode/skills` (global)
- `~/.claude/skills` (global compatibility)
- `~/.agents/skills` (global compatibility)
- `.opencode/` and `.opencode/agents/` directory listings

Reference baseline:
- `/tmp/opencode/skills-work/opencode_skills_official.md`

Repository state:
- `.git/HEAD`
- `orchestration/runtime/runtime.db` (text scan for `AUDIT-` identifiers only; not opened as a database)

## Method

1. Mandatory bootstrap per `AI_START_HERE.md` / `AGENTS.md`: read context, status, handoff, map, decisions.
2. Glob searches (hidden files included) for `**` content under each of the six skills discovery locations; all returned "No files found".
3. Direct directory reads to distinguish "absent" from "empty": each requested skills path returned "File not found"; `.claude/` and `.agents/` do not exist at project or home level; `.opencode/` contains only `agents/`; `~/.config/opencode/` contains only `service.json`.
4. Config inspection: `opencode.json` read in full; no `skills` key, no `permissions` key. No project `opencode.jsonc`; no global OpenCode config file.
5. Case-insensitive repository-wide grep for `skill`: exactly one match outside this deliverable (`PROJECT_MAP.md:19`); all remaining matches are self-references inside this audit file. Re-verified by full unrestricted scan and per-directory greps (`.opencode/`, `agents/`, `contracts/`, `orchestration/`, `standards/`, `integrations/`, `tests/`, root docs): zero other matches. No agent definition, contract, schema, workflow, standard, or test references skills.
6. Git state: shell unavailable to AG-005 (`bash: deny`), so `git status`/`git log` could not be executed; current branch read directly from `.git/HEAD`. Discrepancy vs context docs recorded as finding F-08.
7. No tests were executed: this is a read-only documentation/state audit with zero code changes; evidence is file- and search-based per audit-contract rule 5.

## Findings

### Confirmed current state

- F-01: No project skills directory. `.opencode/skills` does not exist. `.opencode/` contains only `agents/` (18 executable agent files, `ag-001` … `ag-018`). No `command/` or `commands/` directory exists either.
- F-02: No project compatibility skills directories. `.claude/skills` and `.agents/skills` do not exist; the parent directories `.claude/` and `.agents/` are themselves absent from the repository root.
- F-03: No global skills directories. `~/.config/opencode/skills` does not exist (`~/.config/opencode/` holds only `service.json`). Global compatibility paths `~/.claude/skills` and `~/.agents/skills` are absent (no `.claude/` or `.agents/` under `/home/developer`).
- F-04: No skills configuration. Project `opencode.json` contains only `$schema`, `model`, `default_agent`, `instructions`. There is no `skills` sources array (local dirs or HTTP catalogs) and no `skill` permission rules, globally or per agent. No global OpenCode config file exists to contribute additional sources.
- F-05: No skills references in agents or runtime artifacts. Repository-wide case-insensitive grep for `skill` returns exactly one match outside this deliverable: `PROJECT_MAP.md:19` (all other matches are self-references in this audit file). Neither normative `agents/` nor executable `.opencode/agents/` definitions mention skills, skill tools, or skill permissions.
- F-06: The repository contributes zero skills to OpenCode. Skills advertised in the current session (`opencode`, `report`) are runtime built-ins from the OpenCode installation (registration order 1 per official docs), not repository artifacts. Conclusion: **no Skills system exists in AI-Project-Factory today**; the baseline is greenfield.

### Discrepancies (documentation vs reality)

- F-07 (D-01): `PROJECT_MAP.md:19` states `.opencode/` holds "OpenCode executable agents, commands, skills". Reality: only `agents/` exists. Per `AI_START_HERE.md` ("Do not assume documentation is correct when it conflicts with code; investigate and record the discrepancy"), this is recorded, not silently corrected. Owner for correction: AG-018 / AG-001 (see R-01).
- F-08 (D-02): `PROJECT_STATUS.md` and `PROJECT_HANDOFF.md` reference branch `feature/r5.2a-implementation` @ `6b28655` as last validated state, but `.git/HEAD` points to `refs/heads/feature/model-fallback-manager` (tip commit `f676d71`). Context documents are stale relative to the checked-out branch. Recorded for reconciliation; outside this audit's remediation authority.

### Observations

- F-09: `integrations/opencode/opencode-integration.md` does not list skills among "Verified capabilities" and states "Experimental features are not used". This is consistent with the absent skills system. Any future adoption must update this document and comply with ADR-003 (use real installed OpenCode syntax verified against official docs).
- F-10: No approved requirement mandates a Skills system (no requirements artifact references skills). The absence is therefore not a requirements violation. If skills are desired, this is a requirement gap to escalate to AG-004 per AG-005 escalation rules.
- F-11: `~/.config/opencode/service.json` contains a local service password. It lives outside the repository, so the "no real credentials in repository" policy (`PROJECT_CONTEXT.md`, `standards/security/`) is not violated. The value is deliberately not reproduced in this audit. Awareness item for AG-003 only if that file is ever copied into VCS or install artifacts.
- F-12: `PROJECT_DECISIONS.md` contains two distinct entries both numbered ADR-005 (SQLite decision and TEST-006 security event), and ADR-004 appears out of sequence without its own header. Out of scope for this audit, but relevant to traceability: the next free ADR ID for skills work is ADR-007 or later, and the log needs reconciliation by its owner.
- F-13: Audit ID reservation could not be verified against SQLite records with SQL (no execute permission); a text scan of `orchestration/runtime/runtime.db` found no `AUDIT-` strings. Residual risk of ID collision with database-stored audits is low and noted for the runtime owner.

## Current-state inventory

| Discovery location (official docs) | Kind | Exists | Content |
|---|---|---|---|
| `.opencode/skills` | project | No | `.opencode/` contains only `agents/` (18 files) |
| `.claude/skills` | project compat | No | `.claude/` absent |
| `.agents/skills` | project compat | No | `.agents/` absent |
| `~/.config/opencode/skills` | global | No | dir contains only `service.json` |
| `~/.claude/skills` | global compat | No | `~/.claude/` absent |
| `~/.agents/skills` | global compat | No | `~/.agents/` absent |
| `skills` config array | config | No | absent from `opencode.json`; no global config |
| `skill` permission rules | config | No | none global or per agent |
| Skill references in agents | code/docs | No | single repo match outside this deliverable is `PROJECT_MAP.md:19` (doc claim only) |

## Gap analysis vs official Skills documentation

Baseline reference: `/tmp/opencode/skills-work/opencode_skills_official.md`. Nothing below is implemented today; this is the checklist a future skills architecture must satisfy:

1. Skill form and layout: flat `skills/<id>.md` or `skills/<id>/SKILL.md`; one skill per SKILL.md directory; supporting paths relative to the SKILL.md directory.
2. Frontmatter: `description` is mandatory in practice (skills without description are not advertised); `name` is display-only; IDs are path-derived, case-sensitive, recommended lowercase kebab-case 1–64 chars.
3. Invocation control: `metadata.opencode/autoinvoke: false` / `disable-model-invocation: true` for skills that must not be model-invoked; manual load via `@skill-id`.
4. Permissions: `skill` action with skill ID as resource; allow/ask/deny; ordered rules, last match wins; global or per agent. Must be reconciled with the factory's fail-closed permission model (R5.2A) before any adoption.
5. Precedence: built-in → global compat → global config dir → project `.opencode/skills` → explicit config entries; later sources override duplicate IDs. A project-local-only strategy avoids accidental global overrides.
6. Sources config: `skills` array in `opencode.json`; relative paths resolve from working directory, not config file. HTTP catalogs introduce a remote supply-chain surface and should require explicit human approval (ADR-002 supervised autonomy).

## Verdict

**PASS_WITH_OBSERVATIONS**

Rationale:
- The audit objective — verify the current Skills system state — is fully satisfied: all six official discovery locations, project/global config, and all agent definitions were checked with reproducible searches. Confirmed result: no skills directories, no skills configuration, no skills references; the repository contributes zero skills.
- No approved requirement is violated by the absence (F-10), and nothing is broken or blocking; FAIL/BLOCKED do not apply. This is a baseline audit, not a release gate.
- Observations are documented per audit-contract rule 4: two documentation discrepancies (F-07 PROJECT_MAP skills/commands claim; F-08 stale branch references), plus governance/traceability observations (F-09, F-11, F-12, F-13).

## Evidence

- E-01 (F-01, F-02): glob `.opencode/skills/**`, `.claude/skills/**`, `.agents/skills/**` (hidden included) → "No files found". Directory reads: `.opencode/skills` → "File not found"; `.claude/skills` → "The folder /home/developer/AI-Project-Factory/.claude does not exist"; `.agents/skills` → "The folder /home/developer/AI-Project-Factory/.agents does not exist".
- E-02 (F-01): read of `.opencode/` → single entry `agents/`; read of `.opencode/agents/` → 18 files `ag-001-project-coordinator.md` … `ag-018-documentation-engineer.md`.
- E-03 (F-03): glob `.config/opencode/skills/**`, `.claude/skills/**`, `.agents/skills/**` under `/home/developer` → "No files found"; read `~/.config/opencode/skills` → "File not found"; read `~/.config/opencode/` → single entry `service.json`.
- E-04 (F-04): `opencode.json` lines 1–8 contain only `$schema`, `model` (`opencode-go/qwen3.8-flash`), `default_agent` (`build`), `instructions` (`["AGENTS.md"]`). Glob `opencode.json*` at root → only `opencode.json`. `~/.config/opencode/` listing shows no global config file.
- E-05 (F-05, F-07): grep `skill` (case-insensitive, whole repository, all file types) → 1 match outside this deliverable: `PROJECT_MAP.md:19` "- `.opencode/`: OpenCode executable agents, commands, skills."; every other match is a self-reference inside this audit file. Re-verified 2026-11-19 (pass 2) by unrestricted full scan plus per-directory greps over `.opencode/`, `agents/`, `contracts/`, `orchestration/`, `standards/`, `integrations/`, `tests/`, `README.md`, `CHANGELOG.md`, `SESSION_LOG.md`, `PROJECT_PROGRESS.md`: zero matches.
- E-06 (F-06): official docs summary, "Precedence" section (built-in registered first) and "Loading" section; session available-skills list contains only runtime built-ins `opencode` and `report`; no repository skill source exists per E-01–E-04.
- E-07 (F-08): `.git/HEAD` → `ref: refs/heads/feature/model-fallback-manager`; `.git/refs/heads/feature/model-fallback-manager` → `f676d7116dcbf252dd5da0bb19c42e0b657a6e14` (pass 2); `PROJECT_STATUS.md:15` and `PROJECT_HANDOFF.md:52-54` → `6b28655 (feature/r5.2a-implementation)`.
- E-08 (F-09): `integrations/opencode/opencode-integration.md` lines 7–23 ("Verified capabilities", "Limitations": no skills entry; "Experimental features are not used").
- E-09 (F-10): grep result E-05 shows no requirements, contract, or workflow artifact mentions skills; `agents/analysis/ag-005-software-architect.md` "Escalation rules" (requirement gaps → AG-004).
- E-10 (F-11): read of `~/.config/opencode/service.json` (1 key: `password`; value withheld from this document); file located outside the Git working tree.
- E-11 (F-12): `PROJECT_DECISIONS.md` lines 39–49 (ADR-005 SQLite) and lines 61–71 (ADR-005 TEST-006); lines 51–59 (ADR-004 without header); lines 73–83 (ADR-006).
- E-12 (F-13, audit_id): grep `AUDIT-[0-9]{4}` repository-wide → only `tests/contracts/test_schemas.py:142` (`AUDIT-0001`); grep `AUDIT-` in `orchestration/runtime/runtime.db` → no matches (text scan; binary SQL inspection not possible without execute permission).
- E-13 (method constraint): `agents/analysis/ag-005-software-architect.md` "Permissions" (`bash: deny`, `execute: deny`); no execute tool available in session; therefore `git status`/`git log` per `AI_START_HERE.md` were substituted by direct `.git/HEAD` read, and no tests were run (zero code changes).

## Recommendations and escalation

No remediation was performed (read-only mandate; agents/runtime/config/install untouched).

- R-01 (from F-07): correct `PROJECT_MAP.md:19` to reflect reality (`.opencode/` currently holds only executable agents), or create the claimed directories as part of an approved skills initiative. Owner: AG-018 Documentation Engineer, coordinated by AG-001.
- R-02 (from F-08): reconcile `PROJECT_STATUS.md` / `PROJECT_HANDOFF.md` with the actual checked-out branch `feature/model-fallback-manager` before the next stage closure. Owner: AG-001 / AG-018.
- R-03 (from F-10): if a Skills system is desired, escalate the requirement gap to AG-004 (no approved skills requirements exist). Only after approved requirements should AG-005 produce a skills architecture and a new ADR (next free ID ≥ ADR-007, per F-12), satisfying ADR-003 (verified installed syntax) and updating `integrations/opencode/opencode-integration.md`.
- R-04 (from F-04, gap analysis): any future adoption must define `skill` permission rules consistent with the R5.2A fail-closed model, prefer project-local `.opencode/skills` (avoid global/compat override surprises), require descriptions and kebab-case IDs, and treat HTTP skill catalogs as a supply-chain risk requiring explicit human approval (ADR-002). Security review owner: AG-003.
- R-05 (from F-12): reconcile duplicate ADR-005 numbering in `PROJECT_DECISIONS.md` (documentation owner; new decision entry required per `AI_START_HERE.md` rules).
- Escalations per AG-005 rules: requirement gaps → AG-004 (R-03); security concerns → AG-003 (R-04, F-11 awareness).

## Traceability

- Required fields of `contracts/audit-contract.md` and `schemas/audit.schema.json` are all present: `audit_id`, `scope`, `auditor`, `audited_artifacts` (Artifacts section), `findings`, `verdict`, `evidence`, `created_at` (metadata block).
- Section structure follows `templates/audits/audit-template.md` (Scope, Auditor, Artifacts, Findings, Verdict, Evidence), extended with metadata, method, inventory, gap analysis, recommendations, and traceability.
- Audit rules honored: independence documented (rule 1, ADR-004); results not modifiable by audited agents (rule 2 — no audited implementation exists); observations documented (rule 4); every finding maps to file/search evidence (rule 5, E-01…E-13).
- Decisions referenced: ADR-001 (repository is source of truth — this audit is persisted in `docs/skills/`), ADR-002 (supervised autonomy — HTTP catalogs need approval), ADR-003 (verified OpenCode syntax — future skills design constraint), ADR-004 (independent audit).
- Context protocol: `AI_START_HERE.md` → `PROJECT_CONTEXT.md` → `PROJECT_STATUS.md` → `PROJECT_HANDOFF.md` → `PROJECT_MAP.md` → `PROJECT_DECISIONS.md` consulted before auditing.

## Limitations

- No shell/execute permission: Git commands and SQLite queries could not be run; branch verified via `.git/HEAD`, audit-ID collision check limited to text scan (F-13).
- The official Skills reference is a fetched summary (`/tmp/opencode/skills-work/opencode_skills_official.md`, 2026-11-19), not a live re-fetch; behavior must be re-verified against the installed OpenCode version at design time (ADR-003).
- `created_at` carries date precision only; the audit session has no clock access.
- Compliance statement: no files under `agents/`, `.opencode/`, `orchestration/` (runtime), `opencode.json` (config), or `install/` were modified. The only file written by this audit is `docs/skills/AUDIT_CURRENT_SKILLS.md`.
