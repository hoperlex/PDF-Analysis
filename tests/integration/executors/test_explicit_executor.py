"""`EXEC-PAR-START-01` on real PostgreSQL: a run names its executor, and a repeat keeps it.

Same fixtures as ``test_http_run_path.py`` (real database, the executors context's own commands to
seed connections). The container-free counterpart, which proves the same rules over fakes that
record what they were asked, is ``tests/unit/executors/test_explicit_executor.py`` and
``tests/unit/runs/test_executor_choice.py``. What only a database can show is here:

* a named start freezes the named connection's **current** revision although the route names
  another, writes one ``audit_run.executor_chosen`` event and the run's status says which
  executor it is on;
* a run without a choice has no such event and still reports the route's connection it froze;
* every refusal (unknown, archived, unprobed, key rotated since the probe) leaves **no** run, no
  command record and no event, with a usable route and standby right there;
* the same key with another executor is ``idempotency_key_reuse``; with the same one, a replay;
* a repeat of a named run freezes the named connection and not today's route, journals the choice
  again, and is refused -- not redirected -- once that connection is archived or unprobed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.bootstrap.adapters import _run_status_view
from auditmanager.bootstrap.providers import DatabaseProviders
from auditmanager.executors.public import ExecutorRepository, archive_connection
from auditmanager.runs import start_audit_run
from auditmanager.runs.commands import cancel_audit_run, reaudit_run
from auditmanager.shared.errors import DomainError, ErrorCode

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)
engine = harness.engine
session = harness.session
seeded = harness.seeded
new_key = harness.new_key

_SUPPORT_NAME = "am_exec_http_support"
_SUPPORT_PATH = Path(__file__).resolve().parent / "http_support.py"
if _SUPPORT_NAME in sys.modules:
    support = sys.modules[_SUPPORT_NAME]
else:
    _s = importlib.util.spec_from_file_location(_SUPPORT_NAME, _SUPPORT_PATH)
    assert _s is not None and _s.loader is not None
    support = importlib.util.module_from_spec(_s)
    sys.modules[_SUPPORT_NAME] = support
    _s.loader.exec_module(support)

FakeGateway = support.fake_gateway.FakeGateway
LIVE = ProviderConfig(
    mode=ProviderMode.LIVE, model_id=support.PIN.model_id, run_cost_ceiling_usd=1.0, api_key=None,
    ceiling_is_explicit=True,
)
ADMIN = frozenset({"admin"})
CHOSEN = "audit_run.executor_chosen"


def _providers(rings: Any) -> DatabaseProviders:
    return DatabaseProviders(
        ring=rings.private, policy=None, base_config=LIVE, ceiling_usd=1.0,  # type: ignore[arg-type]
    )


def _start(session: Any, seeded: Any, key: str, providers: DatabaseProviders, **named: Any) -> Any:
    return start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live", idempotency_key=key,
        connection_route=providers.freeze, **named,
    )


def _frozen(session: Any, run_id: str) -> str | None:
    return session.execute(text(
        "SELECT connection_revision_id FROM audit_run WHERE run_id = :r"), {"r": run_id}).scalar_one()


def _chosen_events(session: Any, run_id: str) -> list[dict[str, Any]]:
    return list(session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = :t AND aggregate_id = :r"),
        {"t": CHOSEN, "r": run_id}).scalars().all())


def _counts(session: Any) -> tuple[int, int, int]:
    return tuple(session.execute(text(sql)).scalar_one() for sql in (  # type: ignore[return-value]
        "SELECT count(*) FROM audit_run", "SELECT count(*) FROM command_record",
        "SELECT count(*) FROM audit_event",
    ))


def _terminal(session: Any, run_id: str) -> None:
    """A source a repeat may start from: cancelled (a created run is cancellable and terminal
    afterwards), so no model call is needed to make the run terminal."""
    cancel_audit_run(session, run_id=run_id, roles=ADMIN, idempotency_key=support.unique())


def test_a_named_start_freezes_that_connection_not_the_route_and_the_status_says_so(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        routed = support.seed_connection(session, rings, fake.base_url(), name="Маршрут")
        named = support.seed_connection(session, rings, fake.base_url("/b"), name="Выбранный", routed=False)
        providers = _providers(rings)

        chosen = _start(session, seeded, new_key("named"), providers,
                        executor_connection_id=named.connection_id)
        followed = _start(session, seeded, new_key("routed"), providers)

        assert _frozen(session, chosen.run_id) == named.revision_id != routed.revision_id
        assert _frozen(session, followed.run_id) == routed.revision_id
        (event,) = _chosen_events(session, chosen.run_id)
        assert event == {
            "run_id": chosen.run_id, "connection_id": named.connection_id,
            "revision_id": named.revision_id,
        }
        assert _chosen_events(session, followed.run_id) == [], "no choice, no event"
        view = _run_status_view(session, chosen.run_id)
        assert (view.executor.connection_id, view.executor.display_name, view.executor.pin_id) == (
            named.connection_id, "Выбранный", support.PIN.model_id)
        assert _run_status_view(session, followed.run_id).executor.connection_id == routed.connection_id
    finally:
        fake.stop()


def test_a_named_start_takes_the_current_revision_not_the_one_the_route_was_probed_on(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        named = support.seed_connection(session, rings, fake.base_url(), routed=False)
        later = support.revise(session, named.connection_id, fake.base_url("/moved"))
        support.mark_probe(session, named.connection_id)
        started = _start(session, seeded, new_key("current"), _providers(rings),
                         executor_connection_id=named.connection_id)
        assert _frozen(session, started.run_id) == later != named.revision_id
    finally:
        fake.stop()


@pytest.mark.parametrize("how", ["unknown", "archived", "unprobed", "revised_unprobed", "probe_failed"])
def test_a_connection_that_cannot_serve_refuses_the_start_and_writes_nothing(
    session, seeded, new_key, how: str  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        # A usable primary and standby, so a fallback would have somewhere to go.
        primary = support.seed_connection(session, rings, fake.base_url(), name="primary")
        standby = support.seed_connection(session, rings, fake.base_url("/s"), name="standby", routed=False)
        support.route(session, primary.connection_id, standby.connection_id)
        providers = _providers(rings)
        if how == "unknown":
            target, expected = "exc_01M2545JSD15ETSNNV904X991N", ErrorCode.VALIDATION_FAILED
        else:
            seeded_connection = support.seed_connection(
                session, rings, fake.base_url("/x"), name=how, routed=False,
                probe=None if how == "unprobed" else ("credential_refused" if how == "probe_failed" else "ok"))
            target, expected = seeded_connection.connection_id, ErrorCode.DEPENDENCY_UNAVAILABLE
            if how == "revised_unprobed":
                support.revise(session, target, fake.base_url("/y"))
            if how == "archived":
                archive_connection(session, connection_id=target, roles=support.ADMIN_ROLES,
                                   idempotency_key=support.unique(), actor_uid=support.ACTOR)
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _start(session, seeded, new_key(how), providers, executor_connection_id=target)
        assert refused.value.code is expected
        assert _counts(session) == before, "no run, no command record, no event"
    finally:
        fake.stop()


def test_the_same_key_with_another_executor_is_a_conflict_and_with_the_same_one_a_replay(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        first = support.seed_connection(session, rings, fake.base_url(), name="first")
        second = support.seed_connection(session, rings, fake.base_url("/2"), name="second", routed=False)
        providers = _providers(rings)
        key = new_key("idempotent")
        started = _start(session, seeded, key, providers, executor_connection_id=first.connection_id)
        runs_before = _counts(session)[0]

        replay = _start(session, seeded, key, providers, executor_connection_id=first.connection_id)
        assert (replay.replayed, replay.run_id) == (True, started.run_id)
        for other in (second.connection_id, None):
            with pytest.raises(DomainError) as conflict:
                _start(session, seeded, key, providers, executor_connection_id=other)
            assert conflict.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert _counts(session)[0] == runs_before
        assert len(_chosen_events(session, started.run_id)) == 1, "a replay journals nothing more"
    finally:
        fake.stop()


def test_a_repeat_of_a_named_run_keeps_the_executor_and_is_refused_once_it_cannot_serve(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        route_one = support.seed_connection(session, rings, fake.base_url(), name="route one")
        named = support.seed_connection(session, rings, fake.base_url("/n"), name="named", routed=False)
        providers = _providers(rings)
        source = _start(session, seeded, new_key("source"), providers,
                        executor_connection_id=named.connection_id)
        _terminal(session, source.run_id)
        # The route moves on: today's route is no longer the named connection (nor the first).
        route_two = support.seed_connection(session, rings, fake.base_url("/r2"), name="route two")

        def repeat(label: str) -> Any:
            return reaudit_run(
                session, source_run_id=source.run_id, roles=ADMIN, idempotency_key=new_key(label),
                provider_mode="live", connection_route=providers.freeze,
                analysis_profile_id=seeded.analysis_profile_id,
                prompt_bundle_id=seeded.prompt_bundle_id, input_budget_characters=10**9,
            )

        again = repeat("repeat-1")
        assert _frozen(session, again.run_id) == named.revision_id != route_two.revision_id
        (event,) = _chosen_events(session, again.run_id)
        assert event["connection_id"] == named.connection_id, "so the repeat's own repeat keeps it"

        # The named connection loses its probe (a new revision): the repeat is refused.
        support.revise(session, named.connection_id, fake.base_url("/n2"))
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            repeat("repeat-2")
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert _counts(session) == before, "refused, not redirected to the route"
        assert ExecutorRepository().get_connection(session, route_one.connection_id) is not None
    finally:
        fake.stop()


def test_a_repeat_of_a_run_that_followed_the_route_follows_todays_route(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = FakeGateway().start()
    try:
        support.seed_connection(session, rings, fake.base_url(), name="route one")
        providers = _providers(rings)
        source = _start(session, seeded, new_key("routed-source"), providers)
        _terminal(session, source.run_id)
        route_two = support.seed_connection(session, rings, fake.base_url("/r2"), name="route two")
        again = reaudit_run(
            session, source_run_id=source.run_id, roles=ADMIN, idempotency_key=new_key("routed-repeat"),
            provider_mode="live", connection_route=providers.freeze,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id, input_budget_characters=10**9,
        )
        assert _frozen(session, again.run_id) == route_two.revision_id
        assert _chosen_events(session, again.run_id) == []
    finally:
        fake.stop()
