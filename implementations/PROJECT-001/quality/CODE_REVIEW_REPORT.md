# CODE_REVIEW_REPORT — PROJECT-001 Backend

- Report ID: CR-P001-BACKEND-001
- Date: 2026-11-04
- Reviewer: AG-013 Code Reviewer
- Scope reviewed: `implementations/PROJECT-001/backend/app.py` (215 lines, read in full)
- Standards referenced: `standards/coding/coding-standards.md`, `quality-gates/development/defect-severity-matrix.md`
- Requirements referenced: `projects/PROJECT-001/requirements/FUNCTIONAL_REQUIREMENTS.md` (REQ-0001), `BUSINESS_REQUIREMENTS.md` (REQ-0003), `BUSINESS_RULES.md` (RULE-001)
- Findings: 1 (1 CRITICAL)
- Verdict: FAIL — 1 CRITICAL finding blocks the gate per the defect severity matrix (CRITICAL → BLOCKED; RULE-001 policy violation → FAIL)

---

## Finding CR-P001-001

| Field | Value |
|---|---|
| **ID** | CR-P001-001 |
| **File** | `implementations/PROJECT-001/backend/app.py` |
| **Location** | Entire HTTP surface: `Handler.do_GET` (lines 101–126), `Handler.do_POST` (lines 130–194); placeholder-user seeding in `init_db` (lines 56–72); client-supplied `user_id` (lines 172–175) |
| **Description** | No authentication. The backend exposes `GET /tasks` and `POST /tasks` with no credential, token, session, or API-key check on any endpoint, and no authorization scoping of data to a user. |
| **Severity** | CRITICAL (defect-severity-matrix: "Security breach … → BLOCKED"; also a RULE-001 policy violation, independently "FAIL") |
| **Evidence** | 1) `grep -inE "auth|token|session|cookie|login|password|api.?key|bearer" app.py` returns only two hits: line 62 comment `# created without an auth flow in this minimal backend.` and line 66 column name `password_hash` for a seeded placeholder user — no auth logic exists anywhere in the file. 2) `do_GET`/`do_POST` (lines 101–194) never read or validate `Authorization` or any credential header; `_send_json` responses are sent to any caller. 3) Line 118–121: `SELECT * FROM tasks ORDER BY id DESC;` returns **all** tasks of **all** users to any unauthenticated caller. 4) Line 172: `user_id = payload.get("user_id", DEFAULT_USER_ID)` — the caller controls task ownership (IDOR / spoofing). 5) Requirements conflict: REQ-0001 AC-6 "After login, User A cannot read or modify User B's tasks" and REQ-0003 AC "Unauthenticated users cannot reach any task data" are both violated. Mitigating fact (does not change severity): line 204 binds the server to `127.0.0.1` only, so exposure is limited to the local host / processes and any proxy that forwards to it. |
| **Impact** | Any local process or client reaching the port can read the full task dataset and create tasks impersonating any user, breaching REQ-0003 and RULE-001 ("No functionality is accessible without an authenticated session"). Blocks the development quality gate; ships an unshippable security posture if the port is ever exposed or proxied by the frontend/integration layer. |
| **Recommendation** | Implement authentication and per-request authorization before merge: require a validated session/token on every non-health endpoint (401 otherwise); derive `user_id` exclusively from the authenticated principal and remove it from the request-body contract (lines 172–175); filter all queries (`SELECT`, `INSERT`) by the authenticated user id (lines 118–121, 179–186); remove the placeholder-user seed dependency (lines 61–72). Align implementation with REQ-0001/RULE-001 and re-review. Per AG-013 escalation rules, security concerns are also escalated to AG-015 Security Auditor (see Next steps). |
| **Owner** | AG-008 Backend Developer (fix); escalation: AG-015 Security Auditor (security review), AG-002 Quality Gatekeeper (gate verdict) |

---

## Next steps

1. AG-008 implements authentication + authorization and removes client-supplied `user_id` (CR-P001-001).
2. AG-015 performs a security audit of the remediated backend (escalation per `agents/quality/ag-013-code-reviewer.md` line 73).
3. AG-002 re-runs the gate; report to be re-issued after fix.
