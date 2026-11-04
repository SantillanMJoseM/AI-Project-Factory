import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_schemas import validate, load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

def test_f2_schemas_valid_json():
    names = ["project-requirements.schema.json","user-story.schema.json","architecture-component.schema.json","architecture-decision.schema.json","ui-screen.schema.json","database-entity.schema.json","traceability-matrix.schema.json"]
    for name in names:
        load_json(SCHEMAS / name)

def test_project_requirements_example():
    schema = load_json(SCHEMAS / "project-requirements.schema.json")
    example = {
        "project_id": "PROJECT-001",
        "requirements": [{
            "id": "REQ-0001",
            "description": "User can log in",
            "justification": "Authentication needed",
            "priority": "high",
            "origin": "user",
            "dependencies": [],
            "acceptance_criteria": ["Login succeeds"],
            "status": "confirmed",
            "certainty": "confirmed"
        }]
    }
    validate(example, schema)

def test_user_story_example():
    schema = load_json(SCHEMAS / "user-story.schema.json")
    validate({"id":"US-0001","actor":"User","story":"login","acceptance_criteria":["ok"],"priority":"high","related_requirement":"REQ-0001"}, schema)

def test_architecture_component_example():
    schema = load_json(SCHEMAS / "architecture-component.schema.json")
    validate({"id":"COMP-0001","name":"Auth","responsibility":"auth","interfaces":["API"],"dependencies":[],"requirements":["REQ-0001"]}, schema)

def test_architecture_decision_example():
    schema = load_json(SCHEMAS / "architecture-decision.schema.json")
    validate({"id":"ADR-F2-0001","context":"ctx","problem":"p","alternatives":["a"],"decision":"d","justification":"j","consequences":[],"risks":[],"status":"accepted"}, schema)

def test_ui_screen_example():
    schema = load_json(SCHEMAS / "ui-screen.schema.json")
    validate({"id":"SCR-0001","objective":"login","user_profile":"user","displayed_info":[],"actions":[],"validations":[],"states":[],"errors":[],"navigation":[],"related_requirements":["REQ-0001"]}, schema)

def test_database_entity_example():
    schema = load_json(SCHEMAS / "database-entity.schema.json")
    validate({"id":"ENT-0001","description":"User","attributes":[{"name":"id","type":"uuid","key":"primary"}],"relationships":[],"constraints":[],"indexes":[],"requirements":["REQ-0001"]}, schema)

def test_traceability_matrix_example():
    schema = load_json(SCHEMAS / "traceability-matrix.schema.json")
    validate({"project_id":"PROJECT-001","entries":[{"requirement_id":"REQ-0001","user_story":"US-0001","component":"COMP-0001","screen":"SCR-0001","entity":"ENT-0001","acceptance_criteria":"ok","dev_task":"TASK-0001"}]}, schema)

if __name__ == "__main__":
    for name in ["test_f2_schemas_valid_json","test_project_requirements_example","test_user_story_example","test_architecture_component_example","test_architecture_decision_example","test_ui_screen_example","test_database_entity_example","test_traceability_matrix_example"]:
        globals()[name]()
        print("PASS", name)
