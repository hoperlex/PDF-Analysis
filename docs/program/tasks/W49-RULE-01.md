# Task W49-RULE-01 — record the identity rulings R-55 … R-61

## Outcome

The seven rulings the owner confirmed on 2026-10-05 are recorded in `OWNER_RULINGS_2026-09-17.md` §3.19 with their dates and sources, so no W49 task starts on an unrecorded exception.

## Depends on

- `W48-INT-CLOSE` — `23e0579`, full gate `GATE OK`
- the owner's confirmation of the texts in `IDENTITY-WAVES.md` §4, by direct poll on 2026-10-05

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

- premise: section 3.18 is the last rulings section; none of R-55 … R-61 is recorded yet

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `git grep -n '^## 3.1[89]' 23e0579 -- docs/program/OWNER_RULINGS_2026-09-17.md`
- captured_output:
  ```text
  23e0579:docs/program/OWNER_RULINGS_2026-09-17.md:1068:## 3.18 — `R-53` and `R-54`, ruled 2026-10-05 for W48 closure and programme succession
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

- `docs/program/OWNER_RULINGS_2026-09-17.md` — new section 3.19 only
- `docs/program/tasks/W49-RULE-01.md`
- `docs/program/W49-RULE-01.md`

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here

## Non-goals

- the provisional numbers in the plans already equal the recorded ones (R-55 follows R-54); no plan text changes

## Deliverables

- section 3.19 with `R-55` … `R-61`

## Required tests

- each heading found once; `git diff --check`; `tests/contract/program/test_wave_governance.py`

## Integration contract

Every W49–W51 task cites these numbers.

## Failure/idempotency/security cases

- texts recorded as confirmed; no reinterpretation

## Rollback / feature flag

Revert the commit.

## Handoff

- changed files: listed in `docs/program/W49-RULE-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-rule-01` at a recorded SHA
