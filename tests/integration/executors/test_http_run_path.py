"""The run path through a connection (`EXEC-HTTP-01`, plan section 3): freeze, bind, record.

Real PostgreSQL and S3, and a local OpenAI-compatible gateway; no paid call. A run is started with
the provider source ``database``: it freezes the route's revision, ``execute_run`` binds that
revision's adapter at its Attempt, and every call row names the revision. The ``environment``
regression at the end shows the other source unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.bootstrap.providers import DatabaseProviders, EnvironmentProviders, UnboundAdapter
from auditmanager.executors.public import ExecutorRepository, archive_connection
from auditmanager.executors.runtime import DestinationPolicy, bind_connection, freeze_connection
from auditmanager.runs import RunRepository, execute_run, start_audit_run
from auditmanager.runs.commands import reaudit_run
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import ModelCallId
from tests.support.v1_reference_profile import resolve_reference_profile

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
blob_store = harness.blob_store
seeded = harness.seeded
new_key = harness.new_key
recorded_adapter = harness.recorded_adapter
provider_config = harness.provider_config

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
RECORDINGS = Path(__file__).resolve().parents[3] / "fixtures/recorded/text_analysis"
RECORDING = json.loads(next(RECORDINGS.glob("*.json")).read_text("utf-8"))
LIVE = ProviderConfig(
    mode=ProviderMode.LIVE, model_id=support.PIN.model_id, run_cost_ceiling_usd=1.0, api_key=None,
    ceiling_is_explicit=True,
)
ADMIN = frozenset({"admin"})


def _providers(rings: Any, fake: Any, **overrides: Any) -> DatabaseProviders:
    return DatabaseProviders(
        ring=overrides.pop("ring", rings.private), policy=overrides.pop("policy", fake.policy()),
        base_config=LIVE, ceiling_usd=1.0,
    )


def _start(session: Any, seeded: Any, new_key: Any, label: str, providers: DatabaseProviders) -> Any:
    return start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live",
        idempotency_key=new_key(label), connection_route=providers.freeze,
    )


def _execute(session: Any, blob_store: Any, run_id: str, providers: Any) -> Any:
    return execute_run(
        session, run_id, blob_store=blob_store, adapter=UnboundAdapter(), provider_config=LIVE,
        providers=providers.resolve,
        text_profiles=resolve_reference_profile,
    )


def _rows(session: Any, run_id: str) -> dict[str, Any]:
    one = lambda sql: [dict(r) for r in session.execute(text(sql), {"r": run_id}).mappings()]  # noqa: E731
    return {
        "run": one("SELECT * FROM audit_run WHERE run_id = :r")[0],
        "calls": one("SELECT * FROM model_call WHERE run_id = :r"),
        "effects": one("SELECT * FROM provider_call_effect WHERE run_id = :r"),
        "stage": one("SELECT * FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'")[0],
    }


def test_a_run_goes_through_the_frozen_connection_and_every_call_row_names_it(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    cost = (RECORDING["usage"]["input_tokens"] * support.PIN.input_per_mtok_usd
            + RECORDING["usage"]["output_tokens"] * support.PIN.output_per_mtok_usd) / 1e6
    fake = gateway_for(cost)
    try:
        connection = support.seed_connection(session, rings, fake.base_url())
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "http-ok", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()

    assert result.terminal_state == "published" and result.published_finding_count > 0
    assert rows["run"]["connection_revision_id"] == connection.revision_id, "frozen at start"
    (call,), (effect,) = rows["calls"], rows["effects"]
    for row in (call, effect):
        assert row["connection_revision_id"] == connection.revision_id
        assert (row["identity_basis"], row["provider"]) == ("reported", "openai_chat")
    assert (call["cost_basis"], effect["state"]) == ("measured", "completed")
    (sent,) = fake.requests
    assert sent["body"]["model"] == support.GATEWAY_MODEL, "the gateway name is sent, not the pin id"
    assert sent["authorization"] == f"Bearer {support.KEY}"
    cost_row = RunRepository().cost(session, started.run_id)
    assert (cost_row.model_call_count, cost_row.basis) == (1, "measured") and cost_row.cost_micros > 0


def gateway_for(cost: float | None, **options: Any) -> Any:
    options.setdefault("content", RECORDING["output_text"])
    options.setdefault("input_tokens", RECORDING["usage"]["input_tokens"])
    options.setdefault("output_tokens", RECORDING["usage"]["output_tokens"])
    return FakeGateway(cost=cost, **options).start()


def test_an_unmetered_connection_reports_cost_zero_basis_unmetered_and_the_call_count(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        support.seed_connection(session, rings, fake.base_url(), billing="not_metered")
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "http-unmetered", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "published"
    (call,) = rows["calls"]
    assert (call["cost_basis"], call["cost_micros"]) == ("unmetered", 0)
    cost = RunRepository().cost(session, started.run_id)
    assert (cost.model_call_count, cost.cost_micros, cost.basis) == (1, 0, "unmetered")
    assert rows["stage"]["metrics"]["cost_basis"] == "unmetered"


def test_the_run_level_cost_rule_in_sql_covers_unmetered_mixed_and_measured(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    from auditmanager.dashboard.repository import _SPEND, DashboardRepository, spend_record

    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        support.seed_connection(session, rings, fake.base_url(), billing="not_metered")
        providers = _providers(rings, fake)
        run_id = _start(session, seeded, new_key, "http-mix", providers).run_id
        _execute(session, blob_store, run_id, providers)
    finally:
        fake.stop()
    def add(basis: str, micros: int | None) -> None:
        session.execute(text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, "
            "provider_mode, parameters, request_sha256, response_sha256, input_tokens, "
            "output_tokens, latency_ms, cost_micros, cost_basis, status) VALUES (:id, :r, "
            "'text_analysis', 'openai_chat', 'm', 'live', '{}'::jsonb, repeat('a', 64), repeat('b', 64), 1, 1, 1, :c, :b, "
            "'succeeded')"), {"id": str(ModelCallId.new()), "r": run_id, "c": micros, "b": basis})

    def dashboard_spend() -> Any:
        """The dashboard's own SQL and rule, restricted to this run."""
        row = session.execute(text(str(_SPEND) + " WHERE run_id = :r"), {"r": run_id}).one()
        return spend_record(*tuple(row))

    # Only unmetered: zero, unmetered, the count -- on the run and on the aggregate alike.
    only = RunRepository().cost(session, run_id)
    assert (only.model_call_count, only.cost_micros, only.basis) == (1, 0, "unmetered")
    spend = dashboard_spend()
    assert (spend.model_call_count, spend.cost_micros, spend.basis) == (1, 0, "unmetered")
    # A metered call beside it: the metered sum, estimated -- a total that leaves calls out
    # is not a measurement of the run.
    add("measured", 123_000)
    mixed = RunRepository().cost(session, run_id)
    assert (mixed.model_call_count, mixed.cost_micros, mixed.basis) == (2, 123_000, "estimated")
    spend = dashboard_spend()
    assert (spend.model_call_count, spend.cost_micros, spend.basis) == (2, 123_000, "estimated")
    # The deployment-wide query answers without error and is never 'measured' while this
    # run's unmetered call is in it.
    overall = DashboardRepository().summary(session).run_spend
    assert overall is not None and overall.basis != "measured"
    assert spend_record(0, 0, 0, 0) is None, "no call at all is nothing to report, not a zero"


