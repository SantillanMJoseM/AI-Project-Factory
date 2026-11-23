#!/bin/bash
# Verification script for AI-Project-Factory installation.
set -euo pipefail

FACTORY_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$FACTORY_DIR"

FAILED=0

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  PASS: $name"
    else
        echo "  FAIL: $name"
        FAILED=1
    fi
}

echo "=== AI-Project-Factory installation verification ==="

echo "[1/6] Runtime files..."
check "Factory directory exists" test -d "$FACTORY_DIR"
check "Runtime module exists" test -f "$FACTORY_DIR/orchestration/runtime/runtime.py"
check "Sandbox module exists" test -f "$FACTORY_DIR/orchestration/runtime/sandbox.py"
check "Adapter module exists" test -f "$FACTORY_DIR/orchestration/runtime/opencode_adapter.py"

echo "[2/6] Agent definitions..."
check "Normative agents directory" test -d "$FACTORY_DIR/agents"
check "OpenCode agents directory" test -d "$FACTORY_DIR/.opencode/agents"
check "18 OpenCode agents" bash -c "test \$(ls -1 $FACTORY_DIR/.opencode/agents/*.md | wc -l) -ge 18"

echo "[3/6] OpenCode..."
check "OpenCode binary" command -v opencode
check "OpenCode version" bash -c "opencode --version | grep -q 'opencode v'"
check "Agents load" bash -c "opencode debug agents | python3 -m json.tool >/dev/null"

echo "[4/6] Python..."
check "Python 3" command -v python3
check "Runtime imports" python3 -c "import orchestration.runtime.runtime; import orchestration.runtime.sandbox; import orchestration.runtime.opencode_adapter"

echo "[5/6] Tests..."
check "Test suite runs" python3 tests/run_all.py

echo "[6/6] Sandbox..."
check "unshare available" command -v unshare
check "User namespaces" bash -c "unshare -Urm true"

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo "=== ALL VERIFICATION CHECKS PASSED ==="
    exit 0
else
    echo "=== SOME VERIFICATION CHECKS FAILED ==="
    exit 1
fi
