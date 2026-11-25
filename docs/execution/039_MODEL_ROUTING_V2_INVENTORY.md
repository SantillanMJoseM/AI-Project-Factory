# Stage 039 — Model Routing V2: Inventory and Model Discovery

Date: 2026-11-24
Coordinator: AG-001 Project Coordinator
Mode: Phase A + B (inventory + model discovery). No implementation yet.

## 1. Environment

| Field | Value |
|---|---|
| User | developer02 |
| Repository | /home/developer02/projects/AI-Project-Factory |
| OpenCode | v2.4.1 |
| Branch | main |
| HEAD | 5f63b74ca0f54596ff83b1cdd5df02480b7a34da |
| Provider | opencode-go (OpenCode Go) |
| Auth | OpenCode account stored (auth list: "OpenCode OpenCode stored") |

## 2. Go Plus subscription status

- `opencode models` returns 32 models under `opencode-go` provider.
- Auth is configured (OpenCode account stored).
- Go Plus subscription status cannot be verified programmatically from CLI (no `opencode go status` command). User confirms Go Plus USD 40/month is active.
- No `allowance` or usage endpoint discovered via `opencode api` (would require server running with known OpenAPI spec).

## 3. Discovered models (opencode-go provider)

| # | Model ID | Category (inferred) |
|---|---|---|
| 1 | opencode-go/beam-free | Free (baseline) |
| 2 | opencode-go/claude-haiku-5-5 | Premium (Anthropic) |
| 3 | opencode-go/deepseek-v4-pro | Premium (DeepSeek) |
| 4 | opencode-go/deepseek-v4.1-flash | Flash (DeepSeek) |
| 5 | opencode-go/gemini-4-argon | Premium (Google) |
| 6 | opencode-go/glm-5.3 | Premium (Zhipu) |
| 7 | opencode-go/glm-5.3-flash | Flash (Zhipu) |
| 8 | opencode-go/gpt-5.6-luna | Premium (OpenAI) |
| 9 | opencode-go/gpt-6-luna | Premium (OpenAI) |
| 10 | opencode-go/grok-4.7 | Premium (xAI) |
| 11 | opencode-go/hungerg-free | Free |
| 12 | opencode-go/hy3 | Standard |
| 13 | opencode-go/hy4 | Standard |
| 14 | opencode-go/hy4-flash-free | Free |
| 15 | opencode-go/hy4-preview | Preview |
| 16 | opencode-go/iceman-contributor-free | Free (contributor) |
| 17 | opencode-go/kimi-k2.7-code | Premium (Moonshot) |
| 18 | opencode-go/kimi-k3 | Premium (Moonshot) |
| 19 | opencode-go/kimi-k3.1-pro | Premium (Moonshot) |
| 20 | opencode-go/longcat-2.5 | Standard |
| 21 | opencode-go/mimo-v2.5 | Standard (Xiaomi) |
| 22 | opencode-go/mimo-v2.5-pro | Premium (Xiaomi) |
| 23 | opencode-go/mimo-v2.6-flash | Flash (Xiaomi) |
| 24 | opencode-go/mimo-v2.6-pro | Premium (Xiaomi) |
| 25 | opencode-go/minimax-m3 | Standard (MiniMax) |
| 26 | opencode-go/minimax-m3.1-flash | Flash (MiniMax) |
| 27 | opencode-go/muse-spark-1.2-contributor | Free (contributor) |
| 28 | opencode-go/muse-spark-1.3-contributor | Free (contributor) |
| 29 | opencode-go/qwen3.7-plus | Standard (Alibaba) |
| 30 | opencode-go/qwen3.8-flash | Flash (Alibaba) |
| 31 | opencode-go/qwen3.8-max | Premium (Alibaba) |
| 32 | opencode-go/qwen4-max | Premium (Alibaba) |
| 33 | opencode-go/step-5-preview | Preview |

Note: The user's candidate list (Kimi K2.7 Code, GLM-5.3, GLM-5.3-Flash, DeepSeek V4.1 Flash, DeepSeek V4 Pro, Qwen3.8 Flash, Qwen3.8 Max, MiMo-V2.6-Flash, MiMo-V2.6-Pro, MiniMax M3.1 Flash, Claude Haiku 5.5, Gemini 4 Argon) — all present except GLM-5.2 (not in catalog). Qwen4-max and kimi-k3/kimi-k3.1-pro are additional premium options.

