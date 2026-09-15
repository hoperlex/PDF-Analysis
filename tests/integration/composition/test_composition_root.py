"""The composition root's one contract: a missing dependency fails at construction.

Not at first use. The distinction is the whole point - a process that starts, answers a
health check and dies on the first upload has already accepted a document and written a run
row before anyone learns the provider was never configured.
"""

from __future__ import annotations

import os

import pytest

from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.bootstrap.settings import (
    API_KEY_ENV,
    COST_CEILING_ENV,
    PROVIDER_MODE_ENV,
    load,
)


def _base_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()}
    assert env.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return env


class TestItRefusesToStartRatherThanFailLater:
    @pytest.mark.parametrize(
        "missing",
        [
            "DATABASE_URL",
            "S3_ENDPOINT_URL",
            "S3_REGION",
            "S3_ACCESS_KEY_ID",
            "S3_SECRET_ACCESS_KEY",
            "S3_BUCKET",
        ],
    )
    def test_every_required_value_is_checked_at_construction(self, missing: str) -> None:
        env = _base_env()
        env.pop(missing, None)
        with pytest.raises(ConfigurationError) as caught:
            build_application(environ=env)
        assert missing in str(caught.value), (
            f"the refusal does not name {missing}, so an operator cannot act on it"
        )

    def test_an_undeclared_provider_mode_is_refused(self) -> None:
        env = _base_env() | {PROVIDER_MODE_ENV: "sort-of-live"}
        with pytest.raises(ConfigurationError, match="declared modes"):
            build_application(environ=env)

    def test_live_mode_without_a_credential_is_refused(self) -> None:
        """The failure this exists to prevent: a live process that cannot make a call.

        Discovered at startup, it costs nothing. Discovered at first use, a document has
        been uploaded and a run row written before anyone learns.
        """
        env = _base_env() | {PROVIDER_MODE_ENV: "live"}
        env.pop(API_KEY_ENV, None)
        with pytest.raises(ConfigurationError) as caught:
            build_application(environ=env)
        assert API_KEY_ENV in str(caught.value)

    def test_a_ceiling_that_cannot_be_parsed_is_refused(self) -> None:
        """A ceiling that does not parse is a ceiling that does not hold."""
        env = _base_env() | {COST_CEILING_ENV: "one dollar"}
        with pytest.raises(ConfigurationError, match="not a number"):
            build_application(environ=env)

    def test_a_non_positive_ceiling_is_refused(self) -> None:
        env = _base_env() | {COST_CEILING_ENV: "0"}
        with pytest.raises(ConfigurationError, match="must be positive"):
            build_application(environ=env)


class TestWhatItActuallyWires:
    def test_it_builds_all_twelve_frozen_operations(self) -> None:
        app = build_application(environ=_base_env())
        assert len(app.router.routes) == 12, (
            "the router does not carry the twelve operations the frozen document declares"
        )

    def test_the_wired_mode_is_the_configured_one(self) -> None:
        app = build_application(environ=_base_env() | {PROVIDER_MODE_ENV: "recorded"})
        assert app.settings.provider_mode == "recorded"

    def test_no_default_is_invented_for_a_required_value(self) -> None:
        """Absence must be refused, never filled in.

        A default database URL or bucket would turn a misconfiguration into a process that
        quietly writes to the wrong place, which is worse than one that will not start.
        """
        for required in ("DATABASE_URL", "S3_BUCKET", "S3_ENDPOINT_URL"):
            env = _base_env()
            env.pop(required, None)
            with pytest.raises(ConfigurationError):
                load(env)


