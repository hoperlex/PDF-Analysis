# Task W54-TRANSPORT-01 — The bundle transport scripts (`receive-bundle.sh`, `push-bundle.sh`, `lib/forced-command.sh`) refuse every guard and grammar violation of the inbound key's verbs

## Outcome
The bundle transport scripts (`receive-bundle.sh`, `push-bundle.sh`, `lib/forced-command.sh`) refuse every guard and grammar violation of the inbound key's verbs.

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
- Exactly the `W54-TRANSPORT-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage A (`infra/deploy/README.md` only after SEAL's merge — leave it for the rebase), plus `docs/program/W54-TRANSPORT-01.md`.

## Forbidden hotspots
- any path outside the grant; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`
- root dependency/lock files unless the plan grant names them

## Non-goals
- The copy key and its verbs (`W54-STAND-COPY-01`), the importer itself (`W54-BUNDLE-01`), any stand access.

## Deliverables
- Per plan §3.5 and §4: the inbound forced-command verbs (receive/status/import/report/requeue) with a refusal per guard and grammar violation, the real repaired key accepted, size refused before reading, a mismatching tar removed inside staging only, `import`/`report`/`requeue` invoking only the fixed module command; runbook section.

## Required tests
- command: Container-free: `pytest tests/integration/composition/test_bundle_transport_refusals.py` with `docker` stubbed on `PATH`; `shellcheck` if present (report if absent).
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges `agent/w54-transport-01` after reading the diff and the report; heavy steps listed in the report run in the owner's window under `W54-FREEZE-01`.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees; no heavy step outside the window (`R-102`, `W54-FREEZE-01`).
