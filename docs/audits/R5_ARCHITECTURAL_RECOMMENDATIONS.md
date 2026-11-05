# R5_ARCHITECTURAL_RECOMMENDATIONS

Recommended target architecture and implementation sequence for AI-Project-Factory after R5.1. This document preserves the original architectural intent (see `PROJECT_CONTEXT.md`, ADR-001 to ADR-004) and proposes only targeted changes that are justified by the evidence in `INDEPENDENT_ARCHITECTURAL_AUDIT_R5.md`. It does not replace OpenCode's delegation mechanism, does not add a competing agent framework, and does not require a rewrite.

Finding IDs (AUD-R5-nnn) refer to `R5_REMEDIATION_BACKLOG.md`. Verification status is stated for each recommendation: items marked **PROBE** are prerequisites that must be verified before implementation.

## 1. Principles to preserve

1. Repository files and evidence are the audit trail; the runtime database is the operational state (see section 3 for the required reconciliation with ADR-001).
2. Supervised autonomy: human approval is an enforced gate for critical operations, not a record (ADR-002).
3. Independent audit: the auditor is a different agent from the executor, and cannot change its own verdict (ADR-004).
4. OpenCode is the agent runtime; agent definitions stay in `agents/` (normative) and `.opencode/agents/` (executable), with the normative source authoritative.
5. Model selection is configuration, not code (ADR-003).
6. Deterministic checks (Quality Gate, traceability, approval) are program functions, not agents.

## 2. Target architecture

```
Human operator (named principal)
   |  approvals, pilot scope, release decisions
   v
Factory controller (orchestration/runtime, CLI)
   |-- state: SQLite (authoritative for operations), append-only events with hash chain
   |-- transition engine: one function for every state change (AUD-R5-010, AUD-R5-012)
   |-- gate service: R1 quality gate, R2 traceability (fail-closed; AUD-R5-004, AUD-R5-007)
   |-- approval service: bound, single-use, human-only (AUD-R5-006)
   |-- evidence store: envelopes with hashes, exported per stage (AUD-R5-017)
   |-- adapter bridge (OpenCode)
          |
          v
   OpenCode (per task or stage, isolated)
     - AG-001 Project Coordinator (primary) delegates to subagents with the native task tool
     - Executor subagents work only inside their task worktree
     - Auditors (AG-002, AG-003, AG-013, AG-015) are invoked by the controller, not by the executor;
       they run with no shell and no edit permission
```

### 2.1 Two invocation patterns (both explicit and recorded)

- **Coordinated pattern (preferred for multi-agent planning and execution).** The controller starts AG-001 once per stage with the stage brief. AG-001 uses OpenCode's task tool (`permission.task: allow`, already defined) to delegate to subagents. The controller parses the OpenCode event stream and writes one delegation record per child session: `delegation_id`, `task_id`, `from_agent` (AG-001), `to_agent`, `requested_at`, `completed_at`, `result`, `evidence` (coordination contract fields). **PROBE:** the exact event shape for the task tool is not yet recorded in this repository; capture it once with a benign delegation and store the fixture (see section 9).
- **Direct pattern (for deterministic single-owner tasks and for audits).** The controller invokes one named agent. The record sets `from_agent = RUNTIME`. Audits always use this pattern so that the auditor is not chosen by the executor.

Both patterns keep the ownership rule ("every task has one owner", coordination rule 1) and store the same evidence envelope.

## 3. Source of truth (reconciling ADR-001)

Current state: task, execution, approval and audit state lives only in `orchestration/runtime/runtime.db` (gitignored). ADR-001 and `state-management.md` say repository files are the source of truth.

Recommendation (decision required; record it in a new ADR, do not edit ADR-001):

- The SQLite database is the operational store while work is in progress.
- At each stage closure the controller exports a canonical JSON snapshot of the project's tasks, executions, gate results, approvals and audits to `projects/<PROJECT>/evidence/<stage>/`, with its SHA-256 recorded in the stage record. The snapshot is committed by the human or by a controller command under change control.
- Repository evidence is therefore the auditable record; the database is the working state and must match the last snapshot at closure.

## 4. Component corrections (targeted)

### 4.1 OpenCode adapter (`orchestration/runtime/opencode_adapter.py`)

