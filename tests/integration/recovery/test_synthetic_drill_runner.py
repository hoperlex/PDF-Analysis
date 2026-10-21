"""The operator bridge refuses unsafe targets without opening real services."""

from __future__ import annotations

import hashlib
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts.recovery import synthetic_drill_runner as runner
from scripts.recovery.isolated_restore_drill import IsolatedRestoreDrillEvidence
from scripts.recovery.schema_coverage import FINGERPRINTED_TABLES, RestoredSchemaAudit
from scripts.recovery.synthetic_drill_fixture import prepare_synthetic_copy
from scripts.recovery.target_blob_readback import TargetBlobReadback
from scripts.recovery.target_object_restore import TargetObjectRestore


def _env(tmp_path: Path, *, bucket: str = "auditmanager-w58-synthetic-target-01",
         database_url: str | None = None) -> Path:
    name = "auditmanager-w58-synthetic-target-01"
    db = "auditmanager_w58_target_01"
    url = database_url or f"postgresql+psycopg://w58_user:synthetic-password@127.0.0.1:57582/{db}"
    values = {
        "FOUNDATION_INSTANCE": name,
        "POSTGRES_DB": db,
        "POSTGRES_USER": "w58_user",
        "POSTGRES_PASSWORD": "synthetic-password",
        "POSTGRES_PORT": "57582",
        "DATABASE_URL": url,
        "MINIO_ROOT_USER": "synthetic-minio-user",
        "MINIO_ROOT_PASSWORD": "synthetic-minio-password",
        "S3_ENDPOINT_URL": "http://127.0.0.1:61583",
        "S3_API_PORT": "61583",
        "S3_CONSOLE_PORT": "61584",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "synthetic-minio-user",
        "S3_SECRET_ACCESS_KEY": "synthetic-minio-password",
        "S3_BUCKET": bucket,
    }
    path = tmp_path / "target.env"
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="ascii")
    path.chmod(0o600)
    return path


_SCHEMA = RestoredSchemaAudit(55, 4, 72, 31, ())


def _copy(tmp_path: Path, *, payloads: tuple[bytes, ...] = (b"positive Blob",)) -> tuple[Path, Path]:
    paths = []
    lines = "".join(f"{name}|1|{'a' * 64}\n" for name in sorted(FINGERPRINTED_TABLES))
    for name, data in (
        ("dump.input", b"PGDMP\x00synthetic-only"),
        ("fingerprint.lines", lines.encode("ascii")),
        *((f"payload{index}.bin", payload) for index, payload in enumerate(payloads)),
    ):
        path = tmp_path / name
        path.write_bytes(data)
        path.chmod(0o600)
        paths.append(path)
    copy_dir, mirror, _ = prepare_synthetic_copy(
        dump_path=paths[0], fingerprint_lines_path=paths[1], payload_paths=tuple(paths[2:]),
        output_root=tmp_path / "copy", stamp="20261016T120000Z",
        instance="auditmanager-w58-synthetic-source-01", tree_sha="a" * 40,
    )
    return copy_dir, mirror


def test_target_env_is_exact_private_data_and_coherent(tmp_path: Path) -> None:
    path = _env(tmp_path)
    config = runner.load_target_config(path)
    assert config.instance == "auditmanager-w58-synthetic-target-01"
    assert config.target.port == 57582
    assert config.storage.bucket == config.instance
    assert "synthetic-password" not in repr(config)

    path.write_text(path.read_text() + "POSTGRES_PORT=57582\n", encoding="ascii")
    with pytest.raises(runner.SyntheticDrillRefused, match="repeated"):
        runner.load_target_config(path)
    _env(tmp_path)
    path.chmod(0o644)
    with pytest.raises(runner.SyntheticDrillRefused, match="private"):
        runner.load_target_config(path)


@pytest.mark.parametrize("bucket,url", (
    ("foreign-bucket", None),
    ("auditmanager-w58-synthetic-target-01",
     "postgresql+psycopg://w58_user:synthetic-password@db.example:57582/auditmanager_w58_target_01"),
))
def test_wrong_bucket_or_database_endpoint_refuses(tmp_path: Path, bucket: str,
                                                    url: str | None) -> None:
    with pytest.raises(runner.SyntheticDrillRefused):
        runner.load_target_config(_env(tmp_path, bucket=bucket, database_url=url))


