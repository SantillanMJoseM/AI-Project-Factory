# LXC Fresh Install Guide — AI-Project-Factory

## Prerequisites

- OS: Ubuntu 22.04+ or Debian 12+.
- User: developer (non-root).
- Python 3.10+.
- OpenCode CLI v2.x.
- unshare (user namespaces).
- Git.
- Network access for Beam Free provider.

## Steps

1. Clone repository:
   `git clone https://github.com/SantillanMJoseM/AI-Project-Factory.git && cd AI-Project-Factory`
2. Checkout main:
   `git checkout main`
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
9. Configure env:
   `cp .env.example .env` and edit with your OPENCODE_API_KEY.

## BEAM_FREE_ONLY enforcement checklist

- opencode.json model = opencode-go/beam-free.
- No ollama provider block.
- All .opencode/agents/*.md model = opencode-go/beam-free.
- Runtime rejects non-authorized models.

## Post-install verification

- `opencode debug agents` → 19 agents.
- `python3 tests/run_all.py` → PASS.
- `bash install/scripts/verify.sh` → PASS.

## Notes

- Do not modify host Proxmox or other containers.
- Do not restart active OpenCode service.
- Use /tmp/opencode for temporary files.
- Preserve all untracked artifacts (do not git clean).