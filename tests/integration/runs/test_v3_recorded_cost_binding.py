"""The recorded provider binding of an AR v3 beta Run is unmetered; no other binding is (`PROD-11C`).

`D-225` piece 2. The AR v3 worker refuses, after the provider call, a call whose cost is neither an
amount nor an explicit ``unmetered`` (``_check_completed_cost``, `AR-V3-BETA-COST-REFUSAL-01`). A
replayed reply carries no amount, so the stock recorded composition could not publish a recorded v3
Run. The composition root now hands the AR v3 beta Runs of a **recorded** process a binding that says
the replay is unmetered. This module holds the two halves of that statement:

* the recorded composition says it, for the exact sealed v3 pair and nobody else (a v1 Run keeps the
  pin estimate its recorded calls have always had);
* nothing else can say it: the live and the proxy compositions build a binding that is not unmetered
  for every Run, and ``EnvironmentProviders`` refuses, at construction, to carry a "charges nothing"
  binding for an adapter that is not a recorded replay.

Container-free: ``settings.load`` reads a mapping and ``_build_provider`` constructs adapters without
calling them. The end-to-end half (a live-mode call without a cost amount is still refused, on a
real database) is `test_v3_saved_text_layer_probe.py`, facts 3 and 3b.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.analysis.text import CallBinding, ProviderMode, RecordedAdapter
from auditmanager.bootstrap.composition import _build_provider
from auditmanager.bootstrap.providers import EnvironmentProviders, UnboundAdapter
from auditmanager.bootstrap.settings import load
from auditmanager.shared.errors import DomainError

BASE = {
    "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:9/d", "S3_ENDPOINT_URL": "http://127.0.0.1:9",
    "S3_REGION": "r", "S3_ACCESS_KEY_ID": "a", "S3_SECRET_ACCESS_KEY": "b", "S3_BUCKET": "c",
    "AUDITMANAGER_API_TOKEN": "token",
}
PROXY = {"AUDITMANAGER_PROVIDER_MODE": "proxy", "PROXY_LLM_BASE_URL": "https://p.example/agent/v1",
         "PROXY_LLM_TOKEN": "tok", "PROXY_LLM_MODEL": "anthropic/claude-opus-5"}
#: Not a credential; the stock live composition refuses to be built without some key.
LIVE = {"AUDITMANAGER_PROVIDER_MODE": "live", "ANTHROPIC_API_KEY": "placeholder-not-a-credential"}
API_ROLE = {"EXECUTION_ROLE": "api", "AUDITMANAGER_PROVIDER_MODE": "recorded"}

V3_PROFILE, V3_BUNDLE = str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID)
RUNS = {
    "v3 beta pair": (V3_PROFILE, V3_BUNDLE),
    "v1 profile": ("ap_01M5M28ZCDD8VPSP1BTAEW92YF", "pb_01M5M28ZCDVCR37BX1884JGSPN"),
    "v3 profile, other bundle": (V3_PROFILE, "pb_01M5M28ZCDVCR37BX1884JGSPN"),
    "other profile, v3 bundle": ("ap_01M5M28ZCDD8VPSP1BTAEW92YF", V3_BUNDLE),
}


def _run(profile: str, bundle: str, revision: str | None = None) -> Any:
    return SimpleNamespace(analysis_profile_id=profile, prompt_bundle_id=bundle,
                           connection_revision_id=revision)


def _source(extra: dict[str, str]) -> tuple[Any, Any]:
    environ = {**BASE, **extra}
    adapter, _config, _profile, _bundle, source = _build_provider(load(environ), environ)
    return adapter, source


def _call(extra: dict[str, str], run: Any) -> Any:
    return _source(extra)[1].resolve(None, run, None).call  # type: ignore[arg-type]


def test_the_recorded_composition_marks_the_replay_unmetered_for_the_sealed_v3_pair() -> None:
    adapter, source = _source({})
    assert type(adapter) is RecordedAdapter
    bound = source.resolve(None, _run(V3_PROFILE, V3_BUNDLE), None)  # type: ignore[arg-type]
    assert bound.adapter is adapter
    assert bound.call is not None and bound.call.unmetered is True
    assert bound.call.provider_label == "anthropic"
    assert bound.call.connection_revision_id is None and bound.call.identity_basis is None


@pytest.mark.parametrize("label", [name for name in RUNS if name != "v3 beta pair"])
def test_a_recorded_run_that_is_not_the_exact_v3_pair_keeps_the_binding_it_always_had(
    label: str,
) -> None:
    """A v1 Run's recorded calls are priced from the pin table; marking them unmetered would change
    every recorded cost report and the characterisation corpora. A half-matching pair is refused by
    the executor before any call, and gets no mark here either."""
    assert _call({}, _run(*RUNS[label])) is None


@pytest.mark.parametrize("label", list(RUNS))
@pytest.mark.parametrize("extra,name", ((PROXY, "proxy"), (LIVE, "live"), (API_ROLE, "api role")))
def test_no_other_composition_builds_an_unmetered_binding_for_any_run(
    extra: dict[str, str], name: str, label: str
) -> None:
    """The cost safety. The live and the proxy compositions hold the reply to a pinned model and
    leave the cost to the reply (``unmetered`` false, so a call with no amount is refused by the
    worker); the api role builds no call binding at all."""
    call = _call(extra, _run(*RUNS[label]))
    if name == "api role":
        assert call is None
        return
    assert isinstance(call, CallBinding)
    assert call.unmetered is False
    assert call.check_identity is True and call.expected_model


def test_the_live_and_the_proxy_adapters_are_not_recorded_replays() -> None:
    """The premise of the guard below: the compositions above really build live-mode adapters."""
    for extra in (PROXY, LIVE):
        adapter, _source_ = _source(extra)
        assert adapter.provider_mode is ProviderMode.LIVE
    assert _source(API_ROLE)[0].provider_mode is ProviderMode.LIVE


@pytest.mark.parametrize("make", (
    lambda: _source(PROXY)[0],
    lambda: _source(LIVE)[0],
    lambda: UnboundAdapter(),
    lambda: SimpleNamespace(provider_mode=ProviderMode.LIVE),
    lambda: SimpleNamespace(),
    lambda: None,
), ids=("proxy adapter", "live adapter", "unbound adapter", "any live-mode adapter",
        "adapter without a mode", "no adapter"))
def test_a_binding_that_charges_nothing_is_refused_for_an_adapter_that_is_not_a_recorded_replay(
    make: Any,
) -> None:
    with pytest.raises(ValueError, match="recorded adapter only"):
        EnvironmentProviders(make(), object(), None, ar_v3_replay_call=CallBinding(unmetered=True))


def test_the_replay_binding_must_itself_be_unmetered_and_a_recorded_adapter_accepts_it() -> None:
    with pytest.raises(ValueError, match="explicitly unmetered"):
        EnvironmentProviders(RecordedAdapter(), object(), None, ar_v3_replay_call=CallBinding())
    source = EnvironmentProviders(
        RecordedAdapter(), object(), None, ar_v3_replay_call=CallBinding(unmetered=True))
    assert source.resolve(None, _run(*RUNS["v3 beta pair"]), None).call.unmetered is True  # type: ignore[arg-type]
    assert source.resolve(None, _run(*RUNS["v1 profile"]), None).call is None  # type: ignore[arg-type]


def test_a_source_built_without_the_replay_binding_marks_nothing() -> None:
    """The default is the old behaviour: a caller that does not ask gets no mark, for any Run."""
    source = EnvironmentProviders(RecordedAdapter(), object(), None)
    for label in RUNS:
        assert source.resolve(None, _run(*RUNS[label]), None).call is None  # type: ignore[arg-type]


def test_a_run_that_froze_a_connection_is_still_refused_whatever_its_profile() -> None:
    """The route check stays first: the replay binding never serves a run bound to a revision."""
    _adapter, source = _source({})
    run = _run(V3_PROFILE, V3_BUNDLE, revision="excr_01J00000000000000000000000")
    with pytest.raises(DomainError) as refused:
        source.resolve(None, run, None)  # type: ignore[arg-type]
    assert refused.value.code.value == "dependency_unavailable"