def test_with_no_usable_route_the_start_is_refused_and_nothing_is_written(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        providers = _providers(rings, fake)
        runs_before = session.execute(text("SELECT count(*) FROM audit_run")).scalar_one()
        # No route at all.
        with pytest.raises(DomainError) as refused:
            _start(session, seeded, new_key, "no-route", providers)
        assert refused.value.code.value == "dependency_unavailable"
        assert "executor_route_missing" in str(refused.value.detail_fields)
        # A route to a connection that has not passed a probe cannot even be set; a route to one
        # whose revision changed afterwards makes the start refuse until it is probed again.
        connection = support.seed_connection(session, rings, fake.base_url())
        support.revise(session, connection.connection_id, fake.base_url("/v2"))
        with pytest.raises(DomainError) as unprobed:
            _start(session, seeded, new_key, "unprobed", providers)
        assert "executor_route_missing" in str(unprobed.value.detail_fields)
        assert session.execute(text("SELECT count(*) FROM audit_run")).scalar_one() == runs_before
        support.set_key(session, rings, connection.connection_id)
        support.mark_probe(session, connection.connection_id)
        assert _start(session, seeded, new_key, "probed-again", providers).replayed is False
    finally:
        fake.stop()


def test_the_standby_serves_only_at_run_start_when_the_primary_is_unusable_and_the_use_is_journaled(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        primary = support.seed_connection(session, rings, fake.base_url(), name="primary")
        standby = support.seed_connection(session, rings, fake.base_url("/b"), name="standby",
                                          routed=False)
        support.route(session, primary.connection_id, standby.connection_id)
        providers = _providers(rings, fake)
        first = _start(session, seeded, new_key, "standby-not-needed", providers)
        row = session.execute(text(
            "SELECT connection_revision_id FROM audit_run WHERE run_id = :r"), {"r": first.run_id}).scalar_one()
        assert row == primary.revision_id, "a usable primary is always chosen"
        # The primary's address changes: its new revision is unprobed, so the standby serves.
        support.revise(session, primary.connection_id, fake.base_url("/moved"))
        second = _start(session, seeded, new_key, "standby-used", providers)
        frozen = session.execute(text(
            "SELECT connection_revision_id FROM audit_run WHERE run_id = :r"), {"r": second.run_id}).scalar_one()
        assert frozen == standby.revision_id
        events = session.execute(text(
            "SELECT payload FROM audit_event WHERE event_type = 'audit_run.standby_used' "
            "AND payload->>'run_id' = :r"), {"r": second.run_id}).scalars().all()
        assert len(events) == 1
        assert events[0]["reason"] == "primary_not_probed"
        assert events[0]["standby_connection_id"] == standby.connection_id
        none_for_first = session.execute(text(
            "SELECT count(*) FROM audit_event WHERE event_type = 'audit_run.standby_used' "
            "AND payload->>'run_id' = :r"), {"r": first.run_id}).scalar_one()
        assert none_for_first == 0
    finally:
        fake.stop()


def test_a_revision_changed_or_archived_after_the_freeze_still_serves_the_run(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        first = support.seed_connection(session, rings, fake.base_url(), name="first", billing="not_metered")
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "frozen-then-archived", providers)
        # The route moves to another connection and the first is archived.
        other = support.seed_connection(session, rings, fake.base_url("/other"), name="other")
        archive_connection(session, connection_id=first.connection_id, roles=support.ADMIN_ROLES,
                           idempotency_key=support.unique(), actor_uid=support.ACTOR)
        assert ExecutorRepository().get_connection(session, first.connection_id).archived_at is not None
        assert freeze_connection(session, "text_analysis").connection_id == other.connection_id
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "published"
    assert rows["calls"][0]["connection_revision_id"] == first.revision_id
    assert fake.requests[0]["path"] == "/agent/v1/chat/completions", "the frozen revision's address"


def test_a_rotated_key_is_picked_up_at_the_next_attempt_without_a_new_revision(
    session  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        connection = support.seed_connection(session, rings, fake.base_url())
        context = None
        policy = fake.policy()
        from auditmanager.analysis.public import ModelRequest

        request = ModelRequest(model_id=support.PIN.model_id,
                               body={"max_tokens": 4, "messages": [{"role": "user", "content": "x"}]})
        bound = bind_connection(session, connection.revision_id, ring=rings.private, policy=policy,
                                context=context)
        bound.adapter.complete(request)
        support.set_key(session, rings, connection.connection_id, "sk-rotated-0123456789abcdef")
        again = bind_connection(session, connection.revision_id, ring=rings.private, policy=policy,
                                context=context)
        again.adapter.complete(request)
        assert [r["authorization"] for r in fake.requests] == [
            f"Bearer {support.KEY}", "Bearer sk-rotated-0123456789abcdef"]
        assert again.revision.revision_id == bound.revision.revision_id == connection.revision_id
    finally:
        fake.stop()


def test_a_key_that_cannot_be_opened_fails_the_stage_as_credential_refused_and_calls_nothing(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, wrong = support.make_rings(), support.make_rings("other")
    fake = gateway_for(None)
    try:
        support.seed_connection(session, rings, fake.base_url())
        providers = _providers(rings, fake, ring=wrong.private)
        started = _start(session, seeded, new_key, "unreadable", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "failed"
    error = rows["stage"]["error"]
    assert error["code"] == "dependency_credential_refused"
    assert "secret_unreadable" in error["message"]
    assert fake.requests == [] and rows["calls"] == [] and rows["effects"] == []


def test_the_destination_rules_hold_in_the_call_and_the_effect_is_not_processed(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        # A revision aimed at loopback that carries an ok probe, as a forged row would.
        support.seed_connection(session, rings, f"http://127.0.0.1:{fake.port}/v1")
        providers = _providers(rings, fake, policy=DestinationPolicy(networks=lambda: ()))
        started = _start(session, seeded, new_key, "refused-destination", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "failed"
    (effect,) = rows["effects"]
    assert (effect["state"], effect["dispatch_class"]) == ("not_processed", "not_sent")
    assert fake.requests == []


def test_a_reaudit_freezes_todays_route(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        first = support.seed_connection(session, rings, fake.base_url(), name="first")
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "reaudit-source", providers)
        _execute(session, blob_store, started.run_id, providers)
        second = support.seed_connection(session, rings, fake.base_url("/second"), name="second")
        again = reaudit_run(
            session, source_run_id=started.run_id, roles=ADMIN, idempotency_key=support.unique(),
            provider_mode="live", connection_route=providers.freeze,
            analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        )
        frozen = session.execute(text(
            "SELECT connection_revision_id FROM audit_run WHERE run_id = :r"),
            {"r": again.run_id}).scalar_one()
    finally:
        fake.stop()
    assert frozen == second.revision_id != first.revision_id


def test_a_new_kind_plugs_in_by_registering_a_factory_and_is_handed_the_attempt_context(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    """`EXEC-PULL-01` and `EXEC-SSH-01` change nothing in the run path: they register a factory
    for their kind, and it receives the revision, the opened key and the Attempt's context (the
    run, the Attempt, the call being served, when the watchdog started counting and how long it
    allows). The seam is shown with the ``http_api`` kind wrapped by a recording factory."""
    from auditmanager.executors.kinds import adapter_for, register_adapter_factory
    from auditmanager.jobs.public import ATTEMPT_WATCHDOG_SECONDS

    rings = support.make_rings()
    fake = gateway_for(None)
    original = adapter_for("http_api")
    assert original is not None
    seen: list[Any] = []

    def recording(revision: Any, api_key: str, policy: Any, context: Any) -> Any:
        seen.append((revision, api_key, context))
        return original.factory(revision, api_key, policy, context)

    register_adapter_factory("http_api", recording, purpose=original.purpose,
                             serves=original.serves, provider_label=original.provider_label)
    try:
        connection = support.seed_connection(session, rings, fake.base_url())
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "plug-in", providers)
        _execute(session, blob_store, started.run_id, providers)
        call_id = session.execute(text(
            "SELECT model_call_id FROM model_call WHERE run_id = :r"), {"r": started.run_id}).scalar_one()
        attempt_id = session.execute(text(
            "SELECT attempt_id FROM provider_call_effect WHERE run_id = :r"), {"r": started.run_id}).scalar_one()
    finally:
        register_adapter_factory("http_api", original.factory, purpose=original.purpose,
                                 serves=original.serves, provider_label=original.provider_label)
        fake.stop()
    (revision, key, context), = seen
    assert revision.revision_id == connection.revision_id and key == support.KEY
    assert (context.run_id, context.attempt_id) == (started.run_id, attempt_id)
    assert context.call_id == call_id, "the journal names the call being served"
    assert context.watchdog_seconds == ATTEMPT_WATCHDOG_SECONDS and context.started_monotonic > 0


@pytest.mark.parametrize("flavour,behaviour", [
    ("openai_chat", "wrong_model"), ("openai_chat", "no_model"), ("openai_chat", "stub_model"),
    ("anthropic_messages", "wrong_model"), ("anthropic_messages", "stub_model"),
])
def test_a_reply_from_another_model_fails_the_run_closed_and_publishes_nothing(
    session, seeded, blob_store, new_key, flavour, behaviour  # type: ignore[no-untyped-def]
) -> None:
    """`R-133`, now enforced on the run path for both flavours: the reply is held to the revision's
    gateway name. The answer was received and may have been paid for, so the call is not retried,
    its usage is journaled, no call row is completed and no finding is published."""
    from auditmanager.findings import published_finding_count

    rings = support.make_rings()
    fake = gateway_for(None, behaviour=behaviour)
    try:
        base = fake.base_url("" if flavour == "anthropic_messages" else "/agent/v1")
        support.seed_connection(session, rings, base, api_flavour=flavour)
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, f"mismatch-{flavour}-{behaviour}", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "failed"
    assert rows["stage"]["error"]["code"] == "model_identity_mismatch"
    assert published_finding_count(session, started.run_id) == 0
    assert rows["calls"] == [], "no call row is completed for an answer that is not published"
    (effect,) = rows["effects"]
    assert effect["state"] == "response_received" and effect["connection_revision_id"]
    assert len(fake.requests) == 1, "an answer that may have been paid for is never retried"


def test_the_anthropic_flavour_runs_through_the_sdk_and_records_the_connection(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    """The control for the mismatch cases: the same flavour, the reply naming the gateway model,
    publishes -- so a failing mismatch run is the identity check and not a broken flavour."""
    rings = support.make_rings()
    fake = gateway_for(None)
    try:
        connection = support.seed_connection(
            session, rings, fake.base_url(""), api_flavour="anthropic_messages",
            billing="not_metered")
        providers = _providers(rings, fake)
        started = _start(session, seeded, new_key, "anthropic-ok", providers)
        result = _execute(session, blob_store, started.run_id, providers)
        rows = _rows(session, started.run_id)
    finally:
        fake.stop()
    assert result.terminal_state == "published" and result.published_finding_count > 0
    (call,) = rows["calls"]
    assert (call["provider"], call["connection_revision_id"], call["identity_basis"]) == (
        "anthropic_messages", connection.revision_id, "reported")
    assert fake.requests[0]["path"] == "/v1/messages" and fake.requests[0]["x_api_key"] == support.KEY
    assert fake.requests[0]["body"]["model"] == support.GATEWAY_MODEL


def test_under_the_environment_source_a_stub_model_fails_closed_and_an_explicit_one_runs(
    session, seeded, blob_store, new_key  # type: ignore[no-untyped-def]
) -> None:
    from auditmanager.analysis.text import CallBinding, ProxyAdapter, ProxySettings
    from auditmanager.findings import published_finding_count

    outcomes = {}
    for model in ("proxy", support.GATEWAY_MODEL):
        fake = gateway_for(None)
        try:
            adapter = ProxyAdapter(ProxySettings(
                base_url=f"http://127.0.0.1:{fake.port}/agent/v1", token="tok", model=model))
            source = EnvironmentProviders(
                adapter, LIVE, CallBinding(expected_model=model, check_identity=True))
            started = start_audit_run(
                session, version_uid=seeded.version_uid,
                analysis_profile_id=seeded.analysis_profile_id,
                prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live",
                idempotency_key=new_key(f"env-{model}"),
            )
            result = execute_run(
                session, started.run_id, blob_store=blob_store, adapter=adapter,
                provider_config=LIVE, providers=source.resolve,
                text_profiles=resolve_reference_profile,
            )
            outcomes[model] = (result.terminal_state, _rows(session, started.run_id),
                               published_finding_count(session, started.run_id))
        finally:
            fake.stop()
    state, rows, findings = outcomes["proxy"]
    assert state == "failed" and findings == 0
    assert rows["stage"]["error"]["code"] == "model_identity_mismatch"
    assert "model_not_selected" in rows["stage"]["error"]["message"]
    state, rows, findings = outcomes[support.GATEWAY_MODEL]
    assert state == "published" and findings > 0
    assert rows["run"]["connection_revision_id"] is None
    assert rows["calls"][0]["provider"] == "anthropic", "the environment source's rows are unchanged"


def test_the_environment_source_is_unchanged_and_records_no_revision(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key  # type: ignore[no-untyped-def]
) -> None:
    source = EnvironmentProviders(recorded_adapter, provider_config)
    assert source.freeze is None
    started = start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
        idempotency_key=new_key("env-regression"),
    )
    result = execute_run(
        session, started.run_id, blob_store=blob_store, adapter=recorded_adapter,
        provider_config=provider_config, providers=source.resolve,
        text_profiles=resolve_reference_profile,
    )
    rows = _rows(session, started.run_id)
    assert result.terminal_state == "published"
    assert rows["run"]["connection_revision_id"] is None
    (call,) = rows["calls"]
    assert (call["connection_revision_id"], call["identity_basis"], call["provider"]) == (
        None, None, "anthropic")


def test_the_environment_source_refuses_a_run_that_froze_a_connection(
    session, recorded_adapter, provider_config  # type: ignore[no-untyped-def]
) -> None:
    source = EnvironmentProviders(recorded_adapter, provider_config)
    run = type("Run", (), {"connection_revision_id": "excr_01J00000000000000000000000"})()
    with pytest.raises(DomainError) as refused:
        source.resolve(session, run, None)  # type: ignore[arg-type]
    assert refused.value.code.value == "dependency_unavailable"
