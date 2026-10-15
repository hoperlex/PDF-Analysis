# Task W57A-INT-RETRIEVAL-WINDOW-READ-01 — canonical embedding windows

task_id: W57A-INT-RETRIEVAL-WINDOW-READ-01

## Outcome

A SELECT-only reader returns bounded, complete float32 ranking windows for
caller-selected mapped documents from one exact snapshot and embedding build.
It checks the full stored build's ordered metadata against its completion
digest/counts and verifies every returned vector's content digest.

## Depends on

- `W57A-INT-RETRIEVAL-RANK-PREP-01` — completed `RetrievalWindow` and 50,000-window cap.
- `W57A-INT-SNAPSHOT-EVIDENCE-READ-01` — completed mapped-document evidence reader at `ecf5f56f`.
- `W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01` — completed source projection at `a311a2f0`.

## Frozen inputs

- base commit: `8dac96f7c36fad3e3855ab6abeb180a2a503fd9a`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- migration head `0022_findings_v2`; embedding tables are from `0013_norm_embeddings`; `0019` and `0020` do not alter them.
- `norm-embedding-set/2` digest, `bge-m3-dense-v1`, `characters-v2:1200` format, float32 vector-byte SHA and `RetrievalWindow` type on the base commit.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: a completed embedding build records its chunk/window counts and set digest; W57a ranking accepts pure float32 windows, but no SELECT-only full-window reader exists.

### P-01 — exact base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  8dac96f7c36fad3e3855ab6abeb180a2a503fd9a
  ```
- interpretation: the separate reader task starts from this integrated development candidate.

### P-02 — build schema

- captured_at: 2026-10-15
- command: `rg -n 'CREATE TABLE norm_embedding_build|CREATE TABLE norm_embedding|embedding_set_sha256|window_count' db/migrations/versions/20261001_0013_norm_embeddings.py`
- captured_output:
  ```text
  36:        CREATE TABLE norm_embedding_profile (
  93:        CREATE TABLE norm_embedding_build (
  98:            window_count integer NOT NULL,
  99:            embedding_set_sha256 text NOT NULL,
  111:                CHECK (chunk_count >= 0 AND window_count >= chunk_count),
  113:                CHECK (embedding_set_sha256 ~ '^[0-9a-f]{64}$'),
  121:        CREATE TABLE norm_embedding (
  ```
- interpretation: the completion row provides independent stored totals and a digest over ordered window metadata; `0019` and `0020` were inspected and have no embedding table changes. This schema does not itself prove owner map approval or legal corpus qualification.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/window_reader.py`
- `tests/integration/norms/retrieval/test_window_reader.py`
- `docs/program/tasks/W57A-INT-RETRIEVAL-WINDOW-READ-01.md`
- `docs/program/W57A-INT-RETRIEVAL-WINDOW-READ-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing retrieval modules, norms repository,
provider lock, public API, composition root, root dependencies, global styles,
corpus source, `CURRENT_STATE.md`, runner, stand, tags and Git refs.

## Non-goals

No map authoring/review, legal edition choice, independent embedding-build
qualification, tokenizer replay, HNSW query, citation decision, set row,
custody, runtime wiring, DB/S3 publication or beta acceptance.

## Deliverables

One SELECT-only window reader, focused fake-session tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_window_reader.py` — pass;
- Python compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The caller supplies a snapshot ID, reviewed content key, exact build identity,
independent expected `embedding_set_sha256`, and the reviewed map's mapped
`ndoc_` IDs, all inside one consistent read transaction. The reader requires
matching `norm_chunk_build` and `norm_embedding_build` rows, checks that
canonical/stored/build chunk counts coincide, recomputes the full ordered
`norm-embedding-set/2` metadata digest and its window/chunk counts, then reads
all mapped vectors as pgvector text, repacks to float32 and verifies their
SHA-256. It returns up to 50,000 `RetrievalWindow` values for pure ranking;
over a million total build windows refuse as a resource bound. No approximate
index or mutable process state participates.

## Failure/idempotency/security cases

Missing build, changed content key, unexpected build digest, count/digest
drift, missing/duplicate/sparse windows, foreign mapped rows, vector SHA or
unit-norm failure, and capacity overflow refuse. Identical stored rows give
identical outputs. The caller's consistent transaction is necessary; a
read-committed stream across concurrent transactions is not accepted as proof.
No corpus content or credentials enter Git.

## Rollback / feature flag

Remove the additive reader before runtime wiring; no data rollback or flag.

## Handoff

- changed files: four exact allowed paths.
- commands/results: focused suite and checks in result report.
- known limits: stored digest/totality checks are not owner qualification.
- integration notes: use only after map and embedding-build review.
