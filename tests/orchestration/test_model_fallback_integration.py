"""Integration tests for ModelFallbackManager with OpenCodeAdapter (mocked)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from unittest.mock import patch, MagicMock
from orchestration.runtime.opencode_adapter import OpenCodeAdapter
from orchestration.runtime.model_fallback import ModelFallbackManager, FallbackStatus


class TestAdapterFallbackIntegration(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()
        self.adapter = OpenCodeAdapter(use_sandbox=False, fallback_manager=self.fm)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_normal_execution(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.return_value = {"status": "COMPLETED", "output": "OK", "error": None}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t1")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(len(self.fm.get_log()), 1)
        self.assertEqual(self.fm.get_log()[0]["status"], FallbackStatus.COMPLETED)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_quota_fallback_to_second_model(self, mock_invoke, mock_val, mock_avail):
        # First call fails with quota, second succeeds
        mock_invoke.side_effect = [
            {"status": "FAILED", "output": "", "error": "Free usage limit reached"},
            {"status": "COMPLETED", "output": "OK", "error": None},
        ]
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t2")
        self.assertEqual(result["status"], "COMPLETED")
        log = self.fm.get_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["status"], FallbackStatus.FALLBACK_ACTIVE)
        self.assertEqual(log[1]["status"], FallbackStatus.COMPLETED)
        # Effective model should be different from primary
        self.assertNotEqual(log[1]["effective_model"], log[1]["primary_model"])

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_rate_limit_wait(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.side_effect = [
            {"status": "FAILED", "output": "", "error": "rate limit Retry-After: 1"},
            {"status": "COMPLETED", "output": "OK", "error": None},
        ]
        result = self.adapter.invoke("ag-002-quality-gatekeeper", "test", task_id="t3")
        self.assertEqual(result["status"], "COMPLETED")
        log = self.fm.get_log()
        self.assertEqual(log[0]["status"], FallbackStatus.WAITING_RATE_LIMIT)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_auth_needs_intervention(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.return_value = {"status": "FAILED", "output": "", "error": "invalid api key"}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t4")
        self.assertEqual(result["status"], "NEEDS_INTERVENTION")
        self.assertEqual(self.fm.get_log()[0]["status"], FallbackStatus.NEEDS_INTERVENTION)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_transient_retry(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.side_effect = [
            {"status": "FAILED", "output": "", "error": "timeout"},
            {"status": "COMPLETED", "output": "OK", "error": None},
        ]
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t5")
        self.assertEqual(result["status"], "COMPLETED")

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_all_models_unavailable(self, mock_invoke, mock_val, mock_avail):
        # Mark all models unavailable
        for m in self.fm.get_hierarchy("ag-001"):
            self.fm.mark_unavailable(m, seconds=3600)
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t6")
        self.assertEqual(result["status"], "WAITING_QUOTA_RESET")
        self.assertEqual(self.fm.get_log()[0]["status"], FallbackStatus.WAITING_QUOTA_RESET)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_explicit_model_bypasses_fallback(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.return_value = {"status": "COMPLETED", "output": "OK", "error": None}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", model="opencode-go/qwen3.8-flash")
        self.assertEqual(result["status"], "COMPLETED")
        # No fallback log because explicit model bypasses manager
        self.assertEqual(len(self.fm.get_log()), 0)


if __name__ == "__main__":
    unittest.main()
