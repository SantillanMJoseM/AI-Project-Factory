# CHANGELOG

## R5.2A - 2026-11-05

### Added

- Atomic/idempotent migration 4 for R5.2A execution integrity.
- `OpenCodeSandbox` with private `opencode serve` inside `unshare -Urm`.
- Fail-closed `OpenCodeAdapter` without `--auto`, with env allowlist and explicit PWD.
- Agent permission restrictions: AG-001 delegates only to `ag-*`; all factory agents deny `execute`.
- R5.2A test traceability fixes (AC-027, AC-028, AC-to-test mapping).
- Installation scripts and documentation under `install/`.
- ProjectDesk pilot execution and `orchestration/pilot_runner.py`.
- Pilot report: `docs/pilot/FACTORY_FIRST_INSTALL_AND_PROJECTDESK_REPORT.md`.

### Changed

- Development agents use `write: allow` for non-interactive pilot execution.
- `orchestration/preflight/r5_preflight.py` no longer uses `--auto`.

### Pilot result

- PILOT_SUCCESS_WITH_LIMITATIONS.
- Factory tests: PASS; ProjectDesk tests: 30 PASS.
- ProjectDesk branch pushed to `AI-Project-Factory-Pilot`.

## R5.1 - 2026-11-04

### Added

- Agent runtime integration remediation.
- Contract-aligned task states.
- SQLite migration v2.
- OpenCode adapter isolation.
- Task and workflow execution.
- R5.1 audit PASS.

## R5 Preparation - 2026-11-04

### Added

- R5 pilot documentation.
- R5 environment preflight command.
- Controlled invocation evidence.
- R5 preparation audit PASS.

## R4 - 2026-11-04

### Added

- PROJECT-001 functional and security remediation.
- Authentication, authorization, and user isolation.
- Complete task API and frontend.
- Database decision and sessions.
- Quality certification and traceability.
- R4 final audit PASS.

## R3 - 2026-11-04

### Added

- Persistent orchestration runtime.
- SQLite registries and state machine.
- Workflow engine and recovery.
- OpenCode adapter and CLI.
- 28 runtime tests.
- R3 final audit PASS.

## R2 - 2026-11-04

### Added

- Artifact & Release Traceability Engine.
- Traceability validator and CLI.
- Schema traceability fields.
- AG-002, AG-016, AG-017 integration.
- 20 traceability tests.
- R2 final audit PASS.

## R1 - 2026-11-04

### Added

- Executable Quality Gate Runtime and CLI.
- Quality certificate evaluation_id requirement.
- AG-002 runtime integration.
- Runtime tests and real-case reproduction.
- R1 final audit PASS.

## 0.6.0 - 2026-11-04

### Added

- F5 DevOps & Deployment Engine: AG-016 to AG-018.
- DevOps contracts and schemas.
- F5 workflow and Quality Gates.
- Demo pipeline, rollback, release manifest, runbook.
- F5 final audit PASS.

### Published

- Remote: https://github.com/SantillanMJoseM/AI-Project-Factory.git
- Branch: main
- Commit: dbdc242018b1489806261b79f64fefd24bc64f58
- Tags: v0.1.0-f0, v0.2.0-f1, v0.3.0-f2, v0.4.0-f3, v0.5.0-f4, v0.6.0-f5
- Clean clone tests: PASS

## 0.5.0 - 2026-11-04

### Added

- F4 Quality & Testing Engine: AG-012 to AG-015.
- Quality contracts and schemas.
- F4 workflow and Quality Gates.
- Technology detection.
- Demo quality reports and Quality Certificate.
- F4 final audit PASS.

## 0.4.0 - 2026-11-04

### Added

- F3 Development Engine: AG-008 to AG-011.
- Development contracts and schemas.
- F3 workflows and Quality Gates.
- Demo implementation with backend, frontend, database, integration, and tests.
- F3 final audit PASS.

## 0.3.0 - 2026-11-04

### Added

- F2 Intelligence & Architecture Engine: AG-004 to AG-007.
- 7 F2 JSON Schemas.
- F2 workflow, Quality Gates, project template.
- Sample project deliverables.
- F2 tests and integration tests.
- F2 final audit PASS.

## 0.2.0 - 2026-11-04

### Added

- F1 agent control core: AG-001, AG-002, AG-003 functional definitions and OpenCode agents.
- Coordination, audit, and security workflows.
- Risk and defect severity matrices.
- F1 tests and 8 integration tests.
- F1 final audit PASS.

## 0.1.0 - 2026-11-04

### Added

- F0 foundation: repository structure, persistent context, contracts, schemas, agent catalog, workflows, Quality Gates, OpenCode integration, tests, audit.