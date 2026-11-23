"""Ordered model hierarchies per agent for fallback selection.

POLICY: BEAM_FREE_ONLY. The only authorized model is ``opencode-go/beam-free``.
There are NO fallback alternatives: on quota/rate-limit exhaustion the
manager waits for Beam Free to recover; it never switches models.
"""

# The single authorized model for every agent, session, workflow and subprocess.
AUTHORIZED_MODEL = "opencode-go/beam-free"
AUTHORIZED_MODELS = {AUTHORIZED_MODEL}

# Agent ID prefix -> ordered list of models (primary first).
# Under BEAM_FREE_ONLY every hierarchy contains exactly the authorized model.
FALLBACK_ALTERNATIVES: dict = {}

PROVIDER = "opencode-go"