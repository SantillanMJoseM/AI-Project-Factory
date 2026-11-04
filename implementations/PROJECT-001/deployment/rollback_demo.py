import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEPLOY_ROOT = Path("/tmp/scratchpad/project001-deploy")
TARGET = DEPLOY_ROOT / "current"
BACKUP = DEPLOY_ROOT / "backup"
PORT = 8799

def health_check():
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    if not BACKUP.exists():
        print("NO_BACKUP")
        return 1
    if TARGET.exists():
        shutil.rmtree(TARGET, ignore_errors=True)
    shutil.move(str(BACKUP), str(TARGET))
    BACKUP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PORT"] = str(PORT)
    env["DB_PATH"] = str(TARGET / "backend" / "tasks.db")
    env["SCHEMA_PATH"] = str(TARGET / "database" / "schema.sql")
    proc = subprocess.Popen([sys.executable, str(TARGET / "backend" / "app.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not health_check():
            raise RuntimeError("rollback health check failed")
        print("ROLLBACK_OK")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY
