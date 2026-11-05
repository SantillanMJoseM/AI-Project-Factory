# AI-Project-Factory — Installation Guide

This guide installs AI-Project-Factory on a clean Debian 13 system (LXC or VM).

## Quick start

```bash
# 1. Install Debian packages
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv curl util-linux

# 2. Install OpenCode v2.2.5
# Follow https://opencode.ai or use npm if available:
# npm install -g @opencode/cli@2.2.5

# 3. Set provider API key (example: OpenCode/Beam)
export OPENCODE_API_KEY="your-key-here"

# 4. Run installer
bash install/scripts/install.sh /opt/ai-project-factory
```

## What the installer does

1. Checks system requirements (Python 3.10+, git, unshare, curl).
2. Clones or updates the Factory repository.
3. Verifies OpenCode is installed.
4. Installs Python dependencies from `requirements.txt` if present.
5. Creates runtime directories.
6. Runs the verification script.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `APF_REPO_URL` | No | Factory repository URL (default: GitHub). |
| `APF_BRANCH` | No | Branch to install (default: `feature/r5.2a-implementation`). |
| `APF_DB_PATH` | No | SQLite database path (default: `orchestration/runtime/runtime.db`). |
| `OPENCODE_API_KEY` | Yes* | Provider API key. Name depends on provider. |

*Provider key names vary. Set the variable required by your provider.

## Verification

```bash
bash install/scripts/verify.sh /opt/ai-project-factory
```

## Next steps

- Configure the provider: see `CONFIGURATION_GUIDE.md`.
- Run the pilot: see `PILOT_EXECUTION_GUIDE.md`.
- Troubleshoot: see `TROUBLESHOOTING.md`.
