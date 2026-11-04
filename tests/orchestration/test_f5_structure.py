from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_f5_agents():
    for aid in ["ag-016","ag-017","ag-018"]:
        files = list((ROOT / "agents" / "delivery").glob(f"{aid}-*.md"))
        assert files, aid
    for aid in ["ag-016-devops-engineer","ag-017-deployment-manager","ag-018-documentation-engineer"]:
        assert (ROOT / ".opencode" / "agents" / f"{aid}.md").is_file()

def test_f5_schemas():
    names = ["build-plan.schema.json","build-execution.schema.json","pipeline-definition.schema.json","environment-definition.schema.json","deployment-plan.schema.json","deployment-approval.schema.json","deployment-execution.schema.json","rollback-plan.schema.json","release-manifest.schema.json","infrastructure-definition.schema.json","operational-runbook.schema.json","documentation-manifest.schema.json"]
    for name in names:
        assert (ROOT / "schemas" / name).is_file()

def test_f5_quality_gates():
    assert len(list((ROOT / "quality-gates" / "f5").glob("*.md"))) == 10

if __name__ == "__main__":
    test_f5_agents()
    test_f5_schemas()
    test_f5_quality_gates()
    print("PASS f5 structure")