class TestTheProxyIsATransportNotAProvenanceMode:
    """`OD-02` was revised to an LLM proxy on 2026-09-14.

    Three things independently refuse `proxy` as a run's recorded mode, and they agree: the
    database CHECK on `audit_run.provider_mode` admits only `live` and `recorded`;
    `execute_run` refuses a run whose declared mode disagrees with its adapter; and the proxy
    adapter reports `live`, because a model really answered. The composition root translates,
    and it is the only place that knows both the transport and the run.
    """

    def test_proxy_transport_records_a_live_run(self) -> None:
        from auditmanager.bootstrap.composition import _provenance_mode

        assert _provenance_mode("proxy") == "live"
        assert _provenance_mode("live") == "live"
        assert _provenance_mode("recorded") == "recorded"

    def test_the_proxy_adapter_reports_live(self) -> None:
        from auditmanager.analysis.text import ProxyAdapter, ProxySettings

        adapter = ProxyAdapter(ProxySettings(base_url="https://p", token="t"))
        assert adapter.provider_mode.value == "live", (
            "if this ever said 'proxy', the database would refuse every run"
        )

    def test_proxy_mode_without_a_token_is_refused_at_startup(self) -> None:
        env = _base_env() | {
            PROVIDER_MODE_ENV: "proxy",
            "PROXY_LLM_BASE_URL": "https://proxy.example",
        }
        env.pop("PROXY_LLM_TOKEN", None)
        with pytest.raises(ConfigurationError, match="PROXY_LLM_TOKEN"):
            build_application(environ=env)

    def test_proxy_mode_without_a_base_url_is_refused_at_startup(self) -> None:
        env = _base_env() | {PROVIDER_MODE_ENV: "proxy", "PROXY_LLM_TOKEN": "t"}
        env.pop("PROXY_LLM_BASE_URL", None)
        with pytest.raises(ConfigurationError, match="PROXY_LLM_BASE_URL"):
            build_application(environ=env)

    def test_a_proxied_application_wires_all_twelve_operations(self) -> None:
        env = _base_env() | {
            PROVIDER_MODE_ENV: "proxy",
            "PROXY_LLM_BASE_URL": "https://proxy.example",
            "PROXY_LLM_TOKEN": "t",
        }
        app = build_application(environ=env)
        assert len(app.router.routes) == 12
        assert app.settings.provider_mode == "proxy"


class TestTheInjectedEnvironmentGovernsTheWholeWiring:
    """An ``environ`` handed to ``build_application`` must reach every part it builds.

    ``W5CERT-DEF-2``: ``_build_provider`` reached for ``os.environ`` directly, so an
    injected environment set ``AppSettings`` and the provider then enforced whatever the
    *process* said. `W5-CERT` proved the consequence with a live run — a ceiling of 0.01
    passed through ``environ`` published a run that spent 0.0387, while the same value in
    the process environment failed it as ``cost_budget_exceeded``.

    The root's own README calls it "every accepted module constructed from configuration".
    Half of it was constructed from a different configuration.
    """

    def test_the_wired_provider_takes_its_ceiling_from_the_injected_environment(
        self,
    ) -> None:
        app = build_application(
            environ=_base_env() | {COST_CEILING_ENV: "0.01", PROVIDER_MODE_ENV: "recorded"}
        )
        assert app.settings.run_cost_ceiling_usd == 0.01
        assert app.provider_config.run_cost_ceiling_usd == 0.01, (
            "the provider enforces the ceiling; if it reads a different environment from "
            "the one that produced AppSettings, the ceiling a caller set is not the "
            "ceiling the run obeys"
        )

    def test_the_two_halves_cannot_disagree(self) -> None:
        """The property, not the instance: whatever the ceiling, both halves report it.

        `tests/conftest.py` strips `AUDITMANAGER_RUN_COST_CEILING_USD` from the process
        environment for the whole session, so under the defect both halves quietly fell
        back to the same 1.00 default and looked consistent. A test pinning 1.00 would
        have passed against the defect. These values are ones the process does not carry.
        """
        for ceiling in ("0.25", "2.50"):
            app = build_application(
                environ=_base_env()
                | {COST_CEILING_ENV: ceiling, PROVIDER_MODE_ENV: "recorded"}
            )
            assert app.settings.run_cost_ceiling_usd == float(ceiling)
            assert app.provider_config.run_cost_ceiling_usd == float(ceiling)

    def test_the_case_really_does_discriminate(self) -> None:
        """The process environment must not carry the ceiling, or the guards above are
        vacuous: both halves would agree by accident rather than by wiring."""
        assert COST_CEILING_ENV not in os.environ, (
            "the process carries the ceiling, so reading the wrong environment would "
            "still produce the right number and the guards above would prove nothing"
        )
