# Task EXEC-ADR-01 — ADR-0002 addendum: remote executors for model work (R-143c)

task_id: EXEC-ADR-01

## Outcome

`ADR-0002` gains an `R-143` addendum. It replaces, for model work only, the W54 addendum's
sentence "Remote workers on other hosts remain out of scope (W54 non-goal); a second host
would need its own ADR under this one's rule". The W54 addendum's text stays as written,
because history is immutable. The new addendum says:

- the remote party answers model calls;
- it never connects to PostgreSQL or S3;
- the local `worker` stays the Job/Attempt/Lease authority;
- the stand gains exactly one new inbound surface, the runner API of `EXEC-PULL-01`.

`ROADMAP-TO-BETA.md` and `CODE-FIRST-TO-BETA.md` each get a one-line pointer saying that
`R-143d` moves executor connections into the beta scope.

## Depends on

- `EXEC-RULE-01` — merged.

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze (planned on
  `7cb317b0a6fa9ae74c8a5e152419027ec37aca2d`);
- `R-143a`–`R-143d`; plan `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md` §2, §4, §7.

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

- `docs/architecture/adr/ADR-0002-modular-monolith-control-plane.md`
- `docs/program/dispatch/ROADMAP-TO-BETA.md`
- `docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- `docs/program/EXEC-ADR-01.md`

## Forbidden hotspots

`src/**`, `web/**`, `contracts/**`, `db/migrations/**`, `infra/**`, dependency and lock
files, `src/auditmanager/runs/scope.py` (it moves with `EXEC-PULL-01`, the first slice that
has remote execution), `CURRENT_STATE.md`, `DEBT_REGISTER.md`.

## Non-goals

No rewrite of the W54 addendum. No new ADR number. No change to the roadmap's wave table
beyond the pointer.

## Deliverables

The addendum (≤ 30 lines, the same shape as the W54 addendum), the two pointers, and the
report `docs/program/EXEC-ADR-01.md`.

## Required tests

- command: `git diff --check`
- expected: no output.
- command: `python3 -m pytest -q tests/contract/api_v1/test_doc_prose_facts.py tests/contract/program`
- expected: all passed.

## Integration contract

Documentation only. Executed as a Haiku subagent (`R-143e`, a minor task) and merged by the
integrator. It may merge beside `EXEC-SEAL-01`, because the two share no path.

## Failure/idempotency/security cases

The addendum must not claim behaviour that does not exist yet. It states what slices 4–6
will add and points to their task IDs.

## Rollback / feature flag

Revert the merge.

## Handoff

- changed files: the four allowed paths;
- commands/results: the two commands above with exit status;
- known limits: none expected;
- integration notes: none.
