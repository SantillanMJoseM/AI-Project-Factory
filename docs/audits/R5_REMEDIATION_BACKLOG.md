# R5_REMEDIATION_BACKLOG

Prioritised remediation backlog derived from `INDEPENDENT_ARCHITECTURAL_AUDIT_R5.md`.

- Baseline: `main` at `d3c9cde`. Line references are to that commit unless marked R5.2 (`5bd7187`, branch `feature/r5.2-workflow-integrity`).
- Severity: CRITICAL / HIGH / MEDIUM / LOW.
- Complexity: S (up to 2 days), M (3 to 6 days), L (more than 1 week), with one engineer and the existing test harness.
- "R5.2 status" records what the R5.2 commit does for the same finding, based on the same experiments. It is an observation to be re-verified by the R5.2 re-audit, not an acceptance result.
- Experiment identifiers (E*, T*, P*, L*) refer to the audit report, section 12. The harness is outside the repository (`/tmp/opencode/exp/run_exp.py`) and should be promoted into the test suite.

## 1. Summary

| ID | Severity | Title | R5.2 status | Suggested release |
|---|---|---|---|---|
| AUD-R5-001 | CRITICAL | `--auto` removes every `ask` permission gate | Not fixed | R5.2 |
| AUD-R5-002 | CRITICAL | Agent working directory not isolated (`PWD` inheritance) | Not fixed | R5.2 |
| AUD-R5-003 | CRITICAL | CLI completes tasks without Quality Gate, acceptance or review | Not fixed | R5.2 |
| AUD-R5-004 | CRITICAL | Quality Gate validator is fail-open; `evaluate_gate` trusted certificate | Partly fixed (`evaluate_gate` only) | R5.2 |
| AUD-R5-005 | CRITICAL | Workflow reports COMPLETED falsely; ignores stages | Partly fixed (false success fixed; stages not) | R5.2 / R5.3 |
| AUD-R5-006 | CRITICAL | Human approvals are recorded but never enforced | Not fixed | R5.2 |
| AUD-R5-007 | CRITICAL | Release traceability can PASS without approval or with altered artifacts | Not fixed | R5.2 |
| AUD-R5-008 | HIGH | Audit records and event log mutable; self-audit accepted | Partly fixed | R5.2 |
| AUD-R5-009 | HIGH | Native OpenCode delegation and coordination records not implemented | Not fixed | R5.4 |
| AUD-R5-010 | HIGH | Duplicate task assignment under concurrency | Not fixed | R5.2 |
| AUD-R5-011 | HIGH | Retry accounting, retry limit and correction loop missing | Partly fixed (resume) | R5.3 |
| AUD-R5-012 | HIGH | Transition and dependency bypasses (assign, complete, cancel) | Not fixed | R5.2 |
| AUD-R5-013 | HIGH | Execution evidence misrepresents results and context | Partly fixed (inputs) | R5.3 |
| AUD-R5-014 | HIGH | Agent discovery and validation inconsistent; normative IDs rejected; error text lost | Not fixed | R5.2 |
| AUD-R5-015 | HIGH | No filesystem, network or secret boundary for executors | Not fixed | R5.2 |
| AUD-R5-016 | HIGH | Project lifecycle and workflow stages not bound to tasks | Not fixed | R5.3 |
| AUD-R5-017 | HIGH | Quality evidence is self-reported and unverifiable | Not fixed | R5.2 |
| AUD-R5-018 | HIGH | Traceability Quality Gate integration broken in CLI; its test passes vacuously | Not fixed | R5.2 |
| AUD-R5-019 | HIGH | Declared test command covers 5 of 17 test modules; several tests vacuous | Not fixed | R5.2 |
| AUD-R5-020 | HIGH | Remediation records claim capabilities not reproduced | Not fixed | R5.2 (records) |
| AUD-R5-021 | HIGH | PROJECT-001 release evidence misbound and not reproducible | Not applicable | Before any pilot |
| AUD-R5-022 | MEDIUM | Reference and dependency integrity gaps | Partly fixed (cycles) | R5.3 |
| AUD-R5-023 | MEDIUM | Contract and schema field mismatches | Not fixed | R5.3 |
| AUD-R5-024 | MEDIUM | Operator identity and authorisation absent | Not fixed | R5.2 |
| AUD-R5-025 | MEDIUM | Preflight reports PASS for unverified checks | Not fixed | R5.2 |
| AUD-R5-026 | MEDIUM | Documentation contradictions and stale state | Not fixed | R5.2 (docs) |
| AUD-R5-027 | MEDIUM | Adapter process control and result classification | Not fixed | R5.2 |
| AUD-R5-028 | MEDIUM | Quality certificate not bound to audited commit by the gate | Not fixed | R5.2 |
| AUD-R5-029 | MEDIUM | Uncontrolled concurrent state changes and branch switching | Observed during audit | Process |
| AUD-R5-030 | LOW | Traceability verdict never reports BLOCKED | Not fixed | R5.3 |
| AUD-R5-031 | LOW | ID generation by full scan; unbounded list queries | Not fixed | R5.5 |
| AUD-R5-032 | LOW | No structured logs, metrics, backup or retention | Not fixed | R5.5 |
| AUD-R5-033 | LOW | OpenCode and runtime versions not pinned | Not fixed | R5.2 |
| AUD-R5-034 | LOW | Duplicated code, dead code and monolithic runtime | Partly changed | R5.3 |

Counts: 7 CRITICAL, 14 HIGH, 8 MEDIUM, 5 LOW (34).

Suggested sequence: security and state truth first (R5.2), then state integrity and workflow semantics (R5.3), then delegation and audit flow (R5.4), then release and approval enforcement with staging drills (R5.5), then pilot preparation and re-audit (R5.6). Details in `R5_ARCHITECTURAL_RECOMMENDATIONS.md`.

---

## 2. CRITICAL findings

### AUD-R5-001 — `--auto` removes every `ask` permission gate

- Severity: CRITICAL
- Affected component: `orchestration/runtime/opencode_adapter.py` (`invoke`); all executable agents in `.opencode/agents/`.
- Evidence and source references:
  - `opencode_adapter.py` line 37: `cmd = [self.binary, "run", "--agent", agent_id, "--format", "json", "--auto", prompt]`.
  - OpenCode help for `run --auto`: "Auto-approve permissions that are not explicitly denied".
  - Effective permissions (`opencode debug agents`): `shell` is `ask` for AG-001, AG-002, AG-003, AG-008 to AG-012, AG-016, AG-017; `edit` is `ask` for the developers and deployment agents.
  - L1: AG-002 (auditor, `edit: deny`, `bash: ask`) wrote a file outside its project directory through its shell (`/tmp/opencode/exp/ag002_shell_probe.txt`).
  - L2 (control without `--auto`): no file was written; the model declined; the only shell call returned `status: error`.
- Root cause: the adapter forces auto-approval for all non-denied permissions. The factory assumed `ask` would stop the run; it does not in non-interactive mode with `--auto`.
- Risk and operational impact: LEVEL B/C operations (shell, writes, production-related actions) run without human approval; the auditor can modify audited artifacts; normative AG-017 limits are unenforced; ADR-002 is violated in practice.
- Proposed correction:
  1. Remove `--auto` from every factory invocation. Non-interactive `ask` must fail closed (verify this behaviour with a controlled probe first and record it).
  2. Replace per-agent frontmatter-only control with an explicit runtime permission profile per agent: auditors and AG-003 get no `shell` and no `edit`; developers get `edit` restricted to the task worktree; AG-016/AG-017 get no production-capable shell.
  3. Record each permission decision (allowed, denied, asked) in the execution evidence.
  4. Add a startup self-check that refuses to run if the resolved permission profile of an agent differs from its normative definition.
