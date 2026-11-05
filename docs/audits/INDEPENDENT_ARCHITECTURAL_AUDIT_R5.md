# INDEPENDENT_ARCHITECTURAL_AUDIT_R5

## 0. Audit metadata

- Audited baseline: branch `main`, commit `d3c9cde` (`docs: record R5.1 remediation closure`), tag `v0.6.5-r5.1` at `e2c17d4`.
- Git state at audit start: branch `main`, working tree clean (`git status`: "nothing to commit, working tree clean").
- Git state during the audit (observed, not caused by this audit): the working tree of `orchestration/runtime/runtime.py` was modified by another session (an uncommitted "Migration 3 / R5.2" draft), and the checked-out branch later became `feature/r5.2-workflow-integrity` at commit `5bd7187`. This audit did not modify, commit, revert or switch anything. See section 16.
- Method: static review of the committed baseline; execution of the declared test suite and of the omitted test modules in a clean `git archive` export of `d3c9cde`; disposable-database experiments (`/tmp/opencode/exp/run_exp.py`, outside the repository); disposable Git repositories for traceability tests; a small number of benign, scratch-directory OpenCode agent probes (about 14 model calls in total, all in `/tmp/opencode`).
- Line numbers refer to `d3c9cde` unless marked "R5.2" (commit `5bd7187`).
- Scope limits: no production or project databases were touched; no real pilot project was created; no external repository was modified; nothing was deployed. PROJECT-001 was reviewed at a sampling level only (see section 9).

## 1. Executive summary

AI-Project-Factory has a real and well-organised foundation: a normative catalogue of 18 agents whose executable OpenCode definitions agree on mode, domain and permissions, a deterministic Quality Gate evaluator that reproduces the R4 record when given the right evidence directory, a hash/commit traceability validator that works when its fields are present, and an OpenCode adapter that can actually run a factory agent and obtain a completed model response.

The orchestration layer that is supposed to tie these together does not yet enforce the lifecycle the project describes. On the audited baseline (`main`, `d3c9cde`):

- Human approvals, Quality Gate results, acceptance verification, auditor independence and release approval are recorded but not enforced. Several of them can be bypassed with one CLI command.
- Workflow runs report `COMPLETED` when tasks are unfinished, when dependencies cycle, or after reviews that were never completed.
- The OpenCode adapter disables the approval gates (`--auto` turns every `ask` into allow), and it does not reliably execute agents in the requested project directory, because OpenCode takes the working directory from the inherited `PWD` variable.
- Native OpenCode subagent delegation (AG-001 via the task tool) is not implemented or demonstrated. The runtime invokes each agent directly with `--agent`.
- Migration v2 is not reachable from the runtime, so an existing R3 database cannot complete an execution.
- Several R5.1 claims ("task run end-to-end PASS", "workflow execution PASS", "recovery PASS", "SQLite migration v2") are not reproducible on the baseline.

The R5.2 branch (`feature/r5.2-workflow-integrity`, `5bd7187`, not the audited baseline) fixes a substantial part of the workflow and state defects: pending tasks can run, unfinished workflows are marked `BLOCKED`, cycles are detected, resume works, the migration is wired, audit rows are immutable and independence is enforced when the executor is declared, and boolean acceptance is rejected. It does not fix the most serious issues: the `--auto` gate bypass, the `PWD` isolation defect, the CLI `task status … COMPLETED` bypass, the fail-open Quality Gate validator, unenforced approvals, the release gate, the concurrency race, or the adapter's agent-resolution path.

Overall verdict: **PARTIALLY IMPLEMENTED. Components are real; the enforced lifecycle is not.** Pilot readiness: **NOT_READY** (see `R5_PILOT_READINESS_ASSESSMENT.md`).

Findings (baseline `main`, detailed in `R5_REMEDIATION_BACKLOG.md`): **7 CRITICAL, 14 HIGH, 8 MEDIUM, 5 LOW** (34 findings).

## 2. Architecture reconstructed from project definitions

Normative sources read: `PROJECT_CONTEXT.md`, `AI_START_HERE.md`, `PROJECT_STATUS.md`, `PROJECT_HANDOFF.md`, `PROJECT_DECISIONS.md` (ADR-001 to ADR-006), `PROJECT_MAP.md`, `PROJECT_PROGRESS.md`, `SESSION_LOG.md`, `CHANGELOG.md`, `README.md`, `AGENTS.md`; `agents/` (18 normative definitions) and `.opencode/agents/` (18 executable definitions); `contracts/` (agent, task, execution, audit, coordination, quality, development-task, development-execution-report, devops); `orchestration/workflows/`, `orchestration/policies/`, `orchestration/state-management/`, `integrations/opencode/`; `docs/audits/` (F0 to F5, R1 to R5.1); `docs/pilots/` (R5 plan, runbook, acceptance criteria, agent matrix); `tests/`.

Intended lifecycle (from `PROJECT_CONTEXT.md`, `orchestration/workflows/project-lifecycle.md`, `quality-gate-flow.md`, `coordination-contract.md`):

```
USER REQUIREMENT
 -> AG-001 coordination (tasks, dependencies, assignment)
 -> analysis (AG-004..AG-007) -> QG-01/QG-02
 -> development (AG-008..AG-011) -> QG-03
 -> quality (AG-012..AG-015) -> AG-002 independent audit -> QG-04 (AG-003 for LEVEL B/C)
 -> release preparation (AG-016..AG-018) -> QG-05 -> human approval -> QG-06 -> deployment
 -> persistent state and evidence at every step; audits immutable; corrections and re-audit
```

Architecture actually present on `main`:

| Layer | Present | Behaviour |
|---|---|---|
| Normative agents (`agents/`) | Yes | 18 definitions, consistent with executable definitions |
| Executable agents (`.opencode/agents/`) | Yes | Load in OpenCode from the factory directory tree |
| Persistent runtime (`orchestration/runtime/runtime.py`) | Partly | SQLite tables, CLI, simple state checks; many invariants are not enforced |
| OpenCode adapter (`opencode_adapter.py`) | Partly | Real subprocess invocation; permissions and working directory are not isolated |
| Quality Gate (`orchestration/validators/quality_gate.py`) | Partly | Deterministic verdict over well-formed JSON evidence; fail-open for missing or unusual inputs |
| Traceability (`orchestration/validators/traceability/traceability.py`) | Partly | Hash/commit/tree checks when fields are present; approval and hashes optional |
| Native OpenCode delegation (AG-001 -> subagents) | No | Not implemented; not demonstrated |
| Human approval channel | No | Free-text approver; no enforcement |
| Independent audit flow | No | Audit table exists; no flow invokes AG-002 and gates release on it |
| Release/deployment execution | No | Only F5 demo scripts; no runtime-gated deployment |

