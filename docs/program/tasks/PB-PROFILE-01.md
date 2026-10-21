# Task PB-PROFILE-01 — the fire-safety (ПБ) section has a draft text profile and runs instead of being refused

task_id: PB-PROFILE-01

## Outcome

A document version confirmed in section ПБ starts a run through the section routing with its
own text profile (`status: draft`, like the other thirteen) instead of the
`section_profile_unavailable` refusal; a version confirmed in another section is still refused
a foreign profile; the project's analysis settings list the fifteenth profile.

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).
- `MODEL-IDENTITY-CHECK-01` is independent; no ordering is required, the executor runs it first.

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

- `src/auditmanager/analysis/text/profile_registry.py`
- `src/auditmanager/analysis/text/profiles/pb/**` (new)
- `tests/unit/analysis/test_text_profile_registry.py`
- `tests/unit/analysis/text_profiles/**`
- `tests/integration/composition/test_analysis_profiles_over_http.py`
- `tests/integration/runs/test_w59_section_profile_recorded.py`
- `tests/integration/sections/test_routing.py`
- `tests/integration/sections/test_staged_routing.py`
- `docs/program/PB-PROFILE-01.md`
- `docs/program/tasks/PB-PROFILE-01.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-b2`, postgres_port `57621`, s3_api_port `61422`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files,
`src/auditmanager/bootstrap/**`, `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/**`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The
worktree `.local/worktrees/gate-night` and the instance `auditmanager-gate-night` belong to a running
gate and are not read or run. A change that needs a path outside the allowed list is reported to the
integrator at once, not made.

## Non-goals

No expert review claim (`D-178` stays open and the profile says `draft`). No model call and no
recording (that is `SECTION-RECORDINGS-01`). No contract or migration: the fifteen sections and
the registry listing already exist. No edit of the thirteen existing profiles.

## Work

1. Read how one existing profile package is laid out and loaded (`profiles/tx/**` and
   `profile_registry.py`, which expects a legacy `source.files` block) and make the loader accept
   a profile authored for this product, with no legacy source, only where it is declared.
2. Write `profiles/pb/**` in the same package shape: categories and checks for fire safety
   (evacuation, fire resistance, fire compartments, fire-fighting access, smoke control) drawn
   only from standards the norms corpus names; no invented requirement numbers; every open
   question for the expert listed in the package, `status: draft`.
3. Update the pins that name PB as the unprofiled section: the registry unit test, the
   analysis-profiles-over-HTTP count (fourteen profiles, AR included, becomes fifteen), the staged routing tests. Where a
   test used PB as 'a section without a profile', give it another seam (a registry built
   without that section, in the test) rather than weakening the refusal.
4. Tests failing first, then green, and a quoted mutation: a registry without the PB entry
   reddens the new test; the foreign-section refusal still holds.

## Deliverables

`profiles/pb/**`, the loader change, updated pins and `docs/program/PB-PROFILE-01.md`.

## Required tests

`tests/unit/analysis/test_text_profile_registry.py` and `text_profiles` (container-free); the
three integration files above are database-backed: write them, run only what runs without
containers, and state in the report which ones were not run (`R-126`).

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

A ПБ version never runs under another section's profile and another section never runs under ПБ.

## Rollback / feature flag

Revert the merge. No flag.
