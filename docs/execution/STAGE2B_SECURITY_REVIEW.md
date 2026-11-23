# Stage 2B Security Review — Task Orchestration Plane

- **Auditor:** AG-015 (Security Auditor)
- **Date:** 2026-11-20
- **Scope:** `orchestration/task_orchestration/` (Stage 2B) — all 8 modules (~3,255 LOC) and their integration surface into Stage 2A (`orchestration/execution/`) and runtime (`orchestration/runtime/model_fallback.py`)
- **Method:** full source review, policy/contract comparison (`contracts/task-contract.md`, `orchestration/policies/security-policy.md`), read-only dynamic verification of guard behavior in scratch dirs (`/tmp/opencode`), test-suite execution, git/dependency/config inspection
- **Verdict:** **CONDITIONAL PASS** — 1 HIGH, 4 MEDIUM, 3 LOW, 2 INFO. The package contains no command execution, no secrets, no network, and its fail-closed posture is largely real; however one control gap (F-01) defeats the stage's core promise — independent verification of delegated work — and should be remediated before Stage 2B bookkeeping is relied on as authoritative.

---

## 1. Executive Summary

Stage 2B is a pure-stdlib, stdlib-only orchestration bookkeeping plane: task graphs, a guarded state machine implementing Task Contract rules 1–4, delegation with "fail-closed independent verification", a coordination read model, and bridges to Stage 2A (ledger, DCM, snapshots, resume) and to the runtime Model Fallback Manager.

**Static attack surface is well contained:** zero `subprocess`/`os.system`/`eval`/`exec`/`pickle`/network calls in the package (verified by pattern search); the only process launch reachable from Stage 2B is Stage 2A's `git cat-file -e` in `orchestration/execution/resume.py:178` (list-form args, no shell, fail-closed on error). Persistence is confined to `projects/<ID>/orchestration/task-orchestration/*.json`. Load paths re-validate everything (ids, catalog membership of `assigned_agent`, cycles, gate/criterion shape) and refuse corrupt files.

**The weaknesses are authorization and input-validation gaps in the *guarded transition* choke-point**, not code-execution risks:

1. **(HIGH)** A delegated child task can be self-completed via the generic `task-set` CLI path, bypassing `DelegationManager.verify_completion` and its independence checks entirely (F-01, reproduced live).
2. **(MEDIUM)** "Independence" is enforced only as id-difference; gate verdicts and criterion flags are self-declared by the acting agent with no cross-check against the quality-gate plane, and any catalog agent may "verify" a security-audit task (F-02).
3. **(MEDIUM)** Truthy-string coercion (`bool("false") == True`) in `criteria_results` is fail-**open** on the single most security-relevant input — the acceptance-criteria flags that gate COMPLETED (F-03, reproduced live).
4. **(MEDIUM)** `project_id` is never validated before filesystem path construction; a `--project ../escape` argument was demonstrated to load a plan from outside the `projects/` plane (F-04, reproduced live). Writes are mostly saved by content re-validation, but API-level `save(project_id=...)` accepts unvalidated ids.
5. **(MEDIUM)** The entire Stage 2B implementation is untracked in git — no provenance for a governance control, and it weakens the git-anchored integrity chain that Stage 2B's own `resume_view` depends on (F-10).

## 2. Scope and Inventory Reviewed

| Module | LOC | Security-relevant role |
|---|---|---|
| `models.py` | 992 | State machine; Task Contract rules 1–4 enforcement (`transition_task`); graph validation (cycles, catalog, ids) |
| `engine.py` | 548 | Plan build; capability→agent assignment; **file-plane persistence** (`save_plan`/`load_plan`/`next_plan_id`) |
| `delegation.py` | 416 | Parent→child delegation; **fail-closed `verify_completion`**; delegation persistence |
| `coordination.py` | 191 | Read model only; no writes |
| `context_integration.py` | 357 | Bridge to Stage 2A ledger/DCM/snapshot/resume; path containment via `_rel` |
| `model_fallback_integration.py` | 291 | Bridge to runtime ModelFallbackManager; ledger journalling of model events |
| `cli.py` | 288 | JSON command interface; exit-code semantics (0/1/2/3) |
| `__init__.py` | 172 | Public surface; boundary docstring claims |

