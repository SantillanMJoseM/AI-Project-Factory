"""Numbered execution documents — ``EXEC_000N.md`` system (Stage 2A).

Implements §5 of ``docs/execution/EXECUTION_ARCHITECTURE.md``:

* name form ``EXEC_`` + exactly 4 zero-padded digits + ``.md``; document
  ``EXEC_0042.md`` narrates execution ``EXEC-0042`` (mapping is positional);
* two scopes with separate number series — normative ``docs/execution/`` and
  operational ``projects/<PROJECT_ID>/execution/`` — allocated gaplessly via
  an ``index.json`` counter inside each scope (the runtime ``id_sequences``
  DB path is out of reach for this stdlib-only stage; the file counter is
  the repository-plane bridge and is validated against existing files);
* mandatory metadata block (doc_id, execution_id, task_id, agent_id,
  created_at, status, snapshot_refs, ledger_range, content_sha256 of the
  body below the block), then Summary / Evidence / Outcome sections;
* immutability: committed documents are never edited post-terminal;
  corrections are new documents carrying ``supersedes: EXEC_000K``, the
  superseded document receives a one-line footer pointer appended by this
  tooling, and ``DOC_SUPERSEDED`` is journaled when a ledger is supplied;
* ``index.json`` maps EXEC_000N ↔ execution ↔ snapshots ↔ ledger; it can be
  rebuilt from the directory and diffed (divergence ⇒ review BLOCKED).

Latest consolidated state: :func:`consolidated_state` merges the newest
snapshot, the ledger heads, and the newest documents per execution into one
view; :func:`write_state_document` commits that view as a new ``kind: state``
document (superseding the previous state document).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .ledger import Ledger, LedgerError, read_records
from .models import (
    DOC_ID_RE,
    EXEC_ID_RE,
    ExecutionError,
    canonical_json,
    sha256_text,
    utc_now_stamp,
)
from .snapshot import list_snapshots, load_snapshot

SCOPE_NORMATIVE = "normative"
SCOPE_OPERATIONAL = "operational"
SCOPES = (SCOPE_NORMATIVE, SCOPE_OPERATIONAL)

DOC_KINDS = (
    "architecture",
    "runbook",
    "report",
    "recovery",
    "divergence",
    "approval-dossier",
    "state",
    "outcome",
)

DOC_NAME_RE = re.compile(r"^EXEC_([0-9]{4})\.md$")
META_LINE_RE = re.compile(r"^- \*\*([a-z0-9_]+)\*\*: (.*)$")
BODY_SEPARATOR = "\n\n---\n\n"

SUPERSEDE_FOOTER = "\n> Superseded by {new_id}.md — this document is no longer current.\n"


class DocumentError(ExecutionError):
    """Structural or governance failure in the document system (fail-closed)."""


def scope_dir(root: Path, scope: str, project_id: Optional[str] = None) -> Path:
    if scope == SCOPE_NORMATIVE:
        return Path(root) / "docs" / "execution"
    if scope == SCOPE_OPERATIONAL:
        if not project_id:
            raise DocumentError("operational scope requires project_id")
        return Path(root) / "projects" / project_id / "execution"
    raise DocumentError(f"unknown scope: {scope!r}")


# ---------------------------------------------------------------------------
# Index (gapless allocation + reverse diff)
# ---------------------------------------------------------------------------


def index_path(root: Path, scope: str, project_id: Optional[str] = None) -> Path:
    return scope_dir(root, scope, project_id) / "index.json"


def load_index(root: Path, scope: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    path = index_path(root, scope, project_id)
    if not path.exists():
        return {"scope": scope, "project_id": project_id, "next_number": 1, "documents": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DocumentError(f"{path}: corrupt document index: {exc}") from exc


def _save_index(root: Path, scope: str, project_id: Optional[str], index: Dict[str, Any]) -> None:
    path = index_path(root, scope, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(canonical_json(index) + "\n", encoding="utf-8")
    tmp.replace(path)


def _scan_existing_numbers(directory: Path) -> List[int]:
    if not directory.is_dir():
        return []
    numbers = []
    for candidate in directory.glob("EXEC_*.md"):
        match = DOC_NAME_RE.match(candidate.name)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def allocate_doc_id(root: Path, scope: str, project_id: Optional[str] = None) -> str:
    """Allocate the next gapless ``EXEC_00NN`` number for the scope.

    The counter never regresses below any file already present in the
    directory (so hand-placed documents cannot cause collisions).
    """
    directory = scope_dir(root, scope, project_id)
    directory.mkdir(parents=True, exist_ok=True)
    index = load_index(root, scope, project_id)
    existing = _scan_existing_numbers(directory)
    next_number = max(int(index.get("next_number", 1)), (max(existing) + 1) if existing else 1)
    doc_id = f"EXEC_{next_number:04d}"
    index["next_number"] = next_number + 1
    _save_index(root, scope, project_id, index)
    return doc_id


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------


@dataclass
class ExecDocument:
    doc_id: str
    scope: str
    kind: str
    agent_id: str
    created_at: str
    status: str
    title: str = ""
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    snapshot_refs: List[str] = field(default_factory=list)
    ledger_range: Optional[Tuple[int, int]] = None
    supersedes: Optional[str] = None
    content_sha256: str = ""
    body: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "scope": self.scope,
            "kind": self.kind,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "status": self.status,
            "title": self.title,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "snapshot_refs": list(self.snapshot_refs),
            "ledger_range": list(self.ledger_range) if self.ledger_range else None,
            "supersedes": self.supersedes,
            "content_sha256": self.content_sha256,
        }


def render_document(doc: ExecDocument) -> str:
    """Serialize to ``EXEC_000N.md`` bytes (metadata block + body)."""
    ledger_range = (
        f"[{doc.ledger_range[0]}..{doc.ledger_range[1]}]" if doc.ledger_range else "none"
    )
    lines = [
        f"# {doc.doc_id} — {doc.title or doc.kind}",
        "",
        f"- **doc_id**: {doc.doc_id}",
        f"- **scope**: {doc.scope}",
        f"- **kind**: {doc.kind}",
        f"- **execution_id**: {doc.execution_id or 'none'}",
        f"- **task_id**: {doc.task_id or 'none'}",
        f"- **project_id**: {doc.project_id or 'none'}",
        f"- **agent_id**: {doc.agent_id}",
        f"- **created_at**: {doc.created_at}",
        f"- **status**: {doc.status}",
        "- **snapshot_refs**: " + (", ".join(doc.snapshot_refs) if doc.snapshot_refs else "none"),
        f"- **ledger_range**: {ledger_range}",
        f"- **supersedes**: {doc.supersedes or 'none'}",
        f"- **content_sha256**: {doc.content_sha256}",
    ]
    header = "\n".join(lines)
    return header + BODY_SEPARATOR + doc.body.rstrip("\n") + "\n"


def parse_document(text: str) -> ExecDocument:
    """Inverse of :func:`render_document` (metadata + body only)."""
    if BODY_SEPARATOR not in text:
        raise DocumentError("document lacks the metadata/body separator")
    header, body = text.split(BODY_SEPARATOR, 1)
    meta: Dict[str, str] = {}
    title = ""
    for line in header.splitlines():
        if line.startswith("# "):
            title = line[3:].split("—", 1)[-1].strip()
        match = META_LINE_RE.match(line)
        if match:
            meta[match.group(1)] = match.group(2).strip()
    missing = {
        "doc_id", "scope", "kind", "agent_id", "created_at", "status", "content_sha256"
    } - set(meta)
    if missing:
        raise DocumentError(f"document metadata missing fields: {sorted(missing)}")
    ledger_range: Optional[Tuple[int, int]] = None
    range_match = re.match(r"^\[([0-9]+)\.\.([0-9]+)\]$", meta.get("ledger_range", "none"))
    if range_match:
        ledger_range = (int(range_match.group(1)), int(range_match.group(2)))
    refs = (
        []
        if meta.get("snapshot_refs", "none") == "none"
        else [r.strip() for r in meta["snapshot_refs"].split(",") if r.strip()]
    )

    def opt(key: str) -> Optional[str]:
        value = meta.get(key, "none")
        return None if value in ("", "none") else value

    return ExecDocument(
        doc_id=meta["doc_id"],
        scope=meta["scope"],
        kind=meta["kind"],
        agent_id=meta["agent_id"],
        created_at=meta["created_at"],
        status=meta["status"],
        title=title,
        execution_id=opt("execution_id"),
        task_id=opt("task_id"),
        project_id=opt("project_id"),
        snapshot_refs=refs,
        ledger_range=ledger_range,
        supersedes=opt("supersedes"),
        content_sha256=meta["content_sha256"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Create / verify / query
# ---------------------------------------------------------------------------


def create_document(
    root: Path,
    scope: str,
    *,
    kind: str,
    agent_id: str,
    body: str,
    title: str = "",
    execution_id: Optional[str] = None,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    snapshot_refs: Sequence[str] = (),
    ledger_range: Optional[Tuple[int, int]] = None,
    supersedes: Optional[str] = None,
    status: str = "DRAFT",
    stamp: Optional[str] = None,
    ledger: Optional[Ledger] = None,
) -> ExecDocument:
    """Create a new numbered document. Committed documents are never edited:
    corrections supersede (§5). ``supersedes`` triggers the footer pointer
    and, when a ledger handle is supplied, a ``DOC_SUPERSEDED`` record.
    """
    root = Path(root)
    if kind not in DOC_KINDS:
        raise DocumentError(f"unknown document kind: {kind!r} (allowed: {DOC_KINDS})")
    if execution_id is not None and not EXEC_ID_RE.match(execution_id):
        raise DocumentError(f"bad execution_id: {execution_id!r}")
    stamp = stamp or utc_now_stamp()

    doc_id = allocate_doc_id(root, scope, project_id)
    if supersedes is not None:
        _apply_supersede(root, scope, project_id, supersedes, doc_id)

    doc = ExecDocument(
        doc_id=doc_id,
        scope=scope,
        kind=kind,
        agent_id=agent_id,
        created_at=stamp,
        status=status,
        title=title,
        execution_id=execution_id,
        task_id=task_id,
        project_id=project_id,
        snapshot_refs=list(snapshot_refs),
        ledger_range=tuple(ledger_range) if ledger_range else None,
        supersedes=supersedes,
        content_sha256="",
        body=body,
    )
    doc.content_sha256 = sha256_text(doc.body.rstrip("\n") + "\n")

    directory = scope_dir(root, scope, project_id)
    target = directory / (doc.doc_id + ".md")
    if target.exists():
        raise DocumentError(f"document already exists (immutable): {target}")
    target.write_text(render_document(doc), encoding="utf-8")

    index = load_index(root, scope, project_id)
    index.setdefault("documents", {})[doc.doc_id] = {
        "file": target.name,
        "kind": doc.kind,
        "execution_id": doc.execution_id,
        "created_at": doc.created_at,
        "content_sha256": doc.content_sha256,
        "supersedes": doc.supersedes,
        "superseded_by": None,
    }
    _save_index(root, scope, project_id, index)

    if ledger is not None and supersedes is not None:
        ledger.append(
            "DOC_SUPERSEDED",
            agent_id,
            {"superseded": supersedes, "by": doc.doc_id},
            effect="idempotent",
            timestamp=stamp,
        )
    return doc


def _apply_supersede(
    root: Path,
    scope: str,
    project_id: Optional[str],
    old_id: str,
    new_id: str,
) -> None:
    """Append the one-line footer pointer to the superseded document (the
    only mutation this tooling performs on a committed document, §5)."""
    if not DOC_ID_RE.match(old_id):
        raise DocumentError(f"bad supersedes id: {old_id!r}")
    if old_id == new_id:
        raise DocumentError("a document cannot supersede itself")
    old_path = scope_dir(root, scope, project_id) / (old_id + ".md")
    if not old_path.is_file():
        raise DocumentError(f"cannot supersede missing document: {old_path}")
    text = old_path.read_text(encoding="utf-8")
    if "\n> Superseded by " in text:
        raise DocumentError(f"{old_id} is already superseded; supersede chains are linear")
    old_path.write_text(text.rstrip("\n") + SUPERSEDE_FOOTER.format(new_id=new_id), encoding="utf-8")
    index = load_index(root, scope, project_id)
    entry = index.get("documents", {}).get(old_id)
    if entry is not None:
        entry["superseded_by"] = new_id
        _save_index(root, scope, project_id, index)


def load_document(path: Path) -> ExecDocument:
    path = Path(path)
    if not path.exists():
        raise DocumentError(f"document not found: {path}")
    return parse_document(path.read_text(encoding="utf-8"))


def verify_document(path: Path) -> List[str]:
    """Re-check a document's content hash and name ↔ metadata agreement.

    The single permitted post-commit mutation — the supersede footer — is
    tolerated; any other body drift is tampering (fail-closed).
    """
    issues: List[str] = []
    doc = load_document(path)
    name_match = DOC_NAME_RE.match(Path(path).name)
    if not name_match:
        issues.append(f"file name {Path(path).name!r} does not match EXEC_000N.md form")
    elif f"EXEC_{name_match.group(1)}" != doc.doc_id:
        issues.append("file name and metadata doc_id disagree")
    if sha256_text(doc.body.rstrip("\n") + "\n") != doc.content_sha256:
        stripped = _strip_supersede_footer(doc.body)
        if stripped is None or sha256_text(stripped) != doc.content_sha256:
            issues.append("content_sha256 does not match document body")
    return issues


def _strip_supersede_footer(body: str) -> Optional[str]:
    marker = "\n> Superseded by "
    idx = body.rfind(marker)
    if idx == -1:
        return None
    stripped = body[:idx] + "\n"
    if not stripped.endswith("\n\n"):
        stripped = stripped.rstrip("\n") + "\n"
    return stripped.rstrip("\n") + "\n"


def latest_document(
    root: Path,
    scope: str,
    *,
    project_id: Optional[str] = None,
    kind: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> Optional[ExecDocument]:
    """Latest consolidated state query: the highest-numbered document in the
    scope that is not itself superseded (optionally by kind/execution)."""
    root = Path(root)
    directory = scope_dir(root, scope, project_id)
    if not directory.is_dir():
        return None
    best: Optional[Tuple[int, ExecDocument]] = None
    for candidate in directory.glob("EXEC_*.md"):
        match = DOC_NAME_RE.match(candidate.name)
        if not match:
            continue
        doc = parse_document(candidate.read_text(encoding="utf-8"))
        if "\n> Superseded by " in candidate.read_text(encoding="utf-8"):
            continue
        if kind is not None and doc.kind != kind:
            continue
        if execution_id is not None and doc.execution_id != execution_id:
            continue
        number = int(match.group(1))
        if best is None or number > best[0]:
            best = (number, doc)
    return best[1] if best else None


def list_documents(
    root: Path, scope: str, project_id: Optional[str] = None
) -> List[ExecDocument]:
    directory = scope_dir(root, scope, project_id)
    docs: List[Tuple[int, ExecDocument]] = []
    if not directory.is_dir():
        return []
    for candidate in directory.glob("EXEC_*.md"):
        match = DOC_NAME_RE.match(candidate.name)
        if match:
            docs.append((int(match.group(1)), parse_document(candidate.read_text(encoding="utf-8"))))
    return [d for _, d in sorted(docs)]


# ---------------------------------------------------------------------------
# Index rebuild / divergence check (§5: "rebuilt from the ledger and diffed")
# ---------------------------------------------------------------------------


def rebuild_index(root: Path, scope: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Recompute the scope index purely from the files on disk."""
    directory = scope_dir(root, scope, project_id)
    superseded: Dict[str, str] = {}
    documents: Dict[str, Any] = {}
    numbers = _scan_existing_numbers(directory)
    for number in numbers:
        doc_id = f"EXEC_{number:04d}"
        doc = parse_document((directory / f"{doc_id}.md").read_text(encoding="utf-8"))
        documents[doc_id] = {
            "file": f"{doc_id}.md",
            "kind": doc.kind,
            "execution_id": doc.execution_id,
            "created_at": doc.created_at,
            "content_sha256": doc.content_sha256,
            "supersedes": doc.supersedes,
            "superseded_by": None,
        }
        if doc.supersedes:
            superseded[doc.supersedes] = doc_id
    for old_id, new_id in superseded.items():
        if old_id in documents:
            documents[old_id]["superseded_by"] = new_id
    return {
        "scope": scope,
        "project_id": project_id,
        "next_number": (max(numbers) + 1) if numbers else 1,
        "documents": documents,
    }


