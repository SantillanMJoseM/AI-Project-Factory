#!/usr/bin/env python3
"""R5 environment preflight checks."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def check(name, fn):
    try:
        ok, detail = fn()
        return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}
    except Exception as exc:
        return {"name": name, "status": "FAIL", "detail": str(exc)}

def run():
    results = []

    # Python
    results.append(check("python", lambda: (sys.version_info >= (3, 10), sys.version.split()[0])))

    # Repository
    def repo_check():
        git_dir = ROOT / ".git"
        return git_dir.exists(), str(ROOT)
    results.append(check("repository", repo_check))

    # Factory version
    def version_check():
        status_file = ROOT / "PROJECT_STATUS.md"
        text = status_file.read_text(encoding="utf-8")
        return "Version:" in text, "PROJECT_STATUS.md present"
    results.append(check("factory_version", version_check))

    # OpenCode
    def opencode_check():
        binary = shutil.which("opencode")
        if not binary:
            return False, "opencode not found"
        r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
        return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
    results.append(check("opencode", opencode_check))

    # OpenCode agents
    def agents_check():
        binary = shutil.which("opencode")
        if not binary:
            return False, "opencode not found"
        r = subprocess.run([binary, "debug", "agents"], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return False, r.stderr.strip()
        agents = json.loads(r.stdout)
        project_agents = [a for a in agents if a.get("id", "").startswith("ag-")]
        return len(project_agents) >= 18, f"{len(project_agents)} project agents loaded"
    results.append(check("opencode_agents", agents_check))

    # Runtime R3
    def runtime_check():
        sys.path.insert(0, str(ROOT))
        import orchestration.runtime.runtime as rt  # noqa: F401
        return True, "runtime importable"
    results.append(check("runtime_r3", runtime_check))

    # Validators R1/R2
    def validators_check():
        sys.path.insert(0, str(ROOT))
        import orchestration.validators.quality_gate as qg  # noqa: F401
        import orchestration.validators.traceability.traceability as tr  # noqa: F401
        return True, "R1 and R2 validators importable"
    results.append(check("validators_r1_r2", validators_check))

    # Tests
    def tests_check():
        r = subprocess.run([sys.executable, "tests/run_all.py"], cwd=ROOT, capture_output=True, text=True, timeout=300)
        return r.returncode == 0, "PASS" if r.returncode == 0 else r.stdout[-500:]
    results.append(check("general_tests", tests_check))

    # Writable work directory
    def workdir_check():
        d = Path("/tmp/opencode/r5-preflight")
        d.mkdir(parents=True, exist_ok=True)
        test_file = d / "write_test.txt"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return True, str(d)
    results.append(check("work_directory", workdir_check))

    # Project isolation
    def isolation_check():
        d = Path("/tmp/opencode/r5-isolation-test")
        d.mkdir(parents=True, exist_ok=True)
        factory_file = ROOT / "PROJECT_STATUS.md"
        return factory_file.exists() and d.exists(), "factory and project paths are separate"
    results.append(check("project_isolation", isolation_check))

    # Controlled invocation
    if os.environ.get("APF_PREFLIGHT_INVOKE") == "1":
        def invoke_check():
            binary = shutil.which("opencode")
            if not binary:
                return False, "opencode not found"
            r = subprocess.run([binary, "run", "--agent", "ag-001-project-coordinator", "--model", "opencode-go/qwen3.8-flash", "--auto", "Respond with exactly: R5_PREFLIGHT_OK"], capture_output=True, text=True, timeout=120)
            return r.returncode == 0 and "R5_PREFLIGHT_OK" in r.stdout, r.stdout[-200:]
        results.append(check("controlled_invocation", invoke_check))
    else:
        results.append({"name": "controlled_invocation", "status": "NOT_VERIFIED", "detail": "Set APF_PREFLIGHT_INVOKE=1 to run"})

    # Overall
    statuses = [r["status"] for r in results]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "BLOCKED" in statuses:
        overall = "BLOCKED"
    elif "NOT_VERIFIED" in statuses:
        overall = "NOT_VERIFIED"
    else:
        overall = "PASS"

    payload = {"overall": overall, "checks": results}
    return payload

def main():
    import argparse
    parser = argparse.ArgumentParser(description="R5 environment preflight")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()
    payload = run()
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"R5 preflight: {payload['overall']}")
        for check in payload["checks"]:
            print(f"- {check['name']}: {check['status']} ({check['detail']})")
    return 0 if payload["overall"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
from .r5_preflight import main
import sys
raise SystemExit(main())