Reviewed alongside: `contracts/task-contract.md`, `orchestration/execution/resume.py` (subprocess + snapshot verification), `orchestration/runtime/model_fallback.py` (agent-file reads), `tests/task_orchestration/` (4 suites, executed — all PASS).

## 3. Threat Model Applied (STRIDE, condensed)

- **Spoofing:** agent identity in this plane is *self-declared* via `--actor`/`--verifier` CLI flags; there is no caller↔agent binding. Accepted design constraint; its consequences are assessed in F-02/F-05/F-07.
- **Tampering:** file-plane JSON is mutable by anyone with repo write access; integrity controls (git, ledger, snapshots) exist but are not wired into the CLI transition paths (F-07, F-10).
- **Repudiation:** per-file history arrays are append-only *by convention only* (F-07).
- **Information disclosure:** absolute repo paths echoed in CLI error JSON (minor); plan files carry no secrets (goal text, agent ids, gate ids only).
- **DoS:** recursion crash on deep dependency chains (F-08); non-atomic writes can be corrupted by crashes — but corrupt JSON is refused fail-closed on load.
- **Elevation of privilege:** the primary risk class here — bypass of the verification gate (F-01) and weakened independence (F-02).

## 4. Findings

### F-01 — HIGH: Delegation verification bypass via generic `task-set` (CWE-863: Incorrect Authorization)

**Location:** `cli.py:204-224` (`task-set`), `delegation.py:198-207` (`track_status` COMPLETED refusal), `models.py:425-429` (rule-3 check scope).

**Description:** `DelegationManager.track_status` deliberately refuses `COMPLETED` to force delegated children through `verify_completion` ("completion must go through verify… so rules 1-3 are evaluated by a verifier, not asserted by the worker"). But `verify_completion`'s independence guarantees apply **only if the delegation flow is used**. The generic `task-set` command performs `transition_task()` on *any* task in the plan — including a delegated child — with no consultation of delegation records. Since the Task Contract allows `RUNNING -> COMPLETED` directly (`contracts/task-contract.md`, transition list), and `transition_task` applies the reviewer-independence check only to `REVIEW_REQUIRED -> COMPLETED` (`models.py:425`), a delegatee that never submits for review can self-complete its own task, marking its acceptance criteria satisfied inline with `--criteria`.

**Evidence (reproduced against the live package):**
```
F1) delegation track refuses COMPLETED: DelegationError          # intended control works
F2) delegated child self-COMPLETED via task-set (no verify, no independent reviewer):
    child status = COMPLETED | actor == assigned_agent: True | delegation record still: ACTIVE
```
Secondary impact: state divergence — the child is `COMPLETED` while the `DelegationRecord` remains `ACTIVE`, leaving no "verified" artifact anywhere (no `VerificationReport`, no `reviewed_by`).

**Threat:** a non-compliant delegatee agent (the exact adversary this plane exists to catch) trivially self-certifies completion of delegated work. Any orchestration consumer trusting delegation records as proof of independent verification is exposed.

**Remediation (recommended):**
1. In the `task-set` path, look up `DelegationManager.record_for_task(task_id)` and refuse `COMPLETED` (and `REVIEW_REQUIRED -> COMPLETED`) for any task that is a delegated child — direct callers to `delegation-verify`.
2. Or move the enforcement *down* into `transition_task` by passing the delegation context, so no call-site can forget it.
3. Add a coordination-view blocker for "delegated child COMPLETED while record not VERIFIED/COMPLETED" (drift detection).

---

### F-02 — MEDIUM: Independence is nominal (id-difference only); verdicts are self-declared, never cross-checked (CWE-284)

**Location:** `models.py:425-429`, `delegation.py:272-279`; `cli.py:96,128` (`--gates` flags).

