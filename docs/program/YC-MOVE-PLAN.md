# YC-MOVE-PLAN — moving the database, the object storage and the encoder to Yandex Cloud

Status: **planned, not started.** Written 2026-11-10 by the lane `YC-MOVE-PLAN`. Nothing is moved, ordered or measured by this document.

- Owner's decisions: `R-153ab` («запланировать полный перенос на Яндекс. Пока выбрать вариант ночное окно, пометить как временное решение на локальном хранилище») and `R-153af` («Пока не трогаем»: the database is not moved now). The measurement lane for Yandex was dropped (`R-153an`: «Никакие, сразу строим»).
- Why it exists: the move is the first end condition of the temporary decision 2 of `ADR-0029` (the encoder runs only at night on our own server). It also reopens `ADR-0021`, where a managed database was «Not asked»; that ADR carries a dated addendum for it.
- What this document is not: a design of the provider's configuration, a price estimate, or a claim about what the provider offers. Where a fact about the provider is needed it is written as a **check** with a command and a pass condition, not as a fact.

## 1. What a move would change

| Piece | Today | After the move |
| --- | --- | --- |
| PostgreSQL | the `postgres` service of `infra/deploy/compose.server.yml`, a repository-owned image with pgvector 0.8.6 (`infra/postgres/Dockerfile`) | a managed PostgreSQL in Yandex Cloud, reached by one `DATABASE_URL` |
| Object storage | the `s3` service (MinIO) of the same compose file | Yandex Object Storage, through the S3 settings the code already reads |
| Encoder | an offline container in a night window on the production host (`ADR-0029` decision 8) | a separate machine; the night window and its three texts go |
| Everything else | one host, manual copies (`ADR-0021`) | unchanged until a separate decision |

The owner chose a **full** move. The three pieces can still be taken in separate steps (section 4); the end condition of `ADR-0029` is met only when the database, the storage and a separate encoder are all in place.

## 2. What the tree says today

These are read from the tree at `47c90e1ec`.

- **One setting for the database, five for the storage.** The database is `DATABASE_URL`. `S3StorageSettings` (`src/auditmanager/storage/settings.py:35`) holds `endpoint_url`, `region`, `access_key_id`, `secret_access_key` and `bucket`; the client signs with `s3v4` and path addressing (`src/auditmanager/storage/s3.py:915-916`). `docs/program/ALPHA_ROADMAP.md` section 7 already records that the storage switch is configuration, and the measurements it lists (TLS under a 25 MiB upload and a Range read, latency, egress cost, the cluster's connection limit, a restore drill from a managed dump).
- **The vector extension is pinned exactly.** Migration `0013` runs `CREATE EXTENSION vector WITH VERSION '0.8.6'` (`db/migrations/versions/20261001_0013_norm_embeddings.py:23`, `:32`), and `ADR-0020` records «migrations require exact pgvector 0.8.6».
- **The search uses `iterative_scan`.** `src/auditmanager/norms/embedding_repository.py:256` sets `hnsw.iterative_scan = strict_order` (with `hnsw.ef_search` and `hnsw.max_scan_tuples` on the next lines). That setting exists from pgvector 0.8.0.
- **The operator tools assume the compose database.** `infra/deploy/purge-product-data.sh:418` runs `pg_dump` through `compose exec -T postgres`; `erase-project.sh`, `memory-forget.sh`, `reset.sh` and `copy-serve.sh` use the same shape; `infra/deploy/apply-grants.sh:433` creates the application role and grants rights as the owner role (`ADR-0021` decision on two roles).
- **The memory is `KEEP`.** The decision memory outlives an erase and a purge (`ADR-0027`); a move must carry it whole, including the forget protection triggers and the tombstones.
- **The host is 4 GB** (`R-146ad`) and the norm encoder peaks at 3 177,9 MiB (`docs/program/NORM_EMBEDDING_BAKEOFF.md:62`): this is why the encoder is the problem the move solves.

## 3. The pgvector check

A move cannot start before this check passes on a trial cluster. It needs two levels, because two things depend on the extension.

**Why 0.8 or later.** The search sets `hnsw.iterative_scan` (section 2). Without pgvector 0.8.0 or later that setting does not exist and a filtered search can return a short answer; the code refuses a short answer, so the search would fail rather than degrade.

**Level 1 — the version that supports `iterative_scan` (required).** On a trial managed cluster, as an administrator of a scratch database:

```sql
SELECT name, default_version, installed_version
  FROM pg_available_extensions WHERE name = 'vector';
SELECT version FROM pg_available_extension_versions WHERE name = 'vector' ORDER BY version;
CREATE EXTENSION vector;                 -- in the scratch database only
SELECT extversion FROM pg_extension WHERE extname = 'vector';
SET hnsw.iterative_scan = strict_order;  -- must not fail
SHOW hnsw.iterative_scan;                -- must print strict_order
SET hnsw.max_scan_tuples = 20000;        -- must not fail
```

Pass: a version of 0.8.0 or later is available, the extension can be created by the account the migrations will use, and the three `SET` statements and the `SHOW` succeed. Record the provider's own step for enabling an extension, if it has one, and the version it installs.

**Level 2 — the exact version the migration pins (required unless the migration changes).** Pass: `0.8.6` appears in the second query and `CREATE EXTENSION vector WITH VERSION '0.8.6'` succeeds. If the provider offers a different 0.8.x or later, the pin in `0013` has to change; that edits a migration that is already applied on the stand, so it is **a decision for the move's own task and the owner**, not for this plan. Options for that task: make the pinned version a configured value, or add a later migration that does not re-create the extension. Do not decide it by reading this document.

Both levels end in a short record under `docs/program/` with the command output, the cluster's PostgreSQL version and the date. If Level 1 fails, the move waits for another route (a self-managed PostgreSQL on a Yandex virtual machine with the repository's image, which keeps the pin and loses the managed service) and `ADR-0029` temporary decision 2 stays in force.

