"""Go Plus usage tracker for AI-Project-Factory.

Queries the official OpenCode Go endpoints:
- GET https://opencode.ai/inference/go/v1/usage  (rolling/weekly/monthly)
- GET https://opencode.ai/inference/go/v1/models (model catalog + pricing)

Authentication via Bearer token from the OpenCode credential store.
No secrets are printed or logged.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

USAGE_URL = "https://opencode.ai/inference/go/v1/usage"
MODELS_URL = "https://opencode.ai/inference/go/v1/models"

# Conservative internal consumption targets (percent of monthly).
MONTHLY_TARGETS = {
    "week1": 15, "week2": 40, "week3": 65, "week4": 90, "final": 90,
}
ALERT_THRESHOLDS = {50: "warning", 70: "reduce_aux", 85: "prioritize_essentials", 95: "stop_non_critical"}


def _get_api_key() -> Optional[str]:
    """Retrieve the Go API key from the credential store (read-only)."""
    # Try env first
    for env_var in ("OPENCODE_GO_API_KEY", "OPENCODE_API_KEY"):
        val = os.environ.get(env_var)
        if val:
            return val
    # Try credential DB
    db_path = Path.home() / ".local/share/opencode/opencode.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            row = conn.execute("SELECT value FROM credential WHERE integration_id='opencode'").fetchone()
            conn.close()
            if row:
                data = json.loads(row[0])
                if isinstance(data, dict) and "key" in data:
                    return data["key"]
        except Exception:
            pass
    return None


def fetch_usage(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Fetch usage from the Go endpoint. Returns dict with rolling/weekly/monthly."""
    key = api_key or _get_api_key()
    if not key:
        return {"error": "no_api_key", "usage": None}
    try:
        req = urllib.request.Request(USAGE_URL, headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "opencode/2.4.1",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "usage": None}


def fetch_models(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Fetch model catalog from the Go endpoint."""
    key = api_key or _get_api_key()
    if not key:
        return {"error": "no_api_key", "data": []}
    try:
        req = urllib.request.Request(MODELS_URL, headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "opencode/2.4.1",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "data": []}


def check_budget(usage: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate consumption against internal targets and return alerts."""
    result = {"alerts": [], "status": "ok", "usage": usage}
    u = usage.get("usage", {}) if isinstance(usage, dict) else {}
    monthly = u.get("monthly", {}) if isinstance(u, dict) else {}
    percent = monthly.get("percent", 0) if isinstance(monthly, dict) else 0
    for threshold, action in sorted(ALERT_THRESHOLDS.items()):
        if percent >= threshold:
            result["alerts"].append({"threshold": threshold, "action": action})
    if percent >= 95:
        result["status"] = "critical"
    elif percent >= 85:
        result["status"] = "high"
    elif percent >= 70:
        result["status"] = "elevated"
    elif percent >= 50:
        result["status"] = "warning"
    return result


def model_pricing(models_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Extract pricing from models endpoint response."""
    pricing = {}
    for m in models_data.get("data", []):
        mid = m.get("id")
        cost = m.get("cost", {}).get("text", {})
        inp = cost.get("input", {}).get("price", 0)
        out = cost.get("output", {}).get("price", 0)
        cache_read = cost.get("input", {}).get("cache", {}).get("read", 0)
        ctx = m.get("limit", {}).get("context", 0)
        pricing[mid] = {"input": inp, "output": out, "cache_read": cache_read, "context": ctx}
    return pricing


if __name__ == "__main__":
    # CLI for manual usage check (does not print secrets)
    u = fetch_usage()
    print("Usage:", json.dumps(u, indent=2))
    m = fetch_models()
    print("Models:", len(m.get("data", [])))
    p = model_pricing(m)
    for mid, info in sorted(p.items()):
        print(f"  {mid}: in=${info['input']}/M out=${info['output']}/M ctx={info['context']}")