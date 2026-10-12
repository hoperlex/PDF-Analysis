# Task W54-BGE-IMAGE — A pinned, network-free BGE-M3 norms-worker image definition whose build reproduces the recorded bake-off MRR exactly

## Outcome
A pinned, network-free BGE-M3 norms-worker image definition whose build reproduces the recorded bake-off MRR exactly.

## Depends on
- `W54-RULE-01`, `W54-FREEZE-01`

## Frozen inputs
- domain contract: `contracts/domain/v1` at the freeze commit
- API contract: `contracts/api/v1/openapi.json` at the freeze commit
- analysis/comparison/event contract: unchanged
- migration head: `0017_execution_queue`
- base commit: the `W54-FREEZE-01` commit on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

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
- Exactly the `W54-BGE-IMAGE` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage A, plus `docs/program/W54-BGE-IMAGE.md`.

## Forbidden hotspots
- any path outside the grant; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`
- root dependency/lock files unless the plan grant names them

## Non-goals
- The embedder and its repository (`W54-EMBED-01`); any corpus load.

## Deliverables
- Per plan §3.4 and §4: `infra/norms-worker/**` pinned by digests, the `norms_worker` entry in `FOUNDATION_LOCK.json`, `test_norms_worker_image_contract.py` (static contract now), the report.

## Required tests
- command: Container-free now: the static image-contract test. **Heavy, window only:** the build (≈ 6.5 GB increment, ≈ 3.2 GiB RAM, ≈ 450 s) and the `--network none` MRR reproduction on the 24 queries — do not start; hand back the exact commands for the integrator to run in the window.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges `agent/w54-bge-image` after reading the diff and the report; heavy steps listed in the report run in the owner's window under `W54-FREEZE-01`.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees; no heavy step outside the window (`R-102`, `W54-FREEZE-01`).
