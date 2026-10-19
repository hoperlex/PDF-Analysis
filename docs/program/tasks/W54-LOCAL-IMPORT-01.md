# Task W54-LOCAL-IMPORT-01 — rehearse the verified norms bundle import on an isolated local stack

task_id: W54-LOCAL-IMPORT-01

## Outcome

The verified W54 bundle (repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, bundle
digest `7792e307…5245`) is imported into an isolated local application stack under
a test-data waiver, an admin designates it current, and the served API answers
`searchNorms`, `getNormDocument`, `listNormParagraphs` and a ranged
`streamNormDocumentContent` from the real corpus. This rehearses `W55-PLAN.md` §A7
locally; the stand import stays an owner-window operation.

## Depends on

- `W54-BUNDLE-EXPORT-01` — completed verified bundle.

## Frozen inputs

- base commit: the `integration/night-1020` commit that adds this file;
- bundle: `/root/projects/PDF-Analysis/.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245`
  (manifest SHA-256 `cc0f5ee8…21cf`, `min_migration_head` `0018_norm_custody`);
- migration head: `0023_norm_citations`;
- rulings: `R-110` (test-data waiver), `R-135`, `R-139`.

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

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-LOCAL-IMPORT-01.md`
- `docs/program/tasks/W54-LOCAL-IMPORT-01.md`
- `src/auditmanager/norms/bundle/**`
- `tests/integration/norms/**`
- `tests/unit/norms/**`

## Lane resources

- foundation_instance: `auditmanager-w54-local-import`
- postgres_port: `57490`
- s3_api_port: `61090`
- s3_console_port: `61091`
- postgres_db: `auditmanager_w54_local_import`
- s3_bucket: `auditmanager-w54-local-import`

## Forbidden hotspots

`contracts/**`, migrations, composition root, dependency files, the promotion
database and its volume `auditmanager-promotion-data`, the bundle directory
(read-only), `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No stand import or `report` to production, no change of bundle bytes, no
embedding rebuild, no full gate. Code changes only if the import exposes a
defect, with a regression test.

## Deliverables

Report `docs/program/W54-LOCAL-IMPORT-01.md`: commands, exit codes, import
counts, measured time/disk/RAM, the API answers (status codes, counts, first
hits for 3 Russian queries), and the stack left running for the next norms
slices (ports above).

## Required tests

Preflight `date -u; df -B1 /; free -b; uptime` before import (floor: 8 GiB free
disk); the import's own verification; the API probes above. No full gate.

## Integration contract

The integrator merges the report (and any defect fix). The local stack stays up
as the shared norms development stand for this window unless disk falls below
4 GiB.

## Failure/idempotency/security cases

A repeated import of the same bundle must be idempotent or refuse loudly; the
waiver is test-data only and never reaches the stand.

## Rollback / feature flag

`make down` and remove only this lane's two volumes.
