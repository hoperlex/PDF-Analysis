# FF-01 — early PostgreSQL/S3 Foundation Freeze

> **Approval state: FF-01 ACCEPTED on 2026-09-09.** The repository owner approved this
> independently approvable slice without qualification. `P0-FND-00` is complete and
> `P1-INT-00` is dispatchable; P02–P05 remain unapproved and non-dispatchable.

## 1. Outcome

A reproducible local foundation in which PostgreSQL and a private S3-compatible service
start from one command, migrations run from an empty database, and a storage adapter
publishes bytes only after checksum verification. The slice contains no product domain
workflow and makes no production-readiness claim.

This slice is deliberately approved before the full roadmap so implementation can run
while `P0-PLN-01` completes the real-audit and validation plan.

## 2. Frozen decisions

Acceptance freezes these decisions for the prototype:

1. PostgreSQL is the only canonical metadata and durable-state database.
2. Private S3-compatible storage is the only canonical store for source bytes and large
   artifacts. MinIO is the local implementation; application code targets the S3 API.
3. Database and object storage are reached through Python ports/adapters, never directly
   from routers, React components or analysis stages.
4. A blob is addressed in business code by opaque `blob_id`; bucket/key remain adapter
   details.
5. Published bytes carry role, media type, size and SHA-256 and follow
   `temporary -> verify -> publish`.
6. A checksum mismatch, incomplete upload or unavailable storage is an explicit failure;
   no object is presented as published.
7. Local buckets are private and anonymous list/read/write is denied.
8. One task owns root dependency/lock files and the command surface. One task owns the
   migration head. No parallel writer may share either hotspot.
9. Exact dependency and container-image versions are selected and locked by
   `P1-INT-00` before provider lanes start; floating `latest` references are forbidden.
10. The foundation can be replaced only by an explicit freeze-break with a data disposal
    or migration note.

## 3. Stable environment and command names

`P1-INT-00` fixes exact values and executable strings, but the names below are frozen so
parallel tasks do not invent incompatible configuration.

Required environment names:

