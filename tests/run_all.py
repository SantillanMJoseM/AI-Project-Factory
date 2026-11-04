import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tests = [
    "contracts/test_schemas.py",
    "contracts/test_state_transitions.py",
    "policies/test_policy_files.py",
    "orchestration/test_f1_structure.py",
    "policies/test_f1_policies.py",
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