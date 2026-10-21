# `dispatch` boundary

«Диспетчер» (`W61-DISPATCHER-01`, roadmap Q-2): an administrator assigns a project, or one
document of a project, to an expert; the expert moves it through `assigned → in_progress →
done` or returns it with a reason; an administrator reassigns or cancels it. Every change is
an append-only event with its actor and time; the current state is derived, never held in
memory and never stored as an updatable status.

Other contexts import `auditmanager.dispatch.public` only.

## Storage (`0025_work_assignments`)

- `work_assignment` — immutable header: `asg_<ULID>`, project, optional document, first
  assignee, creator, note, time.
- `work_assignment_event` — immutable history (`evt_<ULID>`, per-assignment `seq`): `assigned`
  (seq 1 only), `started`, `completed`, `returned` (reason required), `reassigned` (new
  assignee), `cancelled`.
- `work_assignment_current` — view: latest event and current assignee per assignment.

Every account column is a `RESTRICT` reference registered in `access/references.py`, so an
account that holds or handed out work cannot be purged (archive remains).

## Rules (`policy.py`)

| status | allowed next events |
|---|---|
| `assigned` | started, returned, reassigned, cancelled |
| `in_progress` | completed, returned, reassigned, cancelled |
| `returned` | reassigned, cancelled |
| `done`, `cancelled` | — (terminal) |

- `started` / `completed` / `returned`: the current assignee, holding `expert`.
- create / `reassigned` / `cancelled`: `admin` (`R-60`: an administrator without `expert`
  reads and does not decide an expert's work).
- Reading: an administrator reads every assignment; an expert reads the ones currently
  assigned to them; anything else is `not_found`. No role at all: `permission_denied` (`R-80`).
- One open (non-terminal) assignment per scope (the project, or the project and one
  document). An exact repeat of a creation answers the stored assignment; any other
  creation on an occupied scope is `conflict` with `conflict_reason: assignment_open`.
- An exact repeat of a transition (same kind, reason and new assignee as the latest event)
  answers the current state and writes nothing.
- Refusals use the existing catalog: `validation_failed` (`constraint:
  active_expert_required`, `differs_from_current_assignee`, `required`, `not_allowed`,
  `max_length`, `enum`, `pattern`), `permission_denied` (`role:admin`, `role:expert`,
  `assignment:assignee`), `not_found` (`WorkAssignment`, `Project`, `Document`),
  `conflict` (`assignment_open`), `state_transition_not_allowed` (`machine:
  work_assignment`).

## Identity

`asg_<ULID>` is contracted (`identifiers.json`, entity `WorkAssignment`) and owned by the
shared registry; `identity.py` validates through it and refuses with `validation_failed`
(`field: assignment_uid`). History events use `evt_<ULID>` (`AuditEventId`).
