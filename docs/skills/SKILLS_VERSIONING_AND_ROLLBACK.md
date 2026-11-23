# Skills Versioning and Rollback (Stage 0 Runtime)

| Field | Value |
|---|---|
| doc_id | SKILLS-VERSIONING-AND-ROLLBACK-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | DESCRIBES IMPLEMENTED CODE — lifecycle transitions, append-only history and kill-switch rollback are implemented in `orchestration/skills/registry.py`. Upstream drift probe is NOT implemented. |
| normative inputs | `SKILLS_GOVERNANCE.md` §4 (T-1…T-5), §6 (C1…C6) · `SKILLS_REGISTRY_SCHEMA.md` §3.8/§5/§10 · `SKILLS_ADOPTION_PLAN.md` §6 (batch rollback) · `SKILLS_COVERAGE_MATRIX.md` §6 (G8) |
| enforcement boundary | History and lifecycle are Plane B governance metadata (git + lint), not something OpenCode interprets. |

---

## 1. Purpose

Document the version identity, guarded lifecycle state machine, append-only history and per-skill rollback as implemented at Stage 0. The design goal is an auditable, reversible governance system: every state change appends evidence, rows are never deleted, and rollback is a fast permission kill-switch plus artifact removal with a silent-resurrection re-check.

## 2. Version identity (per row and envelope)

| Element | Location | Implementation |
|---|---|---|
| `schema_version` | envelope | const `"1.0"` in `schemas/skill-registry.schema.json`; versions the registry **format** |
| `registry_version` | envelope / row | `Registry.registry_version` (default `"0.1.0"`); per-row `versioning.registry_version` ties row to pin (e.g. `0.1.0+pin.4220308`) |
| `updated_at` | envelope | set to `date.today().isoformat()` on `Registry.save()` and on transitions/rollback (or `date_str` override) |
| `source.commit_sha` + `versioning.upstream_pin` | row | `<repo>@<sha>` for non-in-house; `None` for in-house (X-7) |
| `versioning.local_rev` | row | integer ≥ 0, increments on local modification (C2); `adapted` rows require ≥ 1 |
| `integrity.file_hashes` | row | map path → `sha256:<64 hex>`; must include SKILL.md; verified against disk when `repo_root` is passed to `validate_registry()` (X-6) |

Evolution policy (schema doc §10, not yet exercised): additive schema changes ⇒ minor bump; breaking changes ⇒ major bump + migration + full V-1…V-8 regression (C4-class).

## 3. Lifecycle state machine

`models.py` encodes the legal transitions and their history events:

```
ALLOWED_TRANSITIONS = {
  CANDIDATE: {REVIEWED, SUSPENDED, RETIRED},
  REVIEWED:  {APPROVED, SUSPENDED, RETIRED},
  APPROVED:  {STAGED, SUSPENDED, RETIRED},
  STAGED:    {ACTIVE, SUSPENDED, RETIRED},
  ACTIVE:    {SUSPENDED, RETIRED},
  SUSPENDED: {CANDIDATE, RETIRED},   # re-entry is CANDIDATE (full G1–G7), not a pause
  RETIRED:   set(),                  # terminal
}

EVENT_BY_LIFECYCLE = {
  CANDIDATE: registered, REVIEWED: re-audited, APPROVED: adopted-via-ADR,
  STAGED: staged, ACTIVE: activated, SUSPENDED: suspended, RETIRED: retired,
}
```

| From → To | Effect (permission / enablement) | History event |
|---|---|---|
| → CANDIDATE / REVIEWED / APPROVED | `enabled_in=[]`, rule `deny` | registered / re-audited / adopted-via-ADR |
| APPROVED → STAGED | promotion copy created if empty, rule `ask`, overrides cleared | staged |
| STAGED → ACTIVE | promotion copy ensured, rule = class default | activated |
| any pre-RETIRED → SUSPENDED | rule `deny`, overrides cleared; copies may remain on disk | suspended |
| SUSPENDED → CANDIDATE | re-entry as new (G1–G7 owed) | registered |
| any → RETIRED | `enabled_in=[]`, rule `deny`; row retained forever | retired |

`Registry.transition()` is fail-closed: an illegal transition raises `RegistryError` and leaves the row untouched (no partial mutation), including no history append.

## 4. Append-only history

Every `versioning.history` entry is a `HistoryEntry` with fields `event`, `date` (ISO or `TBD`), and optional `gates`, `adr`, `actor`, `evidence` (RF-2). `_history_entry()` builds entries with `date_str` override or today's date.

- **T-1:** each transition appends exactly one entry; rows are never deleted (`Registry.add()` refuses duplicate ids; there is no remove method).
- The fixture row begins with `{"event": "registered", "date": "TBD"}` — `TBD` is preserved until a real gate runs (evidence-over-assertion rule).
- `test_history_is_append_only` proves the original prefix is unchanged after REVIEWED→APPROVED→STAGED.
- `test_invalid_transition_is_blocked_without_mutation` proves failed transitions neither change lifecycle nor history.

