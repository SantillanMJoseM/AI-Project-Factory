# Model Routing Live Audit (Stage 041)

Date: 2026-11-25
Coordinator: AG-001

## 1. Current policy

- Default: BEAM_FREE_ONLY (all 19 agents use opencode-go/beam-free).
- V2: opt-in via APF_MODEL_POLICY=MODEL_ROUTING_V2 (requires approval gate, removed in remediation; now env-var only).
- Rollback: unset env var or set BEAM_FREE_ONLY.

## 2. V2 implementation status

- model_routing.py: 33 authorized models, agent assignment, fallback hierarchies, pricing.
- model_hierarchies.py: dual policy (dynamic import).
- model_fallback.py: get_primary, get_hierarchy, is_authorized use routing.
- opencode_adapter.py: uses _rt_authorized_models() for authorization.
- runtime.py: uses authorized_models() for model rejection.
- Agent files: unchanged (model: beam-free baseline; routing overrides at runtime).

## 3. V2 live verification

- V2 mode tested: AG-001 → glm-5.3-flash, AG-002 → deepseek-v4.1-flash, AG-005 → kimi-k2.7-code.
- V2 tests: 19/19 PASS.
- V2 routing in real delegation: NOT_TESTED (default policy BEAM_FREE_ONLY).
- Consumption tracking: BLOCKED (no Go API key in env; go_usage.py works in mocked mode).

## 4. Findings

- V2 is implemented but not exercised in live delegation (default policy).
- Consumption measurement blocked (no API key).
- Budget enforcement not wired (go_usage.check_budget not called by adapter).
- Dead code: MODEL_SWITCHED, on_fallback, recover_primary_model inert under V2.
- verify_effective_model fixed to use _authorized_models().

## 5. Recommendation

V2 is IMPLEMENTED and UNIT_TESTED. LIVE_VERIFIED requires real delegation with V2 active. Consumption tracking requires Go API key. Budget enforcement requires wiring go_usage.check_budget into adapter.