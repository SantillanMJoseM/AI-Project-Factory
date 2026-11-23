# Skills Permission Model (Stage 0 Runtime)

| Field | Value |
|---|---|
| doc_id | SKILLS-PERMISSION-MODEL-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | DESCRIBES IMPLEMENTED CODE — fail-closed permission logic in `orchestration/skills/registry.py` and guards in `validator.py`. Live OpenCode interpretation is NOT yet verified (OQ-4). |
| normative inputs | `SKILLS_GOVERNANCE.md` §5 (P-1…P-5) · `SKILLS_REGISTRY_SCHEMA.md` §3.6/§4.2/§5 (X-2/X-8/X-9/X-10/X-11/X-12) · `SKILLS_SECURITY_POLICY.md` (LEVEL A/B/C, §14 anti-tampering, §16 authorization) · R5.2A fail-closed posture |
| enforcement boundary | The registry and derived config are governance metadata. OpenCode V2 interprets only native per-agent `skill` rules and Plane A autoinvoke; all plane-B semantics are enforced in-house until G6. |

---

## 1. Purpose and posture

Document the permission model as implemented in the Stage 0 runtime: a **fail-closed**, risk-class-driven, per-agent `skill` permission system that is derived deterministically from the registry, never hand-edited.

Non-negotiable posture (inherited from R5.2A and `SKILLS_GOVERNANCE.md` §5.2):

- Default `deny` for the `skill` action; every allowance is generated from a registry row.
- Anything unverified is unusable (NOT-USABLE), never "probably fine".
- Loosening beyond a risk-class default requires recorded human-approval evidence and is never applied automatically by the generator.
- A SUSPENDED (kill-switch) row is `deny` everywhere and cannot be relaxed by any override.

## 2. Native mechanism the model targets

From the OpenCode V2 mechanics snapshot (pending G6/OQ-4 re-verification):

- Per-agent `skill` rules under `agents.<id>.permissions.skill` are **ordered; last match wins** (D-4, P-1).
- `allow` loads silently; `ask` prompts the user; `deny` rejects and hides the skill from the advertised list.
- Plane A `metadata.opencode.autoinvoke: false` (or `disable-model-invocation: true`) removes a skill from the model-driven list while keeping it loadable by exact ID and `@skill-id`; **autoinvoke wins if both flags are present** (`effective_autoinvoke()`, validator.py:313-320).
- OpenCode interprets none of the Plane B governance fields (D-3); a registry `deny` only takes effect once the derived config is written and verified live at G6.

## 3. Risk classes and default rules

`models.py` defines the controlled mapping and strictness ordering:

```
DEFAULT_RULE_BY_RISK = {"A": Rule.ALLOW, "B": Rule.ASK, "C": Rule.DENY}
RULE_STRICTNESS      = {Rule.ALLOW: 0, Rule.ASK: 1, Rule.DENY: 2}
```

| Risk class | AG-015 / security policy equivalent | Default rule | Notes |
|---|---|---|---|
| A | LEVEL A — read-only, side-effect-free, T0/T1 pinned | `allow` | allow-list only; ACCEPT security verdict |
| B | LEVEL B — reversible workspace changes, pinned deps | `ask` | worktree/gitops/CI-CD/migration classes |
| C | LEVEL C — credentials, scripts, egress, destructive, policy change | `deny` | human adjudication; any relaxation needs ADR + evidence |

Class membership comes from `verdicts.security.risk_class` and must equal `permissions.risk_class` (X-8). Upstream/third-party `risk` labels are never substituted (K-9).

## 4. Registry fields

| Field | Type / enum | Implementation constraint |
|---|---|---|
| `permissions.risk_class` | `A`/`B`/`C` | must equal `verdicts.security.risk_class` (X-8) |
| `permissions.rule` | `allow`/`ask`/`deny` | may equal the class default, tighten, or (with human-approved history evidence) loosen |
| `permissions.per_agent_overrides` | map `AG-###` → rule | may tighten freely; may not relax a class-C default or SUSPENDED deny without approval |
| `permissions.autoinvoke` | boolean | must equal Plane A effective autoinvoke (X-10); process-class skills declare `false` (P-3) |
| `assignment.agents` | ≥1 id | `factory-agents`: AG-001…AG-018 (`AGENT_IDS`); `generated-project`: project agent ids, never factory ids (X-11) |
| `assignment.scope` | `factory-agents`/`generated-project` | orphan-enabled skills (STAGED/ACTIVE with no consumer) are rejected (X-11) |

## 5. Effective-rule resolution (`Registry.effective_rule`)

`registry.py:216-228` resolves the rule for one `(entry, agent_id)` with fail-closed ordering:

1. If `lifecycle == SUSPENDED` → `deny` (unconditional kill-switch).
2. Else if `lifecycle == STAGED` → `ask` (pilot posture regardless of class).
3. Else compute the class default from `DEFAULT_RULE_BY_RISK`.
4. Apply an override **only if it is at least as strict as the default** (`RULE_STRICTNESS[override] >= RULE_STRICTNESS[default]`). A loosening override is ignored by the generator.
5. Otherwise return the default.

