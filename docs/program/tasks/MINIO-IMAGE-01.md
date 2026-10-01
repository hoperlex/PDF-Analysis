# Task MINIO-IMAGE-01 — restore reproducible MinIO images from pinned source

> **Status: complete and gated 2026-10-01.** This task owned the MinIO
> image/composition slot for the change below.

## Outcome

`make up` and the alpha composition no longer pull the withdrawn `minio/minio` and
`minio/mc` Docker Hub repositories. Both build repository-owned images from checksum-pinned
official source archives, and retain the existing MinIO server and client release identities.

## Depends on

- `P1-INF-01` — completed and integrated
- `NORM-VECTOR-01` — completed and integrated

## Frozen inputs

- domain contract: candidate revision 8, unchanged
- API contract: 17 paths / 20 operations / 61 schemas, unchanged
- analysis/comparison/event contracts: unchanged
- migration head: `0013_norm_embeddings`, read only
- base commit: `af3ff7ec5e027cad465c6377bf8824b57d429676`
- MinIO server: `RELEASE.2025-09-07T16-13-09Z`, commit
  `07c3a429bfed433e49018cb0f78a52145d4bedeb`
- MinIO client: `RELEASE.2025-08-13T08-35-41Z`, commit
  `7394ce0dd2a80935aded936b09fa12cbb3cb8096`
- S3 bucket names, object keys, persisted volume names and credentials: unchanged

## Allowed paths

- `infra/minio/**`
- MinIO service/build sections of `infra/local/docker-compose.yml`
- MinIO service/build sections of `infra/deploy/compose.server.yml`
- image-pin guards and their prose in `Makefile` and `.env.example`
- `docs/program/FOUNDATION_LOCK.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/MINIO-IMAGE-01.md`
- MinIO image contract tests under `tests/integration/composition/**`

## Forbidden hotspots

- `contracts/**`
- `db/migrations/**` and the migration head
- root dependency manifests and lock files
- API/application/storage/ingest/normative-corpus implementation
- web composition and global styles
- live Docker volumes, object bytes and deployment credentials

## Non-goals

- No live deployment, volume creation/removal, restore or credential rotation.
- No MinIO release upgrade; `D-119` records the security/lifecycle decision separately.
- No immutable normative PDF/crop custody implementation or repair-ledger import.
- No S3 API, bucket-policy or object-key semantic change.

## Deliverables

- one multi-target `infra/minio/Dockerfile` compiling server and client from exact upstream
  commits with source SHA-256 checks and digest-pinned builder/runtime inputs
- local and alpha compositions building the repository-owned `server` and `client` targets
- authenticated MinIO readiness without relying on an image-baked mutable alias
- executable composition tests tying Dockerfile, compose and foundation-lock identities together
- updated foundation lock, state and debt record

## Required tests

- Command: `.venv/bin/python -m pytest tests/integration/composition/test_minio_image_contract.py -q`
  Expected: exit `0`.
- Command: `docker build --target server -f infra/minio/Dockerfile .`
  Expected: exact source builds and `minio --version` identifies the frozen release.
- Command: `docker build --target client -f infra/minio/Dockerfile .`
  Expected: exact source builds and `mc --version` identifies the frozen release.
- Command: `docker compose ... config`
  Expected: both local and alpha compositions resolve without either withdrawn repository.
- Command: `make gate`
  Expected: literal final sentinel `GATE OK`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Consumers still receive S3 at service `s3:9000`, the console at `s3:9001`, the same private
bucket initialized by the same idempotent script, and the same named `s3-data` volume. Image
acquisition changes from a withdrawn pre-built registry repository to a repository-owned build;
runtime release identities and persisted-data mounts do not change.

## Failure/idempotency/security cases

- A changed upstream archive fails its BuildKit SHA-256 check before compilation.
- Builder and runtime base images are tag-and-index-digest pinned in the Dockerfile.
- The build uses `go.sum` in read-only mode; dependency drift is refused.
- The health check authenticates with runtime environment values and never bakes credentials.
- Repeated bucket initialization remains a no-op over an existing private bucket.
- Neither `down` nor rollback removes a named volume.

## Rollback / feature flag

No feature flag: this restores packaging of the already selected releases. Rollback is a
compose/image change only and must preserve all named volumes. Never add `--volumes`, delete an
S3 volume or initialize a replacement volume as part of rollback. The withdrawn registry
references are not a viable cold rollback; retain a known-good locally built image until the
replacement has passed health and object-read checks.

## Handoff

- changed files:
  - `.env.example`, `Makefile`
  - `infra/minio/Dockerfile`
  - `infra/local/docker-compose.yml`, `infra/deploy/compose.server.yml`
  - `tests/integration/composition/test_minio_image_contract.py`
  - `docs/program/{CURRENT_STATE.md,DEBT_REGISTER.md,FOUNDATION_LOCK.json}`
  - `docs/program/tasks/MINIO-IMAGE-01.md`
- commands/results:
  - contract test: **4 passed**; together with the pgvector image contract: **7 passed**
  - real server/client Docker builds: exact release and commit ids printed successfully
  - isolated tmpfs smoke: authenticated readiness, private bucket creation and second-run
    no-op — `MINIO-IMAGE-SMOKE OK`
  - both Compose configs: `COMPOSE-CONFIG-OK`
  - `make up && make check-services`: all PostgreSQL/S3 health, authenticated round-trip,
    idempotency and anonymous-denial checks passed
  - `make gate`: **2636 passed / 5 skipped / 4 warnings / 169 subtests**, foundation **35**,
    frontend **1162 in 82 files**, literal `GATE OK`
  - `git diff --check`: exit `0`
- contracts: foundation image-acquisition contract changed from two withdrawn direct registry
  images to one repository-owned multi-target build. API/domain/event contracts and migration
  head are unchanged.
- known limits: `D-119`; a cold source build requires access to GitHub and Go module sources
  and materially more free disk than the final runtime images.
- integration notes: inventory and back up the existing alpha volumes before the first restart;
  never use `down --volumes`. The first source build is expected to take several minutes.
- forbidden-hotspot proof: `git status --short` contains no path under `contracts/**`,
  `db/migrations/**`, root dependency/lock files, `src/**`, `web/**`, corpus source bytes or
  deployment credential files. The migration head remains `0013_norm_embeddings`.
