import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_schemas import validate, load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

def ex(name, obj):
    validate(obj, load_json(SCHEMAS / name))

def test_all():
    ex("build-plan.schema.json", {"build_id":"BUILD-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","technology":"python","build_steps":["build"],"artifact_name":"app.tar","created_by":"AG-016"})
    ex("build-execution.schema.json", {"execution_id":"BEXEC-0001","build_id":"BUILD-0001","status":"COMPLETED","started_at":"now","completed_at":"now","artifact_path":"a","artifact_hash":"h","logs":[]})
    ex("pipeline-definition.schema.json", {"pipeline_id":"PIPE-0001","project_id":"PROJECT-001","stages":["build"],"trigger":"push"})
    ex("environment-definition.schema.json", {"environment_id":"ENV-0001","name":"dev","type":"development","configuration":{},"secrets_reference":"vault"})
    ex("deployment-plan.schema.json", {"deployment_id":"DEP-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","artifact":"a","environment":"dev","strategy":"in_place","rollback_plan":"rb","created_by":"AG-017"})
    ex("deployment-approval.schema.json", {"approval_id":"APPR-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","artifact":"a","environment":"dev","strategy":"in_place","rollback_plan":"rb","risks":[],"approved_by":"human","approved_at":"now"})
    ex("deployment-execution.schema.json", {"execution_id":"DEXEC-0001","deployment_id":"DEP-0001","status":"COMPLETED","started_at":"now","completed_at":"now","health_check":"ok","smoke_tests":[],"rollback_executed":False})
    ex("rollback-plan.schema.json", {"rollback_id":"RB-0001","deployment_id":"DEP-0001","trigger_conditions":["fail"],"steps":["restore"],"estimated_time":"5m","owner":"AG-017"})
    ex("release-manifest.schema.json", {"release_id":"REL-0001","project_id":"PROJECT-001","version":"0.4.0","commit":"abc","artifact":"a","quality_certificate":"qc","created_by":"AG-016"})
    ex("infrastructure-definition.schema.json", {"infrastructure_id":"INFRA-0001","project_id":"PROJECT-001","components":["app"],"observability":["logs"],"created_by":"AG-016"})
    ex("operational-runbook.schema.json", {"runbook_id":"RUNBOOK-0001","project_id":"PROJECT-001","procedures":["deploy"],"rollback":["restore"],"recovery":["restart"],"owner":"AG-018"})
    ex("documentation-manifest.schema.json", {"manifest_id":"DOCMAN-0001","project_id":"PROJECT-001","documents":["README"],"owner":"AG-018"})

if __name__ == "__main__":
    test_all()
    print("PASS f5 schemas")
