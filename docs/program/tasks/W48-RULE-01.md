# Task W48-RULE-01 — record the durable-effects authority and withdrawn W49

## Outcome

Rulings `R-53` and `R-54` are records of the owner's decisions and the original W48 plan has a
dated addendum assigning the exceptional migration/composition/release slots.

## Depends on

- `W48-SAFE-01`

## Frozen inputs

- domain contract: W48 frozen revision 8
- API contract: W48 frozen 17 / 20 / 61 surface
- analysis/comparison/event contract: unchanged
- migration head: `0014_durable_analysis_effects`
- base commit: `e3e85b05d6baa74387d6f3c0f38d23828f9e1f9d`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `R-52` is the last recorded ruling and W48 still says the migration has no owner

### P-01 — ruling tail and obsolete ownership sentence

- captured_at: 2026-10-05
- command: `rg -n 'R-52|db/migrations/\*\*, migration head' docs/program/OWNER_RULINGS_2026-09-17.md docs/program/dispatch/W48-PLAN.md`
- captured_output:
  ```text
  docs/program/dispatch/W48-PLAN.md:188:| `db/migrations/**`, migration head | frozen/no owner | none |
  ```
- interpretation: the plan needs an addendum; absence of `R-52` from this captured excerpt is
  not used as a numbering measurement.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/dispatch/W48-PLAN.md`
- addendum_path: `docs/program/dispatch/W48-PLAN.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/OWNER_RULINGS_2026-09-17.md`
- `docs/program/dispatch/W48-PLAN.md` (new dated addendum only)
- `docs/program/W48-RULE-01.md`

## Forbidden hotspots

- every contract, migration, runtime, test, lock and composition path
- `origin/dev`, `origin/main`, tags and deployment

## Non-goals

- no implementation, repair or publication

## Deliverables

- exact `R-53`/`R-54` text from `IDENTITY-WAVES.md` section 4, the W48 addendum and report

## Required tests

- each new ruling number is unique in the rulings file
- `git diff --check`

## Integration contract

All following W48 closure tasks may rely on migration `0014`, the public-module slot and the
separate main/tag task being authorised exactly as the addendum states.

## Failure/idempotency/security cases

- any wording beyond the owner's supplied text or any renumbering collision stops the task

## Rollback / feature flag

Documentation-only owner record; correction is a forward addendum, never silent deletion.

## Handoff

- changed files: the three allowed documents
- commands/results: in the task report
- known limits: no deployment authority is granted
- integration notes: dispatch judge 2, guards 2 and tails only after this commit