def test_postgres_tools_must_all_be_version_17(tmp_path: Path) -> None:
    for name in ("pg_dump", "pg_restore", "psql"):
        tool = tmp_path / name
        tool.write_text("fake", encoding="ascii")
        tool.chmod(0o700)
    calls: list[str] = []

    def version(argv: list[str], **_: object) -> CompletedProcess[str]:
        name = Path(argv[0]).name
        calls.append(name)
        major = "16" if name == "pg_restore" else "17"
        return CompletedProcess(argv, 0, f"{name} (PostgreSQL) {major}.11\n", "")

    with pytest.raises(runner.SyntheticDrillRefused, match="not version 17"):
        runner.require_pg17_tools(tmp_path, runner=version)
    assert calls == ["pg_dump", "pg_restore"]


class _Client:
    def __init__(self, *, nonempty: bool) -> None:
        self.nonempty = nonempty
        self.calls = 0

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        self.calls += 1
        assert kwargs == {"Bucket": "auditmanager-w58-synthetic-target-01", "MaxKeys": 1}
        return {"IsTruncated": False, "KeyCount": int(self.nonempty),
                "Contents": [{"Key": "foreign", "Size": 1}] if self.nonempty else []}


def test_nonempty_bucket_refuses_before_engine_or_restore(tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    copy_dir, mirror = _copy(tmp_path)
    env = _env(tmp_path)
    client = _Client(nonempty=True)
    monkeypatch.setattr(runner, "require_pg17_tools", lambda _: None)
    monkeypatch.setattr(runner, "_object_client", lambda _: client)
    monkeypatch.setattr(runner, "create_database_engine", lambda _: pytest.fail("DB engine opened"))
    with pytest.raises(runner.SyntheticDrillRefused, match="not provably empty"):
        runner.run_synthetic_drill(
            copy_dir=copy_dir, objects_root=mirror, target_env=env,
            pg17_bin=Path("/usr/lib/postgresql/17/bin"),
        )
    assert client.calls == 1


def test_bridge_passes_one_target_to_coordinator_and_requires_positive_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror = _copy(tmp_path)
    env = _env(tmp_path)
    client = _Client(nonempty=False)
    calls: list[str] = []

    class Engine:
        def dispose(self) -> None:
            calls.append("dispose")

    engine = Engine()
    marker = object()
    monkeypatch.setattr(runner, "require_pg17_tools", lambda _: calls.append("tools"))
    monkeypatch.setattr(runner, "_object_client", lambda _: client)
    monkeypatch.setattr(runner, "S3BlobStore", lambda _: marker)
    monkeypatch.setattr(runner, "create_database_engine", lambda _: engine)

    digest = hashlib.sha256(b"copy").hexdigest()
    evidence = IsolatedRestoreDrillEvidence(
        record_sha256=digest, dump_sha256=digest,
        source_counts=(("input_manifest_entry", 1),), schema=_SCHEMA,
        target_objects=TargetObjectRestore(1, len(b"positive Blob"), digest),
        target_blobs=TargetBlobReadback(1, len(b"positive Blob"), digest),
    )

    def bridge(**kwargs: object) -> IsolatedRestoreDrillEvidence:
        calls.append("bridge")
        assert client.calls == 1
        assert kwargs["copy_dir"] == copy_dir and kwargs["objects_root"] == mirror
        assert kwargs["object_client"] is client and kwargs["target_blobs"] is marker
        assert kwargs["target_bucket"] == "auditmanager-w58-synthetic-target-01"
        callback = kwargs["restore_database"]
        assert callback.keywords["engine"] is engine  # type: ignore[union-attr]
        target = callback.keywords["target"]  # type: ignore[union-attr]
        assert target.pgpass_file.is_file()
        assert target.pgpass_file.stat().st_mode & 0o077 == 0
        assert runner.os.environ["PATH"].startswith("/usr/lib/postgresql/17/bin:")
        return evidence

    monkeypatch.setattr(runner, "run_isolated_restore_drill", bridge)
    actual = runner.run_synthetic_drill(
        copy_dir=copy_dir, objects_root=mirror, target_env=env,
        pg17_bin=Path("/usr/lib/postgresql/17/bin"),
    )
    assert actual == evidence and calls == ["tools", "bridge", "dispose"]

    def no_blob(**_: object) -> IsolatedRestoreDrillEvidence:
        return IsolatedRestoreDrillEvidence(
            record_sha256=digest, dump_sha256=digest, source_counts=(), schema=_SCHEMA,
            target_objects=TargetObjectRestore(1, len(b"positive Blob"), digest),
            target_blobs=TargetBlobReadback(0, 0, digest),
        )

    monkeypatch.setattr(runner, "run_isolated_restore_drill", no_blob)
    with pytest.raises(runner.SyntheticDrillRefused, match="positive referenced-Blob"):
        runner.run_synthetic_drill(
            copy_dir=copy_dir, objects_root=mirror, target_env=env,
            pg17_bin=Path("/usr/lib/postgresql/17/bin"),
        )

    def no_reference(**_: object) -> IsolatedRestoreDrillEvidence:
        return IsolatedRestoreDrillEvidence(
            record_sha256=digest, dump_sha256=digest, schema=_SCHEMA,
            source_counts=(("input_manifest_entry", 0),),
            target_objects=TargetObjectRestore(1, len(b"positive Blob"), digest),
            target_blobs=TargetBlobReadback(1, len(b"positive Blob"), digest),
        )

    monkeypatch.setattr(runner, "run_isolated_restore_drill", no_reference)
    with pytest.raises(runner.SyntheticDrillRefused, match="positive referenced-Blob"):
        runner.run_synthetic_drill(
            copy_dir=copy_dir, objects_root=mirror, target_env=env,
            pg17_bin=Path("/usr/lib/postgresql/17/bin"),
        )


def _evidence(objects: int, blobs: int, *, object_bytes: int, blob_bytes: int,
              references: int = 1) -> IsolatedRestoreDrillEvidence:
    digest = hashlib.sha256(b"copy").hexdigest()
    return IsolatedRestoreDrillEvidence(
        record_sha256=digest, dump_sha256=digest, schema=_SCHEMA,
        source_counts=(("input_manifest_entry", references), ("price_list_revision", 1)),
        target_objects=TargetObjectRestore(objects, object_bytes, digest),
        target_blobs=TargetBlobReadback(blobs, blob_bytes, digest),
    )


def _drive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence: IsolatedRestoreDrillEvidence,
           *, payloads: tuple[bytes, ...]) -> IsolatedRestoreDrillEvidence:
    copy_dir, mirror = _copy(tmp_path, payloads=payloads)

    class Engine:
        def dispose(self) -> None:
            pass

    monkeypatch.setattr(runner, "require_pg17_tools", lambda _: None)
    monkeypatch.setattr(runner, "_object_client", lambda _: _Client(nonempty=False))
    monkeypatch.setattr(runner, "S3BlobStore", lambda _: object())
    monkeypatch.setattr(runner, "create_database_engine", lambda _: Engine())
    monkeypatch.setattr(runner, "run_isolated_restore_drill", lambda **_: evidence)
    return runner.run_synthetic_drill(
        copy_dir=copy_dir, objects_root=mirror, target_env=_env(tmp_path),
        pg17_bin=Path("/usr/lib/postgresql/17/bin"),
    )


