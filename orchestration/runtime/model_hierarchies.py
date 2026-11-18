"""Ordered model hierarchies per agent for fallback selection.

All models belong to opencode-go (OpenCode Go subscription).
Primary model is read from agent front-matter; alternatives are defined here.
"""

# Agent ID prefix -> ordered list of models (primary first).
# Primary is taken from .opencode/agents/ag-XXX-*.md front-matter at runtime.
# Alternatives below are the fallback order after the primary.
FALLBACK_ALTERNATIVES = {
    "ag-001": ["opencode-go/qwen3.8-max", "opencode-go/kimi-k3.1-pro", "opencode-go/glm-5.3"],
    "ag-002": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-003": ["opencode-go/qwen3.8-max", "opencode-go/kimi-k3.1-pro", "opencode-go/glm-5.3"],
    "ag-004": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-005": ["opencode-go/qwen3.8-max", "opencode-go/kimi-k3.1-pro", "opencode-go/glm-5.3"],
    "ag-006": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-007": ["opencode-go/kimi-k3.1-pro", "opencode-go/qwen3.8-max", "opencode-go/glm-5.3"],
    "ag-008": ["opencode-go/kimi-k3.1-pro", "opencode-go/qwen3.8-max", "opencode-go/glm-5.3"],
    "ag-009": ["opencode-go/kimi-k3.1-pro", "opencode-go/qwen3.8-max", "opencode-go/glm-5.3"],
    "ag-010": ["opencode-go/kimi-k3.1-pro", "opencode-go/qwen3.8-max", "opencode-go/glm-5.3"],
    "ag-011": ["opencode-go/kimi-k3.1-pro", "opencode-go/qwen3.8-max", "opencode-go/glm-5.3"],
    "ag-012": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-013": ["opencode-go/qwen3.8-max", "opencode-go/kimi-k3.1-pro", "opencode-go/glm-5.3"],
    "ag-014": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-015": ["opencode-go/qwen3.8-max", "opencode-go/kimi-k3.1-pro", "opencode-go/glm-5.3"],
    "ag-016": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-017": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
    "ag-018": ["opencode-go/qwen3.8-max", "opencode-go/glm-5.3-flash", "opencode-go/mimo-v2.6-flash"],
}

PROVIDER = "opencode-go"
