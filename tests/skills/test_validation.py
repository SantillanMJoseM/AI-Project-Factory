"""Validation tests: JSON Schema, Plane A frontmatter, V-1/V-3, X-1..X-12."""

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills import (  # noqa: E402
    Registry,
    effective_autoinvoke,
    parse_frontmatter,
    validate_frontmatter,
    validate_json_schema,
    validate_plane_a,
    validate_registry,
    validate_skill_directory,
)
from orchestration.skills.validator import load_schema  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "skills"
REGISTRY_FIXTURE = FIXTURES / "registry.json"
VALID_SKILL = FIXTURES / "valid-skill"
INVALID_SKILL = FIXTURES / "invalid-skill"


def data():
    return json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8"))


def codes(report):
    return [i.code for i in report.issues]


def test_schema_file_is_valid_and_has_expected_defs():
    schema = load_schema()
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert "entry" in schema["$defs"]
    assert "sha256" in schema["$defs"]


def test_valid_fixture_registry_passes_all_checks():
    report = validate_registry(Registry.load(REGISTRY_FIXTURE))
    assert report.ok, report.to_dict()
    assert report.issues == []


def test_schema_rejects_bad_id_and_missing_field():
    bad_id = data()
    bad_id["skills"][0]["skill_id"] = "Bad ID!"
    report = validate_registry(bad_id)
    assert not report.ok
    assert "SCHEMA" in codes(report)

    missing = data()
    del missing["skills"][0]["permissions"]
    report = validate_registry(missing)
    assert not report.ok
    assert any("permissions" in i.message for i in report.errors)


def test_x3_license_exposure_blocks_activation():
    agpl = data()
    row = agpl["skills"][0]
    row["license"]["scope"] = "per-file-verified"
    row["license"]["spdx"] = "AGPL-3.0-only"
    row["lifecycle"] = "ACTIVE"
    row["enabled_in"] = [".opencode/skills/valid-skill"]
    assert "X-3" in codes(validate_registry(agpl))

    unverified = data()
    row = unverified["skills"][0]
    row["lifecycle"] = "APPROVED"
    row["license"]["scope"] = "repo-level-claim"
    assert "X-3" in codes(validate_registry(unverified))


def test_x2_lifecycle_enablement_and_permission_guards():
    staged = data()
    row = staged["skills"][0]
    row["lifecycle"] = "STAGED"
    row["enabled_in"] = [".opencode/skills/valid-skill"]
    assert "X-2" in codes(validate_registry(staged))

    candidate = data()
    candidate["skills"][0]["enabled_in"] = [".opencode/skills/valid-skill"]
    assert "X-2" in codes(validate_registry(candidate))

    suspended = data()
    row = suspended["skills"][0]
    row["lifecycle"] = "SUSPENDED"
    row["permissions"]["per_agent_overrides"] = {"AG-008": "allow"}
    assert "X-2" in codes(validate_registry(suspended))


def test_x4_verdict_guards():
    d = data()
    row = d["skills"][0]
    row["lifecycle"] = "APPROVED"
    row["verdicts"]["compatibility"]["verdict"] = "COMPATIBLE"
    row["verdicts"]["compatibility"]["row"] = "adr"
    row["verdicts"]["security"]["verdict"] = "ACCEPT"
    row["verdicts"]["behavior_review"]["verdict"] = "FAIL"
    assert "X-4" in codes(validate_registry(d))

    held = data()
    row = held["skills"][0]
    row["lifecycle"] = "APPROVED"
    row["verdicts"]["security"]["verdict"] = "HOLD"
    assert "X-4" in codes(validate_registry(held))


def test_x7_provenance_guards():
    vendored = data()
    row = vendored["skills"][0]
    row["source"]["type"] = "vendored-upstream"
    row["versioning"]["upstream_pin"] = "wshobson@4220308"
    assert "X-7" in codes(validate_registry(vendored))

    adapted = data()
    row = adapted["skills"][0]
    row["source"]["type"] = "adapted"
    assert "X-7" in codes(validate_registry(adapted))


