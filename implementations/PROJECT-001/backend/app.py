"""PROJECT-001 backend — minimal stdlib HTTP API over SQLite.

Endpoints:
    GET  /health   -> service and database status
    GET  /tasks    -> list all tasks (newest first)
    POST /tasks    -> create a task from a JSON body
                      {"title": str, "description"?: str, "status"?: str,
                       "priority"?: int, "due_date"?: str|null, "user_id"?: int}

Run:
    python app.py            # listens on http://127.0.0.1:8000

Environment overrides:
    PORT          (default 8000)
    DB_PATH       (default <backend>/tasks.db)
    SCHEMA_PATH   (default <backend>/../database/schema.sql)

Uses only the Python standard library (http.server + sqlite3).
The schema file database/schema.sql is the source of truth; it is
executed on startup with CREATE ... IF NOT EXISTS semantics.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = Path(os.environ.get("SCHEMA_PATH", BASE_DIR.parent / "database" / "schema.sql"))
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "tasks.db"))

VALID_STATUS = ("pending", "in_progress", "done", "cancelled")
DEFAULT_USER_ID = 1  # seeded at startup so POST /tasks works out of the box


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------

@contextmanager
def db():
    """Open a connection with FKs enabled; commit on success, always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the schema from database/schema.sql and seed a default user."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db() as conn:
        conn.executescript(schema_sql)
        # Placeholder user so tasks (user_id NOT NULL, FK -> users) can be
        # created without an auth flow in this minimal backend.
        conn.execute(
            """
            INSERT OR IGNORE INTO users
                (id, username, email, full_name, password_hash)
            VALUES
                (?, 'default', 'default@example.com', 'Default User',
                 'not-used-0000000000')
            """,
            (DEFAULT_USER_ID,),
        )


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "PROJECT001/0.1"

    # -- helpers -----------------------------------------------------------

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    # -- GET ---------------------------------------------------------------

    def do_GET(self) -> None:
        route = self._route()

        if route == "/health":
            try:
                with db() as conn:
                    conn.execute("SELECT 1;")
                self._send_json(200, {"status": "ok", "database": "up"})
            except sqlite3.Error as exc:
                self._send_json(503, {"status": "degraded",
                                      "database": "down",
                                      "error": str(exc)})
            return

        if route == "/tasks":
            try:
                with db() as conn:
                    rows = conn.execute(
                        "SELECT * FROM tasks ORDER BY id DESC;"
                    ).fetchall()
                self._send_json(200, [row_to_dict(r) for r in rows])
            except sqlite3.Error as exc:
                self._send_json(500, {"error": f"database error: {exc}"})
            return

        self._send_json(404, {"error": "not found"})

    # -- POST --------------------------------------------------------------

    def do_POST(self) -> None:
        if self._route() != "/tasks":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"")
        except (ValueError, TypeError):
            self._send_json(400, {"error": "invalid JSON body"})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"error": "body must be a JSON object"})
            return

        # Light validation; the schema's CHECK constraints are the backstop.
        title = payload.get("title")
        if not isinstance(title, str) or not (1 <= len(title.strip()) <= 200):
            self._send_json(400, {"error": "title is required (1-200 chars)"})
            return

        description = payload.get("description", "")
        if not isinstance(description, str) or len(description) > 5000:
            self._send_json(400, {"error": "description must be a string of at most 5000 chars"})
            return

        status = payload.get("status", "pending")
        if status not in VALID_STATUS:
            self._send_json(400, {"error": f"status must be one of {list(VALID_STATUS)}"})
            return

        priority = payload.get("priority", 3)
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            self._send_json(400, {"error": "priority must be an integer between 1 and 5"})
            return

        due_date = payload.get("due_date")
        if due_date is not None and not isinstance(due_date, str):
            self._send_json(400, {"error": "due_date must be a string (YYYY-MM-DD) or null"})
            return

        user_id = payload.get("user_id", DEFAULT_USER_ID)
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            self._send_json(400, {"error": "user_id must be an integer"})
            return

        try:
            with db() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO tasks
                        (user_id, title, description, status, priority, due_date)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (user_id, title.strip(), description, status, priority, due_date),
                )
                row = conn.execute(
                    "SELECT * FROM tasks WHERE id = ?;", (cur.lastrowid,)
                ).fetchone()
            self._send_json(201, row_to_dict(row))
        except sqlite3.IntegrityError as exc:
            self._send_json(400, {"error": f"constraint violated: {exc}"})
        except sqlite3.Error as exc:
            self._send_json(500, {"error": f"database error: {exc}"})


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> None:
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PROJECT-001 backend listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
