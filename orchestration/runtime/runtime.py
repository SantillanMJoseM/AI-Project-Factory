#!/usr/bin/env python3
"""Persistent orchestration runtime for AI-Project-Factory."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("APF_DB_PATH", Path(__file__).resolve().parent / "runtime.db"))

PROJECT_STATES = ["REGISTERED", "ANALYSIS", "ARCHITECTURE", "DEVELOPMENT", "QUALITY", "SECURITY_REVIEW", "RELEASE_PREPARATION", "DEPLOYMENT", "COMPLETED", "BLOCKED", "FAILED", "CANCELLED"]
TASK_STATES = ["PENDING", "READY", "ASSIGNED", "RUNNING", "WAITING_APPROVAL", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"]

PROJECT_TRANSITIONS = {
    "REGISTERED": {"ANALYSIS", "CANCELLED"},
    "ANALYSIS": {"ARCHITECTURE", "BLOCKED", "FAILED", "CANCELLED"},
    "ARCHITECTURE": {"DEVELOPMENT", "BLOCKED", "FAILED", "CANCELLED"},
    "DEVELOPMENT": {"QUALITY", "BLOCKED", "FAILED", "CANCELLED"},
    "QUALITY": {"SECURITY_REVIEW", "BLOCKED", "FAILED", "CANCELLED"},
    "SECURITY_REVIEW": {"RELEASE_PREPARATION", "BLOCKED", "FAILED", "CANCELLED"},
    "RELEASE_PREPARATION": {"DEPLOYMENT", "BLOCKED", "FAILED", "CANCELLED"},
    "DEPLOYMENT": {"COMPLETED", "BLOCKED", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "BLOCKED": {"ANALYSIS", "ARCHITECTURE", "DEVELOPMENT", "QUALITY", "SECURITY_REVIEW", "RELEASE_PREPARATION", "DEPLOYMENT", "CANCELLED"},
    "FAILED": {"REGISTERED", "CANCELLED"},
    "CANCELLED": set(),
}

TASK_TRANSITIONS = {
    "PENDING": {"READY", "CANCELLED"},
    "READY": {"ASSIGNED", "CANCELLED"},
    "ASSIGNED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"WAITING_APPROVAL", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"},
    "WAITING_APPROVAL": {"RUNNING", "BLOCKED", "CANCELLED"},
    "BLOCKED": {"READY", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": {"READY", "CANCELLED"},
    "CANCELLED": set(),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def connect(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def init_db(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        repo_path TEXT NOT NULL,
        technology TEXT,
        architecture TEXT,
        coordinator_agent TEXT NOT NULL,
        initial_commit TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        title TEXT NOT NULL,
        objective TEXT NOT NULL,
        priority TEXT NOT NULL,
        dependencies TEXT NOT NULL,
        acceptance_criteria TEXT NOT NULL,
        inputs TEXT NOT NULL,
        outputs TEXT NOT NULL,
        assigned_files TEXT NOT NULL,
        allowed_directories TEXT NOT NULL,
        git_branch TEXT,
        status TEXT NOT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
    );
    CREATE TABLE IF NOT EXISTS executions (
        execution_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        task_id TEXT,
        workflow_id TEXT,
        agent_id TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        result TEXT,
        evidence TEXT NOT NULL,
        errors TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 1,
        "commit" TEXT,
        context TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
    );
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        execution_id TEXT,
        event_type TEXT NOT NULL,
        actor TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        previous_state TEXT,
        new_state TEXT,
        evidence_refs TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS workflows (
        workflow_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        definition TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS workflow_runs (
        run_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        workflow_id TEXT NOT NULL,
        status TEXT NOT NULL,
        current_step TEXT,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
    );
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        task_id TEXT,
        execution_id TEXT,
        action TEXT NOT NULL,
        environment TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        approved_by TEXT,
        approved_at TEXT,
        expires_at TEXT,
        binding_hash TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version(version, applied_at) VALUES (1, ?)", (now(),))
    # seed workflows
    if conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] == 0:
        wf = {
            "standard-delivery": ["analysis", "architecture", "development", "quality", "release"],
            "analysis-only": ["analysis"],
        }
        for wid, steps in wf.items():
            conn.execute("INSERT INTO workflows(workflow_id, name, definition) VALUES (?,?,?)",
                         (wid, wid, json.dumps({"steps": steps})))
    conn.commit()


def get_conn(db_path=None):
    conn = connect(db_path)
    init_db(conn)
    return conn


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def project_id(conn):
    rows = conn.execute("SELECT project_id FROM projects").fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r["project_id"].split("-")[-1]))
        except Exception:
            pass
    n = max(nums, default=0) + 1
    return f"PROJECT-{n:03d}"


def task_id(conn):
    rows = conn.execute("SELECT task_id FROM tasks").fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r["task_id"].split("-")[-1]))
        except Exception:
            pass
    n = max(nums, default=0) + 1
    return f"TASK-{n:04d}"


def execution_id(conn):
    rows = conn.execute("SELECT execution_id FROM executions").fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r["execution_id"].split("-")[-1]))
        except Exception:
            pass
    n = max(nums, default=0) + 1
    return f"EXEC-{n:04d}"


def approval_id(conn):
    rows = conn.execute("SELECT approval_id FROM approvals").fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r["approval_id"].split("-")[-1]))
        except Exception:
            pass
    n = max(nums, default=0) + 1
    return f"APPR-{n:04d}"


def event_id():
    return f"EVT-{uuid.uuid4().hex[:10].upper()}"


def log_event(conn, project_id, event_type, actor, previous_state=None, new_state=None, execution_id=None, evidence_refs=None):
    conn.execute(
        "INSERT INTO events(event_id, project_id, execution_id, event_type, actor, timestamp, previous_state, new_state, evidence_refs) VALUES (?,?,?,?,?,?,?,?,?)",
        (event_id(), project_id, execution_id, event_type, actor, now(), previous_state, new_state, json.dumps(evidence_refs or [])),
    )


def register_project(conn, name, repo_path, technology=None, architecture=None, coordinator_agent="AG-001", initial_commit=None):
    pid = project_id(conn)
    conn.execute(
        "INSERT INTO projects(project_id,name,repo_path,technology,architecture,coordinator_agent,initial_commit,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (pid, name, repo_path, technology, architecture, coordinator_agent, initial_commit, "REGISTERED", now(), now()),
    )
    log_event(conn, pid, "PROJECT_REGISTERED", coordinator_agent, None, "REGISTERED", None, [])
    conn.commit()
    return pid


def list_projects(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY project_id").fetchall()]


def get_project(conn, project_id):
    row = conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not row:
        raise ValueError("Project not found")
    return dict(row)


def update_project_status(conn, project_id, new_status, actor="AG-001", evidence=None):
    project = get_project(conn, project_id)
    old = project["status"]
    if new_status not in PROJECT_STATES:
        raise ValueError("Invalid project status")
    if new_status not in PROJECT_TRANSITIONS.get(old, set()):
        raise ValueError(f"Invalid project transition {old} -> {new_status}")
    conn.execute("UPDATE projects SET status=?, updated_at=? WHERE project_id=?", (new_status, now(), project_id))
    log_event(conn, project_id, "PROJECT_STATUS_CHANGED", actor, old, new_status, None, evidence or [])
    conn.commit()


def create_task(conn, project_id, agent_id, title, objective, priority="medium", dependencies=None, acceptance_criteria=None, inputs=None, outputs=None, assigned_files=None, allowed_directories=None, git_branch=None):
    get_project(conn, project_id)
    tid = task_id(conn)
    conn.execute(
        "INSERT INTO tasks(task_id,project_id,agent_id,title,objective,priority,dependencies,acceptance_criteria,inputs,outputs,assigned_files,allowed_directories,git_branch,status,retry_count,max_retries,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tid, project_id, agent_id, title, objective, priority, json.dumps(dependencies or []), json.dumps(acceptance_criteria or []), json.dumps(inputs or []), json.dumps(outputs or []), json.dumps(assigned_files or []), json.dumps(allowed_directories or []), git_branch, "PENDING", 0, 3, now(), now()),
    )
    log_event(conn, project_id, "TASK_CREATED", "AG-001", None, "PENDING", None, [tid])
    conn.commit()
    return tid


def list_tasks(conn, project_id=None):
    if project_id:
        rows = conn.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY task_id", (project_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY task_id").fetchall()
    return [dict(r) for r in rows]


def get_task(conn, task_id):
    row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if not row:
        raise ValueError("Task not found")
    return dict(row)


def task_dependencies_complete(conn, task):
    deps = json.loads(task["dependencies"])
    for dep in deps:
        dep_task = get_task(conn, dep)
        if dep_task["status"] != "COMPLETED":
            return False
    return True


def update_task_status(conn, task_id, new_status, actor="AG-001", evidence=None):
    task = get_task(conn, task_id)
    old = task["status"]
    if new_status not in TASK_STATES:
        raise ValueError("Invalid task status")
    if new_status not in TASK_TRANSITIONS.get(old, set()):
        raise ValueError(f"Invalid task transition {old} -> {new_status}")
    if new_status in {"READY", "RUNNING"} and not task_dependencies_complete(conn, task):
        raise ValueError("Task dependencies are not complete")
    conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE task_id=?", (new_status, now(), task_id))
    log_event(conn, task["project_id"], "TASK_STATUS_CHANGED", actor, old, new_status, None, evidence or [task_id])
    conn.commit()


def assign_task(conn, task_id, agent_id, actor="AG-001"):
    task = get_task(conn, task_id)
    if task["status"] not in {"PENDING", "READY", "BLOCKED", "FAILED"}:
        raise ValueError("Task cannot be assigned in current state")
    conn.execute("UPDATE tasks SET agent_id=?, status=?, updated_at=? WHERE task_id=?", (agent_id, "ASSIGNED", now(), task_id))
    log_event(conn, task["project_id"], "TASK_ASSIGNED", actor, task["status"], "ASSIGNED", None, [task_id, agent_id])
    conn.commit()


def create_execution(conn, project_id, task_id, agent_id, workflow_id=None, commit=None, context=None):
    eid = execution_id(conn)
    conn.execute(
        'INSERT INTO executions(execution_id,project_id,task_id,workflow_id,agent_id,status,started_at,completed_at,result,evidence,errors,attempts,"commit",context) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (eid, project_id, task_id, workflow_id, agent_id, "RUNNING", now(), None, None, json.dumps([]), json.dumps([]), 1, commit, context),
    )
    log_event(conn, project_id, "EXECUTION_STARTED", agent_id, None, "RUNNING", eid, [task_id] if task_id else [])
    conn.commit()
    return eid


def complete_execution(conn, execution_id, status, result=None, evidence=None, errors=None, commit=None):
    row = conn.execute("SELECT * FROM executions WHERE execution_id=?", (execution_id,)).fetchone()
    if not row:
        raise ValueError("Execution not found")
    conn.execute(
        'UPDATE executions SET status=?, completed_at=?, result=?, evidence=?, errors=?, "commit"=COALESCE(?,"commit") WHERE execution_id=?',
        (status, now(), result, json.dumps(evidence or []), json.dumps(errors or []), commit, execution_id),
    )
    log_event(conn, row["project_id"], "EXECUTION_COMPLETED", row["agent_id"], "RUNNING", status, execution_id, evidence or [])
    conn.commit()


def list_executions(conn, project_id=None):
    if project_id:
        rows = conn.execute("SELECT * FROM executions WHERE project_id=? ORDER BY started_at", (project_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM executions ORDER BY started_at").fetchall()
    return [dict(r) for r in rows]


def recover_interrupted(conn):
    rows = conn.execute("SELECT * FROM executions WHERE status='RUNNING'").fetchall()
    recovered = []
    for row in rows:
        conn.execute("UPDATE executions SET status='INTERRUPTED', completed_at=?, errors=? WHERE execution_id=?",
                     (now(), json.dumps(["interrupted"]), row["execution_id"]))
        log_event(conn, row["project_id"], "EXECUTION_INTERRUPTED", "RUNTIME", "RUNNING", "INTERRUPTED", row["execution_id"], [])
        if row["task_id"]:
            task = get_task(conn, row["task_id"])
            if task["status"] == "RUNNING":
                conn.execute("UPDATE tasks SET status='BLOCKED', updated_at=? WHERE task_id=?", (now(), row["task_id"]))
                log_event(conn, row["project_id"], "TASK_BLOCKED", "RUNTIME", "RUNNING", "BLOCKED", None, [row["task_id"]])
        recovered.append(row["execution_id"])
    conn.commit()
    return recovered


def seed_workflows(conn):
    if conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] == 0:
        workflows = {
            "standard-delivery": ["analysis", "architecture", "development", "quality", "release"],
            "analysis-only": ["analysis"],
        }
        for wid, steps in workflows.items():
            conn.execute("INSERT INTO workflows(workflow_id,name,definition) VALUES (?,?,?)", (wid, wid, json.dumps({"steps": steps})))


def start_workflow(conn, project_id, workflow_id, actor="AG-001"):
    get_project(conn, project_id)
    row = conn.execute("SELECT * FROM workflows WHERE workflow_id=?", (workflow_id,)).fetchone()
    if not row:
        raise ValueError("Workflow not found")
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("INSERT INTO workflow_runs(run_id,project_id,workflow_id,status,current_step,started_at,completed_at) VALUES (?,?,?,?,?,?,?)",
                 (run_id, project_id, workflow_id, "RUNNING", json.loads(row["definition"])["steps"][0], now(), None))
    log_event(conn, project_id, "WORKFLOW_STARTED", actor, None, "RUNNING", None, [workflow_id, run_id])
    conn.commit()
    return run_id


def workflow_status(conn, run_id):
    row = conn.execute("SELECT * FROM workflow_runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        raise ValueError("Workflow run not found")
    return dict(row)


def list_workflows(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM workflows ORDER BY workflow_id").fetchall()]


def create_approval(conn, project_id, action, environment, description, task_id=None, execution_id=None, actor="AG-003"):
    aid = approval_id(conn)
    binding = json.dumps({"project_id": project_id, "action": action, "environment": environment, "description": description}, sort_keys=True)
    binding_hash = __import__("hashlib").sha256(binding.encode()).hexdigest()
    conn.execute(
        "INSERT INTO approvals(approval_id,project_id,task_id,execution_id,action,environment,description,status,approved_by,approved_at,expires_at,binding_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (aid, project_id, task_id, execution_id, action, environment, description, "PENDING", None, None, None, binding_hash),
    )
    log_event(conn, project_id, "APPROVAL_REQUESTED", actor, None, "PENDING", execution_id, [aid, action, environment])
    conn.commit()
    return aid


def approve(conn, approval_id, approved_by, actor="HUMAN"):
    row = conn.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
    if not row:
        raise ValueError("Approval not found")
    if row["status"] != "PENDING":
        raise ValueError("Approval is not pending")
    conn.execute("UPDATE approvals SET status='APPROVED', approved_by=?, approved_at=? WHERE approval_id=?", (approved_by, now(), approval_id))
    log_event(conn, row["project_id"], "APPROVAL_GRANTED", actor, "PENDING", "APPROVED", row["execution_id"], [approval_id, approved_by])
    conn.commit()


def consume_approval(conn, approval_id):
    row = conn.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
    if not row:
        raise ValueError("Approval not found")
    if row["status"] != "APPROVED":
        raise ValueError("Approval is not approved")
    conn.execute("UPDATE approvals SET status='CONSUMED' WHERE approval_id=?", (approval_id,))
    log_event(conn, row["project_id"], "APPROVAL_CONSUMED", "RUNTIME", "APPROVED", "CONSUMED", row["execution_id"], [approval_id])
    conn.commit()


def list_approvals(conn, project_id=None):
    if project_id:
        rows = conn.execute("SELECT * FROM approvals WHERE project_id=? ORDER BY approval_id", (project_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM approvals ORDER BY approval_id").fetchall()
    return [dict(r) for r in rows]


def evaluate_gate(conn, project_id, certificate_path=None, evidence_dir=None):
    # Import R1 runtime.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from orchestration.validators.quality_gate import evaluate as qg_evaluate
    import json as _json
    if not certificate_path:
        raise ValueError("certificate path required")
    cert = _json.loads(Path(certificate_path).read_text())
    result = qg_evaluate(cert, evidence_dir) if evidence_dir else {"verdict": cert.get("final_verdict", "FAIL"), "rules_violated": [], "exit_code": 0}
    log_event(conn, project_id, "QUALITY_GATE_EVALUATED", "AG-002", None, result["verdict"], None, [certificate_path])
    conn.commit()
    return result


def render(value, as_json=False):
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True, default=str))
    else:
        if isinstance(value, list):
            for item in value:
                print(item)
        elif isinstance(value, dict):
            for k, v in value.items():
                print(f"{k}: {v}")
        else:
            print(value)


def main():
    parser = argparse.ArgumentParser(description="AI-Project-Factory Orchestration Runtime")
    parser.add_argument("--db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    # project
    project = sub.add_parser("project")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    pr = project_sub.add_parser("register")
    pr.add_argument("--name", required=True)
    pr.add_argument("--repo", required=True)
    pr.add_argument("--technology")
    pr.add_argument("--architecture")
    pr.add_argument("--coordinator", default="AG-001")
    pr.add_argument("--initial-commit")
    pr.add_argument("--json", action="store_true")
    pl = project_sub.add_parser("list")
    pl.add_argument("--json", action="store_true")
    ps = project_sub.add_parser("status")
    ps.add_argument("project_id")
    ps.add_argument("--json", action="store_true")
    pi = project_sub.add_parser("inspect")
    pi.add_argument("project_id")
    pi.add_argument("--json", action="store_true")

    # task
    task = sub.add_parser("task")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    tc = task_sub.add_parser("create")
    tc.add_argument("--project", required=True)
    tc.add_argument("--agent", required=True)
    tc.add_argument("--title", required=True)
    tc.add_argument("--objective", required=True)
    tc.add_argument("--priority", default="medium")
    tc.add_argument("--dependencies", default="")
    tc.add_argument("--acceptance", default="")
    tc.add_argument("--files", default="")
    tc.add_argument("--dirs", default="")
    tc.add_argument("--branch")
    tc.add_argument("--json", action="store_true")
    tl = task_sub.add_parser("list")
    tl.add_argument("--project")
    tl.add_argument("--json", action="store_true")
    ti = task_sub.add_parser("inspect")
    ti.add_argument("task_id")
    ti.add_argument("--json", action="store_true")
    ta = task_sub.add_parser("assign")
    ta.add_argument("task_id")
    ta.add_argument("--agent", required=True)
    ta.add_argument("--json", action="store_true")
    tst = task_sub.add_parser("status")
    tst.add_argument("task_id")
    tst.add_argument("new_status")
    tst.add_argument("--actor", default="AG-001")
    tst.add_argument("--json", action="store_true")

    # workflow
    workflow = sub.add_parser("workflow")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    wl = workflow_sub.add_parser("list")
    wl.add_argument("--json", action="store_true")
    ws = workflow_sub.add_parser("start")
    ws.add_argument("project_id")
    ws.add_argument("workflow_id")
    ws.add_argument("--json", action="store_true")
    wst = workflow_sub.add_parser("status")
    wst.add_argument("run_id")
    wst.add_argument("--json", action="store_true")
    wr = workflow_sub.add_parser("resume")
    wr.add_argument("run_id")
    wr.add_argument("--json", action="store_true")

    # execution
    execution = sub.add_parser("execution")
    execution_sub = execution.add_subparsers(dest="execution_command", required=True)
    eh = execution_sub.add_parser("history")
    eh.add_argument("project_id")
    eh.add_argument("--json", action="store_true")

    # gate
    gate = sub.add_parser("gate")
    gate_sub = gate.add_subparsers(dest="gate_command", required=True)
    ge = gate_sub.add_parser("evaluate")
    ge.add_argument("--project", required=True)
    ge.add_argument("--certificate", required=True)
    ge.add_argument("--evidence-dir")
    ge.add_argument("--json", action="store_true")

    # approval
    approval = sub.add_parser("approval")
    approval_sub = approval.add_subparsers(dest="approval_command", required=True)
    ar = approval_sub.add_parser("request")
    ar.add_argument("--project", required=True)
    ar.add_argument("--action", required=True)
    ar.add_argument("--environment", required=True)
    ar.add_argument("--description", required=True)
    ar.add_argument("--task")
    ar.add_argument("--execution")
    ar.add_argument("--json", action="store_true")
    aa = approval_sub.add_parser("approve")
    aa.add_argument("approval_id")
    aa.add_argument("--by", required=True)
    aa.add_argument("--json", action="store_true")
    al = approval_sub.add_parser("list")
    al.add_argument("--project")
    al.add_argument("--json", action="store_true")

    # recovery
    rec = sub.add_parser("recover")
    rec.add_argument("--json", action="store_true")

    args = parser.parse_args()
    conn = get_conn(args.db)
    try:
        result = dispatch(conn, args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 3
    finally:
        conn.close()
    return 0 if result is None else result


def dispatch(conn, args):
    if args.command == "project":
        if args.project_command == "register":
            pid = register_project(conn, args.name, args.repo, args.technology, args.architecture, args.coordinator, args.initial_commit)
            out = {"project_id": pid}
            render(out, args.json)
            return 0
        if args.project_command == "list":
            out = list_projects(conn)
            render(out, args.json)
            return 0
        if args.project_command == "status":
            p = get_project(conn, args.project_id)
            render(p, args.json)
            return 0
        if args.project_command == "inspect":
            p = get_project(conn, args.project_id)
            tasks = list_tasks(conn, args.project_id)
            execs = list_executions(conn, args.project_id)
            evs = conn.execute("SELECT * FROM events WHERE project_id=? ORDER BY timestamp", (args.project_id,)).fetchall()
            out = {"project": p, "tasks": tasks, "executions": execs, "events": [dict(e) for e in evs]}
            render(out, args.json)
            return 0
    if args.command == "task":
        if args.task_command == "create":
            deps = [x for x in args.dependencies.split(",") if x]
            acc = [x for x in args.acceptance.split(";") if x]
            files = [x for x in args.files.split(",") if x]
            dirs = [x for x in args.dirs.split(",") if x]
            tid = create_task(conn, args.project, args.agent, args.title, args.objective, args.priority, deps, acc, [], [], files, dirs, args.branch)
            render({"task_id": tid}, args.json)
            return 0
        if args.task_command == "list":
            tasks = list_tasks(conn, args.project)
            render(tasks, args.json)
            return 0
        if args.task_command == "inspect":
            t = get_task(conn, args.task_id)
            render(t, args.json)
            return 0
        if args.task_command == "assign":
            assign_task(conn, args.task_id, args.agent)
            render({"task_id": args.task_id, "agent_id": args.agent}, args.json)
            return 0
        if args.task_command == "status":
            update_task_status(conn, args.task_id, args.new_status, args.actor)
            render({"task_id": args.task_id, "status": args.new_status}, args.json)
            return 0
    if args.command == "workflow":
        if args.workflow_command == "list":
            render(list_workflows(conn), args.json)
            return 0
        if args.workflow_command == "start":
            rid = start_workflow(conn, args.project_id, args.workflow_id)
            render({"run_id": rid}, args.json)
            return 0
        if args.workflow_command == "status":
            render(workflow_status(conn, args.run_id), args.json)
            return 0
        if args.workflow_command == "resume":
            r = workflow_status(conn, args.run_id)
            render(r, args.json)
            return 0
    if args.command == "execution":
        if args.execution_command == "history":
            render(list_executions(conn, args.project_id), args.json)
            return 0
    if args.command == "gate":
        if args.gate_command == "evaluate":
            result = evaluate_gate(conn, args.project, args.certificate, args.evidence_dir)
            render(result, args.json)
            return 0 if result["verdict"] in {"PASS", "PASS_WITH_OBSERVATIONS"} else (2 if result["verdict"] == "BLOCKED" else 1)
    if args.command == "approval":
        if args.approval_command == "request":
            aid = create_approval(conn, args.project, args.action, args.environment, args.description, args.task, args.execution)
            render({"approval_id": aid}, args.json)
            return 0
        if args.approval_command == "approve":
            approve(conn, args.approval_id, args.by)
            render({"approval_id": args.approval_id, "status": "APPROVED"}, args.json)
            return 0
        if args.approval_command == "list":
            render(list_approvals(conn, args.project), args.json)
            return 0
    if args.command == "recover":
        recovered = recover_interrupted(conn)
        render({"recovered_executions": recovered}, args.json)
        return 0
    raise ValueError("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
