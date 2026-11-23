import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tests = [
    "contracts/test_schemas.py",
    "contracts/test_state_transitions.py",
    "policies/test_policy_files.py",
    "contracts/test_f5_schemas.py",
    "orchestration/test_runtime.py",
    "orchestration/test_sandbox.py",
    "skills/test_registry.py",
    "skills/test_validation.py",
    "skills/test_security_scan.py",
    "skills/test_rollback.py",
    "skills/test_license_check.py",
    "skills/test_task_contract.py",
    "skills/test_drift.py",
    "execution/test_execution_smoke.py",
    "execution/test_ledger.py",
    "execution/test_snapshot.py",
    "execution/test_context.py",
    "execution/test_resume.py",
    "execution/test_documents.py",
    "integration/test_end_to_end.py",
    "task_orchestration/test_engine.py",
    "task_orchestration/test_delegation.py",
    "task_orchestration/test_coordination.py",
    "task_orchestration/test_parallel.py",
]

failed = False
for rel in tests:
    path = ROOT / rel
    result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    print("=== " + rel + " ===")
    print(result.stdout)
    if result.returncode != 0:
        failed = True
        print(result.stderr)

if failed:
    print("TESTS FAILED")
    sys.exit(1)
print("ALL TESTS PASSED")