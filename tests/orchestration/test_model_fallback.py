"""Unit tests for ModelFallbackManager."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from unittest.mock import patch
from orchestration.runtime.model_fallback import (
    ModelFallbackManager, classify_error, extract_retry_after,
    ErrorClass, FallbackStatus,
)


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
        self.assertEqual(classify_error("503 Service Unavailable"), ErrorClass.TRANSIENT)
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
            self.assertTrue(h[0].startswith("opencode-go/"), f"{aid} primary not opencode-go")

    def test_primary_matches_frontmatter(self):
        # AG-001 should be qwen4-max
        self.assertEqual(self.fm.get_primary("ag-001"), "opencode-go/qwen4-max")
        # AG-002 should be qwen3.8-flash
        self.assertEqual(self.fm.get_primary("ag-002"), "opencode-go/qwen3.8-flash")
        # AG-008 should be kimi-k2.7-code
        self.assertEqual(self.fm.get_primary("ag-008"), "opencode-go/kimi-k2.7-code")

    def test_no_duplicate_models(self):
        for i in range(1, 19):
            aid = f"ag-{i:03d}"
            h = self.fm.get_hierarchy(aid)
            self.assertEqual(len(h), len(set(h)), f"{aid} has duplicate models")


class TestFallbackSelection(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_select_primary_when_available(self):
        model = self.fm.select_model("ag-001")
        self.assertEqual(model, "opencode-go/qwen4-max")

    def test_fallback_when_primary_unavailable(self):
        self.fm.mark_unavailable("opencode-go/qwen4-max", seconds=3600)
        model = self.fm.select_model("ag-001")
        self.assertNotEqual(model, "opencode-go/qwen4-max")
        self.assertIsNotNone(model)

    def test_all_unavailable_returns_none(self):
        for m in self.fm.get_hierarchy("ag-001"):
            self.fm.mark_unavailable(m, seconds=3600)
        self.assertIsNone(self.fm.select_model("ag-001"))

    def test_recovery(self):
        self.fm.mark_unavailable("opencode-go/qwen4-max", seconds=0.1)
        import time
        time.sleep(0.2)
        self.assertTrue(self.fm.recover_primary("ag-001"))


class TestHandleError(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_quota_fallback(self):
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "quota exhausted")
        self.assertEqual(d["error_class"], ErrorClass.QUOTA_EXHAUSTED)
        self.assertEqual(d["action"], "fallback")
        self.assertIsNotNone(d["next_model"])
        self.assertEqual(d["status"], FallbackStatus.FALLBACK_ACTIVE)

    def test_rate_limit_wait(self):
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "rate limit Retry-After: 30")
        self.assertEqual(d["error_class"], ErrorClass.RATE_LIMIT)
        self.assertEqual(d["action"], "wait")
        self.assertEqual(d["wait_seconds"], 30.0)
        self.assertEqual(d["status"], FallbackStatus.WAITING_RATE_LIMIT)

    def test_transient_retry(self):
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "timeout")
        self.assertEqual(d["error_class"], ErrorClass.TRANSIENT)
        self.assertEqual(d["action"], "retry")

    def test_auth_intervention(self):
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "invalid api key")
        self.assertEqual(d["error_class"], ErrorClass.AUTH)
        self.assertEqual(d["action"], "intervention")
        self.assertEqual(d["status"], FallbackStatus.NEEDS_INTERVENTION)

    def test_ambiguous_abort(self):
        d = self.fm.handle_error("ag-001", "opencode-go/qwen4-max", "unknown error xyz")
        self.assertEqual(d["error_class"], ErrorClass.AMBIGUOUS)
        self.assertEqual(d["action"], "abort")


class TestLogging(unittest.TestCase):
    def test_log_change(self):
        fm = ModelFallbackManager()
        entry = fm.log_change("ag-001", "task-1", "opencode-go/qwen4-max",
                              "opencode-go/qwen3.8-max", "opencode-go/qwen3.8-max",
                              "quota_exhausted", FallbackStatus.FALLBACK_ACTIVE)
        self.assertEqual(entry["agent_id"], "ag-001")
        self.assertEqual(entry["provider"], "opencode-go")
        self.assertEqual(len(fm.get_log()), 1)


if __name__ == "__main__":
    unittest.main()
