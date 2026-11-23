# Skills Registry Schema

- **doc_id**: SKILLS-REGISTRY-SCHEMA-0001
- **created_at**: 2026-11-19
- **author**: AG-005 Software Architect
- **status**: NORMATIVE CANDIDATE — schema specification for ratification by ADR ≥ ADR-007. **No `registry.json`, schema file, or validator exists today.** This document defines the format; it implements nothing and claims no validation PASS.
- **parent architecture**: `docs/skills/SKILLS_GOVERNANCE.md` (SKILLS-GOVERNANCE-0001)
- **design input**: `docs/skills/SKILLS_REGISTRY_PROPOSAL.md` §3 (AG-018) — field groups and obligations are preserved; refinements are flagged in §2.3.
- **normative references**: `docs/skills/SKILLS_COVERAGE_MATRIX.md` §4 (V-1…V-8), §5 (A-1…A-11), §6 (G0–G8) · `docs/skills/SKILLS_SECURITY_AUDIT.md` (verdicts, risk classes) · `docs/skills/SKILLS_COMPATIBILITY_MATRIX.md` (compat verdicts) · official OpenCode V2 mechanics summary fetched 2026-11-19 (frontmatter fields OpenCode actually interprets).

---

## 1. Scope and enforcement boundary

The registry is the factory's **single source of truth** for skill governance (architecture D-2/D-4). OpenCode itself has no registry concept and interprets **none** of Plane B. Enforcement is therefore split:

| Plane | Artifact | Interpreted by | Enforced by |
|---|---|---|---|
| **A** | `SKILL.md` YAML frontmatter | OpenCode V2 runtime (only the fields in §6) | OpenCode itself |
| **B** | `skills-library/registry.json` | nothing external — governance documentation | in-house lint + CI (V-1/V-2 extensions, V-3, I-1…I-4), gates G0–G8 |

**Never mistake Plane B for runtime enforcement.** A registry row saying `deny` does not deny anything until the permission generator writes the derived `opencode.json` rule and G6 verifies the live effect (OQ-4).

## 2. File location and envelope

### 2.1 Location

- Registry: `skills-library/registry.json` (canonical layer; **not** a discovery location).
- JSON Schema (proposed artifact): `skills-library/registry.schema.json`, draft `2020-12` (§7).
- Enablement copies: `.opencode/skills/<skill-id>/SKILL.md` only (architecture L-1/L-2).

### 2.2 Envelope

```json
{
  "schema_version": "1.0",
  "registry_version": "0.1.0",
  "updated_at": "2026-11-19",
  "skills": [ { "…entry per §3…" } ]
}
```

| Field | Type | Req | Constraints |
|---|---|---|---|
| `schema_version` | string | MUST | const `"1.0"` for this specification; evolution per §10 |
| `registry_version` | string | SHOULD | SemVer of the registry content as a whole (distinct from per-row `versioning.registry_version`) |
| `updated_at` | string | SHOULD | ISO-8601 date of last row change; maintained by the tooling, never hand-waved |
| `skills` | array | MUST | one entry per skill, ever; **rows are never deleted** — retirement is a lifecycle state (T-1/T-3). `skill_id` unique across the array (case-sensitive) |

### 2.3 Refinements relative to the registry proposal (flagged, not silent)

- **RF-1**: `schema_version` moves from per-entry (proposal §3.1 example) to the **envelope**. Rationale: one format version per file prevents per-row schema drift and simplifies lint. Entry fields are otherwise identical to the proposal.
- **RF-2**: `history` entries gain optional `actor` and `evidence` fields (additive) so gate evidence is machine-traceable (A-1…A-11 / G7).
- **RF-3**: cross-field consistency rules (§5, X-1…X-12) are formalized here; the proposal stated them as prose obligations.
- All three require ADR ratification; until then the proposal remains the design input of record.

## 3. Entry field reference

Required unless marked MAY. Placeholder rule: undated/unverified fields carry explicit `"TBD"` or `PENDING` — **never a fabricated PASS** (A-1…A-11 evidence rule).

### 3.1 Identity