## 3. Current implementation assessment

Classification of capabilities (evidence in brackets):

- **Genuinely functional**: normative and executable agent catalogue and loading [`opencode debug agents`: 18 `ag-*` agents, correct modes]; real agent execution through OpenCode with a completed model response [PROBE_OK probe; AG-002 shell probe]; deterministic Quality Gate verdict for well-formed evidence [R4 evidence reproduces `PASS_WITH_OBSERVATIONS`]; hash/commit/tree checks when the fields are present; SQLite persistence basics and project/task CRUD; the declared test runner passes [`tests/run_all.py`: 37 tests, ALL TESTS PASSED].
- **Partially functional**: task lifecycle (transitions exist but are bypassed in several places); workflow execution (runs tasks sequentially, ignores stages); OpenCode invocation (works, but isolation and permission gating fail); Quality Gate (computes a verdict but does not require evidence or provenance); traceability (checks only supplied fields).
- **Simulated / manual / documented only**: independent audit flow; native subagent delegation; human approval; release approval; stage-by-stage QG-01..QG-06 gating; rollback and deployment through the runtime; "agent delegation verified" (R5 acceptance criterion); the R5 "controlled pilot" evidence (only the AG-001 controlled invocation exists).
- **Not implemented**: delegation records; retry accounting; correction loop after REJECTED; per-task isolated working copy; diff/change capture; authenticated operator identity; event-log integrity.

## 4. Agent architecture assessment

Verified:

- The 18 normative agents (`agents/{management,analysis,development,quality,delivery}/`) and the 18 executable agents (`.opencode/agents/`) agree on identifier, mode (AG-001 `primary`; all others `subagent`) and domain.
- Permission sections of the normative definitions match the executable frontmatter (for example AG-002: `bash: ask`, `edit: deny`, `write: deny`, `task: deny`; AG-017: `bash/edit/write: ask`; AG-008: `edit/write/bash: ask`, `task: deny`). The executable permissions are internally consistent with the normative definitions.
- OpenCode's effective permission table (`opencode debug agents`) confirms that `shell` and `edit` are `ask` for coordinators and developers and that `edit` is `deny` for AG-002, AG-003, AG-013, AG-014 and AG-015.

Defects in the agent architecture:

1. **`ask` is not an approval gate under the factory's invocation.** The adapter runs `opencode run ... --auto`. The CLI help states `--auto`: "Auto-approve permissions that are not explicitly denied". Therefore every `ask` (shell for all agents; edit for developers; AG-017 production-related actions) becomes allow in factory runs (AUD-R5-001). The normative AG-017 limit "Production execution requires explicit human approval" has no runtime enforcement.
2. **The independent auditor can write through its shell.** AG-002 has `edit: deny` but `bash: ask`. Under `--auto` a probe asking AG-002 to write `echo AG002_SHELL > /tmp/opencode/exp/ag002_shell_probe.txt` succeeded and the file was created outside the project directory. The `edit: deny` control was therefore not sufficient, and the audit independence rule ("Cannot modify audited artifacts") depends only on the model's self-restraint.
3. **Delegation is not used.** AG-001 has `task: allow` and a subagent surface, but the factory never runs AG-001 as coordinator. `run_task` (`runtime.py` 556-587) invokes whichever agent the task names. No delegation record, no `from_agent`/`to_agent`, no session linkage (coordination-contract delegation fields are absent from code and schemas).
4. **Auditor independence is not a property of the agent system.** The normative contract requires auditors to be independent from developers. The executable definitions do not enforce it; the runtime enforces it only in R5.2 and only when the executor is declared (section 6).
5. **Overlaps and gaps.** AG-012 (QA automation) and AG-002 (gatekeeper) both produce test-related verdicts; AG-013, AG-014 and AG-015 produce review/performance/security findings that feed AG-002 through evidence files. Nothing in the runtime consumes those findings except the Quality Gate reading JSON files. Capability gaps: no agent is responsible for capturing diffs, commit traceability per task, or evidence provenance; no agent owns the correction loop (REJECTED -> RUNNING with correction assignment).
6. **Model selection.** No model is declared in agent definitions or `opencode.json` (consistent with ADR-003), but the preflight and one runtime test hard-code `opencode-go/qwen3.8-flash` (AUD-R5-025).

## 5. Contract compliance matrix

Legend: C = compliant, P = partial, N = non-compliant, U = not verifiable from code.