**Description:**
- Rule 3 enforcement checks only `actor != assigned_agent` (task-set) and `verifier != delegatee AND != delegator` (`verify_completion`). Any other catalog agent — e.g. AG-009 (frontend) — can serve as "independent verifier" of a **security-audit** task's `QG-SECURITY` gate; there is no role/competence requirement and no prohibition on collusion pairs.
- Criterion flags and gate verdicts supplied via `--criteria`/`--gates` are accepted verbatim from the acting agent. The engine never reads the actual quality-gate results plane or any test evidence; `PASSING_GATE_VERDICTS` is enforced against *claimed* verdicts only.

**Evidence (live):** guarded self-completion of a backend task by its own developer, flipping `QG-CODE` PENDING→PASS in the same call:
```
A) self-completion RUNNING->COMPLETED by assigned agent: COMPLETED
```
(For directly assigned tasks this is literally contract-legal — the contract permits `RUNNING->COMPLETED` — which is precisely why the missing cross-check matters; the delegation path closes it, and F-01 re-opens it.)

**Remediation:** (a) require a role-matched verifier for security/review gates (e.g. `QG-SECURITY` → verifier in {AG-015}, `QG-REVIEW` → {AG-013}); (b) when a gate verdict is claimed via `--gates`, optionally cross-reference the governed gate plane (read-only); (c) record the source/evidence ref (ledger event id, test-run id) in `QualityGateResult.notes`.

---

### F-03 — MEDIUM: Truthy-string coercion makes criterion verification fail-open (CWE-697 / CWE-1244)

**Location:** `models.py:401` (`bool(criteria_results.get(...))`) and `delegation.py:286` (`{k: bool(v) ...}`).

**Description:** The single security-relevant input to the completion guard — the acceptance-criteria result map parsed from raw CLI JSON — coerces any value with `bool()`. The string `"false"`, `"FAIL"`, `"0"`, or `[]` all evaluate truthy → a criterion is recorded **satisfied**. A verifier (or an operator wiring an agent harness) that serializes booleans as strings flips the fail-closed guard into fail-open silently. (Gate verdicts do *not* have this bug — `GateVerdict(str(v))` raises on anything unrecognized, exit 3.)

**Evidence (live):**
```
B) criteria_results {'AC-1': 'false'} -> COMPLETED anyway: COMPLETED
```

**Remediation:** strict validation — `isinstance(v, bool)` else raise `TaskError`; accept `true/false` JSON literals only. One-line hardening in two places, plus a regression test.

---

### F-04 — MEDIUM: `project_id` used in filesystem paths before validation (CWE-22 path traversal, CWE-20)

**Location:** `engine.py:160-165` (`task_orchestration_dir`/`plan_file_path` join the raw id), `engine.py:172-191` (`next_plan_id`), `engine.py:209-212` (`load_plan`), `delegation.py:379-385` (`DelegationManager.save` accepts explicit `project_id`), `cli.py:70` (`--project`, free-form string).

**Description:** `PROJECT_ID_RE` exists (`models.py:42`) and validates *file contents* on load, but the `project_id` **argument** is never checked before path construction at any entry point. `--project ../escape` builds `projects/../escape/orchestration/task-orchestration/plan.json`, which POSIX-resolves outside the `projects/` plane. Demonstrated read:

**Evidence (live):**
```
RESULT load: succeeded; stored project_id: PROJECT-001 | loaded task count: 6   # --project ../escape
D3) delegations path built identically from unvalidated arg
```
The CLI further echoes the full attempted absolute path in its JSON error (minor info disclosure).

**Why not HIGH:** write paths are saved by content re-validation — `save_plan()` and delegation persistence derive the target directory from the *loaded and regex-validated* `plan.project_id`, so no arbitrary file write is reachable through the CLI, and a traversal-read still requires the target file to parse as a fully valid, cycle-free plan. But the guarantees are accidental, not engineered: `DelegationManager.save(repo_root, project_id=...)` (`delegation.py:379`) writes `delegations.json` to a **caller-supplied** unvalidated id (`mkdir(parents=True)` included), so any programmatic caller that passes user-influenced input gets a traversal write primitive today.

