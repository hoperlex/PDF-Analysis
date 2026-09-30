# Task NORM-PERSIST-01 — durable canonical norms projection

## Outcome

One deterministic normative-corpus content key is loaded atomically and idempotently as one
durable `NormsSnapshot` with an opaque `ns_<ULID>` identity. Canonical paragraphs are stored
separately from rebuildable retrieval chunks, and a repeated load of identical effective text
returns the existing snapshot without duplicating any row.

## Depends on

- `W33-CORPUS` — completed: deterministic segmentation, chunking and content-derived key
- `W39-CORPUS` — completed: immutable repair ledger and repaired-content key
- `NORM-LEDGER-01` — completed: a validated repair ledger reaches the effective projection

## Frozen inputs

- domain contracts: `contracts/domain/v1/**` at `acc6463`, read only
- API contract: 17 paths / 20 operations / 61 schemas at `acc6463`, read only
- existing identifier `norms_snapshot_id = ns_<ULID>`; no new contract identity is introduced
- incoming migration head: `0011_document_section`
- W33 segmentation and W39 repair-ledger semantics

## Ownership

This task is the sole owner of migration revision `0012_norms_corpus` and the norms persistence
adapter until its handoff is accepted. It does not own a contract, root dependency, composition,
MinIO or web slot.

## Allowed paths

- `docs/program/tasks/NORM-PERSIST-01.md`
- `docs/program/NORM_CORPUS_PERSISTENCE.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `db/migrations/versions/20260930_0012_norms_corpus.py`
- `src/auditmanager/norms/**`
- `tests/integration/norms/**`
- `tests/integration/db/test_norms_corpus_migration.py`
- `tests/integration/db/test_schema_shape.py`

- `docs/program/CURRENT_STATE.md` — live migration-head claim only
- `docs/manual-tests/PC-01_prototype.md` — executable head observation only
- `tests/contract/api_v1/test_doc_prose_facts.py` — derived expected-head guard only
- `tests/integration/db/test_migration_lifecycle.py` — exact declared-relations guard only
- `tests/integration/p02_journey/journey.py` — exhaustive table-count list only
- `src/auditmanager/runs/scope.py` — remove now-instantiated `norms_snapshot` only
## Forbidden hotspots

- `contracts/**` and every API schema/router
- every pre-existing migration revision
- root dependency and lock files
- bootstrap/composition root and global styles
- `src/auditmanager/storage/**`, `src/auditmanager/ingest/**` and MinIO configuration
- `.local/norms/corpus/**`; the source corpus is read only

## Non-goals

- No source-PDF or crop upload and no DB/S3 dual write.
- No pgvector extension, vector column, embedding call, search API or UI.
- No real provider re-recognition call.
- No public identity for norm documents, paragraphs or chunks before their API contract exists.
- No claim that blocked manual acceptance evidence has been collected.

## Deliverables

- a written model distinguishing opaque snapshot identity from deterministic content key
- migration `0012_norms_corpus` with snapshot, document, canonical paragraph and rebuildable
  chunk tables and a foreign key from `audit_run.norms_snapshot_id`
- a transaction-scoped repository and corpus loader with exact-repeat idempotency
- refusal of stale repair ledgers, inconsistent metadata and conflicting stored projections
- integration tests against real PostgreSQL plus deterministic small-corpus tests
- an explicit decision backlog for the later embedding/API/custody slots

## Required tests

- `.venv/bin/pytest tests/integration/norms -q`
- `.venv/bin/pytest tests/integration/db/test_norms_corpus_migration.py -q`
- `.venv/bin/pytest tests/integration/db/test_schema_shape.py -q`
- `make gate`
- `git diff --check`

Expected: all commands pass and `make gate` prints literal `GATE OK`.

## Integration contract

- `norms_snapshot.norms_snapshot_id` is the frozen opaque domain identity.
- `norms_snapshot.content_key` is a unique equality/verification value derived from effective
  corpus text; it is never accepted where `norms_snapshot_id` is required.
- documents and canonical paragraphs are immutable members of a snapshot.
- chunks name a versioned chunking profile and may be deleted/rebuilt from canonical paragraphs;
  they are not canonical evidence.
- the loader accepts an open SQLAlchemy `Session`; its caller owns commit/rollback.
- the loader performs no external side effect, so one DB transaction is sufficient.

## Failure / idempotency / security cases

- same content key: return the stored opaque identity and counts, write nothing
- concurrent same-key inserts: the unique key chooses one snapshot; the loser reads and verifies it
- same key with inconsistent digest/counts: loud conflict, never silent reuse
- any source/ledger mismatch: fail before the first durable row is committed
- any document failure: caller rollback removes the snapshot and all child rows
- no filesystem path, provider credential, object key or source bytes are stored as identity

## Rollback / feature flag

No runtime behavior is wired to this projection in this task. Before consumers exist, downgrade
`0012` on a disposable database. Once an audit run references a snapshot, rollback is restore or
forward repair; deleting cited normative evidence is not an acceptable runtime rollback.

## Handoff

- changed files: migration `20260930_0012_norms_corpus.py`; norms `README.md`, `chunking.py`, `corpus_source.py`, `loader.py`, `model.py`, `repository.py`, `segmentation.py`, `snapshot.py`; programme model/backlog/task/state/manual-test docs; exact migration/schema/journey/run-scope guards; `test_norms_corpus_migration.py`. `NORM-LEDGER-01` and its repair-projection test remain the completed predecessor.
- commands/results: norms `73 passed`; new migration/loader suite `5 passed`; schema-shape `7 passed`; real corpus read-only projection `674 / 348777 / 55702`; loader CLI help exits 0.
- full gate: literal `GATE OK` — backend `2620 passed, 5 skipped, 4 warnings, 169 subtests passed`; foundation `35 passed`; frontend lint/typecheck and `1162 tests in 82 files` passed.
- new/changed contracts: none; API remains 17 paths / 20 operations / 61 schemas, error catalog 22. Migration head changes from `0011_document_section` to `0012_norms_corpus`.
- known limits: the real corpus was validated read-only but not loaded into a persistent working database; no MinIO custody bindings, real repair ledger, pgvector/embedding projection, search API or UI are included; child row keys remain private until the owner answers `NORM-Q01`/`NORM-Q07`.
- integration notes: run `make migrate`, then `PYTHONPATH=src .venv/bin/python -m auditmanager.norms.loader --corpus <root> [--ledger <repairs.json>]`; exact repeats return the existing `ns_<ULID>` and counts. Existing run creation still writes `norms_snapshot_id = NULL`; later run-admission work must pin the opaque ID, never `content_key`.
- forbidden-hotspot proof: final status contains only the paths owned by `NORM-LEDGER-01` and `NORM-PERSIST-01`; `contracts/**`, pre-existing migrations, root dependency/lock files, bootstrap/composition, global styles, web, storage/ingest/MinIO code and `.local/norms/corpus/**` are untouched.