| Contract / rule | Status | Evidence |
|---|---|---|
| Task states (`task-contract.md` lines 3-5) | C (names) | `TASK_STATES` runtime.py 17 |
| Allowed transitions (task-contract 9-21) | P | `TASK_TRANSITIONS` 34-44 matches the contract, but `assign_task` (372-378) writes ASSIGNED from FAILED/BLOCKED/REJECTED outside the table; `complete_task` (420-435) completes from REJECTED; CLI `task status` (`update_task_status`) allows RUNNING/REVIEW_REQUIRED -> COMPLETED without gates (E5, E11) |
| Required task fields (task-contract 25-38; `schemas/task.schema.json`) | N | Table has `objective`, `agent_id`; no `description`, `assigned_agent`, or (on main) `quality_gates` (E11 column check) |
| Rule 1: no COMPLETED without acceptance criteria (task-contract 42) | P | Caller boolean at 427; empty criteria skip the check entirely; CLI bypass (E5). R5.2 rejects boolean and requires verification records |
| Rule 2: no COMPLETED with FAIL/BLOCKED required QG (task-contract 43) | N (main) / P (R5.2) | Main: `quality_gate_verdict` is a caller string (424); CLI bypass. R5.2: QG result required by `complete_task`, but CLI bypass remains |
| Rule 3: REVIEW_REQUIRED requires independent review (task-contract 44) | N | No review record, no reviewer identity check |
| Rule 4: cancellation requires a reason (task-contract 45) | N | `update_task_status(CANCELLED)` takes no reason (E11) |
| Execution required fields (execution-contract 9-19) | P | `inputs` not stored on main (`create_execution` ignores the argument, 381-389); `decisions` never written; `tools_used` is the static string `opencode.run` (run_task 581/584) |
| Execution rule 1: valid task reference | N | Executions accepted for nonexistent tasks (E10); no FK on `executions.task_id` |
| Execution rule 2: record tools used | P | Static string only |
| Execution rule 3: failed executions include errors | P | `errors` is `["unknown"]` when stderr is empty, although the real error is in stdout (observed in the R5.2 run of E14; the adapter code is identical on main, lines 53-58) |
| Execution rule 4: review sets REVIEW_REQUIRED | P | Successful run sets REVIEW_REQUIRED (582); nothing ever resolves it to COMPLETED except bypass paths |
| Execution rule 5: no execution may alter audit results | N (main) / P (R5.2) | Main: audits updatable and deletable (E7). R5.2: audit triggers (E7 re-test: UPDATE/DELETE blocked) |
| Audit required fields (audit-contract 9-16) | P | Table uses `artifacts` not `audited_artifacts`; no audit verdict consumed by release |
| Audit rule 1: auditor independent from developer | N (main) / P (R5.2) | Main: `record_audit` accepts AG-008 as auditor of its own work (E7). R5.2: rejects when executor declared; check is skipped when executor is not declared |
| Audit rule 2: audited agents cannot modify audit results | N (main) / P (R5.2) | As above; events remain deletable on R5.2 (E7 re-test: 1 event deleted) |
| Audit rule 3: FAIL/BLOCKED prevents release | N | No release path reads audit verdicts |
| Audit rule 5: evidence references files/test output | P | Evidence strings are not validated |
| Coordination task fields (coordination-contract 3-17) | P | `retry_count` and `max_retries` exist but are never incremented or enforced (E12) |
| Coordination delegation fields (coordination-contract 19-27) | N | No delegation table, no records |
| Coordination rule 2: dependencies COMPLETED before start | P | Checked in `update_task_status` for ASSIGNED/RUNNING (365) and in `run_task`; not in `assign_task` (E10) |
| Coordination rule 3: retry count <= max_retries | N | Not enforced (E12: six failures, no limit) |
| Coordination rule 4: rejected tasks return with correction assignment | N | No correction assignment mechanism |
| Coordination rule 5: no automatic advancement after FAIL/BLOCKED | P | `run_workflow` stops on first non-COMPLETED task (R5.2: sets BLOCKED) |
| Quality contract: certificates valid only for audited commit | N (R1) / P (R2) | R1 does not compare certificate commit to the repository; R2 does when `--repo` is given and commit fields exist |
| Quality contract: CRITICAL/HIGH block release | P | R1 blocks CRITICAL and FAILs HIGH; release is not gated by runtime |
| Quality contract: auditors cannot approve own work | N | Not enforced for tasks |
| Agent contract: independence (agent-contract "Independence") | N | As audit rule 1 |
| Agent contract rule 3: no critical operations without approval | N | `--auto` plus no approval check (AUD-R5-001, AUD-R5-006) |
| Approval policy (approval-policy.md) | N | Approvals can be granted by any string (E8); consumption has no caller (`consume_approval` 521-529) |
| Security authorization workflow step 5 (LEVEL C block) | N | AG-003 classification is not recorded or enforced by the runtime |
| Project lifecycle (project-lifecycle.md) | N | `update_project_status` (411) is not reachable from the CLI; project stays `REGISTERED` (E-series, `project status`) |
| State management rule (state-management.md) | P | SQLite runtime DB is authoritative for task state but is gitignored and not exported to evidence (see section 14) |
| Model portability (ADR-003) | P | No model in agent definitions; hard-coded model in preflight and one test |

## 6. Runtime and workflow assessment

### 6.1 Verdicts for the eight known investigation points

1. **`run_workflow()` may mark COMPLETED while tasks remain REVIEW_REQUIRED or are skipped. VERIFIED on main.** `run_workflow` (590-610) filters non-COMPLETED tasks (595), skips tasks with unmet dependencies (600-601), treats REVIEW_REQUIRED tasks as done once their run returns COMPLETED, and then writes `workflow_runs.status='COMPLETED'` (608). Experiment E4: one task REVIEW_REQUIRED, dependent task PENDING, run status COMPLETED. Experiment E4e: a dependency cycle produced `COMPLETED` with zero adapter calls. On R5.2 the run becomes `BLOCKED` in both cases (E4, E4e), so the false success is fixed for those cases; a second run on a REVIEW_REQUIRED task still returns COMPLETED for that task without moving it to a terminal state.
2. **Workflow execution does not follow configured stages. VERIFIED on main and on R5.2.** `workflows.definition` lists stages (`standard-delivery`: analysis, architecture, development, quality, release), but `run_workflow` never reads the stages; `current_step` is set once at start (480) and never updated; tasks are not linked to a workflow run; `executions.workflow_id` is never set. Experiment E4b: an `analysis-only` run executed a development agent.
3. **`evaluate_gate()` trusts `final_verdict` when `evidence_dir` is absent. VERIFIED on main; FIXED on R5.2 for this function.** Main line 548 returns `cert["final_verdict"]`; a certificate with an open CRITICAL defect and `final_verdict: PASS` returned PASS (E6c). R5.2 returns FAIL with "evidence_dir required for R1 validation" (E6c). The CLI validator itself remains fail-open (below).
4. **`complete_task()` does not require an independently verifiable QG approval. VERIFIED on main; PARTIAL on R5.2.** Main: `quality_gate_verdict` is an unverified string; `None` is accepted (424); the BLOCKED gate evaluated for the project did not block completion (E5). R5.2 requires a stored QG result inside `complete_task`, so the Python API path is closed, but the CLI path below is not.
5. **Acceptance verification relies on a caller-supplied boolean. VERIFIED on main; FIXED on R5.2.** Main line 427 accepts `acceptance_verified=True`. R5.2 rejects a boolean ("Acceptance criteria require verifiable results, not a boolean flag"). Note: tasks with no acceptance criteria still bypass the check on both branches.
6. **`record_audit()` lacks independence and immutability. VERIFIED on main; PARTIAL on R5.2.** Main: AG-008 recorded an audit of its own work (E7); UPDATE changed a PASS to FAIL (rowcount 1); DELETE removed it (rowcount 1); two events were deleted. R5.2: audit rows are immutable (trigger error "audits are immutable"); independence is enforced when an executor is declared (self-audit rejected); events remain deletable (1 deleted); independence is not checked if no executor is supplied (code path at `record_audit`, not executed). `record_audit` is not reachable from the CLI on either branch.
7. **Recovery may mark interrupted tasks BLOCKED without resuming them. VERIFIED on main; FIXED on R5.2 for resume.** Main E12: a crashed run left execution and task RUNNING; `recover` set INTERRUPTED and BLOCKED; resume raised "Task cannot run from state BLOCKED" and left the task ASSIGNED. R5.2 E12: resume completes the task. Retry accounting is still absent on R5.2 (`retry_count` stays 0 across six failed attempts; no limit).
8. **Individual OpenCodeAdapter invocation may work without proving full native delegation. VERIFIED.** Individual invocations work (section 7), but no native delegation is exercised, and the adapter's isolation is broken (`PWD`, `--auto`).

