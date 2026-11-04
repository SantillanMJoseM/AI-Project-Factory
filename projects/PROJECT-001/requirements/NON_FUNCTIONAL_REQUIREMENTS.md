# NON_FUNCTIONAL_REQUIREMENTS — PROJECT-001

- Task: TEST-F2-001 | Author: AG-004 | Date: 2026-11-04 | Version: 0.1.0 | Status: Draft — pending validation
- Source adjectives — "secure", "responsive", "auditable" — are [C] but unquantified; concrete targets below are [A] or [R] until confirmed. Legend: [C] Confirmed · [A] Assumption · [R] Recommendation · [Q] Open question.

## Security (from "must be secure")

### REQ-0025 — Credential protection
- Description: Passwords stored only with a modern salted adaptive hash (e.g., Argon2id/bcrypt); never logged or exposed in UI/API responses.
- Justification: "secure" [C]; specific mechanism [A]/[R].
- Priority: Must | Origin: [C]/[A] | Dependencies: REQ-0008
- Acceptance criteria: DB inspection shows no plaintext passwords; password fields masked everywhere.
- Status: Draft — pending validation | Verification: T (test) + I (inspection)

### REQ-0026 — Encryption in transit
- Description: All client-server traffic over TLS 1.2+; HTTP redirects to HTTPS; HSTS enabled.
- Justification: "secure" [C]; baseline recommendation [R].
- Priority: Must | Origin: [C]/[R] | Dependencies: REQ-0002
- Acceptance criteria: No cleartext HTTP endpoints; scanner confirms TLS configuration.
- Status: Draft — pending validation | Verification: T

### REQ-0027 — Role-based authorization (RBAC)
- Description: Every operation is authorized by role (Member, Admin) and data visibility is restricted to the user's team(s); least-privilege default-deny.
- Justification: "secure" [C]; RBAC model and team-scoping are [A] (OQ-01, OQ-10).
- Priority: Must | Origin: [C]/[A] | Dependencies: REQ-0012
- Acceptance criteria: Cross-tenant and privilege-escalation tests return 403/404; admin functions invisible to members.
- Status: Draft — pending validation | Verification: T

### REQ-0028 — Session management
- Description: Sessions expire after 30 min idle and 12 h absolute [R]; logout and account deactivation invalidate sessions immediately; cookies HttpOnly/Secure/SameSite.
- Justification: "secure" [C]; values [R] pending OQ-07.
- Priority: Must | Origin: [C]/[R] | Dependencies: REQ-0008, REQ-0011
- Acceptance criteria: Idle expiry forces re-auth; revoked session cannot call any API.
- Status: Draft — pending validation | Verification: T

### REQ-0029 — Application security baseline
- Description: Server-side input validation, output encoding, CSRF protection, OWASP Top 10 mitigations, dependency vulnerability scanning in CI.
- Justification: "secure" [C]; OWASP as acceptance baseline is [R] — OQ-07 asks which standard/compliance applies.
- Priority: Must | Origin: [C]/[R]
- Acceptance criteria: No High/Critical findings in a pre-release scan; security test suite passes.
- Status: Draft — pending validation | Dependencies: none | Verification: T + A (analysis)

## Usability / Responsiveness (from "responsive")

### REQ-0030 — Responsive interface
- Description: UI adapts to mobile (≥360 px), tablet, and desktop breakpoints; all core flows (login, dashboard, create, assign, status, complete, notifications) are operable on a phone browser.
- Justification: "responsive" [C] — interpreted as responsive design [A]; second reading (operational responsiveness) covered by REQ-0033.
- Priority: Must | Origin: [C]/[A] | Dependencies: REQ-0002
- Acceptance criteria: No horizontal scroll or unusable targets at stated widths; manual cross-device walkthrough passes.
- Status: Draft — pending validation | Verification: T (device matrix)

### REQ-0031 — Browser support
- Description: Support last two major versions of Chrome, Firefox, Safari, Edge (desktop and mobile).
- Justification: [R] — source names no browsers.
- Priority: Should | Origin: [R] | Dependencies: REQ-0002
- Acceptance criteria: Automated E2E suite green on the stated matrix.
- Status: Draft — pending validation | Verification: T

## Auditability (from "auditable")

### REQ-0032 — Audit record integrity and retention
- Description: Audit records are append-only, tamper-evident, include actor/action/entity/timestamp, retained ≥ 12 months [R]; retention duration is OQ-05.
- Justification: "auditable" [C]; integrity and retention details [A]/[R].
- Priority: Must | Origin: [C]/[A] | Dependencies: REQ-0023
- Acceptance criteria: App-level APIs cannot update/delete audit rows; test export reconstructs any task's full history.
- Status: Draft — pending validation | Verification: T + I

## Performance & capacity

### REQ-0033 — Performance targets
- Description: p95 ≤ 2 s for dashboard/list pages and ≤ 1 s for task mutations [R]; UI feedback for operations > 400 ms.
- Justification: Source says nothing measurable; numbers are [R] tied to the secondary reading of "responsive" — OQ-06.
- Priority: Should | Origin: [R] | Dependencies: REQ-0020
- Acceptance criteria: Load test at expected scale meets targets.
- Status: Draft — pending validation | Verification: T (load test)

### REQ-0034 — Availability
- Description: ≥ 99.5 % monthly availability excluding announced maintenance [R].
- Justification: [R]; no SLA given — OQ-06.
- Priority: Should | Origin: [R] | Dependencies: deployment (AG-012 stage)
- Acceptance criteria: Monitoring dashboard evidences target; incident log reviewed monthly.
- Status: Draft — pending validation | Verification: A (operations analysis)

### REQ-0035 — Capacity / scale
- Description: Designed for ≤ 500 total users and ≤ 50 concurrent per instance [A] unless corrected — OQ-06 (expected volume unknown).
- Priority: Could | Origin: [A] | Dependencies: architecture (AG-005)
- Justification: Prevents over-engineering; must be confirmed.
- Acceptance criteria: REQ-0033 met at assumed peak load.
- Status: Draft — pending validation | Verification: T (load test)

## Continuity

### REQ-0036 — Backup and recovery
- Description: Automated daily backup of task and audit data; RPO ≤ 24 h, RTO ≤ 4 h [R] — OQ-06 (business continuity needs unknown).
- Priority: Should | Origin: [R] | Dependencies: deployment
- Acceptance criteria: Restore drill recovers to prior day with audit trail intact.
- Status: Draft — pending validation | Verification: T (restore drill)

## NFR notes

- Security specifics (standard, compliance regime, MFA/SSO) escalated to AG-001 and AG-003 (security concerns) per escalation rules.
- Metrics marked [R] are placeholder defaults for estimation, not confirmed requirements; no requirement with a [R]/[A] number may be baselined until answered by AG-001.
