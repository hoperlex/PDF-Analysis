# Task W53-JUDGE-Y-RECHECK — independent consistency verdict on repaired candidate

## Outcome

Independently decide whether Y's mutable queue cursor, provider-effect journal omissions, cross-Run `40P01` reclaim deadlock and ALR guard failures are corrected. Verify test isolation and identify any new consistency defect with a reproducible counterexample. Preserve the undecided global-pause public-journal scope.

## Depends on

- W53-JUDGE-Y
- W53-QA-RECHECK-01
- W53-ALR05-REPAIR-01
- W53-QUEUE-REPAIR-01
- W53-JOBS-REPAIR-03
- W53-QUEUE-TEST-REPAIR-02

## Frozen inputs

- Integrated pre-grant SHA `bb5508413935ccb2e4e784fb7dfddf913dbb708c`; integrator supplies exact post-grant base.
- API `1.0.0-draft.1`, OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain rev 9/29, state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration `0017_execution_queue`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- Original Y counterexamples in `docs/program/W53-JUDGE-Y.md`; confirmed PostgreSQL `40P01` log `/tmp/w53-judge-y/probe.log` SHA-256 `a9ec0aa9f1f5068b6549b30b7951709bc461a0be9c4ff257028698251613a074`. Repairs in queue/jobs/ALR reports. The integrator's fresh private 0017 combined QA/concurrency repeat at `c65d3a30c014aaa029b558ad04f72e282de37dd9` was **23/23**, `/tmp/w53-int-qa/combined.log` SHA-256 `fb788e63b37c86f64a2f090a4bcf10d801197fb07d84e8cf7ae7c96354ded360`.
- 2026-10-09 14:16:44 UTC worktree/Docker filesystem had 10,586,603,520 bytes free. Ports 56980/60580/60581 were unbound on a separate readback. Recheck before service use.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-JUDGE-Y-RECHECK.md` only.

## Forbidden hotspots

Every product/test/contract/migration/dependency/composition/global-style/release/backup/deployment path, other reports, refs/tags and the working stand.

## Non-goals

Source/test edits, contract reseal, arbitrary RunId for a global pause event, deciding owner policy, new MinIO image build, release notes or full gate.

## Deliverables

Private fresh 0017 DB review of queue pagination and two-connection periodic/forced reclaim; read back event counts and safe payloads, in both QA suite orders where useful. Inspect code/SQL for residual inversion or cursor loss beyond the focused tests. Exact PASS/REJECT per original Y finding and a clear disposition for global-pause public journal as an owner decision, not an inferred fix. Six-item AGENTS.md §5 handback and path audit.

## Required checks

Private `gate-w53judge-y2` lane: PostgreSQL 56980, old S3 API 60580, console 60581; unique database/bucket/volumes/credentials. Preflight ports and disk; use existing images only, expected under 1 GiB plus 2 GiB safety margin. Run `tests/integration/qa_w53`, `tests/integration/runs/test_w53_jobs_repair.py`, queue-focused W53 execution nodes and ALR-05; preserve logs/hashes under `/tmp/w53-judge-y-recheck/`. Verify frozen hashes and `git diff --check`; remove only own resources. Do not touch working stand or shared cache.

## Integration contract

Integrator audits and cherry-picks report, repeats any new confirmed defect under a precise grant. No release or publication authority.

## Failure/idempotency/security cases

Priority/state mutation after emitted cursor; equal-priority dispatch order; two simultaneous sweeps; multiple prepared effects and repeat settlement; pause claim; no secret in event payload; global pause has no fabricated Run identity.

## Rollback / feature flag

No behavior change.

## Handoff

Six AGENTS.md §5 items, clean branch and exact HEAD.
