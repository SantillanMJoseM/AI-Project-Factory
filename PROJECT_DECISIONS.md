# PROJECT_DECISIONS

## ADR-001 - Repository files are the source of truth

- ID: ADR-001
- Date: 2026-11-04
- Context: Need continuity across models and sessions.
- Problem: Conversation memory is not portable.
- Alternatives: database state, external memory service.
- Decision: Use repository files as persistent context.
- Justification: Git versioning and portability.
- Impact: All state must be documented in files.
- Status: vigente

## ADR-002 - Supervised autonomy

- ID: ADR-002
- Date: 2026-11-04
- Context: Production safety.
- Problem: Autonomous deployment risk.
- Alternatives: full automation.
- Decision: Human approval for critical operations and production deployment.
- Justification: Risk control.
- Impact: Quality Gates and deployment manager require approval.
- Status: vigente

## ADR-003 - OpenCode integration uses real installed syntax

- ID: ADR-003
- Date: 2026-11-04
- Context: Avoid invented properties.
- Problem: Need executable agents.
- Alternatives: custom runtime.
- Decision: Use OpenCode markdown agents and JSON config as documented by installed version.
- Justification: Verified against official docs.
- Impact: Provider/model can change without losing definitions.
- Status: vigente

## ADR-004 - Independent audit

- ID: ADR-004
- Date: 2026-11-04
- Context: Quality assurance.
- Problem: Self-approval risk.
- Alternatives: developer self-review.
- Decision: Auditor independent from developer; audit results cannot be altered by audited agent.
- Justification: Objectivity.
- Impact: Separate audit contract and Quality Gate.
- Status: vigente