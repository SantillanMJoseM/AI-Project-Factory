import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DATABASE = ROOT / "database"
DEPLOY_ROOT = Path("/tmp/scratchpad/project001-deploy")
TARGET = DEPLOY_ROOT / "current"
BACKUP = DEPLOY_ROOT / "backup"
ARTIFACT = DEPLOY_ROOT / "artifact.zip"
PORT = 8799

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def build():
    if ARTIFACT.exists():
        ARTIFACT.unlink()
    with zipfile.ZipFile(ARTIFACT, "w", zipfile.ZIP_DEFLATED) as z:
        for base in (BACKEND, FRONTEND, DATABASE):
            for p in base.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(ROOT))
    return sha256_file(ARTIFACT)

def deploy(artifact_hash):
    if TARGET.exists():
        if BACKUP.exists():
            shutil.rmtree(BACKUP)
        shutil.move(str(TARGET), str(BACKUP))
    TARGET.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARTIFACT) as z:
        z.extractall(TARGET)
    assert sha256_file(ARTIFACT) == artifact_hash
    return True

def health_check():
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def smoke_test():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
        return r.status == 200

def start_server():
    env = dict(os.environ)
    env["PORT"] = str(PORT)
    env["DB_PATH"] = str(TARGET / "backend" / "tasks.db")
    env["SCHEMA_PATH"] = str(TARGET / "database" / "schema.sql")
    proc = subprocess.Popen([sys.executable, str(TARGET / "backend" / "app.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

def main():
    DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)
    artifact_hash = build()
    print("BUILD_OK", artifact_hash)
    deploy(artifact_hash)
    print("DEPLOY_OK")
    proc = start_server()
    try:
        if not health_check():
            raise RuntimeError("health check failed")
        print("HEALTH_OK")
        if not smoke_test():
            raise RuntimeError("smoke test failed")
        print("SMOKE_OK")
    finally:
        stop_server(proc)
    print("PIPELINE_OK")

if __name__ == "__main__":
    main()
