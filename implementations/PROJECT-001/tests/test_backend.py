import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

# Configure temp DB before importing app.
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

    def test_health(self):
        import urllib.request
        with urllib.request.urlopen(self.url("/health")) as r:
            self.assertEqual(r.status, 200)
            data = __import__("json").loads(r.read())
            self.assertEqual(data["status"], "ok")

    def test_create_and_list_task(self):
        import json, urllib.request
        body = json.dumps({"title": "Test task"}).encode()
        req = urllib.request.Request(self.url("/tasks"), data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 201)
            created = json.loads(r.read())
            self.assertEqual(created["title"], "Test task")
        with urllib.request.urlopen(self.url("/tasks")) as r:
            tasks = json.loads(r.read())
            self.assertTrue(any(t["title"] == "Test task" for t in tasks))


if __name__ == "__main__":
    unittest.main()