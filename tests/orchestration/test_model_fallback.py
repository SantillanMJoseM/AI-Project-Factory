"""Unit tests for ModelFallbackManager (BEAM_FREE_ONLY policy)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import time
import unittest
from unittest.mock import patch

from orchestration.runtime.model_fallback import (
    ModelFallbackManager, classify_error, extract_retry_after,
    ErrorClass, FallbackStatus,
)
from orchestration.runtime.model_hierarchies import AUTHORIZED_MODEL, AUTHORIZED_MODELS


class TestErrorClassification(unittest.TestCase):
    def test_quota_exhausted(self):
        self.assertEqual(classify_error("Free usage limit reached"), ErrorClass.QUOTA_EXHAUSTED)
        self.assertEqual(classify_error("quota exhausted"), ErrorClass.QUOTA_EXHAUSTED)

    def test_rate_limit(self):
        self.assertEqual(classify_error("rate limit exceeded"), ErrorClass.RATE_LIMIT)
        self.assertEqual(classify_error("429 Too Many Requests"), ErrorClass.RATE_LIMIT)
        self.assertEqual(classify_error("Retry-After: 60"), ErrorClass.RATE_LIMIT)

    def test_transient(self):
        self.assertEqual(classify_error("timeout"), ErrorClass.TRANSIENT)
        self.assertEqual(classify_error("connection reset"), ErrorClass.TRANSIENT)
        self.assertEqual(classify_error("network error"), ErrorClass.TRANSIENT)

    def test_auth(self):
        self.assertEqual(classify_error("invalid api key"), ErrorClass.AUTH)
        self.assertEqual(classify_error("401 Unauthorized"), ErrorClass.AUTH)

    def test_ambiguous(self):
        self.assertEqual(classify_error("something weird"), ErrorClass.AMBIGUOUS)
        self.assertEqual(classify_error(""), ErrorClass.AMBIGUOUS)

    def test_retry_after_extraction(self):
        self.assertEqual(extract_retry_after("Retry-After: 120"), 120.0)
        self.assertIsNone(extract_retry_after("no retry info"))


class TestHierarchies(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_all_agents_have_hierarchy(self):
        for i in range(1, 19):
            aid = f"ag-{i:03d}"
            h = self.fm.get_hierarchy(aid)
            self.assertGreater(len(h), 0, f"{aid} has no hierarchy")
            self.assertEqual(h, [AUTHORIZED_MODEL], f"{aid} hierarchy not BEAM_FREE_ONLY")

    def test_primary_matches_authorized_model(self):
        # Under BEAM_FREE_ONLY every agent's primary is the authorized model.
        for i in range(1, 19):
            aid = f"ag-{i:03d}"
            self.assertEqual(self.fm.get_primary(aid), AUTHORIZED_MODEL)

    def test_no_duplicate_models(self):
        for i in range(1, 19):
            aid = f"ag-{i:03d}"
            h = self.fm.get_hierarchy(aid)
            self.assertEqual(len(h), len(set(h)), f"{aid} has duplicate models")

    def test_policy_guard_rejects_non_authorized(self):
        # A non-authorized current model must trigger intervention, never fallback.
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "quota exhausted")
        self.assertEqual(d["error_class"], ErrorClass.AUTH)
        self.assertEqual(d["action"], "intervention")
        self.assertEqual(d["status"], FallbackStatus.NEEDS_INTERVENTION)
        self.assertIsNone(d["next_model"])


class TestFallbackSelection(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_select_primary_when_available(self):
        model = self.fm.select_model("ag-001")
        self.assertEqual(model, AUTHORIZED_MODEL)

    def test_all_unavailable_returns_none(self):
        self.fm.mark_unavailable(AUTHORIZED_MODEL, seconds=3600)
        self.assertIsNone(self.fm.select_model("ag-001"))

    def test_recovery(self):
        self.fm.mark_unavailable(AUTHORIZED_MODEL, seconds=0.1)
        time.sleep(0.2)
        self.assertTrue(self.fm.recover_primary("ag-001"))
        self.assertTrue(self.fm.is_available(AUTHORIZED_MODEL))


class TestHandleError(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_quota_waits_no_fallback(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "quota exhausted")
        self.assertEqual(d["error_class"], ErrorClass.QUOTA_EXHAUSTED)
        self.assertEqual(d["action"], "wait")
        self.assertEqual(d["wait_seconds"], 3600.0)
        self.assertEqual(d["status"], FallbackStatus.WAITING_QUOTA_RESET)
        self.assertEqual(d["next_model"], AUTHORIZED_MODEL)

    def test_rate_limit_wait(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "rate limit Retry-After: 30")
        self.assertEqual(d["error_class"], ErrorClass.RATE_LIMIT)
        self.assertEqual(d["action"], "wait")
        self.assertEqual(d["wait_seconds"], 30.0)
        self.assertEqual(d["status"], FallbackStatus.WAITING_RATE_LIMIT)

    def test_rate_limit_default_wait(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "rate limit exceeded")
        self.assertEqual(d["error_class"], ErrorClass.RATE_LIMIT)
        self.assertEqual(d["action"], "wait")
        self.assertEqual(d["wait_seconds"], 60.0)

    def test_transient_retry(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "timeout")
        self.assertEqual(d["error_class"], ErrorClass.TRANSIENT)
        self.assertEqual(d["action"], "wait")
        self.assertEqual(d["status"], FallbackStatus.WAITING_TRANSIENT_RETRY)
        self.assertGreater(d["wait_seconds"], 0)

    def test_auth_intervention(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "invalid api key")
        self.assertEqual(d["error_class"], ErrorClass.AUTH)
        self.assertEqual(d["action"], "intervention")
        self.assertEqual(d["status"], FallbackStatus.NEEDS_INTERVENTION)

    def test_ambiguous_abort(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "unknown error xyz")
        self.assertEqual(d["error_class"], ErrorClass.AMBIGUOUS)
        self.assertEqual(d["action"], "abort")
        self.assertEqual(d["status"], FallbackStatus.FAILED)

    def test_incompatible_intervention(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "model not found")
        self.assertEqual(d["error_class"], ErrorClass.INCOMPATIBLE)
        self.assertEqual(d["action"], "intervention")
        self.assertEqual(d["status"], FallbackStatus.NEEDS_INTERVENTION)

    def test_provider_down_wait(self):
        d = self.fm.handle_error("ag-001", AUTHORIZED_MODEL, "provider down")
        self.assertEqual(d["error_class"], ErrorClass.PROVIDER_DOWN)
        self.assertEqual(d["action"], "wait")

    def test_quota_weekly_reset(self):
        from orchestration.runtime.model_fallback import quota_reset_seconds
        self.assertEqual(quota_reset_seconds("weekly quota exhausted"), 604800.0)
        self.assertEqual(quota_reset_seconds("daily limit reached"), 86400.0)
        self.assertEqual(quota_reset_seconds("hourly limit reached"), 3600.0)


class TestLogging(unittest.TestCase):
    def test_log_change(self):
        fm = ModelFallbackManager()
        entry = fm.log_change("ag-001", "task-1", AUTHORIZED_MODEL,
                              AUTHORIZED_MODEL, None, "quota_exhausted",
                              FallbackStatus.WAITING_QUOTA_RESET, wait_seconds=3600)
        self.assertEqual(entry["agent_id"], "ag-001")
        self.assertEqual(entry["provider"], "opencode-go")
        self.assertEqual(entry["primary_model"], AUTHORIZED_MODEL)
        self.assertEqual(len(fm.get_log()), 1)


if __name__ == "__main__":
    unittest.main()