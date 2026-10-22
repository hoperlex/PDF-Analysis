# Task PB-PINS-01 — the tests that asserted the ПБ section has no profile say what is now true

task_id: PB-PINS-01

## Outcome

The five test files that pinned «ПБ has no profile» assert the new truth: ПБ has a draft
profile, appears among the executable sections, and a start for it routes to that profile; the
refusal for a section without a profile is still proven, through a seam that does not need a
real section to be profile-less. Nothing is weakened: every assertion removed is replaced by one
that fails if the profile is dropped.

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).
- `PB-PROFILE-01` — completed on `agent/lane-b-01` (tip `ba9f1a63`); this slice starts from that branch.

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `d38f9c54`, `integration/night-1020`);
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

- `tests/integration/runs/test_w59_section_routing_over_http.py` (lines 365-369 and 412-416 at the base)
- `tests/integration/composition/test_the_served_application_routes_by_section.py` (line 114 at the base)
- `web/tests/unit/styles/screens.ts`
- `web/tests/unit/sections/classification-correction.test.ts`
- `web/tests/unit/sections/classification-panel.test.ts`
- `docs/program/PB-PINS-01.md`
- `docs/program/tasks/PB-PINS-01.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-b4`, postgres_port `57625`, s3_api_port `61430`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files,
`src/auditmanager/bootstrap/**`, `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/**`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The
worktree `.local/worktrees/gate-night` and the instance `auditmanager-gate-night` belong to a running
gate and are not read or run. A change that needs a path outside the allowed list is reported to the
integrator at once, not made.

## Non-goals

No source change: the `analysed` flag of `web/src/entities/project/model/section.ts` is a legacy
marker that is `false` for every section but AR although thirteen have profiles (the API's
`SectionReviewOption.executable` decides what can run), so PB staying `false` is consistent and
is left alone unless a test proves otherwise (then report the file and line). The stale sentences
in `api/routers/analysis_profiles.py` and `section_candidates/metadata.py` docstrings stay: they
are prose in `src/**` and a docstring edit there is not worth a source slice now (recorded as
documentation debt in the report).

## Work

1. Read each pinned assertion in context. The two database-backed files cannot be run in this
   lane (`R-126`): edit them with the same care as the others, `py_compile` and `--collect-only`
   them, and say plainly that they were not run; the integrator's complete gate runs them.
2. `test_w59_section_routing_over_http.py`: `PB` is now in the executable set; the start for PB
   routes to its profile (in recorded mode with no recording it ends failed with
   `recording_missing` until `SECTION-RECORDINGS-01`: assert exactly what the code does, citing
   the slice). The refusal `section_profile_unavailable` is proven on a registry built without a
   section, as `PB-PROFILE-01` did in the unit tests.
3. `test_the_served_application_routes_by_section.py`: `PB` is in `section_profiles`.
4. The three web files: the fixtures and expectations that treated ПБ as not executable or as
   profile-less follow the API fixtures; run the named web test paths and the style census guard.
5. A quoted mutation per changed assertion class (a registry without PB reddens it).

## Deliverables

The five changed test files and `docs/program/PB-PINS-01.md`.

## Required tests

Web: `npm --prefix web run typecheck`, `lint -- --quiet`, `npm --prefix web test -- --run
web/tests/unit/sections web/tests/unit/styles`. Python: `py_compile` and `--collect-only` of the
two integration files; they are not run. Quote every command with its exit status.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

A registry without ПБ still refuses a ПБ start with `section_profile_unavailable`.

## Rollback / feature flag

Revert the merge. No flag.
