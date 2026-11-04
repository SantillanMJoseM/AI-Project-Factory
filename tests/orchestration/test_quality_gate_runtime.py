import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "orchestration" / "validators" / "quality_gate.py"

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def base_cert(verdict="PASS", open_defects=None, remediated=None, evidence=None, evaluation_id="EVAL-001"):
    return {
        "certificate_id": "QCERT-0001",
        "project_id": "PROJECT-TEST",
        "version": "1.0",
        "commit": "abc123",
        "date": "2026-11-04",
        "technologies": ["python"],
        "qa_result": "PASS",
        "code_review_result": "PASS",
        "performance_result": "PASS",
        "security_result": "PASS",
        "open_defects": open_defects or [],
        "remediated_defects": remediated or [],
        "authorized_exceptions": [],
        "evidence": evidence or ["code_review.json"],
        "final_verdict": verdict,
        "gatekeeper": "AG-002",
        "evaluation_id": evaluation_id,
    }

def make_evidence(tmp, code_review=None, security=None, defects=None, tests=None, remediation=None, reaudit=None):
    d = Path(tmp)
    if code_review is not None:
        write_json(d / "code_review.json", code_review)
    if security is not None:
        write_json(d / "security_findings.json", security)
    if defects is not None:
        write_json(d / "defects.json", defects)
    if tests is not None:
        write_json(d / "test_execution.json", tests)
    if remediation is not None:
        write_json(d / "remediation.json", remediation)
    if reaudit is not None:
        write_json(d / "reaudit.json", reaudit)
    return d

def run_cli(cert_path, evidence_dir, fmt="json"):
    return subprocess.run(
        [sys.executable, str(RUNTIME), "validate", "--certificate", str(cert_path), "--evidence-dir", str(evidence_dir), "--format", fmt],
        capture_output=True, text=True,
    )

def test_critical_open_blocked():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ev = make_evidence(td, code_review={"verdict": "FAIL", "findings": [{"id": "CR-0001", "severity": "CRITICAL", "status": "open"}]})
        cert = base_cert(verdict="BLOCKED", open_defects=["CR-0001"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "BLOCKED"
        assert r.returncode == 2

def test_high_open_fail():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ev = make_evidence(td, code_review={"verdict": "FAIL", "findings": [{"id": "CR-0002", "severity": "HIGH", "status": "open"}]})
        cert = base_cert(verdict="FAIL", open_defects=["CR-0002"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "FAIL"
        assert r.returncode == 1

def test_low_pass_with_observations():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS_WITH_OBSERVATIONS", "findings": [{"id": "CR-0003", "severity": "LOW", "status": "open"}]})
        cert = base_cert(verdict="PASS_WITH_OBSERVATIONS", open_defects=["CR-0003"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "PASS_WITH_OBSERVATIONS"
        assert r.returncode == 0

def test_code_review_fail_cert_pass_rejected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "FAIL", "findings": [{"id": "CR-0004", "severity": "MEDIUM", "status": "open"}]})
        cert = base_cert(verdict="PASS", open_defects=["CR-0004"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] in {"FAIL", "BLOCKED"}
        assert "Code review failed but certificate attempts to pass" in data["rules_violated"]

def test_cert_omits_critical_rejected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "FAIL", "findings": [{"id": "CR-0005", "severity": "CRITICAL", "status": "open"}]})
        cert = base_cert(verdict="BLOCKED", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "BLOCKED"
        assert any("omits open defects" in rule for rule in data["rules_violated"])

def test_missing_evidence_rejected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["missing.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] != "PASS"
        assert any("Missing evidence reference" in rule for rule in data["rules_violated"])

def test_unreaudited_remediation_rejected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []}, remediation={"remediated": ["DEF-0001"]})
        cert = base_cert(verdict="PASS", open_defects=[], remediated=["DEF-0001"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] != "PASS"
        assert any("reaudit" in rule.lower() for rule in data["rules_violated"])

def test_blocked_cert_rejected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="BLOCKED", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "BLOCKED"
        assert any("BLOCKED state" in rule for rule in data["rules_violated"])

def test_valid_cert_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "PASS"
        assert r.returncode == 0

def test_determinism():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r1 = run_cli(cp, td)
        r2 = run_cli(cp, td)
        assert json.loads(r1.stdout) == json.loads(r2.stdout)

def test_cli_exit_codes():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        assert r.returncode == 0
        # invalid certificate
        bad = td / "bad.json"
        bad.write_text("{", encoding="utf-8")
        r2 = run_cli(bad, td)
        assert r2.returncode == 3

def test_inputs_not_modified():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "PASS", "findings": []})
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        before = cp.read_text()
        run_cli(cp, td)
        after = cp.read_text()
        assert before == after

def test_read_error_no_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "code_review.json").write_text("{", encoding="utf-8")
        cert = base_cert(verdict="PASS", open_defects=[], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] != "PASS"

def test_real_case_critical_cert_pass_with_observations():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_evidence(td, code_review={"verdict": "FAIL", "findings": [{"id": "CR-P001-001", "severity": "CRITICAL", "status": "open"}]})
        cert = base_cert(verdict="PASS_WITH_OBSERVATIONS", open_defects=["CR-P001-001"], evidence=["code_review.json"])
        cp = td / "cert.json"
        write_json(cp, cert)
        r = run_cli(cp, td)
        data = json.loads(r.stdout)
        assert data["verdict"] == "BLOCKED"
        assert r.returncode == 2

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
