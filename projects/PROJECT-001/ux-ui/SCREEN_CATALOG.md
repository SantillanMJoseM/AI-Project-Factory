# Screen Catalog — PROJECT-001

| Field | Value |
|---|---|
| Document | SCREEN_CATALOG.md |
| Version | 0.1 (Draft) |
| Date | 2026-11-04 |
| Author | AG-006 UX/UI Designer |
| Scope | Login, Dashboard, Task List |
| Traceability note | Requirement IDs below are **provisional placeholders** (pattern `REQ-*`). This catalog was produced without access to the approved requirements baseline; every ID must be verified and remapped against `requirements/` before the design is approved. |

---

## Screen 1 — Login

| Attribute | Specification |
|---|---|
| **ID** | `SCR-001` |
| **Objective** | Authenticate the user and grant access to the application only to valid credentials. |
| **User profile** | Guest (unauthenticated). Primary: registered end user. Secondary: administrator (same flow). |
| **Displayed info** | App name/logo; email field; password field (show/hide toggle); "Log in" button; "Forgot password?" link; inline helper/error text. No user data is displayed before authentication. |
| **Actions** | Enter email; enter password; toggle password visibility; submit login; request password recovery (navigation only). |
| **Validations** | Email: required, valid format (`RFC 5322` practical subset), max 254 chars. Password: required, min length enforced by backend policy (design assumes ≥ 8 chars), never shown in plain text by default. Validation runs on submit and on field blur; server-side validation is authoritative. |
| **States** | `default` (fields empty, button enabled but blocks submit with errors); `submitting` (button disabled, spinner, fields locked); `success` (redirect to Dashboard); `error` (inline messages, generic for bad credentials). |
| **Errors** | `E-001-1` Invalid email format → inline message under email field. `E-001-2` Empty required field → inline message per field. `E-001-3` Invalid credentials → single generic banner ("Email or password is incorrect"); never reveal which field failed (account-enumeration protection). `E-001-4` Network/service failure → persistent banner with retry; form data (email only) preserved. Rate-limit / lockout → banner with wait time if provided by backend. |
| **Navigation** | Entry: first visit or session expiry from any screen. Exit: → `SCR-002` Dashboard (success); → Password Recovery (out of this catalog's scope, TBD screen ID). No back-navigation to protected screens. |
| **Related requirements** | Provisional: REQ-AUTH-001 (credential authentication), REQ-AUTH-002 (password recovery entry point), REQ-SEC-001 (generic auth error messaging), REQ-SEC-002 (rate limiting). **To be verified against requirements baseline.** |

---

## Screen 2 — Dashboard

| Attribute | Specification |
|---|---|
| **ID** | `SCR-002` |
| **Objective** | Give the authenticated user a glanceable overview of current work status and fast access to primary tasks (task list). |
| **User profile** | Authenticated end user (all roles). Content is scoped to the user's permissions; design assumes read-only summary plus navigation shortcuts — no data editing on this screen. |
| **Displayed info** | Global app header (app name, user menu, logout); summary cards: tasks pending, tasks completed (period TBD), tasks overdue; recent-activity list (max 5 items, TBD); shortcut to `SCR-003 Task List`. All figures come from backend aggregation; no local computation. |
| **Actions** | Open task list; open user menu; log out; refresh data (pull-to-refresh / refresh button); navigate via summary card → filtered task list (e.g., "Overdue" card opens `SCR-003` with `status=overdue`). |
| **Validations** | N/A for input fields (no user data entry). Guards: screen access requires a valid session; card filters must use only valid, predefined filter values. |
| **States** | `loading` (skeletons for cards and activity list, ≤ 1.5 s perceived); `loaded`; `empty` (new user with zero tasks → empty-state illustration + CTA "Go to Task List"); `partial` (one widget failed → that card shows local error, rest renders); `stale` (offline/last-known data banner with timestamp). |
| **Errors** | `E-002-1` Load failure (5xx/network) → full-screen retry state; `E-002-2` Session expired → redirect to `SCR-001` with notice "Your session expired". `E-002-3` Partial widget failure → inline card error with "Retry" action only for that widget. Errors never show raw technical details; user-facing copy + support reference code. |
| **Navigation** | Entry: successful login from `SCR-001`; app root with valid session. Exit: → `SCR-003` Task List (header nav or summary-card drill-down); → `SCR-001` on logout/session expiry. Dashboard is the default landing screen; other destinations TBD pending requirements confirmation. |
| **Related requirements** | Provisional: REQ-DASH-001 (task summary metrics), REQ-DASH-002 (recent activity), REQ-NAV-001 (global navigation), REQ-AUTH-003 (logout), REQ-AUTH-004 (session expiry handling). **To be verified against requirements baseline.** |

---

## Screen 3 — Task List

| Attribute | Specification |
|---|---|
| **ID** | `SCR-003` |
| **Objective** | Let the user view, filter, and manage their tasks efficiently (read, create, update status; delete TBD pending requirements). |
| **User profile** | Authenticated end user; primary persona: individual contributor who creates and completes daily tasks. If role-based editing rules exist (e.g., admin-only delete), they come from requirements and must be confirmed before visual states are finalized. |
| **Displayed info** | Per task row: title, status badge (To do / In progress / Done), due date, priority indicator, creation date. List-level: total count, active filter chips, sort control (by due date / priority / created — default TBD), search box, "New task" primary button. Pagination or infinite scroll TBD pending backend spec. |
| **Actions** | Create task (modal or dedicated form — pattern TBD); edit task; change status (inline toggle or detail view); delete task (with confirm dialog); search by title; filter by status/priority/due date; sort; open task detail. |
| **Validations** | Create/edit form: Title required, 1–120 chars, trimmed; Due date (optional) must not be in the past on creation (policy TBD); Status must be one of the predefined enum values; Priority one of predefined enum. Client validation blocks submit with per-field messages; server validation is authoritative and mirrors these rules. Delete: requires explicit confirmation (no undo assumed unless backend supports it). |
| **States** | `loading` (skeleton rows ×5); `loaded with data`; `empty — no tasks` (CTA "Create your first task"); `empty — no results` (after search/filter; offers "Clear filters"); `filtering/sorting` (lightweight loading, filters preserved); `offline/stale` (banner + cached list); `mutation pending` (row-level spinner while status change saves). |
| **Errors** | `E-003-1` List load failure → full retry state. `E-003-2` Save/create failure → keep form data open, inline toast + field error if server-returned. `E-003-3` Status change failure → revert optimistic change, toast "Couldn't save, try again". `E-003-4` Validation failure → inline field errors, focus moved to first invalid field. `E-003-5` Permission denied → hide/disable action (preferred) or clear message; never a silent no-op. `E-003-6` Session expired → redirect to `SCR-001`, attempted action context preserved where possible. |
| **Navigation** | Entry: → header nav or dashboard drill-down from `SCR-002` (deep link with filter, e.g., `?status=overdue`); app root. Exit: → task detail (TBD screen, outside this catalog until confirmed); → `SCR-002` via header nav; → `SCR-001` on logout/session expiry. Back from list returns to previous screen with scroll and filters preserved per session. |
| **Related requirements** | Provisional: REQ-TASK-001 (list tasks), REQ-TASK-002 (create task), REQ-TASK-003 (edit task), REQ-TASK-004 (change status), REQ-TASK-005 (delete task — unconfirmed), REQ-TASK-006 (search/filter/sort), REQ-NAV-002 (deep-link filtering). **To be verified against requirements baseline.** |

---

## Cross-screen rules

1. **Session guard:** `SCR-002` and `SCR-003` require a valid session; expiry from either screen redirects to `SCR-001` with an explanatory notice.
2. **Global navigation:** persistent header (app name, nav to Dashboard/Task List, user menu with Logout) shared by `SCR-002` and `SCR-003`.
3. **Error taxonomy:** all error codes `E-xxx-n` must map 1:1 to functional requirements or a documented derived (non-functional, usability) rule; no screen behavior exists without a requirement or explicit derivation note.
4. **TBD items** in this catalog are open questions for the requirements owner and must be resolved before visual design (wireframes/high-fidelity) begins.

## Open questions / escalation

- Requirement IDs are provisional: the approved requirements document for PROJECT-001 was **not consulted** (per instruction for this draft). Remapping is required before approval — escalated to AG-002/requirements owner.
- Undetermined scope items: password recovery screen, task detail screen, delete/soft-delete policy, pagination strategy, role-based permissions, dashboard period filter.
