# Task NORM-VECTOR-01 — pgvector image and durable embedding projection

## Outcome

Both the local foundation and alpha deployment build one repository-owned PostgreSQL 17.11
derivative containing pgvector 0.8.6 from checksum-pinned official source. Migration
`0013_norm_embeddings` installs that exact extension and stores complete, idempotent
`bge-m3-dense-v1` embedding builds over rebuildable norm chunks without making vectors or
chunk rows canonical evidence.

## Depends on

- `NORM-INT-01` — completed and published on `origin/main` at `9b69dba`
- `NORM-EMBED-EVAL-01` — completed: exact BGE-M3 profile and tokenizer long tail measured
- `NORM-PERSIST-01` — completed: canonical corpus and replace-only chunk projection at head 0012

## Frozen inputs

- base commit: `9b69dba`
- PostgreSQL base: `postgres:17.11-trixie` at index digest
  `sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675`
- pgvector: official `v0.8.6`, commit `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c`,
  source archive SHA-256 `d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299`
- embedding profile: `bge-m3-dense-v1` exactly as frozen by `NORM-EMBED-EVAL-01`
- incoming migration head: `0012_norms_corpus`
- owner rulings 2026-10-01: repository-owned pgvector derivative; corpus internal-use only;
  full retention of every corpus snapshot, source PDF, crop and repair ledger

## Ownership

This task is the sole owner of migration revision `0013_norm_embeddings`, the PostgreSQL image
pin/build slot, the local/deployment PostgreSQL composition entries and the norms embedding
repository. It is an explicit successor pin task under `P1-INT-00`'s rule that a later image
change has one new owner.

## Allowed paths

- `docs/program/tasks/NORM-VECTOR-01.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/NORM_EMBEDDING_BAKEOFF.md`
- `docs/program/NORM_CORPUS_PERSISTENCE.md`
- `docs/program/NORM_CORPUS_CUSTODY.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/FOUNDATION_LOCK.json`
- `docs/manual-tests/PC-01_prototype.md`
- `Makefile` — PostgreSQL base/derivative image pin prose only if required
- `infra/postgres/**`
- `infra/local/docker-compose.yml`
- `infra/local/README.md`
- `infra/deploy/compose.server.yml`
- `infra/deploy/README.md`
- `infra/deploy/env/alpha.env.example`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `db/migrations/versions/20261001_0013_norm_embeddings.py`
- `src/auditmanager/norms/embedding_repository.py`
- `src/auditmanager/norms/README.md`
- exact migration/schema/composition/norms tests and derived table/head guards

## Forbidden hotspots

- root Python/frontend dependency and lock files
- API/analysis/comparison/event/domain contracts and every router/UI component
- every pre-existing migration
- storage/ingest/MinIO implementation and secrets
- global styles and source corpus `.local/norms/corpus/**`
- release tags and remote refs

## Non-goals

- No production BGE model download or root runtime dependency.
- No model inference, background job, search API, UI, hybrid retrieval or reranker.
- No claim that the 24-query bake-off is release acceptance.
- No MinIO custody implementation or credentialed 121-page repair run.
- No global retention/TTL/legal-hold ruling beyond the normative-corpus artifacts named above.

## Deliverables

- a multi-stage PostgreSQL derivative Dockerfile with exact base/source pins and license copy
- local and alpha composition using that derivative without a floating third-party image
- migration installing pgvector 0.8.6 and creating immutable profile, complete build and
  replace-only `vector(1024)` window rows with an inner-product HNSW index
- a transaction-local repository that validates dimensions, finite float32 values,
  normalization, token/span bounds and complete-build digests before persistence
- idempotent replay and loud conflicting-rebuild behavior
- tests against real PostgreSQL proving extension version, vector distance ordering, schema,
  rebuild and downgrade refusal with retained data

## Required tests

- build the repository-owned PostgreSQL image from a clean Docker context
- `make foundation`
- `.venv/bin/pytest tests/integration/db tests/integration/norms -q` through the lane env
- composition guards covering exact base/source pins and both compose consumers
- `make gate` with literal `GATE OK`
- `git diff --check`

## Integration contract

- pgvector is installed by migration, not an image init script; image presence alone creates no
  database object.
- `bge-m3-dense-v1` is immutable reference data. Any model/tokenizer/pooling/dimension/distance
  change uses another profile key and a full build.
- An embedding window is a private rebuildable row tied to one chunk and canonical source span;
  search consumers cite snapshot/document/paragraph identities, never its private key.
- A build becomes visible only when all rows and its completion record commit together.
- The caller owns transaction commit/rollback; the repository makes no model or object-store call.

## Failure / idempotency / security cases

- wrong source archive checksum fails the image build before compilation
- missing or wrong extension version fails migration/test; no plain-Postgres fallback
- non-finite, wrong-dimension, non-normalized vector or invalid token/span metadata is refused
- exact replay returns the existing complete build; the same build key with another digest
  conflicts and writes nothing
- downgrade refuses while any embedding build exists; no retained projection is silently dropped
- no credential, corpus text or vector is logged

## Rollback / feature flag

Before any embedding build exists, downgrade 0013 and return composition to the prior image.
After a build exists, downgrade is deliberately refused; use an explicit export/forward repair.
No runtime feature flag is needed because no serving consumer is wired in this task.

## Handoff

- status: complete and published to `origin/main` on 2026-10-01 without a release tag; not deployed
- changed files: repository-owned PostgreSQL Dockerfile; local/alpha PostgreSQL composition and
  operator docs/env comments; migration 0013; norms embedding repository/README; foundation lock;
  owner-decision/persistence/custody/current-state/task records; exact migration, composition,
  schema, journey and live-prose guards
- commands/results:
  - repository-owned Docker build completed from the exact PostgreSQL base and verified pgvector
    control version 0.8.6 plus the copied license
  - `make foundation` passed: existing named volume preserved, 0012 upgraded to 0013, all 35
    foundation tests passed
  - first `make gate` exposed one stale exact table-set guard; after that guard was updated, the
    final `make gate` passed with literal `GATE OK`: backend 2632 passed / 5 skipped / 4 warnings /
    169 subtests, foundation 35, frontend 1162 in 82 files, plus lint and typecheck
  - JSON parse, Python compile checks and `git diff --check` passed
- contracts: API/domain/error catalog unchanged; migration head is `0013_norm_embeddings`;
  foundation image contract now treats the exact PostgreSQL pin as the base of the local
  derivative and freezes pgvector 0.8.6 source commit/archive digest
- known limits: no production BGE runtime, embedding worker, search API/UI, hybrid retrieval or
  reranker; the previous cold-cache host-space measurement predates the added PostgreSQL compile
  stage and remains a lower bound pending a fresh isolated-builder measurement
- integration notes: alpha deploy rebuilds PostgreSQL from the repository Dockerfile while
  preserving `${ALPHA_INSTANCE}-postgres-data`; migration then installs `vector` and creates the
  empty projection schema. No new alpha env name is valid or required.
- forbidden-hotspot proof: `contracts/**`, all pre-0013 migrations, root dependency/lock files,
  API routers, UI sources, global styles, storage/MinIO implementation, corpus source bytes,
  release tags and remote refs are unchanged
