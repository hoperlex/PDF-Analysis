# Task W54-CUSTODY-01 — Two-phase custody of corpus source PDFs and crops (admission, then binding) with D-142 settlement, D-143 report and refusal, and the D-146 concurrent-declarer fix

## Outcome
Two-phase custody of corpus source PDFs and crops (admission, then binding) with D-142 settlement, D-143 report and refusal, and the D-146 concurrent-declarer fix.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: `contracts/domain/v1` after `W54-SEAL-01`
- API contract: `contracts/api/v1/openapi.json` after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers` (not yet DB-tested; the integrator runs it in the window)
- base commit: the Stage-A merge on `integration/w54`

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
- Exactly the `W54-CUSTODY-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 1; in `src/auditmanager/jobs/repository.py` only the D-142 settlement code, and in `tests/integration/qa_w53/test_queue_and_effect_journal.py` only the settlement assertions (WORKER owns the rest of both, in parallel); plus `docs/program/W54-CUSTODY-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations (SEAL's); `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`

## Non-goals
- Repair, snapshot, embedding, bundle, worker service.

## Deliverables
- Per plan §3.1 and §4 Stage B item 1: the five interruption points and eight cases; admission before the target, binding with it; an orphaned admission stays unbound; double admission a no-op; equal bytes under two roles; a media-type conflict; two concurrent declarers (D-146); D-142 settlement and event; D-143 report and refusal.

## Required tests
- command: container-free tests now; DB/S3-backed tests are heavy steps on PostgreSQL `57120`, S3 `60720/60721` and run only when the integrator opens the owner's window (`R-102`, `W54-FREEZE-01`) — write them and list exact commands in the report.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report, and runs the listed heavy steps in the window.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees; no container before the window.
