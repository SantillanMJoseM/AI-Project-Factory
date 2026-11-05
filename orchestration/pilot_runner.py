#!/usr/bin/env python3
"""Pilot runner for ProjectDesk.

Runs Factory tasks for the ProjectDesk project sequentially, invokes the
assigned agent through the sandboxed OpenCode adapter, commits deliverables,
and records execution results.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import orchestration.runtime.runtime as rt
from orchestration.runtime.opencode_adapter import OpenCodeAdapter

DB_PATH = Path("/tmp/opencode/worktrees/projectdesk/.factory/runtime.db")
PROJECT_ID = "PROJECT-001"
MODEL = os.environ.get("APF_MODEL", "opencode-go/qwen3.8-flash")


def git_commit(worktree, message, allow_empty=False):
    subprocess.run(["git", "add", "."], cwd=worktree, check=False)
    cmd = ["git", "commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")
    r = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True)
    if r.returncode != 0 and "nothing to commit" not in r.stdout.lower() and "nothing to commit" not in r.stderr.lower():
        print("git commit warning:", r.stderr)
    return r.returncode == 0


def build_prompt(task, project, previous_outputs):
    deps = json.loads(task["dependencies"] or "[]")
    dep_context = ""
    if deps and previous_outputs:
        dep_context = "\n\nInputs from previous tasks:\n"
        for dep_id in deps:
            if dep_id in previous_outputs:
                dep_context += f"\n--- {dep_id} ---\n{previous_outputs[dep_id][:2000]}\n"

    prompt = f"""You are {task['agent_id']} working on the ProjectDesk pilot project.

Project: {project['name']}
Repository: {project['repo_path']}
Task: {task['title']}
Objective: {task['objective']}

Instructions:
- Work only in the current directory: {project['repo_path']}
- Do not read or write files outside this directory.
- Produce all deliverables as files inside this directory.
- Use Python Flask, SQLite (stdlib or SQLAlchemy), and Jinja2 templates unless the task is analysis/review.
- For analysis/review tasks, write markdown documents under docs/.
- For code tasks, write runnable code and update README.md as needed.
- After finishing, report the files you created or modified and any tests you ran.
- Keep the implementation small, focused, and working.
{dep_context}

Begin the task now.
"""
    return prompt


def main():
    os.environ["APF_DB_PATH"] = str(DB_PATH)
    conn = rt.get_conn(str(DB_PATH))
    project = rt.get_project(conn, PROJECT_ID)
    worktree = Path(project["repo_path"])

    tasks = rt.list_tasks(conn, PROJECT_ID)
    pending = [t for t in tasks if t["status"] != "COMPLETED"]
    pending.sort(key=lambda t: t["task_id"])

    adapter = OpenCodeAdapter(use_sandbox=True, timeout=600, factory_root=ROOT)
    previous_outputs = {}

    for task in pending:
        tid = task["task_id"]
        agent_id = task["agent_id"].lower().replace("-", "-")
        print(f"\n=== {tid} :: {agent_id} :: {task['title']} ===")

        prompt = build_prompt(task, project, previous_outputs)
        eid, result = rt.run_task(conn, tid, prompt, adapter=adapter, model=MODEL)

        print("Status:", result["status"])
        if result.get("error"):
            print("Error:", result["error"][:500])
        previous_outputs[tid] = result.get("output", "")[:4000]

        # Pilot simplification: mark successful agent executions COMPLETED
        # immediately so downstream dependencies can proceed. In a gated
        # workflow this would be a human or AG-002 approval step.
        if result["status"] == "COMPLETED":
            rt.update_task_status(conn, tid, "COMPLETED", actor="AG-001", evidence=[eid])

        # Commit deliverables.
        commit_msg = f"{tid} {agent_id} {task['title']}"
        git_commit(worktree, commit_msg)

    conn.close()
    print("\n=== Pilot run complete ===")


if __name__ == "__main__":
    main()
