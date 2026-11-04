import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_schemas import validate, load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

def test_development_task_example():
    schema = load_json(SCHEMAS / "development-task.schema.json")
    validate({
        "task_id":"DTASK-0001",
        "project_id":"PROJECT-001",
        "module_id":"auth",
        "agent_id":"AG-008",
        "objective":"Implement auth",
        "requirements":["REQ-0001"],
        "dependencies":[],
        "assigned_files":["src/auth.py"],
        "allowed_directories":["src/"],
        "expected_artifacts":["src/auth.py"],
        "acceptance_criteria":["Login works"],
        "test_requirements":["unit"],
        "git_branch":"feature/backend-auth",
        "status":"PENDING"
    }, schema)

def test_development_report_example():
    schema = load_json(SCHEMAS / "development-execution-report.schema.json")
    validate({
        "execution_id":"EXEC-0001",
        "modified_files":["src/auth.py"],
        "generated_artifacts":["src/auth.py"],
        "implementation_summary":"Implemented auth",
        "tests_executed":["pytest"],
        "test_results":"pass",
        "known_issues":[],
        "technical_decisions":[],
        "commit_reference":"abc123",
        "handoff_notes":"done"
    }, schema)

if __name__ == "__main__":
    test_development_task_example()
    test_development_report_example()
    print("PASS f3 schemas")
