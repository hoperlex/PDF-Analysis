# Task W55B-WEB-BLOCKS — «Блоки» shows portal blocks, crops, recognised text and marked portal descriptions, and the run start shows the budget refusal

## Outcome
«Блоки» shows portal blocks, crops, recognised text and marked portal descriptions, and the run start shows the budget refusal.

## Depends on
- `W55B-RULE-01`, `W55B-FREEZE-01`, and every lane before this one in `W55B-FREEZE-01`'s order (merged)

## Frozen inputs
- domain contract: at the freeze, then as `W55B-SEAL-01` reseals it
- API contract: at the freeze (45 / 52 / 116), then as `W55B-SEAL-01` reseals it
- analysis/comparison/event contract: as `W55B-SEAL-01` reseals it
- migration head: `0020_norms_search`, then `0021_portal_bundles` from SEAL on
- base commit: the previous lane's merge on the integration line (the integrator names it at dispatch)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

The plan's measured facts (`W55-PLAN.md` §B2) were taken on `4fe7615`; re-read each cited location on your base before changing it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the grant of Stage B item 5 `W55B-WEB-BLOCKS` in `docs/program/dispatch/W55-PLAN.md` §B4, with §B5's ownership order, plus `docs/program/W55B-WEB-BLOCKS.md`.

## Forbidden hotspots
- any path outside the grant; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `CURRENT_STATE.md` (unless the grant names it), refs, tags, the stand, `.local/norms/**`

## Non-goals
- other W55b lanes' paths; any model looking at a crop (W56); chunked analysis (W56).

## Deliverables
- Per plan §B3 and the lane's §B4 entry, with the numbers of `W55B-FREEZE-01`.

## Required tests
- command: container-free tests now; DB/S3/stack cases on API `57570`, Next `31670` for the journey, one heavy step at a time, ≥ 3 GiB available, cleaned up afterwards (`R-102`).
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees.
