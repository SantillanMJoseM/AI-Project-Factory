# Stage 039 — Model Routing V2: Implementation Report

Date: 2026-11-24
Coordinator: AG-001 Project Coordinator
Mode: Implementation (authorized by user).

## 1. Blocker: Consumption measurement (BLOCKED)

### Cause
The Go Plus consumption endpoint (`https://opencode.ai/inference/go/v1/usage`) requires authentication via Bearer token (Go API key). The org ID and Go API key are not available in the local environment:
- `~/.config/opencode/service.json` contains only the OpenCode account password (not the Go API key).
- `opencode debug config` redacts the org ID (`"x-opencode-org-id": "***"`).
- No `OPENCODE_API_KEY` or similar env var is set.
- The local opencode serve (port 49374) returns 401 for all API paths.

### Safe local procedure for user validation
Run the following in a terminal (do NOT share the output in chat):
```bash
# 1. Get your Go API key from https://opencode.ai/settings (API Keys section)
# 2. Export it (do not commit):
export OPENCODE_GO_API_KEY="<your-key>"
# 3. Query usage:
curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" https://opencode.ai/inference/go/v1/usage | python3 -m json.tool
# 4. Query models:
curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" https://opencode.ai/inference/go/v1/models | python3 -m json.tool
```

### Status
- **Consumption measurement: BLOCKED** (no Go API key available in environment).
- Design and implementation proceed with conservative limits.
- LIVE verification of consumption: NOT_TESTED.

## 2. Discovered models (opencode-go provider, 33 total)

All user-mentioned candidates available except GLM-5.2 (not in catalog).

| Tier | Models | Use case |
|---|---|---|
| Premium (code) | kimi-k2.7-code, kimi-k3, kimi-k3.1-pro, qwen4-max, qwen3.8-max, deepseek-v4-pro, glm-5.3, mimo-v2.6-pro, mimo-v2.5-pro, gpt-5.6-luna, gpt-6-luna, grok-4.7, claude-haiku-5-5, gemini-4-argon | Architecture, complex development, security |
| Standard | qwen3.7-plus, deepseek-v4.1-flash, glm-5.3-flash, mimo-v2.5, mimo-v2.6-flash, minimax-m3, minimax-m3.1-flash, qwen3.8-flash, longcat-2.5, hy3, hy4, hy4-preview, step-5-preview | Development, QA, documentation |
| Free | beam-free, hungerg-free, hy4-flash-free, iceman-contributor-free, muse-spark-1.2/1.3-contributor | Baseline, fallback reserve |

## 3. MODEL_ROUTING_V2 policy design

### Authorized models (initial set)
All 33 opencode-go models are authorized. BEAM_FREE_ONLY is preserved as rollback option (env var `APF_MODEL_POLICY=BEAM_FREE_ONLY`).

### Routing tiers
| Tier | Models (examples) | Agents | Task complexity |
|---|---|---|---|
| T1 (Premium) | kimi-k2.7-code, glm-5.3, deepseek-v4-pro | AG-005 (architect), AG-003 (security), AG-015 (auditor) | Architecture, security audit, complex reasoning |
| T2 (Standard) | qwen3.7-plus, deepseek-v4.1-flash, glm-5.3-flash | AG-008/009/010/011 (dev), AG-012 (QA) | Development, testing, integration |
| T3 (Economy) | qwen3.8-flash, mimo-v2.6-flash, minimax-m3.1-flash | AG-018 (docs), AG-004 (BA), AG-006 (UX) | Documentation, requirements, UX |
| T0 (Free) | beam-free | AG-001 (coordinator), AG-002 (gatekeeper) | Coordination, quality gate (always free to preserve budget) |

### Agent-to-model assignment (initial)
| Agent | Primary | Rationale |
|---|---|---|
| AG-001 Project Coordinator | beam-free | Coordination; preserve budget |
| AG-002 Quality Gatekeeper | beam-free | Independent audit; preserve budget |
| AG-003 Security & Risk Manager | glm-5.3 | Security reasoning |
| AG-003 Security Risk Assessor | glm-5.3 | Security assessment |
| AG-004 Business Analyst | qwen3.8-flash | Requirements (economy) |
| AG-005 Software Architect | kimi-k2.7-code | Architecture (premium) |
| AG-006 UX/UI Designer | qwen3.8-flash | UX (economy) |
| AG-007 Database Architect | deepseek-v4.1-flash | DB design (standard) |
| AG-008 Backend Developer | kimi-k2.7-code | Code (premium) |
| AG-009 Frontend Developer | kimi-k2.7-code | Code (premium) |
| AG-010 Database Developer | deepseek-v4.1-flash | Code (standard) |
| AG-011 Integration Engineer | deepseek-v4.1-flash | Code (standard) |
| AG-012 QA Automation | qwen3.8-flash | Testing (economy) |
| AG-013 Code Reviewer | glm-5.3-flash | Review (standard) |
| AG-014 Performance Engineer | deepseek-v4.1-flash | Analysis (standard) |
| AG-015 Security Auditor | glm-5.3 | Security (premium) |
| AG-016 DevOps Engineer | qwen3.8-flash | DevOps (economy) |
| AG-017 Deployment Manager | beam-free | Deployment coordination (free) |
| AG-018 Documentation Engineer | qwen3.8-flash | Documentation (economy) |

### Automatic model switching
- On quota exhaustion: switch to next available model in the same tier or lower.
- On rate limit: respect Retry-After, wait, then retry same model.
- On transient error: retry with backoff, then switch if persistent.
- On auth error: no automatic switch (requires intervention).
- On incompatible model: switch to compatible alternative.
- On all paid models limited: fall back to beam-free (free reserve).

