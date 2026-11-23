# Stage 2P — Permissions Audit

Date: 2026-11-23
Branch: feature/model-fallback-manager

## 1. Matriz

- File: docs/execution/PERMISSIONS_MATRIX_2H.md.
- V2 ordered permissions array. Minimum privilege. external_directory deny. execute deny. AG-001 subagent allow ag-* only.

## 2. Reconciliación

- Normative agents/ (markdown docs) have no executable permissions.
- Executable .opencode/agents/ hold V2 perms.
- Drift documented (reconciliation pending user authorization).
- No permission changes made without authorization.