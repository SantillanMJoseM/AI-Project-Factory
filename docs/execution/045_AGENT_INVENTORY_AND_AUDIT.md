# Agent Inventory and Audit (Stage 040)

Date: 2026-11-25
Coordinator: AG-001

## 1. Normative agents (18)

| ID | Name | Domain | Mode | Version | Model (exec) | Skills |
|---|---|---|---|---|---|---|
| AG-001 | Project Coordinator | management | primary | 0.2.0 | beam-free (routing: glm-5.3-flash) | writing-plans, executing-plans, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, git-advanced-workflows, architecture-decision-records |
| AG-002 | Quality Gatekeeper | management | subagent | 0.2.0 | beam-free (routing: deepseek-v4.1-flash) | verification-before-completion, code-review-excellence |
| AG-003 | Security & Risk Manager | management | subagent | 0.2.0 | beam-free (routing: glm-5.3) | stride-analysis-patterns, threat-mitigation-mapping, attack-tree-construction, security-requirement-extraction, sast-configuration, secrets-management |
| AG-004 | Business Analyst | analysis | subagent | 0.3.0 | beam-free (routing: qwen3.8-flash) | security-requirement-extraction, api-design-principles, architecture-decision-records |
| AG-005 | Software Architect | analysis | subagent | 0.3.0 | beam-free (routing: kimi-k2.7-code) | architecture-patterns, architecture-decision-records, microservices-patterns, grounded-vault |
| AG-006 | UX/UI Designer | analysis | subagent | 0.3.0 | beam-free (routing: qwen3.8-flash) | visual-design-foundations, design-system-patterns, tailwind-design-system, responsive-design, interaction-design, accessibility-compliance, web-component-design, wcag-audit-patterns |
| AG-007 | Database Architect | analysis | subagent | 0.3.0 | beam-free (routing: deepseek-v4.1-flash) | postgresql-table-design, database-migration, sql-optimization-patterns |
| AG-008 | Backend Developer | development | subagent | 0.4.0 | beam-free (routing: kimi-k2.7-code) | nodejs-backend-patterns, api-design-principles, auth-implementation-patterns, error-handling-patterns, microservices-patterns, openapi-spec-generation, receiving-code-review, git-advanced-workflows |
| AG-009 | Frontend Developer | development | subagent | 0.4.0 | beam-free (routing: kimi-k2.7-code) | web-component-design, tailwind-design-system, responsive-design, interaction-design, visual-design-foundations, javascript-testing-patterns, e2e-testing-patterns, receiving-code-review |
| AG-010 | Database Developer | development | subagent | 0.4.0 | beam-free (routing: deepseek-v4.1-flash) | postgresql-table-design, database-migration, sql-optimization-patterns, receiving-code-review |
| AG-011 | Integration Engineer | development | subagent | 0.4.0 | beam-free (routing: deepseek-v4.1-flash) | microservices-patterns, api-design-principles, auth-implementation-patterns, secrets-management, deployment-pipeline-design, receiving-code-review, git-advanced-workflows |
| AG-012 | QA Automation Engineer | quality | subagent | 0.5.0 | beam-free (routing: qwen3.8-flash) | test-driven-development, javascript-testing-patterns, python-testing-patterns, e2e-testing-patterns, bats-testing-patterns, debugging-strategies, verification-before-completion |
| AG-013 | Code Reviewer | quality | subagent | 0.5.0 | beam-free (routing: glm-5.3-flash) | code-review-excellence, receiving-code-review, requesting-code-review, avoid-ai-writing |
| AG-014 | Performance Engineer | quality | subagent | 0.5.0 | beam-free (routing: deepseek-v4.1-flash) | python-performance-optimization, sql-optimization-patterns, debugging-strategies |
| AG-015 | Security Auditor | quality | subagent | 0.5.0 | beam-free (routing: glm-5.3) | sast-configuration, stride-analysis-patterns, threat-mitigation-mapping, attack-tree-construction, security-requirement-extraction, secrets-management |
| AG-016 | DevOps Engineer | delivery | subagent | 0.6.0 | beam-free (routing: qwen3.8-flash) | deployment-pipeline-design, github-actions-templates, gitlab-ci-patterns, gitops-workflow, k8s-manifest-generator, terraform-module-library, secrets-management, sast-configuration, bats-testing-patterns |
| AG-017 | Deployment Manager | delivery | subagent | 0.6.0 | beam-free (routing: beam-free) | deployment-pipeline-design, gitops-workflow, github-actions-templates |
| AG-018 | Documentation Engineer | delivery | subagent | 0.6.0 | beam-free (routing: qwen3.8-flash) | changelog-automation, hads, avoid-ai-writing, grounded-vault, architecture-decision-records, openapi-spec-generation |

## 2. Executable specialization (AG-003)

| ID | File | Role | Model (routing) |
|---|---|---|---|
| AG-003 | ag-003-security-risk-manager.md | Security & Risk Manager (LEVEL A/B/C) | glm-5.3 |
| AG-003 | ag-003-security-risk-assessor.md | Security Risk Assessor (vulnerability/compliance) | glm-5.3 |

Both share the same skill set and permissions. Documented in `docs/execution/032_STAGE2O_AG003_IDENTITY_PROPOSAL.md`.

## 3. Audit findings

- **Roles:** Clear, non-overlapping. Each agent has a defined objective, responsibilities, limits, inputs, outputs, and acceptance criteria.
- **Permissions:** Minimum privilege applied. `execute`/`webfetch`/`websearch`/`external_directory` denied for all. `shell`/`edit`/`write` ask or deny per role.
- **Skills:** 54 Skills distributed across 19 agent profiles. No agent lacks essential skills; no skill is unused (all assigned to at least one agent).
- **Model routing:** V2 assigns models by task complexity. BEAM_FREE_ONLY preserved as rollback.
- **Dependencies:** Contracts, schemas, workflows, policies all documented per agent.
- **No redundancies:** Each agent has a distinct purpose. AG-003's two specializations are complementary, not duplicate.
- **Security:** No agent has excessive permissions. External directory access denied for all. Secrets not in repo.
- **Delegation:** AG-001 delegates to ag-* only. Independent audit by AG-002. QA by AG-013.

## 4. Per-agent test status

| Agent | Synthetic task test | Status |
|---|---|---|
| AG-001 | Coordination (delegation test) | LIVE_VERIFIED |
| AG-002 | Independent review (delegation test) | LIVE_VERIFIED |
| AG-003 (both) | Not individually tested | NOT_TESTED |
| AG-004 | Not individually tested | NOT_TESTED |
| AG-005 | Synthetic module creation | LIVE_VERIFIED |
| AG-006..AG-018 | Not individually tested | NOT_TESTED |

Recommendation: Create per-agent synthetic task tests in future stages. Current evidence supports LIVE_VERIFIED for AG-001, AG-002, AG-005.