| Field | Type | Constraints |
|---|---|---|
| `skill_id` | string | MUST equal the path-derived ID exactly (case-sensitive). Pattern `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars. V2 does **not** enforce this pattern — V-2/V-3 lint MUST (AG-012 §4) |
| `tier` | enum | `global` \| `shared` \| `specialty` \| `project` (L-5). `in-house` is a provenance partition, **not** a tier (L-6) |
| `category` | enum (provisional) | one of the 14 categories (§4.1); frozen only after OQ-1 ratification (ES-1) |
| `library_path` | string | repo-relative path to the skill directory under `skills-library/`; basename MUST equal `skill_id` (X-1) |
| `enabled_in` | array of strings | repo-relative paths of promotion copies; each MUST be `.opencode/skills/<skill_id>` (X-9); empty unless STAGED/ACTIVE/SUSPENDED (X-2) |

### 3.2 Source (provenance)

| Field | Type | Constraints |
|---|---|---|
| `source.type` | enum | `vendored-upstream` \| `adapted` \| `in-house` \| `http-catalog` |
| `source.repo` | string | MUST for non-in-house (e.g. `wshobson/agents`); null/absent for in-house |
| `source.canonical_url` | string (URL) | MUST for non-in-house; canonical identity re-verified on re-collection (OBS-2 rename hazard) |
| `source.upstream_path` | string | MUST for non-in-house; path within the upstream repo |
| `source.commit_sha` | string | MUST for non-in-house; **pinned audited commit** (D-5); short or full SHA, recorded verbatim |
| `source.cloned` | date \| `"TBD"` | clone/acquisition date |
| `source.approval` | object | MUST when `type: http-catalog`: `{ "approved_by": <human>, "adr": <ADR-id>, "date": <date> }` — I-4 / ADR-002 evidence; catalogs are otherwise forbidden (D-7) |

### 3.3 License

| Field | Type | Constraints |
|---|---|---|
| `license.scope` | enum | `per-file-verified` \| `repo-level-claim` \| `unverified` \| `in-house`. Only `per-file-verified` (or ratified `in-house` policy, ES-8) can pass G3; repo-level strings of aggregators are **claims, not evidence** (F-3) |
| `license.spdx` | string | SPDX expression (e.g. `MIT`, `Apache-2.0`); `"UNVERIFIED"` when scope is unverified. Any `AGPL-*` ⇒ lifecycle MUST NEVER be STAGED/ACTIVE (X-3; rejected for internal posture) |
| `license.notice_files` | array of strings | LICENSE/NOTICE files present in the vendored copy; Apache-2.0 ⇒ NOTICE MUST be listed (K-4) |
| `license.verified_by` | string | gate/actor that verified (e.g. `G3`); independent of the consumer (ADR-004) |
| `license.verified_at` | date \| `"TBD"` | no fabricated dates |

### 3.4 Integrity

| Field | Type | Constraints |
|---|---|---|
| `integrity.file_hashes` | object | map relative path → `sha256:<64 lowercase hex>`; MUST include `SKILL.md`; MUST cover **every** supporting file when references exist (X-6); the drift probe diffs these against the pinned commit |
| `integrity.complete_directory` | boolean | MUST be `true` whenever the skill references supporting files (obra SKILL.md-only lesson, K-10); `false` blocks G3/G5 |
| `integrity.local_modifications` | string | `none` \| `wording-model-neutral` \| `namespace-rewrite` \| `hardening(<description>)`; any non-`none` value ⇒ C2 re-run + compat re-grade; `adapted` source type requires non-`none` here (X-7) |

### 3.5 Verdicts (row-level cross-references, never summary-level — OBS-1)

| Field | Type | Constraints |
|---|---|---|
| `verdicts.compatibility.verdict` | enum (provisional, ES-5) | `COMPATIBLE` \| `COMPATIBLE-AFTER-ADAPTATION` \| `INCOMPATIBLE` \| `PENDING` — vocabulary to be frozen by AG-011 |
| `verdicts.compatibility.doc` / `.row` | string | `SKILLS_COMPATIBILITY_MATRIX.md` + row key; MUST resolve to an existing row |
| `verdicts.security.verdict` | enum | `ACCEPT` \| `ACCEPT-CONDITIONAL` \| `HOLD` \| `REJECT` \| `PENDING` (AG-015 vocabulary) |
| `verdicts.security.risk_class` | enum | `A` \| `B` \| `C` (AG-015/AG-012 A-9) |
| `verdicts.security.doc` | string | `SKILLS_SECURITY_AUDIT.md` row cross-ref |
| `verdicts.security.conditions_closed` | array | for ACCEPT-CONDITIONAL: each stated condition closed **and re-attested**, item-by-item (G4); open conditions block APPROVED (X-4) |
| `verdicts.behavior_review.verdict` | enum | `PASS` \| `FAIL` \| `PENDING` — G5 (behavior-injection vs agent contracts, model-neutral wording) |
| `verdicts.behavior_review.gate` | string | const `G5` |

Upstream/third-party `risk` labels (e.g. sickn33 critical/safe/unknown/offensive) are **never** acceptable values or substitutes here (K-9, coverage matrix rec. 3).

### 3.6 Permissions

| Field | Type | Constraints |
|---|---|---|
| `permissions.risk_class` | enum | `A` \| `B` \| `C`; MUST equal `verdicts.security.risk_class` (X-8) |
| `permissions.rule` | enum | `allow` \| `ask` \| `deny`. Default mapping A→allow, B→ask, C→deny (P-1…P-3). STAGED ⇒ `ask` (X-2); SUSPENDED ⇒ `deny` (X-2); deviation from class default requires human-approved history evidence (loosening only; tightening always allowed) |
| `permissions.per_agent_overrides` | object | map agent ID → rule; may tighten freely; may never relax a SUSPENDED deny or a class-C default without human approval (P-2) |
| `permissions.autoinvoke` | boolean | MUST equal Plane A frontmatter effective autoinvoke (X-10); process-class skills MUST be `false` (P-3) |

### 3.7 Assignment

| Field | Type | Constraints |
|---|---|---|
| `assignment.agents` | array of strings | ≥ 1 consumer (orphan rule). `scope: factory-agents` ⇒ IDs from the verified 18-agent catalog, pattern `^AG-[0-9]{3}$` (X-11); `scope: generated-project` ⇒ the project's agent-set identifiers, never factory agents (P-4) |
| `assignment.scope` | enum | `factory-agents` \| `generated-project` |

### 3.8 Versioning

| Field | Type | Constraints |
|---|---|---|
| `versioning.upstream_pin` | string \| null | `<repo>@<sha>` (e.g. `wshobson@4220308`); null iff `source.type: in-house` (X-7) |
| `versioning.local_rev` | integer ≥ 0 | increments on every local modification (C2) |
| `versioning.registry_version` | string | SemVer + build metadata tying row to pin, e.g. `0.1.0+pin.4220308` |
| `versioning.history` | array, append-only | ≥ 1 entry; never rewritten or deleted (T-1). Entry: `{ event, date, gates?, adr?, actor?, evidence? }` (RF-2). `event` enum: `registered` \| `adopted-via-ADR` \| `promoted` \| `staged` \| `activated` \| `suspended` \| `retired` \| `re-pinned` \| `adapted` \| `permission-change` \| `verdict-change` \| `re-audited`. `date` ISO-8601 or `"TBD"` pre-gate. G6-related entries SHOULD record OpenCode build + model/provider (MM-4) in `evidence` |

### 3.9 Lifecycle and re-audit

| Field | Type | Constraints |
|---|---|---|
| `lifecycle` | enum | `CANDIDATE` \| `REVIEWED` \| `APPROVED` \| `STAGED` \| `ACTIVE` \| `SUSPENDED` \| `RETIRED` (architecture §4; guards X-2…X-5) |
| `reaudit_triggers` | array, unique | ≥ 1 of: `upstream-drift` \| `opencode-version-bump` \| `permission-change` \| `content-edit` \| `security-reclassification` \| `config-drift` (V-8 / C1–C6) |
| `notes` | string | MAY; free text; never a substitute for verdict evidence |

## 4. Controlled vocabularies

### 4.1 Categories (provisional — frozen only at OQ-1 ratification, ES-1)

`agent-process`, `architecture-design`, `backend-api`, `code-quality-review`, `database-data`, `debugging-performance`, `devops-delivery`, `docs-knowledge`, `git-vcs`, `quality-gate`, `requirements-engineering`, `security-compliance`, `testing`, `ui-ux-accessibility` (14; the 12 specialty partitions + the two in-house M-1/M-2 categories).

### 4.2 Lifecycle × enablement × permission matrix (guard summary)

| lifecycle | `enabled_in` | effective rule |
|---|---|---|
| CANDIDATE / REVIEWED / APPROVED / RETIRED | `[]` | n/a (default deny) |
| STAGED | non-empty, pilot copies only | `ask` for all assigned agents |
| ACTIVE | non-empty | class mapping A→allow / B→ask / C→deny unless human-approved deviation |
| SUSPENDED | MAY be non-empty (kill-switch is permission-based) | `deny` everywhere; no override may relax |

## 5. Cross-field consistency rules (in-house lint; JSON Schema alone cannot express all)

| ID | Rule | Gate/check |
|---|---|---|
| X-1 | `skill_id` == basename(`library_path`) == basename of every `enabled_in` path; ID unique across registry **and** all enabled discovery sources + `skills` config array | V-3 / G2 |
| X-2 | lifecycle guards per §4.2 (enablement presence, STAGED ask, SUSPENDED deny) | registry lint / G7 |
| X-3 | `license.spdx` matching `AGPL-*` ⇒ lifecycle ∉ {STAGED, ACTIVE}; scope `unverified`/`repo-level-claim` ⇒ lifecycle ∉ {APPROVED, STAGED, ACTIVE} | V-7 / G3 |
| X-4 | APPROVED or beyond ⇒ compat verdict ∈ {COMPATIBLE, COMPATIBLE-AFTER-ADAPTATION}, security ∈ {ACCEPT, ACCEPT-CONDITIONAL with all conditions closed}, behavior_review PASS; HOLD/REJECT ⇒ lifecycle ∈ {CANDIDATE, REVIEWED, SUSPENDED, RETIRED} | G3–G5 / lint |
| X-5 | verdict `doc`+`row` cross-references resolve to existing rows in the named audit documents (row-level, not summary — OBS-1) | lint / G2 |
| X-6 | skill references supporting files ⇒ `complete_directory: true` and `file_hashes` covers every referenced file; every referenced relative path exists on disk | V-1/V-7 / G3 |
| X-7 | `source.type: in-house` ⇒ no repo/upstream_path/commit_sha, `upstream_pin: null`; non-in-house ⇒ all pin fields present; `adapted` ⇒ `local_modifications != none` and `local_rev ≥ 1` | V-7 / G3 |
| X-8 | `permissions.risk_class` == `verdicts.security.risk_class`; rule matches class default or carries human-approved loosening evidence in history | lint / G4 |
| X-9 | every `enabled_in` path is exactly `.opencode/skills/<skill_id>` (project layer only); global/compat locations empty of factory content | V-3 / I-1, I-2 |
| X-10 | Plane A effective autoinvoke == `permissions.autoinvoke`; Plane A contains **only** OpenCode-interpreted fields (§6) | V-2 / lint |
| X-11 | `assignment.agents` ⊆ 18-agent catalog when scope factory-agents; generated-project scope never lists factory agents; ≥ 1 consumer for STAGED/ACTIVE | lint / G7 |
| X-12 | `opencode.json` skill rules byte-equal the generator output from this registry (regenerate-and-diff); history append-only across git revisions | I-3 / C5, G8 |

## 6. Plane A — SKILL.md frontmatter schema (the only OpenCode-interpreted fields)

```yaml
---
name: Architecture Decision Records      # MAY — display only
description: >                           # MUST — non-empty; missing ⇒ never advertised
  Write and maintain ADRs following the factory decision workflow.
