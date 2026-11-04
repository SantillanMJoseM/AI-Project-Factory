# PROJECT_CONTEXT

## Identity

- Name: AI-Project-Factory
- Version: 0.6.0
- Runtime: OpenCode
- Autonomy: supervised
- Scope: universal
- VCS: Git

## Objective

Build a multi-agent platform that receives requirements, analyzes projects, designs architecture, develops software, executes tests, performs independent audits, and prepares controlled deployments. Human approval is mandatory for critical operations and production deployment.

## Architecture

Modular, extensible, provider-decoupled. Persistent repository state is the source of truth. Agent definitions, contracts, schemas, policies, workflows, Quality Gates, and OpenCode integration are stored in the repository.

## Repository structure

See `PROJECT_MAP.md`.

## Components

- Persistent context files (root).
- OpenCode integration (`.opencode/`, `integrations/opencode/`).
- Normative agent catalog (`agents/`), including AG-004 to AG-007.
- Contracts (`contracts/`) and JSON Schemas (`schemas/`), including F2 schemas.
- Orchestration (`orchestration/`).
- Standards (`standards/`).
- Quality Gates (`quality-gates/`).
- Templates (`templates/`).
- Tests (`tests/`).
- Documentation (`docs/`).
- Generated projects (`projects/`).

## Agent catalog

18 agents: AG-001 to AG-018. See `agents/` and `.opencode/agents/`.

## Contracts

- Agent Contract: `contracts/agent-contract.md`
- Task Contract: `contracts/task-contract.md`
- Execution Contract: `contracts/execution-contract.md`
- Audit Contract: `contracts/audit-contract.md`

## Schemas

- `schemas/agent.schema.json`
- `schemas/task.schema.json`
- `schemas/execution.schema.json`
- `schemas/audit.schema.json`

## Security policies

No real credentials in repository. Supervised autonomy. Human approval for critical and production operations. Independent auditor cannot be the developer. See `standards/security/`.

## Development rules

See `standards/` and `AGENTS.md`. Tests must run before stage closure.

## Key decisions

See `PROJECT_DECISIONS.md`.

## Known restrictions

OpenCode agent definitions use installed OpenCode syntax. Model selection is not hard-coded; provider/model can be changed without losing definitions or state.

## References

- `PROJECT_MAP.md`
- `docs/architecture/`
- `integrations/opencode/`