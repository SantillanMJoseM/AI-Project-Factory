"""CLI for the skills governance runtime.

Run with ``python -m orchestration.skills.cli <command> ...`` from the repo root.
All commands emit JSON on stdout and return a non-zero status on a failed gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from .registry import Registry, RegistryError, render_permissions
from .security_scan import scan_skill_dir
from .validator import check_derived_config, validate_registry, validate_skill_directory


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skills", description="Skills governance runtime (Stage 0)")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="validate a registry and/or skill directories")
    p_validate.add_argument("--registry", required=True, help="path to registry.json")
    p_validate.add_argument("--schema", help="override path to skill-registry.schema.json")
    p_validate.add_argument("--repo-root", help="resolve library_path / hashes / Plane A against this root")
    p_validate.add_argument("--skill-dir", action="append", default=[], help="skill dir to structurally validate (repeatable)")

    p_scan = sub.add_parser("scan", help="offline content-safety scan (V-6)")
    p_scan.add_argument("path", help="skill directory to scan")

    p_permissions = sub.add_parser("permissions", help="render derived opencode.json skill rules (I-3)")
    p_permissions.add_argument("--registry", required=True)
    p_permissions.add_argument("--output", help="write canonical bytes to this file instead of stdout")

    p_check = sub.add_parser("check-permissions", help="regenerate-and-diff a derived config")
    p_check.add_argument("--registry", required=True)
    p_check.add_argument("--config", required=True)

    p_transition = sub.add_parser("transition", help="apply a guarded lifecycle transition")
    p_transition.add_argument("--registry", required=True)
    p_transition.add_argument("--skill-id", required=True)
    p_transition.add_argument("--to", required=True, help="target lifecycle state")
    p_transition.add_argument("--output", help="write updated registry here (default: overwrite input)")
    p_transition.add_argument("--gates", action="append", default=[], help="gate evidence ref (repeatable)")
    p_transition.add_argument("--adr")
    p_transition.add_argument("--actor")
    p_transition.add_argument("--evidence")

    p_rollback = sub.add_parser("rollback", help="kill-switch rollback of one skill (T-3)")
    p_rollback.add_argument("--registry", required=True)
    p_rollback.add_argument("--skill-id", required=True)
    p_rollback.add_argument("--output", help="write updated registry here (default: overwrite input)")
    p_rollback.add_argument("--actor")
    p_rollback.add_argument("--reason")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate":
        registry = Registry.load(args.registry)
        report = validate_registry(registry, schema_path=args.schema, repo_root=args.repo_root)
        for skill_dir in args.skill_dir:
            report.extend(validate_skill_directory(skill_dir))
        report.target = args.registry
        _emit(report.to_dict())
        return 0 if report.ok else 1

    if args.command == "scan":
        result = scan_skill_dir(args.path)
        _emit(result.to_dict())
        return 0 if result.ok else 2

    if args.command == "permissions":
        registry = Registry.load(args.registry)
        text = render_permissions(registry)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            _emit({"written": str(target), "bytes": len(text.encode("utf-8"))})
        else:
            sys.stdout.write(text)
        return 0

    if args.command == "check-permissions":
        registry = Registry.load(args.registry)
        report = check_derived_config(registry, args.config)
        _emit(report.to_dict())
        return 0 if report.ok else 1

    if args.command in ("transition", "rollback"):
        registry = Registry.load(args.registry)
        try:
            if args.command == "transition":
                entry = registry.transition(
                    args.skill_id,
                    args.to,
                    gates=args.gates or None,
                    adr=args.adr,
                    actor=args.actor,
                    evidence=args.evidence,
                )
            else:
                entry = registry.rollback(args.skill_id, actor=args.actor, reason=args.reason)
        except RegistryError as exc:
            _emit({"ok": False, "error": str(exc)})
            return 3
        target = Path(args.output or args.registry)
        registry.save(target)
        _emit({"ok": True, "written": str(target), "skill": entry.to_dict()})
        return 0

    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