- `FOUNDATION_INSTANCE`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `S3_ENDPOINT_URL`
- `S3_API_PORT`
- `S3_CONSOLE_PORT`
- `S3_REGION`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET`

`.env.example` contains disposable local examples only. Real `.env` files and credentials
remain ignored. `POSTGRES_*` and `MINIO_ROOT_*` configure the disposable local services;
`DATABASE_URL` and `S3_*` are the application-facing values. `P1-INT-00` must keep the
two sides coherent without treating root MinIO credentials as a production IAM design.

The root task runner is `make`. These literal commands are frozen:

- `make bootstrap` — reproduce both ignored locked environments: `.venv/bootstrap` for
  governance validators and `.venv` for runtime/foundation tests;
- `make up` — start PostgreSQL and S3-compatible local services;
- `make down` — stop them without deleting persisted data;
- `make check-services` — prove PostgreSQL/MinIO health and idempotent private-bucket
  initialization without inspecting the application migration head;
- `make migrate` — apply the migration head safely;
- `make check-db` — prove application database connectivity and current migration state;
- `make check-storage` — prove the BlobStore adapter can access the private bucket through
  configured application credentials;
- `make test-foundation` — run only the accepted foundation suite;
- `make foundation` — execute `up`, `check-services`, `migrate`, the DB/storage checks and
  the foundation suite.

`P1-INT-00` creates the complete nine-target Makefile surface before provider fan-out.
Targets whose implementations arrive later are stable forwarders to these owned paths:

- service check: `infra/local/check_services.py` (`P1-INF-01`);
- DB check: `src/auditmanager/shared/db/check.py` (`P1-DB-01`);
- storage check: `src/auditmanager/storage/check.py` (`P1-STO-01`);
- convergence suite: `tests/integration/foundation/**` (`P1-QA-00`).

`P1-INT-00` records their exact invocations in `FOUNDATION_LOCK.json`. Later tasks fill
only their reserved paths and invoke the root targets; they neither edit the Makefile nor
create private command aliases.

## 4. Approved implementation scope

Included:

- reproducible Python dependency lock and root command surface;
- containerized PostgreSQL and MinIO/S3-compatible local services;
- health checks and persistent local volumes;
- idempotent private-bucket initialization;
- migration runner and baseline migration infrastructure;
- database session/transaction adapter usable by later bounded contexts;
- a narrow BlobStore port and S3 adapter for temporary upload, checksum verification,
  canonical publication, metadata inspection and reads;
- integration tests against real local PostgreSQL and MinIO;
- startup, shutdown and troubleshooting documentation.

Not approved by this freeze:

- Project, DocumentVersion, AuditRun or finding tables;
- API routes, frontend, analysis pipeline or background job runner;
- generic repository/base service/global utility frameworks;
- direct filesystem or JSON canonical storage;
- automatic retry, outbox, Job/Attempt, lease, heartbeat or fencing;
- multiple buckets, cloud account layout, production IAM, lifecycle or retention;
- backup/restore, HA, DR, load testing or production deployment;
- any legacy runtime or obsolete script.

## 5. Task graph and early parallelism

```text
P0-FND-00 / FF-01 ACCEPTED
  -> P1-INT-00  toolchain, pins, environment and commands
       |-> P1-INF-01  PostgreSQL + MinIO local services ---------|
       |-> P1-DB-01   migration/session foundation --------------|-> P1-QA-00
       |-> P1-STO-01  BlobStore + S3 adapter --------------------|     -> P1-INT-01

In parallel after FF-01:
P0-PLN-01  completes P02-P05; it cannot edit this freeze or P01 providers.
```

`P1-INF-01`, `P1-DB-01` and `P1-STO-01` may write in parallel because their owned paths
are disjoint. Their live-service state must also be disjoint: every authoring lane uses a
unique `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
`POSTGRES_DB` and `S3_BUCKET`. Compose project name, network and volume names derive from
`FOUNDATION_INSTANCE`; a lane may not run `make up` against another lane's instance.

Storage/DB tests that require live services run against their own instance after the INF
provider is available. Official convergence and acceptance commands run serially on one
clean integration instance. This runtime dependency grants no write access to another
task's paths.

## 6. Ownership

| Task | Sole writer | Result |
|---|---|---|
| `P1-INT-00` | root manifests/locks, task runner, `.env.example`, foundation pin record | exact toolchain and command contract |
| `P1-INF-01` | `infra/local/**` | services, namespaced volumes, bucket initializer and service-health checker |
| `P1-DB-01` | `db/migrations/**`, scoped shared DB adapter | migration, transaction foundation and DB-head checker |
| `P1-STO-01` | `src/auditmanager/storage/**` | BlobStore, S3 adapter and storage checker |
| `P1-QA-00` | cross-provider foundation tests only | failure, persistence and privacy evidence |
| `P1-INT-01` | foundation report/state only | independent acceptance and handoff to P02 |

Root locks, migration head and storage implementation never have a second writer in this
slice.

## 7. Blocking acceptance

The foundation is accepted only when a reviewer performs these behaviors from a clean
checkout using the recorded commands:

1. bootstrap twice without changing a lock or tracked file;
2. start PostgreSQL and MinIO without manual preparation;
3. migrate an empty database and rerun migration safely;
4. confirm the configured bucket exists and anonymous list/read/write is denied;
5. upload temporary bytes, verify SHA-256 and publish under an adapter-owned key;
6. reject a wrong checksum and prove no canonical object was published;
7. stop and start services without losing the migrated state or published test object;
8. run two identical bucket-initialization attempts without error or duplicate state;
9. show that public return values contain `blob_id` and metadata, not internal bucket/key;
10. scan tracked changes for credentials and floating container tags.

Failures outside this list do not become foundation blockers merely because a historical
suite reports them. The bootstrap validator and `git diff --check` remain required.

## 8. Handoff contract to later stages

P02 consumers may rely on:

- a reproducible command to start and validate both services;
- a current migration head and transaction/session factory;
- private-bucket initialization;
- a tested BlobStore interface implementing temporary, verify, publish and read;
- explicit unavailable/checksum/publication failures;
- opaque blob identity and no leaked object key.

P02 owns domain schema and use cases. It may extend the migration head through its named
migration owner and add blob metadata persistence, but it may not bypass or silently
replace these providers.

## 9. Estimate

Assuming one integrator plus three worker slots and same-day owner/reviewer response:

| Work | P50 | P80 |
|---|---:|---:|
| `P1-INT-00` pins and command contract | 0.5–1 day | 2 days |
| three provider lanes in parallel | 2–3 days elapsed | 4–5 days |
| convergence QA and remediation | 1–2 days | 3–4 days |
| independent integration acceptance | 0.5–1 day | 2 days |
| **Foundation total after approval** | **4–7 days** | **11–13 days** |

The total is the arithmetic sum of the rows; only the three provider lanes are parallel
inside their row. `P0-PLN-01` runs beside P01 with a separate estimate of 1–2 elapsed days
P50 and 3–4 days P80, so it is not added to the foundation critical path. The first
infrastructure commit is expected 1–2 days after `FF-01 ACCEPTED` at P50 and within
3 days at P80.

## 10. Approval record

The repository owner recorded this acceptance without qualification on 2026-09-09:

```text
FF-01 ACCEPTED
PostgreSQL/S3 foundation approved for P01 implementation.
P02-P05 remain unapproved and non-dispatchable pending P0-PLN-01.
```

This record completes `P0-FND-00` and authorizes dispatch of `P1-INT-00` and
`P0-PLN-01` from the commit containing this record. It does not authorize a P01 provider
before `P1-INT-00` is accepted or any P02 implementation before its separate gates.
