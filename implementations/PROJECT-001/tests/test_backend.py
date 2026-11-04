import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

_tmpdir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmpdir, "test.db")
os.environ["PORT"] = "0"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app


class TestBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.init_db()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def req(self, method, path, data=None, token=None):
        body = None if data is None else json.dumps(data).encode()
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        r = urllib.request.Request(self.url(path), data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, json.loads(raw or b"{}")

    def register(self, username, email="a@example.com", full_name="User", password="password123"):
        return self.req("POST", "/auth/register", {"username": username, "email": email, "full_name": full_name, "password": password})

    def login(self, username, password="password123"):
        return self.req("POST", "/auth/login", {"username": username, "password": password})

    def test_health(self):
        status, data = self.req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_register_and_login(self):
        status, data = self.register("alice", email="alice@example.com")
        self.assertEqual(status, 201)
        status, data = self.login("alice")
        self.assertEqual(status, 200)
        self.assertIn("token", data)

    def test_invalid_login(self):
        self.register("bob")
        status, data = self.login("bob", "wrong")
        self.assertEqual(status, 401)

    def test_unauthenticated_tasks(self):
        status, data = self.req("GET", "/tasks")
        self.assertEqual(status, 401)

    def test_task_crud_and_isolation(self):
        self.register("u1", email="u1@example.com")
        self.register("u2", email="u2@example.com")
        _, d1 = self.login("u1")
        _, d2 = self.login("u2")
        t1 = d1["token"]
        t2 = d2["token"]
        # create task as u1
        status, task = self.req("POST", "/tasks", {"title": "u1 task"}, token=t1)
        self.assertEqual(status, 201)
        task_id = task["id"]
        # u1 can read
        status, data = self.req("GET", f"/tasks/{task_id}", token=t1)
        self.assertEqual(status, 200)
        # u2 cannot read
        status, data = self.req("GET", f"/tasks/{task_id}", token=t2)
        self.assertEqual(status, 404)
        # u2 list does not include u1 task
        status, data = self.req("GET", "/tasks", token=t2)
        self.assertEqual(status, 200)
        self.assertFalse(any(x["id"] == task_id for x in data))
        # u2 cannot update
        status, data = self.req("PATCH", f"/tasks/{task_id}", {"title": "hacked"}, token=t2)
        self.assertEqual(status, 404)
        # u2 cannot delete
        status, data = self.req("DELETE", f"/tasks/{task_id}", token=t2)
        self.assertEqual(status, 404)
        # u1 can update and delete
        status, data = self.req("PATCH", f"/tasks/{task_id}", {"title": "updated"}, token=t1)
        self.assertEqual(status, 200)
        self.assertEqual(data["title"], "updated")
        status, data = self.req("DELETE", f"/tasks/{task_id}", token=t1)
        self.assertEqual(status, 200)

    def test_user_id_cannot_be_spoofed(self):
        self.register("spoof", email="spoof@example.com")
        _, d = self.login("spoof")
        token = d["token"]
        # attempt to create task with another user_id
        status, task = self.req("POST", "/tasks", {"title": "spoofed", "user_id": 999}, token=token)
        self.assertEqual(status, 201)
        # verify owner is authenticated user, not 999
        self.assertNotEqual(task["user_id"], 999)
        # list only own
        status, tasks = self.req("GET", "/tasks", token=token)
        self.assertTrue(all(t["user_id"] == task["user_id"] for t in tasks))

    def test_logout(self):
        self.register("logoutuser", email="logout@example.com")
        _, d = self.login("logoutuser")
        token = d["token"]
        status, _ = self.req("POST", "/auth/logout", token=token)
        self.assertEqual(status, 200)
        status, _ = self.req("GET", "/auth/me", token=token)
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
PY
