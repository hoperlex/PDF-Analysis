# W61-DISPATCHER-01 — «Диспетчер»: work assignments, statuses, «Мои задачи»

**Base:** `979632af` (`origin/dev` `68868d83` plus the frozen task file) for phase A; phase B
from the integrator's go at `1049367e`, then kept current with `integration/night-1020` in
the shared reseal slot (`R-139`): merged `0f0903f2` (analysis settings), `a820849a` (version
upload), `c22f2049` (decision carryover), `beafeab5` (norms catalogue and Excel export) and
the record-only tips after them, each time re-deriving every generated artifact. Branch
`agent/w61-dispatcher-01`, isolated worktree `w61-dispatcher`, lane PostgreSQL 57530 / MinIO
61130. **Status:** phases A and B complete. Development candidate under `R-135`: no full
gate, no live journey, no push, merge into another branch or tag.

## Phase A — result

An administrator assigns a project, or one document of it, to an active expert with an
optional note; the expert starts, completes or returns it (with a reason); an administrator
reassigns or cancels it. Every change is an immutable event with its actor and time; the
current state is derived from the events and is never stored as an updatable status.

### Migration `0025_work_assignments`

| object | what it holds |
|---|---|
| `work_assignment` | `asg_<ULID>`, project (FK), optional document (FK), **first** assignee, creator, note (≤ 2000), `created_at`; `am_immutable_row` |
| `work_assignment_event` | `evt_<ULID>`, assignment, per-assignment `seq` (unique pair), kind, actor, reason, new assignee, `occurred_at`; `am_immutable_row` |
| `work_assignment_current` | view: latest event and current assignee of each assignment |
| `am_require_work_assignment_event` | deferred constraint trigger: an assignment without its `assigned` event (seq 1) is refused at COMMIT (`AM001`) |

Event shape CHECKs: the six kinds; `assigned` is seq 1 and only seq 1; a new assignee exactly
on `reassigned`; a reason on every `returned`, allowed on `reassigned`/`cancelled`, absent
elsewhere; reason and note 1..2000 characters. All account columns (`assignee_user_uid`,
`created_by_user_uid`, `actor_user_uid`, `new_assignee_user_uid`) are `RESTRICT` and
registered in `access/references.py`, so purging such an account answers `conflict`
(`account_referenced`). Project and document are `RESTRICT` too. No backfill. Downgrade drops
the view, the two tables and the function only, and logs how many rows it drops.

Document-belongs-to-project is enforced by the dispatch context in the writing transaction,
not by a composite key: that would need a new constraint on `document`.

### Context `auditmanager.dispatch`

`identity.py` (`AssignmentUid`), `policy.py` (pure rules), `repository.py` (statements),
`commands.py` (`assign_work`, `transition_assignment`), `queries.py` (`list_assignments`,
`get_assignment`), `public.py`. Imports only `access.public`, `documents.public` and `shared`.

| status (derived from latest kind) | allowed next |
|---|---|
| `assigned` (`assigned`, `reassigned`) | started, returned, reassigned, cancelled |
| `in_progress` (`started`) | completed, returned, reassigned, cancelled |
| `returned` | reassigned, cancelled |
| `done` (`completed`), `cancelled` | — |

- create / `reassigned` / `cancelled`: `admin`; the (new) assignee must exist, be active and
  hold `expert` (`validation_failed`, `constraint: active_expert_required`).
- `started` / `completed` / `returned`: only the current assignee, holding `expert`; an
  administrator who is not the assignee is `permission_denied`
  (`required_capability: assignment:assignee`).
- Reading: admin reads all; an expert reads the assignments currently given to them; anything
  else `not_found` (`WorkAssignment`); no role at all `permission_denied`
  (`role:admin|expert`, `R-80`).
- One open assignment per scope (project, or project + document). An exact repeat of a
  creation answers the stored one; any other creation there is `conflict`
  (`conflict_reason: assignment_open`). Creations on one scope serialize on an advisory lock.
- An exact repeat of a transition (kind, reason, new assignee equal to the latest event)
  answers the current state and writes nothing; anything the table does not allow is
  `state_transition_not_allowed` (`machine: work_assignment`, `current_state`,
  `requested_state`). Transitions serialize on the assignment row lock.

### Checks (phase A)

All on the lane's own containers (`make up`, `make migrate` to `0025_work_assignments`),
`PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`:

- `tests/unit/dispatch` — 65 passed (every status × kind cell against an independently
  written table, who may move, exact repeats, shape refusals, the migration restating the
  vocabulary and bounds).
- `tests/integration/dispatch` — the allow/refuse matrix of every command and read, exact
  repeats, the concurrent-creation lock, purge refused for each referencing column.
- `tests/integration/db/test_work_assignments_migration.py` — upgrade of a populated `0024`
  database with no row changed, `AM003` on both tables, `AM001` without the first event,
  each CHECK and FK, format CHECKs, each account column alone blocking a delete, the view,
  downgrade and re-upgrade. It caught a wrong reason CHECK (a reasonless `returned` was
  admitted) before the commit.
- Whole `tests/integration/db` + dispatch suites: 484 passed, 24 failed; every failure is
  pre-existing at the base (measured on `979632af` before any edit: 26 failed): 23
  downgrades that pass through `0022_findings_v2` fail there with `cannot drop columns from
  view`, and `test_norms_corpus_migration` does not list `norm_retrieval_set` (0023). The
  two base failures of `test_schema_shape` (0024's table and confirmer missing from its
  sets) are fixed here.
- Inventory reseal measured from two fresh databases (0024 vs 0025), row-diffed; the 0024
  database equalled the previous seal in every family.
