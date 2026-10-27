"""`ANALYSIS-PRESETS-01` on real PostgreSQL: a run starts with a saved preset.

Same fixtures as ``test_explicit_executor.py`` (real database, the executors context's own commands to
seed connections, the database provider source). What only a database can show:

* **a run started with a preset is the run a hand-chosen executor would have started**: the same
  frozen revision, the same input digest and profile, the same ``audit_run.executor_chosen`` event, the
  same command receipt type and the same status -- except that it records the preset revision and its
  status says so (``test_a_preset_start_is_byte_identical_to_the_hand_chosen_start``);
* the preset's **current** revision is the one applied, and the run keeps pointing at the revision it
  used when the preset is revised afterwards;
* every refusal (an unknown preset, an archived one, a preset beside an executor, a connection that
  cannot serve, no freezer) leaves no run, no command record and no event;
* the key: a replay after the preset was revised is a replay; the same key with a hand-chosen
  executor, or another preset, is ``idempotency_key_reuse``;
* a repeat keeps the executor and records no preset.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.bootstrap.adapters import _run_status_view, resolve_analysis_preset
from auditmanager.bootstrap.providers import DatabaseProviders
from auditmanager.executors.public import archive_connection, archive_preset, create_preset, revise_preset
from auditmanager.runs import RunRepository, start_audit_run
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
blob_store = harness.blob_store
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


def _start(session: Any, seeded: Any, key: Any, providers: DatabaseProviders | None, **named: Any) -> Any:
    freeze = None if providers is None else providers.freeze
    return start_audit_run(
        session, version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="live", idempotency_key=key,
        connection_route=freeze, **named,
    )


def _by_preset(session: Any, seeded: Any, key: Any, providers: Any, preset_id: str, **more: Any) -> Any:
    return _start(session, seeded, key, providers, preset_id=preset_id,
                  preset_resolver=resolve_analysis_preset, **more)


def _preset(session: Any, name: str, connection_id: str) -> Any:
    return create_preset(session, name=name, executor_connection_id=connection_id, roles=ADMIN,
                         idempotency_key=support.unique(), actor_uid=support.ACTOR)


def _row(session: Any, run_id: str) -> Any:
    return RunRepository().get(session, run_id)


def _chosen(session: Any, run_id: str) -> list[dict[str, Any]]:
    return list(session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = :t AND aggregate_id = :r"),
        {"t": CHOSEN, "r": run_id}).scalars().all())


def _counts(session: Any) -> tuple[int, ...]:
    return tuple(session.execute(text(sql)).scalar_one() for sql in (
        "SELECT count(*) FROM audit_run", "SELECT count(*) FROM command_record",
        "SELECT count(*) FROM audit_event"))


def _terminal(session: Any, run_id: str) -> None:
    cancel_audit_run(session, run_id=run_id, roles=ADMIN, idempotency_key=support.unique())


def _two(session: Any) -> tuple[Any, Any, Any, Any]:
    """A route connection, a second connection and the gateway that serves both."""
    rings = support.make_rings()
    fake = FakeGateway().start()
    routed = support.seed_connection(session, rings, fake.vpn_url(), name="Маршрут")
    other = support.seed_connection(session, rings, fake.vpn_url("/b"), name="Другой", routed=False)
    return rings, fake, routed, other


# -- a preset start is a hand-chosen start ------------------------------------------------------


def test_a_preset_start_freezes_the_presets_connection_not_the_route_and_records_the_revision(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, routed, other = _two(session)
    try:
        preset = _preset(session, "Быстрый черновик", other.connection_id)
        started = _by_preset(session, seeded, new_key("preset"), _providers(rings), preset.preset_id)

        row = _row(session, started.run_id)
        assert row.connection_revision_id == other.revision_id != routed.revision_id
        assert row.preset_revision_id == preset.revision_id
        (event,) = _chosen(session, started.run_id)
        assert event == {"run_id": started.run_id, "connection_id": other.connection_id,
                         "revision_id": other.revision_id}, "the choice is journaled as a hand-chosen one"
        view = _run_status_view(session, started.run_id)
        assert view.executor.connection_id == other.connection_id
        assert (view.preset.preset_id, view.preset.revision_no, view.preset.name) == (
            preset.preset_id, 1, "Быстрый черновик")
    finally:
        fake.stop()


def test_a_preset_start_is_byte_identical_to_the_hand_chosen_start(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    """Two runs of one version on one connection: one by hand, one by preset. Every column of the run
    row and of its status, every event payload and the receipt type agree, but the ids, the clock and
    the preset record itself."""
    rings, fake, _routed, other = _two(session)
    try:
        providers = _providers(rings)
        preset = _preset(session, "Основной", other.connection_id)
        by_hand = _start(session, seeded, new_key("hand"), providers, executor_connection_id=other.connection_id)
        by_preset = _by_preset(session, seeded, new_key("preset"), providers, preset.preset_id)

        a, b = _row(session, by_hand.run_id), _row(session, by_preset.run_id)
        moving = {"run_id", "command_id", "created_at", "preset_revision_id"}
        for column in a.__dataclass_fields__:
            if column not in moving:
                assert getattr(a, column) == getattr(b, column), column
        assert a.preset_revision_id is None and b.preset_revision_id == preset.revision_id

        def events(run_id: str) -> list[tuple[str, dict[str, Any]]]:
            rows = session.execute(text(
                "SELECT event_type, payload FROM audit_event WHERE aggregate_id = :r ORDER BY sequence_no"),
                {"r": run_id}).all()
            return [(kind, {k: v for k, v in payload.items() if k != "run_id"}) for kind, payload in rows]

        assert events(by_hand.run_id) == events(by_preset.run_id)
        receipts = [session.execute(text("SELECT command_type FROM command_record WHERE command_id = :c"),
                                    {"c": _row(session, r.run_id).command_id}).scalar_one()
                    for r in (by_hand, by_preset)]
        assert receipts[0] == receipts[1] == "start_audit_run"

        va, vb = _run_status_view(session, by_hand.run_id), _run_status_view(session, by_preset.run_id)
        from dataclasses import replace
        assert va.preset is None and vb.preset is not None
        assert replace(va, run_id="x", created_at=vb.created_at) == replace(vb, run_id="x", preset=None)
    finally:
        fake.stop()


def test_the_current_revision_is_applied_and_an_old_run_keeps_the_revision_it_used(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, routed, other = _two(session)
    try:
        providers = _providers(rings)
        preset = _preset(session, "Основной", routed.connection_id)
        first = _by_preset(session, seeded, new_key("one"), providers, preset.preset_id)
        revised = revise_preset(session, preset_id=preset.preset_id, name="Основной, на втором",
                                executor_connection_id=other.connection_id, roles=ADMIN,
                                idempotency_key=support.unique(), actor_uid=support.ACTOR)
        second = _by_preset(session, seeded, new_key("two"), providers, preset.preset_id)

        assert _row(session, first.run_id).connection_revision_id == routed.revision_id
        assert _row(session, second.run_id).connection_revision_id == other.revision_id
        assert _row(session, second.run_id).preset_revision_id == revised.revision_id
        old = _run_status_view(session, first.run_id).preset
        assert (old.revision_no, old.name) == (1, "Основной"), "the run shows the name it started under"
        assert _run_status_view(session, second.run_id).preset.name == "Основной, на втором"
    finally:
        fake.stop()


# -- refusals write nothing ---------------------------------------------------------------------


def test_an_unknown_preset_is_refused_on_its_field_and_writes_nothing(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, _routed, _other = _two(session)
    try:
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _by_preset(session, seeded, new_key("ghost"), _providers(rings), "evt_01M2545JSD15ETSNNV904X991N")
        assert refused.value.code is ErrorCode.VALIDATION_FAILED
        assert refused.value.detail_fields == {"field": "preset_id", "constraint": "unknown_preset"}
        assert _counts(session) == before
    finally:
        fake.stop()


def test_an_archived_preset_is_a_conflict_and_writes_nothing(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, _routed, other = _two(session)
    try:
        preset = _preset(session, "Старый", other.connection_id)
        archive_preset(session, preset_id=preset.preset_id, roles=ADMIN, idempotency_key=support.unique(),
                       actor_uid=support.ACTOR)
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _by_preset(session, seeded, new_key("archived"), _providers(rings), preset.preset_id)
        assert refused.value.code is ErrorCode.CONFLICT
        assert refused.value.detail_fields["conflict_reason"] == "preset_archived"
        assert _counts(session) == before
    finally:
        fake.stop()


def test_a_preset_beside_an_executor_is_refused_and_writes_nothing(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, routed, other = _two(session)
    try:
        preset = _preset(session, "Основной", other.connection_id)
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _by_preset(session, seeded, new_key("both"), _providers(rings), preset.preset_id,
                       executor_connection_id=routed.connection_id)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED
        assert refused.value.detail_fields == {
            "field": "preset_id", "constraint": "conflicts_with_executor_connection_id"}
        assert _counts(session) == before
    finally:
        fake.stop()


@pytest.mark.parametrize("how", ["archived", "unprobed", "probe_failed"])
def test_a_presets_connection_that_cannot_serve_is_the_existing_refusal_and_never_a_fallback(
    session, seeded, new_key, how: str  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, routed, _other = _two(session)
    try:
        target = support.seed_connection(
            session, rings, fake.vpn_url("/x"), name=how, routed=False,
            probe=None if how == "unprobed" else ("credential_refused" if how == "probe_failed" else "ok"))
        preset = _preset(session, "Нерабочий", target.connection_id)
        if how == "archived":
            archive_connection(session, connection_id=target.connection_id, roles=ADMIN,
                               idempotency_key=support.unique(), actor_uid=support.ACTOR)
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _by_preset(session, seeded, new_key(how), _providers(rings), preset.preset_id)
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert refused.value.detail_fields == {"dependency": "executor_connection"}
        assert _counts(session) == before, "no run, no receipt, no event: not redirected to the route"
        assert routed.connection_id  # the route was usable the whole time
    finally:
        fake.stop()


def test_a_deployment_without_a_freezer_refuses_a_preset_rather_than_ignoring_it(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, _routed, other = _two(session)
    try:
        preset = _preset(session, "Основной", other.connection_id)
        before = _counts(session)
        with pytest.raises(DomainError) as refused:
            _by_preset(session, seeded, new_key("env"), None, preset.preset_id)
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert _counts(session) == before
        with pytest.raises(DomainError) as unresolved:
            _start(session, seeded, new_key("no-resolver"), _providers(rings), preset_id=preset.preset_id)
        assert unresolved.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert _counts(session) == before
    finally:
        fake.stop()


# -- the key ------------------------------------------------------------------------------------


def test_the_same_key_replays_after_the_preset_was_revised_and_conflicts_with_anything_else(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, routed, other = _two(session)
    try:
        providers = _providers(rings)
        preset = _preset(session, "Основной", other.connection_id)
        rival = _preset(session, "Соперник", other.connection_id)
        key = new_key("idempotent")
        started = _by_preset(session, seeded, key, providers, preset.preset_id)
        revise_preset(session, preset_id=preset.preset_id, name="Основной, потом", executor_connection_id=routed.connection_id,
                      roles=ADMIN, idempotency_key=support.unique(), actor_uid=support.ACTOR)
        runs_before = _counts(session)[0]

        replay = _by_preset(session, seeded, key, providers, preset.preset_id)
        assert (replay.replayed, replay.run_id) == (True, started.run_id), "a retry after a revision replays"
        archive_preset(session, preset_id=preset.preset_id, roles=ADMIN, idempotency_key=support.unique(),
                       actor_uid=support.ACTOR)
        assert _by_preset(session, seeded, key, providers, preset.preset_id).replayed is True, \
            "a known key is answered before the preset is read"
        for attempt in (
            lambda: _by_preset(session, seeded, key, providers, rival.preset_id),
            lambda: _start(session, seeded, key, providers, executor_connection_id=other.connection_id),
            lambda: _start(session, seeded, key, providers),
        ):
            with pytest.raises(DomainError) as conflict:
                attempt()
            assert conflict.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert _counts(session)[0] == runs_before
        assert len(_chosen(session, started.run_id)) == 1, "a replay journals nothing more"
    finally:
        fake.stop()


# -- the repeat ---------------------------------------------------------------------------------


def test_a_repeat_of_a_preset_run_keeps_the_executor_and_records_no_preset(
    session, seeded, new_key  # type: ignore[no-untyped-def]
) -> None:
    rings, fake, _routed, other = _two(session)
    try:
        providers = _providers(rings)
        preset = _preset(session, "Основной", other.connection_id)
        source = _by_preset(session, seeded, new_key("source"), providers, preset.preset_id)
        _terminal(session, source.run_id)
        again = reaudit_run(
            session, source_run_id=source.run_id, roles=ADMIN, idempotency_key=new_key("repeat").value,
            provider_mode="live", connection_route=providers.freeze,
            analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
            input_budget_characters=10**9,
        )
        row = _row(session, again.run_id)
        assert row.connection_revision_id == other.revision_id
        assert row.preset_revision_id is None
        assert _run_status_view(session, again.run_id).preset is None
    finally:
        fake.stop()
