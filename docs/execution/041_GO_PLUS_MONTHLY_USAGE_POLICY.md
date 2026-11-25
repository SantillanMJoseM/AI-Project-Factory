# Go Plus Monthly Usage Policy

Date: 2026-11-24
Status: BLOCKED on live consumption measurement (no Go API key available in environment).

## 1. Subscription

- Plan: OpenCode Go Plus, USD 40/month.
- All paid models share a single usage allocation.
- Changing models does NOT create a new allocation or reset consumption.
- Monthly limits are reference capacity, not independent credit pools.

## 2. Consumption endpoints (not yet accessible)

- Models: `GET https://opencode.ai/inference/go/v1/models`
- Usage: `GET https://opencode.ai/inference/go/v1/usage` (requires Go API key as Bearer token)
- Auth: `Authorization: Bearer <go-api-key>`

### Blocker
The Go API key / org ID is not available in the local environment:
- `~/.config/opencode/service.json` contains only the OpenCode account password.
- `opencode debug config` redacts the org ID.
- No `OPENCODE_GO_API_KEY` env var is set.

### Safe local procedure for user
```bash
# 1. Get your Go API key from https://opencode.ai/settings (API Keys section)
# 2. Export it (do not commit or share):
export OPENCODE_GO_API_KEY="<your-key>"
# 3. Query usage:
curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  https://opencode.ai/inference/go/v1/usage | python3 -m json.tool
# 4. Query models:
curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  https://opencode.ai/inference/go/v1/models | python3 -m json.tool
```

## 3. Usage indicators

From the usage endpoint (when available):
- `rolling`: 5-hour rolling usage (percent, status, resetsAt)
- `weekly`: weekly usage (percent, status, resetsAt)
- `monthly`: monthly usage (percent, status, resetsAt)
- `opencode.allowance`: per-response allowance info

## 4. Internal consumption targets (on shared monthly allocation)

| Period | Cumulative target | Action |
|---|---|---|
| Days 1-7 | 15% | Normal operation |
| Days 8-14 | 40% | Monitor |
| Days 15-21 | 65% | Reduce aux tasks |
| Days 22-28 | 90% | Prioritize essentials |
| Days 29-30 | Preserve 10% | Integration, QA, final commit |

## 5. Alert thresholds

| Usage | Action |
|---|---|
| 50% | Warning: review consumption |
| 70% | Reduce auxiliary/costly tasks |
| 85% | Prioritize essential tasks only |
| 95% | Stop non-critical tasks |
| 100% / rate-limit | Use free models (beam-free) or WAITING |

## 6. Concurrency control

- Do NOT start all 19 agents in parallel.
- Progressive concurrency: 2-3 agents initially, scale based on consumption.
- Reduce concurrency when consumption accelerates.
- Reserve 10% budget for integration, QA, audit, final commit.

## 7. Privacy

- Prefer models with zero data retention for code/sensitive tasks.
- Document exceptions.

## 8. Classification

- Consumption measurement: **BLOCKED** (no Go API key available).
- Policy design: **IMPLEMENTED** (conservative limits).
- LIVE verification: **NOT_TESTED**.