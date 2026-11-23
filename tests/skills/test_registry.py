"""Registry runtime tests: load/save, guards, transitions, derived permissions, CLI."""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills import Registry, RegistryError, render_permissions  # noqa: E402
from orchestration.skills.validator import check_derived_config  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "skills"
REGISTRY_FIXTURE = FIXTURES / "registry.json"


def fixture_data():
    return json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8"))


def make_entry(skill_id, **overrides):
    row = copy.deepcopy(fixture_data()["skills"][0])
    row["skill_id"] = skill_id
    row["library_path"] = "skills-library/shared/" + skill_id
    row["enabled_in"] = []
    row["assignment"] = {"agents": ["AG-008"], "scope": "factory-agents"}
    row.update(overrides)
    return row


def test_load_fixture_registry():
    reg = Registry.load(REGISTRY_FIXTURE)
    assert len(reg) == 1
    assert reg.skill_ids() == ["valid-skill"]
    assert reg.schema_version == "1.0"
    assert reg.get("valid-skill") is not None
    assert reg.get("missing") is None


def test_duplicate_id_rejected():
    reg = Registry.load(REGISTRY_FIXTURE)
    try:
        reg.add(copy.deepcopy(reg.get("valid-skill")))
    except RegistryError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate skill_id was accepted")


def test_transition_happy_path():
    reg = Registry.load(REGISTRY_FIXTURE)
    expected_rules = {
        "REVIEWED": "deny",
        "APPROVED": "deny",
        "STAGED": "ask",
        "ACTIVE": "allow",
    }
    for target, rule in expected_rules.items():
        entry = reg.transition("valid-skill", target, adr="ADR-007" if target == "APPROVED" else None, actor="AG-008")
        assert entry.lifecycle == target
        assert entry.permissions.rule == rule
    entry = reg.get("valid-skill")
    assert entry.enabled_in == [".opencode/skills/valid-skill"]
    assert len(entry.versioning.history) == 5
    assert entry.versioning.history[-1].event == "activated"
    assert entry.versioning.history[2].adr == "ADR-007"


def test_invalid_transition_is_blocked_without_mutation():
    reg = Registry.load(REGISTRY_FIXTURE)
    before = reg.get("valid-skill").to_dict()
    for bad in ("ACTIVE", "SUSPENDED_X"):
        try:
            reg.transition("valid-skill", bad)
        except (RegistryError, ValueError):
            pass
        else:
            raise AssertionError("illegal transition %s was accepted" % bad)
        assert reg.get("valid-skill").lifecycle == "CANDIDATE"
    try:
        reg.transition("valid-skill", "SUSPENDED")
        reg.transition("valid-skill", "REVIEWED")
    except RegistryError:
        pass
    else:
        raise AssertionError("SUSPENDED -> REVIEWED must be blocked (re-entry is CANDIDATE)")
    assert reg.get("valid-skill").to_dict()["versioning"]["history"][0] == before["versioning"]["history"][0]


def test_history_is_append_only():
    reg = Registry.load(REGISTRY_FIXTURE)
    original = list(reg.get("valid-skill").versioning.history)
    reg.transition("valid-skill", "REVIEWED")
    reg.transition("valid-skill", "APPROVED")
    reg.transition("valid-skill", "STAGED")
    history = reg.get("valid-skill").versioning.history
    assert history[: len(original)] == original
    assert [h.event.value for h in history] == [
        "registered", "re-audited", "adopted-via-ADR", "staged"
    ]


def test_derive_permissions_is_fail_closed():
    data = fixture_data()
    data["skills"] = [
        make_entry("skill-a", lifecycle="ACTIVE", enabled_in=[".opencode/skills/skill-a"]),
        make_entry("skill-b", lifecycle="ACTIVE", enabled_in=[".opencode/skills/skill-b"],
                   permissions={"risk_class": "B", "rule": "ask", "per_agent_overrides": {}, "autoinvoke": False},
                   verdicts=copy.deepcopy(data["skills"][0]["verdicts"])),
        make_entry("skill-c", lifecycle="ACTIVE", enabled_in=[".opencode/skills/skill-c"],
                   permissions={"risk_class": "C", "rule": "deny", "per_agent_overrides": {}, "autoinvoke": False}),
        make_entry("skill-d", lifecycle="STAGED", enabled_in=[".opencode/skills/skill-d"]),
        make_entry("skill-e", lifecycle="SUSPENDED", enabled_in=[".opencode/skills/skill-e"],
                   permissions={"risk_class": "A", "rule": "deny",
                                "per_agent_overrides": {"AG-008": "allow"}, "autoinvoke": False}),
    ]
    reg = Registry.from_dict(data)
    cfg = reg.derive_permissions()
    assert cfg["permissions"]["skill"] == "deny"
    rules = cfg["agents"]["AG-008"]["permissions"]["skill"]
    by_id = {r["pattern"]: r["action"] for r in rules}
    assert by_id == {
        "skill-a": "allow", "skill-b": "ask", "skill-c": "deny",
        "skill-d": "ask", "skill-e": "deny",
    }
    # Last match wins: the deny rule must be sorted last.
    assert rules[-1] == {"action": "deny", "pattern": "skill-e"}
    # A class-C default cannot be loosened by an override.
    c_entry = reg.get("skill-c")
    c_entry.permissions.per_agent_overrides = {"AG-008": "allow"}
    assert reg.effective_rule(c_entry, "AG-008") == "deny"


def test_save_load_roundtrip():
    reg = Registry.load(REGISTRY_FIXTURE)
    reg.transition("valid-skill", "REVIEWED")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "nested" / "registry.json"
        reg.save(path)
        again = Registry.load(path)
        assert again.to_dict() == reg.to_dict()


def test_cli_validate_permissions_and_check():
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(ROOT) + __import__("os").pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "orchestration.skills.cli"]

    validated = subprocess.run(cmd + ["validate", "--registry", str(REGISTRY_FIXTURE)], cwd=ROOT, env=env,
                               capture_output=True, text=True)
    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["ok"] is True

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "opencode.generated.json"
        rendered = subprocess.run(cmd + ["permissions", "--registry", str(REGISTRY_FIXTURE), "--output", str(out)],
                                  cwd=ROOT, env=env, capture_output=True, text=True)
        assert rendered.returncode == 0, rendered.stderr
        assert out.read_text(encoding="utf-8") == render_permissions(Registry.load(REGISTRY_FIXTURE))

        checked = subprocess.run(cmd + ["check-permissions", "--registry", str(REGISTRY_FIXTURE),
                                        "--config", str(out)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert checked.returncode == 0, checked.stderr
        assert json.loads(checked.stdout)["ok"] is True
        assert check_derived_config(Registry.load(REGISTRY_FIXTURE), out).ok

        out.write_text(out.read_text(encoding="utf-8").replace("deny", "allow"), encoding="utf-8")
        drifted = subprocess.run(cmd + ["check-permissions", "--registry", str(REGISTRY_FIXTURE),
                                        "--config", str(out)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert drifted.returncode == 1
        assert json.loads(drifted.stdout)["ok"] is False


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
