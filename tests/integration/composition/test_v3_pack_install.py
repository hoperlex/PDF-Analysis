"""`AR-V3-BETA-PACK-INSTALL-01`: both composition roots install the sealed pack the environment names.

Without ``AR_V3_BETA_PACK_MANIFEST`` the registry stays empty (the behaviour before this task:
group starts refuse). With it, the API and the worker hold the same one-pack registry; a
variable that names anything the loader refuses stops the start with ``ConfigurationError``
rather than quietly serving an empty registry.

`AR-V3-BETA-PACK-STATUS-API-01`: the same load also gives the API root the attestation that came
with the pack, and ``getArV3BetaPackStatus`` answers from it -- ``not_installed`` while the
variable is unset or blank, the pack's ids, digest, scopes and attestation once it names a good
manifest, and never the configured path.

Container-free: ``build_application`` and ``build_worker_runtime`` open their engine lazily and
nothing here runs a statement. The environment is built from scratch (no ambient ``DATABASE_URL``,
no real endpoint), so the suite depends on nothing outside this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.api.routers.ar_v3_groups import build_ar_v3_group_routes
from auditmanager.bootstrap import adapters as adapters_module
from auditmanager.bootstrap import composition as composition_module
from auditmanager.bootstrap.composition import build_worker_runtime
from auditmanager.bootstrap.settings import EXECUTION_ROLE_ENV
from auditmanager.norms.public import SetIdentity
from auditmanager.runs.public import PACK_MANIFEST_ENV, START_ALLOWED_ENV, ReviewAttestation, seal_manifest
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


# --- `AR-V3-BETA-PACK-STATUS-API-01`: the API root also exposes what was installed ----------


def _api_status(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> tuple[int, dict[str, Any], bytes]:
    """Build the served application, then ask its group port the way the route does."""
    built: dict[str, Any] = {}

    class RunAdapterSpy(adapters_module.RunAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["adapter"] = self

    monkeypatch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    build_application(environ=env)
    router = APIRouter()
    build_ar_v3_group_routes(router, built["adapter"])
    route = next(route for route in router.routes if route.operation_id == "getArV3BetaPackStatus")
    response = route.endpoint()
    return response.status_code, json.loads(response.body), response.body


@pytest.mark.parametrize("env_extra", [{}, {PACK_MANIFEST_ENV: "   "}], ids=["unset", "blank"])
def test_the_api_reports_not_installed_while_no_manifest_is_named(
    monkeypatch: pytest.MonkeyPatch, env_extra: dict[str, str],
) -> None:
    status, answer, _body = _api_status(monkeypatch, _api_env(**env_extra))
    assert (status, answer) == (200, {"state": "not_installed"})


def test_the_api_reports_the_installed_pack_and_its_attestation(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    path, pack = manifest
    status, answer, body = _api_status(monkeypatch, _api_env(**{PACK_MANIFEST_ENV: str(path)}))
    assert status == 200
    assert answer == {
        "state": "installed",
        "analysis_profile_id": pack.analysis_profile_id,
        "prompt_bundle_id": pack.prompt_bundle_id,
        "pack_sha256": pack.sha256,
        "scope_ids": list(SCOPES),
        # `AR-V3-OPT-IN`: the pack is the capability; starting is a separate permission, off unless the environment says `1`.
        "start_allowed": False,
        "review": {
            "reviewer": REVIEW.reviewer, "capacity": REVIEW.capacity,
            "reviewed_at": REVIEW.reviewed_at, "decision_ref": REVIEW.decision_ref,
            "scope_statement": REVIEW.scope_statement,
        },
    }
    assert str(path.parent) not in body.decode("utf-8"), "the configured path stays out of the answer"


def test_the_status_and_the_registry_come_from_one_load(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    """What the screen is told is installed is what a group start would pin."""
    path, _pack_ = manifest
    env = _api_env(**{PACK_MANIFEST_ENV: str(path)})
    registry = _api_registry(monkeypatch, env)
    _status, answer, _body = _api_status(monkeypatch, env)
    selected = registry.select_beta()
    assert selected is not None and answer["pack_sha256"] == selected.sha256


def test_the_worker_root_still_needs_and_gets_only_the_registry(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    path, pack = manifest
    registry = _worker_registry(monkeypatch, _worker_env(**{PACK_MANIFEST_ENV: str(path)}))
    assert registry.select_beta() == pack


# --- `AR-V3-OPT-IN`: the allowance is a second layer, read by the api build only, off by default ------------


def _built_adapter(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> adapters_module.RunAdapter:
    built: dict[str, Any] = {}

    class RunAdapterSpy(adapters_module.RunAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["adapter"] = self

    monkeypatch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    build_application(environ=env)
    return built["adapter"]


@pytest.mark.parametrize(("value", "expected"), [
    (None, False), ("", False), ("   ", False), ("0", False), ("1", True), (" 1 ", True),
], ids=["unset", "blank", "spaces", "zero", "one", "padded-one"])
def test_the_api_build_reads_the_allowance_strictly_and_a_pack_alone_never_allows_a_start(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack], value: str | None, expected: bool,
) -> None:
    path, _pack_ = manifest
    extra = {PACK_MANIFEST_ENV: str(path), **({} if value is None else {START_ALLOWED_ENV: value})}
    status, answer, _body = _api_status(monkeypatch, _api_env(**extra))
    assert status == 200 and answer["state"] == "installed" and answer["start_allowed"] is expected
    assert _built_adapter(monkeypatch, _api_env(**extra))._ar_v3_start_allowed is expected


def test_without_a_pack_the_allowance_is_not_in_the_answer_whatever_the_environment_says(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status, answer, _body = _api_status(monkeypatch, _api_env(**{START_ALLOWED_ENV: "1"}))
    assert (status, answer) == (200, {"state": "not_installed"})


@pytest.mark.parametrize("value", ["true", "yes", "2", "1x", "on"])
def test_a_value_that_is_not_plainly_zero_or_one_stops_the_api_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack], value: str,
) -> None:
    path, _pack_ = manifest
    monkeypatch.setattr(composition_module, "RunAdapter", adapters_module.RunAdapter)
    with pytest.raises(ConfigurationError) as refused:
        build_application(environ=_api_env(**{PACK_MANIFEST_ENV: str(path), START_ALLOWED_ENV: value}))
    assert START_ALLOWED_ENV in str(refused.value)


def test_the_worker_root_does_not_read_the_allowance_so_what_was_accepted_still_runs(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    """A worker given a malformed allowance still builds and still installs the pack: the variable is the api's."""
    path, pack = manifest
    for value in ("true", "0", "1"):
        registry = _worker_registry(monkeypatch, _worker_env(**{PACK_MANIFEST_ENV: str(path), START_ALLOWED_ENV: value}))
        assert registry.select_beta() == pack


def test_with_the_allowance_off_the_served_price_and_start_of_a_group_are_the_typed_conflict(
    monkeypatch: pytest.MonkeyPatch, manifest: tuple[Path, TrustedPack],
) -> None:
    """The served composition, a pack installed and no allowance: the price is refused before the database is asked."""
    from auditmanager.shared.errors import DomainError, ErrorCode

    path, _pack_ = manifest
    adapter = _built_adapter(monkeypatch, _api_env(**{PACK_MANIFEST_ENV: str(path)}))
    with pytest.raises(DomainError) as refused:
        adapter.estimate_ar_v3_group_cost(version_uid="ver_01M2545JSD15ETSNNV904XA001")
    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.detail_fields["conflict_reason"] == "ar_v3_start_not_enabled"
