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
