# Agent Model Assignment Matrix (MODEL_ROUTING_V2)

Date: 2026-11-24
Policy: MODEL_ROUTING_V2 (opt-in via `APF_MODEL_POLICY=MODEL_ROUTING_V2`; default BEAM_FREE_ONLY for rollback).

## Assignment table

| Agent | Primary model | Fallback hierarchy | Tier | Rationale |
|---|---|---|---|---|
| AG-001 Project Coordinator | glm-5.3-flash | [glm-5.3-flash, qwen3.8-flash, beam-free] | T3 (Economy) | Coordination; efficient reasoning |
| AG-002 Quality Gatekeeper | deepseek-v4.1-flash | [deepseek-v4.1-flash, qwen3.8-flash, beam-free] | T2 (Standard) | Independent audit; code analysis |
| AG-003 Security & Risk Manager | glm-5.3 | [glm-5.3, glm-5.3-flash, beam-free] | T1 (Premium) | Security reasoning |
| AG-003 Security Risk Assessor | glm-5.3 | [glm-5.3, glm-5.3-flash, beam-free] | T1 (Premium) | Security assessment |
| AG-004 Business Analyst | qwen3.8-flash | [qwen3.8-flash, qwen3.7-plus, beam-free] | T3 (Economy) | Requirements (economy) |
| AG-005 Software Architect | kimi-k2.7-code | [kimi-k2.7-code, glm-5.3, beam-free] | T1 (Premium) | Architecture (premium) |
| AG-006 UX/UI Designer | qwen3.8-flash | [qwen3.8-flash, qwen3.7-plus, beam-free] | T3 (Economy) | UX (economy) |
| AG-007 Database Architect | deepseek-v4.1-flash | [deepseek-v4.1-flash, deepseek-v4-pro, beam-free] | T2 (Standard) | DB design (standard) |
| AG-008 Backend Developer | kimi-k2.7-code | [kimi-k2.7-code, deepseek-v4.1-flash, beam-free] | T1 (Premium) | Code (premium) |
| AG-009 Frontend Developer | kimi-k2.7-code | [kimi-k2.7-code, deepseek-v4.1-flash, beam-free] | T1 (Premium) | Code (premium) |
| AG-010 Database Developer | deepseek-v4.1-flash | [deepseek-v4.1-flash, qwen3.8-flash, beam-free] | T2 (Standard) | Code (standard) |
| AG-011 Integration Engineer | deepseek-v4.1-flash | [deepseek-v4.1-flash, qwen3.8-flash, beam-free] | T2 (Standard) | Code (standard) |
| AG-012 QA Automation | qwen3.8-flash | [qwen3.8-flash, qwen3.7-plus, beam-free] | T3 (Economy) | Testing (economy) |
| AG-013 Code Reviewer | glm-5.3-flash | [glm-5.3-flash, qwen3.8-flash, beam-free] | T2 (Standard) | Review (standard) |
| AG-014 Performance Engineer | deepseek-v4.1-flash | [deepseek-v4.1-flash, qwen3.8-flash, beam-free] | T2 (Standard) | Analysis (standard) |
| AG-015 Security Auditor | glm-5.3 | [glm-5.3, glm-5.3-flash, beam-free] | T1 (Premium) | Security (premium) |
| AG-016 DevOps Engineer | qwen3.8-flash | [qwen3.8-flash, qwen3.7-plus, beam-free] | T3 (Economy) | DevOps (economy) |
| AG-017 Deployment Manager | beam-free | [beam-free] | T0 (Free) | Deployment coordination (free) |
| AG-018 Documentation Engineer | qwen3.8-flash | [qwen3.8-flash, qwen3.7-plus, beam-free] | T3 (Economy) | Documentation (economy) |

## Notes

- Agent files (`.opencode/agents/*.md`) retain `model: opencode-go/beam-free` as baseline (rollback). The routing policy overrides at runtime when `APF_MODEL_POLICY=MODEL_ROUTING_V2`.
- GLM-5.2 was not available in the catalog; GLM-5.3 is used instead.
- Fallback hierarchies always end with `beam-free` (free reserve).
- No model switching occurs on auth errors (requires intervention).