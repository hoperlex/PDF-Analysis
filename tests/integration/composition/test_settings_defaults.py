"""The per-run cost ceiling's default, pinned to the owner's decision.

`W10-API`'s sweep of `bootstrap/settings.py` found eight of nine rules guarded by
`test_composition_root.py`: the declared-mode set, a non-positive ceiling, an unparseable
ceiling, the proxy base URL, the proxy token, the live credential and every required
value all redden. One did not.

Changing the **default** ceiling from `"1.00"` to `"99.00"` left all 816 tests green.
`tests/conftest.py` strips `AUDITMANAGER_RUN_COST_CEILING_USD` from the process
environment for the whole session, and every existing test that cares about the ceiling
sets one explicitly -- deliberately, because `W5CERT-DEF-2` was found by values the
process does not carry. So the value a process uses when nobody sets one was never
asserted.

That default is not an implementation detail. `docs/program/P02_LOCK.json` records it as
**`OD-03`**, a repository-owner decision of 2026-09-11: "Per-run cost ceiling: USD 1.00 ...
A run over the eight-page corpus costs roughly $0.20 at the recorded rates, so the ceiling
carries about five times headroom". A default of 99.00 is a hundredfold change to the
amount an unconfigured process may spend on one run, and nothing would have said so.

Pinned against the lock file, read from this file's own location, rather than against the
module's own string.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from auditmanager.bootstrap.settings import (
    COST_CEILING_ENV,
    MODEL_ID_ENV,
    PROVIDER_MODE_ENV,
    PROXY_MODEL_ENV,
    load,
)

LOCK = Path(__file__).resolve().parents[3] / "docs/program/P02_LOCK.json"


def _base_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()}
    assert env.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return env


def _declared_ceiling() -> float:
    return json.loads(LOCK.read_text(encoding="utf-8"))["models"]["run_cost_ceiling_usd"]


def test_the_lock_file_records_the_owner_s_ceiling() -> None:
    """`OD-03`. Written out as well as read, so a change to the lock is visible here."""
    assert _declared_ceiling() == 1.0


def test_the_case_discriminates() -> None:
    """If the process carried a ceiling, the assertion below would pass whatever the
    module's default was. `tests/conftest.py` strips it; this checks that it did."""
    assert COST_CEILING_ENV not in os.environ, (
        "the process carries a ceiling, so the default cannot be observed here"
    )


def test_an_unconfigured_process_uses_the_ceiling_the_owner_decided() -> None:
    env = _base_env()
    env.pop(COST_CEILING_ENV, None)
    assert load(env).run_cost_ceiling_usd == _declared_ceiling()


def test_an_empty_ceiling_falls_back_to_the_same_value_not_to_zero() -> None:
    """`env.get(..., "1.00").strip() or "1.00"` has two arms and both must land on the
    decided value. An empty string reaching `float()` would be a startup crash, and one
    falling through to `0` would be a ceiling that refuses every run."""
    env = _base_env() | {COST_CEILING_ENV: "   "}
    assert load(env).run_cost_ceiling_usd == _declared_ceiling()


def test_an_explicit_ceiling_still_wins() -> None:
    """The default must not be applied over a configured value."""
    env = _base_env() | {COST_CEILING_ENV: "0.25"}
    assert load(env).run_cost_ceiling_usd == 0.25


class TestTheModelDefaults:
    """Two more defaults the sweep found unreachable.

    Changing `model_id`'s default from `"claude-opus-5"` to another name, and
    `proxy_model`'s from `"proxy"` to a real model id, each left all 816 tests green.
    Both are set by `env.get(NAME, "").strip() or <default>`, and no test runs `load`
    without those names present or asserts what comes back when they are absent.
    """

    def test_the_model_id_default_is_the_model_the_lock_pins(self) -> None:
        """`P02_LOCK.json` records `models.primary.model_id` together with the rates
        `run_cost_ceiling_usd` was sized against -- USD 5.00 and 25.00 per million
        tokens. A default that drifted from the pinned model would price runs against a
        table that no longer describes them, which is the ceiling's whole basis."""
        pinned = json.loads(LOCK.read_text(encoding="utf-8"))["models"]["primary"]
        assert pinned["model_id"] == "claude-opus-5"
        env = _base_env()
        env.pop(MODEL_ID_ENV, None)
        assert load(env).model_id == pinned["model_id"]

    def test_an_explicit_model_id_still_wins(self) -> None:
        env = _base_env() | {MODEL_ID_ENV: "claude-sonnet-5"}
        assert load(env).model_id == "claude-sonnet-5"

    def test_an_empty_model_id_falls_back_rather_than_being_sent_empty(self) -> None:
        env = _base_env() | {MODEL_ID_ENV: "  "}
        assert load(env).model_id == "claude-opus-5"

    def test_the_proxy_model_default_is_the_stub_not_a_model_name(self) -> None:
        """`"proxy"` is a sentinel, not a model. The module says so: it is "the stub the
        proxy reads as 'I am not choosing a model', so the operator's default and its
        fallback chain apply. Any other value is a real choice that changes routing and
        billing and switches the fallback chain off."

        No external authority declares this string -- it is an agreement with the proxy
        -- so the literal is written here. That a real model id must **not** be the
        default is the property, and it is asserted as well as the value.
        """
        env = _base_env() | {
            PROVIDER_MODE_ENV: "proxy",
            "PROXY_LLM_BASE_URL": "https://proxy.example",
            "PROXY_LLM_TOKEN": "t",
        }
        env.pop(PROXY_MODEL_ENV, None)
        settings = load(env)
        assert settings.proxy_model == "proxy"
        assert settings.proxy_model != settings.model_id, (
            "the proxy default names a real model, so the operator's fallback chain is "
            "switched off for every run that did not choose one"
        )

    def test_an_explicit_proxy_model_still_wins(self) -> None:
        env = _base_env() | {
            PROVIDER_MODE_ENV: "proxy",
            "PROXY_LLM_BASE_URL": "https://proxy.example",
            "PROXY_LLM_TOKEN": "t",
            PROXY_MODEL_ENV: "claude-sonnet-5",
        }
        assert load(env).proxy_model == "claude-sonnet-5"
