"""V5 license-control tests: identification, blocking, incompatibility, mixed,
attribution, redistribution and provenance."""

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.skills.license_check import (  # noqa: E402
    LicenseVerdict,
    check_license,
    check_skill_dir,
    classify,
    identify_license,
)
from orchestration.skills.license_check import Finding  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "skills"
REGISTRY_FIXTURE = FIXTURES / "registry.json"


def row():
    return copy.deepcopy(json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8"))["skills"][0])


def codes(report):
    return {f.code for f in report.findings}


def mit_record(**overrides):
    record = {
        "skill_id": "mit-skill",
        "license": {
            "scope": "per-file-verified",
            "spdx": "MIT",
            "notice_files": ["LICENSE"],
            "verified_by": "G3",
            "verified_at": "2026-11-19",
        },
        "source": {"type": "in-house", "cloned": "TBD"},
        "attribution": "Copyright (c) 2026 Example Author",
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(record.get(key), dict):
            record[key].update(value)
        else:
            record[key] = value
    return record


def test_identify_license_recognizes_spdx_license_text_and_expression():
    assert identify_license("SPDX-License-Identifier: MIT") == ["MIT"]
    assert identify_license("Licensed under the Apache License, Version 2.0") == ["Apache-2.0"]
    assert identify_license("SPDX-License-Identifier: MIT OR Apache-2.0") == ["MIT OR Apache-2.0"]
    assert identify_license("GNU AFFERO GENERAL PUBLIC LICENSE Version 3") == ["AGPL-3.0-only"]
    assert identify_license("no license information here") == []


def test_missing_license_is_blocked_not_pass():
    no_license = row()
    no_license.pop("license")
    report = check_license(no_license)
    assert report.verdict == LicenseVerdict.BLOCKED.value
    assert "V5-MISSING" in codes(report)
    assert report.ok is False

    unknown = mit_record(license={"spdx": "UNKNOWN"})
    assert check_license(unknown).verdict == LicenseVerdict.BLOCKED.value

    # A file-derived license never silently cures a missing declaration.
    undeclared = mit_record(license={"spdx": ""}, detected_licenses=["MIT"])
    report = check_license(undeclared)
    assert report.verdict == LicenseVerdict.BLOCKED.value
    assert report.license_id == "MIT"


def test_in_house_tbd_is_an_observation_not_a_block():
    report = check_license(row())
    assert report.verdict == LicenseVerdict.PASS_WITH_OBSERVATIONS.value
    assert "V5-PROVENANCE" in codes(report)
    assert report.ok is True


def test_clean_mit_license_passes():
    report = check_license(mit_record())
    assert report.verdict == LicenseVerdict.PASS.value
    assert report.findings == []
    assert report.license_id == "MIT"


def test_apache_requires_notice_file():
    missing = check_license(mit_record(license={"spdx": "Apache-2.0"}))
    assert missing.verdict == LicenseVerdict.FAIL.value
    assert "V5-ATTRIBUTION" in codes(missing)

    complete = check_license(
        mit_record(
            license={"spdx": "Apache-2.0", "notice_files": ["LICENSE", "NOTICE"]},
        )
    )
    assert complete.verdict == LicenseVerdict.PASS.value


def test_incompatible_copyleft_license_fails():
    agpl = check_license(
        mit_record(license={"spdx": "AGPL-3.0-only", "notice_files": ["LICENSE"]}),
    )
    assert agpl.verdict == LicenseVerdict.FAIL.value
    assert "V5-INCOMPATIBLE" in codes(agpl)

    gpl = check_license(
        mit_record(license={"spdx": "GPL-3.0-only", "notice_files": ["LICENSE"]}),
    )
    assert "V5-INCOMPATIBLE" in codes(gpl)


def test_mixed_licenses_fail():
    mixed = check_license(mit_record(detected_licenses=["MIT", "Apache-2.0"]))
    assert mixed.verdict == LicenseVerdict.FAIL.value
    assert "V5-MIXED" in codes(mixed)

    dual = check_license(mit_record(license={"spdx": "MIT OR Apache-2.0"}))
    assert "V5-MIXED" not in codes(dual)


def test_redistribution_restrictions_fail():
    restricted = check_license(
        mit_record(license={"spdx": "CC-BY-NC-4.0", "notice_files": ["LICENSE"]}),
    )
    assert restricted.verdict == LicenseVerdict.FAIL.value
    assert "V5-REDISTRIBUTION" in codes(restricted)

    proprietary = check_license(mit_record(license={"spdx": "PROPRIETARY", "notice_files": ["LICENSE"]}))
    assert "V5-REDISTRIBUTION" in codes(proprietary)


def test_provenance_controls():
    repo_claim = check_license(
        mit_record(license={"scope": "repo-level-claim"}),
    )
    assert repo_claim.verdict == LicenseVerdict.PASS_WITH_OBSERVATIONS.value
    assert "V5-PROVENANCE" in codes(repo_claim)

    unverified = check_license(mit_record(license={"scope": "unverified"}))
    assert unverified.verdict == LicenseVerdict.FAIL.value
    assert "V5-PROVENANCE" in codes(unverified)

    unpinned = check_license(
        mit_record(source={"type": "vendored-upstream", "repo": "upstream/skills"}),
    )
    assert "V5-PROVENANCE" in codes(unpinned)

    inconsistent = check_license(
        mit_record(license={"scope": "in-house"}, source={"type": "adapted"}),
    )
    assert inconsistent.verdict == LicenseVerdict.FAIL.value


def test_check_skill_dir_corroborates_declared_license():
    with tempfile.TemporaryDirectory() as td:
        skill = Path(td) / "mit-skill"
        skill.mkdir()
        (skill / "LICENSE").write_text("MIT License\nSPDX-License-Identifier: MIT\n", encoding="utf-8")

        assert check_skill_dir(skill).verdict == LicenseVerdict.BLOCKED.value
        report = check_skill_dir(skill, record=mit_record())
        assert report.verdict == LicenseVerdict.PASS.value
        assert report.target == str(skill)


def test_classify_precedence_and_report_serialization():
    assert classify([]) == LicenseVerdict.PASS.value
    assert classify([Finding("x", "y", "warning")]) == LicenseVerdict.PASS_WITH_OBSERVATIONS.value
    assert classify([Finding("x", "y", "error")]) == LicenseVerdict.FAIL.value
    assert classify([Finding("x", "y", "error"), Finding("z", "w", "blocker")]) == LicenseVerdict.BLOCKED.value

    payload = check_license(mit_record()).to_dict()
    json.loads(json.dumps(payload))
    assert payload["verdict"] == LicenseVerdict.PASS.value
    assert payload["observations"] == []


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("PASS", test.__name__)
