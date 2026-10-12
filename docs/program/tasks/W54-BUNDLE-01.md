# Task W54-BUNDLE-01 — The promotion bundle is exported, transported and imported all-or-nothing with its ids, and report reconciles the stand against the manifest

## Outcome
The promotion bundle is exported, transported and imported all-or-nothing with its ids, and report reconciles the stand against the manifest.

## Depends on
- `W54-FREEZE-01` and the Stage B merges on `integration/w54`

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the EMBED merge on `integration/w54`

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
- Exactly the `W54-BUNDLE-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage C, plus `docs/program/W54-BUNDLE-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**`

## Non-goals
- Stand access; the paid repair run; the full embedding build.

## Deliverables
- Per plan §3.5 and §4 Stage C, with `W54-FREEZE-01` amendment 2 and the contracts fixed by TRANSPORT and STAND-COPY: CLI `python -m auditmanager.norms.bundle import|report <dir> --copy-record <path>` and `requeue <dir>`; bundle digest = SHA-256 of the ASCII-path `SHA256SUMS`; the importer accepts a full attested `import` copy record or an unexpired `test_data_waiver` with a matching fingerprint, and refuses any waiver once `real_data_marker` is set (STAND-COPY report §3.8 proposal); §3.5's order on a disposable stand; replay a no-op; conflicts refused; an unconfirmed admission keeps the bundle; `report` matches and a tampered row fails it; an import alone leaves the fingerprint unchanged (add any written table to the fingerprint exclusions as STAND-COPY notes); refusals without a record, with a stale, unattested or expired one, with a drifted fingerprint, an absent build or a `rejected` manifest Blob; decide and implement the delete step given the read-only bundle mount (STAND-COPY report §4's `discard <KEY>` proposal or an alternative), granting yourself only `receive-bundle.sh`/`lib/forced-command.sh` lines if needed and saying so.

## Required tests
- command: container-free tests now; DB/S3-backed import and report cases on PostgreSQL `57170`, S3 `60770/60771` are heavy steps for the integrator's window — list exact commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window.
