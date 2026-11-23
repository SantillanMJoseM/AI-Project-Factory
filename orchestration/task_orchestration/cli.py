"""CLI for the Task Orchestration plane (Stage 2B).

Run with ``python -m orchestration.task_orchestration.cli <command> ...``
from the repo root. All commands emit JSON on stdout and return a non-zero
status on a failed verification or refused operation — mirroring the
execution-plane CLI convention.

Exit codes: ``0`` ok; ``1`` verification failed (independent verification
refused the child task); ``2`` bad usage; ``3`` refused by a guard (Task
Contract rules 1-4, cycle check, catalog check, delegation preconditions).

The CLI reads and writes the repository file plane only
(``projects/<ID>/orchestration/task-orchestration/``). It authorizes nothing,
starts nothing, and never touches agent/runtime/config files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from .coordination import AgentCoordinationManager
from .delegation import DelegationManager
from .engine import TaskOrchestrationEngine, load_plan, save_plan
from .model_fallback_integration import make_manager
from .models import (
    OrchestrationPlan,
    Priority,
    TaskError,
    TaskState,
    transition_task,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _parse_json_obj(text: Optional[str]) -> Optional[dict]:
    if text is None:
        return None
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-orchestration",
        description=(
            "Task Orchestration (Stage 2B): plans, dependency groups, "
            "delegation with independent verification, coordination state"
        ),
    )
    parser.add_argument(
        "--root", default=str(REPO_ROOT), help="repository root (default: detected)"
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser(
        "plan-build",
        help="analyze a goal, decompose, and build a validated plan (optionally persist it)",
    )
    p.add_argument("--project", required=True, help="PROJECT-NNN")
    p.add_argument("--goal", required=True)
    p.add_argument("--plan-id", help="PLAN-PROJECT-NNN-NNNN (default: next sequential)")
    p.add_argument("--constraint", action="append", default=[], help="constraint note (repeatable)")
    p.add_argument("--save", action="store_true", help="persist to the workspace file plane")
    p.add_argument("--archive", action="store_true", help="with --save: also keep an immutable copy")

    p = sub.add_parser("plan-show", help="print the persisted plan")
    p.add_argument("--project", required=True)

    p = sub.add_parser(
        "groups",
        help="parallel waves, sequential order, and currently-ready tasks of the persisted plan",
    )
    p.add_argument("--project", required=True)

    p = sub.add_parser(
        "task-set",
        help="one guarded task transition on the persisted plan (Task Contract rules enforced)",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True, help="TASK-NNNN")
    p.add_argument("--state", required=True, help="target TaskState (e.g. ASSIGNED, RUNNING)")
    p.add_argument("--actor", required=True, help="AG-NNN performing the transition")
    p.add_argument("--reason", default="")
    p.add_argument("--criteria", help='JSON object {"AC-1": true, ...} overrides criterion flags')
    p.add_argument("--gates", help='JSON object {"QG-CODE": "PASS", ...} overrides gate verdicts')

    p = sub.add_parser(
        "delegate",
        help="create a parent->child delegation (child task joins the plan, ASSIGNED)",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--parent", required=True, help="delegating TASK-NNNN")
    p.add_argument("--delegatee", required=True, help="AG-NNN receiving the child task")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--priority", default="medium",
                   choices=[m.value for m in Priority])

    p = sub.add_parser(
        "delegation-track",
        help="move a delegated child task (COMPLETED is refused: use delegation-verify)",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--delegation", required=True, help="DELEG-NNNN")
    p.add_argument("--state", required=True, help="RUNNING | BLOCKED | REVIEW_REQUIRED | FAILED | CANCELLED")
    p.add_argument("--actor", required=True)
    p.add_argument("--reason", default="")

    p = sub.add_parser(
        "delegation-verify",
        help="fail-closed independent verification of a SUBMITTED delegation",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--delegation", required=True)
    p.add_argument("--verifier", required=True, help="AG-NNN independent of delegatee and delegator")
    p.add_argument("--criteria", help='JSON object {"AC-1": true, ...}')
    p.add_argument("--gates", help='JSON object {"QG-CODE": "PASS", ...}')

    p = sub.add_parser(
        "delegation-revoke",
        help="cancel a delegated child task (§rule 4: reason mandatory)",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--delegation", required=True)
    p.add_argument("--actor", default="")
    p.add_argument("--reason", required=True)

    p = sub.add_parser(
        "status",
        help="consolidated coordination state for the persisted plan",
    )
    p.add_argument("--project", required=True)
    p.add_argument("--models", action="store_true",
                   help="probe model readiness per agent through the runtime fallback manager")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    root = Path(args.root)

    try:
        return _dispatch(args, root)
    except (TaskError, ValueError, KeyError, OSError) as exc:
        _emit({"ok": False, "error": str(exc), "command": args.command})
        return 3


def _load(root: Path, project_id: str) -> OrchestrationPlan:
    return load_plan(root, project_id)


def _dispatch(args: argparse.Namespace, root: Path) -> int:
    cmd = args.command

    if cmd == "plan-build":
        engine = TaskOrchestrationEngine(root)
        plan = engine.build_plan(
            args.goal,
            project_id=args.project,
            plan_id=args.plan_id,
            constraints=args.constraint,
        )
        payload = {"plan": plan.to_dict(), "saved_to": None}
        if args.save:
            payload["saved_to"] = str(save_plan(plan, root, archive=args.archive))
        _emit({"ok": True, "plan_id": plan.plan_id, "waves": plan.graph.waves(),
                "sequential_order": plan.graph.topological_order(), **payload})
        return 0

    if cmd == "plan-show":
        plan = _load(root, args.project)
        _emit({"ok": True, "plan": plan.to_dict()})
        return 0

    if cmd == "groups":
        plan = _load(root, args.project)
        _emit({
            "ok": True,
            "plan_id": plan.plan_id,
            "parallel_groups": plan.graph.waves(),
            "sequential_order": plan.graph.topological_order(),
            "ready_tasks": plan.graph.ready_tasks(),
            "state_counts": plan.graph.state_counts(),
        })
        return 0

    if cmd == "task-set":
        plan = _load(root, args.project)
        task = plan.graph.require(args.task)
        previous = TaskState(task.status).value
        entry = transition_task(
            task,
            args.state.upper(),
            actor=args.actor,
            reason=args.reason,
            criteria_results=_parse_json_obj(args.criteria),
            gate_results=_parse_json_obj(args.gates),
        )
        save_plan(plan, root)
        _emit({
            "ok": True,
            "task_id": task.task_id,
            "transition": entry.to_dict(),
            "previous_state": previous,
            "current_state": TaskState(task.status).value,
        })
        return 0

    if cmd == "delegate":
        plan = _load(root, args.project)
        manager = DelegationManager.load(plan, root)
        record = manager.create_delegation(
            args.parent,
            args.title,
            args.description,
            args.delegatee,
            priority=Priority(args.priority),
        )
        manager.save(root)
        save_plan(plan, root)  # the child task joined the graph
        _emit({"ok": True, "delegation": record.to_dict()})
        return 0

    if cmd == "delegation-track":
        plan = _load(root, args.project)
        manager = DelegationManager.load(plan, root)
        record = manager.track_status(args.delegation, args.state.upper(), args.actor, args.reason)
        manager.save(root)
        save_plan(plan, root)
        _emit({"ok": True, "delegation": record.to_dict()})
        return 0

    if cmd == "delegation-verify":
        plan = _load(root, args.project)
        manager = DelegationManager.load(plan, root)
        report = manager.verify_completion(
            args.delegation,
            args.verifier,
            criteria_results=_parse_json_obj(args.criteria),
            gate_results=_parse_json_obj(args.gates),
        )
        manager.save(root)
        save_plan(plan, root)
        _emit({"ok": report.ok, "report": report.to_dict()})
        return 0 if report.ok else 1

    if cmd == "delegation-revoke":
        plan = _load(root, args.project)
        manager = DelegationManager.load(plan, root)
        record = manager.revoke(args.delegation, actor=args.actor, reason=args.reason)
        manager.save(root)
        save_plan(plan, root)
        _emit({"ok": True, "delegation": record.to_dict()})
        return 0

    if cmd == "status":
        plan = _load(root, args.project)
        manager = DelegationManager.load(plan, root)
        records = [manager.records[k] for k in sorted(manager.records)]
        fallback_manager = make_manager(root) if args.models else None
        coordination = AgentCoordinationManager(plan, records, fallback_manager=fallback_manager)
        state = coordination.consolidated_state(include_model_status=bool(args.models))
        _emit({"ok": True, "state": state.to_dict()})
        return 0

    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
