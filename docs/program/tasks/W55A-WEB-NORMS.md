# Task W55A-WEB-NORMS — The «Нормы» screen searches the current snapshot, opens a norm document with unreliable paragraphs marked, and lets administrators designate the current snapshot

## Outcome
The «Нормы» screen searches the current snapshot, opens a norm document with unreliable paragraphs marked, and lets administrators designate the current snapshot.

## Depends on
- `W55A-FREEZE-01`, `W55A-SEAL-01` (merged)

## Frozen inputs
- domain contract: after `W55A-SEAL-01`
- API contract: after `W55A-SEAL-01` (45 / 52 / 116)
- analysis/comparison/event contract: unchanged
- migration head: `0020_norms_search`
- base commit: the SEAL merge

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
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W55A-WEB-NORMS` grant in `docs/program/dispatch/W55-PLAN.md` §A4 Stage B item 4, plus `docs/program/W55A-WEB-NORMS.md`

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- other W55a lanes' paths (plan §A5).

## Deliverables
- Per plan §A3.7 and §A4 item 4, on SEAL's generated client (the operations answer 503 stubs until SEARCH lands): search with designation, clause, fragment and «открыть» (PDF at `page_label`); a document view (second registry row, `'any-role'`); for admins the snapshot list, «сделать текущим» with confirmation and `expected_current`, and the history; the refusal state rendered (never an empty list) before any current snapshot; role-less kept out; admin controls hidden from experts; `/norms` leaves R-66 `STUBS`.

## Required tests
- command: container-free: web lint, typecheck, Vitest (touched, then one full run); the live journey (`e2e:pc01 --phase all`) is a window step.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