### 6.2 Additional runtime defects (main unless stated)

- `run_task` cannot start a PENDING task. `run_task` checks `task["status"]` (568-573) from a dictionary read before `assign_task` changed the row, so the freshly assigned task fails the check at 573-574 with `Task cannot run from state PENDING`, after writing ASSIGNED (E1, E14). The R5.1 record ("Task run end-to-end: PASS") is therefore not reproducible for the documented path (create, then run). Fixed on R5.2 (E1).
- `assign_task` bypasses the transition table and dependency checks (372-378): FAILED -> ASSIGNED and an unmet dependency are accepted (E10, E11). Still present on R5.2 (E10, E11).
- `complete_task` accepts REJECTED and writes COMPLETED (422, 431); cancellation takes no reason (E11). Still present on R5.2 (E11 cancel).
- The CLI `task status <id> COMPLETED` (dispatch, `update_task_status`) completes RUNNING and REVIEW_REQUIRED tasks with no QG, acceptance or review. VERIFIED on main (E5, E11) and on R5.2 (E5, E11). This is the single most direct quality-gate bypass in the baseline.
- Race condition: concurrent assignment duplicates. Main: 80 concurrent attempts on 20 tasks produced 21, 21 and 23 successful ASSIGNED transitions and 3 tasks with duplicate ASSIGNED events (E13). R5.2: 20 (one run), 25, 24, 24 and 27 successes across five runs, with 0 to 6 duplicate tasks. The read-then-write in `update_task_status` (358-369) is not conditional on the current status, and the runtime never uses `BEGIN IMMEDIATE`. R5.2 does not fix this.
- ID generation is `max+1` over a full scan with no uniqueness guarantee under concurrency (`task_id`, `execution_id`, `approval_id`; main 241-274).
- `run_task` performs several independent commits (task status, execution creation, task status) rather than one transaction (main 556-587). A crash between commits leaves a RUNNING task without a RUNNING execution, or the reverse (static reasoning; not executed).
- `recover_interrupted` (446-460) is global: it marks every RUNNING execution in the database INTERRUPTED with no liveness check (CLI `recover`, 855-858). A second runtime process would corrupt live work (static reasoning; not executed).
- `create_task` accepts unknown dependency identifiers (E10); a missing dependency makes `run_workflow` raise `Task not found` and leaves the run RUNNING forever (E4d, on both branches).
- `migrate()` (66-88) is never called on main: `init_db` (90-216) does not invoke it and `get_conn` (219-222) calls only `init_db`. An R3 database therefore stays at `schema_version` 1 and `complete_execution` fails with `no such column: outputs` (E9). R5.2 calls `migrate` from `init_db` and E9 succeeds (schema versions 1, 2, 3).
- Approval functions: `create_approval` computes `binding_hash` (500) that nothing verifies; `approve` (510-518) accepts any `--by` string; `consume_approval` (521-529) has no caller outside tests. Approvals therefore gate nothing (E8). Unchanged on R5.2 (`consume_approval` still has no runtime caller).
- Project lifecycle: `update_project_status` (411) and `PROJECT_TRANSITIONS` (19-32) exist, but no CLI command calls them. Projects stay REGISTERED.
- No CLI command exposes `record_audit`, delegation records, or acceptance verification.

### 6.3 Dependency, reference and identity integrity

- Repository paths are not validated: a project with a nonexistent `--repo` was registered (E10); two projects for the same repository were registered (E10).
- Executions can reference nonexistent tasks (E10).
- Actor and approver identities are free text (`--actor`, `approval approve --by`), with no authentication (E8).

## 7. OpenCode integration assessment

Verified behaviour (scratch directory `/tmp/opencode/audit-proj`, OpenCode `v2.2.5`):

1. **Individual invocation works.** The adapter returns `COMPLETED` with an assistant answer (`PROBE_OK`) for `ag-001-project-coordinator` (model: default configured model). The assistant can use tools (shell, read, glob) and its tool events are present in the JSON stream.
2. **`--auto` removes the approval gate.** OpenCode's own help says `--auto` "Auto-approve permissions that are not explicitly denied". The adapter sets it unconditionally (`opencode_adapter.py` line 37). Under it, AG-002 (`bash: ask`) executed a shell write outside the project directory (file created). Without `--auto` (control probe), the same request did not produce the file: the model declined, and its only shell call returned `status: error`. That control indicates fail-closed behaviour, but the model's own refusal confounds the attribution, so it is recorded as consistent with, not proof of, fail-closed.
3. **Working directory is not isolated (critical).** OpenCode takes the working directory from the inherited `PWD` environment variable, not from the process `cwd`. Experiment (same agent, same request, subprocess `cwd=/tmp/opencode/audit-proj`):
   - with inherited `PWD=/tmp/opencode/head`, the agent's shell reported `/tmp/opencode/head`;
   - with `PWD=/tmp/opencode/audit-proj`, it reported `/tmp/opencode/audit-proj`.
   `opencode_adapter.py` copies `os.environ` into `env` (line 43) and never sets `PWD`. A runtime launched from the factory repository therefore runs project agents in the factory repository. The default service path also showed intermittent misdirection in earlier probes. `opencode run --standalone` honoured the requested directory when the agent definitions were present in that directory (`pwd` = `/tmp/opencode/audit-proj`). The R5.2 commit does not change the adapter.