## 5. Rollback (T-3)

`Registry.rollback()` (registry.py:156-194) implements the per-skill kill-switch:

1. Refuse if `lifecycle == RETIRED` (`RegistryError: cannot roll back RETIRED row`).
2. Set `permissions.rule = DENY` and clear `per_agent_overrides` (permission kill-switch).
3. Set `enabled_in = []` (remove artifact from all enablement sources).
4. Set `lifecycle = SUSPENDED`.
5. Append one `suspended` history entry with evidence `rollback from <previous state>` plus optional `reason:` and `actor`.
6. Update envelope `updated_at`.

The row is retained (append-only). The caller is responsible for re-running V-3 (step 3 of T-3) to catch silent resurrection; `validate_registry()` provides that check and `test_rollback_resolves_duplicate_enablement_without_resurrection` proves that rolling back a colliding copy clears a V-3 error while the canonical STAGED row survives.

Critically, `derive_permissions()` keeps a SUSPENDED row's explicit deny even though `enabled_in` is now empty, and sorts deny rules last — so the kill-switch survives rollback and cannot be undone by a hidden override (`test_rollback_derives_deny_even_with_hidden_overrides`).

`cli.py` exposes `rollback --registry PATH --skill-id ID [--actor ... --reason ... --output FILE]`; exit 0 on success, 3 on error. With `--output`, the input file is left untouched (`test_cli_rollback_writes_updated_registry`).

## 6. Change classes and re-audit triggers

`ReauditTrigger` enum and the schema's `reaudit_triggers` field encode the V-8 change classes from `SKILLS_GOVERNANCE.md` §6.2:

| Trigger | Change class | Required re-run (normative) | Runtime support |
|---|---|---|---|
| `upstream-drift` | C1 upstream re-pin | V-6, V-7 diff + G3–G6 | trigger declared; no probe implemented |
| `content-edit` | C2 local modification | compat re-grade, V-1…V-3, G5 | trigger declared; hash drift detectable via `repo_root` diff |
| `permission-change` | C3 permission/assignment edit | regenerate config, V-4, G4 if class ≥ B | X-8/X-12 checks + regeneration |
| `opencode-version-bump` | C4 OpenCode version bump | full V-1…V-8; OQ-4 re-verified | trigger declared; CI wiring not implemented |
| `config-drift` | C5 docs/config drift | I-3 regenerate-and-diff ⇒ revert, G8 log | `check_derived_config()` implemented |
| `security-reclassification` | C6 security reclassification | immediate SUSPENDED pending review (T-4) | SUSPENDED posture implemented; auto-trigger not wired |

Additional history events `re-pinned`, `adapted`, `permission-change`, `verdict-change`, `re-audited` are available in the `HistoryEvent` enum for recording these changes, but there is no special transition method for them — they are recorded through metadata edits plus history entries, gated by lint.

## 7. Batch rollback (governance, not runtime)

`SKILLS_ADOPTION_PLAN.md` §6 defines batch rollback: deny a stage's ID list in one permission-rule pass, then remove directories stage by stage; Stage 0 artifacts (harness, ADR) are never rollback targets. The Stage 0 runtime implements the **per-skill** primitive (`Registry.rollback`) only; batch orchestration is a documented procedure, not an implemented command.

## 8. Limitations (honest status)

1. No upstream-drift probe or scheduled cadence exists (ES-4); `upstream-drift` is a declared trigger only.
2. Re-entry from SUSPENDED to CANDIDATE does not itself execute G1–G7 — it resets lifecycle and the gates must be re-run by the owning agents.
3. RETIRED is terminal; `rollback()` and all transitions out of it are refused.
4. No live OpenCode build is involved; history entries recording G6 evidence (build version, model/provider per MM-4) must be supplied by the caller (`--evidence`/history fields), not generated by the runtime.
5. Atomicity across registry file + on-disk artifacts + derived config is not implemented as one transaction; `save()` rewrites the JSON file only. Operators must follow the T-3 checklist manually.

## 9. Evidence index

- `orchestration/skills/models.py` — `Lifecycle`, `HistoryEvent`, `ReauditTrigger`, `ALLOWED_TRANSITIONS`, `EVENT_BY_LIFECYCLE`, `HistoryEntry`.
- `orchestration/skills/registry.py:106-154` — `transition()` (guards + posture + history).
- `orchestration/skills/registry.py:156-194` — `rollback()` (kill-switch).
- `orchestration/skills/registry.py:73-78` — `save()` (JSON write; `updated_at` maintenance).
- `orchestration/skills/registry.py:230-260` — derived-config kill-switch survival and deny-last ordering.
- `tests/skills/test_registry.py` — transitions, append-only history, fail-closed invalid transitions.
- `tests/skills/test_rollback.py` — all seven rollback scenarios including RETIRED refusal and CLI behavior.
- Companion: `SKILLS_PERMISSION_MODEL.md` (rule semantics), `SKILLS_VALIDATION_FRAMEWORK.md` (V-3 / X-12 checks).
