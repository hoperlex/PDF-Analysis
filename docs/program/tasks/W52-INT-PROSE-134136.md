# Task W52-INT-PROSE-134136 — correct W50 return, menu and bundle prose

task_id: W52-INT-PROSE-134136

## Outcome

The live W50 screen-registry comments and plan describe measured return-path,
menu and first-load bundle behavior without the three D-134…D-136 overclaims.

## Depends on

- `W52-INT-129F5-01` — published at
  `5a761f01eb6696eaa23be3ce269f5483bac1bed5`.

## Frozen inputs

- Exact base `5a761f01eb6696eaa23be3ce269f5483bac1bed5`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-134…D-136 in `docs/program/DEBT_REGISTER.md`; W50 Judge X/Y reports
  and `R-66` in the owner rulings.
- Owner direction 2026-10-08: basic tests and lint only; QA, stand and full
  gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: live comments and the plan still assert the three disproved absolutes.

### P-01 — exact base and prose

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'never echoed|hide one it opens|never echoes what it was given|five target routes' web/src/shared/config/screen-registry.ts docs/program/dispatch/W50-PLAN.md`
- captured_output:
  ```text
  5a761f01eb6696eaa23be3ce269f5483bac1bed5
  docs/program/dispatch/W50-PLAN.md:82:registry address shape; anything else is dropped, never echoed. The sign-in form carries the
  docs/program/dispatch/W50-PLAN.md:110:  owner's direct poll of 2026-10-07: the five target routes' first-load JS falls, and no other
  web/src/shared/config/screen-registry.ts:40: * screen. A value that fails it is dropped and never echoed.
  web/src/shared/config/screen-registry.ts:287: * cannot offer a screen the guard refuses, or hide one it opens (`W50-SHELL-FRAME`; the
  web/src/shared/config/screen-registry.ts:363: * never echoes what it was given.
  ```
- interpretation: D-134…D-136 give the measured limits; changing prose does not
  change routing or bundle bytes.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/reviews/W50-JUDGE-X.md` and
  `docs/program/reviews/W50-JUDGE-Y.md` (immutable)
- addendum_path: `docs/program/W52-INT-PROSE-134136.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/shared/config/screen-registry.ts` — comments only
- `docs/program/dispatch/W50-PLAN.md` — §3.2 and §3.4 wording only
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/W52-INT-PROSE-134136.md`
- `docs/program/W52-INT-PROSE-134136.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependency/lock files,
runtime expressions, composition root and global styles.

## Non-goals

No behavior change, framework-metadata filtering, new route, browser QA,
temporary stand, full gate, release, tag or `origin/main` publication.

## Deliverables

- Correct the two return-path comments, the menu comment and the W50 plan's
  return-path and four-decrease/one-increase statements.
- Record what the earlier judges measured and what remains deferred.

## Required tests

- Focused return-path/navigation tests, governance/prose tests, frontend lint
  and `git diff --check`; no browser stand or full gate.

## Integration contract

Only prose changes. Publish to `origin/dev` after exact remote-ref and
fast-forward verification; retain D-139/D-140 for deferred validation.

## Failure/idempotency/security cases

Do not claim invalid raw query bytes are absent from Next Flight metadata;
do state that invalid paths do not reach the visible field/redirect. Do not
make `/optimisation` appear in the menu.

## Rollback / feature flag

Revert this documentation commit. No feature flag because no behavior changes.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and proof
  that forbidden hotspots were untouched.
