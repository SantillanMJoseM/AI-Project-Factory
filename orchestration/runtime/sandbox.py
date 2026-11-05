#!/usr/bin/env python3
"""Sandboxed OpenCode execution with private server inside unshare namespace.

The shared OpenCode service runs in the host mount namespace, so any bind
mounts or tmpfs applied only to the `opencode run` client are ignored by the
service that actually executes agent tools. This module starts a private
OpenCode server inside a user+mount namespace so that filesystem isolation is
effective for the tools themselves.

Network isolation is intentionally partial: the server must reach the model
provider (Beam), so no network namespace is used by default. Agent tool network
access is controlled by OpenCode permissions (webfetch/websearch/execute deny)
and by the environment allowlist.
"""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Environment variables passed into the sandbox server/client.
# Provider credentials are deliberately absent from this allowlist;
# they are injected only for the server process via secure env keys.
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
    "OPENCODE_PASSWORD",
}

# Paths hidden from the agent by mounting an empty tmpfs over them.
MASKED_PATHS = [
    "/mnt/proyectos",
]

# Sensitive home subdirectories masked read-only (if they exist).
SENSITIVE_HOME_DIRS = [
    ".ssh",
    ".aws",
    ".gnupg",
    ".docker",
    ".kube",
    ".npmrc",
    ".netrc",
    ".pgpass",
]


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _filter_env(allowlist):
    return {k: v for k, v in os.environ.items() if k in allowlist}


def _build_sandbox_script(factory_root, worktree, server_port, password, binary, model, agent_id, prompt, context_files, server_env):
    """Build a bash script that sets up the namespace and runs the agent."""
    factory_root = Path(factory_root).resolve()
    worktree = Path(worktree).resolve()
    sbx = Path("/tmp/sbx") / secrets.token_hex(8)

    binds = []
    for src_rel in [
        "agents",
        "contracts",
        "schemas",
        "standards",
        "orchestration",
        "quality-gates",
        "templates",
        "docs/audits",
        ".opencode/agents",
    ]:
        src = factory_root / src_rel
        if src.exists():
            dst = sbx / "factory" / src_rel
            binds.append(f"mkdir -p {dst.parent}")
            binds.append(f"mkdir -p {dst}")
            binds.append(f"mount --bind {src} {dst}")
            binds.append(f"mount -o remount,ro,bind {dst}")

    mask_cmds = []
    for p in MASKED_PATHS:
        mask_cmds.append(f"mount -t tmpfs tmpfs {p} 2>/dev/null || true")

    home_masks = []
    for d in SENSITIVE_HOME_DIRS:
        p = Path.home() / d
        if p.exists():
            home_masks.append(f"mount -t tmpfs tmpfs {p} 2>/dev/null || true")

    # PWD is set explicitly to the worktree below; do not include it in the
    # generic env_exports so it cannot be overridden by the parent environment.
    env_exports = "\n".join(
        f"export {k}={shlex_quote(v)}" for k, v in server_env.items() if k != "PWD"
    )

    context_flags = ""
    if context_files:
        for cf in context_files:
            context_flags += f' --file {shlex_quote(str(cf))}'

    model_flags = f"--model {shlex_quote(model)}" if model else ""

    # The server is started inside the namespace and inherits the namespace
    # mounts, so tool execution respects the isolation.
    script = f"""#!/bin/bash
set -u
SBOX={sbx}
WORKTREE={worktree}
PORT={server_port}
PASSWORD={password}
BINARY={binary}

# User + mount namespace is already created by unshare; create sandbox dirs.
mkdir -p "$SBOX"/factory "$SBOX"/tmp

# Bind factory normative dirs read-only into sandbox BEFORE masking the source tree.
{'\n'.join(binds)}

# Copy root config files before masking the source tree.
if [ -f {shlex_quote(str(factory_root / "opencode.json"))} ]; then
    cp {shlex_quote(str(factory_root / "opencode.json"))} "$SBOX/factory/opencode.json"
fi
if [ -f {shlex_quote(str(factory_root / "AGENTS.md"))} ]; then
    cp {shlex_quote(str(factory_root / "AGENTS.md"))} "$SBOX/factory/AGENTS.md"
fi

# Mask factory tree and sensitive paths.
{'\n'.join(mask_cmds)}

# Mask sensitive home dirs.
{'\n'.join(home_masks)}

# Materialize OpenCode configuration into the worktree.
mkdir -p "$WORKTREE/.opencode/agents"
if [ -d "$SBOX/factory/.opencode/agents" ]; then
    cp -r "$SBOX/factory/.opencode/agents/"*.md "$WORKTREE/.opencode/agents/"
fi
if [ -f "$SBOX/factory/opencode.json" ]; then
    cp "$SBOX/factory/opencode.json" "$WORKTREE/opencode.json"
fi

# Ensure worktree exists and is writable.
cd "$WORKTREE"
export PWD="$WORKTREE"

# Restrict environment for the server and client.
{env_exports}
export OPENCODE_PASSWORD="$PASSWORD"

# Start private OpenCode server.
"$BINARY" serve --hostname 127.0.0.1 --port "$PORT" > "$SBOX"/server.log 2>&1 &
SERVER_PID=$!

# Wait for server.
for i in $(seq 1 30); do
    if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
        break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "SERVER_EXITED" >&2
        cat "$SBOX"/server.log >&2
        exit 90
    fi
    sleep 0.5
done

# Run client against private server.
"$BINARY" run --server "http://127.0.0.1:$PORT" --agent {shlex_quote(agent_id)} {model_flags} --format json {context_flags} -- {shlex_quote(prompt)} < /dev/null

RC=$?
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
exit $RC
"""
    return script


