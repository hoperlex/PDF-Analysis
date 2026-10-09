from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = ROOT / "infra/minio/Dockerfile"
LOCAL_COMPOSE = ROOT / "infra/local/docker-compose.yml"
DEPLOY_COMPOSE = ROOT / "infra/deploy/compose.server.yml"
LOCK = ROOT / "docs/program/FOUNDATION_LOCK.json"

SERVER_RELEASE = "RELEASE.2025-10-15T17-29-55Z"
SERVER_COMMIT = "9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a"
SERVER_SOURCE_SHA256 = "45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841"
CLIENT_RELEASE = "RELEASE.2025-08-13T08-35-41Z"
CLIENT_COMMIT = "7394ce0dd2a80935aded936b09fa12cbb3cb8096"
CLIENT_SOURCE_SHA256 = "95cd293c7119f16921a6dc515a1fb74a2227f19fd994b9c8b770a154e802ac44"
GO_IMAGE = (
    "golang:1.24.8-bookworm@sha256:"
    "4ed690d6649d63c312b99a6120025ec79ce3b542968a37da53d6236c7c61a848"
)
RUNTIME_IMAGE = (
    "alpine:3.22.1@sha256:"
    "4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1"
)


def _service_block(compose: str, service: str, next_service: str | None) -> str:
    start = compose.index(f"  {service}:\n")
    if next_service is None:
        return compose[start:]
    return compose[start : compose.index(f"  {next_service}:\n", start)]


def test_dockerfile_pins_every_base_source_input_and_release_identity() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert f"FROM {GO_IMAGE} AS build" in text
    assert f"FROM {RUNTIME_IMAGE} AS runtime" in text
    assert f"minio/archive/{SERVER_COMMIT}.tar.gz" in text
    assert f"--checksum=sha256:{SERVER_SOURCE_SHA256}" in text
    assert f"mc/archive/{CLIENT_COMMIT}.tar.gz" in text
    assert f"--checksum=sha256:{CLIENT_SOURCE_SHA256}" in text
    assert "go build -mod=readonly -buildvcs=false" in text
    assert f"cmd.ReleaseTag={SERVER_RELEASE}" in text
    assert f"cmd.CommitID={SERVER_COMMIT}" in text
    assert '"$(sed -n \'s/^toolchain go//p\' /src/minio/go.mod)" = "1.24.8"' in text
    assert f'io.auditmanager.minio.server-release="{SERVER_RELEASE}"' in text
    assert f'io.auditmanager.minio.server-commit="{SERVER_COMMIT}"' in text
    assert f"cmd.ReleaseTag={CLIENT_RELEASE}" in text
    assert f"cmd.CommitID={CLIENT_COMMIT}" in text
    assert "FROM minio/minio" not in text
    assert "FROM minio/mc" not in text
    assert ":latest" not in text


def test_both_compositions_build_repository_owned_server_and_client_targets() -> None:
    for path in (LOCAL_COMPOSE, DEPLOY_COMPOSE):
        compose = path.read_text(encoding="utf-8")
        s3 = _service_block(compose, "s3", "s3-init")
        s3_init = _service_block(compose, "s3-init", "migrate" if path == DEPLOY_COMPOSE else None)

        assert "dockerfile: infra/minio/Dockerfile" in s3
        assert "target: server" in s3
        assert f"minio:{SERVER_RELEASE}-{SERVER_COMMIT[:7]}" in s3
        assert "dockerfile: infra/minio/Dockerfile" in s3_init
        assert "target: client" in s3_init
        assert "minio/minio:" not in compose
        assert "minio/mc:" not in compose


def test_server_readiness_configures_an_authenticated_runtime_alias() -> None:
    for path in (LOCAL_COMPOSE, DEPLOY_COMPOSE):
        compose = path.read_text(encoding="utf-8")
        s3 = _service_block(compose, "s3", "s3-init")

        assert "mc alias set local http://127.0.0.1:9000" in s3
        assert '"$$MINIO_ROOT_USER" "$$MINIO_ROOT_PASSWORD"' in s3
        assert "&& mc ready local" in s3


def test_foundation_lock_matches_the_executable_build_contract() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    server = lock["images"]["s3"]
    client = lock["images"]["s3_client"]

    assert server == {
        "role": "repository-owned MinIO server image",
        "release": SERVER_RELEASE,
        "commit": SERVER_COMMIT,
        "source_archive_sha256": SERVER_SOURCE_SHA256,
        "source_url": f"https://github.com/minio/minio/archive/{SERVER_COMMIT}.tar.gz",
        "dockerfile": "infra/minio/Dockerfile",
        "target": "server",
        "local_image": "auditmanager-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e",
        "deploy_image_template": (
            "${ALPHA_INSTANCE}-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e"
        ),
    }
    assert client == {
        "role": "repository-owned MinIO client image",
        "release": CLIENT_RELEASE,
        "commit": CLIENT_COMMIT,
        "source_archive_sha256": CLIENT_SOURCE_SHA256,
        "source_url": f"https://github.com/minio/mc/archive/{CLIENT_COMMIT}.tar.gz",
        "dockerfile": "infra/minio/Dockerfile",
        "target": "client",
        "local_image": "auditmanager-mc:RELEASE.2025-08-13T08-35-41Z-7394ce0",
        "deploy_image_template": (
            "${ALPHA_INSTANCE}-mc:RELEASE.2025-08-13T08-35-41Z-7394ce0"
        ),
    }

    build_inputs = lock["images"]["minio_build_inputs"]
    assert build_inputs["go_image"] == GO_IMAGE
    assert build_inputs["runtime_image"] == RUNTIME_IMAGE
    assert build_inputs["owner"] == "W53-MINIO-01"