def test_x8_risk_class_and_loosening_guards():
    mismatch = data()
    mismatch["skills"][0]["permissions"]["risk_class"] = "B"
    assert "X-8" in codes(validate_registry(mismatch))

    loosened = data()
    row = loosened["skills"][0]
    row["lifecycle"] = "ACTIVE"
    row["enabled_in"] = [".opencode/skills/valid-skill"]
    row["verdicts"]["security"]["risk_class"] = "B"
    row["permissions"]["risk_class"] = "B"
    row["permissions"]["rule"] = "allow"  # class B default is ask
    assert "X-8" in codes(validate_registry(loosened))


def test_x9_and_x11_guards():
    d = data()
    row = d["skills"][0]
    row["lifecycle"] = "STAGED"
    row["enabled_in"] = [".claude/skills/valid-skill"]
    report = validate_registry(d)
    assert "X-9" in codes(report)

    bad_agent = data()
    bad_agent["skills"][0]["assignment"]["agents"] = ["AG-999"]
    assert "X-11" in codes(validate_registry(bad_agent))


def test_v3_detects_silent_resurrection():
    d = data()
    d["skills"][0]["lifecycle"] = "STAGED"
    d["skills"][0]["enabled_in"] = [".opencode/skills/valid-skill"]
    second = copy.deepcopy(d["skills"][0])
    second["skill_id"] = "second-skill"
    second["library_path"] = "skills-library/shared/second-skill"
    d["skills"].append(second)
    report = validate_registry(d)
    assert "V-3" in codes(report)
    assert any("silent resurrection" in i.message for i in report.errors)


def test_frontmatter_valid_and_invalid_fixtures():
    valid = parse_frontmatter((VALID_SKILL / "SKILL.md").read_text(encoding="utf-8"))
    assert valid["description"].strip()
    assert effective_autoinvoke(valid) is False
    assert validate_frontmatter(valid).ok

    report = validate_frontmatter(parse_frontmatter((INVALID_SKILL / "SKILL.md").read_text(encoding="utf-8")))
    assert not report.ok
    assert any("allowed_tools" in i.message for i in report.errors)


def test_validate_skill_directory_structure_and_references():
    assert validate_skill_directory(VALID_SKILL, expected_id="valid-skill").ok
    invalid = validate_skill_directory(INVALID_SKILL, expected_id="invalid-skill")
    assert not invalid.ok
    assert "V-2" in codes(invalid)
    wrong_id = validate_skill_directory(VALID_SKILL, expected_id="other-id")
    assert "V-1" in codes(wrong_id)


def test_plane_a_autoinvoke_crosscheck_and_both_flags():
    assert validate_plane_a(VALID_SKILL / "SKILL.md", False).ok
    assert "X-10" in codes(validate_plane_a(VALID_SKILL / "SKILL.md", True))

    with tempfile.TemporaryDirectory() as td:
        skill = Path(td) / "both-flags"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: Both\ndescription: Both flags present.\nmetadata:\n"
            "  opencode:\n    autoinvoke: false\n    disable-model-invocation: false\n---\nbody\n",
            encoding="utf-8",
        )
        report = validate_plane_a(skill / "SKILL.md", False)
        assert report.ok
        assert any(i.severity == "warning" for i in report.issues)
        assert effective_autoinvoke(parse_frontmatter((skill / "SKILL.md").read_text())) is False


def test_validate_registry_with_repo_root_detects_hash_drift():
    reg = Registry.load(REGISTRY_FIXTURE)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "skills-library" / "shared" / "valid-skill"
        shutil.copytree(VALID_SKILL, target)
        assert validate_registry(reg, repo_root=root).ok
        skill_md = target / "SKILL.md"
        skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nDrifted line.\n", encoding="utf-8")
        report = validate_registry(reg, repo_root=root)
        assert not report.ok
        assert any("hash mismatch" in i.message for i in report.errors)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