metadata:
  opencode:
    autoinvoke: false                    # MUST be explicit for process-class skills (P-3)
    # disable-model-invocation: false    # MAY — boolean; autoinvoke WINS if both present
---
```

| Field | OpenCode V2 behavior | Factory rule |
|---|---|---|
| `name` | display only | MAY; MUST NOT be relied on for identity (ID is path-derived) |
| `description` | required in practice for advertisement; only ID/name/description are advertised | MUST, non-empty; model-neutral triggering wording (MM-3) |
| `metadata.opencode.autoinvoke` | controls model-driven loading; `false` ⇒ hidden from model list, still loadable by exact ID and `@skill-id` | MUST be explicit; MUST match Plane B (X-10) |
| `metadata.opencode.disable-model-invocation` | alternative control; autoinvoke wins if both | avoid mixing; lint flags both-present |
| `license`, `compatibility` (top-level portability fields) | **accepted but NOT interpreted** | MUST NOT be used for gating; governance lives in Plane B (D-3). Policy: omit from Plane A to avoid false confidence |
| any other governance field | not interpreted | forbidden in Plane A (R-3); V-2 lint rejects |

ID derivation (V2 mechanics): `<id>.md` at a source root → `<id>`; `<id>/SKILL.md` → `<id>`; case-sensitive; a SKILL.md directory is exactly one skill (no inner search); recommended kebab-case ≤ 64 is **not enforced by V2** ⇒ V-2/V-3 lint enforces `^[a-z0-9]+(-[a-z0-9]+)*$`, maxLength 64. Body is injected without frontmatter; supporting files (≤ 10 sample paths surfaced) are never auto-loaded.

## 7. JSON Schema draft (2020-12) — proposed artifact `skills-library/registry.schema.json`

Draft for ratification; cross-field rules X-1…X-12 are implemented by the lint suite, not by this schema alone.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ai-project-factory.local/schemas/skills-registry-1.0.json",
  "title": "AI-Project-Factory Skills Registry",
  "type": "object",
  "required": ["schema_version", "skills"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "const": "1.0" },
    "registry_version": { "type": "string" },
    "updated_at": { "$ref": "#/$defs/dateOrTBD" },
    "skills": {
      "type": "array",
      "items": { "$ref": "#/$defs/entry" }
    }
  },
  "$defs": {
    "skillId": { "type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$", "minLength": 1, "maxLength": 64 },
    "sha256": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
    "agentId": { "type": "string", "pattern": "^AG-[0-9]{3}$" },
    "dateOrTBD": { "anyOf": [ { "type": "string", "format": "date" }, { "const": "TBD" } ] },
    "rule": { "enum": ["allow", "ask", "deny"] },
    "riskClass": { "enum": ["A", "B", "C"] },
    "entry": {
      "type": "object",
      "required": ["skill_id", "tier", "category", "library_path", "enabled_in",
                   "source", "license", "integrity", "verdicts", "permissions",
                   "assignment", "versioning", "lifecycle", "reaudit_triggers"],
      "additionalProperties": false,
      "properties": {
        "skill_id": { "$ref": "#/$defs/skillId" },
        "tier": { "enum": ["global", "shared", "specialty", "project"] },
        "category": {
          "enum": ["agent-process", "architecture-design", "backend-api", "code-quality-review",
                   "database-data", "debugging-performance", "devops-delivery", "docs-knowledge",
                   "git-vcs", "quality-gate", "requirements-engineering", "security-compliance",
                   "testing", "ui-ux-accessibility"],
          "$comment": "Provisional until OQ-1 ratification (ES-1)"
        },
        "library_path": { "type": "string", "pattern": "^skills-library/" },
        "enabled_in": {
          "type": "array", "uniqueItems": true,
          "items": { "type": "string", "pattern": "^\\.opencode/skills/[a-z0-9]+(-[a-z0-9]+)*$" }
        },
        "source": {
          "type": "object",
          "required": ["type"],
          "additionalProperties": false,
          "properties": {
            "type": { "enum": ["vendored-upstream", "adapted", "in-house", "http-catalog"] },
            "repo": { "type": ["string", "null"] },
            "canonical_url": { "type": ["string", "null"] },
            "upstream_path": { "type": ["string", "null"] },
            "commit_sha": { "type": ["string", "null"] },
            "cloned": { "$ref": "#/$defs/dateOrTBD" },
            "approval": {
              "type": "object",
              "required": ["approved_by", "adr", "date"],
              "properties": {
                "approved_by": { "type": "string" },
                "adr": { "type": "string" },
                "date": { "$ref": "#/$defs/dateOrTBD" }
              }
            }
          },
          "allOf": [
            {
              "if": { "properties": { "type": { "enum": ["vendored-upstream", "adapted", "http-catalog"] } } },
              "then": { "required": ["repo", "canonical_url", "upstream_path", "commit_sha"] }
            },
            {
              "if": { "properties": { "type": { "const": "http-catalog" } } },
              "then": { "required": ["approval"] }
            }
          ]
        },
        "license": {
          "type": "object",
          "required": ["scope", "spdx", "notice_files", "verified_by", "verified_at"],
          "additionalProperties": false,
          "properties": {
            "scope": { "enum": ["per-file-verified", "repo-level-claim", "unverified", "in-house"] },
            "spdx": { "type": "string" },
            "notice_files": { "type": "array", "items": { "type": "string" } },
            "verified_by": { "type": "string" },
            "verified_at": { "$ref": "#/$defs/dateOrTBD" }
          }
        },
        "integrity": {
          "type": "object",
          "required": ["file_hashes", "complete_directory", "local_modifications"],
          "additionalProperties": false,
          "properties": {
            "file_hashes": {
              "type": "object", "minProperties": 1, "required": ["SKILL.md"],
              "additionalProperties": { "$ref": "#/$defs/sha256" }
            },
            "complete_directory": { "type": "boolean" },
            "local_modifications": { "type": "string", "minLength": 1 }
          }
        },
        "verdicts": {
          "type": "object",
          "required": ["compatibility", "security", "behavior_review"],
          "additionalProperties": false,
          "properties": {
            "compatibility": {
              "type": "object", "required": ["verdict", "doc", "row"],
              "properties": {
                "verdict": { "enum": ["COMPATIBLE", "COMPATIBLE-AFTER-ADAPTATION", "INCOMPATIBLE", "PENDING"],
                             "$comment": "Provisional vocabulary — AG-011 to freeze (ES-5)" },
                "doc": { "type": "string" }, "row": { "type": "string" }
              }
            },
            "security": {
              "type": "object", "required": ["verdict", "risk_class", "doc", "conditions_closed"],
              "properties": {
                "verdict": { "enum": ["ACCEPT", "ACCEPT-CONDITIONAL", "HOLD", "REJECT", "PENDING"] },
                "risk_class": { "$ref": "#/$defs/riskClass" },
                "doc": { "type": "string" },
                "conditions_closed": { "type": "array", "items": { "type": "string" } }
              }
            },
            "behavior_review": {
              "type": "object", "required": ["verdict", "gate"],
              "properties": {
                "verdict": { "enum": ["PASS", "FAIL", "PENDING"] },
                "gate": { "const": "G5" }
              }
            }
          }
        },
        "permissions": {
          "type": "object",
          "required": ["risk_class", "rule", "per_agent_overrides", "autoinvoke"],
          "additionalProperties": false,
          "properties": {
            "risk_class": { "$ref": "#/$defs/riskClass" },
            "rule": { "$ref": "#/$defs/rule" },
            "per_agent_overrides": { "type": "object", "additionalProperties": { "$ref": "#/$defs/rule" } },
            "autoinvoke": { "type": "boolean" }
          }
        },
        "assignment": {
          "type": "object", "required": ["agents", "scope"],
          "additionalProperties": false,
          "properties": {
            "agents": { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "type": "string" } },
            "scope": { "enum": ["factory-agents", "generated-project"] }
          },
          "if": { "properties": { "scope": { "const": "factory-agents" } } },
          "then": { "properties": { "agents": { "items": { "$ref": "#/$defs/agentId" } } } }
        },
        "versioning": {
          "type": "object",
          "required": ["upstream_pin", "local_rev", "registry_version", "history"],
          "additionalProperties": false,
          "properties": {
            "upstream_pin": { "type": ["string", "null"] },
            "local_rev": { "type": "integer", "minimum": 0 },
            "registry_version": { "type": "string" },
            "history": {
              "type": "array", "minItems": 1,
              "items": {
                "type": "object", "required": ["event", "date"],
                "properties": {
                  "event": { "enum": ["registered", "adopted-via-ADR", "promoted", "staged", "activated",
                                       "suspended", "retired", "re-pinned", "adapted", "permission-change",
                                       "verdict-change", "re-audited"] },
                  "date": { "$ref": "#/$defs/dateOrTBD" },
                  "gates": { "type": "array", "items": { "type": "string", "pattern": "^G[0-8]$" } },
                  "adr": { "type": "string" },
                  "actor": { "type": "string" },
                  "evidence": { "type": "string" }
                }
              }
            }
          }
        },
        "lifecycle": { "enum": ["CANDIDATE", "REVIEWED", "APPROVED", "STAGED", "ACTIVE", "SUSPENDED", "RETIRED"] },
        "reaudit_triggers": {
          "type": "array", "minItems": 1, "uniqueItems": true,
          "items": { "enum": ["upstream-drift", "opencode-version-bump", "permission-change",
                              "content-edit", "security-reclassification", "config-drift"] }
        },
        "notes": { "type": "string" }
      }
    }
  }
}
```

