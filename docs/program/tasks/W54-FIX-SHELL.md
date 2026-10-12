# Task W54-FIX-SHELL — The stand scripts refuse instead of passing silently, serialise resume with import and record writers, and keep the previous copy restorable

## Outcome
The stand scripts refuse instead of passing silently, serialise resume with import and record writers, and keep the previous copy restorable.

## Depends on
- `W54-JUDGE-A`, `W54-JUDGE-Y` (`docs/program/reviews/W54-JUDGE-{A,Y}.md`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the judges' record commit on `integration/w54`

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
- `infra/deploy/{deploy,copy-serve,receive-bundle}.sh`, `infra/deploy/lib/forced-command.sh`, `tests/integration/composition/{test_deploy_script_refusals,test_stand_copy_refusals,test_bundle_transport_refusals}.py`, `docs/program/DEPLOYMENT_RUNBOOK.md` (§11 only), `docs/program/W54-FIX-SHELL.md`

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**`

## Non-goals
- JUDGE-Y F4 (a contract reseal; registered), JUDGE-A F7 (rehearsal), F8 (registered).

## Deliverables
- JUDGE-A F1 (`deploy.sh` refuses when the copy or staging parent exists but is not searchable — no silent pass; refusal case), F3 (`resume` holds `import.lock`; `import` takes it before `require_record_admits_import`), F4 (every writer of `record.json` takes `copy.lock`), F6 (keep `record.prev.json` until a new dump completes; `restore-db` by an older stamp); fix the STAND-COPY report §4 discard sentence via a note in your own report (do not edit other lane reports).

## Required tests
- command: container-free tests now (`bash -n`, `shellcheck -x`, the refusal suites with `docker` stubbed, non-postgres pytest); DB/S3-backed cases are the integrator's window step — list exact commands.
- expected: exit 0; each fix has a test that fails without it.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