### Consumption control
- Monthly budget: $40 (shared across all models).
- Alert thresholds: 50% (warning), 70% (reduce aux), 85% (prioritize essentials), 95% (stop non-critical).
- Budget reserve: 10% for integration/QA/final commit.
- Daily targets: 15% (week 1), 40% (week 2), 65% (week 3), 90% (week 4), 100% (preserve 10%).
- Concurrency: progressive (not all 19 agents in parallel).

### Privacy
- Prefer models with zero data retention for code/sensitive tasks.
- Document exceptions.

## 4. Implementation plan (incremental)

### Phase 1: Policy and hierarchy (low risk)
- Update `model_hierarchies.py` to support MODEL_ROUTING_V2 with multiple authorized models and tier-based routing.
- Add `APF_MODEL_POLICY` env var (default: `BEAM_FREE_ONLY` for backward compat; set to `MODEL_ROUTING_V2` to enable).
- Keep BEAM_FREE_ONLY as rollback.

### Phase 2: Agent definitions (medium risk)
- Update `.opencode/agents/*.md` `model:` field per assignment matrix.
- Update normative `agents/` definitions.

### Phase 3: Runtime enforcement (medium risk)
- Update `model_fallback.py` to use routing policy.
- Update `opencode_adapter.py` to allow authorized models from routing policy.
- Update `runtime.py` to track consumption.

### Phase 4: Consumption tracking (blocked on LIVE data)
- Implement consumption tracker (rolling/weekly/monthly).
- Mark as BLOCKED until Go API key available.

### Phase 5: Tests (medium risk)
- Update unit/integration tests for multi-model routing.
- Add routing policy tests.
- Add consumption tracking tests (mocked).

### Phase 6: Documentation (low risk)
- Update ADR-007 or create ADR-009.
- Update design/implementation/validation docs.
- Update agent assignment matrix.

### Phase 7: Validation (requires live data)
- LIVE verification of consumption (BLOCKED).
- Comparative model tests (laboratory tasks).
- Independent QA (AG-002).

## 5. Current blockers

| Blocker | Status | Mitigation |
|---|---|---|
| Go Plus API key / org ID | BLOCKED | User must provide or run endpoint manually |
| Model pricing/limits | BLOCKED | Consult official docs |
| Consumption measurement | BLOCKED | Conservative limits until LIVE data available |

## 6. Next steps

1. **User action required:** Obtain Go API key from https://opencode.ai/settings and run:
   ```bash
   export OPENCODE_GO_API_KEY="<key>"
   curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" https://opencode.ai/inference/go/v1/usage
   curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" https://opencode.ai/inference/go/v1/models
   ```
2. **Implementation:** Begin Phase 1 (policy + hierarchy) with BEAM_FREE_ONLY as default and MODEL_ROUTING_V2 as opt-in.
3. **Tests:** Update tests incrementally.
4. **Validation:** Run full battery after each phase.

No implementation performed yet. Backup created. Awaiting user to provide API key or run endpoints.
## 6. Implementation status (updated 2026-11-24)

### Phase 1: Policy and hierarchy — IMPLEMENTED
- `orchestration/runtime/model_routing.py` created: routing policy, 30 authorized models, agent assignment, fallback hierarchies.
- `model_hierarchies.py` updated: dual policy (BEAM_FREE_ONLY default + MODEL_ROUTING_V2 opt-in via `APF_MODEL_POLICY`).
- `model_fallback.py` updated: `get_primary`, `get_hierarchy`, `is_authorized` use routing when V2.
- `opencode_adapter.py` updated: uses `_rt_authorized_models()` for authorization.
- `runtime.py` updated: uses `authorized_models()` for model rejection.
- Rollback: set `APF_MODEL_POLICY=BEAM_FREE_ONLY` (default).

### Phase 2: Agent definitions — DEFERRED
- Agent files (`.opencode/agents/*.md`) retain `model: opencode-go/beam-free` as baseline (rollback).
- Routing overrides model at runtime when V2 is active. No file changes to agents.

### Phase 3: Runtime enforcement — IMPLEMENTED
- Adapter and runtime use routing policy for authorization.
- BEAM_FREE_ONLY enforcement preserved as fallback.

### Phase 4: Consumption tracking — BLOCKED
- No Go API key available in environment.
- Safe local procedure documented in `041_GO_PLUS_MONTHLY_USAGE_POLICY.md`.
- Conservative limits used in design.

### Phase 5: Tests — PARTIAL
- Existing tests pass in BEAM_FREE_ONLY mode.
- V2-specific tests not yet added.

### Phase 6: Documentation — IMPLEMENTED
- `040_AGENT_MODEL_ASSIGNMENT_MATRIX.md` created.
- `041_GO_PLUS_MONTHLY_USAGE_POLICY.md` created.
- `042_MODEL_ROUTING_QA_REPORT.md` created.
- ADR-009 pending (not yet created).

### Phase 7: Validation — BLOCKED
- LIVE verification of consumption: BLOCKED (no Go API key).
- Comparative model tests: NOT_TESTED.
- Independent QA: pending.

## 7. Agent count reconciliation

- Normative agents: 18 (AG-001..AG-018).
- Executable agents: 19 (AG-003 has 2 documented specializations: security-risk-manager + security-risk-assessor).
- The matrix in `040_AGENT_MODEL_ASSIGNMENT_MATRIX.md` lists 19 entries (including both AG-003 specializations).
- AG-001 assignment corrected to `glm-5.3-flash` (was beam-free).
- AG-002 assignment corrected to `deepseek-v4.1-flash` (was beam-free).

## 8. Rollback

Set `APF_MODEL_POLICY=BEAM_FREE_ONLY` (or unset) to restore single-model behavior. All code changes are backward compatible. No agent files modified.
