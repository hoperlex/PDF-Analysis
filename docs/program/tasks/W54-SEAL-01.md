# Task W54-SEAL-01 — Migrations `0018_norm_custody` and `0019_execution_workers`, the new identifiers, the two stub operations, the role registers and the four-document reseal exist, with every pin swept

## Outcome
Migrations `0018_norm_custody` and `0019_execution_workers`, the new identifiers, the two stub operations, the role registers and the four-document reseal exist, with every pin swept.

## Depends on
- `W54-RULE-01`, `W54-FREEZE-01`

## Frozen inputs
- domain contract: `contracts/domain/v1` at the freeze commit
- API contract: `contracts/api/v1/openapi.json` at the freeze commit
- analysis/comparison/event contract: unchanged
- migration head: `0017_execution_queue`
- base commit: the `W54-FREEZE-01` commit on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: contracts/api/v1/openapi.json
- enumerator_owner: W54-SEAL-01
- totality_query: `.venv/bin/python tools/plan/pin_sweep.py --help` (run the reseal-surface/migration/table/route sweep and grant every printed path)

## Captured premise evidence
- premise: none

The plan's measured facts (`W54-PLAN.md` §2) were taken on `4fe7615`; re-read each cited location before changing it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W54-SEAL-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage A, plus every further path `tools/plan/pin_sweep.py` prints for this reseal, plus `docs/program/W54-SEAL-01.md`.

## Forbidden hotspots
- any path outside the grant; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`
- root dependency/lock files unless the plan grant names them

## Non-goals
- Custody, repair, snapshot, embedding, worker logic (Stage B); stub operations answer as the plan says and implement nothing else.

## Deliverables
- Per plan §4 `W54-SEAL-01` and §3.1/§3.6: both migrations (upgrade from empty and from `0017` with rows; refused downgrade with retained data), identifiers `nad`, `nbd`, `nrc`, `wrk`, the two stub operations, role registers (R-80 any-role for product reads), the reseal of the four contract documents, facts, ADR addenda (`R-104`, `R-105`), `NORM_CORPUS_CUSTODY.md`, and the swept pins.

## Required tests
- command: Container-free now: `pytest tests/contract`, web lint/typecheck/vitest of touched files. **Heavy, window only** (do not run before the integrator says the window is open): the migration tests on the private lane (PostgreSQL 57110, S3 60710/60711) — hand back listing them.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges `agent/w54-seal-01` after reading the diff and the report; heavy steps listed in the report run in the owner's window under `W54-FREEZE-01`.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees; no heavy step outside the window (`R-102`, `W54-FREEZE-01`).
