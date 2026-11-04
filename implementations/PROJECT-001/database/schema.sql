-- =============================================================
-- PROJECT-001 — Database Schema
-- Engine: SQLite 3 (compatible with 3.24+ for UPSERT support)
-- =============================================================
-- NOTE: SQLite enforces foreign keys only when the pragma is
-- enabled per connection:
--   PRAGMA foreign_keys = ON;
-- It is included below as a reminder; it does not persist in
-- the schema itself.
-- =============================================================

PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------
-- Table: users
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER      PRIMARY KEY AUTOINCREMENT,
    username      TEXT         NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT         NOT NULL UNIQUE COLLATE NOCASE
                              CHECK (length(email) > 3
                                     AND email LIKE '%_@_%._%'),
    full_name     TEXT         NOT NULL
                              CHECK (length(full_name) BETWEEN 1 AND 200),
    password_hash TEXT         NOT NULL
                              CHECK (length(password_hash) >= 16),
    is_active     INTEGER      NOT NULL DEFAULT 1
                              CHECK (is_active IN (0, 1)),
    created_at    TEXT         NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT         NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
-- Table: tasks
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER  NOT NULL
                          REFERENCES users (id)
                          ON DELETE CASCADE
                          ON UPDATE CASCADE,
    title        TEXT     NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    description  TEXT     NOT NULL DEFAULT ''
                          CHECK (length(description) <= 5000),
    status       TEXT     NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'in_progress',
                                            'done', 'cancelled')),
    priority     INTEGER  NOT NULL DEFAULT 3
                          CHECK (priority BETWEEN 1 AND 5),
    due_date     TEXT     NULL
                          CHECK (due_date IS NULL
                                 OR due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    completed_at TEXT     NULL,
    created_at   TEXT     NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT     NOT NULL DEFAULT (datetime('now')),

    -- completed_at is only allowed for terminal statuses
    CHECK (
        completed_at IS NULL
        OR status IN ('done', 'cancelled')
    )
);

-- -------------------------------------------------------------
-- Indexes
-- -------------------------------------------------------------

-- Speed up task lookups by owner (the implicit FK index is not
-- created automatically by SQLite).
CREATE INDEX IF NOT EXISTS idx_tasks_user_id
    ON tasks (user_id);

-- Common filtered listing: a user's open tasks by due date.
CREATE INDEX IF NOT EXISTS idx_tasks_user_status_due
    ON tasks (user_id, status, due_date);

-- Queue/report queries over status and priority.
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
    ON tasks (status, priority);

-- Partial index: only overdue, non-terminal tasks.
CREATE INDEX IF NOT EXISTS idx_tasks_overdue
    ON tasks (due_date)
    WHERE status IN ('pending', 'in_progress')
      AND due_date IS NOT NULL;

-- Supporting lookups on user activity state.
CREATE INDEX IF NOT EXISTS idx_users_is_active
    ON users (is_active)
    WHERE is_active = 1;

-- -------------------------------------------------------------
-- Trigger: keep tasks.updated_at current on modification
-- -------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_tasks_touch_updated_at
AFTER UPDATE ON tasks
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tasks
       SET updated_at = datetime('now')
     WHERE id = OLD.id;
END;

-- -------------------------------------------------------------
-- Trigger: keep users.updated_at current on modification
-- -------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_users_touch_updated_at
AFTER UPDATE ON users
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE users
       SET updated_at = datetime('now')
     WHERE id = OLD.id;
END;

-- -------------------------------------------------------------
-- Table: sessions
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT    NOT NULL UNIQUE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
