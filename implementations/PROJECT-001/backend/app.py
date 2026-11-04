"""PROJECT-001 backend — authenticated task management API over SQLite."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = Path(os.environ.get("SCHEMA_PATH", BASE_DIR.parent / "database" / "schema.sql"))
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "tasks.db"))

VALID_STATUS = ("pending", "in_progress", "done", "cancelled")
SESSION_TTL_HOURS = 8


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2$100000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db() as conn:
        conn.executescript(schema_sql)


def row_to_dict(row):
    return dict(row) if row is not None else None


def get_user_by_token(token: str):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with db() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (token_hash, now_iso()),
        ).fetchone()
    return row_to_dict(row)


def require_auth(handler):
    auth = handler.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return get_user_by_token(auth[7:].strip())


def parse_body(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def send_json(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "PROJECT001/0.2"

    def _route(self):
        return urlparse(self.path).path.rstrip("/") or "/"

    def do_GET(self):
        route = self._route()
        if route == "/health":
            try:
                with db() as conn:
                    conn.execute("SELECT 1;")
                send_json(self, 200, {"status": "ok", "database": "up"})
            except sqlite3.Error as exc:
                send_json(self, 503, {"status": "degraded", "database": "down", "error": str(exc)})
            return

        if route == "/auth/me":
            user = require_auth(self)
            if not user:
                send_json(self, 401, {"error": "authentication required"})
                return
            send_json(self, 200, {"id": user["id"], "username": user["username"], "email": user["email"], "full_name": user["full_name"]})
            return

        if route == "/tasks":
            user = require_auth(self)
            if not user:
                send_json(self, 401, {"error": "authentication required"})
                return
            with db() as conn:
                rows = conn.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
            send_json(self, 200, [row_to_dict(r) for r in rows])
            return

        # /tasks/{id}
        parts = route.split("/")
        if len(parts) == 3 and parts[1] == "tasks":
            user = require_auth(self)
            if not user:
                send_json(self, 401, {"error": "authentication required"})
                return
            try:
                task_id = int(parts[2])
            except ValueError:
                send_json(self, 400, {"error": "invalid task id"})
                return
            with db() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user["id"])).fetchone()
            if not row:
                send_json(self, 404, {"error": "task not found"})
                return
            send_json(self, 200, row_to_dict(row))
            return

        send_json(self, 404, {"error": "not found"})

    def do_POST(self):
        route = self._route()

        if route == "/auth/register":
            try:
                payload = parse_body(self)
            except Exception:
                send_json(self, 400, {"error": "invalid JSON body"})
                return
            username = payload.get("username")
            email = payload.get("email")
            full_name = payload.get("full_name")
            password = payload.get("password")
            if not all(isinstance(x, str) and x.strip() for x in (username, email, full_name, password)):
                send_json(self, 400, {"error": "username, email, full_name, password are required"})
                return
            if len(password) < 8:
                send_json(self, 400, {"error": "password must be at least 8 characters"})
                return
            try:
                with db() as conn:
                    cur = conn.execute(
                        "INSERT INTO users (username, email, full_name, password_hash) VALUES (?, ?, ?, ?)",
                        (username.strip(), email.strip(), full_name.strip(), hash_password(password)),
                    )
                    row = conn.execute("SELECT id, username, email, full_name FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
                send_json(self, 201, row_to_dict(row))
            except sqlite3.IntegrityError:
                send_json(self, 409, {"error": "username or email already exists"})
            except sqlite3.Error as exc:
                send_json(self, 500, {"error": str(exc)})
            return

        if route == "/auth/login":
            try:
                payload = parse_body(self)
            except Exception:
                send_json(self, 400, {"error": "invalid JSON body"})
                return
            username = payload.get("username")
            password = payload.get("password")
            if not isinstance(username, str) or not isinstance(password, str):
                send_json(self, 400, {"error": "username and password are required"})
                return
            with db() as conn:
                user = conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                send_json(self, 401, {"error": "invalid credentials"})
                return
            token = secrets.token_urlsafe(32)
            expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
            with db() as conn:
                conn.execute(
                    "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                    (hashlib.sha256(token.encode()).hexdigest(), user["id"], expires),
                )
            send_json(self, 200, {"token": token, "token_type": "Bearer", "expires_at": expires})
            return

        if route == "/auth/logout":
            user = require_auth(self)
            if not user:
                send_json(self, 401, {"error": "authentication required"})
                return
            auth = self.headers.get("Authorization", "")
            token = auth[7:].strip()
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            with db() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            send_json(self, 200, {"status": "logged_out"})
            return

        if route == "/tasks":
            user = require_auth(self)
            if not user:
                send_json(self, 401, {"error": "authentication required"})
                return
            try:
                payload = parse_body(self)
            except Exception:
                send_json(self, 400, {"error": "invalid JSON body"})
                return
            title = payload.get("title")
            if not isinstance(title, str) or not (1 <= len(title.strip()) <= 200):
                send_json(self, 400, {"error": "title is required (1-200 chars)"})
                return
            description = payload.get("description", "")
            if not isinstance(description, str) or len(description) > 5000:
                send_json(self, 400, {"error": "description must be a string of at most 5000 chars"})
                return
            status = payload.get("status", "pending")
            if status not in VALID_STATUS:
                send_json(self, 400, {"error": f"status must be one of {list(VALID_STATUS)}"})
                return
            priority = payload.get("priority", 3)
            if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
                send_json(self, 400, {"error": "priority must be an integer between 1 and 5"})
                return
            due_date = payload.get("due_date")
            if due_date is not None and not isinstance(due_date, str):
                send_json(self, 400, {"error": "due_date must be a string or null"})
                return
            with db() as conn:
                cur = conn.execute(
                    "INSERT INTO tasks (user_id, title, description, status, priority, due_date) VALUES (?, ?, ?, ?, ?, ?)",
                    (user["id"], title.strip(), description, status, priority, due_date),
                )
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
            send_json(self, 201, row_to_dict(row))
            return

        send_json(self, 404, {"error": "not found"})

    def do_PATCH(self):
        route = self._route()
        parts = route.split("/")
        if len(parts) != 3 or parts[1] != "tasks":
            send_json(self, 404, {"error": "not found"})
            return
        user = require_auth(self)
        if not user:
            send_json(self, 401, {"error": "authentication required"})
            return
        try:
            task_id = int(parts[2])
        except ValueError:
            send_json(self, 400, {"error": "invalid task id"})
            return
        try:
            payload = parse_body(self)
        except Exception:
            send_json(self, 400, {"error": "invalid JSON body"})
            return
        with db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user["id"])).fetchone()
            if not row:
                send_json(self, 404, {"error": "task not found"})
                return
            fields = []
            values = []
            if "title" in payload:
                if not isinstance(payload["title"], str) or not (1 <= len(payload["title"].strip()) <= 200):
                    send_json(self, 400, {"error": "invalid title"})
                    return
                fields.append("title = ?")
                values.append(payload["title"].strip())
            if "description" in payload:
                if not isinstance(payload["description"], str) or len(payload["description"]) > 5000:
                    send_json(self, 400, {"error": "invalid description"})
                    return
                fields.append("description = ?")
                values.append(payload["description"])
            if "status" in payload:
                if payload["status"] not in VALID_STATUS:
                    send_json(self, 400, {"error": "invalid status"})
                    return
                fields.append("status = ?")
                values.append(payload["status"])
            if "priority" in payload:
                p = payload["priority"]
                if isinstance(p, bool) or not isinstance(p, int) or not 1 <= p <= 5:
                    send_json(self, 400, {"error": "invalid priority"})
                    return
                fields.append("priority = ?")
                values.append(p)
            if "due_date" in payload:
                dd = payload["due_date"]
                if dd is not None and not isinstance(dd, str):
                    send_json(self, 400, {"error": "invalid due_date"})
                    return
                fields.append("due_date = ?")
                values.append(dd)
            if not fields:
                send_json(self, 400, {"error": "no updatable fields provided"})
                return
            values.append(task_id)
            values.append(user["id"])
            conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND user_id = ?", values)
            row = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user["id"])).fetchone()
        send_json(self, 200, row_to_dict(row))

    def do_DELETE(self):
        route = self._route()
        parts = route.split("/")
        if len(parts) != 3 or parts[1] != "tasks":
            send_json(self, 404, {"error": "not found"})
            return
        user = require_auth(self)
        if not user:
            send_json(self, 401, {"error": "authentication required"})
            return
        try:
            task_id = int(parts[2])
        except ValueError:
            send_json(self, 400, {"error": "invalid task id"})
            return
        with db() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user["id"]))
            if cur.rowcount == 0:
                send_json(self, 404, {"error": "task not found"})
                return
        send_json(self, 200, {"status": "deleted"})

    def log_message(self, format, *args):
        return


def main():
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
