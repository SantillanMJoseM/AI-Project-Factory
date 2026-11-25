# Model Routing QA Report

Date: 2026-11-24
Auditor: AG-001 (self-assessment; independent AG-002 audit pending authorization).

## 1. Implementation status

| Component | Status | Evidence |
|---|---|---|
| model_routing.py (routing policy) | IMPLEMENTED | 30 authorized models, agent assignment, fallback hierarchies |
| model_hierarchies.py (dual policy) | IMPLEMENTED | BEAM_FREE_ONLY default + MODEL_ROUTING_V2 opt-in via env var |
| model_fallback.py (routing-aware) | IMPLEMENTED | get_primary/get_hierarchy/is_authorized use routing when V2 |
| opencode_adapter.py (policy enforcement) | IMPLEMENTED | Rejects non-authorized models; uses _rt_authorized_models() |
| runtime.py (model rejection) | IMPLEMENTED | authorized_models() from routing |
| Agent definitions (.opencode/agents/) | UNCHANGED (rollback baseline) | model: beam-free retained |
| Consumption tracking | BLOCKED | No Go API key available |
| Tests | IMPLEMENTED (BEAM_FREE_ONLY) | V2 tests not yet added |

## 2. Test results (BEAM_FREE_ONLY mode, default)

| Suite | Result | Exit |
|---|---|---|
| tests/run_all.py (38 suites) | ALL TESTS PASSED | 0 |
| test_structure.py | 8/8 PASS | 0 |
| test_model_fallback.py | 23/23 PASS | 0 |
| test_model_fallback_integration.py | 8/8 PASS | 0 |
| install/scripts/verify.sh | ALL CHECKS PASSED | 0 |
| Quality Gate Runtime | PASS_WITH_OBSERVATIONS | 0 |

## 3. V2 mode verification (env var)

```
APF_MODEL_POLICY=MODEL_ROUTING_V2 python3 -c "..."
```
- V2 active: True
- AG-005 primary: opencode-go/kimi-k2.7-code
- AG-005 hierarchy: [kimi-k2.7-code, glm-5.3, beam-free]
- AG-001 primary: opencode-go/beam-free
- authorized count: 30

## 4. Risks

1. **Consumption measurement BLOCKED** — no Go API key available.
2. **No V2-specific tests** — tests still validate BEAM_FREE_ONLY behavior.
3. **Agent definitions unchanged** — model field still beam-free (routing overrides at runtime).
4. **No live verification** of model switching or consumption.
5. **Rollback available** — set `APF_MODEL_POLICY=BEAM_FREE_ONLY` (default).

## 5. Recommendation

- Obtain Go API key to enable consumption measurement.
- Add V2-specific tests (routing, fallback, budget).
- Run comparative model tests (laboratory tasks).
- Independent QA (AG-002) audit after V2 tests pass.

## 6. Classification

| Capability | Classification |
|---|---|
| Routing policy (V2) | IMPLEMENTED |
| Model assignment matrix | IMPLEMENTED |
| Fallback hierarchies (V2) | IMPLEMENTED |
| Runtime enforcement (V2) | IMPLEMENTED |
| Consumption tracking | BLOCKED (no API key) |
| V2 unit tests | NOT_TESTED |
| V2 integration tests | NOT_TESTED |
| V2 live verification | NOT_TESTED |
| Rollback (BEAM_FREE_ONLY) | IMPLEMENTED + TESTED |