- Remove `--auto` (AUD-R5-001). **PROBE:** confirm the non-interactive behaviour of `ask` without `--auto` on the pinned OpenCode version, with an auditor shell probe, a developer shell probe and an edit probe, each in a scratch directory. The current evidence (L2) is consistent with fail-closed but confounded by model refusal.
- Set `PWD` explicitly to the resolved target directory; run a canary that reports the working directory before each run (AUD-R5-002). Keep `cwd`.
- Build the child environment from an allowlist (AUD-R5-015). Never pass secrets; pass only the variables OpenCode needs.
- Materialise the executable agent definitions into the task worktree (`.opencode/agents/`, copied from the normative mapping with a recorded hash), so discovery is the same in validation and invocation (AUD-R5-014). **PROBE:** verify that a worktree-local `.opencode/` is loaded with `--standalone` and with the default service, from the same directory, 20 times. The current evidence shows `--standalone` honours the directory (L4); the default service has shown intermittent misdirection (L3 history).
- Map identifiers from one table: `AG-xxx` (normative) to `ag-xxx-name` (OpenCode), generated from `agents/`.
- Parse JSON events: classify `error` events as FAILED or BLOCKED; capture tool uses, decisions, session identifiers; store the raw stream as a hashed file with a size cap (AUD-R5-013, AUD-R5-027).
- Process group per run; kill the group on timeout (AUD-R5-027).

### 4.2 Transition engine (`runtime.py`)

- One `transition(entity, to, actor, reason, evidence)` function for tasks, executions and workflow runs. It consults the transition table, checks dependencies for ASSIGNED and RUNNING, requires a reason for CANCELLED, uses compare-and-set (`WHERE status = ?`, `rowcount == 1`), runs in `BEGIN IMMEDIATE`, and writes the event in the same transaction (AUD-R5-010, AUD-R5-012).
- Remove COMPLETED from the generic status setter. Completion goes only through `complete_task` (AUD-R5-003).
- Identifiers from `INTEGER PRIMARY KEY AUTOINCREMENT` or a sequence table updated in the transaction (AUD-R5-010, AUD-R5-031).

### 4.3 Quality gates (`orchestration/validators/quality_gate.py`, `evaluate_gate`)

- The validator fails closed: a missing mandatory evidence source is BLOCKED; a defect is closed only if its status is in an explicit closed set; any FAIL or BLOCKED result field contradicting a PASS verdict yields FAIL (AUD-R5-004).
- Evidence is an envelope: `producer`, `commit`, `created_at`, `inputs_hash`, `tool`, `tool_version`, and a content hash recorded by the controller (AUD-R5-017). The controller computes the hash; the producer does not.
- `evaluate_gate` always runs the validator with the envelope; it persists the full result (inputs hashed) and returns it. Completion references the stored result id (AUD-R5-003, AUD-R5-028).

### 4.4 Workflow engine (`run_workflow`)

- A run is COMPLETED only if every task of every stage is COMPLETED and every stage gate is PASS or PASS_WITH_OBSERVATIONS with recorded observations; otherwise BLOCKED with the reason (AUD-R5-005).
- Tasks carry `workflow_run_id` and `stage`; the runner executes stage by stage in definition order (AUD-R5-005, AUD-R5-016).
- The project lifecycle state advances only on stage completion (AUD-R5-016).

### 4.5 Approvals

- Gated actions: `release.publish`, `deploy.staging`, `deploy.production`, `data.destructive`, `policy.change` (AUD-R5-006).
- Approval binding: project, version, commit, artifact hash, environment, strategy, rollback plan, risks (normative AG-017 limits). The action verifies and consumes the approval in the same transaction as the state change.
- Approver identity: the OS user, mapped to an allow-listed human principal in a repository file under change control. Agent identifiers are refused (AUD-R5-024).

### 4.6 Audit flow

- The controller invokes the auditor (AG-002 for quality; AG-003 for LEVEL B/C risk) in direct pattern with a read-only permission profile (no shell, no edit, no task).
- The auditor returns a structured verdict; the controller stores it as an audit with `executor` derived from the task record (never caller-supplied), enforces independence, and stores audits and events append-only with hash chaining (AUD-R5-008).
- Re-audit after correction is a new audit linked by `previous_audit_id`; the executor cannot be the re-auditor.