def test_a_many_blob_copy_needs_every_sealed_object_restored_and_every_blob_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = (b"source pdf", b"text layer", b"crop")
    sizes = sum(map(len, payloads))
    good = _evidence(3, 3, object_bytes=sizes, blob_bytes=sizes)
    (tmp_path / "ok").mkdir()
    assert _drive(tmp_path / "ok", monkeypatch, good, payloads=payloads) == good

    refused = {
        "an-object-was-not-restored": _evidence(2, 2, object_bytes=sizes, blob_bytes=sizes),
        "an-unsealed-object-appeared": _evidence(4, 3, object_bytes=sizes, blob_bytes=sizes),
        "fewer-objects-than-available-blobs": _evidence(3, 4, object_bytes=sizes, blob_bytes=sizes),
        "fewer-bytes-than-the-blobs": _evidence(3, 3, object_bytes=sizes - 1, blob_bytes=sizes),
        "no-manifest-reference": _evidence(3, 3, object_bytes=sizes, blob_bytes=sizes, references=0),
    }
    for name, evidence in refused.items():
        (tmp_path / name).mkdir()
        with pytest.raises(runner.SyntheticDrillRefused, match="positive referenced-Blob"):
            _drive(tmp_path / name, monkeypatch, evidence, payloads=payloads)


def test_a_copy_at_another_head_is_refused_before_any_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror = _copy(tmp_path)
    record = copy_dir / "record.json"
    record.write_bytes(record.read_bytes().replace(b"0028_classification_corrections",
                                                    b"0023_norm_citations"))
    monkeypatch.setattr(runner, "require_pg17_tools", lambda _: None)
    monkeypatch.setattr(runner, "_object_client", lambda _: pytest.fail("S3 opened"))
    with pytest.raises(runner.SyntheticDrillRefused, match="declared head"):
        runner.run_synthetic_drill(
            copy_dir=copy_dir, objects_root=mirror, target_env=_env(tmp_path),
            pg17_bin=Path("/usr/lib/postgresql/17/bin"),
        )
