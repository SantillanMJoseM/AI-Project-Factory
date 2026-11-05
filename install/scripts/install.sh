#!/bin/bash
# AI-Project-Factory — idempotent installation script for Debian 13 LXC.
# Usage: ./install/scripts/install.sh [FACTORY_DIR]
# Default FACTORY_DIR: /opt/ai-project-factory
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_DIR="${1:-/opt/ai-project-factory}"
REPO_URL="${APF_REPO_URL:-https://github.com/SantillanMJoseM/AI-Project-Factory.git}"
BRANCH="${APF_BRANCH:-feature/r5.2a-implementation}"

echo "=== AI-Project-Factory installer ==="
echo "Target directory: $FACTORY_DIR"
echo "Repository: $REPO_URL"
echo "Branch: $BRANCH"

# 1. System requirements
echo "[1/8] Checking system requirements..."
if [[ "$(id -u)" -eq 0 ]]; then
    echo "WARNING: Running as root. The runtime will drop privileges inside the sandbox, but it is safer to run as an unprivileged user."
fi

for cmd in git python3 unshare curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: required command not found: $cmd"
        echo "Install with: apt-get update && apt-get install -y git python3 util-linux curl"
        exit 1
    fi
done

PYVER="$(python3 --version | awk '{print $2}')"
PYMAJOR="${PYVER%%.*}"
PYMINOR="$(echo "$PYVER" | cut -d. -f2)"
if [[ "$PYMAJOR" -lt 3 || ( "$PYMAJOR" -eq 3 && "$PYMINOR" -lt 10 ) ]]; then
    echo "ERROR: Python 3.10+ required, found $PYVER"
    exit 1
fi

# 2. Clone or update Factory repository
echo "[2/8] Cloning/updating Factory repository..."
if [[ -d "$FACTORY_DIR/.git" ]]; then
    cd "$FACTORY_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    git clone --branch "$BRANCH" "$REPO_URL" "$FACTORY_DIR"
    cd "$FACTORY_DIR"
fi

# 3. OpenCode
echo "[3/8] Checking OpenCode..."
if ! command -v opencode >/dev/null 2>&1; then
    echo "OpenCode not found. Install it manually from https://opencode.ai and rerun."
    echo "Alternatively, if npm is available, run: npm install -g @opencode/cli"
    exit 1
fi
opencode --version

# 4. Provider configuration
echo "[4/8] Provider configuration..."
if [[ -z "${OPENCODE_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "WARNING: No provider API key detected in environment."
    echo "Set OPENCODE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY before running agents."
fi

# 5. Python dependencies
echo "[5/8] Installing Python dependencies..."
python3 -m pip install --upgrade pip
if [[ -f "$FACTORY_DIR/requirements.txt" ]]; then
    python3 -m pip install -r "$FACTORY_DIR/requirements.txt"
fi

# 6. Runtime database directory
echo "[6/8] Preparing runtime directories..."
mkdir -p "$FACTORY_DIR/orchestration/runtime"
mkdir -p "$FACTORY_DIR/projects"
mkdir -p /tmp/opencode/worktrees

# 7. Verify installation
echo "[7/8] Running verification..."
"$FACTORY_DIR/install/scripts/verify.sh" "$FACTORY_DIR"

# 8. Summary
echo "[8/8] Installation complete."
echo ""
echo "Next steps:"
echo "  cd $FACTORY_DIR"
echo "  export APF_DB_PATH=$FACTORY_DIR/orchestration/runtime/runtime.db"
echo "  python3 -m orchestration.runtime --help"
echo "  python3 tests/run_all.py"
echo ""
echo "To run the ProjectDesk pilot, see install/docs/PILOT_EXECUTION_GUIDE.md"
