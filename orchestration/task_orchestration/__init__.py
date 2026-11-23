"""Task Orchestration (Stage 2B) — goal analysis, dependency planning,
delegation with independent verification, coordination read model, and
integrations with the execution continuity plane (Stage 2A) and the runtime
Model Fallback Manager.

Modules
-------
``models``                   Task Contract data layer: states, guarded
                             transitions, ``TaskGraph`` (cycles, waves,
                             topological order), plans, delegation records.
``engine``                   ``TaskOrchestrationEngine``: analyze → decompose
                             → validated plan; capability → agent, skills
                             binding; workspace persistence (file plane).
``delegation``               ``DelegationManager``: parent→child delegation
                             lifecycle; fail-closed ``verify_completion``.
``coordination``             ``AgentCoordinationManager``: consolidated
                             point-in-time ``CoordinationState`` (read model).
``context_integration``      Bridges to Stage 2A: ledger journalling, DCM
                             context assembly, checkpoints, resume views.
``model_fallback_integration`` Binds task agents to runtime-selected models
                             (fallback/wait/retry/recovery; readiness probe).
``cli``                      JSON command interface
                             (``python -m orchestration.task_orchestration.cli``).

Design posture: fail-closed and stdlib-only. This package plans, assigns,
verifies, and reports; it authorizes nothing and mutates only the repository
file plane under ``projects/<ID>/orchestration/task-orchestration/``.
"""

from __future__ import annotations

from .models import (  # noqa: F401  (re-export surface)
    ACCEPTED_GATE_VERDICTS,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    AcceptanceCriterion,
    CoordinationState,
    CycleError,
    DelegationRecord,
    DelegationStatus,
    GateVerdict,
    GoalAnalysis,
    KNOWN_AGENTS,
    OrchestrationPlan,
    PASSING_GATE_VERDICTS,
    Priority,
    QualityGateResult,
    StatusHistoryEntry,
    Task,
    TaskError,
    TaskGraph,
    TaskState,
    VerificationReport,
    can_transition,
    transition_task,
    utc_now_stamp,
)
from .engine import (
    CAPABILITY_AGENTS,
    CAPABILITY_DEFAULTS,
    IMPLEMENTATION_CAPABILITIES,
    PlanningError,
    TaskOrchestrationEngine,
    TaskSpec,
    delegations_file_path,
    load_plan,
    next_plan_id,
    plan_file_path,
    save_plan,
    task_orchestration_dir,
)
from .delegation import DelegationError, DelegationManager, TRACKABLE_STATES
from .coordination import BLOCKER_STATES, IN_FLIGHT_STATES, AgentCoordinationManager
from .context_integration import (
    ContextIntegrationError,
    GOVERNED_TASK_REF,
    assemble_task_context,
    checkpoint_integrity,
    checkpoint_plan,
    delegations_rel_path,
    journal_delegation_change,
    journal_plan_published,
    journal_task_change,
    plan_rel_path,
    publish_workspace,
    restore_workspace,
    resume_view,
)
from .model_fallback_integration import (
    ErrorClass,
    FallbackIntegrationError,
    FallbackStatus,
    ModelFallbackManager,
    agent_model_status,
    bind_task_model,
    make_manager,
    on_task_model_error,
    recover_primary_model,
)

__all__ = [
    # models
    "ACCEPTED_GATE_VERDICTS",
    "ALLOWED_TRANSITIONS",
    "AcceptanceCriterion",
    "BLOCKER_STATES",
    "CoordinationState",
    "CycleError",
    "DelegationRecord",
    "DelegationStatus",
    "GateVerdict",
    "GoalAnalysis",
    "IN_FLIGHT_STATES",
    "KNOWN_AGENTS",
    "OrchestrationPlan",
    "PASSING_GATE_VERDICTS",
    "Priority",
    "QualityGateResult",
    "StatusHistoryEntry",
    "TERMINAL_STATES",
    "Task",
    "TaskError",
    "TaskGraph",
    "TaskOrchestrationEngine",
    "TaskSpec",
    "TaskState",
    "TRACKABLE_STATES",
    "VerificationReport",
    "can_transition",
    "transition_task",
    "utc_now_stamp",
    # engine / persistence
    "CAPABILITY_AGENTS",
    "CAPABILITY_DEFAULTS",
    "IMPLEMENTATION_CAPABILITIES",
    "PlanningError",
    "delegations_file_path",
    "load_plan",
    "next_plan_id",
    "plan_file_path",
    "save_plan",
    "task_orchestration_dir",
    # delegation
    "DelegationError",
    "DelegationManager",
    # coordination
    "AgentCoordinationManager",
    # context integration (Stage 2A bridge)
    "ContextIntegrationError",
    "GOVERNED_TASK_REF",
    "assemble_task_context",
    "checkpoint_integrity",
    "checkpoint_plan",
    "delegations_rel_path",
    "journal_delegation_change",
    "journal_plan_published",
    "journal_task_change",
    "plan_rel_path",
    "publish_workspace",
    "restore_workspace",
    "resume_view",
    # model fallback integration (runtime bridge)
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
