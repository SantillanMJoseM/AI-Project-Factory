# FUNCTIONAL_REQUIREMENTS — PROJECT-001

- Project: PROJECT-001 (Task Management Web App)
- Document version: 0.1.0
- Date: 2026-11-04
- Author: AG-004 Business Analyst
- Status of document: Draft — pending stakeholder validation

## 1. Basis of this document

The only confirmed stakeholder input is Need **NEED-001**: "a task management web app" (user request, 2026-11-04). No stakeholders, users, constraints, or business rules have been provided beyond this statement. Per AG-004 limits, no requirement is presented as "requested" unless confirmed. All requirements below are analyst-derived from the stated domain scope and are marked with certainty levels defined in Section 2.

## 2. Definitions

### 2.1 Certainty levels

| Level | Meaning |
|---|---|
| Confirmed | Explicitly stated or approved by a stakeholder. |
| Assumed | Derived from the confirmed scope; plausible but not validated with a stakeholder. |
| Recommended | Analyst's professional recommendation; may be removed without breaking the minimum scope. |

### 2.2 Requirement status

`Draft` → `Under review` → `Approved` / `Rejected`. All requirements are `Draft` until stakeholder validation.

### 2.3 Priority scale (MoSCoW)

`Must` (product not viable without it) / `Should` (important, workarounds exist) / `Could` (desirable) / `Won't`.

## 3. Functional requirements

---

### REQ-0001 — User account management (registration and authentication)

- **Description:** The system shall allow a user to create an account with email and password, authenticate (log in / log out), and recover access via an email-based password reset. All task data shall be scoped to the authenticated user's account.
- **Justification:** The stated scope is a multi-user web application; without identity there is no way to attribute, isolate, or protect a user's tasks. It is the foundation for every other requirement in this document.
- **Priority:** Must
- **Origin:** Analyst-derived from NEED-001 (no stakeholder statement on authentication mode).
- **Dependencies:** None.
- **Acceptance criteria:**
  1. A visitor can register with a syntactically valid, not-yet-registered email and a password meeting the configured policy, and receives account confirmation or direct activation per agreed policy (see OQ-002).
  2. Registration with a duplicate email is rejected with a clear error message and no account is created.
  3. A registered user can log in with valid credentials and reaches their task workspace; invalid credentials produce a generic error without revealing which field failed.
  4. A logged-in user can log out; subsequent attempts to access protected pages redirect to the login screen.
  5. A user can initiate password recovery with their email and complete the reset through the emailed link; the reset token expires and is single-use.
  6. After login, User A cannot read or modify User B's tasks via direct object references (verified by test).
- **Status:** Draft
- **Certainty:** Assumed

---

### REQ-0002 — Task lifecycle (create, view, edit, delete)

- **Description:** The system shall let an authenticated user create a task with at minimum a title, view a list of their tasks and each task's details, edit any field of a task, and delete a task, with confirmation before deletion.
- **Justification:** Core capability implied by "task management": without full CRUD on tasks, the product delivers no primary value.
- **Priority:** Must
- **Origin:** Analyst-derived from NEED-001.
- **Dependencies:** REQ-0001 (task data is scoped per user account).
- **Acceptance criteria:**
  1. A user can create a task supplying only a title; creation succeeds and the task appears in their task list immediately.
  2. A task without a title cannot be saved; the system shows a validation message.
  3. The task list shows all of the current user's tasks (with pagination behavior per REQ-0004 / NFR scope) and excludes other users' tasks.
  4. A user can open a task, modify its title, description, status, due date and priority, and the changes persist after reload and are visible only to that user.
  5. Deletion requires explicit confirmation; after confirmation the task no longer appears in any list or query result.
  6. Creating a task requires ≤ 2 actions from the main workspace (time-and-actions check for a usability test).
- **Status:** Draft
- **Certainty:** Assumed

---

### REQ-0003 — Task status management (workflow states)

- **Description:** The system shall let the user change a task's status among a default set of states — "To Do", "In Progress", "Done" — with immediate persistence, and shall display the status on list views and detail views.
- **Justification:** Task management's business value is tracking progress. Status is the minimum data needed to distinguish a task list from a todo tracker. The default three-state set is an assumption (see OQ-003).
- **Priority:** Must
- **Origin:** Analyst-derived from NEED-001.
- **Dependencies:** REQ-0002 (status is an attribute of a task).
- **Acceptance criteria:**
  1. Every task has exactly one status at all times; new tasks default to "To Do".
  2. A user can change a task's status to any other state in the default set; the new status is visible in the list and detail views within one refresh cycle.
  3. Status changes persist across sessions (log out / log in retains the value).
  4. A user can filter or view their tasks grouped by the three default statuses.
  5. An invalid status value submitted directly to the API (if any) is rejected with a validation error.
- **Status:** Draft
- **Certainty:** Assumed

---

### REQ-0004 — Task organization: lists/projects, priority, and sorting

