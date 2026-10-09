# W53-MINIO-01 hand-back — source pin ready, image validation stopped by disk capacity

**Branch:** `agent/w53-minio-01`
**Dispatch base:** `2e458ca9b1867d7dd360a2314b4bf55d848e4aed`
**Result:** code-ready only. The image build, disposable old-write/new-read check and rollback check remain open; this task is not accepted as a working-stand upgrade.

## 1. Changed files

- `infra/minio/Dockerfile` — server source, Go toolchain and release metadata pinned to `RELEASE.2025-10-15T17-29-55Z`; the `mc` client pin is unchanged.
- `infra/local/docker-compose.yml`, `infra/deploy/compose.server.yml` — server image tag only.
- `docs/program/FOUNDATION_LOCK.json` — server entry and `minio_build_inputs.go_image`/owner only.
- `tests/integration/composition/test_minio_image_contract.py` — exact release, source, toolchain, labels and compose-tag assertions.
- This report.

## 2. Checks and results

- Official tag: `git ls-remote https://github.com/minio/minio.git refs/tags/RELEASE.2025-10-15T17-29-55Z` returned `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`.
- Commit-addressed official archive: `sha256sum` returned `45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841`; its `go.mod` declares `toolchain go1.24.8`.
- `docker buildx imagetools inspect golang:1.24.8-bookworm` returned multi-arch index digest `sha256:4ed690d6649d63c312b99a6120025ec79ce3b542968a37da53d6236c7c61a848`.
- `/root/projects/PDF-Analysis/.venv/bin/pytest -q tests/integration/composition/test_minio_image_contract.py` — **4 passed**.
- `/root/projects/PDF-Analysis/.venv/bin/python -m json.tool docs/program/FOUNDATION_LOCK.json` — passed.
- `git diff --check` — passed.
- `ruff check` was unavailable in the shared virtual environment; the focused Python test file imports and runs successfully.
- One `DOCKER_BUILDKIT=1 docker build --progress=plain --target server ...` attempt began and was deliberately stopped when free disk fell from about 13 GB to 8.9 GB while Go was compiling. The stopped client returned 137; no new image was published. Build log: `/tmp/w53-minio-build.log`, SHA-256 `c1019c0add2c5dedb2113baee1bd9d6f9719f604420c9390d9dc84f6fc55ce70`. After removing only this lane's temporary source archives, free disk was 9.5 GB. Shared BuildKit cache was not pruned.
- **Not run:** completed image version/label inspection, old-image writes → new-image reads on a disposable data copy, and S3-level rollback restore/read. The new image does not exist yet. A disposable-only rehearsal helper is at `/tmp/w53-minio-rehearsal.py`; it uses only `gate-w53minio` resources and reserved port 60440, but it has not been executed.

## 3. Contracts

No API, domain, error-catalog or migration contract changed. The image build contract now pins MinIO server `RELEASE.2025-10-15T17-29-55Z`, commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`, archive SHA-256 `45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841` and digest-pinned Go 1.24.8. The client and Alpine runtime pins remain unchanged.

## 4. Risks and limitations

The source and static contract are verified, but the build has no success evidence. Runtime compatibility and rollback remain unproven. The combined host has insufficient safely available disk for the current build alongside other active work. The working stand was not accessed or changed. `D-119` and `D-123` remain open.

## 5. Integrator instructions

Merge this lane only as code-ready preparation. In a separately available build slot with sufficient disk, build the exact server target, inspect version and labels, then run old-write/new-read against a stopped-volume copy and an S3-level restore into a fresh old-image volume. Keep the working stand closed until its recoverable S3 copy and inventory are separately authorized and verified. Do not infer a successful image or wave acceptance from the four static tests.

## 6. Allowed-path and forbidden-hotspot proof

The committed `git diff --name-only 2e458ca9b1867d7dd360a2314b4bf55d848e4aed HEAD` lists only the six paths in §1. These are exactly the task's allowed paths. No contracts, migrations, root dependency/lock files, composition root, global styles, SEAL files, backup/deploy scripts, `VERSION`, release notes, published refs, tags or working-stand assets were changed. No lane Docker container or volume was created; no shared Docker cache was removed.
