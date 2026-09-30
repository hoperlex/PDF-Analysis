# Task NORM-CUSTODY-01 — immutable source and crop custody contract

## Outcome

The MinIO branch receives an implementation-ready custody model: each source PDF and each crop
is an independent immutable `Blob` with its own opaque `blob_id`; normative source/crop bindings
become visible only through a transactional intent plus idempotent reconciliation, never through
a direct PostgreSQL + object-store dual write.

## Depends on

- `NORM-PERSIST-01` — completed in the working tree: DB corpus loading has no object-store side
  effect and therefore provides a clean reconciliation boundary

## Frozen inputs

- owner ruling of 2026-09-30: source PDF and every crop are independent blobs
- domain `Blob` identity/state semantics and ADR-0007 outbox prohibition
- existing MinIO/storage implementation is owned by the parallel branch and is read only here
- API contract: read only; no new custody endpoint in this task

## Ownership

This task owns only the written custody/reconciliation design and handoff. The parallel MinIO
branch owns code, migration, object layout and credentials.

## Allowed paths

- `docs/program/tasks/NORM-CUSTODY-01.md`
- `docs/program/NORM_CORPUS_CUSTODY.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `src/auditmanager/storage/**`, `src/auditmanager/ingest/**`, MinIO configuration and secrets
- migrations, contracts, API/router/UI, root dependencies and composition root
- `.local/norms/corpus/**`

## Non-goals

- No object upload, deletion, credential test or bucket mutation.
- No choice of object-key layout as identity.
- No claim that the 121-page re-recognition ledger exists before credentials/run evidence exist.
- No retention/deletion policy; `NORM-Q06` remains separate.

## Deliverables

- aggregate/binding topology for source PDFs, crops, norm documents/pages and repair attempts
- transactional outbox/reconciliation sequence and idempotency keys
- publication invariant, checksum/media metadata, retry and orphan handling
- exact integration handoff for the MinIO owner

## Required tests

- documentation guard/read-through only in this task
- `git diff --check`

Expected: no executable/storage file changes.

## Integration contract

- one byte object equals one immutable Blob entity with one `blob_id`; source and crop IDs differ
- object key, file name, checksum, document slug, page label and block reference are attributes
  or lookup anchors, never identity
- DB state publishes a binding only after object-store confirmation and checksum verification
- retries converge on the same intent/blob; discrepancies become explicit reconciliation faults
- normative loader remains DB-only and can run independently of MinIO availability

## Failure / idempotency / security cases

- staged object lost: use the existing retryable `staged_upload_lost` semantics
- same intent and same bytes: return/reconcile the existing blob
- same intent and different bytes: conflict; create/publish nothing silently
- DB commit succeeds and object write fails: pending intent remains retryable
- object write succeeds and confirmation fails: reconciler confirms or quarantines; never guesses
- object keys and credentials never enter domain identities or caller-safe error details

## Rollback / feature flag

Design-only in this task. The implementing branch must specify its own forward-repair and
rollback policy before creating a migration or custody binding.

## Handoff

- changed files: `NORM_CORPUS_CUSTODY.md`, custody task, decision backlog and current-state
  summary; no executable storage file
- commands/results: documentation read-through plus `git diff --check`; complete
  `make gate` prints literal **`GATE OK`**
- contracts: implementation handoff requires an independent `blob_id` for every PDF and crop,
  transactional intent/outbox, read-back checksum verification and idempotent reconciliation;
  no API/domain contract was changed here
- known limits: no MinIO migration/code/upload, credentials, 121-page provider run or resulting
  repair ledger is claimed; retry ceiling and old-snapshot/Blob retention need owner decisions
- integration notes: the MinIO owner must claim its migration and storage/composition slots,
  concrete binding schema, dispatcher and reconciler; the norms loader remains DB-only
- forbidden-hotspot proof: `src/auditmanager/storage/**`, ingest, MinIO configuration/secrets,
  migrations, root dependencies, API/UI and the source corpus are untouched by this task
