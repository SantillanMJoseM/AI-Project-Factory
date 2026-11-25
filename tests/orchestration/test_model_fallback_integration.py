"""Integration tests for ModelFallbackManager with OpenCodeAdapter (mocked)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from unittest.mock import patch, MagicMock
from orchestration.runtime.opencode_adapter import OpenCodeAdapter
from orchestration.runtime.model_fallback import ModelFallbackManager, FallbackStatus
from orchestration.runtime.model_hierarchies import AUTHORIZED_MODEL


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
        self.assertEqual(result["model_effective"], AUTHORIZED_MODEL)
        log = self.fm.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["status"], FallbackStatus.COMPLETED)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_quota_returns_waiting_no_retry(self, mock_invoke, mock_val, mock_avail):
        # Quota exhausted: persist wait decision and return WAITING (no in-process retry)
        mock_invoke.return_value = {"status": "FAILED", "output": "", "error": "Free usage limit reached"}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t2")
        self.assertEqual(result["status"], "WAITING_QUOTA_RESET")
        mock_invoke.assert_called_once()
        log = self.fm.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["status"], FallbackStatus.WAITING_QUOTA_RESET)
        self.assertEqual(log[0]["effective_model"], AUTHORIZED_MODEL)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_rate_limit_returns_waiting(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.return_value = {"status": "FAILED", "output": "", "error": "rate limit Retry-After: 1"}
        result = self.adapter.invoke("ag-002-quality-gatekeeper", "test", task_id="t3")
        self.assertEqual(result["status"], "WAITING_RATE_LIMIT")
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
        mock_invoke.return_value = {"status": "FAILED", "output": "", "error": "timeout"}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t5")
        self.assertEqual(result["status"], "WAITING_TRANSIENT_RETRY")
        mock_invoke.assert_called_once()

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_all_models_unavailable(self, mock_invoke, mock_val, mock_avail):
        for m in self.fm.get_hierarchy("ag-001"):
            self.fm.mark_unavailable(m, seconds=3600)
        result = self.adapter.invoke("ag-001-project-coordinator", "test", task_id="t6")
        self.assertEqual(result["status"], "WAITING_QUOTA_RESET")
        self.assertEqual(self.fm.get_log()[0]["status"], FallbackStatus.WAITING_QUOTA_RESET)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_explicit_non_authorized_model_blocked(self, mock_invoke, mock_val, mock_avail):
        # BEAM_FREE_ONLY: a non-authorized explicit model is blocked, no fallback log
        result = self.adapter.invoke("ag-001-project-coordinator", "test", model="opencode-go/qwen3.8-flash")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(self.fm.get_log()), 0)

    @patch.object(OpenCodeAdapter, "available", return_value=True)
    @patch.object(OpenCodeAdapter, "validate_agent", return_value=True)
    @patch.object(OpenCodeAdapter, "_invoke_direct")
    def test_explicit_authorized_model_accepted(self, mock_invoke, mock_val, mock_avail):
        mock_invoke.return_value = {"status": "COMPLETED", "output": "OK", "error": None}
        result = self.adapter.invoke("ag-001-project-coordinator", "test", model="opencode-go/beam-free")
        self.assertEqual(result["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()