### 4.7 Traceability (`traceability.py`)

- Required fields and hashes for every release manifest; approval required for staging and production targets; `generate` refuses non-PASS certificates; `validate` re-runs the quality gate with the envelope (AUD-R5-007).
- Fix the `sys.path` anchor (AUD-R5-018) and map CRITICAL to BLOCKED explicitly (AUD-R5-030).

### 4.8 Tests and preflight

- One discovery-based runner; the adversarial suite (E1 to E14, T1 to T5, P1, P2) as deterministic regression tests; real OpenCode probes opt-in with recorded outputs (AUD-R5-019).
- Preflight checks become behavioural: canary directory, discovery in target context, permission profile, configured model, OpenCode version (AUD-R5-025, AUD-R5-033).

## 5. Permission model

| Agent group | Shell | Edit/write | Task (delegation) | Network | Notes |
|---|---|---|---|---|---|
| AG-001 coordinator | Deny (controller runs commands) | Deny outside controller-owned state | Allow to subagents | Deny | Normative: may not approve own work |
| Developers (AG-008..AG-011) | Restricted allowlist inside worktree (**PROBE**) | Inside task worktree only | Deny | Deny | Normative limits: no production credentials |
| QA and performance (AG-012, AG-014) | Restricted allowlist (test commands) | Deny (reports via envelope) | Deny | Deny | Results are evidence, not edits |
| Reviewers and auditors (AG-002, AG-003, AG-013, AG-015) | Deny | Deny | Deny | Deny | Invoked by controller only |
| Architects and analysts (AG-004..AG-007) | Deny | Documents in worktree only | Deny | Deny | Outputs are documents |
| DevOps and deployment (AG-016, AG-017) | Deny in controller-owned staging runs; release commands executed by controller after approval | Packaging files in worktree only | Deny | Deny | AG-017 may prepare, never execute production |
| Documentation (AG-018) | Deny | Documents in worktree only | Deny | Deny | |

The table is a target. Its exact expression in OpenCode permission syntax must be verified (**PROBE**) and generated from the normative definitions so that the executable and normative permissions cannot drift (AUD-R5-001, AUD-R5-014).

## 6. Implementation sequence

Each release has an exit condition that must be demonstrated on the release commit and then re-audited by an auditor who did not implement it.

### R5.2 — Security and truth of state (first, mandatory)

Scope: AUD-R5-019 (test runner first), AUD-R5-001, AUD-R5-002, AUD-R5-003, AUD-R5-004, AUD-R5-006, AUD-R5-007, AUD-R5-010, AUD-R5-012, AUD-R5-014, AUD-R5-015 (minimal allowlist), AUD-R5-017 (envelope, minimum), AUD-R5-018, AUD-R5-024, AUD-R5-025, AUD-R5-026 (context files), AUD-R5-020 (records), AUD-R5-028, AUD-R5-033.

Exit conditions: the adversarial regression set passes; L1 probe fails; L3 canary matches for 20 consecutive runs; E13 yields 20 successes for 20 consecutive runs; T1 to T5 refused or corrected; approval gates release and deployment actions; declared test command covers every module.

Note: R5.2 must not continue to rely on the current `feature/r5.2-workflow-integrity` changes without re-audit. Several of its fixes (audit triggers, resume, migration wiring, cycle detection, BLOCKED status) are worth keeping after verification.

### R5.3 — Workflow semantics and state integrity

Scope: AUD-R5-005 (stage execution), AUD-R5-016 (lifecycle binding), AUD-R5-011 (retry limit, lease, correction loop), AUD-R5-013 (brief, status mapping, change capture), AUD-R5-022 (referential integrity), AUD-R5-023 (schema conformance), AUD-R5-030, AUD-R5-034 (initial refactor).

Exit conditions: E4, E4b, E4d, E4e refused or BLOCKED with reasons; a two-stage run executes in order; seventh attempt refused; live lease not recovered; execution records contain brief hash, before and after commits and changed files; schema conformance test passes.

### R5.4 — Native delegation and independent audit flow

Scope: AUD-R5-009 (AG-001 coordinated pattern, delegation records, event parsing), AUD-R5-008 (audit flow and event chain), AUD-R5-027 (process groups, event classification), AUD-R5-017 (re-audit independence).

