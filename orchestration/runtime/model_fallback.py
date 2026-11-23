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


def is_authorized_model(model: str) -> bool:
    return model in AUTHORIZED_MODELS


class ErrorClass:
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    AUTH = "auth"
    AMBIGUOUS = "ambiguous"


class FallbackStatus:
    RUNNING = "RUNNING"
    WAITING_RATE_LIMIT = "WAITING_RATE_LIMIT"
    WAITING_QUOTA_RESET = "WAITING_QUOTA_RESET"
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
    for pat in _TRANSIENT_PATTERNS:
        if re.search(pat, low):
            return ErrorClass.TRANSIENT
    return ErrorClass.AMBIGUOUS


def extract_retry_after(error_text: str) -> float | None:
    """Try to extract Retry-After seconds from error text."""
    m = re.search(r"retry[- ]after[:\s]+(\d+)", error_text, re.IGNORECASE)
    if m:
        return float(m.group(1))
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
        agents_dir = self.factory_root / ".opencode" / "agents"
        for agent_file in sorted(agents_dir.glob("ag-*.md")):
            m = re.match(r"(ag-\d{3})", agent_file.name)
            if not m:
                continue
            aid = m.group(1)
            primary = self._read_primary_model(agent_file)
            # BEAM_FREE_ONLY: hierarchy is exactly the authorized model.
            self._hierarchies[aid] = [AUTHORIZED_MODEL]

    def _read_primary_model(self, agent_file: Path) -> str:
        """Read model: from agent front-matter."""
        try:
            text = agent_file.read_text(encoding="utf-8")
        except OSError:
            return AUTHORIZED_MODEL
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                m = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE)
                if m:
                    candidate = m.group(1)
                    # Policy: only the authorized model is ever accepted.
                    if candidate in AUTHORIZED_MODELS:
                        return candidate
        return AUTHORIZED_MODEL

    def get_hierarchy(self, agent_id: str) -> list[str]:
        """Return ordered model list for agent (short id like ag-001)."""
        short = self._short_id(agent_id)
        return [AUTHORIZED_MODEL]

    def get_primary(self, agent_id: str) -> str:
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

        BEAM_FREE_ONLY: only the authorized model may be selected.
        """
        if not self.is_available(AUTHORIZED_MODEL):
            return None
        return AUTHORIZED_MODEL

    def is_authorized(self, model: str) -> bool:
        return model in AUTHORIZED_MODELS

    def verify_effective_model(self, model: str) -> bool:
        return model == AUTHORIZED_MODEL

    def handle_error(self, agent_id: str, current_model: str, error_text: str) -> dict:
        """Classify error and decide next action.

        Returns dict with:
          action: 'fallback' | 'wait' | 'retry' | 'intervention' | 'abort'
          next_model: model to use (if fallback/retry)
          wait_seconds: seconds to wait (if wait)
          error_class: classification
          status: FallbackStatus
        """
        # Policy guard: never handle a non-authorized model.
        if current_model not in AUTHORIZED_MODELS:
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
            self.mark_unavailable(AUTHORIZED_MODEL, seconds=3600)
            # No fallback: wait for Beam Free to recover.
            result.update(action="wait", wait_seconds=3600,
                          status=FallbackStatus.WAITING_QUOTA_RESET,
                          next_model=AUTHORIZED_MODEL)
        elif ec == ErrorClass.RATE_LIMIT:
            wait = extract_retry_after(error_text) or 60
            result.update(action="wait", next_model=current_model,
                          wait_seconds=wait, status=FallbackStatus.WAITING_RATE_LIMIT)
        elif ec == ErrorClass.TRANSIENT:
            result.update(action="retry", next_model=current_model,
                          wait_seconds=0, status=FallbackStatus.RUNNING)
        elif ec == ErrorClass.AUTH:
            result.update(action="intervention", status=FallbackStatus.NEEDS_INTERVENTION)
        else:  # ambiguous
            result.update(action="abort", status=FallbackStatus.FAILED)
        return result

    def log_change(self, agent_id: str, task_id: str | None, primary: str,
                   effective: str, fallback: str | None, reason: str | None,
                   status: str, wait_seconds: float = 0, retries: int = 0,
                   error_message: str | None = None, execution_id: str | None = None):
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
        }
        self._log.append(entry)
        return entry

    def get_log(self) -> list[dict]:
        return list(self._log)

    def recover_primary(self, agent_id: str) -> bool:
        """Check if primary model is available again. Returns True if recovered."""
        primary = self.get_primary(agent_id)
        return self.is_available(primary)
