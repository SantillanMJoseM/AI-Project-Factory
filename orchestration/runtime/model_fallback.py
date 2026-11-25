"""Centralized model fallback manager for AI-Project-Factory.

Provides ordered model selection, error classification, fallback,
rate-limit waiting, and primary-model recovery for all 18 agents.
All models are restricted to the opencode-go provider.
"""

import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from orchestration.runtime.model_hierarchies import (
    AUTHORIZED_MODEL,
    AUTHORIZED_MODELS,
    FALLBACK_ALTERNATIVES,
    PROVIDER,
)

def _authorized_models() -> set:
    try:
        from orchestration.runtime.model_routing import is_model_routing_v2, authorized_models
        if is_model_routing_v2():
            return authorized_models()
    except ImportError:
        pass
    return {"opencode-go/beam-free"}


def is_authorized_model(model: str) -> bool:
    return model in _authorized_models()


class ErrorClass:
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    AUTH = "auth"
    INCOMPATIBLE = "incompatible"
    PROVIDER_DOWN = "provider_down"
    AMBIGUOUS = "ambiguous"


class FallbackStatus:
    RUNNING = "RUNNING"
    WAITING_RATE_LIMIT = "WAITING_RATE_LIMIT"
    WAITING_QUOTA_RESET = "WAITING_QUOTA_RESET"
    WAITING_TRANSIENT_RETRY = "WAITING_TRANSIENT_RETRY"
    FALLBACK_ACTIVE = "FALLBACK_ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_INTERVENTION = "NEEDS_INTERVENTION"


# Patterns for error classification (case-insensitive)
_QUOTA_PATTERNS = [
    r"quota", r"usage limit reached", r"free usage limit", r"limit reached",
    r"exhausted", r"no credits", r"insufficient credits",
]
_RATE_PATTERNS = [
    r"rate.?limit", r"retry.?after", r"hourly limit", r"window",
    r"too many requests", r"429",
]
_TRANSIENT_PATTERNS = [
    r"timeout", r"timed out", r"5\d\d", r"network", r"unavailable",
    r"connection", r"temporary", r"transient",
]
_AUTH_PATTERNS = [
    r"auth", r"invalid key", r"unauthorized", r"forbidden", r"401", r"403",
    r"api.?key", r"credential",
]
_INCOMPATIBLE_PATTERNS = [
    r"not found", r"unsupported", r"invalid model", r"model not", r"no such model",
    r"does not exist", r"unavailable model",
]
_PROVIDER_DOWN_PATTERNS = [
    r"service unavailable", r"502", r"503", r"504", r"connection refused",
    r"dns", r"host unreachable", r"provider down", r"backend down",
]


def classify_error(error_text: str) -> str:
    """Classify an error string into one of ErrorClass constants."""
    if not error_text:
        return ErrorClass.AMBIGUOUS
    low = error_text.lower()
    for pat in _QUOTA_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.QUOTA_EXHAUSTED
    for pat in _RATE_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.RATE_LIMIT
    for pat in _AUTH_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.AUTH
    for pat in _INCOMPATIBLE_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.INCOMPATIBLE
    for pat in _PROVIDER_DOWN_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.PROVIDER_DOWN
    for pat in _TRANSIENT_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.TRANSIENT
    return ErrorClass.AMBIGUOUS


def quota_reset_seconds(error_text: str) -> float:
    """Estimate seconds until quota reset based on error text.

    Distinguishes hourly (3600), daily (86400) and weekly (604800) limits.
    Falls back to 3600 when no qualifier is present.
    """
    # Explicit Retry-After takes precedence over qualifiers.
    ra = extract_retry_after(error_text)
    if ra is not None:
        return ra
    low = (error_text or "").lower()
    if re.search(r"week", low):
        return 604800.0
    if re.search(r"day|daily", low):
        return 86400.0
    if re.search(r"hour|hourly", low):
        return 3600.0
    return 3600.0


