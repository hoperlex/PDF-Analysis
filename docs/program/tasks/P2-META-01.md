# Task P2-META-01 — ingest: immutable DocumentVersion, InputManifest and registered blobs

> **Status: specified; not dispatchable.** Planned for P02.

## Outcome

An accepted PDF becomes one immutable document version with an input manifest and a
checksum-verified private S3 object registered as blob metadata, and every out-of-envelope
input fails explicitly with nothing published.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P2-DOM-01` — the P02 migration head and domain primitives
  - `P2-BHV-01` — the AR corpus and negative fixtures

## Frozen inputs

- domain contract: the import and blob machines and the project, document, version, blob
  and command identifiers
- migration head: the P02 head, read only
- storage: the P01 BlobStore port implementing temporary, verify and publish, read only
- base commit: the accepted `P2-DOM-01` integration commit

## Allowed paths

- `src/auditmanager/documents/**`, `src/auditmanager/ingest/**`
- `src/auditmanager/storage/**` — blob metadata repository only, as the post-P01 owner
- `tests/integration/ingest/**`
- `docs/navigation/incidents/p2-meta-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P2-META-01.md`
- `docs/navigation/entries/p2-meta-01.json`

## Forbidden hotspots

- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `tests/integration/storage/**` and `tests/integration/db/**`, owned by P01
- `src/auditmanager/{runs,exports,analysis,findings,decisions,api}/**`, `contracts/**`, `fixtures/**`

## Non-goals

- No OCR, ZIP, companion, multi-file or folder upload, and no second discipline.
- No presigned browser upload, version deletion or cross-version diff.
- No canonical text extraction: the admission probe answers yes/no questions only.

## Deliverables

- create and list project, plus a direct single-PDF upload command carrying an idempotency
  key
- an admission probe rejecting, before any publication, non-PDF magic bytes, an encrypted
  PDF, an oversize file, an over-page-count file and any page without extractable embedded
  text, each with `validation_failed` and a constraint detail
- the publication order temporary upload, checksum verification, publish, blob metadata
  row, then document version and input manifest rows, in one transaction with the command
  record
- immutability: a published version's manifest and blob set refuse any later write with
  `state_transition_not_allowed`
- a reconciliation entrypoint reporting a published object with no committed version row,
  and failing a version whose blob is missing with `storage_integrity_error`

## Required tests

- Command: `make foundation`
  Expected: exit `0` on this lane's instance.
- Command: `.venv/bin/pytest tests/integration/ingest`
  Expected: exit `0` against PostgreSQL and MinIO. The suite asserts that the baseline
  fixture produces one version and one available blob whose SHA-256 matches; that each
  negative fixture returns `validation_failed` with no project, version, manifest, blob row
  or canonical object created; that a repeat under the same key and payload returns the
  same version and creates nothing; that the same key with a different payload returns
  `idempotency_key_reuse`; that mutating a published manifest returns
  `state_transition_not_allowed`; and that a forced checksum mismatch leaves no available
  blob and no version.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Consumers receive the version identity plus a manifest of role, blob identity, checksum,
size and media type. Bucket and object key never appear in a return value, log or error.
Analysis reads source bytes only through the BlobStore port by blob identity.

## Failure/idempotency/security cases

- `GJ-01-EO-06` opaque identity, `GJ-01-EO-07` duplicate reasoning over content digests,
  and `GJ-01-FC-01`, `GJ-01-FC-02` and `GJ-01-FC-03` for empty, forbidden-extension and
  traversal-shaped inputs rejected with nothing stored.
- A crash between publish and commit leaves an orphan object rather than a half-version,
  and reconciliation reports it.

## Rollback / feature flag

Not applicable: the slice has no prior behavior to flag. Revert before any real document is
uploaded; test objects are removed only by scoped cleanup.

## Estimate

Effort P50 2.5 person-days, P80 4.5 person-days. Basis: one ingest use case with an admission probe and a reconciliation entrypoint. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the public application ports and the envelope rules with their error codes
- the reconciliation entrypoint
- the object-key privacy proof
