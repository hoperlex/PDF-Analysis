# W61-DISPATCHER-01 — «Диспетчер»: work assignments, statuses, «Мои задачи»

**Base:** `979632af` (`origin/dev` `68868d83` plus the frozen task file), branch
`agent/w61-dispatcher-01`, isolated worktree `w61-dispatcher`, lane PostgreSQL 57530 / MinIO
61130. **Status:** phase A (migration and domain context) complete; phase B (operations,
reseal, screens) waits for the contract slot. Development candidate under `R-135`: no full
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

### Known limitations

- `asg` is minted on the shared registry's pattern but is not contracted: phase B needs
  `contracts/domain/v1/identifiers.json` **and** `src/auditmanager/shared/identity/ids.py`
  (the catalog test holds them equal), and `shared/**` is not in this task's paths.
- New detail values (`assignment_open`, `active_expert_required`,
  `differs_from_current_assignee`, `assignment:assignee`) and the `work_assignment` machine
  are to be registered in `contracts/domain/v1` in phase B.
- An account archived or stripped of `expert` keeps its open assignments; an administrator
  reassigns or cancels them.