def extract_retry_after(error_text: str) -> float | None:
    """Extract Retry-After seconds from error text.

    Supports:
    - numeric seconds: "Retry-After: 120" or "Retry-After 120"
    - HTTP-date: "Retry-After: Wed, 21 Oct 2015 07:28:00 GMT"
    Returns None when no reliable value is present (never invents a wait).
    """
    if not error_text:
        return None
    # Numeric seconds.
    m = re.search(r"retry[- ]after[:\s]+(\d+(?:\.\d+)?)", error_text, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if val < 0:
            return None
        return val
    # HTTP-date form.
    m = re.search(r"retry[- ]after[:\s]+([A-Za-z]{3},\s*\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+GMT)", error_text, re.IGNORECASE)
    if m:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(m.group(1))
            now = datetime.now(timezone.utc)
            delta = (dt - now).total_seconds()
            if delta < 0:
                return 0.0
            return float(delta)
        except Exception:
            return None
    return None


class ModelFallbackManager:
    """Manages model hierarchies, fallback selection, and recovery."""

    def __init__(self, factory_root: Path | None = None):
        self.factory_root = factory_root or Path(__file__).resolve().parents[2]
        self._hierarchies: dict[str, list[str]] = {}
        self._unavailable: dict[str, float] = {}  # model -> unavailable_until timestamp
        self._log: list[dict] = []
        self._load_hierarchies()

    def _load_hierarchies(self):
        """Build hierarchies from agent front-matter + alternatives."""
        try:
            from orchestration.runtime.model_routing import (
                is_model_routing_v2, authorized_models, fallback_hierarchy, primary_model,
            )
            v2 = is_model_routing_v2()
        except ImportError:
            v2 = False
        agents_dir = self.factory_root / ".opencode" / "agents"
        for agent_file in sorted(agents_dir.glob("ag-*.md")):
            m = re.match(r"(ag-\d{3})", agent_file.name)
            if not m:
                continue
            aid = m.group(1)
            if v2:
                self._hierarchies[aid] = fallback_hierarchy(aid)
            else:
                self._hierarchies[aid] = [AUTHORIZED_MODEL]

    def _read_primary_model(self, agent_file: Path) -> str:
        """Read model: from agent front-matter."""
        try:
            text = agent_file.read_text(encoding="utf-8")
        except OSError:
            return self.get_primary("ag-001")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                m = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE)
                if m:
                    candidate = m.group(1)
                    try:
                        from orchestration.runtime.model_routing import is_authorized
                        if is_authorized(candidate):
                            return candidate
                    except ImportError:
                        if candidate in _authorized_models():
                            return candidate
        try:
            from orchestration.runtime.model_routing import primary_model
            return primary_model("ag-001")
        except ImportError:
            return AUTHORIZED_MODEL

    def get_hierarchy(self, agent_id: str) -> list[str]:
        """Return ordered model list for agent (short id like ag-001)."""
        short = self._short_id(agent_id)
        try:
            from orchestration.runtime.model_routing import is_model_routing_v2, fallback_hierarchy
            if is_model_routing_v2():
                return fallback_hierarchy(short)
        except ImportError:
            pass
        return [AUTHORIZED_MODEL]

    def get_primary(self, agent_id: str) -> str:
        short = self._short_id(agent_id)
        try:
            from orchestration.runtime.model_routing import is_model_routing_v2, primary_model
            if is_model_routing_v2():
                return primary_model(short)
        except ImportError:
            pass
        return AUTHORIZED_MODEL

    def _short_id(self, agent_id: str) -> str:
        m = re.match(r"(ag-\d{3})", agent_id.lower())
        return m.group(1) if m else agent_id.lower()

    def is_available(self, model: str) -> bool:
        """Check if model is currently available (not marked unavailable)."""
        until = self._unavailable.get(model)
        if until is None:
            return True
        if time.time() >= until:
            del self._unavailable[model]
            return True
        return False

    def mark_unavailable(self, model: str, seconds: float = 3600):
        """Mark model as unavailable for a duration (default 1h)."""
        self._unavailable[model] = time.time() + seconds

    def select_model(self, agent_id: str) -> str | None:
        """Select the best available model for agent. Returns None if unavailable.

        Under BEAM_FREE_ONLY only beam-free is selectable.
        Under MODEL_ROUTING_V2 the primary (and alternatives) are tried in order.
        """
        hierarchy = self.get_hierarchy(agent_id)
        for model in hierarchy:
            if self.is_available(model):
                return model
        return None

    def is_authorized(self, model: str) -> bool:
        return model in _authorized_models()

    def verify_effective_model(self, model: str) -> bool:
        return model in _authorized_models()

    def handle_error(self, agent_id: str, current_model: str, error_text: str, retries: int = 0) -> dict:
        """Classify error and decide next action.

        Returns dict with:
          action: 'fallback' | 'wait' | 'retry' | 'intervention' | 'abort'
          next_model: model to use (if fallback/retry)
          wait_seconds: seconds to wait (if wait)
          error_class: classification
          status: FallbackStatus
        """
        # Policy guard: never handle a non-authorized model.
        if current_model not in _authorized_models():
            return {
                "error_class": ErrorClass.AUTH,
                "action": "intervention",
                "next_model": None,
                "wait_seconds": 0,
                "status": FallbackStatus.NEEDS_INTERVENTION,
            }

        ec = classify_error(error_text)
        result = {
            "error_class": ec,
            "action": "abort",
            "next_model": None,
            "wait_seconds": 0,
            "status": FallbackStatus.FAILED,
        }
        if ec == ErrorClass.QUOTA_EXHAUSTED:
            wait = quota_reset_seconds(error_text)
            self.mark_unavailable(current_model, seconds=wait)
            # Fallback to next available model in hierarchy (or beam-free reserve).
            hierarchy = self.get_hierarchy(agent_id)
            next_model = None
            for m in hierarchy:
                if m != current_model and self.is_available(m):
                    next_model = m
                    break
            if next_model is None:
                next_model = "opencode-go/beam-free"
            result.update(action="wait", wait_seconds=wait,
                          status=FallbackStatus.WAITING_QUOTA_RESET,
                          next_model=next_model)
        elif ec == ErrorClass.RATE_LIMIT:
            wait = extract_retry_after(error_text) or 60
            result.update(action="wait", next_model=current_model,
                          wait_seconds=wait, status=FallbackStatus.WAITING_RATE_LIMIT)
        elif ec == ErrorClass.TRANSIENT:
            # Non-blocking: persist a WAITING_TRANSIENT_RETRY state with a
            # bounded backoff deadline; do not sleep in-process.
            wait = min(2 ** (retries + 1), 30)
            result.update(action="wait", next_model=current_model,
                          wait_seconds=wait, status=FallbackStatus.WAITING_TRANSIENT_RETRY)
        elif ec == ErrorClass.AUTH:
            result.update(action="intervention", status=FallbackStatus.NEEDS_INTERVENTION)
        elif ec == ErrorClass.INCOMPATIBLE:
            result.update(action="intervention", status=FallbackStatus.NEEDS_INTERVENTION)
        elif ec == ErrorClass.PROVIDER_DOWN:
            result.update(action="wait", wait_seconds=60,
                          status=FallbackStatus.WAITING_RATE_LIMIT,
                          next_model=current_model)
        else:  # ambiguous
            result.update(action="abort", status=FallbackStatus.FAILED)
        return result

    def log_change(self, agent_id: str, task_id: str | None, primary: str,
                   effective: str, fallback: str | None, reason: str | None,
                   status: str, wait_seconds: float = 0, retries: int = 0,
                   error_message: str | None = None, execution_id: str | None = None,
                   attempt_number: int = 0, error_class: str | None = None,
                   http_status: int | None = None, retry_after: float | None = None,
                   reset_timestamp: str | None = None, wait_until: str | None = None,
                   completed_at: str | None = None):
        entry = {
            "log_id": f"mfl-{uuid.uuid4().hex[:12]}",
            "execution_id": execution_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "primary_model": primary,
            "effective_model": effective,
            "fallback_model": fallback,
            "reason": reason,
            "provider": PROVIDER,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "wait_seconds": wait_seconds,
            "retries": retries,
            "status": status,
            "error_message": error_message,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attempt_number": attempt_number,
            "error_class": error_class,
            "http_status": http_status,
            "retry_after": retry_after,
            "reset_timestamp": reset_timestamp,
            "wait_until": wait_until,
            "completed_at": completed_at,
        }
        self._log.append(entry)
        return entry

    def get_log(self) -> list[dict]:
        return list(self._log)

    def recover_primary(self, agent_id: str) -> bool:
        """Check if primary model is available again. Returns True if recovered."""
        primary = self.get_primary(agent_id)
        return self.is_available(primary)
