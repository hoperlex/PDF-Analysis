# Task W49-FREEZE-01 — freeze the identity wave

## Outcome

The W49 base, contract set and migration head are recorded; every W49 task file exists with exact paths; lane ports are taken.

## Depends on

- `W49-RULE-01`

## Frozen inputs

- domain contract: revision 8, 27 opaque identities (moves only in `W49-SEAL-01`)
- API contract: 17 / 20 / 61 (moves only in `W49-SEAL-01`)
- error catalog: 22 codes (moves only in `W49-SEAL-01`: `rate_limited`)
- migration head: `0014_durable_analysis_effects` (moves only in `W49-ACCESS-01`)
- code base: `23e0579`, the W48 closure published to `origin/dev`
- controlling plan: `docs/program/dispatch/W49-PLAN.md` at the freeze commit

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the base carries one migration head and the frozen surface

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads`
- captured_output:
  ```text
  0014_durable_analysis_effects (head)
  ```
- interpretation: measured on the code base before dispatch; the lane re-measures it first.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W49-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W49-*.md`
- `docs/program/W49-FREEZE-01.md`
- `docs/program/dispatch/PORT_REGISTRY.md` — W49 rows and the corrected W48 judge/fix rows

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here

## Non-goals

- no code; no ref publication (the owner publishes `origin/dev`)

## Deliverables

- eight task files; port rows; the freeze record

## Required tests

- `tests/contract/program/test_wave_governance.py`; `git diff --check`

## Integration contract

Every lane starts from the freeze commit on `integration/w49` and nothing else.

## Failure/idempotency/security cases

- a moved base or a red gate at the base stops the freeze

## Rollback / feature flag

Revert the commit.

## Handoff

- changed files: listed in `docs/program/W49-FREEZE-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-freeze-01` at a recorded SHA
