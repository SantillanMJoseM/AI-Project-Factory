"""Tests for MODEL_ROUTING_V2 policy (opt-in via APF_MODEL_POLICY)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["APF_MODEL_POLICY"] = "MODEL_ROUTING_V2"

from orchestration.runtime.model_routing import (
    AGENT_MODEL_ASSIGNMENT,
    ACTIVE_PROFILE_MODELS,
    AUTHORIZED_MODELS_V2,
    FALLBACK_HIERARCHIES_V2,
    MODEL_PRICING,
    authorized_models,
    fallback_hierarchy,
    get_policy,
    is_authorized,
    is_model_routing_v2,
    model_tier,
    primary_model,
)
from orchestration.runtime.model_fallback import ModelFallbackManager


class TestRoutingPolicy(unittest.TestCase):
    def test_policy_active(self):
        self.assertTrue(is_model_routing_v2())
        self.assertEqual(get_policy(), "MODEL_ROUTING_V2")

    def test_authorized_models_count(self):
        self.assertGreaterEqual(len(authorized_models()), 30)

    def test_beam_free_in_authorized(self):
        self.assertTrue(is_authorized("opencode-go/beam-free"))

    def test_non_authorized_rejected(self):
        self.assertFalse(is_authorized("opencode-go/nonexistent-model"))

    def test_ag001_primary(self):
        self.assertEqual(primary_model("ag-001"), "opencode-go/glm-5.3-flash")

    def test_ag002_primary(self):
        self.assertEqual(primary_model("ag-002"), "opencode-go/deepseek-v4.1-flash")

    def test_ag005_primary(self):
        self.assertEqual(primary_model("ag-005"), "opencode-go/kimi-k2.7-code")

    def test_ag008_primary(self):
        self.assertEqual(primary_model("ag-008"), "opencode-go/kimi-k2.7-code")

    def test_fallback_hierarchy_ends_with_beam_free(self):
        for aid in ["ag-001", "ag-002", "ag-005", "ag-008", "ag-018"]:
            h = fallback_hierarchy(aid)
            self.assertTrue(len(h) >= 1)
            self.assertEqual(h[-1], "opencode-go/beam-free")

    def test_all_agents_have_assignment(self):
        for i in range(1, 19):
            aid = f"ag-{i:03d}"
            self.assertIn(aid, AGENT_MODEL_ASSIGNMENT, f"{aid} missing assignment")

    def test_model_tier_classification(self):
        self.assertEqual(model_tier("opencode-go/beam-free"), "free")
        self.assertEqual(model_tier("opencode-go/glm-5.3-flash"), "economy")
        self.assertEqual(model_tier("opencode-go/kimi-k2.7-code"), "premium")

    def test_pricing_available(self):
        self.assertIn("opencode-go/kimi-k2.7-code", MODEL_PRICING)
        self.assertEqual(MODEL_PRICING["opencode-go/kimi-k2.7-code"]["input"], 0.95)
        self.assertEqual(MODEL_PRICING["opencode-go/kimi-k2.7-code"]["output"], 4.0)

    def test_active_profile_size(self):
        self.assertEqual(len(ACTIVE_PROFILE_MODELS), 6)


class TestRoutingManager(unittest.TestCase):
    def setUp(self):
        self.fm = ModelFallbackManager()

    def test_ag001_primary_v2(self):
        self.assertEqual(self.fm.get_primary("ag-001"), "opencode-go/glm-5.3-flash")

    def test_ag002_primary_v2(self):
        self.assertEqual(self.fm.get_primary("ag-002"), "opencode-go/deepseek-v4.1-flash")

    def test_ag005_hierarchy_v2(self):
        h = self.fm.get_hierarchy("ag-005")
        self.assertEqual(h[0], "opencode-go/kimi-k2.7-code")
        self.assertEqual(h[-1], "opencode-go/beam-free")

    def test_authorized_check_v2(self):
        self.assertTrue(self.fm.is_authorized("opencode-go/kimi-k2.7-code"))
        self.assertTrue(self.fm.is_authorized("opencode-go/beam-free"))
        self.assertFalse(self.fm.is_authorized("opencode-go/nonexistent"))

    def test_select_model_v2(self):
        model = self.fm.select_model("ag-005")
        self.assertEqual(model, "opencode-go/kimi-k2.7-code")

    def test_fallback_hierarchy_v2(self):
        h = self.fm.get_hierarchy("ag-008")
        self.assertIn("opencode-go/beam-free", h)
        self.assertGreater(len(h), 1)


if __name__ == "__main__":
    unittest.main()