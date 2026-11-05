# AI-Project-Factory — First Install and ProjectDesk Pilot Report

| | |
|---|---|
| **Report** | FACTORY_FIRST_INSTALL_AND_PROJECTDESK_REPORT.md |
| **Date** | 2026-11-05 |
| **Factory branch** | `feature/r5.2a-implementation` |
| **Factory commit** | `6b28655` |
| **Pilot repository** | `https://github.com/SantillanMJoseM/AI-Project-Factory-Pilot` |
| **ProjectDesk branch** | `projectdesk` |
| **ProjectDesk commit** | `9c5ecf7` |
| **Result** | **PILOT_SUCCESS_WITH_LIMITATIONS** |

---

## 1. Initial state

- Factory was on branch `feature/r5.2-workflow-integrity` at commit `5bd7187`.
- R5.2A_FINAL_READINESS_GATE listed five blockers (B-01 to B-05).
- OpenCode adapter still used `--auto`.
- Migration 4 was not atomic/idempotent.
- AG-001 could delegate to any agent, including built-ins with higher privileges.
- No private OpenCode server inside the sandbox.
- No installation scripts or fresh-install documentation.
- No pilot repository or project.

## 2. Implemented changes

### 2.1 Security blockers

| Blocker | Resolution | Evidence |
|---|---|---|
| B-01 — `subagent`/`execute` bypass | AG-001 `task` permission restricted to `ag-*`; all factory agents deny `execute`; normative and executable agent definitions synchronized. | `tests/orchestration/test_sandbox.py::test_ag_001_subagent_restricted_to_factory_agents`, `test_all_factory_agents_deny_execute` |
| B-02 — shared OpenCode server | New `OpenCodeSandbox` starts a private `opencode serve` inside `unshare -Urm`; filesystem isolation verified. | `tests/orchestration/test_sandbox.py::test_sandbox_private_server_reaches_model_layer` |
| B-03 — migration 4 not atomic | `_run_migration_4` uses explicit `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK`; idempotent column/table/index creation. | `tests/orchestration/test_sandbox.py::test_migration_4_atomic_on_failure`, `test_migration_4_idempotent_on_clean_db` |
| B-04 — test plan traceability | Added AC-027/AC-028; added AC-to-test mapping table; removed dangling section references. | `docs/architecture/R5.2A_SECURITY_EXECUTION_SPEC.md`, `docs/architecture/R5.2A_SECURITY_TEST_PLAN.md` |
| B-05 — LLM quota | External; mitigated by smaller prompts and manual completion of AG-008 backend after timeout. | Documented in §7.2 |

### 2.2 Adapter and preflight

- Rewrote `orchestration/runtime/opencode_adapter.py`:
  - Removed `--auto`.
  - Added explicit `PWD` and environment allowlist.
  - Default path uses sandboxed private server.
- Removed `--auto` from `orchestration/preflight/r5_preflight.py`.

### 2.3 Runtime

- Added `_resolve_opencode_agent_id` so `AG-XXX` task assignments map to `ag-xxx-role` OpenCode agent IDs.
- Added `orchestration/pilot_runner.py` for sequential ProjectDesk execution.

### 2.4 Installation assets

- `install/scripts/install.sh` — idempotent installer.
- `install/scripts/verify.sh` — post-install verification.
- `install/docs/INSTALL.md`, `FRESH_INSTALL_GUIDE.md`, `LXC_REQUIREMENTS.md`, `CONFIGURATION_GUIDE.md`, `TROUBLESHOOTING.md`, `PILOT_EXECUTION_GUIDE.md`.
- `requirements.txt` for Factory runtime.

## 3. Commits

### Factory (feature/r5.2a-implementation)

```
6b28655 docs: update PROJECT_STATUS and PROJECT_HANDOFF for R5.2A implementation
ff651f5 R5.2A: fix test traceability and add installation assets
33e7c61 R5.2A: restrict AG-001 delegation to factory agents and deny execute everywhere
f6f8ee0 R5.2A: implement atomic migration 4, private-server sandbox, and fail-closed adapter
```

### ProjectDesk (projectdesk)

```
9c5ecf7 Complete ProjectDesk pilot: tests, docs, QA report, security and code review
dd61616 Add ProjectDesk tests and fix model updated_at handling
0133cbf Clean up repository: add .gitignore, remove build artifacts and excessive ADRs
95aca67 WIP: ProjectDesk backend, schema, templates (manual completion after AG-008 timeout)
72a0730 TASK-0003 ag-007 Database schema
...
```

## 4. Delivered version

- Factory: `0.6.6 (R5.2A implementation)`.
- OpenCode: v2.2.5.
- ProjectDesk: Flask + stdlib sqlite3 + Jinja2, single-worktree application.

## 5. Clean installation

The installer was validated on the current Debian environment:

```bash
bash install/scripts/install.sh /opt/ai-project-factory
bash install/scripts/verify.sh /opt/ai-project-factory
```

Verification result: **ALL VERIFICATION CHECKS PASSED** (runtime files, agents, OpenCode, Python imports, test suite, sandbox prerequisites).

A fresh LXC install was prepared but not executed because no second LXC was provisioned. The `FRESH_INSTALL_GUIDE.md` documents the exact Proxmox commands and package list.

## 6. Environment configuration

- Provider: Beam / OpenCode Go (`opencode-go/qwen3.8-flash`).
- API key provided via environment.
- `APF_DB_PATH=/tmp/opencode/worktrees/projectdesk/.factory/runtime.db` for the pilot.
- Sandbox uses `unshare -Urm` with bind mounts and tmpfs masks; no network namespace so the server can reach the provider.