## 4. Steps of the move

Each step has a check that can fail and a way back. No step starts without the owner's order for it; `R-153af` is the current order, and it says not now.

0. **Owner order and a replacing ADR.** `ADR-0021`'s revisit trigger («a managed database … is decided») names this moment: the move's start is the day that ADR is replaced by one that records the new topology, the data location and the new failure domains. Also decided there: where the data may be held and by whom, a legal question for the owner that this plan does not answer; the cost; who holds the cloud account. Until then nothing below starts.
1. **Trial cluster and the pgvector check** (section 3), on an empty database with no client data. Way back: delete the cluster.
2. **The object storage first** (optional order; it is configuration only). Create the bucket and a key limited to it; point a throwaway copy of the stand at it; run the ordinary upload, Range read and erase paths. Observations to take, not gates (`ALPHA_ROADMAP.md` section 7): TLS and a 25 MiB upload, latency against the run's timing, egress cost. Switching production needs a copy of the objects first and a way back to the local volume, which is kept until step 6.
3. **The database.**
   - Prepare: the roles (the owner role that applies the rights, the application role) and `apply-grants.sh` run against the managed instance; the operator tools' `compose exec -T postgres` calls need a variant that reaches a remote database (a task of the move, listed in section 5).
   - Move: a quiesced dump of the production database with the checks `purge-product-data.sh` already uses (`pg_restore --list`), a restore into the managed instance, the migration head compared, the row counts of the `KEEP` tables compared (the decision memory above all), then the switch of `DATABASE_URL` in a window with no run in progress.
   - Verify: `infra/deploy/verify-deployed.sh`, one run through the one-button start, one forget plan on a test case.
   - Way back: the old volume stays untouched until step 6; `DATABASE_URL` is switched back.
4. **The encoder on a separate machine.** Where it runs and how it reaches the intents is the move's decision: files through the object storage (the interface it has now, no database access) or a restricted database role as `DECISION-MEMORY-01` section 3.6 first designed. The memory limit and the unit-norm check on import stay in either case.
5. **Remove the night mode.** The window check in the run issue, the wait cause `vector_window`, the host timer, and the three texts of `ADR-0029` section «Temporary decisions» go; the pause of vectors stays. No new consent is needed (the policy's content did not change).
6. **Retire the local copies** only after a restore drill from a backup taken on the managed side. Until then a disk loss is still the risk `A-1` of `ADR-0021`.

## 5. What a move touches (a list for its tasks, not a scope grant)

- The compose file and `deploy.sh` (the `postgres`, `s3`, `s3-init` services and the checks that expect them) and `verify-deployed.sh`.
- The operator tools that call `compose exec -T postgres` and the recovery tools that classify and purge tables: `purge-product-data.sh`, `erase-project.sh`, `memory-forget.sh`, `reset.sh`, `copy-serve.sh`, `scripts/recovery/**`.
- `apply-grants.sh` and the two roles of `ADR-0021`.
- The restore drill and the copy records of `ADR-0021` (a managed backup is a different artefact from a dump on the host).
- The documents: `ADR-0021` (topology), `ADR-0020` (the single failure domain and the exact pgvector pin), `ADR-0029` (end of temporary decision 2), `ADR-0022` (where personal data may be held), `ALPHA_ROADMAP.md` section 7.

## 6. What this plan does not do

- It does not choose the provider's product, region, size or price.
- It does not move, order or measure anything, and it adds no task to a wave.
- It does not decide the pgvector pin question of section 3, the data-location question of step 0 or the encoder's access path of step 4.
- It does not change `R-146a` (one host) for today.
