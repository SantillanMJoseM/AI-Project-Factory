# SECURITY_AUDIT_REPORT — PROJECT-001 Backend (Hardcoded Secrets)

- Report ID: SA-P001-SECRETS-001
- Date: 2026-11-04
- Auditor: AG-015 Security Auditor
- Scope: `implementations/PROJECT-001/backend/app.py` (215 lines, read in full)
- Task: scan for hardcoded secrets. Findings: 1 (0 CRITICAL/HIGH/MEDIUM, 1 INFO)

## Method

1. Keyword/pattern grep: `(?i)(api[_-]?key|secret|token|passw|credential|aws_|AKIA|BEGIN .*PRIVATE|private[_-]?key|bearer|auth)`
2. High-entropy / known-key-format grep: `[0-9a-fA-F]{16,}`, base64 runs ≥25 chars, `sk-`, `ghp_`, `xox[baprs]-`
3. Full-file manual review of every literal and assignment.

## Findings

### SA-P001-001 (INFO) — Placeholder password_hash seeded in code

| Field | Value |
|---|---|
| File / Location | `backend/app.py`, `init_db`, line 69 |
| Evidence | `'not-used-0000000000'` inserted as `password_hash` for the seeded `default` user (lines 63–72) |
| Assessment | Not a secret: it is a non-credential placeholder (invalid hash format, nothing verifies it, no auth flow exists — see line 62 comment). Flagged so secret scanners can whitelist it and so it does not become a real credential later. |
| Recommendation | Keep no password-like literal even for placeholders; use `NULL`/`''` with a CHECK, or remove the seed when real auth lands (already required by CR-P001-001 in CODE_REVIEW_REPORT.md). |

## Verified clean

- No API keys, tokens, passwords, private keys, or cloud credentials found (greps 1–2 returned only line 62 comment and line 66 column name `password_hash`).
- Configuration via environment variables only: `PORT`, `DB_PATH`, `SCHEMA_PATH` (lines 32–33, 203) — correct practice.
- SQLite access uses no embedded credentials (line 46).
- SQL is fully parameterized (lines 63–72, 179–189); no injection-via-concatenation secrets surface.

## Verdict

**PASS for hardcoded secrets.** 0 real secrets present; 1 INFO (placeholder hash, SA-P001-001). Note: authentication gaps are out of scope here and tracked under CR-P001-001 (CRITICAL, CODE_REVIEW_REPORT.md) — that finding still blocks the gate.