4. **Agent discovery depends on the working directory and on hidden state.** `opencode debug agents` loads the 18 `ag-*` agents only when the working directory contains the factory's `.opencode/` tree. `OPENCODE_CONFIG_DIR` set to the factory root or to `.opencode` does not add the agents for a project directory (0 loaded from a project cwd, both settings). `validate_agent` (`list_agents`, line 23) runs `opencode debug agents` from the runtime's cwd without the environment override, while `invoke` runs `opencode run` in the project cwd with the override. Validation can therefore pass while invocation fails (`Agent not found`). Observed "Agent not found" from a project cwd on several calls; the same calls later succeeded with no repository change. The mechanism is not fully root-caused (background service state is the most likely explanation); the practical conclusion is that discovery is not deterministic and is not diagnosed.
5. **Error reporting loses information.** OpenCode reports run errors as JSON on stdout with exit code 1. The adapter maps the exit code to FAILED and takes the error text from stderr (line 57), which is empty; the execution record stores `unknown`. Observed in the R5.2 run of E14: the execution's `errors` field is `["unknown"]` while its evidence contains `Agent not found`. The adapter code is identical on main.
6. **Classification.** `COMPLETED` is decided only by exit code 0 (line 53). The adapter does not parse OpenCode events (no error-event check, no tool-event capture). `BLOCKED` results from the adapter's own pre-checks become FAILED in `run_task` (580-585; E2).
7. **Timeouts and processes.** `subprocess.run(timeout=...)` kills the direct child only (line 52, 61-62). The background service and any tool subprocesses are not terminated (not verified; design risk).
8. **Environment exposure.** The agent receives the full parent environment (line 43). Any secret in the runtime's environment is visible to agents, and under `--auto` to their shell (not exploited; exposure by construction).
9. **Native delegation is not verified.** The runtime never runs AG-001 as coordinator, and no experiment observed an AG-001 `task` tool call to a subagent. The integration document's "Verified capabilities: task tool delegation" (`integrations/opencode/opencode-integration.md`) is not supported by evidence in this repository.
10. **Model selection.** The adapter passes `--model` only if the caller supplies one; the preflight (line 106) and a runtime test (`test_runtime.py` line 323) hard-code `opencode-go/qwen3.8-flash`.
11. **Version pinning.** No OpenCode version is recorded in the repository. The audit used `v2.2.5`.

## 8. Quality and testing assessment

Test execution (clean export of `d3c9cde`):

- `python3 tests/run_all.py` → ALL TESTS PASSED (exit 0), **37 test functions** from **5 files** (`contracts/test_schemas.py`, `contracts/test_state_transitions.py`, `policies/test_policy_files.py`, `contracts/test_f5_schemas.py`, `orchestration/test_runtime.py`).
- Omitted test modules, each run directly with the interpreter (pytest is not installed): `orchestration/test_quality_gate_runtime.py` (14 tests), `orchestration/test_traceability.py` (20), `orchestration/test_structure.py` (7), `orchestration/test_f1_structure.py` … `test_f5_structure.py` (3 each), `contracts/test_f2_schemas.py` (8), `contracts/test_f3_schemas.py` (2), `contracts/test_f4_schemas.py` (8), `implementations/PROJECT-001/tests/test_backend.py` (unittest, OK). All exit 0. Repository total: 115 test functions in 17 modules. Roughly 78 of them are not executed by the declared command.

Assessment of test quality:

- **Tautological test.** `tests/contracts/test_state_transitions.py` (lines 1-17) tests a private copy of the transition table and never imports the runtime. It cannot fail when the runtime changes.
- **Vacuous runtime tests.** `test_blocked_by_critical_defect` (158-167) never calls the gate and asserts only that the project is REGISTERED. `test_blocked_by_missing_approval` (169-180) asserts that the approval is APPROVED, which is the opposite of its name. `test_real_opencode_adapter_invocation` (314-327) returns silently when the status is not COMPLETED (324-325), so it passes when the real invocation fails. `test_closure_requires_conditions` (277-279) asserts a dictionary entry only. `test_event_modification_rejected` (119-122) checks only for the absence of two functions.
- **Test of the wrong contract.** `test_opencode_adapter_contract` (300-312) tests a fake adapter.
- **Integration test that cannot fail.** `tests/orchestration/test_traceability.py::test_r1_integration` (289-303) asserts only `returncode != 0`. The R1 integration is broken when the validator is run as a script (AUD-R5-018), so the test passes for the wrong reason.
- **Missing adversarial tests.** No test covers: CLI status bypass; PENDING start; unfinished workflow completion; cyclic or unknown dependencies; approval enforcement; fail-open Quality Gate inputs; audit mutation; concurrency; the working-directory (PWD) isolation; permission `ask` semantics; migration of an existing database.
- **R1/R2 claims.** The R1 record says "16 tests" (`docs/audits/R1_FINAL_AUDIT.md` line 20); the file contains 14 test functions. The R2 record says 20 tests (matches).

Positive: the Quality Gate and traceability test files do exercise meaningful negative cases (critical open defect, certificate omits defect, commit mismatch, artifact modified); these pass.

## 9. Security assessment

| Area | Assessment | Evidence |
|---|---|---|
| Permission gates | Bypassed in factory runs | `--auto` (adapter 37); AG-002 shell write outside project |
| Repository isolation | Not guaranteed | `PWD` inheritance; agent reported the wrong directory |
| Factory repository protection | Not enforced | Agents can write any absolute path; no sandbox; repository `cwd` is not a boundary |
| Filesystem boundaries | Not enforced | Absolute-path shell write succeeded |
| Shell execution | Unrestricted under `--auto` | Gate bypass |
| Secrets handling | Full environment inherited | adapter line 43; `.gitignore` covers `.env`, but environment is not filtered |
| Permissions and identity | Free-text actors; no authentication | `--actor`, `--by`; approvals (E8) |
| Approval requirements | Not enforced | No runtime check; `consume_approval` unused |
| Prompt injection | Exposed | Task prompts and repository contents reach agents with shell access under `--auto` |
| Privilege escalation | Possible through the bypass | Auditor (AG-002) writes via shell; a developer's task can complete via CLI |
| Audit integrity | Mutable on main; partly fixed on R5.2 | E7; R5.2 triggers on audits only |
| Supply chain | Partly controlled | Runtime uses only the standard library (positive); OpenCode CLI version unpinned; no lockfile |
| Data protection | Runtime DB at `orchestration/runtime/runtime.db` by default (`runtime.py` 14), gitignored; no access control or encryption | Repository path default |
| PROJECT-001 (R4) | Sampled: PBKDF2 (100,000 iterations) password hashing; session tokens stored as SHA-256 hashes; task queries scoped by `user_id`; the only dynamic SQL builds fixed column fragments with parameterised values (`app.py` 302-342) | Sampling only; not a full penetration test |