def verify_index(root: Path, scope: str, project_id: Optional[str] = None) -> List[str]:
    """Diff the stored index against a from-files rebuild. Divergence ⇒ the
    caller must treat the stage close as BLOCKED (§5)."""
    stored = load_index(root, scope, project_id)
    rebuilt = rebuild_index(root, scope, project_id)
    issues: List[str] = []
    if int(stored.get("next_number", 1)) < int(rebuilt["next_number"]):
        issues.append("stored next_number regresses below existing files")
    stored_docs = stored.get("documents", {})
    rebuilt_docs = rebuilt.get("documents", {})
    for doc_id, row in rebuilt_docs.items():
        stored_row = stored_docs.get(doc_id)
        if stored_row is None:
            issues.append(f"{doc_id} exists on disk but is missing from the index")
        elif stored_row.get("content_sha256") != row["content_sha256"]:
            issues.append(f"{doc_id} content hash differs between index and disk")
    for doc_id in stored_docs:
        if doc_id not in rebuilt_docs:
            issues.append(f"{doc_id} is indexed but no file exists")
    return issues


# ---------------------------------------------------------------------------
# Latest consolidated state
# ---------------------------------------------------------------------------


def consolidated_state(root: Path, project_id: str) -> Dict[str, Any]:
    """Merge snapshots + ledgers + documents into one operational view (§5)."""
    root = Path(root)
    executions: Dict[str, Any] = {}

    def entry_for(exec_id: str) -> Dict[str, Any]:
        return executions.setdefault(
            exec_id,
            {
                "execution_id": exec_id,
                "task_id": None,
                "agent_id": None,
                "snapshots": [],
                "latest_snapshot": None,
                "ledger": None,
                "terminal": False,
                "resumed_from": None,
                "documents": [],
            },
        )

    for row in list_snapshots(root, project_id):
        snap = load_snapshot(row.path)
        entry = entry_for(snap.execution_id)
        entry["task_id"] = entry["task_id"] or snap.task_id
        entry["agent_id"] = entry["agent_id"] or snap.agent_id
        entry["snapshots"].append(
            {"snapshot_id": snap.snapshot_id, "path": str(row.path.relative_to(root))}
        )
        entry["latest_snapshot"] = {
            "snapshot_id": snap.snapshot_id,
            "path": str(row.path.relative_to(root)),
            "snapshot_hash": snap.snapshot_hash,
            "created_at": snap.created_at,
            "reason": snap.reason.value if hasattr(snap.reason, "value") else str(snap.reason),
            "eligible": snap.resume_eligibility.eligible,
        }

    ledger_dir = root / "projects" / project_id / "execution" / "ledger"
    if ledger_dir.is_dir():
        for candidate in sorted(ledger_dir.glob("LEDGER-*.jsonl")):
            try:
                records = read_records(candidate)
            except LedgerError:
                records = []
            if not records:
                continue
            entry = entry_for(records[0].execution_id)
            entry["ledger"] = {
                "path": str(candidate.relative_to(root)),
                "count": len(records),
                "head_hash": records[-1].record_hash,
            }
            entry["terminal"] = any(e.event_type == "EXECUTION_TERMINAL" for e in records)
            opened = next((e for e in records if e.event_type == "EXECUTION_OPENED"), None)
            if opened and opened.payload.get("resumed_from"):
                entry["resumed_from"] = opened.payload["resumed_from"]

    directory = scope_dir(root, SCOPE_OPERATIONAL, project_id)
    if directory.is_dir():
        for candidate in sorted(directory.glob("EXEC_*.md")):
            if not DOC_NAME_RE.match(candidate.name):
                continue
            doc = parse_document(candidate.read_text(encoding="utf-8"))
            if doc.execution_id in executions:
                executions[doc.execution_id]["documents"].append(doc.doc_id)

    return {
        "project_id": project_id,
        "generated_at": utc_now_stamp(),
        "executions": dict(sorted(executions.items())),
    }


