"""The PostgreSQL derivative has one exact, shared supply-chain definition."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "docs/program/FOUNDATION_LOCK.json"
DOCKERFILE = ROOT / "infra/postgres/Dockerfile"
LOCAL_COMPOSE = ROOT / "infra/local/docker-compose.yml"
DEPLOY_COMPOSE = ROOT / "infra/deploy/compose.server.yml"

BASE = (
    "postgres:17.11-trixie@sha256:"
    "67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675"
)
VERSION = "0.8.6"
COMMIT = "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c"
ARCHIVE_SHA256 = "d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299"
LOCAL_IMAGE = "auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9"
DEPLOY_IMAGE = "${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-postgres-pgvector:17.11-v0.8.6-8ee86c9"


def _service_block(text_value: str, service: str) -> str:
    lines = text_value.splitlines()
    start = next(index for index, line in enumerate(lines) if line.rstrip() == "services:")
    captured: list[str] = []
    active = False
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            if active:
                break
            active = line.strip().rstrip(":") == service
            continue
        if active:
            captured.append(line)
    assert captured, f"compose has no non-empty {service!r} service block"
    return "\n".join(captured)


def test_lock_names_the_exact_base_and_pgvector_source() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    postgres = lock["images"]["postgres"]
    derivative = postgres["derivative"]

    assert postgres["reference"] == BASE
    assert derivative == {
        "dockerfile": "infra/postgres/Dockerfile",
        "local_image": LOCAL_IMAGE,
        "deploy_image_template": "${ALPHA_INSTANCE}-postgres-pgvector:17.11-v0.8.6-8ee86c9",
        "pgvector_version": VERSION,
        "pgvector_commit": COMMIT,
        "source_archive_sha256": ARCHIVE_SHA256,
        "source_url": f"https://github.com/pgvector/pgvector/archive/{COMMIT}.tar.gz",
    }


def test_derivative_verifies_source_before_build_and_copies_only_runtime_artifacts() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert f"ARG POSTGRES_BASE_IMAGE={BASE}" in dockerfile
    assert dockerfile.count("FROM ${POSTGRES_BASE_IMAGE}") == 2
    assert f"ARG PGVECTOR_VERSION={VERSION}" in dockerfile
    assert f"ARG PGVECTOR_COMMIT={COMMIT}" in dockerfile
    assert f"ADD --checksum=sha256:{ARCHIVE_SHA256}" in dockerfile
    assert f"https://github.com/pgvector/pgvector/archive/{COMMIT}.tar.gz" in dockerfile
    assert "OPTFLAGS=\"\"" in dockerfile
    assert "COPY --from=pgvector-build /tmp/pgvector-root/ /" in dockerfile
    assert "/usr/share/doc/pgvector/LICENSE" in dockerfile
    assert "pgvector/pgvector:" not in dockerfile


def test_local_and_alpha_use_the_same_dockerfile_and_frozen_base() -> None:
    local = _service_block(LOCAL_COMPOSE.read_text(encoding="utf-8"), "postgres")
    deploy = _service_block(DEPLOY_COMPOSE.read_text(encoding="utf-8"), "postgres")

    for block in (local, deploy):
        assert "context: ../.." in block
        assert "dockerfile: infra/postgres/Dockerfile" in block
        assert "pgvector/pgvector:" not in block
    assert "POSTGRES_BASE_IMAGE: ${FOUNDATION_POSTGRES_IMAGE:?" in local
    assert f"image: {LOCAL_IMAGE}" in local
    assert f"POSTGRES_BASE_IMAGE: {BASE}" in deploy
    assert f"image: {DEPLOY_IMAGE}" in deploy
