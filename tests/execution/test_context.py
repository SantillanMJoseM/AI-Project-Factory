"""Dynamic Context Manager tests: tiers, budgeting, staleness, resume rebuild."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.execution.context import (  # noqa: E402
    ContextError,
    assemble_context,
    check_staleness,
    context_dir,
    find_manifest_by_hash,
    load_manifest,
    manifest_id_for,
)
from orchestration.execution.ledger import Ledger, ledger_path  # noqa: E402
from orchestration.execution.models import (  # noqa: E402
    T0_BOOTSTRAP_FILES,
    TIER_T0,
    TIER_T1,
    TIER_T2,
    TIER_T3,
    Staleness,
)
from orchestration.execution.snapshot import create_snapshot  # noqa: E402

BOOTSTRAP = list(T0_BOOTSTRAP_FILES)


def make_repo(td):
    root = Path(td)
    for name in BOOTSTRAP:
        (root / name).write_text(name + "\n", encoding="utf-8")
    (root / "contracts").mkdir()
    (root / "contracts" / "api.md").write_text("contract v1\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("a\n", encoding="utf-8")
    (root / ".opencode" / "skills" / "hads").mkdir(parents=True)
    (root / ".opencode" / "skills" / "hads" / "SKILL.md").write_text("# hads\n", encoding="utf-8")
    return root


def assemble(root, **overrides):
    kwargs = dict(
        project_id="PROJECT-001",
        execution_id="EXEC-0001",
        task_refs=["contracts/api.md"],
        skills=[("hads", ".opencode/skills/hads/SKILL.md")],
        working_refs=["src/a.py"],
        stamp="2026-11-19T10:00:00Z",
    )
    kwargs.update(overrides)
    return assemble_context(root, **kwargs)


def test_tiers_and_self_hash():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        manifest = assemble(root)
        assert manifest.manifest_id == manifest_id_for("EXEC-0001", 1)
        assert [r.ref for r in manifest.tiers[TIER_T0]] == BOOTSTRAP  # read order kept
        assert [r.ref for r in manifest.tiers[TIER_T1]] == ["contracts/api.md"]
        assert manifest.tiers[TIER_T2][0].skill_id == "hads"
        assert manifest.tiers[TIER_T3][0].ref == "src/a.py"
        assert manifest.compute_hash() == manifest.manifest_hash
        stored = context_dir(root, "PROJECT-001") / (manifest.manifest_id + ".json")
        assert stored.is_file()
        reloaded = load_manifest(stored)  # verifies self-hash
        assert reloaded.manifest_id == manifest.manifest_id
        assert not manifest.validate()


def test_missing_bootstrap_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        (root / "PROJECT_MAP.md").unlink()
        try:
            assemble(root)
        except ContextError as exc:
            assert "PROJECT_MAP.md" in str(exc)
        else:
            raise AssertionError("missing T0 file was tolerated")


def test_missing_task_ref_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        try:
            assemble(root, task_refs=["contracts/ghost.md"])
        except ContextError:
            pass
        else:
            raise AssertionError("missing T1 reference was tolerated")


def test_budget_trims_recorded_not_silent():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        (root / "src" / "big1.py").write_text("x" * 4000 + "\n", encoding="utf-8")
        (root / "src" / "big2.py").write_text("y" * 4000 + "\n", encoding="utf-8")
        manifest = assemble(
            root, working_refs=["src/a.py", "src/big1.py", "src/big2.py"], token_budget=1500
        )
        kept = [r.ref for r in manifest.tiers[TIER_T3]]
        excluded = {x.ref: x.reason for x in manifest.excluded_for_budget}
        assert "src/a.py" in kept
        assert "src/big2.py" in excluded  # trimmed first (recency order)
        assert excluded["src/big2.py"] == "low-recency"
        assert manifest.compute_hash() == manifest.manifest_hash
        # impossible budget: assembly aborts rather than silently truncating T0/T1
        try:
            assemble(root, token_budget=1)
        except ContextError as exc:
            assert "budget" in str(exc)
        else:
            raise AssertionError("over-budget assembly silently succeeded")


def test_staleness_rules():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        manifest = assemble(root)
        report = check_staleness(root, manifest)
        assert report.staleness is Staleness.CURRENT and report.ok

        (root / "src" / "a.py").write_text("a-changed\n", encoding="utf-8")
        report = check_staleness(root, manifest)
        assert report.staleness is Staleness.STALE
        assert report.changed_refs == ["src/a.py"]
        assert report.ok  # stale, but not governed: re-assemble, resume may proceed

        (root / "contracts" / "api.md").write_text("contract v2 UNAPPROVED\n", encoding="utf-8")
        report = check_staleness(root, manifest)
        assert not report.ok  # governed content moved: execution may not run on this manifest
        assert report.governed_stale_refs == ["contracts/api.md"]


def test_manifest_lookup_by_hash():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        first = assemble(root)
        second = assemble(root)  # seq 2
        assert first.manifest_id != second.manifest_id
        found = find_manifest_by_hash(root, "PROJECT-001", first.manifest_hash)
        assert found.manifest_id == first.manifest_id
        try:
            find_manifest_by_hash(root, "PROJECT-001", "sha256:" + "0" * 64)
        except ContextError:
            pass
        else:
            raise AssertionError("unknown manifest hash resolved")


def test_rebuild_for_resume_requires_pinned_manifest():
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(td)
        manifest = assemble(root)
        ledger = Ledger.create(
            ledger_path(root, "PROJECT-001", "EXEC-0001"), "EXEC-0001", actor_agent="AG-008"
        )
        snapshot = create_snapshot(
            root,
            project_id="PROJECT-001",
            execution_id="EXEC-0001",
            task_id="TASK-0001",
            agent_id="AG-008",
            reason="periodic",
            files=["src/a.py"],
            context_manifest_hash=manifest.manifest_hash,
            ledger=ledger,
            stamp="2026-11-19T10:02:00Z",
        )
        from orchestration.execution.context import rebuild_for_resume

        found, report = rebuild_for_resume(root, "PROJECT-001", snapshot)
        assert found.manifest_hash == manifest.manifest_hash
        assert report.ok

        (root / "schemas").mkdir()
        (root / "schemas" / "x.schema.json").write_text("{}\n", encoding="utf-8")
        naked = create_snapshot(
            root,
            project_id="PROJECT-001",
            execution_id="EXEC-0002",
            task_id="TASK-0002",
            agent_id="AG-008",
            reason="periodic",
            files=["src/a.py"],
            stamp="2026-11-19T10:03:00Z",
        )
        try:
            rebuild_for_resume(root, "PROJECT-001", naked)
        except ContextError as exc:
            assert "context_manifest_hash" in str(exc)
        else:
            raise AssertionError("manifest-less snapshot reported resume-eligible")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