- Dependencies: AUD-R5-002 (worktree), AUD-R5-014 (discovery), AUD-R5-015 (environment).
- Acceptance criteria:
  - No factory-initiated `opencode run` contains `--auto`.
  - An auditor probe attempting a shell write fails and leaves no file.
  - An executor probe attempting a shell write outside its worktree fails.
  - Permission profile mismatch aborts the run before invocation.
- Required tests: adapter unit test asserting the command vector; permission probes (auditor shell write denied; developer write outside worktree denied; developer write inside worktree allowed); regression test for L1.
- Status on R5.2: not fixed (adapter unchanged).
- Estimated complexity: M.

### AUD-R5-002 — Agent working directory not isolated (`PWD` inheritance)

- Severity: CRITICAL
- Affected component: `opencode_adapter.py` (`invoke`, environment construction at line 43; subprocess `cwd` at line 52).
- Evidence and source references:
  - Line 43: `env = dict(os.environ)` with no `PWD` override; line 52: `subprocess.run(..., cwd=workdir, env=env)`.
  - L3: same agent and request, subprocess `cwd=/tmp/opencode/audit-proj`; inherited `PWD=/tmp/opencode/head` → the agent's shell reported `/tmp/opencode/head`; with `PWD=/tmp/opencode/audit-proj` → `/tmp/opencode/audit-proj`.
  - Earlier probes from the factory tree reported the wrong directory intermittently.
  - L4: `--standalone` with project-local `.opencode` reported the requested directory.
- Root cause: OpenCode resolves the working directory from `PWD`, which Python's `subprocess` does not update when `cwd=` is used.
- Risk and operational impact: a runtime launched from the factory repository runs project agents in the factory repository; writes can land in the wrong project; project and factory isolation (ADR and `PROJECT_CONTEXT.md`) cannot be relied on.
- Proposed correction:
  1. Set `env["PWD"] = str(cwd)` (absolute, resolved) in every invocation.
  2. Add a canary check before each real run: the adapter executes a no-side-effect probe in the target directory and asserts the reported directory; refuse to run on mismatch.
  3. Evaluate `opencode run --standalone` for executor runs (verified to honour the requested directory when agent definitions are present in that directory) and record the decision.
  4. Store the verified working directory in the execution record.
- Dependencies: AUD-R5-014 (agent definitions must be present in the isolated directory), AUD-R5-015.
- Acceptance criteria: the canary matches the requested directory in 100 of 100 consecutive invocations in a test loop; a deliberately wrong `PWD` is corrected; mismatch aborts before any write.
- Required tests: unit test that the adapter sets `PWD`; integration canary test (no model call required for the canary if the probe is a non-LLM check, otherwise a single benign model call); regression for L3.
- Status on R5.2: not fixed (adapter unchanged).
- Estimated complexity: S.

### AUD-R5-003 — CLI completes tasks without Quality Gate, acceptance or review

- Severity: CRITICAL
- Affected component: `runtime.py` `update_task_status` (358-369) and CLI `task status`.
- Evidence and source references:
  - `update_task_status` validates only the transition table; RUNNING → COMPLETED and REVIEW_REQUIRED → COMPLETED are both in `TASK_TRANSITIONS` (34-44).
  - E5 and E11 (main and R5.2): `python -m orchestration.runtime task status <id> COMPLETED --actor AG-002` completed tasks from RUNNING and REVIEW_REQUIRED, with acceptance criteria present and no gate result.
  - `contracts/task-contract.md` rules 1 to 3 (lines 42-44) and `orchestration/workflows/task-lifecycle.md` ("Completion requires acceptance criteria and Quality Gates").
- Root cause: the generic status setter is reachable for terminal states; completion rules live only in `complete_task`.
- Risk and operational impact: the single most direct bypass of the Quality Gate; any operator or agent that can run the CLI can mark work complete; audit trail records the operator as an agent identity.
- Proposed correction:
  1. Forbid transitions into COMPLETED, REJECTED-to-COMPLETED and REVIEW_REQUIRED via the generic setter; route them through a single `complete_task` function that requires a stored, verified QG result, a stored acceptance verification, and (for REVIEW_REQUIRED) an independent reviewer record.
  2. Remove COMPLETED from the CLI status vocabulary (or require the dedicated command).
  3. Record every completion with the artefact identifiers that justified it.
- Dependencies: AUD-R5-004, AUD-R5-008, AUD-R5-024.
- Acceptance criteria: `task status <id> COMPLETED` fails in every state; completion succeeds only with a stored passing QG result for the same task and commit; completion fails when the stored result is FAIL or BLOCKED.
- Required tests: E5 and E11 as regression tests (expect refusal); positive completion path with a PASS result; completion refused for FAIL, BLOCKED, missing and stale results.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-004 — Quality Gate validator is fail-open; `evaluate_gate` trusted certificate

- Severity: CRITICAL
- Affected component: `orchestration/validators/quality_gate.py` (`collect_defects` 37-84, `evaluate` 111-212, `OPEN_STATUSES` 11); `runtime.py` `evaluate_gate` (540-551).
- Evidence and source references:
  - E6a: empty evidence directory, certificate with `qa_result`, `code_review_result`, `performance_result`, `security_result` all FAIL/BLOCKED and `final_verdict: PASS` → PASS, exit 0. The certificate's result fields are never read.
  - E6b: CRITICAL findings with status `in progress` and `wontfix` → PASS, because only `open`, `failed`, `active`, `pending`, `new`, `unresolved` and empty are open (line 11).
  - `quality_gate.py` lines 47-51: a missing source file (`code_review.json`, `security_findings.json`, `defects.json`, `test_execution.json`) is recorded as `present: False` and produces no rule violation.
  - E6c (main): `evaluate_gate` without `evidence_dir` returned the certificate's `final_verdict` (line 548): PASS with an open CRITICAL defect. R5.2 changes this to FAIL (fixed for that function only).
  - E6d (main and R5.2): evidence with a CRITICAL `in progress` finding returns PASS.
- Root cause: the gate computes verdicts from whatever evidence is present and defaults to PASS for absent sources; the open-status set is a deny-list of closed statuses rather than an allow-list of closed ones.
- Risk and operational impact: a certificate can pass the gate with no evidence and with critical defects; CRITICAL and HIGH blocking rules (quality-contract) can be silently skipped.
- Proposed correction:
  1. Mandatory evidence set per certificate type (code review, security, tests, re-audit when remediated). Missing mandatory source → BLOCKED.
  2. Certificate result fields must agree with the evidence; any FAIL/BLOCKED result field with a PASS verdict → FAIL.
  3. Open-status allow-list: a defect is closed only if its status is in an explicit closed set (`remediated`, `closed`, `verified`, `fixed`, `resolved`, `accepted_risk` with an authorised exception record). Any other status is open.
  4. `evaluate_gate` must always run the validator; a certificate alone is never sufficient.
  5. Persist the full gate result (inputs hashed) and return it to the caller.
- Dependencies: AUD-R5-017 (provenance), AUD-R5-028 (commit binding).
- Acceptance criteria: E6a, E6b, E6d now return FAIL or BLOCKED; a complete PASS evidence set returns PASS; a missing mandatory source returns BLOCKED; existing PROJECT-001 evidence (P2) still returns PASS_WITH_OBSERVATIONS.
- Required tests: unit tests for each rule; regression for E6a, E6b, E6c, E6d; golden test on PROJECT-001 evidence.
- Status on R5.2: `evaluate_gate` fixed for the no-evidence case (E6c); validator unchanged (E6a, E6b, E6d still PASS).
- Estimated complexity: M.

