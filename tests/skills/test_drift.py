"""Drift tests: six dimensions, approval handling, CLI exit codes."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills.drift import (  # noqa: E402
    DriftError,
    DriftFinding,
    DriftVerdict,
    baseline_from_entry,
    check_directory,
    classify,
    detect_drift,
    snapshot_dir,
)

FIXTURES = ROOT / "tests" / "fixtures" / "skills"
VALID_SKILL = FIXTURES / "valid-skill"
REGISTRY_FIXTURE = FIXTURES / "registry.json"


def baseline():
    return {
        "version": "1.0.0",
        "files": {"SKILL.md": "sha256:" + "a" * 64},
        "content": {"SKILL.md": "original body"},
        "permissions": {"AG-008": "ask"},
        "metadata": {"description": "original description"},
        "dependencies": ["requests==2.31.0"],
    }


def kinds(report):
    return {f.kind for f in report.findings}


def test_snapshot_is_deterministic_and_complete():
    first = snapshot_dir(VALID_SKILL)
    second = snapshot_dir(VALID_SKILL)
    assert first == second
    assert set(first) == {"version", "files", "content", "permissions", "metadata", "dependencies"}
    assert "SKILL.md" in first["files"]
    assert first["files"]["SKILL.md"].startswith("sha256:")
    assert isinstance(first["version"], str)


def test_checked_in_ci_baseline_matches_fixture_skill():
    """The baseline consumed by .github/workflows/skills-validation.yml."""
    baseline_path = FIXTURES / "drift-baseline.json"
    assert baseline_path.is_file()
    approved = json.loads(baseline_path.read_text(encoding="utf-8"))
    report = check_directory(VALID_SKILL, approved)
    assert report.verdict == DriftVerdict.PASS.value, report.to_dict()


def test_clean_snapshot_passes():
    snapshot = snapshot_dir(VALID_SKILL)
    report = detect_drift(snapshot, copy.deepcopy(snapshot))
    assert report.verdict == DriftVerdict.PASS.value
    assert report.findings == []
    assert report.ok is True
    assert report.blocked is False


def test_unapproved_version_change_blocks():
    current = baseline()
    current["version"] = "1.1.0"
    report = detect_drift(baseline(), current)
    assert report.verdict == DriftVerdict.BLOCKED.value
    assert "version" in kinds(report)
    assert report.ok is False


def test_approved_version_change_is_an_observation():
    current = baseline()
    current["version"] = "1.1.0"
    approvals = [{"kind": "version", "from": "1.0.0", "to": "1.1.0", "approved_by": "ADR-008"}]
    report = detect_drift(baseline(), current, approvals=approvals)
    assert report.verdict == DriftVerdict.PASS_WITH_OBSERVATIONS.value
    assert report.findings[0].approved is True
    assert report.findings[0].approved_by == "ADR-008"

    string_form = detect_drift(baseline(), current, approvals=["version:version:1.0.0->1.1.0"])
    assert string_form.verdict == DriftVerdict.PASS_WITH_OBSERVATIONS.value


def test_all_six_dimensions_are_detected():
    before = baseline()
    after = copy.deepcopy(before)
    after["version"] = "2.0.0"
    after["files"]["SKILL.md"] = "sha256:" + "b" * 64
    after["content"]["SKILL.md"] = "modified body"
    after["permissions"]["AG-008"] = "allow"
    after["metadata"]["description"] = "modified description"
    after["dependencies"] = ["requests==2.32.0", "new-lib==1.0.0"]

    report = detect_drift(before, after)
    assert kinds(report) == {
        "version", "hash", "content", "permission", "metadata", "dependency"
    }
    assert report.verdict == DriftVerdict.BLOCKED.value
    assert len(report.findings) == 7  # dependency has two entries


def test_content_edit_on_disk_blocks_then_approves():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "valid-skill"
        shutil.copytree(VALID_SKILL, target)
        approved_baseline = snapshot_dir(target)

        skill_md = target / "SKILL.md"
        skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nDrifted line.\n", encoding="utf-8")

        blocked = check_directory(target, approved_baseline)
        assert blocked.verdict == DriftVerdict.BLOCKED.value
        assert "hash" in kinds(blocked)
        assert "content" in kinds(blocked)

        approved = check_directory(
            target,
            approved_baseline,
            approvals=["hash:*", "content:*"],
        )
        assert approved.verdict == DriftVerdict.PASS_WITH_OBSERVATIONS.value


def test_permission_metadata_and_dependency_drift():
    before = baseline()
    after = copy.deepcopy(before)
    after["permissions"] = {"AG-008": "deny"}
    after["metadata"] = {"description": "original description", "license": "MIT"}
    after["dependencies"] = {"requests": "2.31.0"}

    report = detect_drift(before, after)
    assert "permission" in kinds(report)
    assert "metadata" in kinds(report)
    # Mapping and list forms normalize to the same values: no dependency drift.
    assert "dependency" not in kinds(report)


def test_baseline_from_registry_entry():
    data = json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8"))
    snapshot = baseline_from_entry(data["skills"][0])
    assert snapshot["version"] == "0.1.0#0"
    assert snapshot["files"] == data["skills"][0]["integrity"]["file_hashes"]
    assert snapshot["metadata"]["lifecycle"] == "CANDIDATE"
    assert snapshot["dependencies"] == []


def test_classify_precedence():
    assert classify([]) == DriftVerdict.PASS.value
    assert classify([DriftFinding("version", "version", "1", "2", "ADR-1")]) == DriftVerdict.PASS_WITH_OBSERVATIONS.value
    assert classify([DriftFinding("version", "version", "1", "2")]) == DriftVerdict.BLOCKED.value


def test_invalid_snapshot_fails_closed():
    try:
        detect_drift([], {})
    except DriftError:
        pass
    else:
        raise AssertionError("non-object baseline was accepted")

    try:
        snapshot_dir(Path(tempfile.gettempdir()) / "definitely-missing-skill-dir")
    except DriftError:
        pass
    else:
        raise AssertionError("missing skill directory was accepted")


def test_cli_exit_codes_for_clean_and_drifted_snapshots():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "orchestration.skills.drift"]

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        clean_path = root / "clean.json"
        clean_path.write_text(json.dumps(snapshot_dir(VALID_SKILL)), encoding="utf-8")
        clean = subprocess.run(cmd + ["--baseline", str(clean_path), "--current", str(clean_path)],
                               cwd=ROOT, env=env, capture_output=True, text=True)
        assert clean.returncode == 0, clean.stderr
        assert json.loads(clean.stdout)["verdict"] == "PASS"

        changed = json.loads(clean_path.read_text(encoding="utf-8"))
        changed["version"] = "9.9.9"
        changed_path = root / "changed.json"
        changed_path.write_text(json.dumps(changed), encoding="utf-8")
        drifted = subprocess.run(cmd + ["--baseline", str(clean_path), "--current", str(changed_path)],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
        assert drifted.returncode == 2
        assert json.loads(drifted.stdout)["verdict"] == "BLOCKED"

        bad_path = root / "bad.json"
        bad_path.write_text("[]", encoding="utf-8")
        bad = subprocess.run(cmd + ["--baseline", str(bad_path), "--current", str(clean_path)],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        assert bad.returncode == 1
        assert json.loads(bad.stdout)["verdict"] == "FAIL"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
