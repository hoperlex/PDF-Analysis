"""The provider source switch (`EXEC-HTTP-01`, plan section 6): what a process refuses to start with.

Container-free: ``settings.load`` reads a mapping and touches nothing.
"""

from __future__ import annotations

import pytest

from auditmanager.bootstrap.composition import _build_provider
from auditmanager.bootstrap.providers import DatabaseProviders, EnvironmentProviders, UnboundAdapter
from auditmanager.bootstrap.settings import ConfigurationError, load

BASE = {
    "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:9/d", "S3_ENDPOINT_URL": "http://127.0.0.1:9",
    "S3_REGION": "r", "S3_ACCESS_KEY_ID": "a", "S3_SECRET_ACCESS_KEY": "b", "S3_BUCKET": "c",
    "AUDITMANAGER_API_TOKEN": "token",
}
# A well-formed private key (32 zero bytes is not a valid secret in practice, but it parses).
RING = "k1:" + "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
ACTIVE = {"AUDITMANAGER_SECRETS_ACTIVE_KID": "k1"}
PROXY = {"AUDITMANAGER_PROVIDER_MODE": "proxy", "PROXY_LLM_BASE_URL": "https://p.example/agent/v1",
         "PROXY_LLM_TOKEN": "tok", "PROXY_LLM_MODEL": "anthropic/claude-opus-5"}


WORKER_BASE = {k: v for k, v in BASE.items() if k != "AUDITMANAGER_API_TOKEN"}


def _load(**extra: str):  # type: ignore[no-untyped-def]
    # The worker holds no API token (R-105), so it is loaded from the base without it.
    base = WORKER_BASE if extra.get("EXECUTION_ROLE") == "worker" else BASE
    return load({**base, **extra})


def test_the_default_source_is_environment_and_changes_nothing_for_a_recorded_process() -> None:
    settings = _load()
    assert (settings.provider_source, settings.provider_mode) == ("environment", "recorded")


def test_an_undeclared_source_is_refused() -> None:
    with pytest.raises(ConfigurationError, match="AUDITMANAGER_PROVIDER_SOURCE"):
        _load(AUDITMANAGER_PROVIDER_SOURCE="both")


def test_the_database_source_needs_live_mode() -> None:
    for mode in ("recorded", "proxy"):
        with pytest.raises(ConfigurationError, match="must be live"):
            _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE=mode,
                  AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE)


@pytest.mark.parametrize("leftover", [
    {"PROXY_LLM_BASE_URL": "https://p"}, {"PROXY_LLM_TOKEN": "t"}, {"PROXY_LLM_MODEL": "m"},
    {"ANTHROPIC_API_KEY": "sk"},
])
def test_the_database_source_refuses_incomplete_or_unowned_environment_keys(leftover: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError, match="triplet|without its baseline|still set"):
        _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
              EXECUTION_ROLE="worker", AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE, **leftover)


def test_a_complete_worker_only_baseline_is_accepted_without_becoming_a_second_provider() -> None:
    baseline = {key: value for key, value in PROXY.items() if key != "AUDITMANAGER_PROVIDER_MODE"}
    worker = _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
                   EXECUTION_ROLE="worker", AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE, **baseline)
    assert worker.provider_source == "database" and worker.proxy_token == "tok"
    for role in ("api", "all"):
        with pytest.raises(ConfigurationError, match="worker-only"):
            _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
                  EXECUTION_ROLE=role, AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE,
                  **baseline)


def test_the_database_source_needs_no_environment_key_but_a_worker_needs_the_ring() -> None:
    worker = _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
                   EXECUTION_ROLE="worker", AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE)
    assert worker.provider_source == "database" and worker.api_key is None
    with pytest.raises(ConfigurationError, match="AUDITMANAGER_SECRETS_KEYS is unset"):
        _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
              EXECUTION_ROLE="worker")


def test_the_api_role_demands_no_provider_credential_in_either_branch() -> None:
    for extra in ({"AUDITMANAGER_PROVIDER_MODE": "live"}, {"AUDITMANAGER_PROVIDER_MODE": "proxy"}):
        assert _load(EXECUTION_ROLE="api", **extra).execution_role == "api"
    # ... while every other role still does.
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        _load(EXECUTION_ROLE="all", AUDITMANAGER_PROVIDER_MODE="live")
    with pytest.raises(ConfigurationError, match="PROXY_LLM_BASE_URL"):
        _load(EXECUTION_ROLE="all", AUDITMANAGER_PROVIDER_MODE="proxy")


def test_the_environment_source_hands_every_run_its_adapter_and_holds_the_reply_to_the_model() -> None:
    settings = _load(**PROXY)
    adapter, _config, _profile, _bundle, source = _build_provider(settings, {**BASE, **PROXY})
    assert isinstance(source, EnvironmentProviders) and source.freeze is None
    binding = source.resolve(None, type("Run", (), {"connection_revision_id": None})(), None)  # type: ignore[arg-type]
    assert binding.adapter is adapter
    assert (binding.call.expected_model, binding.call.check_identity) == (
        "anthropic/claude-opus-5", True)
    assert binding.call.provider_label == "anthropic"


def test_the_environment_source_refuses_a_run_that_froze_a_connection() -> None:
    settings = _load(**PROXY)
    *_, source = _build_provider(settings, {**BASE, **PROXY})
    run = type("Run", (), {"connection_revision_id": "excr_01J00000000000000000000000"})()
    from auditmanager.shared.errors import DomainError

    with pytest.raises(DomainError) as refused:
        source.resolve(None, run, None)  # type: ignore[arg-type]
    assert refused.value.code.value == "dependency_unavailable"


def test_the_api_role_builds_no_provider_adapter_and_the_database_source_none_of_its_own() -> None:
    api_settings = _load(EXECUTION_ROLE="api", AUDITMANAGER_PROVIDER_MODE="proxy")
    adapter, *_ = _build_provider(api_settings, {**BASE, "AUDITMANAGER_PROVIDER_MODE": "proxy",
                                                 "EXECUTION_ROLE": "api"})
    assert isinstance(adapter, UnboundAdapter)
    database = _load(AUDITMANAGER_PROVIDER_SOURCE="database", AUDITMANAGER_PROVIDER_MODE="live",
                     EXECUTION_ROLE="worker", AUDITMANAGER_SECRETS_KEYS=RING, **ACTIVE)
    adapter, _config, _p, _b, source = _build_provider(database, {
        **WORKER_BASE, "AUDITMANAGER_PROVIDER_MODE": "live",
        "AUDITMANAGER_PROVIDER_SOURCE": "database", "EXECUTION_ROLE": "worker"})
    assert isinstance(adapter, UnboundAdapter) and isinstance(source, DatabaseProviders)
    assert source.freeze is not None
    from auditmanager.shared.errors import DomainError

    with pytest.raises(DomainError) as unbound:
        adapter.complete(None)  # type: ignore[arg-type]
    assert unbound.value.code.value == "dependency_unavailable"