**Remediation:** validate `project_id` against `PROJECT_ID_RE` at the top of `load_plan`, `next_plan_id`, `task_orchestration_dir`, `plan_file_path`, `delegations_file_path`, `DelegationManager.save`, and the CLI parser (`type=` converter), and reject any id containing path separators — fail before touching the filesystem.

---

### F-05 — LOW: Catalog enforcement asymmetric — actors and loaded delegators bypass the agent catalog (CWE-863)

**Location:** `models.py:389-390` (actor regex only), `delegation.py:370` (`load_dict` adopts `delegator_agent` from file without any check), `models.py:708-730` (`DelegationRecord.validate` regex-only for agents).

**Description:** `Task.assigned_agent` is checked against `KNOWN_AGENTS` (AG-001..018) but transition actors are only regex-checked: `AG-999` is accepted as the actor of a guarded transition, and `AG-042` is adopted as the delegation's `delegator_agent` when read back from a tampered `delegations.json` — weakening `verify_completion`'s delegator-independence comparison (a forged delegator that matches a chosen "independent" verifier defeats rule 3).

**Evidence (live):**
```
C) PENDING->ASSIGNED with actor=AG-999 (outside catalog): accepted
E) delegator_agent after reload from tampered delegations.json: 'AG-042'
```

**Remediation:** apply `agent in KNOWN_AGENTS` uniformly to actors, verifiers, delegators, and load paths (create-path already does for delegatee, `delegation.py:116-117`).

---

### F-06 — LOW: Non-atomic read-modify-write persistence; lost-update races and archive TOCTOU (CWE-362/367)

**Location:** `engine.py:194-206` (`save_plan` `write_text`, archive `exists()`→write), `delegation.py:379-385`; every CLI mutation is `load_plan → mutate → save_plan` with no locking.

**Description:** Concurrent CLI invocations interleave load/modify/save: one writer's guarded transitions (or an entire delegation) are silently overwritten — a governance-integrity failure with no error surfaced. A crash during `write_text` leaves corrupt JSON (subsequent loads refuse fail-closed — good — but the plane is unavailable until manual repair). The "append-only" archive check (`archived.exists()` then write) has a race window, and file creation is non-exclusive.

**Mitigations present:** `delegation_counter` monotonic recompute on load (`delegation.py:374-376`) reduces id-collision impact; corrupt-file handling is fail-closed; archive refusal exists.

**Remediation:** write via temp-file + `os.replace` (atomic rename) + `fsync`; take an advisory lock (`fcntl.flock` on a per-project lockfile) around load→save; open archives with `O_EXCL`.

---

### F-07 — LOW: Transitions are not journalled by the CLI; audit trail is tamper-evident only if Stage 2A integration is used separately (CWE-531)

**Location:** `cli.py:204-281` (no `journal_*` calls); `context_integration.py:86-152` (journal functions exist but nothing in the CLI calls them); `models.py:258` (`history` list is mutable in the same file it is written to).

**Description:** The package's answer to repudiation is per-task/per-record `history` arrays — but these live in the same plain JSON that any actor of the plane rewrites wholesale on every save. `journal_task_change`/`journal_delegation_change` would bind transitions to the hash-chained Stage 2A ledger, and `checkpoint_plan` would pin the plan with snapshots; none of it is reachable through the CLI today. An agent with write access to the file plane can therefore edit history/verdicts undetectably *unless* git + ledger operation is mandatory — see also F-10 (the code itself isn't even committed).

**Remediation:** make `task-set`/`delegate`/`delegation-verify` optionally (then mandatorily) journal `STATE_CHANGED` via `context_integration`, and record `ledger event id` in the `StatusHistoryEntry.reason` or a new field; wire `checkpoint_plan` into `--save`.

---

### F-08 — LOW: Recursive cycle detection crashes CLI on deep dependency chains (CWE-674)

**Location:** `models.py:569-589` (`find_cycle.visit` recursion), `cli.py:160` (catch tuple excludes `RecursionError`).

**Description:** A linear dependency chain of ~1,000+ tasks (TASK ids allow up to 9999) exceeds Python's default recursion limit during `validate()`/`topological_order()`. The resulting `RecursionError` escapes the CLI's handler (`TaskError, ValueError, KeyError, OSError`) producing a raw traceback — an ugly non-zero exit and absolute-path leakage, though the behavior remains fail-closed (nothing is accepted).