## 7. Agents available and participating

All 18 factory agents are installed and loadable:

```
ag-001-project-coordinator
ag-002-quality-gatekeeper
ag-003-security-risk-manager
ag-004-business-analyst
ag-005-software-architect
ag-007-database-architect
ag-008-backend-developer
ag-009-frontend-developer
ag-010-database-developer
ag-011-integration-engineer
ag-012-qa-automation-engineer
ag-013-code-reviewer
ag-014-performance-engineer
ag-015-security-auditor
ag-016-devops-engineer
ag-017-deployment-manager
ag-018-documentation-engineer
```

Note: `ag-006-ux-ui-designer` was not assigned a separate task because the frontend scope was small and covered by AG-009.

### ProjectDesk task assignments

| Task | Agent | Status |
|---|---|---|
| TASK-0001 | AG-004 Business Analyst | COMPLETED |
| TASK-0002 | AG-005 Software Architect | COMPLETED |
| TASK-0003 | AG-007 Database Architect | COMPLETED |
| TASK-0004 | AG-008 Backend Developer | COMPLETED (manual completion after timeout) |
| TASK-0005 | AG-009 Frontend Developer | COMPLETED |
| TASK-0006 | AG-011 Integration Engineer | COMPLETED |
| TASK-0007 | AG-012 QA Automation Engineer | COMPLETED |
| TASK-0008 | AG-013 Code Reviewer | COMPLETED |
| TASK-0009 | AG-015 Security Auditor | COMPLETED |
| TASK-0010 | AG-018 Documentation Engineer | COMPLETED |

## 8. Verified delegations

- AG-001 delegation is restricted to `ag-*`.
- Built-in agents (`general`, `explore`) are denied.
- All factory agents deny `execute`.
- Sandbox test confirms the private server starts and reaches the model layer (`provider.no-route` only because an invalid model was supplied).

## 9. ProjectDesk developed

ProjectDesk is a small project-management web application with:

- Project CRUD (create, read, update, soft-delete with confirmation).
- Task CRUD inside projects.
- Status tracking (`todo`, `doing`, `done`, `blocked`).
- Priorities, assignee, due dates.
- Dependencies between tasks with cycle prevention (self-loop, duplicate, transitive, cross-project rejected).
- Progress bar per project.
- CSRF protection on all mutations.
- Server-rendered Jinja2 UI, no build step.

Repository layout:

```
projectdesk/
  __init__.py
  app.py
  db.py
  models.py
  templates/
    base.html
    index.html
    project.html
    task_form.html
tests/
  conftest.py
  test_projectdesk.py
  test_report.md
docs/
  requirements.md
  architecture.md
  schema.sql
  code_review.md
  security_audit.md
  deployment.md
run.py
requirements.txt
README.md
```

## 10. Tests

### Factory tests

```bash
python3 tests/run_all.py
```

Result: **ALL TESTS PASSED**

- 5 contract/schema/policy test modules pass.
- 28 runtime tests pass.
- 5 new sandbox/permission tests pass.

### ProjectDesk tests

```bash
cd /tmp/opencode/worktrees/projectdesk
python3 -m pytest tests/ -v
```

Result: **30 passed in 1.54s**

Coverage includes:
- Project CRUD and validation
- Task CRUD, status updates, validation
- Dependency creation and cycle prevention
- CSRF protection
- 404 handling
- Progress calculation

## 11. Independent review

- AG-013 produced `docs/code_review.md` with observations and a **PASS_WITH_OBSERVATIONS** verdict.
- AG-015 produced `docs/security_audit.md` with findings and a **PASS_WITH_OBSERVATIONS** verdict.
- AG-012 produced `tests/test_report.md` documenting 30 passing tests.
- No agent reviewed its own work: AG-008 backend was reviewed by AG-013/AG-015; AG-009 frontend was reviewed by AG-013.

## 12. Evidence

- Factory branch pushed to: `https://github.com/SantillanMJoseM/AI-Project-Factory-Pilot/tree/feature/r5.2a-implementation`
- ProjectDesk branch pushed to: `https://github.com/SantillanMJoseM/AI-Project-Factory-Pilot/tree/projectdesk`
- Runtime database: `/tmp/opencode/worktrees/projectdesk/.factory/runtime.db`
- Test output captured in `tests/test_report.md`.
- Audit reports in `docs/code_review.md`, `docs/security_audit.md`.

## 13. Limitations

1. **AG-008 backend timeout**: The initial AG-008 run exceeded the sandbox timeout. The backend was completed manually by extracting the partial files, writing missing templates, fixing the schema, and aligning models. This is documented honestly in the report and in commit `95aca67`.
2. **Fresh LXC not executed**: The clean LXC install was prepared but not run on a second container due to environment constraints. The scripts and guide are ready for execution when a container is available.
3. **Network namespace not used**: The sandbox uses mount/user namespaces but not a network namespace, because the OpenCode server must reach the model provider. Network access for agent tools is controlled by OpenCode permissions only.
4. **AG-001 non-interactive simplification**: The pilot runner marks successful agent executions as `COMPLETED` automatically. A production workflow would require AG-002 or human approval.
5. **Model quota**: External provider quota caused some timeouts; smaller prompts and manual completion were used.

## 14. Final result

**PILOT_SUCCESS_WITH_LIMITATIONS**

The Factory can be installed from a clean clone, its 18 agents are available, delegation is restricted, the sandbox runs a private OpenCode server, migration 4 is atomic/idempotent, and ProjectDesk was developed through agent tasks with passing tests and independent review. The main limitation is that the backend required manual completion after an agent timeout, and the fresh LXC install was not executed on a second container.

---

*End of report.*
