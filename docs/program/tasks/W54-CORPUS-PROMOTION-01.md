# Task W54-CORPUS-PROMOTION-01 — load and restore-verify the base corpus

task_id: W54-CORPUS-PROMOTION-01

## Outcome

The pinned normative source is loaded into the isolated local promotion
PostgreSQL, then dumped and restore-verified. The result records its opaque
snapshot ID, content key, counts and verified dump digest.

## Depends on

- `W54-CORPUS-OPERATE-01` — complete source SHA256SUMS verification.

## Frozen inputs

- base commit: `a7046b7c59a164446e1c3bea0bcc128e9e7a6d65`
- source manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- verified SHA256SUMS SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- runtime `uv.lock` SHA-256: `461631e7a31bb27aa8058492ab5def78890be1a3c6244da2ad0dfe38932468c4`;
- frozen W54 contracts and migration head `0022_findings_v2` remain unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: source bytes are verified; local promotion env and matching runtime
  are absent; disk and RAM must be measured again for each heavy step.
- source_record: `W54-CORPUS-OPERATE-01.md`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-CORPUS-PROMOTION-01.md`
- `docs/program/W54-CORPUS-PROMOTION-01.md`
- `docs/program/CURRENT_STATE.md`
- `.local/promotion/**`
- `.local/norms/promotion-dumps/**`
- `.local/uv-cache/**`
- `.venv/**`

## Lane resources

- foundation_instance: `auditmanager-promotion`
- postgres_port: `57190`
- s3_api_port: not_applicable
- s3_console_port: not_applicable
- postgres_db: `auditmanager_promotion`
- s3_bucket: not_applicable

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, source corpus/sums bytes, repair journal, embedding/bundle
artifacts, production stand, credentials in Git, tags and `origin/main`.

## Non-goals

No paid repair, embedding build, S3/production import, current snapshot
designation or beta acceptance.

## Deliverables

An ignored mode-0600 promotion env, lock-matched local Python runtime, base
snapshot metrics, one dump with checksum/fingerprint and `.verified` marker,
and a report. Stop the promotion DB after verification.

## Required tests

- Verify the source sums digest, runtime lock match, image pin and port claim.
- Before stack/load and each dump/restore: record `date -u`, `df -B1 /`,
  `free -b`, load average; require the W54 increment plus 3 GiB disk and
  6 GiB available RAM excluding swap.
- `scripts/promotion/stack.sh up`, `migrate`, loader with absolute corpus,
  `dump.sh`, `verify-dump.sh`, `stack.sh stop`; retain exact outputs.
- Direct task governance and `git diff --check` on report changes.

## Integration contract

Only a restore-verified base dump may feed the W54 durable-repair sample.
The next task receives exact `ns_`, content key, sums SHA and dump SHA, and
must remeasure floors before its own steps. User authorized operation when
the actual resource window exists on 2026-10-15.

## Failure/idempotency/security cases

If env/runtime cannot be prepared offline, any floor fails, the loader
refuses, or dump verification fails: stop the project-specific stack and
report the exact gate. Never print or commit credentials. Rerun an idempotent
loader only after checking whether a snapshot was already committed.

## Rollback / feature flag

The promotion DB is isolated; retain its volume and latest verified dump for
reconciliation. Never delete the volume to conceal a partial run. No runtime
feature flag changes in this task.

## Handoff

- changed files, checks, contracts, limits and next operation: report locally.
