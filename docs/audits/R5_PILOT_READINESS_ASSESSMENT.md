# R5_PILOT_READINESS_ASSESSMENT

## 1. Overall verdict

**NOT_READY**

The Factory is not ready for a controlled pilot. The pilot plan's own entry criteria are not met: the runtime does not enforce the human-approval, Quality Gate, audit-independence or release controls the pilot depends on; the OpenCode invocation path disables its approval gates and does not reliably run agents in the requested directory; native subagent delegation, which the R5 acceptance criteria require, does not exist.

Basis: `INDEPENDENT_ARCHITECTURAL_AUDIT_R5.md` (baseline `main` at `d3c9cde`). Findings referenced below use the IDs in `R5_REMEDIATION_BACKLOG.md`.

## 2. Verdict per dimension

Labels are restricted to READY, READY_WITH_RESTRICTIONS and NOT_READY.

| Dimension | Verdict | Reason (finding IDs) |
|---|---|---|
| Agent catalogue (18 normative and executable definitions) | READY | Consistent identifiers, modes, domains and permissions (audit section 4) |
| Permission and approval gates in OpenCode invocation | NOT_READY | `--auto` converts `ask` into allow (AUD-R5-001); auditor wrote through its shell (L1) |
| Working directory and repository isolation | NOT_READY | `PWD` inheritance; agent ran in another directory (AUD-R5-002, L3) |
| Secrets and filesystem boundary | NOT_READY | Full environment inherited; no sandbox (AUD-R5-015) |
| Task state integrity | NOT_READY | CLI completion bypass (AUD-R5-003); transition bypasses (AUD-R5-012); duplicate assignment race (AUD-R5-010) |
| Workflow truthfulness and stages | NOT_READY | False COMPLETED on main (AUD-R5-005); stages ignored (E4b; AUD-R5-016); R5.2 still ignores stages |
| Quality Gate correctness | NOT_READY | Validator fail-open (AUD-R5-004); self-reported evidence (AUD-R5-017) |
| Independent audit and audit integrity | NOT_READY | Self-audit accepted and audits mutable on main (AUD-R5-008); no audit flow invokes AG-002 (AUD-R5-009); R5.2 improves audit rows only |
| Human approval | NOT_READY | Approvals recorded but never enforced; any string approves (AUD-R5-006) |
| Native OpenCode delegation (AG-001 to subagents) | NOT_READY | Not implemented or demonstrated (AUD-R5-009) |
| Release traceability and approval | NOT_READY | Passes without approval and with altered artefacts (AUD-R5-007); PROJECT-001 release misbound (AUD-R5-021) |
| Deployment and rollback through the runtime | NOT_READY | No gated deployment or rollback path; F5 is demonstration only |
| Persistence, migration and recovery | READY_WITH_RESTRICTIONS | WAL and busy timeout; migration reachable and tested on R5.2 (E9); resume exists on R5.2; retry and lease controls missing (AUD-R5-011). Acceptable only for single-operator local use |
| Test evidence and claim reliability | NOT_READY | Declared command covers 5 of 17 modules; vacuous tests; unreproduced R5.1 claims (AUD-R5-019, AUD-R5-020) |
| Operator identity and access | NOT_READY | Free-text actors and approvers; database inside the working tree (AUD-R5-024) |
| Documentation and context accuracy | NOT_READY | Stale handoff/status; wrong commit references; duplicate ADR IDs; source-of-truth contradiction (AUD-R5-026) |
| Operability (logs, backup, versions) | READY_WITH_RESTRICTIONS | Single host, manual procedures acceptable for a restricted pilot; no structured logs, backup or pinned OpenCode version (AUD-R5-032, AUD-R5-033) |

## 3. Entry criteria from the R5 pilot plan (`docs/pilots/R5_PILOT_PLAN.md`)

| Entry criterion | Status | Evidence |
|---|---|---|
| Factory tests pass | Met for the declared command only | `tests/run_all.py` passes (37 tests from 5 files); 115 test functions exist (AUD-R5-019) |
| Runtime R3 operational | Not met | False COMPLETED (E4), task run from PENDING fails (E1, main), recovery does not resume (E12, main) |
| R1 and R2 validators available | Partly met | R1 reproduces the R4 verdict with the right evidence directory; R1 fail-open (E6a); R2 cannot call R1 in script mode (T5) |
| OpenCode agents load | Partly met | 18 agents load from the factory tree; project-directory discovery and validation disagree (AUD-R5-014) |
| Human-approved project brief | Not verifiable | No approval mechanism is enforced (AUD-R5-006) |

## 4. Exit criteria from the R5 pilot plan

| Exit criterion | Status |
|---|---|
| Project deployed to isolated staging | Not met (no gated deployment, AUD-R5-007) |
| Rollback tested | Not met for the runtime (F5 demonstration only) |
| Quality certificate valid | Not met as an enforced property (AUD-R5-004, AUD-R5-017) |
| Traceability valid | Not met as an enforced property (AUD-R5-007) |
| Documentation complete | Not met (AUD-R5-026) |
| Independent audit PASS | Not met (no audit flow; AUD-R5-009) |

## 5. Acceptance criteria from `docs/pilots/R5_ACCEPTANCE_CRITERIA.md`

