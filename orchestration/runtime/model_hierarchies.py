"""Ordered model hierarchies per agent for fallback selection.

Supports two policies via env var APF_MODEL_POLICY:
- BEAM_FREE_ONLY (default): only opencode-go/beam-free is authorized.
- MODEL_ROUTING_V2: multi-model routing (see model_routing.py).

Rollback: set APF_MODEL_POLICY=BEAM_FREE_ONLY.
"""

import os

PROVIDER = "opencode-go"

# Policy-aware: delegate to model_routing dynamically.
def _is_v2():
    try:
        from orchestration.runtime.model_routing import is_model_routing_v2
        return is_model_routing_v2()
    except ImportError:
        return False

if _is_v2():
    from orchestration.runtime.model_routing import (
        AUTHORIZED_MODELS_V2 as AUTHORIZED_MODELS,
        FALLBACK_HIERARCHIES_V2 as _HIERARCHIES,
        AGENT_MODEL_ASSIGNMENT,
    )
    AUTHORIZED_MODEL = "opencode-go/beam-free"
    FALLBACK_ALTERNATIVES = {}
else:
    AUTHORIZED_MODEL = "opencode-go/beam-free"
    AUTHORIZED_MODELS = {AUTHORIZED_MODEL}
    _HIERARCHIES = {}
    FALLBACK_ALTERNATIVES = {}