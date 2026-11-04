# USER_STORIES — PROJECT-001

- Task: TEST-F2-001 | Author: AG-004 | Date: 2026-11-04 | Version: 0.1.0 | Status: Draft — pending validation
- Legend: [C] Confirmed · [A] Assumption · [R] Recommendation · [Q] Open question. Priorities: MoSCoW.

## Epic: Access control

### US-001 — Sign in [C] · Must
As a team member I want to log in with my credentials so that I can access my team's tasks.
- Acceptance: Valid credentials open the dashboard; invalid ones show a generic error; 5 failures trigger RULE-012 throttle.
- Links: REQ-0008, REQ-0003 · UC-001 · RULE-001, RULE-012

### US-002 — Sign out [A] · Must
As a member I want to log out so that my session cannot be used by others on shared devices.
- Acceptance: Session invalidated immediately; back-navigation does not restore protected views.
- Links: REQ-0009, REQ-0028 · UC-001

### US-003 — Create account [C→A] · Must
As an admin I want to create a user account so that a new teammate can start working.
- Acceptance: Account with role Member/Admin is provisioned; user can log in; event audited.
- Links: REQ-0010 · UC-002 · RULE-003 (OQ-08: credential delivery mechanism)

### US-004 — Deactivate/reactivate account [A] · Must
As an admin I want to deactivate a user so that access ends when someone leaves the team.
- Acceptance: Deactivated user cannot log in; open tasks reassigned per RULE-004; event audited.
- Links: REQ-0011 · UC-002 · RULE-004

### US-005 — Change role [A/Q] · Should
As an admin I want to change a user's role so that responsibilities match access.
- Acceptance: New role effective on next request; last-admin demotion blocked [R]; event audited.
- Links: REQ-0012 · UC-002 · RULE-002 (OQ-01: are there more than 2 roles?)

## Epic: Task lifecycle

### US-006 — Create task [C] · Must
As a member I want to create a task so that work is captured for the team.
- Acceptance: Title required; description/due date optional; task visible to team; audited.
- Links: REQ-0014 · UC-003 · RULE-006

### US-007 — Edit task [A] · Should
As a member I want to correct task details so that information stays accurate.
- Acceptance: Only creator/assignee/admin can edit; changes audited with before/after.
- Links: REQ-0015 · UC-003 · RULE-008

### US-008 — Cancel task [A/Q] · Could
As an admin I want to cancel an obsolete task so that it stops appearing as active work without destroying history.
- Acceptance: Status Cancelled (terminal); reason recorded; creator+assignee notified; audited.
- Links: REQ-0016 · UC-006 · RULE-007 (OQ-08: is hard delete ever required?)

### US-009 — Assign task [C] · Must
As a member I want to assign a task to a teammate so that ownership is clear.
- Acceptance: Assignee must be an active member of the same team; assignee notified; audited.
- Links: REQ-0017 · UC-004 · RULE-005, RULE-009 (OQ-10: multi-assignee?)

### US-010 — Track task status [C] · Must
As a member I want to move a task through To Do → In Progress so that progress is visible.
- Acceptance: Only valid transitions accepted; invalid transition shows error; changes listed/filtered correctly; audited+notified.
- Links: REQ-0013, REQ-0018 · UC-005 · RULE-007, RULE-009

### US-011 — Complete task [C] · Must
As the assignee I want to mark a task Done so that the team sees finished work.
- Acceptance: Requires assignee [A] (OQ-09); completion timestamp recorded; creator notified; audited.
- Links: REQ-0019 · UC-006 · RULE-007

## Epic: Visibility & awareness

### US-012 — View dashboard [C] · Must
As a member I want a dashboard after login so that I immediately know my pending work and team activity.
- Acceptance: My open tasks, team counts, recent activity render within REQ-0033 target; team-scoped data only.
- Links: REQ-0020 · UC-007 (OQ-03: exact widgets?)

### US-013 — Receive notifications [C→A] · Must
As a member I want to be notified when a task is assigned to me or its status changes so that I can react without polling.
- Acceptance: Notification created per RULE-009 matrix ≤ 10 s [R]; in-app list shows unread/read; mark-as-read persists.
- Links: REQ-0021, REQ-0022 · UC-008 (OQ-04: channels beyond in-app?)

### US-014 — Review audit trail [C→A] · Must
As an admin I want to search the audit trail so that I can reconstruct who did what and when.
- Acceptance: Filter by actor/action/date; results match system events exactly; records immutable.
- Links: REQ-0023, REQ-0024 · UC-009 · RULE-011 (OQ-05: retention & access scope?)

## Story coverage note
Every FR (REQ-0008…REQ-0024) is covered by at least one story above; no story exists without an FR. Stories whose certainty is [A]/[Q] must not enter a committed sprint backlog until AG-001 resolves the linked OQ.
