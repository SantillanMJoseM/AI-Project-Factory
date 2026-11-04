# BUSINESS_REQUIREMENTS — PROJECT-001

- Task: TEST-F2-001 | Author: AG-004 Business Analyst | Date: 2026-11-04 | Version: 0.1.0
- Status: Draft — pending validation (contains open questions; not approvable as-is per AG-004 limits)
- Source requirement (verbatim, [C]): "Web app for teams to create, assign, track, and complete tasks. Users log in, view dashboard, manage tasks, receive notifications. Admins manage users. Must be secure, responsive, auditable."
- Certainty legend: [C] Confirmed in source · [A] Assumption (analyst) · [R] Recommendation · [Q] Open question (escalated to AG-001)

## Stakeholders

| Stakeholder | Interest | Basis |
|---|---|---|
| Team member ("User") | Creates, works on, and completes tasks | [C] |
| Administrator | Manages users; (assumed) reviews audit trail | [C] / [A] |
| Product owner / requester | Accepts the delivered app | [A] |
| Security/audit consumer | Trusts logs and access control | [C] (implied by "secure, auditable") |

## Actors (system boundary)

- **Member** — authenticated team user. [C]
- **Admin** — elevated user managing accounts. [C]
- **Notification channel** (external email/SMS or internal only) — undecided. [Q]
- Assumed roles are exactly Member and Admin (RBAC). [A] — see OQ-01.

## Business Requirements

### REQ-0001 — Shared team task management
- Description: Provide teams a central place to create, assign, track, and complete tasks.
- Justification: Core purpose stated in source. [C]
- Priority: Must (MoSCoW) | Origin: user statement [C]
- Dependencies: REQ-0003 (authenticated access)
- Acceptance criteria: End-to-end flow exists: task created → assigned → status tracked → marked complete, by two different users.
- Status: Draft — pending validation
- Links: REQ-0013–REQ-0019; US-006–US-011; UC-003–UC-006

### REQ-0002 — Web-delivered application
- Description: Application is delivered as a web app accessible from a browser (no native install required).
- Justification: "Web app" stated. [C] Desktop/mobile browser support detailed in REQ-0030.
- Priority: Must | Origin: user statement [C]
- Dependencies: none
- Acceptance criteria: App is fully usable on latest desktop and mobile browsers without installation.
- Status: Draft — pending validation
- Links: REQ-0030, REQ-0031

### REQ-0003 — Controlled access via login
- Description: The app is usable only after user login; identity gates all functionality.
- Justification: "Users log in" + "must be secure". [C] (credential mechanism = email/password assumed [A], see OQ-02)
- Priority: Must | Origin: user statement [C]
- Dependencies: REQ-0002
- Acceptance criteria: Unauthenticated users cannot reach any task data; login succeeds only with valid credentials.
- Status: Draft — pending validation
- Links: REQ-0008, REQ-0009, REQ-0025–REQ-0028; US-001/US-002; UC-001

### REQ-0004 — Work-visibility dashboard
- Description: Logged-in users view a dashboard summarizing their work.
- Justification: "view dashboard" stated. [C] Content of dashboard is undefined in source — [A]: shows tasks assigned to me, team task overview, recent activity. See OQ-03.
- Priority: Must | Origin: user statement [C]
- Dependencies: REQ-0003, REQ-0001
- Acceptance criteria: After login, dashboard renders the assumed widgets within the performance target REQ-0033.
- Status: Draft — pending validation
- Links: REQ-0020; US-012; UC-007

### REQ-0005 — Event notifications
- Description: Users receive notifications about relevant task events.
- Justification: "receive notifications" stated. [C] Triggers and channels are NOT specified — [A]: assignment, status change, completion; [Q] channels (in-app assumed, email undecided) — OQ-04.
- Priority: Must (capability) / Should (email channel) | Origin: user statement [C]
- Dependencies: REQ-0001, REQ-0003
- Acceptance criteria: When a task is assigned or its status changes, the relevant users are notified per the event matrix (RULE-009).
- Status: Draft — pending validation
- Links: REQ-0021, REQ-0022; US-013; UC-008

### REQ-0006 — Administrative user management
- Description: Admins manage user accounts.
- Justification: "Admins manage users" stated. [C] "Manage" is ambiguous — [A]: create, deactivate/reactivate, modify profile/role. Self-registration is assumed NOT in scope [A]. See OQ-01.
- Priority: Must | Origin: user statement [C]
- Dependencies: REQ-0003
- Acceptance criteria: Admin can create an account, the new account can log in; deactivated account cannot.
- Status: Draft — pending validation
- Links: REQ-0010–REQ-0012; US-003–US-005; UC-002

### REQ-0007 — Auditability
- Description: Actions are auditable: the system can answer who did what and when.
- Justification: "must be ... auditable" stated. [C] Scope is underspecified: which events, retention, and access rights are [A]/[Q] — OQ-05.
- Priority: Must | Origin: user statement [C]
- Dependencies: REQ-0003, REQ-0006
- Acceptance criteria: For login, user-management, and task-lifecycle events, a retrievable record with actor, action, target, timestamp exists.
- Status: Draft — pending validation
- Links: REQ-0023, REQ-0024, REQ-0032; US-014; UC-009

## Constraints

- Web/HTTP delivery implied; no offline or native requirements stated. [C/A]
- Security is a stated non-negotiable quality (REQ-0025–REQ-0029). [C]
- No technology, budget, schedule, or integration constraints were provided. [Q] — OQ-06.

## Out of scope (assumed, pending confirmation)

- External integrations (Slack/Jira/SSO/calendar), mobile apps, reporting/analytics, billing. [A] — OQ-06.

## Ambiguities detected in source (documented, not resolved)

1. "secure" — no standard, threat model, or compliance target given (OQ-07).
2. "responsive" — could mean responsive layout [primary interpretation, A] or operational responsiveness/performance [R: both covered by REQ-0030/REQ-0033].
3. "auditable" — no retention, format, or regulator named (OQ-05).
4. "manage tasks" / "manage users" — verb scope not enumerated (assumptions REQ-0010–REQ-0016).
5. Contradictions: none detected between stated requirements.

## Open question register

Full register with owners: see REQUIREMENTS_TRACEABILITY.md §Gap Register (OQ-01…OQ-10). Critical ones (OQ-04, OQ-05, OQ-07) escalated to AG-001.