Conclusion: an agent operating through the factory can perform LEVEL C operations (shell, destructive or production-related) without the human approval the factory's rules require, and can operate outside the intended project directory. This is a critical control failure.

## 10. Release and deployment assessment

- **Traceability is optional where it matters.** `evaluate` (`traceability.py` 69-209): approval is checked only when `--approval` is passed (159); artifact hash only when present in the manifest (133-141); certificate hash only when referenced (116-124); tree hash only when present (101-104). Experiments (disposable Git repository): a PASS certificate targeting `production` with no approval → **PASS** (T1); an artifact changed after the manifest was written → **PASS** (T2); a certificate whose content changed (critical open defect added, verdict unchanged, no certificate hash) → **PASS** (T4).
- **Manifest generation ignores verdicts.** `cmd_generate` (232-263) writes a release manifest from a FAIL certificate and exits 0 (T3).
- **Quality Gate integration broken from the CLI.** Run as a script, `traceability.py` inserts `orchestration/` (not the repository root) into `sys.path` (line 178). With `--evidence-dir`, the release validation fails with `No module named 'orchestration'` (T5). Run with `python3 -m`, it works, so the defect shows only in the documented script invocation.
- **PROJECT-001 release record.** `RELEASE_MANIFEST.json` (REL-0002, version 1.0.0, commit `6404e4d`) is validated **PASS** with no approval (R2). Its only approval record, `APPROVAL.json` (APPR-0001), refers to version 0.4.0 and commit `26a5af6` (an F-phase merge) with artifact `artifact.zip`; with that approval the validator returns FAIL on three mismatches. The artifact lives at `/tmp/scratchpad/project001-deploy/artifact.zip`, outside the repository, so it is not reproducible from a clean clone. The certificate hash in the manifest was verified (`1d484ddd…` matches the canonical hash of `QUALITY_CERTIFICATE.json`), and the tree hash `e3bad5fd…` matches commit `6404e4d`.
- **Quality Gate on PROJECT-001.** R1 with the correct directory (`implementations/PROJECT-001/quality/evidence/`) returns `PASS_WITH_OBSERVATIONS` with one open LOW defect, reproducing the R4 record. The gate's inputs are self-reported (section 6 and AUD-R5-017): `reaudit.json` is `{"performed": true}` and `test_execution.json` is `{"status":"PASS","failed_tests":[]}`, with no auditor, no commit and no test identifiers.
- **Rollback and deployment.** No runtime-gated deployment or rollback exists. F5 provides demonstration scripts (`implementations/PROJECT-001/deployment/pipeline.py`, `rollback_demo.py`), not gated execution.
- **Evidence retention.** Evidence is referenced by path; no hashes are stored for the evidence files themselves; no retention policy exists.

Conclusion: the release process is **not enforceable** in its current form. A release can be marked PASS without approval, with altered artifacts or certificate content, and with failing certificates.

## 11. Operational assessment

- **Recovery after process or host interruption.** Partially. SQLite WAL and `busy_timeout` are configured (`runtime.py` 56-58). Interrupted executions are detectable only with the manual, global `recover` command (main 446-460). R5.2 adds resume.
- **Concurrency.** Not safe for concurrent writers: duplicate assignments are reproducible (section 6.2).
- **Scalability.** Single-host SQLite is adequate for pilot scale. ID generation scans all rows; `list_*` functions are unbounded. Not measured.
- **Logging and observability.** The `events` table records transitions (append-only in intent, deletable in fact). There are no structured logs, no metrics, no alerting, and no backup or export procedure. Execution evidence is the raw stdout of OpenCode, stored in the database.
- **Configuration management.** Environment variables (`APF_DB_PATH`, `OPENCODE_BIN`, `OPENCODE_CONFIG_DIR`) and CLI flags. No configuration file, no per-environment settings.
- **Installation and clean-clone reproducibility.** A clean export of `d3c9cde` passes `tests/run_all.py` (verified). The OpenCode CLI is an external, unpinned dependency.
- **Documentation quality.** Extensive and structured, but several records are inaccurate (section 14).
- **Maintainability.** Single large `runtime.py` (863 lines on main; 1,300+ lines on R5.2) mixes persistence, state rules, adapter calls and CLI; duplicated workflow seeding (`init_db` and `seed_workflows`); multiple near-identical ID generators.

## 12. Verified defects and evidence

All experiments ran against disposable databases in `/tmp/opencode/exp/` (harness: `run_exp.py`; the harness selects the code root with `APF_ROOT`). They are not in the repository and are not deliverables; they should be promoted to regression tests in R5.2 (see the backlog).

