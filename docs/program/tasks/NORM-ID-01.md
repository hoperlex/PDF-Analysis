# Task NORM-ID-01 — public opaque identities for canonical norms

## Outcome

Every normative document and canonical paragraph loaded into a `NormsSnapshot` receives its
own globally unique opaque identity. Neither identity is derived from content, source names,
ordinals or database sequence values. Retrieval chunks remain an uncontracted rebuildable
projection and deliberately receive no public identity.

## Depends on

- `NORM-PERSIST-01` — completed in the working tree: durable snapshot/document/paragraph/chunk
  topology and idempotent loader

## Frozen inputs

- owner ruling of 2026-09-30: public identities are required for normative documents and
  canonical paragraphs; no public chunk identity
- domain contract `1.0.0-draft.1`, incoming candidate revision `7`
- API contract: 17 paths / 20 operations / 61 schemas; read only
- error catalog: 22 codes; no semantic change
- incoming migration head: unpublished working-tree revision `0012_norms_corpus`
- base release: `alpha-w47`; the current dirty worktree belongs to `NORM-LEDGER-01` and
  `NORM-PERSIST-01`

## Ownership

This task is the sole owner of the domain identifier contract reseal to candidate revision 8,
the shared identity types, and an amendment of the unpublished `0012_norms_corpus` revision.
The amendment is permitted because `0012` has not been committed, tagged, deployed or loaded
into a persistent database. The task owns no API, error-code, root dependency, composition,
MinIO or web slot.

## Allowed paths

- `docs/program/tasks/NORM-ID-01.md`
- `docs/program/NORM_CORPUS_PERSISTENCE.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/CURRENT_STATE.md`
- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/identifiers.schema.json`
- `contracts/domain/v1/README.md`
- `contracts/domain/v1/state-machines.json` — `candidate_revision` only
- `contracts/domain/v1/state-machines.schema.json` — candidate-revision `const` only
- `contracts/domain/v1/error-codes.json` — `candidate_revision` only
- `contracts/domain/v1/error-codes.schema.json` — candidate-revision `const` only
- `src/auditmanager/shared/identity/ids.py`
- `src/auditmanager/shared/identity/__init__.py`
- `src/auditmanager/norms/repository.py`
- `src/auditmanager/norms/README.md`
- `db/migrations/versions/20260930_0012_norms_corpus.py`
- `tests/contract/domain_p02/test_identifier_catalog.py`
- `tests/contract/test_cp00_candidate.py` — only if a derived revision/count guard requires it
- `tests/integration/db/test_norms_corpus_migration.py`
- `tests/integration/db/test_schema_shape.py`

## Forbidden hotspots

- API/analysis/comparison/event contracts and all routers or UI schemas
- error-code meanings, code set, state-machine semantics and lifecycle rows
- any migration other than the explicitly owned unpublished `0012_norms_corpus`
- root dependency/lock files, composition root and global styles
- storage/ingest/MinIO implementation and `.local/norms/corpus/**`

## Non-goals

- No `norm_chunk_id`, search API, UI route, pgvector column or embedding call.
- No identity derived from slug, source document reference, ordinal, checksum or content key.
- No custody upload or DB/object-store dual write.
- No new state machine or error code.

## Deliverables

- `norm_document_id = ndoc_<ULID>` and `norm_paragraph_id = npar_<ULID>` in the domain catalog,
  its closed schema, shared value types and persistence schema
- loader allocation of one fresh identity per newly created immutable entity
- database format/uniqueness checks and tests proving source anchors cannot substitute for IDs
- candidate revision 8 coherence across all six domain catalog/schema files
- architecture/backlog prose recording that retrieval chunks have no durable public identity

## Required tests

- `.venv/bin/pytest tests/contract/domain_p02/test_identifier_catalog.py -q`
- `.venv/bin/pytest tests/integration/db/test_norms_corpus_migration.py -q`
- `.venv/bin/pytest tests/integration/db/test_schema_shape.py -q`
- `.venv/bin/pytest tests/integration/norms -q`
- `make gate`
- `git diff --check`

Expected: all pass; the full gate prints literal `GATE OK`. The standalone
`tests/contract/test_cp00_candidate.py` is deliberately not a reseal gate: it certifies byte
identity of the historical CP-00 tree and explicitly declares `contracts/**` untouchable.
Running it against any later owner-authorized contract revision must go red. It is not weakened
or edited here; current domain schema/coherence tests and the project gate are the applicable
checks.

## Integration contract

- `NormDocumentId` and `NormParagraphId` are equality-only opaque values generated once.
- IDs remain stable for the immutable entity lifetime and are globally unique across snapshots.
- a corrected/replaced corpus creates a new snapshot and new child entities; it never derives or
  reuses IDs from the previous snapshot
- source references, slugs, paragraph ordinals and database PKs remain internal anchors only
- retrieval chunks expose canonical paragraph IDs or normative anchors when an API is later
  designed; a chunk row never becomes the cited normative authority

## Failure / idempotency / security cases

- malformed/wrong-prefix child IDs are rejected by both value type and database CHECK
- duplicate child IDs are rejected globally
- an exact repeated corpus load reuses the existing snapshot and every existing child identity
- failed first load rolls back all allocated identities together with their rows
- identities carry no source bytes or secrets and are safe to log for an authorized caller

## Rollback / feature flag

No runtime consumer is wired yet and `0012` is unpublished. Rollback is reverting this task and
re-running the migration lifecycle on disposable databases. Once any external consumer receives
a child identity, it must never be reused or rewritten; subsequent repair is forward-only.

## Handoff

- changed files: the six domain catalog/schema files plus domain README; shared identity
  types/exports; unpublished `0012_norms_corpus`; norms repository/README; identifier,
  migration and schema guards; corpus persistence/backlog/current-state docs
- commands/results: targeted identity + migration + schema + norms suites **122 passed**;
  `make gate` prints literal **`GATE OK`**; `git diff --check` is clean
- contracts: domain candidate revision 8 adds `norm_document_id`/`NormDocument` and
  `norm_paragraph_id`/`NormParagraph`; no API, state-machine meaning or error-code change
- known limits: the candidate is still unfrozen/unratified; no API returns these identities yet;
  historical `test_cp00_candidate.py` intentionally rejects all post-CP-00 contract bytes and
  is not weakened or presented as the current reseal gate
- integration notes: freeze/review candidate revision 8 before an external consumer; keep
  `0012` as the migration head; exact content-key replay must preserve all child IDs; never
  add a durable retrieval-chunk identity
- forbidden-hotspot proof: API/analysis/event contracts, root dependencies/locks, composition,
  web/global styles and storage/ingest/MinIO implementation are untouched by this task;
  migration ownership is limited to the explicitly unpublished `0012_norms_corpus`
