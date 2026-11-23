"""Rollback tests (T-3): kill-switch, artifact removal, row retention, V-3 re-check."""

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills import Registry, RegistryError, validate_registry  # noqa: E402

REGISTRY_FIXTURE = ROOT / "tests" / "fixtures" / "skills" / "registry.json"


def active_registry():
    reg = Registry.load(REGISTRY_FIXTURE)
    for state in ("REVIEWED", "APPROVED", "STAGED", "ACTIVE"):
        reg.transition("valid-skill", state, actor="AG-008")
    return reg


def test_rollback_sets_suspended_deny_and_clears_artifact():
    reg = active_registry()
    entry = reg.rollback("valid-skill", actor="AG-008", reason="adverse finding")
    assert entry.lifecycle == "SUSPENDED"
    assert entry.permissions.rule == "deny"
    assert entry.enabled_in == []
    assert entry.versioning.history[-1].event == "suspended"
    assert "adverse finding" in entry.versioning.history[-1].evidence
    assert validate_registry(reg).ok


def test_rollback_keeps_row_and_appends_history_only():
    reg = active_registry()
    before = copy.deepcopy(reg.get("valid-skill").versioning.history)
    ids_before = reg.skill_ids()
    reg.rollback("valid-skill", actor="AG-008")
    entry = reg.get("valid-skill")
    assert reg.skill_ids() == ids_before  # rows are never deleted
    assert entry.versioning.history[: len(before)] == before
    assert len(entry.versioning.history) == len(before) + 1


def test_rollback_derives_deny_even_with_hidden_overrides():
    reg = active_registry()
    entry = reg.get("valid-skill")
    entry.permissions.per_agent_overrides = {"AG-008": "allow"}
    reg.rollback("valid-skill", actor="AG-008")
    cfg = reg.derive_permissions()
    rules = cfg["agents"]["AG-008"]["permissions"]["skill"]
    assert rules[-1] == {"action": "deny", "pattern": "valid-skill"}
    assert reg.effective_rule(reg.get("valid-skill"), "AG-008") == "deny"


def test_rollback_from_every_pre_retired_state():
    for state in ("CANDIDATE", "REVIEWED", "APPROVED", "STAGED", "ACTIVE"):
        reg = Registry.load(REGISTRY_FIXTURE)
        if state != "CANDIDATE":
            for target in ("REVIEWED", "APPROVED", "STAGED", "ACTIVE"):
                reg.transition("valid-skill", target)
                if target == state:
                    break
        entry = reg.rollback("valid-skill", actor="AG-008")
        assert entry.lifecycle == "SUSPENDED"
        assert entry.permissions.rule == "deny"
        assert validate_registry(reg).ok


def test_rollback_of_retired_row_is_rejected():
    reg = active_registry()
    reg.transition("valid-skill", "RETIRED", actor="AG-008")
    try:
        reg.rollback("valid-skill", actor="AG-008")
    except RegistryError as exc:
        assert "RETIRED" in str(exc)
    else:
        raise AssertionError("rolling back a RETIRED row must be refused")


def test_rollback_resolves_duplicate_enablement_without_resurrection():
    data = json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8"))
    row = data["skills"][0]
    row["lifecycle"] = "STAGED"
    row["enabled_in"] = [".opencode/skills/valid-skill"]
    row["permissions"]["rule"] = "ask"
    row["verdicts"]["compatibility"]["verdict"] = "COMPATIBLE"
    row["verdicts"]["compatibility"]["row"] = "adr"
    row["verdicts"]["security"]["verdict"] = "ACCEPT"
    row["verdicts"]["behavior_review"]["verdict"] = "PASS"
    second = copy.deepcopy(row)
    second["skill_id"] = "second-skill"
    second["library_path"] = "skills-library/shared/second-skill"
    data["skills"].append(second)

    assert any(i.code == "V-3" for i in validate_registry(data).issues)
    reg = Registry.from_dict(data)
    # Roll back the colliding copy; the canonical row keeps its valid path.
    reg.rollback("second-skill", actor="AG-008", reason="precedence cleanup")
    report = validate_registry(reg)
    assert not any(i.code == "V-3" for i in report.issues), report.to_dict()
    assert report.ok, report.to_dict()
    assert reg.get("valid-skill").lifecycle == "STAGED"


def test_cli_rollback_writes_updated_registry():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    with tempfile.TemporaryDirectory() as td:
        source = Path(td) / "registry.json"
        out = Path(td) / "rolled-back.json"
        source.write_text(json.dumps(active_registry().to_dict()), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "orchestration.skills.cli", "rollback", "--registry", str(source),
             "--skill-id", "valid-skill", "--output", str(out), "--actor", "AG-008", "--reason", "cli test"],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        updated = Registry.load(out)
        assert updated.get("valid-skill").lifecycle == "SUSPENDED"
        assert updated.get("valid-skill").permissions.rule == "deny"
        assert json.loads(source.read_text())["skills"][0]["lifecycle"] == "ACTIVE"  # input untouched


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
