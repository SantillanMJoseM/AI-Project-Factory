#!/usr/bin/env python3
"""OpenCode agent adapter for AI-Project-Factory runtime."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class OpenCodeAdapter:
    def __init__(self, binary="opencode", timeout=120):
        self.binary = binary or os.environ.get("OPENCODE_BIN", "opencode")
        self.timeout = timeout

    def available(self):
        return shutil.which(self.binary) is not None

    def list_agents(self):
        if not self.available():
            raise RuntimeError("opencode binary not available")
        result = subprocess.run([self.binary, "debug", "agents"], capture_output=True, text=True, timeout=self.timeout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    def validate_agent(self, agent_id):
        agents = self.list_agents()
        return any(a.get("id") == agent_id for a in agents)

    def invoke(self, agent_id, prompt, context_files=None, model=None, cwd=None, factory_root=None):
        if not self.available():
            return {"status": "BLOCKED", "output": "", "error": "opencode binary not available", "command": None}
        if not self.validate_agent(agent_id):
            return {"status": "BLOCKED", "output": "", "error": f"agent not found: {agent_id}", "command": None}
        cmd = [self.binary, "run", "--agent", agent_id, "--format", "json", "--auto", prompt]
        if model:
            cmd[2:2] = ["--model", model]
        if context_files:
            for f in context_files:
                cmd.extend(["--file", str(f)])
        env = dict(os.environ)
        if factory_root:
            env["OPENCODE_CONFIG_DIR"] = str(factory_root)
        workdir = str(cwd) if cwd else None
        if workdir:
            path = Path(workdir)
            if not path.is_dir():
                return {"status": "BLOCKED", "output": "", "error": f"working directory not found: {workdir}", "command": None}
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, cwd=workdir, env=env)
            status = "COMPLETED" if result.returncode == 0 else "FAILED"
            return {
                "status": status,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "command": cmd,
                "cwd": workdir,
            }
        except subprocess.TimeoutExpired:
            return {"status": "FAILED", "output": "", "error": "timeout", "command": cmd, "cwd": workdir}
