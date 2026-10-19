# W59-VERSION-UPLOAD-01 — upload a further version into an existing document set

Status: **phase A complete** on `agent/w59-version-upload-01` (base `641f2b9e` = `origin/dev`
`1af17a48` + the frozen task file). Phase B (contract, router, BFF, screen) waits for the
integrator to hand over the contract slot.

## Phase A — the next version in ingest and documents

**Result.** `IngestService.upload_next_version(project_uid, document_uid, content,
source_filename, idempotency_key)` admits a portal bundle as the next immutable version
of an existing document. It is `upload_bundle` with the document named — not a copy of it
— so the envelope (portal bundle only, ≤ 500 pages / 250 MiB), the custody order (stage,
verify, `verifying` breadcrumbs in one transaction, publish, then blobs `available` +
version + manifest + command outcome in one transaction), reconciliation's breadcrumbs
and the command record are the same code as `uploadDocument`'s.

What the next version does:

- **Next ordinal, pointer moves.** No `document` row is created; the version takes the
  document's next `version_ordinal` and `document.current_version_uid` moves to it in the
  publishing transaction. The project still counts one document; `listDocuments` names the
  new head, `listVersions` lists every version newest first.
- **Inherits nothing.** No title and no section are taken: the document keeps its title,
  `document.section` stays the legacy document-level fact written at the first upload, and
  the new version has no `document_version_classification` row (stage and confirmed
  section absent until an expert confirms them, `W59-SECTION-IDENTITY-DECISION-01`). The
  older version's row, manifest and classification are byte-for-byte unchanged.
- **Idempotency as `uploadDocument`.** Same command type; the fingerprint already names
  the document, so an exact retry (same key, document and bundle) replays the first
  version (`replayed=True`), and the same key spent on another document — or on
  `uploadDocument` — is `idempotency_key_reuse`.
- **Refusals.** An unknown project is `not_found` naming `Project`; an unknown document or a
  document of another project is `not_found` naming `Document`. Both are decided before the
  key is claimed or a byte is staged (the key stays free). Envelope refusals are
  `uploadDocument`'s (a bare PDF: `validation_failed` / `portal_bundle_required`), with no
  version, no command record and the pointer unchanged.
- **Concurrency.** `DocumentRepository.publish_version` now locks the document row
  (`SELECT … FOR NO KEY UPDATE`) before reading `max(version_ordinal) + 1`. Two uploads into
  one document queue on that row and get consecutive ordinals. Before this, both read the
  same ordinal and the second died on `uq_document_version_ordinal` as `internal_error`
  (reachable already through `upload_bundle(document_uid=…)`). `FOR NO KEY UPDATE` is the
  lock the closing `UPDATE document` takes anyway, taken earlier; it does not block other
  transactions' foreign-key checks against the document. The lock also makes the
  repository refuse a missing document as `not_found` instead of a foreign-key fault.

No migration: the schema already expresses a further version (`document_version.
version_ordinal` with `uq_document_version_ordinal`, the mutable `document.
current_version_uid`, classification in its own table).

**Changed files (phase A).**

- `src/auditmanager/documents/repository.py` — `_LOCK_DOCUMENT` and its use in
  `publish_version`.
- `src/auditmanager/ingest/service.py` — `upload_next_version` and the module note.
- `tests/integration/ingest/test_next_version.py` — 11 tests (new).
- `docs/program/W59-VERSION-UPLOAD-01.md` — this report.

**Checks (phase A),** lane `auditmanager-w59-version-upload` (postgres 57550, s3
61150/61151), `PY=…/w55b-main-candidate/.venv/bin/python`,
`PYTHONPATH=src $PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

- `tests/integration/ingest/test_next_version.py`: **11 passed**; the concurrency test
  5 × green in a row.
- Mutation probes (each restored with `git checkout`):
  - M1, `_LOCK_DOCUMENT` without `FOR NO KEY UPDATE`:
    `test_concurrent_next_versions_get_consecutive_ordinals` **fails** with
    `DomainError: An unclassified server fault` (the `uq_document_version_ordinal` collision).
  - M2, the `locked is None` refusal removed:
    `test_publishing_into_a_missing_document_is_refused_by_the_repository` **fails** with
    `ForeignKeyViolation … document_version_document_uid_fkey`.
  - The first draft of the concurrency test stayed green under M1: its two bundles shared the
    block-list and markdown blobs, and the shared blob row serialised the two publishing
    transactions by accident. The bundles now differ in every stored member (a stem per
    revision), which is also what real revisions look like.
- `tests/integration/ingest` + `tests/unit/ingest`: **650 passed** (83.8 s).
- Other callers of `publish_version`, read-only: `tests/integration/runs/test_w59_classification_command.py`
  + `tests/integration/composition/test_version_comparison_over_http.py`: **17 passed**.

## Proposed operation for phase B

`POST /projects/{project_uid}/documents/{document_uid}/versions`, `operationId:
uploadDocumentVersion`, tag `documents`, the same roles as `uploadDocument`:

- parameters: `Idempotency-Key` (required, as `uploadDocument`), `X-Correlation-Id`;
- request: `multipart/form-data` with the `file` part encoded `application/zip`, exactly as
  `uploadDocument`; the schema `UploadDocumentVersionRequest` is closed and holds **only**
  `file` — a further version takes no `display_title` and no `section`, and accepting and
  ignoring them would be a silent fallback (an undeclared part is the usual
  `additionalProperties` 422);
- `201 DocumentVersion` for a published version and for an exact replay;
- refusals: `uploadDocument`'s `401, 403, 404, 409, 422, 500, 503` (envelope `422`,
  `upload_capacity` `503` with `Retry-After`), with `404` also for an unknown document or a
  document of another project (`details.aggregate_type: Document`);
- the route goes through `UploadRoute` (strict multipart, part bounds, upload capacity) like
  `uploadDocument`.

Surface after phase B: **52 paths / 59 operations / 148 schemas** (one path, one
operation, one request schema).
