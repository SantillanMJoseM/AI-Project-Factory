"""Skill task-contract tests: schema fields, safety rules TC-1..TC-6, file IO."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills.task_contract import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    REQUIRED_FIELDS,
    TaskContract,
    TaskContractError,
    validate_contract,
)


def contract():
    return {
        "contract_id": "TC-0001",
        "skill": "valid-skill",
        "version": "0.1.0",
        "executor_agent": "AG-008",
        "objective": "Validate the skill task contract runtime",
        "inputs": ["tests/fixtures/skills/registry.json"],
        "authorized_files": ["orchestration/skills/task_contract.py"],
        "allowed_tools": ["read"],
        "restrictions": ["no network"],
        "expected_result": "A validated contract report with ok=true",
        "acceptance_criteria": ["validate_contract returns ok=True", "no SCHEMA issues"],
        "evidence": ["G3"],
    }


def codes(report):
    return [i.code for i in report.issues]


def test_schema_declares_all_formal_fields():
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["additionalProperties"] is False
    assert schema["required"] == list(REQUIRED_FIELDS)
    for field in REQUIRED_FIELDS:
        assert field in schema["properties"]
    assert schema["properties"]["skill"]["$ref"] == "#/$defs/skillId"
    assert schema["properties"]["executor_agent"]["$ref"] == "#/$defs/agentId"


def test_valid_contract_passes_and_roundtrips():
    data = contract()
    report = validate_contract(data)
    assert report.ok, report.to_dict()
    assert report.issues == []

    materialized = TaskContract.from_dict(data)
    assert materialized.to_dict() == data
    assert materialized.validate().ok is True


def test_missing_required_fields_are_reported():
    data = contract()
    del data["evidence"]
    del data["authorized_files"]
    report = validate_contract(data)
    assert not report.ok
    assert "SCHEMA" in codes(report)
    assert any("evidence" in i.message for i in report.issues)
    assert any("authorized_files" in i.message for i in report.issues)


def test_unknown_field_is_rejected():
    data = contract()
    data["unauthorized_field"] = "surprise"
    report = validate_contract(data)
    assert not report.ok
    assert any("unexpected property" in i.message for i in report.issues)


def test_tc1_executor_agent_must_be_verified_factory_agent():
    data = contract()
    data["executor_agent"] = "AG-999"
    report = validate_contract(data)
    assert "TC-1" in codes(report)


def test_tc2_authorized_files_must_be_safe_relative_paths():
    for unsafe in ("/etc/passwd", "../secrets.txt", "docs/../../.env", ".env", "C:\\secret"):
        data = contract()
        data["authorized_files"] = [unsafe]
        report = validate_contract(data)
        assert "TC-2" in codes(report), "unsafe path accepted: %s" % unsafe

    data = contract()
    data["authorized_files"] = ["docs/guides/guide.md"]
    assert validate_contract(data).ok is True


def test_tc3_restricted_tool_requires_approval_restriction():
    data = contract()
    data["allowed_tools"] = ["read", "shell"]
    report = validate_contract(data)
    assert "TC-3" in codes(report)

    data["restrictions"] = ["requires human approval before shell use"]
    assert "TC-3" not in codes(validate_contract(data))


def test_tc4_placeholders_and_blank_entries_are_rejected():
    data = contract()
    data["objective"] = "TBD"
    data["acceptance_criteria"] = ["   "]
    report = validate_contract(data)
    assert "TC-4" in codes(report)


def test_tc5_skill_id_and_pinned_version_are_required():
    data = contract()
    data["skill"] = "Bad ID!"
    data["version"] = "latest"
    report = validate_contract(data)
    assert "SCHEMA" in codes(report)
    assert "TC-5" in codes(report)


def test_tc6_acceptance_criteria_required_evidence_is_observation():
    data = contract()
    data["acceptance_criteria"] = []
    report = validate_contract(data)
    assert not report.ok
    assert "TC-6" in codes(report)

    data = contract()
    data["evidence"] = []
    report = validate_contract(data)
    assert report.ok is True
    assert "TC-6" in [i.code for i in report.warnings]


def test_load_contract_from_file():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "contract.json"
        path.write_text(json.dumps(contract()), encoding="utf-8")
        loaded = TaskContract.load(path)
        assert loaded.contract_id == "TC-0001"
        assert loaded.validate().ok is True


def test_from_dict_rejects_unmaterializable_payload():
    try:
        TaskContract.from_dict({"inputs": 7})
    except TaskContractError as exc:
        assert "cannot materialize" in str(exc)
    else:
        raise AssertionError("unmaterializable payload was accepted")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