**Remediation:** iterative DFS/Tarjan, or a depth guard with a clean `PlanningError`.

---

### F-09 — INFO: Boundary claims slightly narrower than actual behavior (documentation accuracy)

- `cli.py:12-14` claims the CLI "never touches agent/runtime/config files" — `status --models` performs **read-only** loads of `.opencode/agents/ag-*.md` through `ModelFallbackManager._load_hierarchies` (`runtime/model_fallback.py:91-108`). Reads, not mutations — but the claim should say "never modifies".
- `__init__.py:25-27` claims the package "mutates only … `projects/<ID>/orchestration/task-orchestration/`" — the documented integration surface (`checkpoint_plan`, `assemble_task_context(persist=True)`, `journal_*`) legitimately also writes `projects/<ID>/execution/…` (ledger, snapshots, context manifests) when callers use it. Nothing escapes the project plane (writes derive from validated ids), but the docstring understates the write set for anyone mapping permissions in the governance plane.
- No integrity issue; align the docstrings before the next permission-reconciliation task (see `PROJECT_STATUS.md` pending item).

---

### F-10 — MEDIUM: Stage 2B package (and its integration surfaces) untracked in git — no provenance for a governance control (CWE-1188 / A2 supply-chain: integrity)

**Evidence:** `git ls-files orchestration/task_orchestration` → empty; `git status --porcelain` → `?? orchestration/task_orchestration/`, `?? orchestration/execution/`, `?? orchestration/skills/`, `?? docs/execution/`, `?? docs/skills/`. `__pycache__/*.pyc` artifacts are present in the source tree (harmless but indicating no ignore policy yet applied to these paths).

**Description:** Stage 2B's `resume_view`/`checkpoint_integrity` trust git anchors (`before/after_commit`, Stage 2A clause 2 `git cat-file -e`) and snapshot hash verification to certify state — yet the orchestration *control code itself* has no committed baseline. Any silent edit to the guards in `models.py`/`delegation.py` (e.g. deleting the rule-3 check) is undetectable: no diff, no review trail, no revert point. For an integrity-audit plane this is the weakest kind of provenance gap.

**Remediation:** commit `orchestration/task_orchestration/` (+ `tests/task_orchestration/`) on a reviewed branch with the test-run evidence attached; add `__pycache__/` to `.gitignore`; consider including the module-tree hash in the checkpoint manifest (Stage 2A `context_manifest_hash` already pins files *referenced* by a context — extend governed refs to the orchestration package).

## 5. Controls Verified as Effective (positive findings)

| Control | Evidence |
|---|---|
| No command execution anywhere in Stage 2B (grep: `subprocess`, `os.system`, `eval(`, `exec(`, `pickle`, `shell`, `socket`, `requests`, `yaml` → **zero hits**) | pattern search over all 8 modules |
| Only reachable `subprocess` is Stage 2A git anchor check: list-form args, no shell, `OSError`→False fail-closed (`resume.py:176-184`); `commit` value only reaches `git cat-file -e` (object-exists probe) — no injection primitive | code review |
| Single guarded transition choke-point enforcing legality + rules 1/2/4; refusal leaves task untouched (prospective materialization, `models.py:394-412`) | code + contract match |
| Stricter-than-contract gate policy: PENDING (never-evaluated) gates also refuse completion (`models.py:120-136`) | code + `test_delegation.py` |
| `verify_completion`: precondition-bound to SUBMITTED, self-review and delegator-review refused, failed verification moves child to REJECTED with recorded reasons | `test_verify_self_review_and_delegator_refused` + live run |
| `track_status` refuses COMPLETED on the delegation path (the intent F-01 bypasses) | live F1 |
| Cancellation/revoke require reason (rule 4) | code + tests |
| Graph validation on every load: ids, catalog `assigned_agent`, dangling edges, self-edges, cycles — corrupt/inconsistent JSON refused fail-closed (`PlanningError`), never silently repaired | `engine.py:209-220`, `test_save_archive_append_only_and_corrupt_refused` |
| Delegation cross-plan protection (`load_dict` refuses records of another plan) | `delegation.py:368-369` |
| `_rel()` containment guard rejects journalling paths that resolve outside repo root | `context_integration.py:62-66` |
| CLI exit-code contract (0/1/2/3) surfaces verification failures and guard refusals non-zero | `cli.py:8-10,150-162` |
| No secrets, credentials, or PII in persisted planes (plans/delegations carry ids, titles, verdicts only) | file inspection |
| Runtime bridge mutates nothing on disk: `log_change` is in-memory; agent front-matter reads are read-only with safe defaults | `model_fallback.py:198-220,110-123` |

