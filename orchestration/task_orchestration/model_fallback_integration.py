"""Model fallback integration — reuse the runtime Model Fallback Manager
for task-orchestration agent bindings (Stage 2B).

Wraps (never modifies) ``orchestration/runtime/model_fallback.py``:

* :func:`bind_task_model` — pick the best available model for the assigned
  agent and journal ``MODEL_BOUND`` to the execution ledger (§4.4 vocabulary,
  reused from Stage 2A; no new event types);
* :func:`on_task_model_error` — classify the failure via the manager, apply
  its verdict (fallback / wait / retry / intervention), journal
  ``FAILURE_CLASSIFIED`` and, when the effective model changes,
  ``MODEL_SWITCHED`` + the manager's own change log;
* :func:`recover_primary_model` — when the primary hierarchy entry is
  available again, switch back and journal the switch;
* :func:`agent_model_status` — read-only probe used by the coordination
  view (selectable model per agent; nothing is mutated).

Boundary: selection policy, hierarchies, and unavailability windows belong
to the runtime manager. This module only translates those decisions into
task-orchestration outcomes: a delegation is *ready* only when a model is
selectable, and quota/auth outcomes surface as intervention instead of
silent degradation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from orchestration.execution.ledger import Ledger
from orchestration.execution.models import Effect, EventType

from orchestration.runtime.model_fallback import (
    ErrorClass,
    FallbackStatus,
    ModelFallbackManager,
    classify_error,
)

from .models import TaskError, utc_now_stamp


class FallbackIntegrationError(TaskError):
    """Refusal in model binding for a task (fail-closed)."""


def make_manager(repo_root: Optional[Path] = None) -> Optional[ModelFallbackManager]:
    """Best-effort runtime manager construction; None if unavailable.

    Callers must degrade (no model binding) rather than fail: task
    orchestration works without runtime model data; only readiness probes
    lose fidelity.
    """
    try:
        return ModelFallbackManager(factory_root=Path(repo_root) if repo_root else None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------


def bind_task_model(
    manager: ModelFallbackManager,
    agent_id: str,
    task_id: str,
    *,
    ledger: Optional[Ledger] = None,
    execution_id: Optional[str] = None,
    actor_agent: Optional[str] = None,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Select and journal the effective model for one task's assigned agent.

    Returns ``{"bound": bool, "model": str|None, "primary": str,
    "fallback": bool, "status": FallbackStatus}``. When every hierarchy
    entry is unavailable, nothing is bound and the status is
    NEEDS_INTERVENTION — the engine must surface a blocker, not run blind.
    """
    stamp = stamp or utc_now_stamp()
    primary = manager.get_primary(agent_id)
    selected = manager.select_model(agent_id)
    result: Dict[str, Any] = {
        "bound": selected is not None,
        "agent_id": agent_id,
        "task_id": task_id,
        "model": selected,
        "primary": primary,
        "fallback": bool(selected and selected != primary),
        "status": FallbackStatus.RUNNING if selected else FallbackStatus.NEEDS_INTERVENTION,
    }
    if selected is None:
        return result
    if ledger is not None:
        ledger.append(
            EventType.MODEL_BOUND,
            actor_agent or agent_id,
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "model_binding": {
                    "provider": selected.split("/", 1)[0],
                    "model": selected,
                    "primary_model": primary,
                    "fallback_status": result["status"],
                },
            },
            effect=Effect.NONE,
            timestamp=stamp,
        )
    manager.log_change(
        agent_id=agent_id,
        task_id=task_id,
        primary=primary,
        effective=selected,
        fallback=selected if result["fallback"] else None,
        reason="initial-bind" if not result["fallback"] else "initial-fallback-bind",
        status=result["status"],
        execution_id=execution_id,
    )
    return result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def on_task_model_error(
    manager: ModelFallbackManager,
    agent_id: str,
    task_id: str,
    current_model: str,
    error_text: str,
    *,
    ledger: Optional[Ledger] = None,
    execution_id: Optional[str] = None,
    actor_agent: Optional[str] = None,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Route a model error through the fallback manager and journal it.

    Outcomes (manager-owned): ``fallback`` (switch to next hierarchy entry),
    ``wait`` (rate-limit/quota-reset), ``retry`` (transient), ``intervention``
    (auth), ``abort`` (ambiguous). ``wait`` never sleeps here: orchestration
    records the deadline intent and the caller (runner) owns real waiting.
    """
    stamp = stamp or utc_now_stamp()
    if not current_model:
        raise FallbackIntegrationError("current_model is required to route a model error")
    decision = manager.handle_error(agent_id, current_model, error_text)
    classification = decision.get("error_class", classify_error(error_text))
    if ledger is not None:
        ledger.append(
            EventType.FAILURE_CLASSIFIED,
            actor_agent or agent_id,
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "model": current_model,
                "error_class": classification,
                "action": decision.get("action"),
            },
            effect=Effect.NONE,
            timestamp=stamp,
        )
    if decision.get("action") == "fallback" and decision.get("next_model"):
        next_model = decision["next_model"]
        if ledger is not None:
            ledger.append(
                EventType.MODEL_SWITCHED,
                actor_agent or agent_id,
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "from_model": current_model,
                    "to_model": next_model,
                    "reason": classification,
                },
                effect=Effect.IDEMPOTENT,
                timestamp=stamp,
            )
        manager.log_change(
            agent_id=agent_id,
            task_id=task_id,
            primary=manager.get_primary(agent_id),
            effective=next_model,
            fallback=next_model,
            reason=classification,
            status=decision.get("status", FallbackStatus.FALLBACK_ACTIVE),
            error_message=error_text,
            execution_id=execution_id,
        )
    elif classification == ErrorClass.QUOTA_EXHAUSTED and not decision.get("next_model"):
        manager.log_change(
            agent_id=agent_id,
            task_id=task_id,
            primary=manager.get_primary(agent_id),
            effective=current_model,
            fallback=None,
            reason=classification,
            status=decision.get("status", FallbackStatus.WAITING_QUOTA_RESET),
            wait_seconds=float(decision.get("wait_seconds") or 0),
            error_message=error_text,
            execution_id=execution_id,
        )
    return {
        "agent_id": agent_id,
        "task_id": task_id,
        "effective_model": decision.get("next_model") if decision.get("action") in ("fallback", "retry", "wait") else None,
        **decision,
    }


# ---------------------------------------------------------------------------
# Recovery / readiness
# ---------------------------------------------------------------------------


def recover_primary_model(
    manager: ModelFallbackManager,
    agent_id: str,
    task_id: str,
    current_model: str,
    *,
    ledger: Optional[Ledger] = None,
    execution_id: Optional[str] = None,
    actor_agent: Optional[str] = None,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Return to the primary model if it became available; else no-op."""
    stamp = stamp or utc_now_stamp()
    primary = manager.get_primary(agent_id)
    recovered = manager.recover_primary(agent_id)
    result = {"recovered": False, "model": current_model, "primary": primary}
    if not recovered or current_model == primary:
        return result
    if ledger is not None:
        ledger.append(
            EventType.MODEL_SWITCHED,
            actor_agent or agent_id,
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "from_model": current_model,
                "to_model": primary,
                "reason": "primary-recovered",
            },
            effect=Effect.IDEMPOTENT,
            timestamp=stamp,
        )
    manager.log_change(
        agent_id=agent_id,
        task_id=task_id,
        primary=primary,
        effective=primary,
        fallback=None,
        reason="primary-recovered",
        status=FallbackStatus.RUNNING,
        execution_id=execution_id,
    )
    result.update(recovered=True, model=primary)
    return result


def agent_model_status(manager: ModelFallbackManager, agent_id: str) -> Dict[str, Any]:
    """Read-only readiness probe (used by the coordination view)."""
    selected = manager.select_model(agent_id)
    primary = manager.get_primary(agent_id)
    return {
        "selectable": selected is not None,
        "model": selected,
        "primary": primary,
        "on_fallback": bool(selected and selected != primary),
        "hierarchy_size": len(manager.get_hierarchy(agent_id)),
    }


__all__ = [
    "ErrorClass",
    "FallbackIntegrationError",
    "FallbackStatus",
    "ModelFallbackManager",
    "agent_model_status",
    "bind_task_model",
    "make_manager",
    "on_task_model_error",
    "recover_primary_model",
]
