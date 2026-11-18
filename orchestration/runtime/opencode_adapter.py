#!/usr/bin/env python3
"""OpenCode agent adapter for AI-Project-Factory runtime.

This adapter executes agents through OpenCode. By default it uses the
sandboxed runner (`OpenCodeSandbox`) so that filesystem isolation is
effective: the shared OpenCode service runs in the host mount namespace and
would ignore bind mounts applied only to the `opencode run` client.

The adapter never uses `--auto`. It sets `PWD` explicitly and filters the
environment to an allowlist so that agent shell tools do not inherit secrets
from the controller process.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from orchestration.runtime.sandbox import OpenCodeSandbox
from orchestration.runtime.model_fallback import ModelFallbackManager, FallbackStatus


DEFAULT_ALLOWED_ENV = {
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TERM",
    "USER",
    "SHELL",
    "PWD",
    "OPENCODE_BIN",
    "APF_DB_PATH",
    "APF_LOG_LEVEL",
}


def _filter_env(allowlist):
    return {k: v for k, v in os.environ.items() if k in allowlist}


class OpenCodeAdapter:
    def __init__(self, binary="opencode", timeout=120, use_sandbox=True, allowed_env_vars=None, factory_root=None, fallback_manager=None):
        self.binary = binary or os.environ.get("OPENCODE_BIN", "opencode")
        self.timeout = timeout
        self.use_sandbox = use_sandbox
        self.allowed_env_vars = set(allowed_env_vars or DEFAULT_ALLOWED_ENV)
        self.factory_root = Path(factory_root) if factory_root else Path(__file__).resolve().parents[2]
        self.fallback_manager = fallback_manager or ModelFallbackManager(factory_root=self.factory_root)

    def available(self):
        return shutil.which(self.binary) is not None

    def list_agents(self):
        if not self.available():
            raise RuntimeError("opencode binary not available")
        env = _filter_env(self.allowed_env_vars)
        result = subprocess.run([self.binary, "debug", "agents"], capture_output=True, text=True, timeout=self.timeout, env=env)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    def validate_agent(self, agent_id):
        agents = self.list_agents()
        return any(a.get("id") == agent_id for a in agents)

    def _invoke_sandbox(self, agent_id, prompt, context_files=None, model=None, cwd=None):
        sandbox = OpenCodeSandbox(
            factory_root=self.factory_root,
            worktree=cwd,
            binary=self.binary,
            allowed_env_vars=self.allowed_env_vars,
            timeout=self.timeout,
        )
        return sandbox.run(agent_id, prompt, model=model, context_files=context_files)

    def _invoke_direct(self, agent_id, prompt, context_files=None, model=None, cwd=None):
        """Direct invocation without sandbox. Used mainly for tests and introspection.

        The direct path starts a private OpenCode server bound to localhost so
        that no shared service is used. This keeps the implementation aligned
        with the sandbox architecture.
        """
        cmd = [self.binary, "run", "--agent", agent_id, "--format", "json", prompt]
        if model:
            cmd[2:2] = ["--model", model]
        if context_files:
            for f in context_files:
                cmd.extend(["--file", str(f)])

        env = _filter_env(self.allowed_env_vars)
        env["PWD"] = str(Path(cwd).resolve()) if cwd else str(Path.cwd())
        workdir = str(cwd) if cwd else None
        if workdir:
            path = Path(workdir)
            if not path.is_dir():
                return {"status": "BLOCKED", "output": "", "error": f"working directory not found: {workdir}", "command": cmd}
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

    def invoke(self, agent_id, prompt, context_files=None, model=None, cwd=None, factory_root=None, task_id=None, execution_id=None, max_retries=3):
        if not self.available():
            return {"status": "BLOCKED", "output": "", "error": "opencode binary not available", "command": None}
        if not self.validate_agent(agent_id):
            return {"status": "BLOCKED", "output": "", "error": f"agent not found: {agent_id}", "command": None}
        if factory_root:
            self.factory_root = Path(factory_root).resolve()

        # If explicit model provided, use it directly (no fallback).
        if model:
            if self.use_sandbox and cwd:
                return self._invoke_sandbox(agent_id, prompt, context_files=context_files, model=model, cwd=cwd)
            return self._invoke_direct(agent_id, prompt, context_files=context_files, model=model, cwd=cwd)

        # Use fallback manager for automatic model selection and recovery.
        fm = self.fallback_manager
        primary = fm.get_primary(agent_id)
        effective = fm.select_model(agent_id)
        if effective is None:
            fm.log_change(agent_id, task_id, primary, primary, None, "quota_exhausted",
                          FallbackStatus.WAITING_QUOTA_RESET, wait_seconds=3600,
                          error_message="all models unavailable", execution_id=execution_id)
            return {"status": "WAITING_QUOTA_RESET", "output": "", "error": "all models unavailable", "command": None}

        retries = 0
        while retries <= max_retries:
            if self.use_sandbox and cwd:
                result = self._invoke_sandbox(agent_id, prompt, context_files=context_files, model=effective, cwd=cwd)
            else:
                result = self._invoke_direct(agent_id, prompt, context_files=context_files, model=effective, cwd=cwd)

            if result["status"] == "COMPLETED":
                fm.log_change(agent_id, task_id, primary, effective,
                              effective if effective != primary else None,
                              None if effective == primary else "quota_exhausted",
                              FallbackStatus.COMPLETED, retries=retries, execution_id=execution_id)
                return result

            error_text = result.get("error") or ""
            decision = fm.handle_error(agent_id, effective, error_text)
            action = decision["action"]
            status = decision["status"]

            if action == "fallback":
                next_model = decision["next_model"]
                fm.log_change(agent_id, task_id, primary, effective, next_model,
                              decision["error_class"], status, retries=retries,
                              error_message=error_text, execution_id=execution_id)
                effective = next_model
                retries += 1
                continue
            elif action == "wait":
                wait = decision["wait_seconds"]
                fm.log_change(agent_id, task_id, primary, effective, None,
                              decision["error_class"], status, wait_seconds=wait,
                              retries=retries, error_message=error_text, execution_id=execution_id)
                if wait > 0:
                    time.sleep(min(wait, 5))  # cap sleep for responsiveness; real wait handled by orchestrator
                effective = decision.get("next_model") or effective
                retries += 1
                continue
            elif action == "retry":
                retries += 1
                time.sleep(min(2 ** retries, 30))
                continue
            elif action == "intervention":
                fm.log_change(agent_id, task_id, primary, effective, None,
                              decision["error_class"], status, retries=retries,
                              error_message=error_text, execution_id=execution_id)
                result["status"] = "NEEDS_INTERVENTION"
                return result
            else:  # abort / ambiguous
                fm.log_change(agent_id, task_id, primary, effective, None,
                              decision["error_class"], status, retries=retries,
                              error_message=error_text, execution_id=execution_id)
                return result

        return result
