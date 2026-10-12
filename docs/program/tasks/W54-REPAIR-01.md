# Task W54-REPAIR-01 — The 121 corpus page repairs run through a durable, locally fsynced call journal with a $10 ceiling and a sample stop

## Outcome
The repair machinery (promotion database tooling, re-recognition, durable repair journal) exists and is proven with zero live calls; the paid run itself is `W54-CORPUS-OPERATE-01`.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01`, `W54-CUSTODY-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the CUSTODY merge on `integration/w54`

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
- Exactly the `W54-REPAIR-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 2, plus `docs/program/W54-REPAIR-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**` (read-only)

## Non-goals
- the paid repair run (`W54-CORPUS-OPERATE-01`, in a window, with the owner's proxy key); snapshot, embedding, bundle.

## Deliverables
- Per plan §3.2, §3.3 and §4 Stage B item 2: a kill after acceptance and before the ledger write does not re-pay; the write order and both reconcile directions; `R-79`'s tries; 503 ambiguous (`R-85`/D-153); the cumulative $10 ceiling and the sample stop (`R-95`); the local fsynced journal (`R-98`); a lost volume reconciled; a model mismatch refused; the `+<m>u` key and the inverted test; zero live calls in tests. SEAL's note: `norm_repair_call` stores only `response_sha256`; keep the response bytes beside the local journal.

## Required tests
- command: container-free tests now; DB-backed tests (promotion database, `tests/integration/norms/**`) are heavy steps on PostgreSQL `57140`, S3 `60740/60741` for the integrator's window — list exact commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report and runs the listed heavy steps in the window.

## Failure/idempotency/security cases
- No live provider call anywhere in this lane. Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window.
