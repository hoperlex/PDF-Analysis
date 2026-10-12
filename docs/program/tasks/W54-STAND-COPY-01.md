# Task W54-STAND-COPY-01 — The one-off stand copy tooling (copy key verbs, attested copy record, test-data waiver, real-data marker) and the deploy.sh refusal while a copy or import is open

## Outcome
The one-off stand copy tooling (copy key verbs, attested copy record, test-data waiver, real-data marker) and the deploy.sh refusal while a copy or import is open.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01`, `W54-TRANSPORT-01`, `W54-WORKER-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the WORKER merge on `integration/w54`

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
- Exactly the `W54-STAND-COPY-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage C, plus `docs/program/W54-STAND-COPY-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- The importer's acceptance rule (`W54-BUNDLE-01`); any stand access.

## Deliverables
- Per plan §3.5, §3.10 and §4 Stage C, and `W54-FREEZE-01` amendment 2: copy verbs `capacity`, `dump-db`, `inventory-s3`, `fetch`, `attest`, `verify-objects`, `restore-db`, `resume`, `status` with a refusal per guard and verb; `attest --test-data` writing a `test_data_waiver` record; the `real_data` marker written by a full copy, after which waivers are refused; `dump-db` stops exactly the writers present (including the W54 `worker` service); `resume` refused under an import lock (`<staging>/import.lock`, TRANSPORT's contract); `restore-db` re-quiesces and checks the digest; `deploy.sh` refuses with `stand_copy_open` / `stand_import_locked` before any docker call, with its case in `test_deploy_script_refusals.py`; `shellcheck`.

## Required tests
- command: container-free with `docker` stubbed on `PATH`: the composition refusal suites named in the grant; `shellcheck`; restore-here and dump-reproduces-fingerprint cases that need a real PostgreSQL are heavy steps for the window — list exact commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window.
