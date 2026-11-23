"""Task Orchestration Engine — goal analysis, decomposition, dependency
planning, and agent/skill selection (Stage 2B).

Responsibilities (mirroring the AG-001 coordinator role in ``agents/``):

* ``analyze_goal``     - classify a goal statement into required capabilities
  (keyword-driven, deterministic, no LLM call);
* ``decompose``        - project the capabilities onto a standard
  factory pipeline (coordination → analysis → architecture → design →
  implementation fan-out → QA → review → delivery), as ``TaskSpec`` rows;
* ``build_plan``       - materialize specs into a validated ``TaskGraph``
  (TASK-NNNN ids, catalog agents assigned, dependencies cycle-checked),
  bind skills, and compute parallel/sequential groupings;
* ``select_agent``     - capability → AG-NNN from the 18-agent catalog;
* ``select_skills``    - agent + category → ACTIVE skills in the governed
  registry (``orchestration/skills/registry.json``); a missing/corrupt
  registry yields no skills (degradable, never fatal — selection is
  advisory, execution authorization stays with the governance plane).

Parallel/sequential semantics: ``TaskGraph.waves()`` gives maximal groups of
mutually independent tasks (may run in parallel); ``topological_order()``
gives one deterministic sequential execution order; the two are consistent
by construction (each wave is a prefix layer of the order).

Boundary: the engine plans and assigns. It starts nothing, approves nothing,
and modifies no agent/runtime/config files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .models import (
    GoalAnalysis,
    OrchestrationPlan,
    Priority,
    Task,
    TaskError,
    TaskGraph,
    utc_now_stamp,
    AcceptanceCriterion,
    QualityGateResult,
    GateVerdict,
    TaskState,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Capability → catalog agent. Keys are the stable vocabulary this engine
#: plans against; values are the 18-agent catalog in ``agents/``.
CAPABILITY_AGENTS: Dict[str, str] = {
    "coordination": "AG-001",
    "quality-governance": "AG-002",
    "security-risk": "AG-003",
    "business-analysis": "AG-004",
    "architecture": "AG-005",
    "ux-design": "AG-006",
    "database-design": "AG-007",
    "backend": "AG-008",
    "frontend": "AG-009",
    "database": "AG-010",
    "integration": "AG-011",
    "qa-testing": "AG-012",
    "code-review": "AG-013",
    "performance": "AG-014",
    "security-audit": "AG-015",
    "devops": "AG-016",
    "deployment": "AG-017",
    "documentation": "AG-018",
    "general": "AG-008",
}

#: Keyword fragments → capability (substring match on the lowercased goal).
#: Ordering matters only for the capability list; detection is a set union.
CAPABILITY_KEYWORDS: List[Tuple[str, Tuple[str, ...]]] = [
    ("business-analysis", ("requirement", "analyze", "analysis", "specification", "backlog", "user story")),
    ("architecture", ("architecture", "design the", "system design", "service", "microservice", "api design")),
    ("ux-design", ("ux", "ui ", "interface", "screen", "dashboard", "layout", "user experience")),
    ("database-design", ("data model", "database design", "schema design", "er model")),
    ("backend", ("backend", "orchestration", "engine", "business logic", "service layer", "rest", "endpoint")),
    ("frontend", ("frontend", "web app", "client", "react", "viewport", "web page")),
    ("database", ("database", "sql", "migration", "persist", "repository store", "data layer")),
    ("integration", ("integration", "integrate", "pipeline", "wire", "glue", "e2e flow")),
    ("performance", ("performance", "latency", "throughput", "load test", "benchmark", "optimize")),
    ("security-audit", ("security", "vulnerabilit", "threat", "penetration", "audit")),
    ("security-risk", ("risk", "compliance", "policy")),
    ("devops", ("deploy", "ci/cd", "ci pipeline", "infrastructure", "monitoring", "container", "kubernetes")),
    ("deployment", ("release", "production", "rollout", "promotion")),
    ("documentation", ("documentation", "docs", "adr", "guide", "changelog", "readme")),
]

#: Risk hint → surfaced risk note for the analysis record.
RISK_HINTS: List[Tuple[str, str]] = [
    ("production", "touches production: LEVEL C human approval required for deploy"),
    ("security", "security-sensitive: independent audit required (auditor != developer)"),
    ("migration", "data migration: backup + verified rollback required"),
    ("credentials", "credentials handling: no real secrets in repository"),
]

IMPLEMENTATION_CAPABILITIES = ("backend", "frontend", "database", "integration")

#: Default acceptance criteria and quality gates per capability.
CAPABILITY_DEFAULTS: Dict[str, Tuple[List[str], List[str]]] = {
    "coordination": (["Plan is complete and consistent", "Dependencies and waves are cycle-free"], []),
    "business-analysis": (["Requirements are enumerated and testable"], []),
    "quality-governance": (["Gate verdicts recorded for every deliverable"], []),
    "architecture": (["Architecture decisions are documented"], ["QG-ARCH"]),
    "security-risk": (["Threats are identified and mapped to controls"], []),
    "ux-design": (["Interaction flows cover every requirement"], []),
    "database-design": (["Schema covers every entity in the requirements"], ["QG-SCHEMA"]),
    "backend": (["Module implements the contract", "Unit tests pass"], ["QG-CODE", "QG-TEST"]),
    "frontend": (["UI implements the approved design", "Build passes"], ["QG-CODE"]),
    "database": (["Migrations apply and roll back cleanly"], ["QG-TEST"]),
    "integration": (["End-to-end flow passes against real modules"], ["QG-TEST"]),
    "qa-testing": (["Regression suite passes", "Every acceptance criterion has a test"], ["QG-TEST"]),
    "code-review": (["Review findings are resolved or waived with evidence"], ["QG-REVIEW"]),
    "performance": (["Measured targets met or deviations documented"], []),
    "security-audit": (["Audit report issued with no unresolved HIGH findings"], ["QG-SECURITY"]),
    "devops": (["Pipeline stages pass in staging"], []),
    "deployment": (["Deployment runbook followed", "Rollback path verified"], ["QG-DEPLOY"]),
    "documentation": (["Docs match delivered behavior"], []),
    "general": (["Deliverable satisfies its stated objective"], ["QG-CODE"]),
}


@dataclass
class TaskSpec:
    """Engine-internal decomposition row (pre-id, key-referenced deps)."""

    key: str
    capability: str
    title: str
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    def acceptance_criteria(self) -> List[AcceptanceCriterion]:
        criteria, _ = CAPABILITY_DEFAULTS.get(self.capability, CAPABILITY_DEFAULTS["general"])
        return [AcceptanceCriterion(f"AC-{i + 1}", text) for i, text in enumerate(criteria)]

    def quality_gates(self) -> List[QualityGateResult]:
        _, gates = CAPABILITY_DEFAULTS.get(self.capability, CAPABILITY_DEFAULTS["general"])
        return [QualityGateResult(g, GateVerdict.PENDING) for g in gates]


class PlanningError(TaskError):
    """Refusal to build a plan from inconsistent inputs (fail-closed)."""


# ---------------------------------------------------------------------------
# Workspace persistence (repository file plane; DB stays runtime-owned)
# ---------------------------------------------------------------------------


def task_orchestration_dir(repo_root: Path, project_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "orchestration" / "task-orchestration"


def plan_file_path(repo_root: Path, project_id: str) -> Path:
    return task_orchestration_dir(repo_root, project_id) / "plan.json"


def delegations_file_path(repo_root: Path, project_id: str) -> Path:
    return task_orchestration_dir(repo_root, project_id) / "delegations.json"


def next_plan_id(repo_root: Path, project_id: str) -> str:
    """PLAN-<project>-NNNN, sequential over persisted plans (file plane)."""
    directory = task_orchestration_dir(repo_root, project_id)
    used = []
    if directory.is_dir():
        for candidate in sorted(directory.glob("PLAN-*.json")):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                used.append(int(str(data.get("plan_id", "")).rsplit("-", 1)[-1]))
            except (ValueError, OSError):
                continue
    existing = plan_file_path(repo_root, project_id)
    if existing.is_file():
        try:
            data = json.loads(existing.read_text(encoding="utf-8"))
            used.append(int(str(data.get("plan_id", "")).rsplit("-", 1)[-1]))
        except (ValueError, OSError):
            pass
    seq = (max(used) + 1) if used else 1
    return f"PLAN-{project_id}-{seq:04d}"


def save_plan(plan: OrchestrationPlan, repo_root: Path, archive: bool = False) -> Path:
    """Persist the plan; ``archive=True`` also keeps an immutable per-plan copy."""
    directory = task_orchestration_dir(repo_root, plan.project_id)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"
    if archive:
        archived = directory / (plan.plan_id + ".json")
        if archived.exists():
            raise PlanningError(f"plan archive is append-only: {archived} exists")
        archived.write_text(payload, encoding="utf-8")
    target = plan_file_path(repo_root, plan.project_id)
    target.write_text(payload, encoding="utf-8")
    return target


def load_plan(repo_root: Path, project_id: str) -> OrchestrationPlan:
    path = plan_file_path(repo_root, project_id)
    if not path.is_file():
        raise PlanningError(f"no task-orchestration plan for {project_id}: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise PlanningError(f"{path}: corrupt plan JSON: {exc}") from exc
    try:
        return OrchestrationPlan.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise PlanningError(f"{path}: bad plan shape: {exc}") from exc


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TaskOrchestrationEngine:
    """Plans work for a goal: analyze → decompose → graph → agents/skills."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        registry_path: Optional[Path] = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else REPO_ROOT
        self.registry_path = (
            Path(registry_path)
            if registry_path
            else self.repo_root / "orchestration" / "skills" / "registry.json"
        )
        self._registry: Any = None
        self._registry_loaded = False

    # -- goal analysis --------------------------------------------------------

    def analyze_goal(self, goal: str, constraints: Sequence[str] = ()) -> GoalAnalysis:
        """Deterministic keyword-driven capability detection.

        Baseline capabilities (coordination, business-analysis, architecture,
        qa-testing, code-review) are always present: the factory pipeline
        mandates planning, requirements, an architecture step, testing, and
        an independent review before completion.
        """
        if not goal or not goal.strip():
            raise PlanningError("goal must be a non-empty statement")
        low = " " + goal.lower() + " "
        detected: Set[str] = {"coordination", "business-analysis", "architecture", "qa-testing", "code-review"}
        for capability, keywords in CAPABILITY_KEYWORDS:
            if any(kw in low for kw in keywords):
                detected.add(capability)
        risks = sorted({note for hint, note in RISK_HINTS if hint in low})
        ordered = self._pipeline_order(sorted(detected))
        return GoalAnalysis(
            goal=goal.strip(),
            capabilities=ordered,
            constraints=[str(c) for c in constraints],
            risks=risks,
        )

    # -- decomposition ----------------------------------------------------------

    def decompose(self, analysis: GoalAnalysis) -> List[TaskSpec]:
        """Project capabilities onto the standard pipeline with dependencies."""
        caps = set(analysis.capabilities)
        specs: List[TaskSpec] = []

        def add(key: str, capability: str, depends_on: Iterable[str], priority: Priority = Priority.MEDIUM) -> None:
            title, description = self._task_text(capability, analysis.goal)
            specs.append(
                TaskSpec(
                    key=key,
                    capability=capability,
                    title=title,
                    description=description,
                    depends_on=[d for d in depends_on if any(s.key == d for s in specs)],
                    priority=priority,
                    inputs=[f"goal: {analysis.goal}"] if not depends_on else [f"upstream: {d}" for d in depends_on],
                    outputs=[f"{capability} deliverable"],
                )
            )

        add("coordination", "coordination", [], Priority.CRITICAL)
        add("analysis", "business-analysis", ["coordination"])
        add("architecture", "architecture", ["analysis"])
        if "security-risk" in caps:
            add("security-risk", "security-risk", ["architecture"])
        if "ux-design" in caps:
            add("ux-design", "ux-design", ["architecture"])
        if "database-design" in caps:
            add("db-design", "database-design", ["architecture"])
        design_deps = ["architecture"]
        if "db-design" in caps:
            design_deps.append("db-design")
        implemented: List[str] = []
        if "backend" in caps:
            add("backend", "backend", design_deps, Priority.HIGH)
            implemented.append("backend")
        if "database" in caps:
            add("database", "database", design_deps, Priority.HIGH)
            implemented.append("database")
        if "frontend" in caps:
            ux_dep = ["ux-design"] if "ux-design" in caps else []
            add("frontend", "frontend", ["architecture"] + ux_dep, Priority.HIGH)
            implemented.append("frontend")
        if "integration" in caps and len(implemented) > 1:
            add("integration", "integration", list(implemented), Priority.HIGH)
            integration_done = ["integration"]
        else:
            integration_done = [d for d in implemented]
        qa_deps = list(integration_done) or ["architecture"]
        add("qa", "qa-testing", qa_deps, Priority.HIGH)
        if "performance" in caps:
            add("performance", "performance", ["qa"])
        if "security-audit" in caps:
            add("security-audit", "security-audit", qa_deps, Priority.HIGH)
        add("review", "code-review", ["qa"], Priority.HIGH)
        if "devops" in caps:
            add("devops", "devops", ["review"])
        if "deployment" in caps:
            add("deployment", "deployment", ["devops" if "devops" in caps else "review"], Priority.HIGH)
        if "documentation" in caps:
            add("documentation", "documentation", ["review"])
        if "quality-governance" in caps:
            add("governance", "quality-governance", ["review"])
        return specs

    @staticmethod
    def _task_text(capability: str, goal: str) -> Tuple[str, str]:
        verbs = {
            "coordination": ("Coordinate task orchestration", "Own the plan, assign tasks, track completion for goal."),
            "business-analysis": ("Analyze requirements", "Enumerate functional/non-functional requirements and acceptance criteria."),
            "architecture": ("Design architecture", "Produce the architecture and component contracts for the goal."),
            "quality-governance": ("Govern quality gates", "Record quality gate verdicts for every deliverable."),
            "security-risk": ("Assess security risk", "Identify threats and map them to controls."),
            "ux-design": ("Design UX", "Specify interaction flows and layouts."),
            "database-design": ("Design data model", "Define schema, constraints, and migrations plan."),
            "backend": ("Implement backend services", "Deliver backend modules per the approved architecture."),
            "frontend": ("Implement frontend", "Deliver UI per the approved design."),
            "database": ("Implement data layer", "Apply schema migrations and repository stores."),
            "integration": ("Integrate components", "Wire modules and prove the end-to-end flow."),
            "qa-testing": ("Verify with tests", "Build and run the test evidence for every acceptance criterion."),
            "code-review": ("Independent code review", "Review the delivered diff; auditor must not be the developer."),
            "performance": ("Validate performance", "Measure and report against targets."),
            "security-audit": ("Security audit", "Independent audit of the delivered surface."),
            "devops": ("Prepare delivery pipeline", "CI/CD and infrastructure for controlled deployment."),
            "deployment": ("Deploy in a controlled release", "Run the deployment runbook with rollback path."),
            "documentation": ("Write documentation", "Document delivered behavior."),
            "general": ("Deliver assigned work", "Complete the delegated unit of work."),
        }
        title, description = verbs.get(capability, verbs["general"])
        return f"{title} — {goal[:80]}", description

    # -- planning -----------------------------------------------------------------

    def select_agent(self, capability: str) -> str:
        agent = CAPABILITY_AGENTS.get(capability)
        if agent is None:
            raise PlanningError(f"unknown capability: {capability!r}")
        return agent

    def select_skills(self, agent_id: str, capability: str) -> List[str]:
        """ACTIVE skills assigned to ``agent_id`` (registry-driven, degradable)."""
        registry = self._load_registry()
        if registry is None:
            return []
        from orchestration.skills.models import Lifecycle  # governance vocabulary

        preferred = _CAPABILITY_SKILL_CATEGORY.get(capability)
        rows = [
            entry
            for entry in registry
            if entry.lifecycle == Lifecycle.ACTIVE and agent_id in entry.assignment.agents
        ]
        if preferred:
            matched = sorted(e.skill_id for e in rows if e.category.value == preferred)
            if matched:
                return matched
        return sorted(e.skill_id for e in rows)

    def build_plan(
        self,
        goal: str,
        *,
        project_id: str,
        plan_id: Optional[str] = None,
        constraints: Sequence[str] = (),
        created_at: Optional[str] = None,
    ) -> OrchestrationPlan:
        """Full pipeline: analyze → decompose → validated graph + skill bindings."""
        from .models import PLAN_ID_RE

        analysis = self.analyze_goal(goal, constraints)
        specs = self.decompose(analysis)
        graph = TaskGraph()
        key_to_id: Dict[str, str] = {}
        stamp = created_at or utc_now_stamp()
        skills_by_task: Dict[str, List[str]] = {}
        for spec in specs:
            task_id = f"TASK-{graph.next_task_number():04d}"
            agent = self.select_agent(spec.capability)
            task = Task(
                task_id=task_id,
                title=spec.title,
                description=spec.description,
                status=TaskState.PENDING,
                priority=spec.priority,
                assigned_agent=agent,
                inputs=list(spec.inputs),
                outputs=list(spec.outputs),
                acceptance_criteria=spec.acceptance_criteria(),
                quality_gates=spec.quality_gates(),
                created_at=stamp,
                updated_at=stamp,
            )
            deps = [key_to_id[k] for k in spec.depends_on]
            missing = [k for k in spec.depends_on if k not in key_to_id]
            if missing:
                raise PlanningError(f"spec {spec.key} depends on unknown keys: {missing}")
            graph.add_task(task, depends_on=deps)
            key_to_id[spec.key] = task_id
            skills_by_task[task_id] = self.select_skills(agent, spec.capability)
        # Validate plan identity format before construction.
        probe_id = plan_id or next_plan_id(self.repo_root, project_id)
        if not PLAN_ID_RE.match(probe_id):
            raise PlanningError(f"bad plan_id: {probe_id!r} (expected PLAN-PROJECT-NNN-NNNN)")
        plan = OrchestrationPlan(
            plan_id=probe_id,
            project_id=project_id,
            analysis=analysis,
            graph=graph,
            skills_by_task=skills_by_task,
            created_at=stamp,
        )
        issues = plan.validate()
        if issues:
            raise PlanningError("invalid plan: " + "; ".join(issues))
        return plan

    # -- grouping queries -----------------------------------------------------------

    @staticmethod
    def parallel_groups(plan: OrchestrationPlan) -> List[List[str]]:
        """Waves of mutually independent tasks (parallel within, sequential across)."""
        return plan.graph.waves()

    @staticmethod
    def sequential_order(plan: OrchestrationPlan) -> List[str]:
        return plan.graph.topological_order()

    @staticmethod
    def ready_tasks(plan: OrchestrationPlan) -> List[str]:
        return plan.graph.ready_tasks()

    # -- internals --------------------------------------------------------------------

    @staticmethod
    def _pipeline_order(capabilities: List[str]) -> List[str]:
        order = [
            "coordination",
            "business-analysis",
            "architecture",
            "security-risk",
            "ux-design",
            "database-design",
            "backend",
            "frontend",
            "database",
            "integration",
            "performance",
            "qa-testing",
            "security-audit",
            "code-review",
            "quality-governance",
            "devops",
            "deployment",
            "documentation",
        ]
        rank = {cap: i for i, cap in enumerate(order)}
        return sorted(capabilities, key=lambda c: (rank.get(c, len(order)), c))

    def _load_registry(self) -> Any:
        if self._registry_loaded:
            return self._registry
        self._registry_loaded = True
        path = self.registry_path
        if not path or not Path(path).is_file():
            self._registry = None
            return None
        try:
            from orchestration.skills.registry import Registry

            self._registry = Registry.load(path)
        except Exception:
            # Degradation, not failure: skill binding is advisory only and
            # must never block planning. Governance plane remains the gate.
            self._registry = None
        return self._registry


#: capability → skills-registry category value (``Category`` enum members).
_CAPABILITY_SKILL_CATEGORY: Dict[str, str] = {
    "coordination": "agent-process",
    "business-analysis": "requirements-engineering",
    "quality-governance": "quality-gate",
    "architecture": "architecture-design",
    "security-risk": "security-compliance",
    "ux-design": "ui-ux-accessibility",
    "database-design": "database-data",
    "backend": "backend-api",
    "frontend": "ui-ux-accessibility",
    "database": "database-data",
    "integration": "devops-delivery",
    "performance": "debugging-performance",
    "qa-testing": "testing",
    "security-audit": "security-compliance",
    "code-review": "code-quality-review",
    "devops": "devops-delivery",
    "deployment": "devops-delivery",
    "documentation": "docs-knowledge",
    "general": "agent-process",
}


__all__ = [
    "CAPABILITY_AGENTS",
    "CAPABILITY_DEFAULTS",
    "IMPLEMENTATION_CAPABILITIES",
    "PlanningError",
    "TaskOrchestrationEngine",
    "TaskSpec",
    "delegations_file_path",
    "load_plan",
    "next_plan_id",
    "plan_file_path",
    "save_plan",
    "task_orchestration_dir",
]
