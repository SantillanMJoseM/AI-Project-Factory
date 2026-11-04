import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_schemas import validate, load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

def test_test_plan_example():
    validate({"plan_id":"TPLAN-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","scope":"backend","test_types":["unit"],"created_by":"AG-012"}, load_json(SCHEMAS/"test-plan.schema.json"))

def test_test_case_example():
    validate({"case_id":"TC-0001","title":"health","objective":"health","steps":["call"],"expected_result":"200","priority":"high"}, load_json(SCHEMAS/"test-case.schema.json"))

def test_test_execution_example():
    validate({"execution_id":"TEXEC-0001","plan_id":"TPLAN-0001","commit":"abc","framework":"unittest","environment":"local","total":2,"passed":2,"failed":0,"skipped":0,"evidence":["log"],"duration_seconds":1.0}, load_json(SCHEMAS/"test-execution.schema.json"))

def test_defect_example():
    validate({"defect_id":"DEF-0001","title":"bug","severity":"HIGH","component":"backend","evidence":["log"],"impact":"x","recommendation":"fix","status":"open"}, load_json(SCHEMAS/"defect.schema.json"))

def test_code_review_example():
    validate({"finding_id":"CR-0001","file":"app.py","location":"1","description":"x","severity":"LOW","evidence":"y","impact":"z","recommendation":"r","owner":"AG-008"}, load_json(SCHEMAS/"code-review.schema.json"))

def test_performance_report_example():
    validate({"report_id":"PERF-0001","commit":"abc","environment":"local","hardware":"laptop","configuration":"dev","tool":"time","load":"1 user","duration_seconds":1.0,"results":["ok"],"limitations":[]}, load_json(SCHEMAS/"performance-report.schema.json"))

def test_security_finding_example():
    validate({"finding_id":"SEC-0001","category":"config","component":"app","evidence":["x"],"impact":"y","probability":"low","severity":"LOW","recommendation":"r","status":"open"}, load_json(SCHEMAS/"security-finding.schema.json"))

def test_quality_certificate_example():
    validate({"certificate_id":"QCERT-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","date":"2026-11-04","technologies":["python"],"qa_result":"pass","code_review_result":"pass","performance_result":"pass","security_result":"pass","open_defects":[],"remediated_defects":[],"authorized_exceptions":[],"evidence":["log"],"final_verdict":"PASS","gatekeeper":"AG-002"}, load_json(SCHEMAS/"quality-certificate.schema.json"))

if __name__ == "__main__":
    for fn in [test_test_plan_example,test_test_case_example,test_test_execution_example,test_defect_example,test_code_review_example,test_performance_report_example,test_security_finding_example,test_quality_certificate_example]:
        fn()
        print("PASS", fn.__name__)
