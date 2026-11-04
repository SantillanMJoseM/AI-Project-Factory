#!/usr/bin/env python3
"""Executable Quality Gate Runtime for AI-Project-Factory."""

import argparse
import json
import os
import sys
from pathlib import Path

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
OPEN_STATUSES = {"open", "failed", "active", "pending", "new", "unresolved", ""}
REMEDIATED_STATUSES = {"remediated", "closed", "verified", "fixed", "resolved"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_defect(defect, source):
    severity = str(defect.get("severity", "MEDIUM")).upper()
    if severity not in SEVERITY_RANK:
        severity = "MEDIUM"
    status = str(defect.get("status", "open")).lower()
    defect_id = defect.get("id") or defect.get("defect_id") or defect.get("finding_id") or defect.get("case_id")
    return {
        "id": defect_id,
        "source": source,
        "severity": severity,
        "status": status,
        "open": status in OPEN_STATUSES,
        "title": defect.get("title") or defect.get("description") or defect.get("summary") or "",
        "evidence": defect.get("evidence", []),
    }


def collect_defects(evidence_dir):
    evidence_dir = Path(evidence_dir)
    defects = []
    sources = {}
    expected = {
        "code_review.json": "code_review",
        "security_findings.json": "security",
        "defects.json": "defect_registry",
        "test_execution.json": "tests",
    }
    for filename, source in expected.items():
        path = evidence_dir / filename
        if not path.exists():
            sources[source] = {"present": False, "path": str(path)}
            continue
        try:
            data = load_json(path)
        except Exception as exc:
            raise ValueError(f"Cannot parse {path}: {exc}")
        sources[source] = {"present": True, "path": str(path)}
        if source == "code_review":
            for finding in data.get("findings", data.get("defects", [])):
                defects.append(normalize_defect(finding, source))
            if data.get("verdict") or data.get("result"):
                sources[source]["verdict"] = data.get("verdict") or data.get("result")
        elif source == "security":
            for finding in data.get("findings", data.get("defects", [])):
                defects.append(normalize_defect(finding, source))
            if data.get("verdict") or data.get("result"):
                sources[source]["verdict"] = data.get("verdict") or data.get("result")
        elif source == "defect_registry":
            for defect in data.get("defects", []):
                defects.append(normalize_defect(defect, source))
        elif source == "tests":
            for defect in data.get("defects", []):
                defects.append(normalize_defect(defect, source))
            for failed in data.get("failed_tests", []):
                defects.append({
                    "id": failed if isinstance(failed, str) else failed.get("id"),
                    "source": source,
                    "severity": "MEDIUM",
                    "status": "open",
                    "open": True,
                    "title": failed if isinstance(failed, str) else failed.get("name", "failed test"),
                    "evidence": [str(path)],
                })
            sources[source]["status"] = data.get("status") or data.get("result")
    return defects, sources


def validate_certificate_schema(certificate):
    required = [
        "certificate_id", "project_id", "version", "commit", "date", "technologies",
        "qa_result", "code_review_result", "performance_result", "security_result",
        "open_defects", "remediated_defects", "authorized_exceptions", "evidence",
        "final_verdict", "gatekeeper", "evaluation_id",
    ]
    for field in required:
        if field not in certificate:
            return [f"Missing required field: {field}"]
    errors = []
    if not isinstance(certificate.get("open_defects"), list):
        errors.append("open_defects must be an array")
    if not isinstance(certificate.get("remediated_defects"), list):
        errors.append("remediated_defects must be an array")
    if not isinstance(certificate.get("evidence"), list) or not certificate.get("evidence"):
        errors.append("evidence must be a non-empty array")
    if certificate.get("final_verdict") not in {"PASS", "PASS_WITH_OBSERVATIONS", "FAIL", "BLOCKED"}:
        errors.append("Invalid final_verdict")
    if not str(certificate.get("gatekeeper", "")).startswith("AG-"):
        errors.append("Invalid gatekeeper")
    return errors


def evaluate(certificate, evidence_dir):
    evidence_dir = Path(evidence_dir)
    rules_violated = []
    try:
        defects, sources = collect_defects(evidence_dir)
    except Exception as exc:
        return {
            "verdict": "FAIL",
            "exit_code": 1,
            "rules_violated": [f"Evidence read error: {exc}"],
            "defects": [],
            "sources": {},
        }

    schema_errors = validate_certificate_schema(certificate)
    rules_violated.extend(schema_errors)

    open_defects = [d for d in defects if d["open"]]
    critical_open = [d for d in open_defects if d["severity"] == "CRITICAL"]
    high_open = [d for d in open_defects if d["severity"] == "HIGH"]
    medium_open = [d for d in open_defects if d["severity"] == "MEDIUM"]
    low_open = [d for d in open_defects if d["severity"] == "LOW"]

    computed_verdict = "PASS"
    if critical_open:
        computed_verdict = "BLOCKED"
    elif high_open or medium_open:
        computed_verdict = "FAIL"
    elif low_open or any(d["severity"] == "INFO" for d in open_defects):
        computed_verdict = "PASS_WITH_OBSERVATIONS"

    # Consistency checks.
    if certificate.get("final_verdict") == "BLOCKED":
        rules_violated.append("Certificate cannot certify a BLOCKED state as approved")
    if certificate.get("final_verdict") != computed_verdict:
        rules_violated.append(
            f"Certificate verdict {certificate.get('final_verdict')} does not match computed verdict {computed_verdict}"
        )

    code_review_source = sources.get("code_review", {})
    if code_review_source.get("verdict") in {"FAIL", "BLOCKED", "REJECTED"} and certificate.get("final_verdict") in {"PASS", "PASS_WITH_OBSERVATIONS"}:
        rules_violated.append("Code review failed but certificate attempts to pass")

    security_source = sources.get("security", {})
    if security_source.get("verdict") in {"FAIL", "BLOCKED", "REJECTED"} and certificate.get("final_verdict") in {"PASS", "PASS_WITH_OBSERVATIONS"}:
        rules_violated.append("Security audit failed but certificate attempts to pass")

    test_source = sources.get("tests", {})
    if test_source.get("status") in {"FAIL", "FAILED", "BLOCKED"} and certificate.get("final_verdict") in {"PASS", "PASS_WITH_OBSERVATIONS"}:
        rules_violated.append("Test execution failed but certificate attempts to pass")

    # Certificate must include all open defect IDs.
    cert_open_ids = set(certificate.get("open_defects", []))
    actual_open_ids = {d["id"] for d in open_defects if d["id"]}
    missing_ids = actual_open_ids - cert_open_ids
    if missing_ids:
        rules_violated.append(f"Certificate omits open defects: {sorted(missing_ids)}")

    # Evidence references must exist.
    for ref in certificate.get("evidence", []):
        ref_path = Path(ref)
        if not ref_path.is_absolute():
            ref_path = evidence_dir / ref
            if not ref_path.exists():
                ref_path = Path(ref)
        if not ref_path.exists():
            rules_violated.append(f"Missing evidence reference: {ref}")

    # Remediation requires re-audit.
    remediated = certificate.get("remediated_defects", [])
    reaudit_path = evidence_dir / "reaudit.json"
    if remediated:
        if not reaudit_path.exists():
            rules_violated.append("Remediated defects require reaudit evidence")
        else:
            try:
                reaudit = load_json(reaudit_path)
                if not reaudit.get("performed"):
                    rules_violated.append("Reaudit evidence indicates reaudit was not performed")
            except Exception as exc:
                rules_violated.append(f"Cannot parse reaudit evidence: {exc}")

    if certificate.get("final_verdict") == "BLOCKED":
        computed_verdict = "BLOCKED"

    if rules_violated and computed_verdict in {"PASS", "PASS_WITH_OBSERVATIONS"}:
        if critical_open:
            computed_verdict = "BLOCKED"
        else:
            computed_verdict = "FAIL"

    exit_code = 0 if computed_verdict in {"PASS", "PASS_WITH_OBSERVATIONS"} else (2 if computed_verdict == "BLOCKED" else 1)

    return {
        "verdict": computed_verdict,
        "exit_code": exit_code,
        "rules_violated": sorted(set(rules_violated)),
        "defects": defects,
        "open_defects": open_defects,
        "sources": sources,
        "certificate_verdict": certificate.get("final_verdict"),
    }


def main():
    parser = argparse.ArgumentParser(description="AI-Project-Factory Quality Gate Runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate a Quality Certificate against evidence")
    validate.add_argument("--certificate", required=True, help="Path to quality certificate JSON")
    validate.add_argument("--evidence-dir", required=True, help="Directory containing evidence files")
    validate.add_argument("--format", choices=["human", "json"], default="human")
    validate.add_argument("--output", help="Optional output file")
    args = parser.parse_args()

    if args.command != "validate":
        parser.error("Unknown command")

    try:
        certificate = load_json(args.certificate)
    except Exception as exc:
        print(f"ERROR: cannot read certificate: {exc}")
        return 3

    result = evaluate(certificate, args.evidence_dir)

    if args.format == "json":
        rendered = json.dumps(result, indent=2, sort_keys=True)
    else:
        lines = []
        lines.append(f"Quality Gate verdict: {result['verdict']}")
        lines.append(f"Exit code: {result['exit_code']}")
        if result["rules_violated"]:
            lines.append("Rules violated:")
            for rule in result["rules_violated"]:
                lines.append(f"  - {rule}")
        else:
            lines.append("No rules violated.")
        lines.append(f"Open defects: {len(result['open_defects'])}")
        rendered = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
PY