## 8. Worked examples (illustration only — no such rows exist today)

### 8.1 Vendored, ACTIVE (post-ratification shape)

```json
{
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
    "scope": "per-file-verified", "spdx": "MIT",
    "notice_files": ["LICENSE"], "verified_by": "G3", "verified_at": "TBD"
  },
  "integrity": {
    "file_hashes": { "SKILL.md": "sha256:<64-hex>", "references/template.md": "sha256:<64-hex>" },
    "complete_directory": true, "local_modifications": "none"
  },
  "verdicts": {
    "compatibility": { "verdict": "COMPATIBLE", "doc": "SKILLS_COMPATIBILITY_MATRIX.md", "row": "adr" },
    "security": { "verdict": "ACCEPT", "risk_class": "A", "doc": "SKILLS_SECURITY_AUDIT.md", "conditions_closed": [] },
    "behavior_review": { "verdict": "PENDING", "gate": "G5" }
  },
  "permissions": { "risk_class": "A", "rule": "allow", "per_agent_overrides": {}, "autoinvoke": false },
  "assignment": { "agents": ["AG-005", "AG-018", "AG-001"], "scope": "factory-agents" },
  "versioning": {
    "upstream_pin": "wshobson@4220308", "local_rev": 0, "registry_version": "0.1.0+pin.4220308",
    "history": [
      { "event": "registered", "date": "TBD" },
      { "event": "adopted-via-ADR", "adr": "ADR-007", "date": "TBD", "gates": ["G0", "G1", "G2", "G3", "G4"] }
    ]
  },
  "lifecycle": "APPROVED",
  "reaudit_triggers": ["upstream-drift", "opencode-version-bump", "permission-change", "content-edit"],
  "notes": "Schema illustration. APPROVED ⇒ enabled_in must actually be [] per X-2; shown non-empty here only to display the field shape — a real APPROVED row fails lint until promoted to STAGED. No registry exists today."
}
```