Human-approved loosening (X-8) is an *authoring* condition validated by lint (`_has_human_approval()` checks history for a `permission-change` event with human/approval evidence). The generator itself never widens a rule.

## 6. Derived configuration (`Registry.derive_permissions` / `render_permissions`)

`registry.py:230-267` renders the derived `opencode.json` permission document:

- Global default is `{"permissions": {"skill": "deny"}}` — deny everything not explicitly allowed.
- Only rows with lifecycle `STAGED`, `ACTIVE` or `SUSPENDED` are included.
- A row with empty `enabled_in` is skipped **unless it is SUSPENDED**: suspended rows keep an explicit deny rule even after their artifact was removed, so the kill-switch survives rollback and guards against silent resurrection (GOV-2 / T-3).
- For each assigned agent, a rule `{"action": <effective rule>, "pattern": <skill_id>}` is emitted.
- Rules are sorted so that `deny` actions are placed **last** — under last-match-wins semantics the kill-switch always wins regardless of insertion order.
- `render_permissions()` emits canonical bytes (`indent=2, sort_keys=True, trailing newline`) for byte-for-byte regenerate-and-diff (I-3). `check_derived_config()` (X-12) flags both byte drift and semantic drift.

## 7. Lifecycle-dependent permission posture

`Registry.transition()` (registry.py:106-154) sets enablement and permission posture per target state:

| Target state | `enabled_in` | `permissions.rule` | Overrides |
|---|---|---|---|
| CANDIDATE / REVIEWED / APPROVED / RETIRED | cleared to `[]` | `deny` | left as-is for these states (lint governs) |
| STAGED | defaults to `.opencode/skills/<id>` if empty | `ask` | cleared (`{}`) |
| ACTIVE | defaults to `.opencode/skills/<id>` if empty | class default (A→allow, B→ask, C→deny) | retained (tighten-only at generation) |
| SUSPENDED | unchanged (copies may remain on disk) | `deny` | cleared (`{}`) |

`effective_rule()` is stricter than the stored `rule`: a STAGED row is always `ask`, a SUSPENDED row always `deny`, irrespective of the `permissions.rule` field.

Lint guards (X-2) reject a STAGED row whose rule is not `ask`, and a SUSPENDED row whose rule is not `deny` or which carries any override.

## 8. Human approval and anti-tampering

- **LEVEL C / rule loosening:** `SKILLS_SECURITY_POLICY.md` §16 requires explicit recorded human approval (other than the requester) in `PROJECT_DECISIONS.md`. The runtime enforces the machine-checkable part via X-8: a rule looser than the class default, or a loosening per-agent override, fails lint unless history carries human-approval evidence.
- **Separation of duties (§14.4):** the requester may not self-approve; security verdicts come from AG-015/AG-003, never from upstream labels (ADR-004).
- **No delegation bypass (§14.3):** controls follow the operation, not the actor — a sub-agent cannot launder a denied operation. This is a policy control, not implemented in the Stage 0 runtime; it is documented here as the governing rule.
- **Policy protection (§14.1/§14.2):** the policy, `AGENTS.md`, `.opencode/` config and context docs are human-controlled only. No skill is installed that changes them (and no skill was installed at all).

## 9. Enforcement gaps (honest status)

1. OpenCode V2 has **not** been run against these rules. P-5 / OQ-4 / ADR-003: no permission-dependent claim is evidence until G6 executes V-4/V-5 live probes and records the installed build version. A permission leak (e.g. `allow` where `ask` was intended) is a hard G6 FAIL.
2. The derived config currently has no committed target file in `.opencode/`; `permissions`/`check-permissions` are available for generation and diffing, but no live config is installed or verified.
3. `{permissions: {skill: "deny"}}` at global scope is what the generator emits; whether a given OpenCode build enforces global-vs-agent precedence exactly as documented must be confirmed at G6 (last-match-wins ordering is relied upon for the deny-last sort).

## 10. Evidence index

- `orchestration/skills/models.py` — `DEFAULT_RULE_BY_RISK`, `RULE_STRICTNESS`, `Rule`, `RiskClass`, `Permissions`, `AGENT_IDS`, `ALLOWED_TRANSITIONS`.
- `orchestration/skills/registry.py:216-267` — `effective_rule()`, `derive_permissions()`, `render_permissions()`.
- `orchestration/skills/validator.py:452-579` — X-8 human-approval check, X-9 enablement, X-11 assignment, and permission guards.
- `orchestration/skills/validator.py:610-629` — `check_derived_config()` (X-12).
- `orchestration/skills/validator.py:313-361` — `effective_autoinvoke()` and Plane A frontmatter validation (X-10).
- `tests/skills/test_registry.py::test_derive_permissions_is_fail_closed` — executable proof of the fail-closed matrix including a SUSPENDED row with a hidden `allow` override.
- `tests/skills/test_validation.py::test_x8_risk_class_and_loosening_guards`, `::test_x9_and_x11_guards`, `::test_x2_lifecycle_enablement_and_permission_guards`.
- Companion: `SKILLS_VERSIONING_AND_ROLLBACK.md` (kill-switch lifecycle), `SKILLS_VALIDATION_FRAMEWORK.md` (X-rule enforcement).
