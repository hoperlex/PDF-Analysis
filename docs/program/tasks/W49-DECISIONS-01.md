# Task W49-DECISIONS-01 — the decision event names its author's account

## Outcome

Every new decision event persists `author_user_uid` beside `author_label`; history rows stay NULL and read as "author account unknown".

## Depends on

- `W49-ACCESS-01` merged (the column exists from 01a)

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

- premise: the ledger writes only a display label today

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `git grep -n 'author_label' -- src/auditmanager/decisions/ledger.py | head -3`
- captured_output:
  ```text
  src/auditmanager/decisions/ledger.py:21:``author_label`` is ``OD-12``, and since `R-37` it is **the display name of the reviewer
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

- `src/auditmanager/decisions/**`
- `tests/integration/decisions/**`
- `docs/program/W49-DECISIONS-01.md`

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here; routers (`W49-SEAL-01` wires the subject)

## Non-goals

- no wire change to `DecisionEvent`

## Deliverables

- `ledger` and `journal` accept and persist `author_user_uid`; a NULL history row is listed without error

## Required tests

- the column is written on every new event; a NULL history row lists; `make gate` with literal `GATE OK`

## Integration contract

The ledger signature takes `author_user_uid`; `W49-SEAL-01` passes the subject's `user_uid`.

## Failure/idempotency/security cases

- unique lane ports taken with `ss -ltn` and recorded; owned disposable services only; never kill a process by pattern; no credential in evidence

## Rollback / feature flag

Revert the commit; the column stays (owned by `0015`).

## Handoff

- changed files: listed in `docs/program/W49-DECISIONS-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-decisions-01` at a recorded SHA