> Consistency note: the example deliberately mirrors the proposal's illustration; a **valid** APPROVED row has `enabled_in: []`. The lint suite (X-2) is the authority, not the example.

### 8.2 In-house, CANDIDATE (M-1 track)

```json
{
  "skill_id": "requirements-engineering",
  "tier": "shared",
  "category": "requirements-engineering",
  "library_path": "skills-library/in-house/requirements-engineering",
  "enabled_in": [],
  "source": { "type": "in-house", "cloned": "TBD" },
  "license": { "scope": "in-house", "spdx": "TBD", "notice_files": [], "verified_by": "G3", "verified_at": "TBD" },
  "integrity": { "file_hashes": { "SKILL.md": "sha256:<64-hex>" }, "complete_directory": true, "local_modifications": "none" },
  "verdicts": {
    "compatibility": { "verdict": "PENDING", "doc": "SKILLS_COMPATIBILITY_MATRIX.md", "row": "TBD" },
    "security": { "verdict": "PENDING", "risk_class": "A", "doc": "SKILLS_SECURITY_AUDIT.md", "conditions_closed": [] },
    "behavior_review": { "verdict": "PENDING", "gate": "G5" }
  },
  "permissions": { "risk_class": "A", "rule": "deny", "per_agent_overrides": {}, "autoinvoke": false },
  "assignment": { "agents": ["AG-004"], "scope": "factory-agents" },
  "versioning": { "upstream_pin": null, "local_rev": 0, "registry_version": "0.1.0", "history": [ { "event": "registered", "date": "TBD" } ] },
  "lifecycle": "CANDIDATE",
  "reaudit_triggers": ["content-edit", "opencode-version-bump", "permission-change"],
  "notes": "Factory-authored ≠ exempt: same V-1…V-8 / A-1…A-11 path from authoring day (AG-012 rec. 6). License policy pending ES-8."
}
```

