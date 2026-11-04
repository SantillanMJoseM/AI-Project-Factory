import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tests = [
    "contracts/test_schemas.py",
    "contracts/test_state_transitions.py",
    "policies/test_policy_files.py",
    "contracts/test_f5_schemas.py",
    "orchestration/test_quality_gate_runtime.py",
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