- **Description:** The system shall let the user group tasks into user-defined lists or projects (create, rename, delete), assign an optional priority level to each task (default set: High / Medium / Low), and sort the task view by creation date, due date, and priority.
- **Justification:** Flat task lists do not scale for managing work across contexts; grouping and prioritization are the standard mechanisms that make "management" (not just "tracking") possible. The list-vs-project terminology is an assumption (see OQ-004).
- **Priority:** Should
- **Origin:** Analyst-derived from NEED-001; recommended feature set.
- **Dependencies:** REQ-0002 (organizes tasks), REQ-0001 (lists are per user).
- **Acceptance criteria:**
  1. A user can create a list/project with a non-empty name and see it in their navigation.
  2. A task can be assigned to zero or one list/project; unassigned tasks appear in an "Inbox"/unassigned view and are never lost.
  3. Deleting a list/project prompts a choice per the agreed policy — move its tasks to Inbox or delete them (policy open: OQ-005) — and the chosen outcome is verifiable.
  4. A user can set a task's priority (High/Medium/Low); sorting by priority orders tasks accordingly with a documented tie-break rule (e.g., due date, then creation date).
  5. Sorting and group filters can be combined and the result set updates correctly.
- **Status:** Draft
- **Certainty:** Recommended

---

### REQ-0005 — Due dates and date-based visibility

- **Description:** The system shall let the user assign an optional due date (date, optionally with time) to a task and shall visually highlight overdue tasks and tasks due today in the task list.
- **Justification:** Deadlines are the primary time dimension of task management; without due dates the product cannot support commitments or planning. In-app highlighting is derived; **email/push reminders are explicitly NOT included** as they depend on unconfirmed channel decisions (see OQ-006 and NON_FUNCTIONAL_REQUIREMENTS / future REQ candidates).
- **Priority:** Should
- **Origin:** Analyst-derived from NEED-001.
- **Dependencies:** REQ-0002 (due date is a task attribute); interacts with REQ-0003 (an overdue task still keeps its status until completed — no automatic status change; see OQ-007).
- **Acceptance criteria:**
  1. A user can set, change, or clear a task's due date; the value persists.
  2. Tasks with a due date in the past and status ≠ "Done" render with a distinct overdue indicator in the list view.
  3. Tasks due today render with a distinct "today" indicator.
  4. A calendar-date input rejects invalid dates with a clear validation message.
  5. The user can filter tasks by "Overdue", "Today", "This week" and results match the definitions stated in the requirements glossary (to be created).
- **Status:** Draft
- **Certainty:** Assumed

---

## 4. Requirement summary matrix

| ID | Requirement | Priority | Origin | Certainty | Status | Depends on |
|---|---|---|---|---|---|---|
| REQ-0001 | User account management | Must | Analyst-derived (NEED-001) | Assumed | Draft | — |
| REQ-0002 | Task lifecycle (CRUD) | Must | Analyst-derived (NEED-001) | Assumed | Draft | REQ-0001 |
| REQ-0003 | Task status management | Must | Analyst-derived (NEED-001) | Assumed | Draft | REQ-0002 |
| REQ-0004 | Organization: lists, priority, sorting | Should | Analyst-derived (NEED-001) | Recommended | Draft | REQ-0001, REQ-0002 |
| REQ-0005 | Due dates and date visibility | Should | Analyst-derived (NEED-001) | Assumed | Draft | REQ-0002, REQ-0003 |

## 5. Open questions (blocking approval)

| ID | Question | Blocks |
|---|---|---|
| OQ-001 | Who are the stakeholders and target users (single-user tool, team tool, both)? Team collaboration would add assignment/sharing requirements not covered here. | Whole scope |
| OQ-002 | Is email verification at registration required, or direct activation? | REQ-0001 |
| OQ-003 | Are the three default statuses acceptable? Must users define custom statuses/workflows? | REQ-0003 |
| OQ-004 | Naming and depth of organization model: one level (lists) or hierarchy (projects > lists)? | REQ-0004 |
| OQ-005 | Policy when deleting a list: move tasks to Inbox or cascade-delete? | REQ-0004 |
| OQ-006 | Are reminders/notifications (email/push) required? Deliberately excluded pending an answer. | REQ-0005 scope |
| OQ-007 | Should overdue tasks auto-change status, or remain manual? Current baseline: manual. | REQ-0005, REQ-0003 |

## 6. Ambiguities and assumptions register

- **Ambiguity:** "task management web app" does not state whether multi-user collaboration (sharing, assignment between users, roles) is in scope. This document deliberately covers only personal task management per user; if collaboration is required, this is a scope change, not a requirement edit. (OQ-001)
- **Assumption A1:** Web browser access only; no mobile apps in initial scope.
- **Assumption A2:** One workspace per user account; team spaces out of initial scope.
- **Assumption A3:** English-language document baseline; locale requirements not stated.

## 7. Escalation to AG-001

**Escalated — critical information gaps:** PROJECT-001 has no stakeholder register, no PROJECT_CONTEXT.md, no constraints, and no confirmation that the five requirements above match the user's actual need. REQ-0001..REQ-0005 cannot be approved (only drafted) until OQ-001 (users/collaboration scope) is answered. Recommendation to AG-001: run a stakeholder elicitation round before AG-005 (architecture) consumes this document.

## 8. Next outputs (AG-004 backlog for PROJECT-001)

- BUSINESS_REQUIREMENTS.md (formalize NEED-001)
- NON_FUNCTIONAL_REQUIREMENTS.md
- USER_STORIES.md, USE_CASES.md, BUSINESS_RULES.md
- REQUIREMENTS_TRACEABILITY.md, REQUIREMENTS_GLOSSARY.md