## 4. Current policy (BEAM_FREE_ONLY)

- `AUTHORIZED_MODEL = "opencode-go/beam-free"` (model_hierarchies.py:9)
- `AUTHORIZED_MODELS = {AUTHORIZED_MODEL}` (model_hierarchies.py:10)
- `FALLBACK_ALTERNATIVES = {}` (model_hierarchies.py:14)
- ADR-007 records this policy.
- All 19 executable agents use `model: opencode-go/beam-free`.
- Runtime enforces: adapter rejects non-authorized, run_task rejects non-authorized.

## 5. Current architecture (relevant modules)

| Module | Role |
|---|---|
| `orchestration/runtime/model_hierarchies.py` | Authorized model set + fallback alternatives |
| `orchestration/runtime/model_fallback.py` | ModelFallbackManager: selection, error classification, wait/recovery |
| `orchestration/runtime/opencode_adapter.py` | Adapter: invokes OpenCode, enforces BEAM_FREE_ONLY |
| `orchestration/runtime/runtime.py` | Runtime: run_task, resume, persistence, SQLite |
| `orchestration/task_orchestration/model_fallback_integration.py` | Task-orchestration binding, coordination probe |
| `contracts/model-fallback-contract.md` | Normative contract (stale: multi-model) |
| `docs/architecture/MODEL_FALLBACK_DESIGN.md` | Design doc (updated for BEAM_FREE_ONLY) |

## 6. Current test state

- `tests/run_all.py`: 38 suites, ALL TESTS PASSED.
- Legacy fallback tests: updated to BEAM_FREE_ONLY (23 + 8 tests pass).
- Quality Gate Runtime: PASS_WITH_OBSERVATIONS (1 open LOW defect CR-P001-R4-002).

## 7. Backup

- `/tmp/opencode/backups/etapa039-pre-migration.tar.gz` (SHA256 `5efd422459596ffeec32a105602fb5082888eb04180a53f6950462f70e4db462`, 791 files, 0 mismatches).

## 8. Open questions (require user authorization)

1. **Go Plus verification:** Cannot verify subscription status programmatically. User confirms active. Recommend checking `opencode.ai/settings` or billing page.
2. **Consumption measurement:** No `allowance` endpoint discovered. The `opencode stats` command shows session/token counts but not per-model quota. Need to determine how to measure actual consumption.
3. **Model pricing:** No pricing data available from CLI. Need to consult https://opencode.ai/docs/console/go/ for per-model pricing and limits.
4. **Migration scope:** Changing from BEAM_FREE_ONLY to MODEL_ROUTING_V2 affects ADR-007, all agent definitions, runtime enforcement, tests, and documentation. This is a significant architectural change.
5. **Rollback:** BEAM_FREE_ONLY must remain available as a rollback option (currently implemented and tested).

## 9. Recommendation

Before implementing MODEL_ROUTING_V2, the following must be resolved:

1. **Verify Go Plus subscription** (user action: check billing/subscription page).
2. **Obtain model pricing and limits** from official docs (https://opencode.ai/docs/console/go/).
3. **Design the routing policy** (which model for which agent/task, fallback order, budget allocation).
4. **Authorize the migration** (this changes ADR-007 and affects all 19 agents, runtime, tests).
5. **Implement incrementally** with rollback capability.

This is a major architectural migration, not a remediation. It should not be started without explicit authorization and a clear model evaluation plan.

## 10. Next steps (pending authorization)

- [ ] User verifies Go Plus subscription status.
- [ ] Obtain per-model pricing and monthly limits from official docs.
- [ ] Design MODEL_ROUTING_V2 policy (routing matrix, budget allocation).
- [ ] Authorize migration (update ADR-007 or create ADR-009).
- [ ] Implement routing layer incrementally.
- [ ] Update agent definitions (model field).
- [ ] Update runtime enforcement.
- [ ] Update tests.
- [ ] Run full validation.
- [ ] Update documentation.

No implementation performed in this phase. Backup created and verified.