def render_state_markdown(state: Dict[str, Any]) -> str:
    # Note: state['generated_at'] is deliberately NOT rendered. The document
    # metadata's created_at carries the time; keeping volatile timestamps out
    # of the body makes write_state_document idempotent while state is stable.
    lines = [
        f"# Consolidated operational state — {state['project_id']}",
        "",
        f"- executions: {len(state['executions'])}",
        "",
        "| execution | task | latest snapshot | ledger records | terminal | resumed_from | documents |",
        "|---|---|---|---|---|---|---|",
    ]
    for exec_id, entry in state["executions"].items():
        snapshot = entry.get("latest_snapshot") or {}
        ledger = entry.get("ledger") or {}
        lines.append(
            "| {eid} | {task} | {snap} | {count} | {terminal} | {resumed} | {docs} |".format(
                eid=exec_id,
                task=entry.get("task_id") or "—",
                snap=snapshot.get("snapshot_id", "—"),
                count=ledger.get("count", 0),
                terminal="yes" if entry.get("terminal") else "no",
                resumed=entry.get("resumed_from") or "—",
                docs=", ".join(entry.get("documents", [])) or "—",
            )
        )
    return "\n".join(lines) + "\n"


def write_state_document(
    root: Path,
    project_id: str,
    *,
    agent_id: str,
    stamp: Optional[str] = None,
) -> ExecDocument:
    """Commit the latest consolidated state as a ``kind: state`` document,
    superseding the previous state document when the state has changed."""
    root = Path(root)
    state = consolidated_state(root, project_id)
    body = render_state_markdown(state)
    previous = latest_document(root, SCOPE_OPERATIONAL, project_id=project_id, kind="state")
    if previous is not None and previous.content_sha256 == sha256_text(body):
        return previous  # state unchanged; current document stays canonical
    return create_document(
        root,
        SCOPE_OPERATIONAL,
        kind="state",
        agent_id=agent_id,
        project_id=project_id,
        title=f"Consolidated state {project_id}",
        body=body,
        supersedes=previous.doc_id if previous else None,
        status="CURRENT",
        stamp=stamp,
    )


__all__ = [
    "BODY_SEPARATOR",
    "DOC_KINDS",
    "DocumentError",
    "ExecDocument",
    "SCOPE_NORMATIVE",
    "SCOPE_OPERATIONAL",
    "allocate_doc_id",
    "consolidated_state",
    "create_document",
    "index_path",
    "latest_document",
    "list_documents",
    "load_document",
    "load_index",
    "parse_document",
    "rebuild_index",
    "render_document",
    "render_state_markdown",
    "scope_dir",
    "verify_document",
    "verify_index",
    "write_state_document",
]
