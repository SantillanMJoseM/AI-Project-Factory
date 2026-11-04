# Data Dictionary — PROJECT-001

| Field | Value |
|---|---|
| Project | PROJECT-001 |
| Document | DATA_DICTIONARY.md |
| Version | 1.0.0 (Draft for F2 review) |
| Author | AG-007 Database Architect |
| Date | 2026-11-04 |
| Reference engine | PostgreSQL 15+ (portability notes per entity) |
| Status | Design only — no migrations executed |

## 1. Purpose and Scope

This dictionary defines the canonical data model for the two core entities of
PROJECT-001: `User` and `Task`. It is the source of truth for attribute
naming, key roles, relationships, integrity constraints, indexing, and the
requirements each entity traces to. No other project files were consulted in
this revision; content is self-contained.

### 1.1 Notation

- **Key column**: `PK` primary key · `FK(n)` foreign key to entity `n` · `UK` unique/alternate key · `—` non-key attribute.
- **Null?**: `N` = NOT NULL, `Y` = nullable.
- All timestamps are stored in UTC (`timestamptz`); application layer handles display timezone.
- Identifiers for traceability: entities `ENT-*`, constraints `C-<ENT>-*`, indexes `I-<ENT>-*`, relationships `REL-*`, requirements `REQ-<ENT>-*`.

---

## 2. Entity: User

| Field | Value |
|---|---|
| Entity ID | ENT-001 |
| Table name | `users` |
| Description | Registered account of a person operating the system. Holds identity, credentials (hash only), profile, and account lifecycle state. A User owns and is assigned Tasks. |
| Cardinality expectations | Expected initial volume: ≤ 10⁴ rows; growth ≤ 10³/year (low, read-heavy). |

### 2.1 Attributes

| # | Name | Type | Key | Null? | Default | Description |
|---|---|---|---|---|---|---|
| 1 | `id` | `uuid` | PK | N | `gen_random_uuid()` | Surrogate primary key. Immutable; never reused. |
| 2 | `email` | `varchar(254)` | UK | N | — | Login identifier. RFC 5321 max length; stored lowercased. |
| 3 | `username` | `varchar(32)` | UK | N | — | Public handle. Pattern: `^[a-z0-9_]{3,32}$`. |
| 4 | `password_hash` | `varchar(255)` | — | N | — | Argon2id/BCrypt hash. Never plaintext; excluded from all API projections by default. |
| 5 | `display_name` | `varchar(100)` | — | N | `username` | Name shown in UI. |
| 6 | `role` | `varchar(16)` | — | N | `'member'` | Authorization role. Domain: `admin`, `member`, `viewer`. |
| 7 | `status` | `varchar(16)` | — | N | `'active'` | Lifecycle: `active`, `suspended`, `deactivated`. |
| 8 | `last_login_at` | `timestamptz` | — | Y | `NULL` | Last successful authentication; audit aid. |
| 9 | `created_at` | `timestamptz` | — | N | `now()` | Row creation time (UTC). |
| 10 | `updated_at` | `timestamptz` | — | N | `now()` | Last row modification; maintained by trigger at write time. |

### 2.2 Relationships

| ID | Relationship | Type | Foreign keys / actions | Notes |
|---|---|---|---|---|
| REL-001 | User 1 → N Task (assignee) | One-to-many | Referenced by `tasks.assignee_id` → `users.id`; `ON DELETE RESTRICT` | A user cannot be hard-deleted while assigned tasks exist; deactivation is the supported path. |
| REL-002 | User 1 → N Task (creator) | One-to-many | Referenced by `tasks.created_by` → `users.id`; `ON DELETE RESTRICT` | Provenance of task creation. |
| — | User ↔ Task (self, optional) | None | — | No user-to-user relations modeled in this revision. |

### 2.3 Constraints

| ID | Constraint | Definition | Purpose |
|---|---|---|---|
| C-USR-001 | `pk_users` | `PRIMARY KEY (id)` | Row identity. |
| C-USR-002 | `uq_users_email` | `UNIQUE (email)` | One account per email address. |
| C-USR-003 | `uq_users_username` | `UNIQUE (username)` | Handles are globally unique. |
| C-USR-004 | `chk_users_email_format` | `email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'` | Rejects malformed emails at the storage layer. |
| C-USR-005 | `chk_users_username_format` | `username ~ '^[a-z0-9_]{3,32}$'` | Normalizes handle format. |
| C-USR-006 | `chk_users_role` | `role IN ('admin','member','viewer')` | Closed role domain. |
| C-USR-007 | `chk_users_status` | `status IN ('active','suspended','deactivated')` | Closed lifecycle domain. |
| C-USR-008 | `chk_users_timestamps` | `updated_at >= created_at` | Prevents clock-inconsistent writes. |

