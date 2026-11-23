"""Dynamic Context Manager — assemble, budget, freeze resumable context (Stage 2A).

Implements §4.1 and §6.2 of ``docs/execution/EXECUTION_ARCHITECTURE.md``:

* assembly tiers T0 (bootstrap, context-policy read order) → T1 (task) →
  T2 (skills) → T3 (working set); each entry is a *reference plus content
  hash*, never a copy of governed content;
* token budgeting by tier priority: trimming starts at T3, then T2; trimmed
  items are recorded in ``excluded_for_budget``, never silently dropped;
* staleness rule: every referenced file is fingerprinted at assembly; at
  consumption time hashes are re-checked. A stale contract, schema, policy,
  or gate makes the manifest unusable for execution (fail-closed);
* the manifest is the input contract of snapshots — persisted under
  ``projects/<ID>/execution/context/CTX-<EXEC-NNNN>-<seq>.json`` and pinned
  into snapshots by ``context_manifest_hash``.

Boundary: the DCM assembles; it authorizes nothing (§4.1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .models import (
    ContextManifest,
    ContextRef,
    ExcludedRef,
    ExecutionError,
    Staleness,
    T0_BOOTSTRAP_FILES,
    TIER_ORDER,
    TIER_T0,
    TIER_T1,
    TIER_T2,
    TIER_T3,
    canonical_json,
    hash_without,
    is_governed,
    sha256_file,
    utc_now_stamp,
)


class ContextError(ExecutionError):
    """Assembly or consumption failure in the DCM (fail-closed)."""


#: Cheap deterministic size estimate (chars/4); budgets are approximations,
#: hashes are not.
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def context_dir(repo_root: Path, project_id: str) -> Path:
    return Path(repo_root) / "projects" / project_id / "execution" / "context"


def manifest_id_for(execution_id: str, seq: int) -> str:
    return f"CTX-{execution_id}-{seq:04d}"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _fingerprint(repo_root: Path, rel: str) -> ContextRef:
    target = Path(rel)
    if not target.is_absolute():
        target = repo_root / target
    if not target.is_file():
        raise ContextError(f"context reference missing: {rel!r}")
    rel_norm = str(Path(rel))
    try:
        rel_norm = str(target.resolve().relative_to(Path(repo_root).resolve()))
    except ValueError:
        pass
    return ContextRef(ref=rel_norm.replace("\\", "/"), sha256=sha256_file(target))


def assemble_context(
    repo_root: Path,
    *,
    project_id: str,
    execution_id: str,
    task_refs: Sequence[str] = (),
    skills: Iterable[Tuple[str, str]] = (),
    working_refs: Sequence[str] = (),
    token_budget: Optional[int] = None,
    seq: Optional[int] = None,
    stamp: Optional[str] = None,
    persist: bool = True,
) -> ContextManifest:
    """Freeze the operational context for one execution as a hashed manifest.

    ``skills`` yields ``(skill_id, SKILL.md path)`` pairs. ``token_budget``
    trims T3 (oldest-first) then T2 (last-first); every trimmed item is
    recorded as excluded with a reason. Fail-closed: a missing T0 or T1
    reference aborts assembly.
    """
    repo_root = Path(repo_root)
    stamp = stamp or utc_now_stamp()

    t0: List[ContextRef] = []
    for rel in T0_BOOTSTRAP_FILES:
        candidate = repo_root / rel
        if not candidate.is_file():
            raise ContextError(f"T0 bootstrap file missing: {rel!r}")
        t0.append(_fingerprint(repo_root, rel))

    t1 = [_fingerprint(repo_root, rel) for rel in task_refs]
    t2: List[ContextRef] = []
    for skill_id, skill_path in skills:
        ref = _fingerprint(repo_root, skill_path)
        ref.skill_id = skill_id
        t2.append(ref)
    t3 = [_fingerprint(repo_root, rel) for rel in working_refs]

    excluded: List[ExcludedRef] = []
    if token_budget is not None:
        def tier_cost(refs: List[ContextRef]) -> int:
            total = 0
            for r in refs:
                p = repo_root / r.ref
                total += estimate_tokens(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else 0
            return total

        def _trim(refs: List[ContextRef], reason: str) -> None:
            while refs and _total_cost() > token_budget:
                dropped = refs.pop()  # last (least recent/relevant) first
                excluded.append(ExcludedRef(ref=dropped.ref, reason=reason))

        def _total_cost() -> int:
            return sum(map(tier_cost, (t0, t1, t2, t3)))

        _trim(t3, "low-recency")
        _trim(t2, "low-relevance")
        if _total_cost() > token_budget:
            # T0/T1 are mandatory: over-budget with no trimmable tier left is
            # an assembly failure, not a silent truncation.
            raise ContextError(
                f"context does not fit budget {token_budget} even after trimming T2/T3"
            )

    if seq is None:
        seq = len(list(context_dir(repo_root, project_id).glob("CTX-*.json"))) + 1 if persist else 1

    manifest = ContextManifest(
        manifest_id=manifest_id_for(execution_id, seq),
        execution_id=execution_id,
        assembled_at=stamp,
        tiers={TIER_T0: t0, TIER_T1: t1, TIER_T2: t2, TIER_T3: t3},
        excluded_for_budget=excluded,
        staleness=Staleness.CURRENT,
        manifest_hash="",
    )
    manifest.manifest_hash = manifest.compute_hash()
    issues = manifest.validate()
    if issues:
        raise ContextError("invalid context manifest: " + "; ".join(issues))

    if persist:
        directory = context_dir(repo_root, project_id)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (manifest.manifest_id + ".json")
        if target.exists():
            raise ContextError(f"context manifest already exists (append-only): {target}")
        target.write_text(canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Persistence / lookup
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> ContextManifest:
    path = Path(path)
    if not path.exists():
        raise ContextError(f"context manifest not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = ContextManifest.from_dict(data)
    except (ValueError, KeyError, TypeError) as exc:
        raise ContextError(f"{path}: bad context manifest: {exc}") from exc
    if hash_without(manifest.to_dict(), "manifest_hash") != manifest.manifest_hash:
        raise ContextError(f"{path}: manifest_hash does not match committed bytes")
    return manifest


def find_manifest_by_hash(
    repo_root: Path, project_id: str, manifest_hash: str
) -> ContextManifest:
    """Resolve the exact manifest a snapshot pinned (§4.3: rebuild from the
    snapshot manifest). Absent or unverifiable ⇒ fail closed."""
    directory = context_dir(Path(repo_root), project_id)
    if not directory.is_dir():
        raise ContextError("no context manifests stored for this project")
    for candidate in sorted(directory.glob("CTX-*.json")):
        manifest = load_manifest(candidate)  # verifies self-hash
        if manifest.manifest_hash == manifest_hash:
            return manifest
    raise ContextError(f"context manifest {manifest_hash!r} not found for {project_id}")


# ---------------------------------------------------------------------------
# Staleness (§4.1)
# ---------------------------------------------------------------------------


@dataclass
class StalenessReport:
    """Result of re-fingerprinting a manifest against the live repository."""

    manifest_id: str = ""
    staleness: Staleness = Staleness.CURRENT
    missing_refs: List[str] = field(default_factory=list)
    changed_refs: List[str] = field(default_factory=list)
    governed_stale_refs: List[str] = field(default_factory=list)
    ok: bool = True

    @property
    def may_run(self) -> bool:
        """An execution may not run on a manifest whose governed tier is stale."""
        return self.ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "staleness": self.staleness.value,
            "missing_refs": list(self.missing_refs),
            "changed_refs": list(self.changed_refs),
            "governed_stale_refs": list(self.governed_stale_refs),
            "ok": self.ok,
        }


def check_staleness(repo_root: Path, manifest: ContextManifest) -> StalenessReport:
    """Re-verify every referenced file's fingerprint (§4.1 staleness rule).

    Any divergence marks the manifest ``STALE`` and requires re-assembly; if
    the divergent file is a contract, schema, policy, or gate, the manifest
    is *not runnable* (fail-closed — DCM assembles, authorizes nothing).
    """
    repo_root = Path(repo_root)
    report = StalenessReport(manifest_id=manifest.manifest_id)
    for tier in TIER_ORDER:
        for ref in manifest.tiers.get(tier, []):
            target = repo_root / ref.ref
            if not target.is_file():
                report.missing_refs.append(ref.ref)
            elif sha256_file(target) != ref.sha256:
                report.changed_refs.append(ref.ref)
    stale = set(report.missing_refs) | set(report.changed_refs)
    if stale:
        report.staleness = Staleness.STALE
        report.governed_stale_refs = sorted(r for r in stale if is_governed(r))
        report.ok = not report.governed_stale_refs
    return report


def rebuild_for_resume(
    repo_root: Path, project_id: str, snapshot
) -> Tuple[ContextManifest, StalenessReport]:
    """Resume-time context rebuild: locate the pinned manifest, re-fingerprint.

    Returns the manifest and its staleness report; callers must treat
    ``report.ok == False`` as BLOCKED (§8 flow node G + staleness rule).
    """
    if not snapshot.context_manifest_hash:
        raise ContextError(
            f"snapshot {snapshot.snapshot_id} carries no context_manifest_hash; "
            "it is not resume-eligible (§4.1)"
        )
    manifest = find_manifest_by_hash(repo_root, project_id, snapshot.context_manifest_hash)
    if manifest.execution_id != snapshot.execution_id:
        raise ContextError("pinned manifest belongs to a different execution")
    return manifest, check_staleness(repo_root, manifest)


__all__ = [
    "ContextError",
    "ContextManifest",
    "StalenessReport",
    "assemble_context",
    "check_staleness",
    "context_dir",
    "estimate_tokens",
    "find_manifest_by_hash",
    "load_manifest",
    "manifest_id_for",
    "rebuild_for_resume",
]
