# Stage 2D — Security Report

**Date:** 2026-11-20

## Scope
Independent review of Stage 2A/2B/2C integration: snapshot integrity, ledger tampering, delegation boundaries, context recovery, model fallback.

## Findings
- Snapshot hashes use SHA-256 with self-hash exclusion; verified by tests.
- Ledger is append-only JSONL with chain hashes.
- Resume engine fail-closed.
- No permission escalation: agents retain their own permissions.
- No external network access in components.
- Model fallback preserves task state via snapshots.
- Task tool not available in `opencode run` CLI; delegation via CLI only.

## Verdict
PASS_WITH_OBSERVATIONS (offline review; live AG-015 session did not produce full report due to quota/session limits).