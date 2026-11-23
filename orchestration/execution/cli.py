"""CLI for the execution continuity plane (Stage 2A).

Run with ``python -m orchestration.execution.cli <command> ...`` from the repo
root. All commands emit JSON on stdout and return a non-zero status on a
failed verification or blocked operation — mirroring the skills governance
CLI convention.

Exit codes: ``0`` ok; ``1`` verification failed / blocked; ``2`` bad usage;
``3`` refused by a governance guard (approval required, duplicate resume,
needs-intervention, append-only violation).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from .context import assemble_context, check_staleness, load_manifest
from .documents import (
    SCOPE_NORMATIVE,
    SCOPE_OPERATIONAL,
    consolidated_state,
    create_document,
    latest_document,
    verify_document,
    verify_index,
    write_state_document,
)
from .ledger import Ledger, LedgerError, ledger_path, verify_ledger
from .models import ExecutionError
from .resume import (
    DuplicateResumeError,
    ResumeBlocked,
    ResumeNeedsIntervention,
    evaluate_resume,
    start_resume,
)
from .snapshot import create_snapshot, list_snapshots, verify_snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="execution",
        description="Execution continuity plane: snapshots, ledger, context, resume, docs (Stage 2A)",
    )
    parser.add_argument(
        "--root", default=str(REPO_ROOT), help="repository root (default: detected)"
    )
    sub = parser.add_subparsers(dest="command")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", required=True, help="PROJECT-NNN")
        p.add_argument("--execution", required=True, help="EXEC-NNNN")
        p.add_argument("--agent", required=True, help="AG-NNN acting")

    p = sub.add_parser("snapshot-create", help="freeze a checkpoint (writes snapshot + journals checkpoint)")
    common(p)
    p.add_argument("--task", required=True)
    p.add_argument("--reason", required=True, help="checkpoint trigger (§4.2)")
    p.add_argument("--file", action="append", default=[], help="working-set file, repo-relative (repeatable)")
    p.add_argument("--ledger", help="ledger JSONL path (default: conventional projects/<ID>/execution/ledger path)")
    p.add_argument("--manifest-hash", help="context manifest hash to pin")
    p.add_argument("--skill", action="append", default=[], help="skill_id=path to pin (repeatable)")
    p.add_argument("--model", help="model id for model_binding")
    p.add_argument("--provider", help="provider id for model_binding")
    p.add_argument("--branch", default="")
    p.add_argument("--before-commit", default="")
    p.add_argument("--after-commit", default="")
    p.add_argument("--no-eligibility", action="store_true", help="mark snapshot NOT resume-eligible")
    p.add_argument("--requires-approval", action="store_true")
    p.add_argument("--notes", default="")

    p = sub.add_parser("snapshot-verify", help="re-verify one snapshot (hash, files, ledger chain)")
    p.add_argument("snapshot", help="path to SNAP-*.json")
    p.add_argument("--no-files", action="store_true", help="skip working-tree comparison")

    p = sub.add_parser("snapshot-list", help="list snapshots for a project/execution")
    p.add_argument("--project", required=True)
    p.add_argument("--execution")

    p = sub.add_parser("ledger-append", help="append one chained event to a ledger")
    common(p)
    p.add_argument("--ledger", help="ledger JSONL path (default: conventional path)")
    p.add_argument("--event", required=True, help="event_type (§4.4 vocabulary)")
    p.add_argument("--payload", default="{}", help="JSON object payload")
    p.add_argument("--effect", default="none", help="none | idempotent | applied-irreversible")

    p = sub.add_parser("ledger-verify", help="full chain verification of a ledger")
    p.add_argument("--ledger", required=True)

    p = sub.add_parser("ledger-show", help="print ledger records")
    p.add_argument("--ledger", required=True)

    p = sub.add_parser("context-assemble", help="build and persist a context manifest")
    common(p)
    p.add_argument("--task-ref", action="append", default=[], help="T1 file (repeatable)")
    p.add_argument("--skill", action="append", default=[], help="skill_id=path (repeatable)")
    p.add_argument("--working-ref", action="append", default=[], help="T3 file (repeatable)")
    p.add_argument("--budget", type=int, help="token budget for trimming T2/T3")

    p = sub.add_parser("context-check", help="re-fingerprint a stored manifest (staleness)")
    p.add_argument("manifest", help="path to CTX-*.json")

    p = sub.add_parser("resume-eval", help="fail-closed eligibility evaluation for a snapshot")
    p.add_argument("snapshot")
    p.add_argument("--no-git", action="store_true", help="skip git-anchor probing")

    p = sub.add_parser("resume-start", help="execute the forward-only resume transaction")
    p.add_argument("snapshot")
    p.add_argument("--new-execution", required=True, help="EXEC-NNNN successor id")
    p.add_argument("--agent", required=True)
    p.add_argument("--failure-signature", default="")
    p.add_argument("--model", help="JSON model_binding for the successor")
    p.add_argument("--no-git", action="store_true")

    p = sub.add_parser("doc-create", help="create a numbered EXEC_000N.md document")
    p.add_argument("--scope", required=True, choices=[SCOPE_NORMATIVE, SCOPE_OPERATIONAL])
    p.add_argument("--project", help="required for operational scope")
    p.add_argument("--agent", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--execution", help="EXEC-NNNN the document narrates")
    p.add_argument("--task", help="TASK id")
    p.add_argument("--body-file", help="markdown body source file (default: stdin)")
    p.add_argument("--supersedes", help="EXEC_000K of the document being corrected")
    p.add_argument("--status", default="DRAFT")

    p = sub.add_parser("doc-verify", help="verify document hash / index integrity")
    p.add_argument("--scope", required=True, choices=[SCOPE_NORMATIVE, SCOPE_OPERATIONAL])
    p.add_argument("--project")
    p.add_argument("--doc", help="verify one EXEC_000N.md by path instead of the whole index")

    p = sub.add_parser("doc-latest", help="show the latest non-superseded document")
    p.add_argument("--scope", required=True, choices=[SCOPE_NORMATIVE, SCOPE_OPERATIONAL])
    p.add_argument("--project")
    p.add_argument("--kind")
    p.add_argument("--execution")

    p = sub.add_parser("state-show", help="print the latest consolidated operational state")
    p.add_argument("--project", required=True)

    p = sub.add_parser("state-consolidate", help="commit the consolidated state as an EXEC_000N.md document")
    p.add_argument("--project", required=True)
    p.add_argument("--agent", required=True)

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
    except (ExecutionError, LedgerError, ValueError, OSError) as exc:
        _emit({"ok": False, "error": str(exc), "command": args.command})
        return 3


def _dispatch(args: argparse.Namespace, root: Path) -> int:
    cmd = args.command

    if cmd == "snapshot-create":
        skills = []
        for spec in args.skill:
            sid, _, path = spec.partition("=")
            skills.append((sid, path))
        model_binding = {}
        if args.model or args.provider:
            model_binding = {"provider": args.provider, "model": args.model, "fallback_status": "RUNNING"}
        ledger_file = Path(args.ledger or ledger_path(root, args.project, args.execution))
        ledger = Ledger.open(ledger_file, args.execution) if ledger_file.exists() else None
        snapshot = create_snapshot(
            root,
            project_id=args.project,
            execution_id=args.execution,
            task_id=args.task,
            agent_id=args.agent,
            reason=args.reason,
            files=args.file,
            context_manifest_hash=args.manifest_hash,
            skills=skills,
            model_binding=model_binding,
            ledger=ledger,
            resume_eligible=not args.no_eligibility,
            requires_approval=args.requires_approval,
            eligibility_notes=args.notes,
            git_branch=args.branch,
            before_commit=args.before_commit,
            after_commit=args.after_commit,
        )
        _emit({"ok": True, "snapshot": snapshot.to_dict()})
        return 0

    if cmd == "snapshot-verify":
        report = verify_snapshot(
            root, Path(args.snapshot), check_files=not args.no_files, check_ledger=True
        )
        _emit(report.to_dict())
        return 0 if report.ok else 1

    if cmd == "snapshot-list":
        rows = list_snapshots(root, args.project, args.execution)
        _emit({"ok": True, "snapshots": [
            {"snapshot_id": r.snapshot_id, "execution_id": r.execution_id, "path": str(r.path.relative_to(root))}
            for r in rows
        ]})
        return 0

    if cmd == "ledger-append":
        payload = json.loads(args.payload)
        ledger = _load_ledger_or_create(root, args)
        entry = ledger.append(args.event, args.agent, payload, effect=args.effect)
        _emit({"ok": True, "record": entry.to_dict()})
        return 0

    if cmd == "ledger-verify":
        report = verify_ledger(Path(args.ledger))
        _emit(report.to_dict())
        return 0 if report.ok else 1

    if cmd == "ledger-show":
        report = verify_ledger(Path(args.ledger))
        if not report.ok:
            _emit(report.to_dict())
            return 1
        from .ledger import read_records

        _emit({"ok": True, "records": [e.to_dict() for e in read_records(Path(args.ledger))]})
        return 0

    if cmd == "context-assemble":
        skills = []
        for spec in args.skill:
            sid, _, path = spec.partition("=")
            skills.append((sid, path))
        manifest = assemble_context(
            root,
            project_id=args.project,
            execution_id=args.execution,
            task_refs=args.task_ref,
            skills=skills,
            working_refs=args.working_ref,
            token_budget=args.budget,
        )
        _emit({"ok": True, "manifest": manifest.to_dict()})
        return 0

    if cmd == "context-check":
        manifest = load_manifest(Path(args.manifest))
        report = check_staleness(root, manifest)
        _emit(report.to_dict())
        return 0 if report.ok else 1

    if cmd == "resume-eval":
        decision = evaluate_resume(root, Path(args.snapshot), check_git=not args.no_git)
        _emit(decision.to_dict())
        return 0 if decision.eligible else 1

    if cmd == "resume-start":
        model_binding = json.loads(args.model) if args.model else None
        try:
            result = start_resume(
                root,
                Path(args.snapshot),
                new_execution_id=args.new_execution,
                actor_agent=args.agent,
                failure_signature=args.failure_signature,
                model_binding=model_binding,
                check_git=not args.no_git,
            )
        except (ResumeBlocked, ResumeNeedsIntervention, DuplicateResumeError) as exc:
            _emit({"ok": False, "refusal": type(exc).__name__, "error": str(exc)})
            return 3
        _emit(result)
        return 0

    if cmd == "doc-create":
        body = (
            Path(args.body_file).read_text(encoding="utf-8")
            if args.body_file
            else sys.stdin.read()
        )
        doc = create_document(
            root,
            args.scope,
            kind=args.kind,
            agent_id=args.agent,
            body=body,
            title=args.title,
            execution_id=args.execution,
            task_id=args.task,
            project_id=args.project,
            supersedes=args.supersedes,
            status=args.status,
        )
        _emit({"ok": True, "doc_id": doc.doc_id, "content_sha256": doc.content_sha256})
        return 0

    if cmd == "doc-verify":
        if args.doc:
            issues = verify_document(Path(args.doc))
            _emit({"ok": not issues, "issues": issues})
            return 0 if not issues else 1
        issues = verify_index(root, args.scope, args.project)
        _emit({"ok": not issues, "issues": issues})
        return 0 if not issues else 1

    if cmd == "doc-latest":
        doc = latest_document(
            root, args.scope, project_id=args.project, kind=args.kind, execution_id=args.execution
        )
        if doc is None:
            _emit({"ok": True, "document": None})
            return 0
        payload = doc.to_dict()
        payload["body"] = doc.body
        _emit({"ok": True, "document": payload})
        return 0

    if cmd == "state-show":
        _emit({"ok": True, "state": consolidated_state(root, args.project)})
        return 0

    if cmd == "state-consolidate":
        doc = write_state_document(root, args.project, agent_id=args.agent)
        _emit({"ok": True, "doc_id": doc.doc_id, "content_sha256": doc.content_sha256})
        return 0

    parser = build_parser()
    parser.print_help()
    return 2


def _load_ledger_or_create(root: Path, args: argparse.Namespace) -> Ledger:
    path = Path(getattr(args, "ledger", None) or ledger_path(root, args.project, args.execution))
    if path.exists():
        return Ledger.open(path, args.execution)
    return Ledger.create(path, args.execution, actor_agent=args.agent, payload={"source": "cli"})


if __name__ == "__main__":
    sys.exit(main())