### 2.4 Indexes

| ID | Index | Definition | Rationale |
|---|---|---|---|
| I-USR-001 | `pk_users` (clustered B-tree) | `id` | PK access path (implicit via C-USR-001). |
| I-USR-002 | `uq_users_email` (B-tree, unique) | `email` | Login lookup by email (implicit via C-USR-002). |
| I-USR-003 | `uq_users_username` (B-tree, unique) | `username` | Handle lookup/resolution (implicit via C-USR-003). |
| I-USR-004 | `ix_users_status_role` | `CREATE INDEX ix_users_status_role ON users (status, role)` | Admin listings of active accounts per role. |

### 2.5 Requirements

| ID | Requirement | Traces to |
|---|---|---|
| REQ-USR-001 | Each user must have a unique email and username usable for identification. | Attrs 2–3; C-USR-002/003/004/005; I-USR-002/003 |
| REQ-USR-002 | Credentials must be stored only as a salted hash; never exposed by default. | Attr 4 |
| REQ-USR-003 | The system must support three authorization roles. | Attr 6; C-USR-006 |
| REQ-USR-004 | Accounts must support deactivation/suspension without losing historical task ownership. | Attr 7; C-USR-007; REL-001/002 (`RESTRICT`) |
| REQ-USR-005 | Account creation and modification times must be auditable. | Attrs 9–10; C-USR-008 |

---

## 3. Entity: Task

| Field | Value |
|---|---|
| Entity ID | ENT-002 |
| Table name | `tasks` |
| Description | A unit of work tracked in the system, assigned to a User, with a lifecycle status and priority. Soft-deleted rows are retained for audit. |
| Cardinality expectations | Expected initial volume: ≤ 10⁶ rows; growth ≤ 5×10⁵/year (moderate, mixed read/write). |

### 3.1 Attributes

| # | Name | Type | Key | Null? | Default | Description |
|---|---|---|---|---|---|---|
| 1 | `id` | `uuid` | PK | N | `gen_random_uuid()` | Surrogate primary key. Immutable. |
| 2 | `task_key` | `varchar(16)` | UK | N | — | Human-readable key (e.g., `P1-1024`). Pattern: `^[A-Z]{1,8}-[0-9]{1,9}$`. |
| 3 | `title` | `varchar(200)` | — | N | — | Short imperative summary. Trimmed, non-blank. |
| 4 | `description` | `text` | — | Y | `NULL` | Free-form detail (Markdown). |
| 5 | `status` | `varchar(16)` | — | N | `'todo'` | Lifecycle: `todo`, `in_progress`, `done`, `archived`. |
| 6 | `priority` | `varchar(8)` | — | N | `'medium'` | Domain: `low`, `medium`, `high`, `critical`. |
| 7 | `assignee_id` | `uuid` | FK(users.id) | Y | `NULL` | User responsible; `NULL` = unassigned backlog. |
| 8 | `created_by` | `uuid` | FK(users.id) | N | — | User who created the task; immutable after insert. |
| 9 | `due_at` | `timestamptz` | — | Y | `NULL` | Deadline; overdue = `due_at < now() AND status NOT IN ('done','archived')`. |
| 10 | `completed_at` | `timestamptz` | — | Y | `NULL` | Set exactly when status first enters `done`. |
| 11 | `revision` | `integer` | — | N | `0` | Optimistic-locking counter; incremented on each update. |
| 12 | `deleted_at` | `timestamptz` | — | Y | `NULL` | Soft-delete marker; `NULL` = live row. |
| 13 | `created_at` | `timestamptz` | — | N | `now()` | Row creation time (UTC). |
| 14 | `updated_at` | `timestamptz` | — | N | `now()` | Last modification; trigger-maintained. |

### 3.2 Relationships

| ID | Relationship | Type | Foreign keys / actions | Notes |
|---|---|---|---|---|
| REL-001 | Task N → 1 User (assignee) | Many-to-one | `assignee_id → users.id`, `ON DELETE RESTRICT` | Reciprocal of REL-001 (User). Reassignment is an update, not a delete. |
| REL-002 | Task N → 1 User (creator) | Many-to-one | `created_by → users.id`, `ON DELETE RESTRICT` | Provenance; reciprocal of REL-002 (User). |
| — | Task ↔ Task | None | — | No subtask/dependency graph modeled in this revision (candidate for F3). |

### 3.3 Constraints

