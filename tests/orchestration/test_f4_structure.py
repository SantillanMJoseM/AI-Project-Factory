from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_f4_agents():
    for aid in ["ag-012","ag-013","ag-014","ag-015"]:
        files = list((ROOT / "agents" / "quality").glob(f"{aid}-*.md"))
        assert files, aid
    for aid in ["ag-012-qa-automation-engineer","ag-013-code-reviewer","ag-014-performance-engineer","ag-015-security-auditor"]:
        assert (ROOT / ".opencode" / "agents" / f"{aid}.md").is_file()

def test_f4_schemas():
    names = ["test-plan.schema.json","test-case.schema.json","test-execution.schema.json","defect.schema.json","code-review.schema.json","performance-report.schema.json","security-finding.schema.json","quality-certificate.schema.json"]
    for name in names:
        assert (ROOT / "schemas" / name).is_file()

def test_f4_quality_gates():
    assert len(list((ROOT / "quality-gates" / "f4").glob("*.md"))) == 7

if __name__ == "__main__":
    test_f4_agents()
    test_f4_schemas()
    test_f4_quality_gates()
    print("PASS f4 structure")