def shlex_quote(s):
    # Minimal shlex quote for our controlled inputs.
    if s and all(c.isalnum() or c in "_-,./:@" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


class OpenCodeSandbox:
    def __init__(self, factory_root, worktree, binary=None, allowed_env_vars=None, timeout=240):
        self.factory_root = Path(factory_root).resolve()
        self.worktree = Path(worktree).resolve()
        self.binary = binary or os.environ.get("OPENCODE_BIN", "opencode")
        self.allowed_env_vars = set(allowed_env_vars or DEFAULT_ALLOWED_ENV)
        self.timeout = timeout

    def available(self):
        return shutil.which(self.binary) is not None and shutil.which("unshare") is not None

    def _make_server_env(self, provider_env=None):
        env = _filter_env(self.allowed_env_vars)
        if provider_env:
            env.update(provider_env)
        return env

    def run(self, agent_id, prompt, model=None, context_files=None, provider_env=None):
        if not self.available():
            return {"status": "BLOCKED", "output": "", "error": "opencode or unshare not available", "command": None}
        if not self.worktree.is_dir():
            return {"status": "BLOCKED", "output": "", "error": f"working directory not found: {self.worktree}", "command": None}

        server_port = _free_port()
        password = secrets.token_urlsafe(32)
        server_env = self._make_server_env(provider_env)
        script = _build_sandbox_script(
            factory_root=self.factory_root,
            worktree=self.worktree,
            server_port=server_port,
            password=password,
            binary=self.binary,
            model=model,
            agent_id=agent_id,
            prompt=prompt,
            context_files=context_files,
            server_env=server_env,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script)
            script_path = f.name
        os.chmod(script_path, 0o700)

        cmd = ["unshare", "-Urm", "/bin/bash", script_path]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=server_env,
            )
        except subprocess.TimeoutExpired:
            return {"status": "FAILED", "output": "", "error": "sandbox timeout", "command": cmd}
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

        # Parse JSONL output.
        events = []
        for line in result.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except Exception:
                pass

        status = "COMPLETED" if result.returncode == 0 else "FAILED"
        error = result.stderr if result.returncode != 0 else None
        return {
            "status": status,
            "output": result.stdout,
            "error": error,
            "command": cmd,
            "events": events,
            "cwd": str(self.worktree),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sandboxed OpenCode agent runner")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--model")
    parser.add_argument("--prompt", default="Respond with exactly: SANDBOX_OK")
    parser.add_argument("--file", action="append", dest="context_files")
    args = parser.parse_args()
    sbx = OpenCodeSandbox(args.factory_root, args.worktree)
    res = sbx.run(args.agent, args.prompt, model=args.model, context_files=args.context_files)
    print(json.dumps({"status": res["status"], "error": res["error"], "stdout_preview": res["output"][:500]}, indent=2))
    sys.exit(0 if res["status"] == "COMPLETED" else 1)
