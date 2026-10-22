# Task SECTION-RECORDINGS-01 — every section profile is proven in recorded mode and refuses a foreign section

task_id: SECTION-RECORDINGS-01

## Outcome

Each of the ten sections that has a profile but no recording (КЖ, КМ, ОВ, ВК, ПТ, ЭОМ, СС, ИТП,
ГП, and ПБ once `PB-PROFILE-01` is merged) has a synthetic recorded case that replays through its
own profile, and a negative case that a foreign section's request is refused; the recordings are
labelled synthetic.

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).
- `PB-PROFILE-01` for the ПБ case only; the other nine do not wait for it.

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `b1154df2`, `integration/night-1020`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`
  sealed: this task changes no contract and adds no migration;
- rulings: `R-135` (no complete gate in a lane), `R-126`, and the owner's direct instruction of
  2026-10-22 «гони до беты без вопросов»: a naming or policy choice that is not blocked by a
  recorded owner decision is taken with the default named below and reported, not asked.

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

- `fixtures/recorded/sections/**`
- `tests/integration/sections/test_section_recordings.py`
- `docs/program/SECTION-RECORDINGS-01.md`
- `docs/program/tasks/SECTION-RECORDINGS-01.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-b3`, postgres_port `57622`, s3_api_port `61424`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files,
`src/auditmanager/bootstrap/**`, `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/**`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The
worktree `.local/worktrees/gate-night` and the instance `auditmanager-gate-night` belong to a running
gate and are not read or run. A change that needs a path outside the allowed list is reported to the
integrator at once, not made.

## Non-goals

Not field evidence: the recordings stay synthetic and say so (`D-183`). No model call, no live
mode, no change to `src/**`. The `infra/deploy/Dockerfile.api` comment named by `D-183` is an
`infra/**` change and is left to the next infra slice.

## Work

1. Follow the existing pattern (`fixtures/recorded/sections/build_fixtures.py` and the four
   existing section directories) to produce a recording per missing section; recordings are
   keyed by the request digest, so build them with the script, never by hand.
2. Extend `tests/integration/sections/test_section_recordings.py` to cover every section with a
   profile and the foreign-section refusal.
3. `build_fixtures.py --check` passes (the recordings are reproducible), and a quoted mutation
   (a changed profile text, a changed request) reddens it.

## Deliverables

The recordings, the extended test and `docs/program/SECTION-RECORDINGS-01.md` with the command and result of `--check`.

## Required tests

`fixtures/recorded/sections/build_fixtures.py --check` and the recordings test where it runs
without containers; state what was not run.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

A recording for one section never answers another section's request.

## Rollback / feature flag

Revert the merge. No flag.