**Test evidence:** all four Stage 2B suites executed at audit time — `test_engine.py`, `test_delegation.py`, `test_coordination.py`, `test_parallel.py` — PASS (standalone runners; repo `tests/run_all.py` list includes them).

## 6. Command-Execution & Escalation Assessment

- **Direct execution surface: none.** Stage 2B never spawns processes, loads dynamic modules from user data, or deserializes executable formats (JSON-only, stdlib `json`, no pickle/`importlib` on inputs).
- **Indirect execution surface:** Stage 2B hands control to (a) Stage 2A ledger/snapshot/resume functions — reviewed: subprocess use is git-only and inert, path operations derive from validated ids; (b) the DCM manifest, where caller-supplied `task_refs` strings (API-only; no CLI exposure) pass to Stage 2A for resolution — containment there is Stage 2A's responsibility, and Stage 2B should not widen it: `assemble_task_context` is fine as-is but `task_refs` validation would keep the boundary honest.
- **Privilege model:** the plane "authorizes nothing"; execution authorization stays with the governance plane — consistent with `__init__.py` and the ADR-002 posture. The escalation-relevant weaknesses are therefore all *bookkeeping-authority* weaknesses (F-01/F-02/F-03), which matter because downstream consumers (runners, gates) are expected to trust "COMPLETED" as proof of verification.

## 7. Prioritized Remediation Plan

| # | Finding | Severity | Effort | Suggested owner/gate |
|---|---|---|---|---|
| 1 | F-01 delegation-completion bypass | HIGH | S | AG-008 + test; must block before Stage 2C consumes "COMPLETED" as verified |
| 2 | F-03 strict bool validation | MEDIUM | XS | AG-008; one-line ×2 + regression test |
| 3 | F-04 validate `project_id` at every entry point | MEDIUM | S | AG-008/AG-016 (CLI) |
| 4 | F-02 role-matched verifiers + gate cross-check | MEDIUM | M | AG-002 (governance) + AG-015 sign-off |
| 5 | F-10 commit package + `.gitignore` for `__pycache__` | MEDIUM | XS | coordinator (AG-001) at stage closure |
| 6 | F-05 catalog uniformity for actors/loaded delegators | LOW | XS | AG-008 |
| 7 | F-06 atomic writes + flock | LOW | M | AG-008 |
| 8 | F-07 wire ledger journalling into CLI mutations | LOW | M | AG-008 with Stage 2A contract check (no new event types — existing vocabulary suffices) |
| 9 | F-08 iterative cycle detection | LOW | S | AG-008 |
| 10 | F-09 docstring/boundary alignment | INFO | XS | docs owner |

## 8. Residual Risk Statement

After F-01 and F-03 are remediated and the package is committed (F-10), the plane's claim — "plans, assigns, verifies, reports; authorizes nothing" — will be substantiated for the delegation flow, with remaining accepted risk limited to the self-declared-identity model (mitigated externally by git + the Stage 2A ledger once F-07 lands) and repository-local attackers, who by ADR-002 premises are within the governance plane's trust boundary, not the threat model of this layer.

---
*Prepared by AG-015. Review-only engagement: no file under `orchestration/`, `tests/`, or `contracts/` was modified. All dynamic probes ran against throwaway scratch trees under `/tmp`; the repository source was exercised read-only. Verification commands and outputs are reproducible via the snippets embedded in each finding.*