### AUD-R5-005 — Workflow reports COMPLETED falsely; execution ignores stages

- Severity: CRITICAL (on main)
- Affected component: `runtime.py` `run_workflow` (590-610), `start_workflow` (473-483), `workflows` seeds (208-216, 463-470).
- Evidence and source references:
  - E4 (main): one task REVIEW_REQUIRED, dependent task PENDING, run status COMPLETED (line 608).
  - E4e (main): dependency cycle → COMPLETED with zero adapter calls.
  - E4b (main and R5.2): `analysis-only` executed `ag-008-backend-developer`.
  - `current_step` is written once (480) and never updated; `executions.workflow_id` is never set (run_task at 576 passes no workflow id).
- Root cause: `run_workflow` iterates over every non-terminal task of the project in identifier order; it neither reads `definition.steps` nor treats skipped or review-pending tasks as blocking.
- Risk and operational impact: false success is the most harmful reporting error for a factory; the configured lifecycle has no effect; a pilot would report completion without analysis, architecture or quality work.
- Proposed correction:
  1. A workflow run is COMPLETED only when every task of its stages is COMPLETED and every stage gate has a PASS result; otherwise BLOCKED with the reason recorded.
  2. Bind tasks to workflow runs and stages (`workflow_run_id`, `stage`); the runner executes stage by stage in definition order.
  3. Stage completion requires the stage's QG (QG-01..QG-06 mapping).
  4. Unfinished, cyclic or unknown dependencies make the run BLOCKED with a diagnostic (see AUD-R5-022).
- Dependencies: AUD-R5-003, AUD-R5-004, AUD-R5-016, AUD-R5-022.
- Acceptance criteria: E4, E4b, E4e each produce BLOCKED with the correct reason and never COMPLETED; a two-stage run executes stage 1 tasks before stage 2 tasks; `executions.workflow_id` and `tasks.stage` are populated.
- Required tests: regression for E4, E4b, E4e, E4d; ordering test; full happy-path test with mocked adapter returning COMPLETED and gates PASS.
- Status on R5.2: false success fixed (BLOCKED); stage ignorance and binding not fixed (E4b).
- Estimated complexity: L.

### AUD-R5-006 — Human approvals are recorded but never enforced

- Severity: CRITICAL
- Affected component: `runtime.py` `create_approval` (497-507), `approve` (510-518), `consume_approval` (521-529), CLI `approval` (728-745).
- Evidence and source references:
  - `binding_hash` (500) is computed and stored; nothing verifies it.
  - E8: `approval approve APPR-0001 --by any-string-user` → APPROVED with approver `any-string-user`.
  - `consume_approval` has no caller in the runtime (grep: only tests). R5.2 also has no caller.
  - `orchestration/workflows/security-authorization-workflow.md` step 5 and `orchestration/policies/approval-policy.md` require human approval for production deployment, release approval, destructive data and security-policy changes.
- Root cause: approvals are a table, not a gate; no action checks for an approved, unconsumed, matching approval.
- Risk and operational impact: "human approval is mandatory" (ADR-002) is not enforced by any code path; any actor can self-approve.
- Proposed correction:
  1. Define the gated actions (`release.publish`, `deploy.production`, `deploy.staging`, `data.destructive`, `policy.change`) and require a matching approval for each; the action function checks and atomically consumes the approval in the same transaction as the state change.
  2. Bind approvals to project, version, commit, artifact hash, environment, strategy, rollback plan and risks (as normative AG-017 requires) and verify the binding hash.
  3. Approver identity must come from the authenticated operator (AUD-R5-024) and must be an allow-listed human principal, never an agent identifier.
  4. Expiry and single-use enforced.
- Dependencies: AUD-R5-024, AUD-R5-007.
- Acceptance criteria: an action without an approved matching approval is refused; a consumed approval cannot be reused; an approval for another commit or artifact is refused; an agent identifier cannot approve.
- Required tests: E8 as regression (expect refusal when approver is not allow-listed); reuse, binding-mismatch, expiry and agent-approver tests; end-to-end gated release test.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-007 — Release traceability can PASS without approval or with altered artifacts

- Severity: CRITICAL
- Affected component: `orchestration/validators/traceability/traceability.py` (`evaluate` 69-209; `cmd_generate` 232-263); release records under `implementations/PROJECT-001/deployment/`.
- Evidence and source references:
  - T1: PASS certificate, `target_environment: production`, no approval → PASS (exit 0).
  - T2: artifact changed after the manifest was written; manifest has no `artifact_hash` → PASS.
  - T4: certificate content changed (critical open defect added, verdict PASS, no `certificate_hash`) → PASS.
  - T3: `generate` writes a release manifest from a FAIL certificate, exit 0 (`cmd_generate` does not read the verdict).
  - P1: PROJECT-001 release REL-0002 (`RELEASE_MANIFEST.json`) → PASS with no approval; with the only approval record (`APPROVAL.json`, version 0.4.0, commit `26a5af6`) → FAIL on three mismatches.
  - Hash, approval and deployment-plan checks are conditional on field presence (lines 101-104, 116-124, 133-141, 147-173).
- Root cause: integrity checks are opt-in; approval is optional; the generator does not enforce the gate it precedes.
- Risk and operational impact: a release can be presented as validated while it is unapproved, unverified, or built from a failing certificate.
- Proposed correction:
  1. Required fields and required hashes for every release manifest (`artifact_hash`, `quality_certificate_hash`, `source_tree_hash`, `evaluation_id`); absence is FAIL.
  2. Production and staging targets require a matching approval (AUD-R5-006); absence is BLOCKED.
  3. `generate` refuses unless the certificate verdict is PASS or PASS_WITH_OBSERVATIONS and the QG re-validation passes.
  4. Re-evaluate the quality gate inside `validate` (`--evidence-dir` mandatory for release).
  5. Verify the artifact file hash in the manifest's location and record evidence hashes.
- Dependencies: AUD-R5-004, AUD-R5-006, AUD-R5-018, AUD-R5-021.
- Acceptance criteria: T1, T2, T3, T4 each produce FAIL or BLOCKED; REL-0002 without a matching approval is BLOCKED.
- Required tests: regression for T1 to T4 and P1; positive release test with matching approval; hash-tamper tests for certificate and artifact.
- Status on R5.2: not fixed (traceability unchanged).
- Estimated complexity: M.

---

## 3. HIGH findings

### AUD-R5-008 — Audit records and event log mutable; self-audit accepted

- Severity: HIGH
- Affected component: `runtime.py` `record_audit` (409-417), `events` table (`init_db` 150-160), CLI (no audit command).
- Evidence and source references:
  - E7 (main): AG-008 recorded an audit of its own work (accepted); UPDATE changed a PASS to FAIL (rowcount 1); DELETE succeeded; two `AUDIT_RECORDED` events deleted.
  - `contracts/audit-contract.md` rules 1, 2 and 3 (lines 10-14).
  - R5.2 (E7): audit rows are protected by triggers (`audits_no_update`, `audits_no_delete`); a declared executor equal to the auditor is refused; events remain deletable (one deleted); when no executor is declared the independence check is skipped.
- Root cause: the audit table was added without integrity controls; the event table was never protected; independence depends on optional fields.
- Risk and operational impact: audits can be altered or erased; the audit trail cannot evidence independence.
- Proposed correction:
  1. Keep the R5.2 audit triggers; add the same protection to `events` (append-only triggers) and store a hash chain (`prev_hash`, `row_hash`) over events and audits.
  2. Derive the executor from the task or execution record; never accept it from the caller. Refuse audits without a resolvable executor.
  3. Persist audit records only through a single function invoked by the auditor agent's flow (AUD-R5-009).
  4. Periodically export the chain head to an evidence file for external comparison.
