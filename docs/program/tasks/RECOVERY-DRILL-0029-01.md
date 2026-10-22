# Task RECOVERY-DRILL-0029-01 — the B6 restore drill repeated at migration head 0029

task_id: RECOVERY-DRILL-0029-01

## Outcome

The synthetic backup-and-restore drill of `RECOVERY-REBASE-01` (database and Blob copy, isolated restore, schema audit, Blob audit, independent
cross-check) is run once more on a lane stack at head `0029_routing_refusal_codes`, with the realistic recorded-provider dataset, and its
evidence is recorded, so that beta criterion B6 (`BETA-MATRIX-02.md` §B6) reads "drill run at the current head" instead of "run at 0028;
the pin moved to 0029 without a drill".

## Depends on

- `RECOVERY-REBASE-01` — completed (the drill and the tooling); `BETA-MATRIX-02` — merged (it names the gap).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `ddcef5b2`);
- migration head `0029_routing_refusal_codes` (`scripts/recovery/schema_coverage.py` `HEAD` already names it); API 73/83/242; no contract and no migration change;
- rulings: `R-135`; the owner's standing order of 2026-10-22 «гони до беты без вопросов»; no paid call (recorded provider only, `R-29`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/RECOVERY-DRILL-0029-01.md`
- `docs/program/tasks/RECOVERY-DRILL-0029-01.md`
- `scripts/recovery/**` and `tests/integration/recovery/**` only if the drill at 0029 shows a head-pinned defect there (then the report names it, the failing test first, a quoted mutation)

## Lane resources

- foundation_instance: `auditmanager-lane-i`
- postgres_port: `57690` is taken by the gate stand; use `57700`
- s3_api_port: `61500`, s3_console_port: `61501`
- postgres_db: `auditmanager_lane_i`
- s3_bucket: `auditmanager-lane-i`

## Forbidden hotspots

Every `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `web/**`, `tests/support/**`, any
`conftest.py`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. Never run anything in or write to
`.local/worktrees/gate-night` and never touch its containers, volumes or ports; never touch another lane's stand.

## Non-goals

No real backup of the stand, no use of the stand's data, no restore onto any existing database, no change of the tooling unless the drill proves it needed.

## Work

1. Read `docs/program/RECOVERY-REBASE-01.md` sections 5, 6 and 9 ("Reproduce" has the exact commands) and `BETA-MATRIX-02.md` §B6.
2. Provision your worktree (`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, your `.env` with BOTH sides rewritten to the lane resources above), bring up only your own stack,
   migrate to head (`make migrate`), confirm the head with `alembic current`.
3. Run the section-9 sequence on the fresh lane database: seed, copy (list, conditional read, rehash, seal), offline preflight, isolated restore with audit, readback, independent compare.
   Quote every command with its exit status and time; the evidence is exit 0, N of N objects and Blobs, every table and view equal, every trigger equal.
4. Run `tests/integration/recovery` in full on the lane stack (one pytest process; 239 passed at 0028 is the reference) and report any red with its cause.
5. A deliberate negative: run the drill's loud guard once against a copy whose table set differs (the existing tests do it; quote the test names and their result), so the report shows the drill can fail.
6. `make down` for YOUR instance when done; remove nothing else.

## Deliverables

`docs/program/RECOVERY-DRILL-0029-01.md`: the head, the dataset size, the commands with exit status and time, the equality figures, what was not claimed (a real stand backup, the Blob store of the stand, the retention policy `U-04`).

## Required tests

The drill itself and `tests/integration/recovery` as above; `git diff --check`.

## Integration contract

Merged by the integrator (not by the executor) as a real merge. Commit after every solid step; hand back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A restore never targets an existing database; no secret appears in a log or the report; the lane stack is removed (`make down`) at the end.

## Rollback / feature flag

Revert the merge. Documentation (and tests only if the tooling needed a repair); no flag.