- `tests/contract/architecture`, `domain_p02`, `api_v1/test_doc_prose_facts.py`,
  `api_v1/test_openapi_conformance.py`, `tools/test_pin_sweep.py`: 286 passed, 1 failed —
  `test_the_scanned_docs_state_the_migration_head_this_tree_has`, because
  `docs/program/CURRENT_STATE.md` (integrator) and `docs/manual-tests/PC-01_prototype.md`
  (phase B path) still say `0024`.

## Phase B — result

### Surface

| | integration tip `beafeab5` | this branch |
|---|---|---|
| paths / operations / schemas | 56 / 63 / 161 | **59 / 67 / 171** |
| API error codes | 25 | 25 |
| migration head | `0024_version_classification` | **`0025_work_assignments`** |

This lane adds 3 paths, 4 operations and 10 schemas to whatever the slot holds.

Four operations, tag `dispatch` (`src/auditmanager/api/routers/dispatch.py`, port
`DispatchPort`, adapter `DispatchAdapter`, wired in `bootstrap/composition.py`):

- `createAssignment` — `POST /assignments`, `admin` (seam register and the command's own
  check), body `CreateAssignmentRequest {project_uid, document_uid?, assignee_user_uid,
  note?}`, `200 Assignment` (new or the exact repeat). `404` for a project or a document not
  of it; `422` `active_expert_required`; `409 conflict` `assignment_open`.
- `listAssignments` — `GET /assignments?mine&status&project_uid&cursor&limit`, any one role,
  `200 AssignmentPage`, newest first; an expert reads only the work currently given to them.
- `getAssignment` — `GET /assignments/{assignment_uid}`, any one role, `200 AssignmentDetail`
  (assignment and history, oldest first); `404` when absent or not visible. No `422`: a
  path identity only, like `getUser`.
- `transitionAssignment` — `POST /assignments/{assignment_uid}/transitions`, any one role at
  the seam; body `TransitionAssignmentRequest {kind, reason?, new_assignee_user_uid?}`;
  `200 Assignment`; `403` (`assignment:assignee`, `role:admin`, `role:expert`), `404`,
  `409 state_transition_not_allowed` (`machine: work_assignment`), `422`.

Ten schemas: `AssignmentUid`, `AssignmentStatus`, `AssignmentEventKind`,
`AssignmentTransitionKind`, `CreateAssignmentRequest`, `TransitionAssignmentRequest`,
`Assignment`, `AssignmentEvent`, `AssignmentDetail`, `AssignmentPage`; one parameter
component `AssignmentUid`; tag `dispatch`. People are named by `display_label` resolved in
the adapter through `access` (`R-55`), never by a client.

Domain family moved to candidate revision 15 together: `identifiers.json` contracts `asg`
(entity `WorkAssignment`; the shared registry gains `AssignmentUid` and the dispatch type
validates through it), `state-machines.json` gains `work_assignment` (not seeded into
`contract_state_transition`; decided by `auditmanager.dispatch`), and `error-codes.json`
notes register `assignment_open`, `active_expert_required`, `differs_from_current_assignee`
and `assignment:assignee`. No error code added.

Reseal (re-derived after every merge of the slot): `web/openapi/openapi.json` byte-identical
to the contract, client regenerated (`api:generate`, `api:verify` OK, contract SHA-256
`10ee059fbcddc3381284510d486ebe30911ac4e9b99b65c8d4138842ee4e3bfa`), `FRONTEND_LOCK.json`,
`expected_facts.json` (59/67/171, head `0025_work_assignments`), the surface prose
(P02_SEAMS operation table and §7 repeat rules, ALPHA_ROADMAP triple, manual-tests head,
infra/deploy README/nginx/serve, api README/app/health, declarations, errors, BFF route,
authorization.ts), the 422 split (48 declare one, 19 do not), and the pins that count
operations: the NotFound sweep (42), the GET partition (22 addressed / 17 not), the
identifier count (34), the prose mutation lines. Tests that enumerate operations name the
four: `test_openapi_document`, `test_authorization`, `test_role_register`,
`test_operation_surface`, `test_served_document_and_health_plane`, `test_query_surface`
(plus a dedicated test driving `mine`, `status`, `project_uid`, `cursor`, `limit`),
`test_every_port_implementation_is_whole`.

### Web

- «Диспетчер» at `/dispatcher`, in «Работа» after «Оптимизация разделов» (`any-role`): an
  administrator gets «Назначить работу» (project, optional document, active expert, note) and
  the list with status filter, «Только мои», reassign/cancel and per-row history; an expert
  gets their own work with «Взять в работу» / «Отметить выполненным» / «Вернуть» (reason).
  The viewer's identity comes from `getMe`, so the assignee's moves appear only on their rows.
- «Мои задачи» on the home screen for a session holding `expert`: open work (assigned, in
  progress, returned) with the moves and links to the project or document, and a link to the
  whole list.
- Slices: entity `assignment`, features `create-assignment` and `transition-assignment`,
  widgets `assignment-board` and `my-tasks`, page `dispatcher`, route `app/dispatcher`; query
  root `assignments` (documented in `web/docs/PC01_UI_SEAM.md` §6); `routes.dispatcher()`.

### Known limitations

- An account archived or stripped of `expert` keeps its open assignments; an administrator
  reassigns or cancels them.
- The creation form lists the first page of projects and of each project's documents (50),
  and the first page of accounts (50) as the expert choices.
- The live browser journey was not run (`R-135`); the manifest gains the `/dispatcher` route
  and the home screen's optional `listAssignments`.
- `docs/program/CURRENT_STATE.md` still states 51/58/147 and head `0024` (integrator's file;
  `test_doc_prose_facts` names exactly those two lines).
