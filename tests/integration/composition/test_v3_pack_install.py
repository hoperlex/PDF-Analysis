"""`AR-V3-BETA-PACK-INSTALL-01`: both composition roots install the sealed pack the environment names.

Without ``AR_V3_BETA_PACK_MANIFEST`` the registry stays empty (the behaviour before this task:
group starts refuse). With it, the API and the worker hold the same one-pack registry; a
variable that names anything the loader refuses stops the start with ``ConfigurationError``
rather than quietly serving an empty registry.

Container-free: ``build_application`` and ``build_worker_runtime`` open their engine lazily and
nothing here runs a statement. The environment is built from scratch (no ambient ``DATABASE_URL``,
no real endpoint), so the suite depends on nothing outside this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.bootstrap import adapters as adapters_module
from auditmanager.bootstrap import composition as composition_module
from auditmanager.bootstrap.composition import build_worker_runtime
from auditmanager.bootstrap.settings import EXECUTION_ROLE_ENV
from auditmanager.norms.public import SetIdentity
from auditmanager.runs.public import PACK_MANIFEST_ENV, ReviewAttestation, seal_manifest
from auditmanager.runs.v3_group import SCOPES, ReviewedScope, TrustedPack, TrustedPackRegistry
from auditmanager.shared.identity import NormRetrievalSetId

PROFILE = resolve_beta_v3_profile("ap_01M5M28ZCDD8VPSP1BTAEW92YE", "pb_01M5M28ZCDVCR37BX1884JGSPM")
REVIEW = ReviewAttestation("Test Reviewer", "expert", "2026-10-26", "TEST-1", "test only")


def test_the_variable_name_is_the_documented_one() -> None:
    assert PACK_MANIFEST_ENV == "AR_V3_BETA_PACK_MANIFEST"


def _base_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql+psycopg://am:am@127.0.0.1:1/am",
        "S3_ENDPOINT_URL": "http://127.0.0.1:1",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "test-key",
        "S3_SECRET_ACCESS_KEY": "test-secret",
        "S3_BUCKET": "test-bucket",
    }


def _api_env(**extra: str) -> dict[str, str]:
    return {**_base_env(), "AUDITMANAGER_API_TOKEN": "composition-suite-token", **extra}


def _worker_env(**extra: str) -> dict[str, str]:
    return {**_base_env(), EXECUTION_ROLE_ENV: "worker", **extra}


def _pack() -> TrustedPack:
    return TrustedPack(
        str(PROFILE.analysis_profile_id), str(PROFILE.prompt_bundle_id),
        tuple(
            ReviewedScope(
                scope_id=scope_id,
                identity=SetIdentity(
                    map_sha256=f"{index:x}" * 64, snapshot_id=PROFILE.snapshot_id,
                    reviewed_content_key="ar-v3-beta-synthetic",
                    embedding_build="bge-m3-dense-v1:characters-v2:1200",
                ),
                chunking_profile="characters-v2:1200",
                set_id=str(NormRetrievalSetId.new()), set_sha256=f"{index + 8:x}" * 64,
            )
            for index, scope_id in enumerate(SCOPES, 1)
        ),
    )


@pytest.fixture
def manifest(tmp_path: Path) -> tuple[Path, TrustedPack]:
    pack = _pack()
    path = tmp_path / "pack.json"
    path.write_bytes(seal_manifest(pack, REVIEW))
    return path, pack


def _api_registry(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> TrustedPackRegistry:
    built: dict[str, Any] = {}

    class RunAdapterSpy(adapters_module.RunAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["registry"] = self._ar_v3_pack_registry

    monkeypatch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    build_application(environ=env)
    return built["registry"]


def _worker_registry(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> TrustedPackRegistry:
    seen: dict[str, Any] = {}

    def run_to_terminal_spy(*_args: Any, **kwargs: Any) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(composition_module, "run_to_terminal", run_to_terminal_spy)
    runtime = build_worker_runtime(environ=env)
    try:
        runtime.execute("run_00000000000000000000000000", "wrk_00000000000000000000000000")
    finally:
        runtime.engine.dispose()
    return seen["ar_v3_pack_registry"]


ROOTS = pytest.mark.parametrize(
    ("registry_of", "env_of"),
    [
        pytest.param(_api_registry, _api_env, id="application"),
        pytest.param(_worker_registry, _worker_env, id="worker"),
    ],
)


@ROOTS
def test_without_the_variable_the_registry_is_empty(
    monkeypatch: pytest.MonkeyPatch, registry_of: Any, env_of: Any,
) -> None:
    registry = registry_of(monkeypatch, env_of())
    assert registry == TrustedPackRegistry.empty()
    assert registry.select_beta() is None


@ROOTS
def test_a_blank_variable_is_the_same_as_none(
    monkeypatch: pytest.MonkeyPatch, registry_of: Any, env_of: Any,
) -> None:
    assert registry_of(monkeypatch, env_of(**{PACK_MANIFEST_ENV: "  "})) == TrustedPackRegistry.empty()


@ROOTS
def test_the_named_manifest_is_installed(
    monkeypatch: pytest.MonkeyPatch, registry_of: Any, env_of: Any,
    manifest: tuple[Path, TrustedPack],
) -> None:
    path, pack = manifest
    registry = registry_of(monkeypatch, env_of(**{PACK_MANIFEST_ENV: str(path)}))
    assert registry.installed == (pack,)
    assert registry.select_beta() == pack


def test_both_roots_install_the_same_pack(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    path, _pack_ = manifest
    from_api = _api_registry(monkeypatch, _api_env(**{PACK_MANIFEST_ENV: str(path)}))
    from_worker = _worker_registry(monkeypatch, _worker_env(**{PACK_MANIFEST_ENV: str(path)}))
    assert from_api == from_worker and from_api.installed[0].sha256 == from_worker.installed[0].sha256


def _tampered(tmp_path: Path, pack: TrustedPack) -> Path:
    document = json.loads(seal_manifest(pack, REVIEW))
    document["scopes"][0]["set_sha256"] = "e" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@ROOTS
@pytest.mark.parametrize("case", ["missing", "malformed", "tampered", "directory"])
def test_a_variable_that_names_a_bad_manifest_refuses_the_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, registry_of: Any, env_of: Any, case: str,
) -> None:
    paths = {
        "missing": tmp_path / "absent.json",
        "malformed": tmp_path / "malformed.json",
        "tampered": _tampered(tmp_path, _pack()),
        "directory": tmp_path,
    }
    paths["malformed"].write_text("{}", encoding="utf-8")
    reasons = {
        "missing": "manifest_missing", "malformed": "manifest_keys",
        "tampered": "pack_digest_mismatch", "directory": "manifest_not_regular_file",
    }
    path = paths[case]
    with pytest.raises(ConfigurationError, match=reasons[case]) as refused:
        registry_of(monkeypatch, env_of(**{PACK_MANIFEST_ENV: str(path)}))
    assert PACK_MANIFEST_ENV in str(refused.value)
    assert str(tmp_path) not in str(refused.value), "the configured path stays out of the message"