## 9. Validation wiring

- **Schema lint** (V-1/V-2 extension, `scripts/validate_skills.py` + `tests/skills/`): JSON Schema §7 + X-1…X-12 + Plane A field allow-list (§6). Runs in CI on every change under `skills-library/`, `.opencode/skills/`, or skill-related config.
- **Uniqueness/precedence** (V-3): registry IDs vs all enabled sources in official registration order 1→6 + `skills` config array; I-1/I-2; seeded 11-pair collision block-list; case-insensitive near-collision flags.
- **Derived-config check** (I-3 / X-12): regenerate `opencode.json` skill rules from the registry; byte-diff; mismatch ⇒ C5 revert-to-registry + G8 log.
- **Live probes** (V-4/V-5, G6): only after promotion; record OpenCode build + model/provider per run (MM-4); resolve OQ-4 on first run.
- **Provenance/safety** (V-6/V-7): hash manifests, per-file license evidence, content scan on every vendored byte change; drift probe diffs `file_hashes` vs pinned commit on the ADR-fixed cadence (ES-4).

## 10. Schema evolution policy

- `schema_version` is SemVer-like: **additive** changes (new optional fields, new enum values) ⇒ minor bump, lint updated same PR; **breaking** changes (renames, removals, tightened constraints) ⇒ major bump + migration script + full V-1…V-8 regression (C4-class treatment).
- Enum additions for `category` require OQ-1 ratification first (ES-1); `verdicts.compatibility.verdict` additions require AG-011 freeze (ES-5).
- Registry rows are append-only in spirit: lifecycle RETIRED replaces deletion; `history` is never rewritten (git enforces the audit chain; X-12 checks it).
- The schema file itself is versioned in git alongside the registry; a registry PR that changes shape without a `schema_version` bump fails lint.