| ID | Constraint | Definition | Purpose |
|---|---|---|---|
| C-TSK-001 | `pk_tasks` | `PRIMARY KEY (id)` | Row identity. |
| C-TSK-002 | `uq_tasks_key` | `UNIQUE (task_key)` | Stable human-readable references. |
| C-TSK-003 | `chk_tasks_key_format` | `task_key ~ '^[A-Z]{1,8}-[0-9]{1,9}$'` | Key format enforcement. |
| C-TSK-004 | `chk_tasks_title_not_blank` | `btrim(title) <> ''` | Rejects empty titles. |
| C-TSK-005 | `chk_tasks_status` | `status IN ('todo','in_progress','done','archived')` | Closed lifecycle domain. |
| C-TSK-006 | `chk_tasks_priority` | `priority IN ('low','medium','high','critical')` | Closed priority domain. |
| C-TSK-007 | `chk_tasks_completed` | `completed_at IS NULL OR status IN ('done','archived')` | Completion stamp only on terminal-ish states. |
| C-TSK-008 | `chk_tasks_revision` | `revision >= 0` | Guard on optimistic-lock counter. |
| C-TSK-009 | `chk_tasks_timestamps` | `updated_at >= created_at` | Prevents clock-inconsistent writes. |
| C-TSK-010 | `fk_tasks_assignee` | `FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE RESTRICT` | Referential integrity (REL-001). |
| C-TSK-011 | `fk_tasks_creator` | `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT` | Referential integrity (REL-002). |

### 3.4 Indexes

| ID | Index | Definition | Rationale |
|---|---|---|---|
| I-TSK-001 | `pk_tasks` (clustered B-tree) | `id` | PK access path (implicit via C-TSK-001). |
| I-TSK-002 | `uq_tasks_key` (B-tree, unique) | `task_key` | Key-based lookup (implicit via C-TSK-002). |
| I-TSK-003 | `ix_tasks_assignee_status` | `CREATE INDEX ix_tasks_assignee_status ON tasks (assignee_id, status) WHERE deleted_at IS NULL` | Primary query: "my open tasks". Partial to skip soft-deleted rows. |
| I-TSK-004 | `ix_tasks_status_due_at` | `CREATE INDEX ix_tasks_status_due_at ON tasks (status, due_at) WHERE deleted_at IS NULL AND status IN ('todo','in_progress')` | Due/overdue dashboards; small partial index. |
| I-TSK-005 | `ix_tasks_created_by` | `CREATE INDEX ix_tasks_created_by ON tasks (created_by)` | FK support for creator lookups and RESTRICT checks. |
| I-TSK-006 | `ix_tasks_priority_created` | `CREATE INDEX ix_tasks_priority_created ON tasks (priority, created_at DESC) WHERE deleted_at IS NULL` | Prioritized backlog ordering. |

### 3.5 Requirements

| ID | Requirement | Traces to |
|---|---|---|
| REQ-TSK-001 | Tasks must be uniquely addressable by a human-readable key. | Attr 2; C-TSK-002/003; I-TSK-002 |
| REQ-TSK-002 | Every task must follow a closed four-state lifecycle with an auditable completion time. | Attrs 5, 10; C-TSK-005/007 |
| REQ-TSK-003 | Tasks support four priorities and deadline tracking for overdue detection. | Attrs 6, 9; C-TSK-006; I-TSK-004/006 |
| REQ-TSK-004 | A task may be assigned to at most one user and may exist unassigned. | Attr 7; C-TSK-010; REL-001 |
| REQ-TSK-005 | Task provenance (creator) is mandatory and preserved; deletion of referenced users is blocked. | Attr 8; C-TSK-011; REL-002 |
| REQ-TSK-006 | Concurrent updates must not silently overwrite each other. | Attr 11; C-TSK-008 |
| REQ-TSK-007 | Deleted tasks remain recoverable/auditable without appearing in operational queries. | Attr 12; I-TSK-003/004/006 (partial predicates) |

---

## 4. Cross-Entity Rules and Engine Notes

1. **Deletion policy**: physical `DELETE` is disallowed for both entities in normal operation; `users.status` and `tasks.deleted_at` are the sanctioned soft paths. `RESTRICT` actions enforce this at the engine level.
2. **Enums**: statuses/priorities use `varchar + CHECK` rather than native DB `ENUM` types to allow painless domain extension. (MySQL note: same pattern applies; consider `VARCHAR(16)` + `CHECK` ≥ 8.0.16. SQLite note: `CHECK` enforcement requires `PRAGMA foreign_keys = ON` per connection.)
3. **UUID generation**: PostgreSQL `pgcrypto`'s `gen_random_uuid()` (built-in since PG13). Applications MAY supply IDs; engines without native UUID default (SQLite/MySQL < 8.0.13) generate in the application layer.
4. **Trigger ownership**: `updated_at` maintenance and `revision` increments are application/trigger responsibilities documented here for F2; implementation deferred to F3 migration work.
5. **No migrations executed** in this stage; DDL will be derived from this dictionary.

## 5. Change Log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-11-04 | AG-007 Database Architect | Initial draft: entities User (ENT-001) and Task (ENT-002). |
