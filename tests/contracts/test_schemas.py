import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

def load_json(path):
    return json.loads(path.read_text())

def validate(instance, schema):
    # minimal validator for our schemas
    if schema.get("type") == "object":
        if not isinstance(instance, dict):
            raise AssertionError("not object")
        for req in schema.get("required", []):
            assert req in instance, f"missing {req}"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                assert key in props, f"unexpected property {key}"
        for key, value in instance.items():
            if key in props:
                validate_value(value, props[key])
    elif schema.get("type") == "array":
        assert isinstance(instance, list)
        items = schema.get("items", {})
        for item in instance:
            validate_value(item, items)
        if "minItems" in schema:
            assert len(instance) >= schema["minItems"]

def validate_value(value, schema):
    t = schema.get("type")
    if isinstance(t, list):
        # nullable
        if value is None and "null" in t:
            return
        t = [x for x in t if x != "null"][0]
    if t == "string":
        assert isinstance(value, str)
        if "minLength" in schema:
            assert len(value) >= schema["minLength"]
        if "enum" in schema:
            assert value in schema["enum"]
        if "pattern" in schema:
            assert re.match(schema["pattern"], value), f"pattern fail {value}"
        if schema.get("format") == "date-time":
            # allow Z
            txt = value.replace("Z", "+00:00")
            datetime.fromisoformat(txt)
    elif t == "array":
        assert isinstance(value, list)
        items = schema.get("items", {})
        for item in value:
            validate_value(item, items)
        if "minItems" in schema:
            assert len(value) >= schema["minItems"]
    elif t == "object":
        validate(value, schema)
    elif t == "integer":
        assert isinstance(value, int) and not isinstance(value, bool)
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
    elif t == "boolean":
        assert isinstance(value, bool)
    elif t == "null":
        assert value is None

def test_schemas_are_valid_json():
    for name in ["agent.schema.json", "task.schema.json", "execution.schema.json", "audit.schema.json"]:
        schema = load_json(SCHEMAS / name)
        assert schema["$schema"].startswith("https://json-schema.org")

def test_agent_example_validates():
    schema = load_json(SCHEMAS / "agent.schema.json")
    example = {
        "id": "AG-001",
        "name": "Project Coordinator",
        "domain": "management",
        "objective": "Coordinate",
        "responsibilities": ["Coordinate"],
        "limits": [],
        "inputs": [],
        "outputs": [],
        "tools": ["read"],
        "permissions": ["read: allow"],
        "dependencies": [],
        "acceptance_criteria": ["Done"],
        "escalation_rules": []
    }
    validate(example, schema)

def test_agent_example_invalid():
    schema = load_json(SCHEMAS / "agent.schema.json")
    bad = {"id": "AG-001", "name": "X"}
    try:
        validate(bad, schema)
    except AssertionError:
        return
    raise AssertionError("invalid agent accepted")

def test_task_example_validates():
    schema = load_json(SCHEMAS / "task.schema.json")
    example = {
        "id": "TASK-0001",
        "title": "Test",
        "description": "Desc",
        "status": "PENDING",
        "priority": "medium",
        "assigned_agent": "AG-001",
        "inputs": [],
        "outputs": [],
        "acceptance_criteria": ["Done"],
        "quality_gates": ["QG-01"],
        "created_at": "2026-11-04T00:00:00Z",
        "updated_at": "2026-11-04T00:00:00Z"
    }
    validate(example, schema)

def test_execution_example_validates():
    schema = load_json(SCHEMAS / "execution.schema.json")
    example = {
        "execution_id": "EXEC-0001",
        "task_id": "TASK-0001",
        "agent_id": "AG-001",
        "started_at": "2026-11-04T00:00:00Z",
        "status": "COMPLETED",
        "inputs": [],
        "outputs": [],
        "tools_used": ["read"],
        "decisions": [],
        "errors": [],
        "completed_at": "2026-11-04T01:00:00Z"
    }
    validate(example, schema)

def test_audit_example_validates():
    schema = load_json(SCHEMAS / "audit.schema.json")
    example = {
        "audit_id": "AUDIT-0001",
        "scope": "F0",
        "auditor": "AG-015",
        "audited_artifacts": ["README.md"],
        "findings": [],
        "verdict": "PASS",
        "evidence": ["tests"],
        "created_at": "2026-11-04T00:00:00Z"
    }
    validate(example, schema)

if __name__ == "__main__":
    for fn in [test_schemas_are_valid_json, test_agent_example_validates, test_agent_example_invalid,
               test_task_example_validates, test_execution_example_validates, test_audit_example_validates]:
        fn()
        print("PASS", fn.__name__)
