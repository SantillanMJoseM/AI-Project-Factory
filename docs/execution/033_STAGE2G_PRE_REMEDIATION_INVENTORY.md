# Stage 2G — Pre-Remediation Inventory (Phase 0)

Date: 2026-11-23
Coordinator: AG-001 Project Coordinator
Mode: READ-ONLY inventory + backup. No remediation applied in this phase.

## 1. Environment identity (verified)

| Field | Value |
|---|---|
| User | `developer02` |
| Repository path | `/home/developer02/projects/AI-Project-Factory` |
| OpenCode | `v2.4.1` |
| Branch | `main` |
| HEAD | `5f63b74ca0f54596ff83b1cdd5df02480b7a34da` |
| Remote | `origin https://github.com/SantillanMJoseM/AI-Project-Factory.git` |
| Working tree | 9 tracked modified + 6 untracked (reconciliation edits, uncommitted) |

No mismatch with authorized environment. No external environments mixed.

## 2. Repository inventory (non-destructive)

| Item | Count |
|---|---|
| Tracked files | 672 |
| Untracked files | 6 |
| Tracked modified | 9 |
| Normative agents (`agents/`) | 18 (AG-001..AG-018) |
| Executable agents (`.opencode/agents/`) | 19 (AG-003 has 2 specializations) |
| Skills (`.opencode/skills/`) | 54 (all with SKILL.md) |
| Test files (`tests/**/*.py`) | 39 |
| Docs files (`docs/`) | 100+ |
| SQLite DB files in repo | 0 (runtime.db is gitignored and not present) |
| OpenCode processes | serve (PID 379), cli (PID 1062), pty daemon (PID 1154) — not restarted |

## 3. Modified (tracked) files (pre-remediation)

1. CHANGELOG.md
2. PROJECT_CONTEXT.md
3. PROJECT_STATUS.md
4. README.md
5. docs/architecture/MODEL_FALLBACK_DESIGN.md
6. docs/architecture/MODEL_FALLBACK_IMPLEMENTATION.md
7. docs/architecture/MODEL_FALLBACK_VALIDATION.md
8. tests/integration/test_end_to_end.py
9. tests/orchestration/test_structure.py

## 4. Untracked files

1. docs/execution/RECON-018-DOCS-003.md
2. tests/fixtures/skills/drift-baseline.json
3. tests/fixtures/skills/invalid-skill/SKILL.md
4. tests/fixtures/skills/registry.json
5. tests/fixtures/skills/valid-skill/SKILL.md
6. tests/fixtures/skills/valid-skill/references/guide.md

## 5. Backup

- Location (outside repo): `/tmp/opencode/backups/stage2g-pre-remediation/`
- Tarball: `AI-Project-Factory-pre-remediation.tar.gz` (2,757,533 bytes)
- Tarball SHA256: `c623175747fe88d148580e733e59c44d276dad0e81ca9c9bd60c567436539eb7`
- Manifest: `manifest.sha256.json` (786 file entries)
- Verification: extracted to temp dir; 786/786 files present, 0 hash mismatches.
- SQLite: none present; no DB backup required.

## 6. Gate status

Phase 0 complete. Backup verified. No modifications made to repository during this phase except this inventory document (explicitly required by Phase 0).

Proceeding to Phase 1 only after this inventory is presented.