Prerequisite probes: capture a benign task-tool delegation event fixture; verify that AG-001 cannot delegate outside its permission profile; verify that an auditor invoked by the controller cannot write.

Exit conditions: one controlled delegation from AG-001 to a subagent produces a complete delegation record; an audit of that subagent's work by AG-002 is recorded with an independent executor; a self-audit attempt is refused.

### R5.5 — Release, approval and staging drill

Scope: AUD-R5-006 (full approval binding, expiry, single use), AUD-R5-007 (release gate hardening), AUD-R5-021 (reproducible PROJECT-001 release, new approval), AUD-R5-032 (backup, export, logs), AUD-R5-031 (pagination, identifiers).

Exit conditions: release REL with a new approval validates PASS from a clean clone; the same release without approval is BLOCKED; approval for another commit is refused; staging deploy and rollback are executed through the controller, with evidence and a backup restore check.

### R5.6 — Pilot preparation and independent re-audit

Scope: reconcile records; execute the R5 pilot runbook against an isolated copy of an approved project in staging; re-audit the exact commit; update `R5_PILOT_READINESS_ASSESSMENT.md` with a new verdict.

Exit conditions: `R5_PILOT_READINESS_ASSESSMENT.md` verdict READY (or READY_WITH_RESTRICTIONS with the restrictions accepted by the human operator) for the exact commit.

## 7. Items deliberately not recommended

- Replacing OpenCode delegation with a custom agent-to-agent protocol. OpenCode already provides the task tool and permission controls; the correction is to record and bound its use.
- Adding a second orchestration framework, message broker or workflow engine. SQLite with a transition engine is adequate for the pilot scale; the defects are in enforcement, not in technology.
- Rewriting the Quality Gate or traceability validators. They are correct for well-formed input; the change is to fail closed and to require provenance.
- Adding agents. The 18-agent catalogue is consistent; the gaps are controller functions (approval, audit flow, delegation records), not agent roles.
- Moving to PostgreSQL now. ADR-005 keeps SQLite for the local implementation; revisit only if concurrency requirements exceed what the transition engine delivers.
- Automatic production deployment. ADR-002 forbids it.

## 8. Risks and trade-offs requiring human decisions

1. **Materialising agent definitions into worktrees** duplicates files; the benefit is deterministic discovery and bounded permissions. Decide whether generated copies are committed or ephemeral.
2. **Restricted shell allowlists for developers** reduce capability; decide which commands (build, test, lint) each stack needs.
3. **Sandboxing** (container or bubblewrap-style) adds an operational dependency; decide the sandbox technology for the host.
4. **Pinned OpenCode version** may delay updates; decide the upgrade procedure (test with the audit probes before adoption).
5. **Source-of-truth model** (section 3) changes how evidence is committed; decide whether snapshots are committed by the controller or by the human.
6. **Approver roster** must be maintained; decide who may approve pilot and release actions.

Each decision should be recorded as a new ADR, not by editing ADR-001 to ADR-006.

## 9. Prerequisite probes before R5.2 and R5.4

Run in scratch directories only, with benign prompts and no repository writes:

1. Non-interactive `ask` without `--auto`: auditor shell write; developer shell write outside and inside a worktree; edit probe on a developer.
2. Working directory canary: 20 consecutive runs with `PWD` set and with `--standalone`; record the reported directories.
3. Discovery: `opencode debug agents` and `opencode run` from a worktree with materialised `.opencode/`, 20 consecutive times; record agreement.
4. Task-tool delegation: one benign AG-001 run that delegates a trivial question to one subagent; store the full JSON event stream as a fixture.
5. Error events: an invocation with an invalid model; store the error event fixture (already observed: `provider.no-route`).

Record each probe's command, environment (`PWD`, cwd, OpenCode version), and output in an evidence file before using its result as a design basis.

## 10. Summary

The factory's design is sound and its components are real. The remediation path is to make the enforcement real, in this order: safe execution (no `--auto`, correct directory, bounded environment), truthful state (single transition engine, fail-closed gates, enforced approvals and audit independence), then delegation and the audit flow that the original architecture intends. Each step is a targeted change to an existing component, verified by the adversarial suite that this audit has already defined.
