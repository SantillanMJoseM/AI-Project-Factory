# Stage 2H — LXC Clean Install Procedure (Static Review)

Date: 2026-11-23
Status: NOT_EXECUTED (no second LXC available; procedure documented for authorized run)

## Prerequisites

- OS: Linux (Ubuntu 22.04+ or Debian 12+).
- User: developer (non-root). No global OpenCode config changes.
- Python 3.10+ (verified 3.13 in current env).
- OpenCode CLI installed (verified v2.x).
- `unshare` available (user namespaces enabled).
- Git installed.
- Network access for OpenCode model provider (beam-free).

## Steps

1. Clone repository:
   `git clone <repo-url> AI-Project-Factory && cd AI-Project-Factory`
2. Checkout branch:
   `git checkout feature/model-fallback-manager`
3. Verify Python:
   `python3 --version`
4. Verify OpenCode:
   `opencode --version && opencode debug agents`
5. Verify model policy:
   `opencode debug agents | python3 -c "import sys,json; d=json.load(sys.stdin); ag=[a for a in d if a['id'].startswith('ag-')]; print(set(a['model']['providerID']+'/'+a['model']['id'] for a in ag))"` → must show only opencode-go/beam-free.
6. Run factory tests:
   `python3 tests/run_all.py` → ALL TESTS PASSED.
7. Run install verification:
   `bash install/scripts/verify.sh` → ALL CHECKS PASSED.
8. Verify SQLite:
   `python3 -c "import sqlite3; print(sqlite3.connect('orchestration/runtime/runtime.db').execute('PRAGMA integrity_check').fetchone())"` → ok.
9. Functional smoke (optional, quota permitting):
   `python3 -c "import orchestration.runtime.runtime as rt; ..."` (register project, create task, run_task, verify beam-free).
10. Confirm no Ollama provider in opencode.json.

## BEAM_FREE_ONLY enforcement checklist

- opencode.json model = opencode-go/beam-free.
- No ollama provider block.
- All .opencode/agents/*.md model = opencode-go/beam-free.
- runtime.py rejects non-authorized models.
- opencode_adapter.py rejects non-authorized models.

## Post-install verification

- `opencode debug agents` → 19 agents.
- `python3 tests/run_all.py` → PASS.
- `bash install/scripts/verify.sh` → PASS.

## Notes

- Do not modify host Proxmox or other containers.
- Do not restart active OpenCode service.
- Use /tmp/opencode for temporary files.
- Preserve all untracked artifacts (do not git clean).