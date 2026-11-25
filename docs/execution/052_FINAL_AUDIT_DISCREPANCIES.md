# Stage 2Q Final Audit — Discrepancies

Date: 2026-11-23
Branch: feature/model-fallback-manager

## 1. Discrepancias identificadas

### D1: TASK-0014 FAILED (no recovery)
- TASK-0014: status FAILED.
- EXEC-0014: INTERRUPTED (simulated). EXEC-0015: FAILED (resume attempt with empty context — bug fixed later).
- No successful recovery for TASK-0014. Legitimate failure, documented.
- Severity: MEDIUM.

### D2: 51 Skills NOT_TESTED
- Only 5/54 LIVE_VERIFIED. 49 ASSIGNED/NOT_TESTED.
- Reason: quota protection.
- Severity: LOW (by design).

### D3: Normative vs executable permission drift
- agents/ (markdown docs) have no executable permissions.
- .opencode/agents/ hold V2 perms.
- Reconciliation pending user authorization.
- Severity: LOW.

### D4: AG-003 identity conflict
- Two files under AG-003 (risk manager + assessor).
- No deletion/rename performed. Proposal documented.
- Severity: MEDIUM (requires user authorization).

### D5: LXC install not executed
- No second LXC available.
- Procedure documented. BLOCKED.
- Severity: LOW.

### D6: 2 INTERRUPTED executions (EXEC-0014, EXEC-0016)
- EXEC-0016 recovered via EXEC-0017. EXEC-0014 not recovered (failed resume).
- Severity: MEDIUM (EXEC-0014 remains FAILED).

## 2. Sin discrepancias críticas

- No data loss.
- No security vulnerabilities detected.
- No unauthorized model usage.
- No unauthorized commits/pushes beyond authorized.