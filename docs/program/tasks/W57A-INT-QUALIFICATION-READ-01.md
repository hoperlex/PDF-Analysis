# Task W57A-INT-QUALIFICATION-READ-01 — read stored snapshot/build facts

task_id: W57A-INT-QUALIFICATION-READ-01

## Outcome

A SELECT-only reader returns exact-key stored snapshot, source-PDF binding,
chunk-build and embedding-build counts for a later W57a qualification owner.
Missing completion rows stay explicit. The reader issues no verified verdict.

## Depends on

- `W57A-INT-SNAPSHOT-EVIDENCE-READ-01` — completed source SELECT reader;
- `W57A-INT-RETRIEVAL-WINDOW-READ-01` — completed embedding-window reader;
- `CFB-INT-DEV-PUBLISH-12` — completed dev integration at `8f113f6b`.

## Frozen inputs

- base commit: `8f113f6b8987f2fb702872435f61999e143bdc50`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- migration head `0022_findings_v2`; norm corpus `0012`, embedding `0013` and custody `0018` table shapes unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: snapshot/build completion metadata and stored rows exist, but no
  W57a reader currently exposes their counts together to a qualification
  owner under an exact reviewed content key.

### P-01 — schema rows and custody slot

- captured_at: 2026-10-16
- command: `rg -n 'CREATE TABLE (norm_chunk_build|norm_embedding_build|norm_embedding|norm_custody_binding)|source_document_ref text NOT NULL' db/migrations/versions/20260930_0012_norms_corpus.py db/migrations/versions/20261001_0013_norm_embeddings.py db/migrations/versions/20261012_0018_norm_custody.py`
- captured_output:
  ```text
  db/migrations/versions/20260930_0012_norms_corpus.py:88:            source_document_ref text NOT NULL,
  db/migrations/versions/20260930_0012_norms_corpus.py:183:        CREATE TABLE norm_chunk_build (
  db/migrations/versions/20261001_0013_norm_embeddings.py:93:        CREATE TABLE norm_embedding_build (
  db/migrations/versions/20261001_0013_norm_embeddings.py:121:        CREATE TABLE norm_embedding (
  db/migrations/versions/20261012_0018_norm_custody.py:267:        CREATE TABLE norm_custody_binding (
  ```
- interpretation: the reader may use these existing tables and the `norm_source`
  PDF slot without adding a migration; counts alone cannot prove byte-level
  source integrity, complete vectors or an approved retrieval set.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/qualification_reader.py`;
- `tests/integration/norms/retrieval/test_qualification_reader.py`;
- `docs/program/tasks/W57A-INT-QUALIFICATION-READ-01.md`;
- `docs/program/W57A-INT-QUALIFICATION-READ-01.md`.

## Forbidden hotspots

`contracts/**`, migrations, existing retrieval/custody modules, provider
lock, API/UI, composition root, root dependencies/locks, global styles,
corpus source, `CURRENT_STATE.md`, refs and deployment.

## Non-goals

No source-PDF readback, row-digest recomputation, reliable-paragraph coverage
proof, independent embedding digest comparison, map/target approval, verified
set row, custody publication, DB write, S3 access, runtime activation or beta.

## Deliverables

One SELECT-only DTO reader, refusal tests, this task and result report.

## Required tests

- focused fake-session reader tests, Python compilation, direct task
  governance, frozen SHA, exact paths and whitespace;
- no full `make gate` under R-135; no live DB or S3 access.

## Integration contract

The caller supplies a valid snapshot ID, the exact reviewed content key and
a reliability-aware `characters-v2` chunking profile. It holds one consistent
read transaction while combining this DTO with the independent corpus,
source-byte, row-digest, map, window and expected-artifact evidence. Equal
stored and declared counts are only inputs to that later proof; a missing
chunk or embedding completion row remains `None`, not a silent fallback.

## Failure/idempotency/security cases

Malformed caller IDs/key/profile refuse before SQL. Missing/wrong-key
snapshot, malformed scalar rows, impossible PDF-bound count and a partial
embedding completion row refuse. Drifted stored counts return as facts for
the qualification owner to reject; this reader never labels them complete.
Repeating one snapshot transaction has no side effect.

## Rollback / feature flag

Remove the additive reader before runtime wiring; no data rollback or flag.

## Handoff

- changed files and checks: accompanying report;
- contracts: none;
- next: qualification owner must prove row/vector bytes and independent
  expected digests before any verified-row or custody action.
