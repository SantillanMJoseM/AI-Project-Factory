# ADR-R5.2A — Source of Truth Reconciliation

## Status

Proposed (requires human approval before implementation)

## Date

2026-11-04

## Context

ADR-001 states: "Repository files are the source of truth." `state-management.md` states: "No hidden runtime state may become authoritative."

The current implementation uses SQLite (`orchestration/runtime/runtime.db`, gitignored) as the sole authoritative record for task, execution, approval, audit and event state. Repository files contain normative definitions, contracts, schemas, and evidence, but not operational state.

This creates a contradiction: the normative decision says files are authoritative, but the implementation makes a hidden database authoritative.

## Decision

### 1. Authoritative source by information type

| Information type | Authoritative source | Rationale |
|---|---|---|
| Normative definitions (agents, contracts, schemas, policies, workflows) | Repository files (`agents/`, `contracts/`, `schemas/`, `orchestration/`) | Version-controlled, auditable, portable |
| Operational state (tasks, executions, approvals, audits, events) | SQLite database (`runtime.db`) | Transactional, concurrent-safe, queryable |
| Evidence (test results, quality reports, security findings) | Repository files (`projects/<id>/evidence/`) + database reference | Version-controlled, hashable, auditable |
| Quality Gate results | Database (`quality_gate_results` table) + evidence files | Linked to certificate and commit |
| Release manifests | Repository files (`projects/<id>/deployment/`) | Version-controlled, hashable |
| Agent definitions (normative) | Repository files (`agents/`) | Single source of truth |
| Agent definitions (executable) | Repository files (`.opencode/agents/`) | Generated from normative; verified by hash |
| Configuration | Repository files (`opencode.json`, `orchestration/policies/`) | Version-controlled |
| Secrets | Environment variables / secret store | Never in repository |

### 2. Reconciliation mechanism

The SQLite database is the operational store while work is in progress. At each stage closure, the controller exports a canonical JSON snapshot:

```
projects/<PROJECT_ID>/evidence/<STAGE>/state_snapshot.json
```

The snapshot contains:
- All tasks (with status, agent, dependencies, acceptance criteria, quality gates)
- All executions (with status, inputs, outputs, tools, errors, commit)
- All quality gate results (with verdict, rules violated, certificate hash)
- All approvals (with status, binding, approver, consumption)
- All audits (with verdict, findings, evidence, content hash)
- All events (with type, actor, timestamp, state transition)
- Chain head hash (prev_hash of last event/audit)

The snapshot is:
1. Hashed (SHA-256 of canonical JSON).
2. Recorded in the stage record (database).
3. Committed by the human operator or by a controller command under change control.

### 3. Divergence detection

At stage closure, the controller compares the database state with the last committed snapshot. If they differ:
- The difference is reported (which entities changed, how).
- The operator must resolve the divergence before proceeding.
- The database is the operational truth; the snapshot is the auditable record.

### 4. Recovery from divergence

If the database is lost or corrupted:
1. Restore from the last committed snapshot (import JSON into SQLite).
2. Verify chain hash matches.
3. Re-run any in-progress work.

If the snapshot is lost:
1. Export current database state as a new snapshot.
2. Record the divergence in a decision record.
3. Re-verify all state against evidence files.

### 5. Hash chain integrity

Every event and audit records:
- `prev_hash`: SHA-256 of the previous event/audit row (in insertion order).
- `row_hash`: SHA-256 of the current row's content (excluding prev_hash and row_hash).

Chain verification:
1. Order events/audits by insertion order (timestamp + rowid).
2. For each row, verify `row_hash` matches computed hash.
3. Verify `prev_hash` matches the previous row's `row_hash`.
4. Report any mismatch.

### 6. Authoritative source decision

**For operational state:** SQLite database is authoritative while work is in progress. The repository snapshot is authoritative after stage closure and commit.

**For normative definitions:** Repository files are always authoritative. The database stores references (agent_id, contract version) but not definitions.

**For evidence:** Repository files are authoritative. The database stores references (file paths, hashes) but not content.

**For identity:** The approver roster file is authoritative. The database stores approval records but not the roster.

### 7. Consequences

- A new ADR (ADR-007) must be created documenting this reconciliation.
- ADR-001 is not modified (it remains valid for normative definitions).
- `state-management.md` must be updated to reflect the dual-source model.
- The export command must be implemented before stage closure is possible.
- The hash chain must be implemented before audit integrity is verifiable.

### 8. Related decisions

- ADR-001: Repository files are source of truth (preserved for normative definitions).
- ADR-002: Supervised autonomy (preserved).
- ADR-004: Independent audit (preserved; hash chain strengthens it).
- ADR-005: SQLite for PROJECT-001 (preserved; extended to factory runtime).

## Status

Proposed. Requires human approval. If approved, creates ADR-007.