| Exp | Question | Main `d3c9cde` | R5.2 `5bd7187` |
|---|---|---|---|
| E1 | First run of a PENDING task | Error `Task cannot run from state PENDING`; task left ASSIGNED; adapter not called | Runs; REVIEW_REQUIRED |
| E2 | Adapter BLOCKED result; prompt and inputs | BLOCKED recorded as FAILED; prompt is the CLI string only; inputs `[]` | Inputs stored; BLOCKED still recorded as FAILED; objective still not sent |
| E4 | Workflow with unmet dependency | COMPLETED; dependent task PENDING | BLOCKED |
| E4b | Analysis-only workflow with development task | Development agent executed | Same |
| E4d | Missing dependency identifier | `Task not found`; run stays RUNNING | Same |
| E4e | Dependency cycle | COMPLETED; zero work | BLOCKED |
| E5 | Completion after a BLOCKED gate | Completed | Refused (`Quality Gate did not pass`) |
| E5/E11 | CLI `task status … COMPLETED` from RUNNING or REVIEW_REQUIRED | Completed (no gate) | Completed (no gate) |
| E6a | Empty evidence directory; certificate result fields FAIL/BLOCKED; final PASS | PASS, exit 0 | PASS, exit 0 (validator unchanged) |
| E6b | CRITICAL defects with status `in progress` / `wontfix` | PASS | PASS (validator unchanged) |
| E6c | `evaluate_gate` without evidence; open CRITICAL; final PASS | PASS | FAIL |
| E6d | `evaluate_gate` with evidence; status `in progress` | PASS | PASS |
| E7 | Audit by the developer; UPDATE and DELETE of audit; event deletion | Accepted; UPDATE and DELETE succeed; 2 events deleted | Developer audit refused; UPDATE/DELETE blocked; 1 event deleted |
| E8 | Approval by arbitrary string | APPROVED by `any-string-user`; nothing consumes it | Same |
| E9 | R3 database opened by the current code | `schema_version` stays 1; `complete_execution` → `no such column: outputs` | Migrated to 3; completes |
| E10 | Repository, task and dependency references | Nonexistent repo accepted; duplicate repo accepted; execution for nonexistent task accepted; unknown dependency accepted; assign ignores dependencies | Same (unchanged) |
| E11 | Transition bypasses | FAILED → ASSIGNED; REJECTED → COMPLETED; cancel without reason | FAILED → ASSIGNED; REJECTED completion now gated; cancel without reason |
| E12 | Crash, recovery and retries | Recovered to BLOCKED; resume impossible; retry_count 0 after six failures | Resume completes; retry_count still 0; unlimited attempts |
| E13 | 80 concurrent assignments on 20 tasks | 21, 21, 23 successes; 3 duplicated tasks | 20, 25, 24, 24, 27 successes; 0 to 6 duplicated tasks |
| E14 | CLI `task run` | `Agent not available in OpenCode: AG-008` (normative id); `Task cannot run from state PENDING` (executable id) | Normative id still rejected; executable id reaches the real adapter and FAILs with `Agent not found` (project cwd) |
| T1 | Production release, PASS certificate, no approval | PASS | not re-tested (traceability unchanged) |
| T2 | Artifact changed after manifest | PASS | not re-tested |
| T3 | Manifest generated from FAIL certificate | Written, exit 0 | not re-tested |
| T4 | Certificate content changed; no certificate hash | PASS | not re-tested |
| T5 | R1 integration from script CLI | FAIL (`No module named 'orchestration'`) | not re-tested |
| P1 | PROJECT-001 release validation | R2 PASS without approval; FAIL with `APPROVAL.json` (version/commit/artifact mismatch) | not re-tested |
| P2 | PROJECT-001 Quality Gate (correct evidence dir) | PASS_WITH_OBSERVATIONS (reproduces record) | not re-tested |
| L1 | AG-002 shell write, `--auto` | File created outside project | not re-tested (adapter unchanged) |
| L2 | AG-002 without `--auto` | No file; model declined; shell status error | not re-tested |
| L3 | Agent working directory vs PWD | `PWD=head` → head; `PWD=audit-proj` → audit-proj | adapter unchanged |
| L4 | `--standalone` with project-local `.opencode` | `pwd` = project directory | not re-tested |
| L5 | Adapter invocation of AG-001 | COMPLETED, `PROBE_OK` | adapter unchanged |

Model-call budget: approximately 14 calls, all with benign prompts, scratch paths only.

Also verified without model calls: `opencode debug agents` loads the 18 `ag-*` agents only from a factory-tree cwd; `validate_agent('AG-008') == False`, `validate_agent('ag-008-backend-developer') == True`.

## 13. Missing capabilities

1. Native OpenCode delegation from AG-001 with delegation records (`delegation_id`, `from_agent`, `to_agent`, `requested_at`, `completed_at`, `result`, `evidence`).
2. An audit flow that invokes AG-002 (or AG-003) with an independence check and records the verdict; release gated on that verdict.
3. An authenticated human approval channel, approvals bound to project, version, commit, artifact hash, environment, strategy and rollback plan (as AG-017 requires), and atomic consumption by the gated action.
4. Per-task isolated working copy (for example a git worktree on a task branch), change capture (`git diff --name-status`, file hashes), and commit traceability for each execution.
5. Parsing of OpenCode JSON events: tool use, errors, decisions, session identifiers.
6. Retry accounting and limits (`retry_count`, `max_retries`), and the correction loop for REJECTED tasks.
7. Stage gating that binds workflow stages to tasks, agents and Quality Gates (QG-01..QG-06).
8. Project lifecycle transitions driven by the runtime.
9. Runtime-gated deployment and rollback (with approval) and deployment evidence.
10. Operator identity and authorisation (who approved, who ran, who may change state).
11. Event-log integrity (append-only enforcement, hash chaining or external export).
12. Export of runtime state to versioned evidence files, reconciling ADR-001 with the SQLite source of truth.
13. Process-level isolation or sandboxing for executors.

## 14. Contradictions in documentation

1. **Stale handoff.** `PROJECT_HANDOFF.md` line 22 lists "Merge to main and create remediation tag" as pending; `main` already contains the merge (`e2c17d4`) and the tag exists (`v0.6.5-r5.1`). `PROJECT_STATUS.md` lines 13-14 repeat the pending merge.
2. **Wrong commit reference.** `PROJECT_PROGRESS.md` lines 75 and 86 attribute v0.6.1-r1 to commit `d5d015a`. `d5d015a` is `docs: prepare R5 pilot and preflight` (correctly cited at line 123 for R5 preparation); the tag `v0.6.1-r1` is `cecf2ea`. `PROJECT_CONTEXT.md` line 7 and `CHANGELOG.md` line 80 record a "published commit" `dbdc242` that is historical, not the current state.
3. **Duplicate and misordered ADR identifiers.** `PROJECT_DECISIONS.md`: ADR-005 is used twice (line 39 for the SQLite decision, line 61 for the TEST-006 security event); ADR-004 appears after the second ADR-005 (line 51); ADR-006 exists (line 73), but `PROJECT_HANDOFF.md` lists "ADR-001 to ADR-005".
4. **Source of truth.** ADR-001 and `state-management.md` state that repository files are the single source of truth and that no hidden runtime state may be authoritative. The runtime's SQLite database (`orchestration/runtime/runtime.db`, gitignored) is the only authoritative record of task, execution, approval and audit state.
5. **Delegation claim.** `integrations/opencode/opencode-integration.md` lists "Task tool delegation controlled by permission.task" under "Verified capabilities". No delegation was executed or recorded. `docs/pilots/R5_ACCEPTANCE_CRITERIA.md` requires "Agent delegation is verified"; that criterion is not met.
6. **Model portability.** `integrations/opencode/opencode-integration.md` says no model is hard-coded; `orchestration/preflight/r5_preflight.py` line 106 and `tests/orchestration/test_runtime.py` line 323 hard-code `opencode-go/qwen3.8-flash`.
7. **Autonomy.** `PROJECT_CONTEXT.md` declares "Autonomy: supervised" and ADR-002 requires human approval for critical operations; the adapter runs with `--auto`.
8. **R5.1 claims.** `docs/audits/R5.1_FINAL_AUDIT.md` records "Task run end-to-end: PASS", "Workflow execution: PASS", "Recovery: PASS", "SQLite migration v2", "Added record_audit and complete_task enforcement", and "Real agent invocation verified". On the audited baseline: task run from PENDING fails (E1); workflow reports COMPLETED falsely (E4); recovery does not resume (E12); migration is not reachable (E9); audit and completion enforcement are partial (E5, E7); real invocation is verified only for a benign agent prompt while isolation is broken.
9. **R1 test count.** `docs/audits/R1_FINAL_AUDIT.md` line 20: "Runtime tests: 16 tests PASS"; the test file has 14 test functions.
10. **Test coverage.** `PROJECT_HANDOFF.md` lines 36-38 and the audit records describe `python3 tests/run_all.py` as the validation of R1 to R5.1; it executes 5 of 17 test modules.
11. **Preflight semantics.** `orchestration/preflight/r5_preflight.py` lines 92-98 labelled "project isolation" PASS without testing isolation; line 27-30 "repository" tests only that `.git` exists. `docs/pilots/R5_ACCEPTANCE_CRITERIA.md` and the R5 preparation audit present preflight PASS as readiness evidence.
12. **Operational R4 records.** `PROJECT_PROGRESS.md` and `docs/audits/R4_PROJECT001_FINAL_AUDIT.md` record R1 `PASS_WITH_OBSERVATIONS` and R2 `PASS`. R1 reproduces (P2); R2 PASS holds only because approval is optional (P1). The R2 record does not say so.
13. **Schema versus implementation.** `schemas/task.schema.json` requires `description`, `assigned_agent`, `quality_gates`; `schemas/execution.schema.json` requires `inputs`, `outputs`, `tools_used`, `decisions`. The runtime's tables do not match these names (section 5).
14. **Contract claim of required fields.** `contracts/execution-contract.md` lists `inputs` and `decisions` as required; the runtime does not persist decisions and (on main) does not persist inputs.