- "Project is registered independently": met for registration; repository existence is not checked (AUD-R5-022).
- "Tasks and executions are persisted": met (SQLite), with reference-integrity gaps (AUD-R5-022).
- "Agent delegation is verified": not met (AUD-R5-009).
- "R1 blocks invalid certificates": not met (AUD-R5-004).
- "R2 validates traceability": partly met (AUD-R5-007, AUD-R5-018).
- "Staging deployment succeeds", "Health checks pass", "Smoke tests pass", "Rollback succeeds": not evidenced for the runtime.
- "No CRITICAL or HIGH defects remain open": not met (7 CRITICAL and 14 HIGH open at baseline).
- "Documentation reflects the deployed system": not met.
- "Independent audit returns PASS": not met.

## 6. Conditions to reach READY_WITH_RESTRICTIONS

All of the following are required. Each condition must be verified on the exact commit proposed for the pilot, with the regression set in `R5_REMEDIATION_BACKLOG.md` section 7.

1. Adapter invocation runs without `--auto`; non-interactive `ask` is verified to fail closed; auditors have no shell and no edit (AUD-R5-001).
2. Working directory is verified by a canary before each run; `PWD` is set explicitly (AUD-R5-002).
3. CLI cannot set a task to COMPLETED; completion requires a stored, passing Quality Gate result for the same task and commit (AUD-R5-003).
4. Quality Gate validator fails closed: mandatory evidence, open-status allow-list, certificate fields consistent with evidence (AUD-R5-004).
5. Workflow runs cannot report COMPLETED with unfinished or unverified work, and run stages in order (AUD-R5-005).
6. Approval gates the production and staging actions, with binding, single use and an allow-listed human approver (AUD-R5-006, AUD-R5-024).
7. Release generation and validation refuse missing approval, missing hashes, FAIL certificates and mismatched commits (AUD-R5-007, AUD-R5-028).
8. Atomic compare-and-set transitions; no duplicate assignment in 20 consecutive concurrency runs (AUD-R5-010).
9. Agent identifiers map deterministically to OpenCode agents; discovery is checked in the execution context; error text is reported (AUD-R5-014).
10. Minimal executor boundary: environment allowlist, and an OS-level sandbox or equivalent restriction limiting writes to the task worktree (AUD-R5-015).
11. The declared test command runs every module; adversarial regression set passes; vacuous tests replaced (AUD-R5-019).
12. The R5 records are corrected with reproduction commands; claims not reproduced are marked NOT VERIFIED (AUD-R5-020).
13. Human-approval procedure and pilot scope documented, reviewed and approved by a named human.

Restrictions that would accompany READY_WITH_RESTRICTIONS:

- A single operator, on a single host, with the runtime database outside the repository working tree.
- Only a copy of a designated project repository in an isolated staging path, with no production credentials and no network egress beyond what the pilot approval names.
- Every executor run individually approved by the human operator; no unattended runs.
- No release publication and no deployment. Staging deployment only after AUD-R5-006 and AUD-R5-007 are closed and a human approval is recorded.
- Every Quality Gate and audit verdict re-verified by the human operator against the evidence envelope before it is relied on.
- No use of PROJECT-001 release artefacts as evidence of a release (AUD-R5-021).

## 7. Conditions to reach READY (full pilot)

In addition to section 6:

1. Native delegation with delegation records, or a documented decision to use direct invocation with recorded `from_agent=RUNTIME` for every subagent call (AUD-R5-009).
2. Independent audit flow invoked by the runtime, with independence derived from the task record and verdicts gating release (AUD-R5-008, AUD-R5-009).
3. Retry limit, lease-based recovery and correction loop (AUD-R5-011).
4. Workflow stages bound to tasks and to Quality Gates QG-01 to QG-06, with project lifecycle driven by the runtime (AUD-R5-016).
5. Event-log and audit integrity (append-only protection and hash chain) (AUD-R5-008, AUD-R5-032).
6. Execution evidence with the complete brief, change capture and adapter error classification (AUD-R5-013, AUD-R5-027).
7. Reconciled documentation and context files; no duplicate decision identifiers (AUD-R5-026).
8. A clean-clone reproduction of the release, including the artefact and approval, for the pilot scope (AUD-R5-021).
9. Pinned OpenCode version recorded and checked (AUD-R5-033).
10. A rollback drill in staging executed through the runtime, with evidence stored.
11. A fresh independent re-audit of the exact commit to be piloted, performed by an auditor who did not implement the change.

## 8. What must not happen before READY_WITH_RESTRICTIONS

- Running `task run` or `workflow run` against any real project repository (AUD-R5-001, AUD-R5-002).
- Using `task status … COMPLETED` or `approval approve` as a workflow step (AUD-R5-003, AUD-R5-006).
- Creating or closing a pilot project as a record of progress (the brief forbids it in this audit; it is also a readiness decision for the human).
- Publishing the R5.1 or R5.2 records as proof of pilot readiness before AUD-R5-020 is closed.

## 9. Decision requested from the human

1. Confirm NOT_READY as the current status of the Factory.
2. Approve the R5.2 scope in `R5_ARCHITECTURAL_RECOMMENDATIONS.md` (security and truth of state first).
3. Decide whether the R5.2 branch `feature/r5.2-workflow-integrity` (commit `5bd7187`) is to be continued, as it fixes several baseline defects, or replaced. Any continuation must be re-audited; its present fixes are not accepted by this assessment.
4. Decide the ownership of the working tree: one worktree per branch, and no concurrent edits to `orchestration/runtime/runtime.py` (AUD-R5-029).
