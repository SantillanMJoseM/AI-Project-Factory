"""Model routing policy for AI-Project-Factory.

Supports two policies:
- BEAM_FREE_ONLY (default, legacy): only opencode-go/beam-free is authorized.
- MODEL_ROUTING_V2: multi-model routing based on task complexity and agent role.

Policy selection via env var APF_MODEL_POLICY (default: BEAM_FREE_ONLY).
Rollback: set APF_MODEL_POLICY=BEAM_FREE_ONLY to restore single-model behavior.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

BEAM_FREE_ONLY = "BEAM_FREE_ONLY"
MODEL_ROUTING_V2 = "MODEL_ROUTING_V2"

DEFAULT_POLICY = BEAM_FREE_ONLY

# ---------------------------------------------------------------------------
# Authorized models (MODEL_ROUTING_V2)
# ---------------------------------------------------------------------------

# Chat models available in Go Plus (from /inference/go/v1/models, 2026-11-25).
# Excludes embedding/decision models (not suitable for agent tasks).
AUTHORIZED_MODELS_V2: set[str] = {
    # Free (baseline / reserve)
    "opencode-go/beam-free",
    "opencode-go/hungerg-free",
    "opencode-go/hy4-flash-free",
    "opencode-go/iceman-contributor-free",
    "opencode-go/muse-spark-1.2-contributor",
    "opencode-go/muse-spark-1.3-contributor",
    # Economy (Flash)
    "opencode-go/qwen3.8-flash",
    "opencode-go/mimo-v2.6-flash",
    "opencode-go/minimax-m3.1-flash",
    "opencode-go/glm-5.3-flash",
    "opencode-go/deepseek-v4.1-flash",
    "opencode-go/gpt-6-luna",
    "opencode-go/claude-haiku-5-5",
    "opencode-go/hy3",
    # Standard
    "opencode-go/qwen3.7-plus",
    "opencode-go/deepseek-v4-pro",
    "opencode-go/mimo-v2.5",
    "opencode-go/mimo-v2.6-pro",
    "opencode-go/minimax-m3",
    "opencode-go/hy4",
    "opencode-go/longcat-2.5",
    "opencode-go/qwen3.8-max",
    "opencode-go/qwen4-max",
    "opencode-go/gpt-5.6-luna",
    "opencode-go/gemini-4-argon",
    "opencode-go/hy4-preview",
    "opencode-go/mimo-v2.5-pro",
    "opencode-go/step-5-preview",
    # Premium
    "opencode-go/kimi-k2.7-code",
    "opencode-go/kimi-k3",
    "opencode-go/kimi-k3.1-pro",
    "opencode-go/glm-5.3",
    "opencode-go/grok-4.7",
}

# Pricing (USD per million tokens) from /inference/go/v1/models (2026-11-25)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "opencode-go/beam-free": {"input": 0.0, "output": 0.0},
    "opencode-go/hungerg-free": {"input": 0.0, "output": 0.0},
    "opencode-go/hy4-flash-free": {"input": 0.0, "output": 0.0},
    "opencode-go/iceman-contributor-free": {"input": 0.0, "output": 0.0},
    "opencode-go/muse-spark-1.2-contributor": {"input": 0.1, "output": 0.2},
    "opencode-go/muse-spark-1.3-contributor": {"input": 0.1, "output": 0.2},
    "opencode-go/qwen3.8-flash": {"input": 0.15, "output": 0.47},
    "opencode-go/mimo-v2.6-flash": {"input": 0.14, "output": 0.28},
    "opencode-go/minimax-m3.1-flash": {"input": 0.15, "output": 0.6},
    "opencode-go/glm-5.3-flash": {"input": 0.15, "output": 0.5},
    "opencode-go/deepseek-v4.1-flash": {"input": 0.15, "output": 0.6},
    "opencode-go/gpt-6-luna": {"input": 0.1, "output": 0.5},
    "opencode-go/claude-haiku-5-5": {"input": 0.1, "output": 0.5},
    "opencode-go/hy3": {"input": 0.14, "output": 0.58},
    "opencode-go/qwen3.7-plus": {"input": 0.4, "output": 1.6},
    "opencode-go/deepseek-v4-pro": {"input": 0.66, "output": 1.98},
    "opencode-go/mimo-v2.5": {"input": 0.0, "output": 0.0},
    "opencode-go/mimo-v2.6-pro": {"input": 0.435, "output": 0.87},
    "opencode-go/minimax-m3": {"input": 0.3, "output": 1.2},
    "opencode-go/hy4": {"input": 0.834, "output": 2.501},
    "opencode-go/longcat-2.5": {"input": 0.3, "output": 1.2},
    "opencode-go/qwen3.8-max": {"input": 2.0, "output": 6.0},
    "opencode-go/qwen4-max": {"input": 1.5, "output": 4.5},
    "opencode-go/gpt-5.6-luna": {"input": 0.2, "output": 1.2},
    "opencode-go/gemini-4-argon": {"input": 2.0, "output": 10.0},
    "opencode-go/hy4-preview": {"input": 0.834, "output": 2.501},
    "opencode-go/mimo-v2.5-pro": {"input": 0.0, "output": 0.0},
    "opencode-go/step-5-preview": {"input": 1.0, "output": 2.7},
    "opencode-go/kimi-k2.7-code": {"input": 0.95, "output": 4.0},
    "opencode-go/kimi-k3": {"input": 3.0, "output": 15.0},
    "opencode-go/kimi-k3.1-pro": {"input": 2.0, "output": 10.0},
    "opencode-go/glm-5.3": {"input": 1.4, "output": 4.4},
    "opencode-go/grok-4.7": {"input": 2.0, "output": 6.0},
}

# ---------------------------------------------------------------------------
# Agent-to-model assignment (MODEL_ROUTING_V2)
# ---------------------------------------------------------------------------

AGENT_MODEL_ASSIGNMENT: Dict[str, str] = {
    "ag-001": "opencode-go/glm-5.3-flash",
    "ag-002": "opencode-go/deepseek-v4.1-flash",
    "ag-003": "opencode-go/glm-5.3",
    "ag-004": "opencode-go/qwen3.8-flash",
    "ag-005": "opencode-go/kimi-k2.7-code",
    "ag-006": "opencode-go/qwen3.8-flash",
    "ag-007": "opencode-go/deepseek-v4.1-flash",
    "ag-008": "opencode-go/kimi-k2.7-code",
    "ag-009": "opencode-go/kimi-k2.7-code",
    "ag-010": "opencode-go/deepseek-v4.1-flash",
    "ag-011": "opencode-go/deepseek-v4.1-flash",
    "ag-012": "opencode-go/qwen3.8-flash",
    "ag-013": "opencode-go/glm-5.3-flash",
    "ag-014": "opencode-go/deepseek-v4.1-flash",
    "ag-015": "opencode-go/glm-5.3",
    "ag-016": "opencode-go/qwen3.8-flash",
    "ag-017": "opencode-go/beam-free",
    "ag-018": "opencode-go/qwen3.8-flash",
}

# Specialization: AG-003 assessor uses same as manager
AGENT_MODEL_ASSIGNMENT["ag-003-security-risk-assessor"] = "opencode-go/glm-5.3"

# ---------------------------------------------------------------------------
# Operational profile (4 categories)
# ---------------------------------------------------------------------------

# DISCOVERED: all models found in the Go catalog (37 as of 2026-11-25)
DISCOVERED_MODELS: set[str] = AUTHORIZED_MODELS_V2 | {
    "opencode-go/jev-1.14",
    "opencode-go/gemini-decision-1",
    "opencode-go/gpt-6-luna-decision",
    "opencode-go/text-embedding-3-small",
    "opencode-go/qwen3-embedding-8b",
    "opencode-go/gemini-embedding-2",
}

# AUTHORIZED: permitted by policy (all discovered chat models)
AUTHORIZED_MODELS_V2 = AUTHORIZED_MODELS_V2

# ACTIVE_PROFILE: enabled in the current operational profile (6 models)
ACTIVE_PROFILE_MODELS: set[str] = {
    "opencode-go/glm-5.3-flash",      # coordination, docs, aux
    "opencode-go/kimi-k2.7-code",     # development
    "opencode-go/deepseek-v4.1-flash",# QA, analysis
    "opencode-go/glm-5.3",            # architecture, security
    "opencode-go/qwen3.8-flash",      # economy tasks
    "opencode-go/beam-free",          # free reserve
}

# RESERVE: available but not in active profile (contingency)
RESERVE_MODELS: set[str] = AUTHORIZED_MODELS_V2 - ACTIVE_PROFILE_MODELS


def model_tier(model: str) -> str:
    """Return the operational tier of a model."""
    if model in ("opencode-go/beam-free", "opencode-go/hungerg-free",
                 "opencode-go/hy4-flash-free", "opencode-go/iceman-contributor-free",
                 "opencode-go/muse-spark-1.2-contributor", "opencode-go/muse-spark-1.3-contributor"):
        return "free"
    if model in ("opencode-go/glm-5.3-flash", "opencode-go/qwen3.8-flash",
                 "opencode-go/mimo-v2.6-flash", "opencode-go/minimax-m3.1-flash",
                 "opencode-go/deepseek-v4.1-flash", "opencode-go/gpt-6-luna",
                 "opencode-go/claude-haiku-5-5", "opencode-go/hy3"):
        return "economy"
    if model in ("opencode-go/glm-5.3", "opencode-go/kimi-k2.7-code",
                 "opencode-go/deepseek-v4-pro", "opencode-go/qwen3.8-max",
                 "opencode-go/qwen4-max", "opencode-go/gpt-5.6-luna",
                 "opencode-go/gemini-4-argon", "opencode-go/grok-4.7",
                 "opencode-go/kimi-k3", "opencode-go/kimi-k3.1-pro",
                 "opencode-go/mimo-v2.6-pro", "opencode-go/minimax-m3",
                 "opencode-go/hy4", "opencode-go/hy4-preview",
                 "opencode-go/mimo-v2.5-pro", "opencode-go/step-5-preview",
                 "opencode-go/mimo-v2.5", "opencode-go/qwen3.7-plus",
                 "opencode-go/longcat-2.5"):
        return "premium"
    return "unknown"


# ---------------------------------------------------------------------------
# Fallback hierarchies (MODEL_ROUTING_V2)
# ---------------------------------------------------------------------------

# Ordered list of models to try (primary first, then alternatives by tier).
# Under BEAM_FREE_ONLY this is always [beam-free].
FALLBACK_HIERARCHIES_V2: Dict[str, List[str]] = {
    "ag-001": ["opencode-go/glm-5.3-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-002": ["opencode-go/deepseek-v4.1-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-003": ["opencode-go/glm-5.3", "opencode-go/glm-5.3-flash", "opencode-go/beam-free"],
    "ag-004": ["opencode-go/qwen3.8-flash", "opencode-go/qwen3.7-plus", "opencode-go/beam-free"],
    "ag-005": ["opencode-go/kimi-k2.7-code", "opencode-go/glm-5.3", "opencode-go/beam-free"],
    "ag-006": ["opencode-go/qwen3.8-flash", "opencode-go/qwen3.7-plus", "opencode-go/beam-free"],
    "ag-007": ["opencode-go/deepseek-v4.1-flash", "opencode-go/deepseek-v4-pro", "opencode-go/beam-free"],
    "ag-008": ["opencode-go/kimi-k2.7-code", "opencode-go/deepseek-v4.1-flash", "opencode-go/beam-free"],
    "ag-009": ["opencode-go/kimi-k2.7-code", "opencode-go/deepseek-v4.1-flash", "opencode-go/beam-free"],
    "ag-010": ["opencode-go/deepseek-v4.1-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-011": ["opencode-go/deepseek-v4.1-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-012": ["opencode-go/qwen3.8-flash", "opencode-go/qwen3.7-plus", "opencode-go/beam-free"],
    "ag-013": ["opencode-go/glm-5.3-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-014": ["opencode-go/deepseek-v4.1-flash", "opencode-go/qwen3.8-flash", "opencode-go/beam-free"],
    "ag-015": ["opencode-go/glm-5.3", "opencode-go/glm-5.3-flash", "opencode-go/beam-free"],
    "ag-016": ["opencode-go/qwen3.8-flash", "opencode-go/qwen3.7-plus", "opencode-go/beam-free"],
    "ag-017": ["opencode-go/beam-free"],
    "ag-018": ["opencode-go/qwen3.8-flash", "opencode-go/qwen3.7-plus", "opencode-go/beam-free"],
}


def get_policy() -> str:
    """Return the active model policy from env (default BEAM_FREE_ONLY).

    MODEL_ROUTING_V2 is enabled by setting APF_MODEL_POLICY=MODEL_ROUTING_V2.
    Rollback: set APF_MODEL_POLICY=BEAM_FREE_ONLY (or unset).
    """
    return os.environ.get("APF_MODEL_POLICY", DEFAULT_POLICY)


def is_model_routing_v2() -> bool:
    return get_policy() == MODEL_ROUTING_V2


def authorized_models() -> set[str]:
    if is_model_routing_v2():
        return AUTHORIZED_MODELS_V2
    return {"opencode-go/beam-free"}


def primary_model(agent_id: str) -> str:
    short = agent_id.lower().split("-")[0] + "-" + agent_id.lower().split("-")[1] if "-" in agent_id else agent_id.lower()
    # Normalize ag-003-specialization to ag-003
    aid = agent_id.lower()[:6] if agent_id.lower().startswith("ag-") else agent_id.lower()
    if is_model_routing_v2():
        return AGENT_MODEL_ASSIGNMENT.get(aid, "opencode-go/beam-free")
    return "opencode-go/beam-free"


def fallback_hierarchy(agent_id: str) -> List[str]:
    aid = agent_id.lower()[:6] if agent_id.lower().startswith("ag-") else agent_id.lower()
    if is_model_routing_v2():
        return list(FALLBACK_HIERARCHIES_V2.get(aid, ["opencode-go/beam-free"]))
    return ["opencode-go/beam-free"]


def is_authorized(model: str) -> bool:
    return model in authorized_models()