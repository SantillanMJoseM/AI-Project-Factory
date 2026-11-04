from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_f1_agent_files():
    for rel in [
        "agents/management/ag-001-project-coordinator.md",
        "agents/management/ag-002-quality-gatekeeper.md",
        "agents/management/ag-003-security-risk-manager.md",
        ".opencode/agents/ag-001-project-coordinator.md",
        ".opencode/agents/ag-002-quality-gatekeeper.md",
        ".opencode/agents/ag-003-security-risk-manager.md",
    ]:
        assert (ROOT / rel).is_file(), rel

def test_f1_workflows():
    for rel in [
        "orchestration/workflows/coordination-workflow.md",
        "orchestration/workflows/audit-workflow.md",
        "orchestration/workflows/security-authorization-workflow.md",
    ]:
        assert (ROOT / rel).is_file(), rel

def test_f1_contracts():
    assert (ROOT / "contracts/coordination-contract.md").is_file()

if __name__ == "__main__":
    for fn in [test_f1_agent_files, test_f1_workflows, test_f1_contracts]:
        fn()
        print("PASS", fn.__name__)
