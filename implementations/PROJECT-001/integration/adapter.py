"""Integration adapter for PROJECT-001 backend API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class TaskApiClient:
    def __init__(self, base_url, token=None, timeout=10, max_retries=3, backoff=0.5):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method, path, data=None):
        url = self.base_url + path
        body = None if data is None else json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    return resp.status, json.loads(raw) if raw else None
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                payload = json.loads(raw) if raw else {"error": exc.reason}
                if 500 <= exc.code < 600 and attempt < self.max_retries:
                    time.sleep(self.backoff * (2 ** attempt))
                    continue
                return exc.code, payload
            except urllib.error.URLError:
                if attempt < self.max_retries:
                    time.sleep(self.backoff * (2 ** attempt))
                    continue
                raise

    def login(self, username, password):
        status, data = self._request("POST", "/auth/login", {"username": username, "password": password})
        if status == 200 and data and "token" in data:
            self.token = data["token"]
        return status, data

    def register(self, username, email, full_name, password):
        return self._request("POST", "/auth/register", {
            "username": username, "email": email, "full_name": full_name, "password": password
        })

    def me(self):
        return self._request("GET", "/auth/me")

    def logout(self):
        return self._request("POST", "/auth/logout")

    def list_tasks(self):
        return self._request("GET", "/tasks")

    def get_task(self, task_id):
        return self._request("GET", f"/tasks/{task_id}")

    def create_task(self, title, description="", status="pending", priority=3, due_date=None):
        return self._request("POST", "/tasks", {
            "title": title, "description": description, "status": status,
            "priority": priority, "due_date": due_date
        })

    def update_task(self, task_id, **fields):
        return self._request("PATCH", f"/tasks/{task_id}", fields)

    def delete_task(self, task_id):
        return self._request("DELETE", f"/tasks/{task_id}")
EOF
echo done