- Dependencies: AUD-R5-009, AUD-R5-024.
- Acceptance criteria: UPDATE and DELETE on audits and events fail; a chain verification command detects any tampering; an audit without a resolvable executor is refused.
- Required tests: E7 regression (updated expectations); chain-tamper test; audit without executor refused.
- Status on R5.2: partly fixed (audit rows); events and derived independence not fixed.
- Estimated complexity: M.

### AUD-R5-009 — Native OpenCode delegation and coordination records not implemented

- Severity: HIGH
- Affected component: `runtime.py` `run_task` (556-587) and CLI; schema (no delegation table); AG-001 definition.
- Evidence and source references:
  - The runtime invokes `opencode run --agent <task agent>` directly. AG-001 is never the invoking agent and no subagent call is recorded.
  - `contracts/coordination-contract.md` lines 19-27 define delegation fields (`delegation_id`, `task_id`, `from_agent`, `to_agent`, `requested_at`, `completed_at`, `result`, `evidence`); none exist in code or schema.
  - `integrations/opencode/opencode-integration.md` lists task-tool delegation as "Verified capability"; no evidence exists.
  - `docs/pilots/R5_ACCEPTANCE_CRITERIA.md`: "Agent delegation is verified" is unmet.
  - `orchestration/workflows/agent-delegation.md`: delegation must include task context and expected output; results return to the invoking agent; nested depth defaults to 1.
- Root cause: the runtime was built as a direct invoker, not as a controller of AG-001's delegation.
- Risk and operational impact: the factory's central lifecycle (AG-001 coordination via native subagents) is not demonstrated; delegation cannot be audited; the model of "one owner per task" (coordination rule 1) is not evidenced.
- Proposed correction: adopt a dual model (see recommendations, section 4):
  1. Deterministic stages (QG, traceability, approval) are runtime functions, not agents.
  2. Multi-agent planning and execution use AG-001 as the only invoked primary agent per stage; the runtime records each `task` tool call by parsing the OpenCode event stream (session identifiers, child sessions) into delegation records.
  3. Direct invocation of a subagent by the runtime is allowed only for the independent audit (AG-002/AG-003), recorded as `from_agent=RUNTIME`.
  4. Add a `delegations` table matching the coordination contract.
- Dependencies: AUD-R5-001, AUD-R5-002, AUD-R5-014, AUD-R5-027 (event parsing).
- Acceptance criteria: a controlled scenario where AG-001 delegates to one subagent produces a delegation record with `from_agent`, `to_agent`, session identifiers, result and evidence; an audit of the delegated work is recorded with an independent executor.
- Required tests: controlled delegation probe (one benign model call); parser unit tests on recorded event fixtures; end-to-end delegation record test.
- Status on R5.2: not fixed.
- Estimated complexity: L.

### AUD-R5-010 — Duplicate task assignment under concurrency

- Severity: HIGH
- Affected component: `runtime.py` `update_task_status` (358-369), `assign_task` (372-378), ID generators (241-274), `connect` (51-59).
- Evidence and source references:
  - E13 (main): 80 concurrent assignments on 20 tasks → 21, 21, 23 successes; 3 tasks with duplicate ASSIGNED events.
  - E13 (R5.2): 20, 25, 24, 24, 27 successes across five runs; duplicate events in four of them (0 to 6 tasks).
  - Status is read, checked and then written in separate statements with no conditional predicate and no `BEGIN IMMEDIATE`.
- Root cause: optimistic check without compare-and-set; autocommit reads.
- Risk and operational impact: two agents can own one task (coordination rule 1 violated); duplicated execution and conflicting evidence; repeated work.
- Proposed correction:
  1. Compare-and-set: `UPDATE tasks SET status=? WHERE task_id=? AND status=?` and require `rowcount == 1`.
  2. Run every transition in `BEGIN IMMEDIATE` with the transition check and the event insert in the same transaction.
  3. Replace `max+1` identifiers with `INTEGER PRIMARY KEY AUTOINCREMENT` or a sequence table updated within the transaction.
  4. Add a unique constraint on active execution per task (`UNIQUE` partial index on executions where status = RUNNING and task_id).
- Dependencies: AUD-R5-011, AUD-R5-012.
- Acceptance criteria: E13 yields exactly 20 successful assignments and zero duplicate events in 20 consecutive runs; a second concurrent execution for the same task is refused.
- Required tests: E13 as regression with repetition; unit test of compare-and-set; concurrent run-attempt test.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-011 — Retry accounting, retry limit and correction loop missing

- Severity: HIGH
- Affected component: `runtime.py` `recover_interrupted` (446-460), `run_task` (556-587); schema columns `retry_count`, `max_retries` (123-124).
- Evidence and source references:
  - E12 (main): crash → execution RUNNING, task RUNNING; recover → INTERRUPTED, BLOCKED; resume raised; task left ASSIGNED.
  - E12 (R5.2): resume completes the task (fixed); `retry_count` remains 0 after six failed attempts; six executions recorded; no limit (`max_retries` = 3 is never read).
  - `contracts/coordination-contract.md` rules 3 and 4 (lines 17-19 approx.: retry limit; REJECTED returns with correction assignment).
  - `recover_interrupted` is global and has no liveness check (main 446-460, CLI 855-858).
- Root cause: retry fields were added but no code path updates or enforces them; recovery is a manual, global status flip.
- Risk and operational impact: infinite retries waste resources and obscure failure; a second runtime process can mark live executions INTERRUPTED.
- Proposed correction:
  1. Increment `retry_count` in the same transaction as a failed execution; refuse when `retry_count >= max_retries` and move to BLOCKED with a reason.
  2. Recovery: record a lease (owner process identifier, heartbeat) on RUNNING executions; recover only expired leases, scoped to a project, and never silently.
  3. Implement REJECTED → RUNNING with a correction assignment record (contract rule 4).
  4. Make `max_retries` configurable per task with the contract default of 3.
- Dependencies: AUD-R5-010, AUD-R5-009.
- Acceptance criteria: the seventh attempt is refused; retry_count equals the number of failed attempts; a live lease is not recovered; REJECTED re-run creates a correction record.
- Required tests: E12 retry regression; lease expiry test; recovery of expired lease only; REJECTED correction test.
- Status on R5.2: resume fixed; retry accounting and lease not fixed.
- Estimated complexity: M.

### AUD-R5-012 — Transition and dependency bypasses

- Severity: HIGH
- Affected component: `runtime.py` `assign_task` (372-378), `complete_task` (420-435), `update_task_status` (358-369).
- Evidence and source references:
  - E11 (main and R5.2): `assign_task` moved a FAILED task to ASSIGNED (`TASK_TRANSITIONS[FAILED]` is {PENDING, CANCELLED}).
  - E11 (main and R5.2): `complete_task` moved a REJECTED task to COMPLETED (line 422 accepts REJECTED).
  - E11 (main and R5.2): cancellation without reason accepted (`task-contract.md` rule 4).
  - E10 (main and R5.2): `assign_task` ignored an unmet dependency (`coordination-contract.md` rule 2 requires COMPLETED dependencies before start; assignment is the start of ownership).
- Root cause: transition checks are duplicated per function; the table is not the single authority.
- Risk and operational impact: tasks reach states the contract forbids; dependency ordering can be defeated by assignment.
- Proposed correction: one `transition(task, to, actor, reason, evidence)` function that consults `TASK_TRANSITIONS`, checks dependencies for ASSIGNED/RUNNING, requires a reason for CANCELLED, and writes the event in the same transaction; all other writers call it.
- Dependencies: AUD-R5-003, AUD-R5-010.
- Acceptance criteria: FAILED → ASSIGNED refused; REJECTED → COMPLETED refused; CANCELLED without reason refused; ASSIGNED with unmet dependency refused.
- Required tests: E10 and E11 regressions; a table-driven test that enumerates all state pairs against the contract.
- Status on R5.2: not fixed.
- Estimated complexity: S.

