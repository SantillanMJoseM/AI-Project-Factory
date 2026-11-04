from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_f3_agents():
    for aid in ["ag-008","ag-009","ag-010","ag-011"]:
        files = list((ROOT / "agents" / "development").glob(f"{aid}-*.md"))
        assert files, aid
    for aid in ["ag-008-backend-developer","ag-009-frontend-developer","ag-010-database-developer","ag-011-integration-engineer"]:
        assert (ROOT / ".opencode" / "agents" / f"{aid}.md").is_file()

def test_f3_schemas():
    for name in ["development-task.schema.json","development-execution-report.schema.json"]:
        assert (ROOT / "schemas" / name).is_file()

def test_f3_workflows():
    for rel in ["orchestration/workflows/f3-development-workflow.md","orchestration/workflows/interface-contract-workflow.md"]:
        assert (ROOT / rel).is_file()

if __name__ == "__main__":
    test_f3_agents()
    test_f3_schemas()
    test_f3_workflows()
    print("PASS f3 structure")
