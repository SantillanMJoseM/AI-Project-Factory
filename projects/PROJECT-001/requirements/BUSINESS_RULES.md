# BUSINESS_RULES — PROJECT-001

- Task: TEST-F2-001 | Author: AG-004 | Date: 2026-11-04 | Version: 0.1.0 | Status: Draft — pending validation
- Legend: [C] Confirmed (directly from source) · [A] Assumption · [R] Recommendation · [Q] Open question. Rules marked [A]/[R] are analyst-proposed defaults that enforce stated requirements; they require confirmation before baseline.

| ID | Rule | Certainty | Enforces | Linked |
|---|---|---|---|---|
| RULE-001 | No functionality is accessible without an authenticated session. | [C] | "secure"; "users log in" | REQ-0003, REQ-0008, REQ-0027 |
| RULE-002 | Exactly two roles exist: Member and Admin. A user may hold one role at a time. The last active Admin cannot be demoted or deactivated [R guard]. | [A] (role count unstated) | "Admins manage users" | REQ-0006, REQ-0012 · OQ-01 |
| RULE-003 | Only an Admin may create users, change roles, and deactivate/reactivate accounts. Members cannot administer accounts. | [C] scope / [A] mechanism | "Admins manage users" | REQ-0010–REQ-0012 · UC-002 |
| RULE-004 | A deactivated user cannot authenticate and existing sessions are revoked immediately. Tasks assigned to them must be reassigned by an Admin; deactivation never deletes task or audit history. | [A] | "secure", auditability | REQ-0011, REQ-0028 · OQ-08 |
| RULE-005 | Team scoping: a user sees and acts only on tasks of the team(s) they belong to. Tasks may be assigned only to active members of the same team. | [A] (team concept implied by "for teams") | data isolation, security | REQ-0013, REQ-0017, REQ-0020, REQ-0027 · OQ-10 |
| RULE-006 | A task has: mandatory title; optional description and due date; exactly one assignee (may be unassigned). No attachments, sub-tasks, or priorities without confirmation. | [A] | "create tasks" | REQ-0014 · OQ-09 |
| RULE-007 | Task lifecycle states: **To Do → In Progress → Done**; **Cancelled** reachable from To Do/In Progress by Admin only. Done and Cancelled are terminal; reopen not offered until OQ-09 is answered. No skipping states. | [A] | "track, complete" | REQ-0016, REQ-0018, REQ-0019 |
| RULE-008 | A task's editable fields (title, description, due date) may be changed only by its creator, its assignee, or an Admin. Status transitions follow RULE-007 with the same actors plus assignee. | [A] | "manage tasks" | REQ-0015, REQ-0018 |
| RULE-009 | Notification matrix: **assigned/reassigned** → new assignee; **status change** → creator and current assignee (if distinct from actor); **completed** → creator; **cancelled** → creator and assignee. The acting user receives no self-notification. | [A] | "receive notifications" | REQ-0021 · OQ-04 |
| RULE-010 | Dashboard content is filtered to the current user and their team(s) per RULE-005; a user never sees other teams' data on the dashboard. | [A] | security + "dashboard" | REQ-0020 |
| RULE-011 | Every action in REQ-0023 (login/logout/failed login, user create/role/deactivate, task create/edit/assign/status/complete/cancel) appends one immutable audit record: {actor, action, entity ID, timestamp UTC, before/after state}. App users cannot update or delete audit records. | [C] intent / [A] event set | "auditable" | REQ-0023, REQ-0032 · OQ-05 |
| RULE-012 | After 5 consecutive failed logins for one account, authentication for that account is throttled for 15 minutes [R]; attempts are audited. | [R] | "secure" | REQ-0008 · OQ-07 |

## Notes
- No rule contradicts the source statement. RULE-007 and RULE-012 are the two most consequential defaults; both are flagged for AG-001 validation before architecture baseline (AG-005) consumes them.