### AUD-R5-013 — Execution evidence misrepresents results and context

- Severity: HIGH
- Affected component: `runtime.py` `run_task` (576-585), `create_execution` (381-389); `opencode_adapter.py` result mapping.
- Evidence and source references:
  - E2 (main): adapter `BLOCKED` recorded as execution FAILED and task FAILED; the BLOCKED reason is lost.
  - E2 (main and R5.2): the adapter receives only the CLI `--prompt`; the task's `objective` and `acceptance_criteria` are not sent.
  - E2 (main): `inputs` stored as `[]` although the prompt is passed as an input (`create_execution` ignores the argument at 381-389); R5.2 stores `["p"]`.
  - `commit` is the project's initial commit (576), not the commit the agent worked on; no change capture (`git` diff, changed files, hashes).
  - `tools_used` is the constant `["opencode.run"]` (581, 584).
  - `contracts/execution-contract.md` rules 2 and 3 and required fields.
- Root cause: evidence fields are populated with placeholders; context assembly is not implemented.
- Risk and operational impact: the agent receives an incomplete brief; evidence cannot show what changed or under what commit; BLOCKED failures look like defects.
- Proposed correction:
  1. Build an execution brief from the task (objective, acceptance criteria, allowed files, dependencies' outputs) and store it as the execution input with a hash.
  2. Map adapter statuses one-to-one (BLOCKED stays BLOCKED).
  3. Capture the working copy's HEAD before and after, the `git diff --name-status`, and the file hashes of changed files.
  4. Parse OpenCode events for tool uses, decisions and errors (AUD-R5-027).
- Dependencies: AUD-R5-002, AUD-R5-027.
- Acceptance criteria: the brief contains the task objective and criteria; BLOCKED remains BLOCKED; the execution record contains before and after commits and a changed-file list; `tools_used` lists tools observed in events.
- Required tests: brief content test; BLOCKED mapping test; change-capture test on a scratch repository; event-parsing test.
- Status on R5.2: inputs stored; other items not fixed.
- Estimated complexity: M.

### AUD-R5-014 — Agent discovery and validation inconsistent; normative IDs rejected; error text lost

- Severity: HIGH
- Affected component: `opencode_adapter.py` (`list_agents` 20-26, `validate_agent` 28-30, `invoke` 32-62); `runtime.py` `run_task` (566-567).
- Evidence and source references:
  - `validate_agent` runs `opencode debug agents` from the runtime's working directory without the environment override; `invoke` runs `opencode run` in the project directory with `OPENCODE_CONFIG_DIR` set. The two can disagree.
  - `opencode debug agents` loads the 18 `ag-*` agents only from a working directory that contains `.opencode/`; `OPENCODE_CONFIG_DIR` set to the factory root or to `.opencode` loads none from a project directory (verified).
  - Normative IDs (`AG-008`) are rejected: `validate_agent('AG-008') == False`; the CLI returns `Agent not available in OpenCode: AG-008` (E14, main and R5.2).
  - Executable IDs in project directories returned `Agent not found` on several calls and later succeeded with no repository change (observed; mechanism not root-caused; OpenCode background service suspected).
  - stderr is used for error text (line 57); OpenCode reports the error on stdout (E14 R5.2 evidence: `Agent not found`, stored as `unknown`).
- Root cause: agent identity is not mapped between the normative catalogue and OpenCode; discovery is tied to the working directory and to hidden service state; errors are read from the wrong stream.
- Risk and operational impact: runs fail or succeed unpredictably; failures are misdiagnosed; the preflight "opencode_agents" check (AUD-R5-025) passes while invocation fails.
- Proposed correction:
  1. Maintain an explicit mapping `AG-xxx -> ag-xxx-name` derived from the normative catalogue (single source) and validate it at startup.
  2. Validate agent presence in the same context as invocation (same working directory, same environment), by running the discovery command in the target directory with the same environment.
  3. Materialise the agent definitions into the isolated working directory (or use a dedicated config directory verified to contain them) before each run; record their hashes.
  4. Read error text from stdout JSON events and stderr; classify `Agent not found` as configuration error (BLOCKED), not execution failure.
- Dependencies: AUD-R5-002, AUD-R5-033.
- Acceptance criteria: `task run` with `AG-008` resolves to `ag-008-backend-developer`; the same discovery context is used for validation and invocation; `Agent not found` is reported as BLOCKED with the message; 20 consecutive discoveries in the target directory agree.
- Required tests: mapping test; discovery-context test; error classification test with recorded event fixtures.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-015 — No filesystem, network or secret boundary for executors

- Severity: HIGH
- Affected component: `opencode_adapter.py` (line 43 environment; `--auto`), agent permissions, project layout.
- Evidence and source references:
  - Environment inherited in full (line 43); no filtering.
  - L1: an auditor's shell wrote an absolute path outside the project.
  - `.gitignore` excludes `.env`, but the process environment is not filtered.
  - Task prompts and repository contents reach agents with shell access (prompt-injection exposure).
- Root cause: no sandbox; no environment allowlist; trust in agent self-restraint.
- Risk and operational impact: secrets in the operator's environment are visible to agents and can be exfiltrated via shell; agents can modify files outside the project; prompt injection from repository content can drive actions.
- Proposed correction:
  1. Environment allowlist for agent processes (`PATH`, `HOME` scoped, `LANG`, `OPENCODE_*` required keys only); never pass tokens or cloud credentials.
  2. Run executors in an OS-level sandbox (container, bubblewrap or equivalent) with a writable bind mount only for the task worktree and read-only access to the normative catalogue.
  3. Network egress disabled by default; explicitly enabled per task with approval.
  4. Treat repository text and task prompts as untrusted: separate instruction and data channels in the brief; forbid agents from reading `.env*` (already `ask`, now enforced).
- Dependencies: AUD-R5-001, AUD-R5-002.
- Acceptance criteria: a probe reading a planted secret environment variable fails; a write outside the worktree fails in the sandbox; egress probe fails.
- Required tests: sandbox boundary tests; environment allowlist test; planted-secret probe; prompt-injection fixture (a repository file instructing deletion must not execute).
- Status on R5.2: not fixed.
- Estimated complexity: L.

### AUD-R5-016 — Project lifecycle and workflow stages not bound to tasks

- Severity: HIGH
- Affected component: `runtime.py` `update_project_status` (310-319), `PROJECT_TRANSITIONS` (19-32), workflow and task binding (no columns), CLI.
- Evidence and source references:
  - `update_project_status` is not called by any CLI command or workflow path; projects remain REGISTERED.
  - Tasks carry no stage or workflow identifier (main); R5.2 adds `stage` but the CLI does not set it (E4b remains).
  - `orchestration/workflows/project-lifecycle.md`: "No stage may be marked complete without evidence" and "Independent audit before release".
- Root cause: the project state machine was implemented but not wired.
- Risk and operational impact: the factory cannot report where a project is in its lifecycle; stage completion has no meaning.
- Proposed correction: drive project status from workflow runs (on stage completion with gates PASS); expose `project advance` only through the gated path; bind tasks to stages at creation.
- Dependencies: AUD-R5-005.
- Acceptance criteria: a registered project moves ANALYSIS → ... → COMPLETED only through gated workflow transitions; status history is in events.
- Required tests: lifecycle test; illegal transition refused; CLI status reflects state.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-017 — Quality evidence is self-reported and unverifiable

- Severity: HIGH
- Affected component: `quality_gate.py` `collect_defects` (37-84), reaudit check (181-191); evidence files under `implementations/PROJECT-001/quality/evidence/`.
- Evidence and source references:
  - `reaudit.json` is `{"performed": true}`: no auditor, commit, artefact or timestamp.
  - `test_execution.json` is `{"status":"PASS","failed_tests":[]}`: no test identifiers, counts or runner output reference.
  - `security_findings.json` is `{"verdict":"PASS_WITH_OBSERVATIONS","findings":[]}`: no scan tool, version or scope.
  - No hash of the evidence is recorded; the gate does not check who produced the evidence or from which commit.
  - P2: the gate returns PASS_WITH_OBSERVATIONS from these inputs; the verdict is only as strong as the evidence.
- Root cause: evidence schema lacks provenance fields; the gate accepts any JSON with the expected keys.
- Risk and operational impact: a PASS can be produced by writing a file; re-audit and test claims cannot be verified.
- Proposed correction:
  1. Evidence envelope with `producer` (agent identifier and session), `commit`, `created_at`, `inputs_hash`, `tool` and `tool_version`, and a content hash recorded by the runtime (not the producer).
  2. Test evidence must reference test identifiers and counts parsed from the runner output.
  3. Re-audit evidence must name an independent auditor distinct from the executor.
  4. The gate verifies the envelope and the hashes; missing provenance → BLOCKED.
- Dependencies: AUD-R5-004, AUD-R5-008, AUD-R5-028.
- Acceptance criteria: evidence without provenance is BLOCKED; a modified evidence file is detected; re-audit by the executor is refused.
- Required tests: provenance tests; tamper test; independence test for re-audit; migration of PROJECT-001 evidence to the envelope (re-issued, not edited in place).
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-018 — Traceability Quality Gate integration broken in the CLI; its test passes vacuously

- Severity: HIGH
- Affected component: `traceability.py` line 178 (`sys.path.insert(0, str(Path(__file__).resolve().parents[2]))`); `tests/orchestration/test_traceability.py` `test_r1_integration` (289-303).
- Evidence and source references:
  - `parents[2]` of `traceability/traceability.py` is the `orchestration/` directory; the import `orchestration.validators...` then fails: `Quality Gate Runtime integration failed: No module named 'orchestration'` (T5). With `python3 -m orchestration.validators.traceability` it works.
  - `test_r1_integration` asserts only `returncode != 0`, so the import failure satisfies it.
- Root cause: wrong parent index; test asserts a broad failure condition.
- Risk and operational impact: the release gate silently cannot consult R1 when invoked as documented; the test suite reports success.
- Proposed correction: use `parents[3]` or import relative to the package; assert the specific expected verdict and rule in the test; add a test that runs the CLI as a script.
- Dependencies: AUD-R5-007, AUD-R5-019.
- Acceptance criteria: T5 returns the R1 verdict (PASS_WITH_OBSERVATIONS for PROJECT-001 evidence); the test checks the verdict string and the violated rule.
- Required tests: script-mode CLI test; verdict-specific assertions.
- Status on R5.2: not fixed (traceability unchanged).
- Estimated complexity: S.

### AUD-R5-019 — Declared test command covers 5 of 17 test modules; several tests vacuous

- Severity: HIGH
- Affected component: `tests/run_all.py` (6-12); `tests/contracts/test_state_transitions.py` (1-17); `tests/orchestration/test_runtime.py` (119-122, 158-167, 169-180, 277-279, 300-312, 314-327).
- Evidence and source references:
  - `run_all.py` invokes 5 files and reports `ALL TESTS PASSED`; 115 test functions exist across 17 modules; the declared command executes 37 test PASS lines.
  - Omitted modules pass when run directly (Quality Gate 14, traceability 20, structure 22, schema modules 18, PROJECT-001 unittest), so the omission hides coverage rather than hiding failures.
  - `test_state_transitions.py` tests a local copy of the table and never imports the runtime (tautology).
  - `test_blocked_by_critical_defect` never calls the gate; `test_blocked_by_missing_approval` asserts APPROVED; `test_real_opencode_adapter_invocation` returns silently unless COMPLETED; `test_closure_requires_conditions` checks a dictionary entry; `test_opencode_adapter_contract` tests a fake.
  - No test covers any of the adversarial cases in section 12 of the audit report.
- Root cause: no single test registry; tests written to pass rather than to specify.
- Risk and operational impact: "tests PASS" is cited as release evidence (R1 to R5.1 records) while critical behaviour is untested.
- Proposed correction:
  1. One discovery-based runner (`python3 -m unittest discover` or pytest) for all modules; the runner fails if any module is not discovered.
  2. Replace tautological and vacuous tests with specification tests that import the runtime and assert outcomes; remove silent `return` paths (use skip with reason, counted in the report).
  3. Add the adversarial suite (E1 to E14, T1 to T5, P1, P2 as golden tests) with deterministic fake adapters; keep real OpenCode tests in a separate, opt-in marker.
  4. Report counts per module in the output.
- Dependencies: none (should land first in R5.2).
- Acceptance criteria: the declared command runs every test module; no test passes when its asserted behaviour is absent (verified by mutation checks on three runtime functions); skipped tests are reported.
- Required tests: runner self-test (fails when a module is removed); mutation checks.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-020 — Remediation records claim capabilities not reproduced

- Severity: HIGH
- Affected component: `docs/audits/R5.1_FINAL_AUDIT.md`, `docs/audits/R5_PREPARATION_AUDIT.md`, `docs/audits/R3_FINAL_AUDIT.md`, `PROJECT_PROGRESS.md` (lines 126-133), `PROJECT_HANDOFF.md`, `CHANGELOG.md` (R5.1 section).
- Evidence and source references:
  - R5.1 "Task run end-to-end: PASS (TASK_RUN_OK)": not reproducible from a created task (E1, E14).
  - R5.1 "Workflow execution: PASS": reports false success (E4, E4e).
  - R5.1 "Recovery: PASS": no resume on main (E12).
  - R5.1 "SQLite migration v2": not reachable on main (E9).
  - R5.1 "Added record_audit and complete_task enforcement": partial (E5, E7).
  - R5 preparation: "Agent delegation is verified" acceptance criterion: no delegation exists.
- Root cause: audit records were written from test-suite results that did not exercise these paths (see AUD-R5-019).
- Risk and operational impact: decisions (including the decision to proceed to pilot) rest on unverified claims.
- Proposed correction: add a "reproduction" section to every audit record listing the exact commands and the observed output; mark claims not reproduced as NOT VERIFIED; correct the R5.1 record with a dated addendum (no silent edits).
- Dependencies: AUD-R5-019.
- Acceptance criteria: each capability claim in the R5.x records has a reproduction command and output; the addendum exists.
- Required tests: documentation check that every "PASS" claim names a reproduction command (manual review gate in the audit template).
- Status on R5.2: not fixed (records untouched).
- Estimated complexity: S.

### AUD-R5-021 — PROJECT-001 release evidence misbound and not reproducible

- Severity: HIGH
- Affected component: `implementations/PROJECT-001/deployment/RELEASE_MANIFEST.json`, `APPROVAL.json`; release artefact location.
- Evidence and source references:
  - `RELEASE_MANIFEST.json`: REL-0002, version 1.0.0, commit `6404e4d…`, `artifact` = `/tmp/scratchpad/project001-deploy/artifact.zip` (outside the repository); the artefact exists in scratch and is not in version control.
  - `APPROVAL.json`: APPR-0001, version 0.4.0, commit `26a5af6…`, artifact `artifact.zip`, environment `staging-local`, approved_by `human`; mismatches the release (P1).
  - The certificate hash (`1d484ddd…`) and tree hash (`e3bad5fd…`) match the repository (verified).
- Root cause: release artefacts are generated outside the repository; approvals are reused across versions.
- Risk and operational impact: the R4 release cannot be reproduced from a clean clone; the only approval does not cover the release.
- Proposed correction: regenerate the release artefact from a clean export of commit `6404e4d` inside the repository's release directory (or an evidence store) with its hash; create a new approval bound to version 1.0.0 and commit `6404e4d` after human review; keep APPR-0001 as historical.
- Dependencies: AUD-R5-006, AUD-R5-007.
- Acceptance criteria: the manifest's artefact is reproducible from a clean clone and its hash matches; traceability validation with the new approval returns PASS; the old approval is marked superseded.
- Required tests: reproduction script; traceability validation with the new approval.
- Status on R5.2: not applicable (PROJECT-001 unchanged).
- Estimated complexity: S (after AUD-R5-006 exists).

---

## 4. MEDIUM findings

### AUD-R5-022 — Reference and dependency integrity gaps

- Severity: MEDIUM
- Affected component: `runtime.py` `create_task` (322-331), `register_project` (288-296), `create_execution` (381-389), schema foreign keys.
- Evidence and source references: E10 (nonexistent repository path accepted; duplicate registration of the same repository accepted; execution for nonexistent task accepted; unknown dependency identifier accepted). E4d: missing dependency crashes the run. E4e: cycle undetected on main (detected on R5.2).
- Root cause: no referential validation at write time; `executions.task_id` has no foreign key.
- Risk: orphan executions; crashed workflow runs; cyclic plans that never start.
- Proposed correction: validate repository existence and Git work tree; unique active registration per repository path; foreign keys on `executions.task_id`, `events.project_id`; reject unknown and cyclic dependencies at creation; add `ON DELETE RESTRICT` semantics.
- Dependencies: none.
- Acceptance criteria: E10 cases refused; E4d and E4e refused at creation with a diagnostic.
- Required tests: referential integrity tests; cycle detection tests.
- Status on R5.2: cycle detection at run time only.
- Estimated complexity: S.

### AUD-R5-023 — Contract and schema field mismatches

- Severity: MEDIUM
- Affected component: `schemas/task.schema.json`, `schemas/execution.schema.json`, `schemas/audit.schema.json`; `runtime.py` tables (`init_db` 90-216).
- Evidence and source references: task schema requires `description`, `assigned_agent`, `quality_gates`; the table has `objective`, `agent_id` and (main) no `quality_gates`. Execution schema requires `decisions` and `outputs` persisted. Audit contract requires `audited_artifacts`; the table has `artifacts`. Coordination delegation fields absent (AUD-R5-009).
- Root cause: schemas and tables evolved separately; no contract test links them.
- Risk: contract-conformant tooling cannot read runtime data; evidence fields appear present but are empty.
- Proposed correction: one mapping document and a conformance test that validates runtime records against the JSON schemas after each operation; align names (or document aliases in one place).
- Dependencies: AUD-R5-013, AUD-R5-009.
- Acceptance criteria: a conformance test validates a created task, execution and audit against the schemas without errors.
- Required tests: schema conformance tests on records produced by the runtime.
- Status on R5.2: partly (quality_gates column added).
- Estimated complexity: S.

### AUD-R5-024 — Operator identity and authorisation absent

- Severity: MEDIUM
- Affected component: CLI actor and approver arguments (`--actor` default `AG-001`; `approval approve --by`); database location (`runtime.py` line 14).
- Evidence and source references: E8 (approver is any string); CLI `task status --actor` accepts any identifier, including an agent identifier, as the completing actor; the default database is `orchestration/runtime/runtime.db` inside the repository working tree (gitignored) with default file permissions.
- Root cause: no identity model; no authorisation policy; trust placed in the CLI caller.
- Risk: impersonation; loss of accountability; anyone with file access can edit state.
- Proposed correction: operator identity from the OS user (`getpass.getuser()` plus a human-principal allow-list in a repository file reviewed under change control); reject agent identifiers as human actors; restrict database file permissions (0600) and move the default database outside the repository; state the trust model in the architecture document.
- Dependencies: AUD-R5-006.
- Acceptance criteria: an agent identifier cannot approve or complete; an unlisted OS user cannot approve; the database file is not world-readable.
- Required tests: identity tests; file-permission test.
- Status on R5.2: not fixed.
- Estimated complexity: S.

### AUD-R5-025 — Preflight reports PASS for unverified checks

- Severity: MEDIUM
- Affected component: `orchestration/preflight/r5_preflight.py`, `tests/orchestration/test_runtime.py` (line 323).
- Evidence and source references: lines 92-98 ("project isolation") check only that two directories exist; lines 27-30 ("repository") check only that `.git` exists; lines 49-59 check agents from the runtime's working directory, not the target; line 106 hard-codes `opencode-go/qwen3.8-flash`, contrary to ADR-003 and `integrations/opencode/opencode-integration.md`; line 323 hard-codes the same model in a test.
- Root cause: checks are existence checks labelled as verification.
- Risk: preflight PASS is cited as readiness evidence (R5 preparation audit) while isolation and discovery are not verified.
- Proposed correction: replace with behavioural checks: canary working directory (AUD-R5-002), agent discovery in the target context (AUD-R5-014), permission profile check (AUD-R5-001), and a configurable model from `opencode.json` or environment; rename any check that is only an existence test.
- Dependencies: AUD-R5-002, AUD-R5-014.
- Acceptance criteria: the preflight fails when the canary or discovery fails; no hard-coded model.
- Required tests: preflight negative tests (broken PWD, missing agent definitions).
- Status on R5.2: not fixed.
- Estimated complexity: S.

### AUD-R5-026 — Documentation contradictions and stale state

- Severity: MEDIUM
- Affected component: root context files and records (see audit report section 14 for exact lines).
- Evidence and source references: `PROJECT_HANDOFF.md` line 22 and `PROJECT_STATUS.md` lines 13-14 (merge pending; main already merged); `PROJECT_PROGRESS.md` lines 75 and 86 (wrong commit for v0.6.1-r1); `PROJECT_CONTEXT.md` line 7 and `CHANGELOG.md` line 80 (historical published commit presented as current); `PROJECT_DECISIONS.md` lines 39, 51, 61, 73 (duplicate and misordered ADR identifiers); ADR-001 and `state-management.md` (repository as source of truth) versus SQLite runtime database; `integrations/opencode/opencode-integration.md` ("task tool delegation" as verified); `docs/audits/R1_FINAL_AUDIT.md` line 20 (16 tests; file has 14).
- Root cause: records updated by hand after events; no reconciliation step.
- Risk: incorrect decisions and onboarding of future sessions from stale state (AI_START_HERE requires reading these files).
- Proposed correction: reconcile all context files in R5.2 (status, handoff, progress, decisions); renumber the duplicate ADR as ADR-007 with a dated note (no silent renumbering of historical entries); add a decision record on the source-of-truth model (ADR-007 or ADR-008); correct the R1 test count with an addendum.
- Dependencies: AUD-R5-020.
- Acceptance criteria: the context files agree with `git log`, tags and the R5.2 decision; no duplicated ADR identifiers.
- Required tests: a documentation consistency check (script) comparing tags and ADR identifiers.
- Status on R5.2: not fixed.
- Estimated complexity: S.

### AUD-R5-027 — Adapter process control and result classification

- Severity: MEDIUM
- Affected component: `opencode_adapter.py` (`invoke` 32-62; `subprocess.run` 52; classification 53; `TimeoutExpired` 61-62).
- Evidence and source references: the timeout kills only the direct child (the OpenCode client); the background service and tool subprocesses are not terminated (design risk, not measured). Classification uses the exit code only (53); the adapter never parses OpenCode events (no error event detection, no tool-use capture). Output is returned as an unbounded string.
- Root cause: process management delegated to the client; no event parsing.
- Risk: runaway tool processes after timeout; success reported for runs that emitted errors (only if the client exits 0); unbounded evidence size.
- Proposed correction: start the agent in its own process group and kill the group on timeout; parse the JSON event stream: any `error` event makes the run FAILED or BLOCKED; cap evidence size and store the raw stream as a file with its hash.
- Dependencies: AUD-R5-013, AUD-R5-014.
- Acceptance criteria: a timeout leaves no child processes; an error event yields a non-COMPLETED status even with exit 0; evidence is stored as a file with a size limit.
- Required tests: timeout test with a fake long-running command; error-event fixture test.
- Status on R5.2: not fixed.
- Estimated complexity: M.

### AUD-R5-028 — Quality certificate not bound to the audited commit by the gate

- Severity: MEDIUM
- Affected component: `quality_gate.py` (no commit check); `contracts/quality-contract.md` ("Certificates are valid only for the audited commit").
- Evidence and source references: the R1 evaluation never reads the repository; certificates with any `commit` value pass if their other fields are consistent. Only R2 checks commit equality, and only with `--repo` and both commit fields present.
- Root cause: gate and traceability are separate; the gate has no repository context.
- Risk: a certificate from an earlier commit can be presented for a later release.
- Proposed correction: the gate requires `--repo` and verifies that the certificate commit exists and equals the commit under evaluation; the runtime passes the commit from the task's execution record.
- Dependencies: AUD-R5-004, AUD-R5-017.
- Acceptance criteria: a certificate for another commit is refused by the gate.
- Required tests: stale certificate test on a scratch repository.
- Status on R5.2: not fixed.
- Estimated complexity: S.

### AUD-R5-029 — Uncontrolled concurrent state changes and branch switching during the audit

- Severity: MEDIUM
- Affected component: repository change control (process), `orchestration/runtime/runtime.py` working copy.
- Evidence and source references: during this audit, the working tree on `main` acquired an uncommitted 72-line change to `runtime.py` (a "Migration 3 / R5.2" draft); the checked-out branch later became `feature/r5.2-workflow-integrity` at `5bd7187`. `AGENTS.md` requires "Keep Git clean at stage closure" and "Inspect before modifying". No audit record exists for these changes. The audit did not modify the repository (verified: only the four documents were added).
- Root cause: parallel work in the same working tree without a worktree or branch discipline.
- Risk: audited baseline and implemented state diverge; findings may be attributed to the wrong version; unreviewed code enters a branch.
- Proposed correction: use one git worktree per branch (`git worktree add`), require clean status before any audit, and record the audited commit in every audit record. Gate any merge on the re-audit of the exact commit.
- Dependencies: none.
- Acceptance criteria: every audit record names the commit it audited; no uncommitted changes exist at audit start (checked by a script).
- Required tests: audit-start check script.
- Status on R5.2: not applicable (process).
- Estimated complexity: S.

---

## 5. LOW findings

### AUD-R5-030 — Traceability verdict never reports BLOCKED

- Severity: LOW
- Affected component: `traceability.py` (`evaluate`, verdict logic 191-199).
- Evidence: the BLOCKED mapping tests whether the rule text contains `CRITICAL`; no rule text contains it, so the verdict is FAIL for every violation.
- Proposed correction: give each rule a severity and map CRITICAL to BLOCKED explicitly.
- Dependencies: AUD-R5-007.
- Acceptance criteria: a rule classified CRITICAL yields BLOCKED with exit code 2.
- Tests: verdict mapping tests.
- Complexity: S.

### AUD-R5-031 — ID generation by full scan; unbounded list queries

- Severity: LOW
- Affected component: `runtime.py` `project_id`, `task_id`, `execution_id`, `approval_id` (241-274); `list_*` functions (300-339, 438-443, 532-537).
- Evidence: each ID is computed by scanning the whole table; list functions are unbounded. Not measured under load.
- Proposed correction: database-generated identifiers within transactions (see AUD-R5-010); pagination for list commands.
- Dependencies: AUD-R5-010.
- Acceptance criteria: identifier generation is O(1) and collision-free under concurrency; list commands accept `--limit`.
- Tests: concurrency and pagination tests.
- Complexity: S.

### AUD-R5-032 — No structured logs, metrics, backup or retention

- Severity: LOW
- Affected component: operations; `runtime.py` (no logging); `.gitignore`.
- Evidence: the only operational record is the `events` table and stored stdout; no backup or export command; no retention policy.
- Proposed correction: structured JSON logs for each command and execution; `runtime backup` (SQLite online backup API) and `runtime export` to an evidence directory; a documented retention policy.
- Dependencies: AUD-R5-008 (hash chain).
- Acceptance criteria: a backup restores to an identical event count and chain head; logs include execution identifiers.
- Tests: backup and restore test.
- Complexity: M.

### AUD-R5-033 — OpenCode and runtime versions not pinned

- Severity: LOW
- Affected component: deployment and configuration; `opencode.json`; `integrations/opencode/opencode-integration.md`.
- Evidence: the audit used OpenCode `v2.2.5`; nothing in the repository records or enforces the version; `opencode.json` has no version constraint; the preflight does not check it.
- Proposed correction: record the tested OpenCode version in `integrations/opencode/` and in the preflight; refuse to run on an untested version unless overridden with a recorded decision.
- Dependencies: AUD-R5-025.
- Acceptance criteria: preflight reports the version and fails on an untested version.
- Tests: version gate test.
- Complexity: S.

### AUD-R5-034 — Duplicated code, dead code and monolithic runtime

- Severity: LOW
- Affected component: `runtime.py` (863 lines on main; more than 1,300 lines on R5.2).
- Evidence: workflow seeding duplicated (`init_db` 208-216 and `seed_workflows` 463-470); `migrate()` unused on main (66-88); `consume_approval` unused; near-identical ID generators; the file mixes persistence, state rules, adapter calls and CLI.
- Proposed correction: split into modules (`state`, `store`, `adapter_bridge`, `cli`); remove dead code once AUD-R5-006 and AUD-R5-010 are implemented.
- Dependencies: after the functional fixes, to avoid churn.
- Acceptance criteria: no duplicated seeding; the CLI module contains no state logic.
- Tests: existing suite plus import tests.
- Complexity: M.

---

## 6. Dependency graph (short form)

- AUD-R5-019 (test runner) → every other item (regression coverage).
- AUD-R5-002 (PWD) and AUD-R5-001 (`--auto`) → AUD-R5-014, AUD-R5-015, AUD-R5-025, AUD-R5-009.
- AUD-R5-003, AUD-R5-004, AUD-R5-006 → AUD-R5-005, AUD-R5-007, AUD-R5-008.
- AUD-R5-010 (atomic transitions) → AUD-R5-011, AUD-R5-012.
- AUD-R5-005 → AUD-R5-016.
- AUD-R5-009 (delegation) → AUD-R5-008 (executor from delegation), AUD-R5-013.

## 7. Required regression set (minimum for R5.2)

The following must exist and pass before R5.2 closure: E1, E2 (BLOCKED mapping only), E4, E4b, E4d, E4e, E5, E6a, E6b, E6c, E6d, E7, E8, E9, E10, E11, E12, E13 (repeated 20 times), E14 (normative ID mapping), T1, T2, T3, T4, T5, P1, P2 (golden), L1 and L3 as opt-in real-OpenCode probes with recorded outputs, and the adversarial items from AUD-R5-001 to AUD-R5-003.
