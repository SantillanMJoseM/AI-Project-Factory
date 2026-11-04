"""PROJECT-001 integration adapter: TaskApiClient (stdlib urllib, retry on 5xx)."""

import json
import time
import urllib.error
import urllib.request


class TaskApiError(Exception):
    """Raised when the Task API returns a non-recoverable error."""

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


class TaskApiClient:
    """Minimal JSON HTTP client for the Task API using urllib."""

    def __init__(self, base_url, api_key=None, timeout=10, max_retries=3, backoff=0.5):
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key  # never logged or echoed in errors
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def request(self, method, path, payload=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        data = None
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as exc:
                if exc.code >= 500 and attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.backoff * (2 ** (attempt - 1)))
                    continue
                raise TaskApiError(
                    f"{method} {url} failed: HTTP {exc.code}",
                    status=exc.code,
                    body=exc.read().decode("utf-8", errors="replace"),
                ) from exc
            except urllib.error.URLError as exc:
                raise TaskApiError(f"{method} {url} failed: {exc.reason}") from exc

    # -- task operations -------------------------------------------------

    def list_tasks(self):
        return self.request("GET", "/tasks")

    def get_task(self, task_id):
        return self.request("GET", f"/tasks/{task_id}")

    def create_task(self, task):
        return self.request("POST", "/tasks", payload=task)

    def update_task(self, task_id, task):
        return self.request("PATCH", f"/tasks/{task_id}", payload=task)

    def delete_task(self, task_id):
        return self.request("DELETE", f"/tasks/{task_id}")