## 11. Traceability and limitations

| Obligation source | Schema element |
|---|---|
| Registry proposal §3.2 identity | `skill_id` pattern + X-1 (V2 does not enforce ⇒ lint must) |
| Proposal §3.2 source / AG-015 rec. 7 | `source.*` pin fields, X-7 |
| Proposal §3.2 license / AG-015 §3 | `license.*`, X-3 (AGPL never ACTIVE; per-file evidence) |
| Proposal §3.2 integrity / AG-011 KI-1 | `integrity.*`, X-6 (complete directory) |
| Proposal §3.2 verdicts / OBS-1 | row-level `doc`+`row` cross-refs, X-5 |
| Proposal §3.2 permissions / R5.2A | `permissions.*`, X-8, §4.2 guards |
| Proposal §3.2 assignment | `assignment.*`, X-11 (orphan rule, 18-agent catalog) |
| Proposal §3.2 lifecycle / A-1…A-11 | `lifecycle`, `history`, X-2/X-4; TBD placeholders, no fabricated PASS |
| Coverage matrix §4 V-1…V-8 | §9 wiring |
| Architecture D-3 / R-3 | §1 planes, §6 Plane A allow-list |

Limitations: this schema is **specified, not implemented**; no validator has been run; provisional enums (category, compatibility verdicts) are escalation items ES-1/ES-5; OpenCode frontmatter semantics are a fetched-docs snapshot pending G6/OQ-4 re-verification (ADR-003). Refinements RF-1…RF-3 diverge from the proposal's illustration intentionally and require ADR ratification. Sole files written by this tasking: this document and `docs/skills/SKILLS_GOVERNANCE.md`; no commits, configuration, or agent-definition changes.
