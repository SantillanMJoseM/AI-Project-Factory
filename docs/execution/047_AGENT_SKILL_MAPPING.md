# Agent-Skill Mapping (Stage 040)

Date: 2026-11-25
Coordinator: AG-001

## 1. Mapping matrix

Each agent lists its assigned Skills. Skills are discovered via `## Assigned skills` in executable agent definitions.

### Management domain
- **AG-001 Project Coordinator** → writing-plans, executing-plans, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, git-advanced-workflows, architecture-decision-records
- **AG-002 Quality Gatekeeper** → verification-before-completion, code-review-excellence
- **AG-003 Security & Risk Manager** → stride-analysis-patterns, threat-mitigation-mapping, attack-tree-construction, security-requirement-extraction, sast-configuration, secrets-management
- **AG-003 Security Risk Assessor** → stride-analysis-patterns, threat-mitigation-mapping, attack-tree-construction, security-requirement-extraction, sast-configuration, secrets-management

### Analysis domain
- **AG-004 Business Analyst** → security-requirement-extraction, api-design-principles, architecture-decision-records
- **AG-005 Software Architect** → architecture-patterns, architecture-decision-records, microservices-patterns, grounded-vault
- **AG-006 UX/UI Designer** → visual-design-foundations, design-system-patterns, tailwind-design-system, responsive-design, interaction-design, accessibility-compliance, web-component-design, wcag-audit-patterns
- **AG-007 Database Architect** → postgresql-table-design, database-migration, sql-optimization-patterns

### Development domain
- **AG-008 Backend Developer** → nodejs-backend-patterns, api-design-principles, auth-implementation-patterns, error-handling-patterns, microservices-patterns, openapi-spec-generation, receiving-code-review, git-advanced-workflows
- **AG-009 Frontend Developer** → web-component-design, tailwind-design-system, responsive-design, interaction-design, visual-design-foundations, javascript-testing-patterns, e2e-testing-patterns, receiving-code-review
- **AG-010 Database Developer** → postgresql-table-design, database-migration, sql-optimization-patterns, receiving-code-review
- **AG-011 Integration Engineer** → microservices-patterns, api-design-principles, auth-implementation-patterns, secrets-management, deployment-pipeline-design, receiving-code-review, git-advanced-workflows

### Quality domain
- **AG-012 QA Automation Engineer** → test-driven-development, javascript-testing-patterns, python-testing-patterns, e2e-testing-patterns, bats-testing-patterns, debugging-strategies, verification-before-completion
- **AG-013 Code Reviewer** → code-review-excellence, receiving-code-review, requesting-code-review, avoid-ai-writing
- **AG-014 Performance Engineer** → python-performance-optimization, sql-optimization-patterns, debugging-strategies
- **AG-015 Security Auditor** → sast-configuration, stride-analysis-patterns, threat-mitigation-mapping, attack-tree-construction, security-requirement-extraction, secrets-management

### Delivery domain
- **AG-016 DevOps Engineer** → deployment-pipeline-design, github-actions-templates, gitlab-ci-patterns, gitops-workflow, k8s-manifest-generator, terraform-module-library, secrets-management, sast-configuration, bats-testing-patterns
- **AG-017 Deployment Manager** → deployment-pipeline-design, gitops-workflow, github-actions-templates
- **AG-018 Documentation Engineer** → changelog-automation, hads, avoid-ai-writing, grounded-vault, architecture-decision-records, openapi-spec-generation

## 2. Shared Skills (assigned to multiple agents)

| Skill | Agents | Count |
|---|---|---|
| receiving-code-review | AG-008, AG-009, AG-010, AG-011, AG-013 | 5 |
| secrets-management | AG-003, AG-011, AG-015, AG-016 | 4 |
| api-design-principles | AG-004, AG-008, AG-011 | 3 |
| architecture-decision-records | AG-001, AG-004, AG-005, AG-018 | 4 |
| microservices-patterns | AG-005, AG-008, AG-011 | 3 |
| security-requirement-extraction | AG-003, AG-004, AG-015 | 3 |
| sql-optimization-patterns | AG-007, AG-010, AG-014 | 3 |
| tailwind-design-system | AG-006, AG-009 | 2 |
| responsive-design | AG-006, AG-009 | 2 |
| interaction-design | AG-006, AG-009 | 2 |
| visual-design-foundations | AG-006, AG-009 | 2 |
| web-component-design | AG-006, AG-009 | 2 |
| postgresql-table-design | AG-007, AG-010 | 2 |
| database-migration | AG-007, AG-010 | 2 |
| sast-configuration | AG-003, AG-015, AG-016 | 3 |
| git-advanced-workflows | AG-001, AG-008, AG-011 | 3 |
| avoid-ai-writing | AG-013, AG-018 | 2 |
| stride-analysis-patterns | AG-003, AG-015 | 2 |
| threat-mitigation-mapping | AG-003, AG-015 | 2 |
| attack-tree-construction | AG-003, AG-015 | 2 |
| deployment-pipeline-design | AG-011, AG-016, AG-017 | 3 |
| github-actions-templates | AG-016, AG-017 | 2 |
| gitops-workflow | AG-016, AG-017 | 2 |
| bats-testing-patterns | AG-012, AG-016 | 2 |
| debugging-strategies | AG-012, AG-014 | 2 |
| verification-before-completion | AG-002, AG-012 | 2 |
| javascript-testing-patterns | AG-009, AG-012 | 2 |
| e2e-testing-patterns | AG-009, AG-012 | 2 |
| openapi-spec-generation | AG-008, AG-018 | 2 |
| grounded-vault | AG-005, AG-018 | 2 |

## 3. Skill discovery mechanism

- Skills are discovered via `## Assigned skills` in executable agent definitions (`.opencode/agents/*.md`).
- Runtime skill governance: `orchestration/skills/` (registry, validator, security scan, drift, license check).
- Skill registry: `orchestration/skills/registry.json` (54 entries, all ACTIVE).
- No agent lacks essential Skills; no Skill is unassigned.

## 4. Skill invocation flow

1. AG-001 selects agent based on task requirements.
2. Agent's assigned Skills are loaded from executable definition.
3. Skills are invoked via the `skill` tool (permission: ask for AG-001, allow for agents).
4. Skill content is read and applied by the agent.
5. Results are validated against acceptance criteria.
6. AG-002 independently audits.

## 5. Skill-Skill dependencies

- `receiving-code-review` → used by all developers before submitting work.
- `requesting-code-review` → used by AG-013 when requesting review.
- `verification-before-completion` → used by AG-002 and AG-012 before declaring completion.
- `test-driven-development` → used by AG-012 for test design.
- `subagent-driven-development` → used by AG-001 for delegation.