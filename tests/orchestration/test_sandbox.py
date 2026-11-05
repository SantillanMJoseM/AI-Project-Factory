#!/usr/bin/env python3
"""Tests for R5.2A sandbox and migration integrity."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import orchestration.runtime.runtime as rt
from orchestration.runtime.sandbox import OpenCodeSandbox


def _v3_schema_only(db_path):
    """Create a clean schema-version-3 database for migration tests."""
    conn = rt.connect(db_path)
    conn.executescript("""
    CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
    CREATE TABLE projects (project_id TEXT PRIMARY KEY, name TEXT NOT NULL, repo_path TEXT NOT NULL, technology TEXT, architecture TEXT, coordinator_agent TEXT NOT NULL, initial_commit TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE tasks (task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, agent_id TEXT NOT NULL, title TEXT NOT NULL, objective TEXT NOT NULL, priority TEXT NOT NULL, dependencies TEXT NOT NULL, acceptance_criteria TEXT NOT NULL, inputs TEXT NOT NULL, outputs TEXT NOT NULL, assigned_files TEXT NOT NULL, allowed_directories TEXT NOT NULL, git_branch TEXT, status TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 3, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, quality_gates TEXT NOT NULL DEFAULT '[]', stage TEXT, acceptance_verification_id TEXT);
    CREATE TABLE executions (execution_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT, agent_id TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, result TEXT, evidence TEXT NOT NULL, errors TEXT NOT NULL, inputs TEXT NOT NULL DEFAULT '[]', outputs TEXT NOT NULL DEFAULT '[]', tools_used TEXT NOT NULL DEFAULT '[]', decisions TEXT NOT NULL DEFAULT '[]', attempts INTEGER NOT NULL DEFAULT 1, "commit" TEXT, context TEXT, quality_gate_result_id TEXT, acceptance_verification_id TEXT, resumed_from TEXT);
    CREATE TABLE events (event_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, execution_id TEXT, event_type TEXT NOT NULL, actor TEXT NOT NULL, timestamp TEXT NOT NULL, previous_state TEXT, new_state TEXT, evidence_refs TEXT NOT NULL);
    CREATE TABLE workflows (workflow_id TEXT PRIMARY KEY, name TEXT NOT NULL, definition TEXT NOT NULL);
    CREATE TABLE workflow_runs (run_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, workflow_id TEXT NOT NULL, status TEXT NOT NULL, current_step TEXT, started_at TEXT NOT NULL, completed_at TEXT, results TEXT NOT NULL DEFAULT '[]', steps TEXT, definition_snapshot TEXT, resumed_count INTEGER NOT NULL DEFAULT 0, last_resumed_at TEXT);
    CREATE TABLE approvals (approval_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT, execution_id TEXT, action TEXT NOT NULL, environment TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, approved_by TEXT, approved_at TEXT, expires_at TEXT, binding_hash TEXT NOT NULL);
    CREATE TABLE audits (audit_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, execution_id TEXT, scope TEXT NOT NULL, auditor TEXT NOT NULL, artifacts TEXT NOT NULL, findings TEXT NOT NULL, verdict TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT NOT NULL, task_id TEXT, executor_agent TEXT, independence_verified INTEGER NOT NULL DEFAULT 0, content_hash TEXT, previous_audit_id TEXT, quality_gate_result_id TEXT);
    CREATE TABLE quality_gate_results (qg_result_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT, execution_id TEXT, certificate_path TEXT, evidence_dir TEXT, verdict TEXT NOT NULL, rules_violated TEXT NOT NULL DEFAULT '[]', certificate_verdict TEXT, gatekeeper TEXT, created_at TEXT NOT NULL);
    CREATE TABLE acceptance_verifications (verification_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, execution_id TEXT, criteria_results TEXT NOT NULL DEFAULT '[]', all_passed INTEGER NOT NULL DEFAULT 0, verified_by TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
    INSERT INTO schema_version(version, applied_at) VALUES (1,'x'),(2,'x'),(3,'x');
    """)
    conn.commit()
    return conn


def test_migration_4_atomic_on_failure():
    """Migration 4 must leave the database unchanged when it fails."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = _v3_schema_only(db_path)
    assert conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0] == 3
    assert "description" not in rt._columns(conn, "tasks")

    # Create a duplicate RUNNING execution condition that migration 4 must reject.
    pid = rt.register_project(conn, "MIG-TEST", "/tmp/mig-test")
    tid = rt.create_task(conn, pid, "AG-008", "t", "o")
    for i in range(2):
        conn.execute(
            "INSERT INTO executions(execution_id,project_id,task_id,agent_id,status,started_at,evidence,errors) VALUES (?,?,?,?,?,datetime('now'),'[]','[]')",
            (f"MIG-E{i}", pid, tid, "AG-008", "RUNNING"),
        )
    conn.commit()
    conn.close()

    conn = rt.connect(db_path)

    conn = rt.connect(db_path)
    try:
        rt._run_migration_4(conn)
        raise AssertionError("migration should have failed on duplicate RUNNING executions")
    except Exception as exc:
        assert "UNIQUE constraint failed" in str(exc)
    assert "description" not in rt._columns(conn, "tasks")
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='delegations'").fetchone()
    assert conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0] == 3
    conn.close()


def test_migration_4_idempotent_on_clean_db():
    """Migration 4 can be re-applied to an already-migrated database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = rt.get_conn(db_path)
    assert conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0] == 4
    conn.close()
    conn = rt.get_conn(db_path)
    assert conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0] == 4
    assert "description" in rt._columns(conn, "tasks")
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='delegations'").fetchone()
    conn.close()


def test_sandbox_private_server_reaches_model_layer():
    """Sandbox starts a private server and client connects to it."""
    if not shutil.which("unshare") or not shutil.which("opencode"):
        print("SKIP sandbox test: unshare or opencode unavailable")
        return
    with tempfile.TemporaryDirectory() as td:
        worktree = Path(td) / "wt"
        worktree.mkdir()
        sbx = OpenCodeSandbox(ROOT, worktree, timeout=120)
        result = sbx.run("ag-001-project-coordinator", "test", model="invalid-provider/none")
        assert result["status"] == "FAILED"
        # The only acceptable failure is model routing, not server/agent setup.
        assert "provider.no-route" in result["output"] or "no-route" in result.get("error", "") or "no-route" in result["output"]


def test_ag_001_subagent_restricted_to_factory_agents():
    """AG-001 cannot delegate outside the ag-* namespace."""
    if not shutil.which("opencode"):
        print("SKIP agent permission test: opencode unavailable")
        return
    result = subprocess.run(["opencode", "debug", "agents"], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    agents = json.loads(result.stdout)
    ag001 = next((a for a in agents if a.get("id") == "ag-001-project-coordinator"), None)
    assert ag001 is not None
    subagent_perms = [(p["resource"], p["effect"]) for p in ag001["permissions"] if p["action"] == "subagent"]
    assert ("ag-*", "allow") in subagent_perms
    assert ("*", "deny") in subagent_perms


def test_all_factory_agents_deny_execute():
    """No factory agent inherits Code Mode execution by default."""
    if not shutil.which("opencode"):
        print("SKIP execute permission test: opencode unavailable")
        return
    result = subprocess.run(["opencode", "debug", "agents"], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    for a in json.loads(result.stdout):
        if not a.get("id", "").startswith("ag-"):
            continue
        execute_effects = {p["effect"] for p in a["permissions"] if p["action"] == "execute"}
        assert "allow" not in execute_effects, f"{a['id']} allows execute"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