## 15. Previously claimed remediations: verification status

Verified:

- Normative and executable agent catalogue; 18 agents load; mode and domain consistency (F1, F5 records).
- Quality Gate deterministic verdict for R4 evidence (R1 record reproduces with the correct evidence directory).
- Traceability hash, commit and tree checks when fields are present (test suite; T4 demonstrates absence where fields are missing).
- Real OpenCode invocation of a factory agent (R3/R5.1 claim; reproduced as L5).
- Declared test runner passes on a clean export (`tests/run_all.py`).
- R4 PROJECT-001 authentication and data-access primitives (sampled).
- R3 SQLite basics (persistence, WAL, project/task CRUD via CLI).

Partially demonstrated:

- "Quality Gate / acceptance enforcement" (R5.1): gate is bypassable through the CLI (E5, E11); acceptance boolean removed only on R5.2.
- "record_audit and complete_task enforcement" (R5.1): partial (E5, E7).
- "Workflow execution" (R5.1): executes, but reports false success on main (E4) and ignores stages (E4b).
- "Recovery" (R5.1): detection works; resumption does not on main (E12).
- "SQLite migration v2" (R5.1): defined but not reachable on main (E9); reachable on R5.2 (E9).
- "Real agent invocation" (R5.1): works, but permissions and working directory are not isolated (L1, L3).
- "Preflight PASS" (R5 preparation): tool checks are real; the isolation check is a no-op; the agent check validates from a different context from invocation.
- "R2 PASS" for PROJECT-001: holds only with approval optional.

Not verified or contradicted:

- "Task run end-to-end: PASS" (R5.1): not reproducible from PENDING (E1, E14).
- "Agent delegation is verified" (R5 acceptance): no delegation exists.
- "Recovery: PASS" as a resumption property (R5.1): not on main.
- "Human approval required for critical operations" (ADR-002, approval policy): not enforced.
- "R1 16 tests" (R1 record): 14 functions.

## 16. R5.2 delta observation (`feature/r5.2-workflow-integrity`, `5bd7187`)

This section is an observation outside the audited baseline. It records what the same experiments show on the R5.2 commit, so that the R5.2 scope can be decided on facts. R5.2 changes only `orchestration/runtime/runtime.py` (520 insertions, 45 deletions); the adapter, the Quality Gate and the traceability validator are unchanged.

Fixed relative to main: pending start (E1); unfinished workflow becomes BLOCKED (E4, E4e); resume (E12); migration reachable and tested (E9); audit immutability (E7, triggers) and auditor independence when declared (E7); evaluate_gate without evidence → FAIL (E6c); boolean acceptance rejected; quality-gate result required by `complete_task`.

Not fixed: CLI `task status … COMPLETED` bypass (E5, E11); fail-open Quality Gate validator (E6a, E6b, E6d); approval enforcement (E8, `consume_approval` has no caller); assign and dependency bypasses (E10, E11); retry accounting (E12); duplicate-assignment race (E13: 20–27 successes for 20 tasks); events deletable (E7); BLOCKED recorded as FAILED and adapter error text lost (E2, E14); normative identifiers rejected (E14); development agents run in analysis-only workflows (E4b); missing-dependency crash (E4d); all adapter findings (`--auto`, `PWD`, discovery).

Caveat: the R5.2 branch is a moving target (it was being edited while this audit ran). Its fixes should be re-verified by the R5.2 re-audit, not inherited from this observation.

## 17. Overall verdict

**Architectural verdict: PARTIALLY IMPLEMENTED.** The factory has the right components and a valid normative design: persistent state, agent catalogue, executable Quality Gates, traceability validation, and a real OpenCode invocation path. The enforcement that makes the design trustworthy is absent or bypassable: approvals, Quality Gates on completion, auditor independence and immutability (on main), release approval, permission gates, and working-directory isolation. Native OpenCode delegation is not implemented, so the central lifecycle (AG-001 coordination through subagent delegation) is not demonstrated.

**Pilot readiness: NOT_READY.** See `R5_PILOT_READINESS_ASSESSMENT.md`.

**Remediation scope recommendation.** R5.2 should be scoped to security and truth-of-state first (adapter isolation and permissions, closure of the CLI bypass, fail-closed gates, approval enforcement, release gate, atomic transitions, and the adversarial test suite), before any further workflow feature work. See `R5_ARCHITECTURAL_RECOMMENDATIONS.md` and `R5_REMEDIATION_BACKLOG.md`.
