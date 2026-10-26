"""`EXEC-PAR-START-01`: a run may name its executor, and a named executor never falls back.

Container-free. ``freeze_connection`` is driven over an in-memory stand-in of the executor
repository that answers exactly the reads the usability test makes and **records every read**, so
the claims below are about what the function asked, not only what it answered:

* a named connection is frozen at its *current* revision, and neither the route nor the standby
  is read;
* every way a connection can fail the test refuses the start with a typed error -- an unknown or
  malformed id ``validation_failed`` on ``executor_connection_id``, an archived, unserved or
  unprobed one ``dependency_unavailable`` (``executor_connection``) -- even when the route has a
  perfectly usable primary and standby (no fallback);
* the refusals survive the error catalogue's own screen (``DomainError.envelope``);
* without a name, ``freeze_connection`` is the route's function it always was (primary, then the
  standby with its reason), and ``DatabaseProviders.freeze`` calls it exactly as before.

What PostgreSQL does with the rows is in ``tests/integration/executors/test_explicit_executor.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.analysis.public import pinned_models
from auditmanager.bootstrap import providers as providers_module
from auditmanager.bootstrap.providers import DatabaseProviders
from auditmanager.executors import resolver
from auditmanager.executors.model import (
    ConnectionRecord,
    ProbeRecord,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
    SecretRecord,
)
from auditmanager.executors.resolver import FrozenConnection, freeze_connection
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorConnectionId

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 26, 12, 5, tzinfo=timezone.utc)
WORK_KIND = "text_analysis"
PIN = pinned_models()[0].model_id


def _new_id() -> str:
    return str(ExecutorConnectionId.new())


def _settings(**changes: Any) -> RevisionSettings:
    base: dict[str, Any] = dict(
        pin_id=PIN, gateway_model="gateway-model", billing="metered",
        allow_client_documents=False, timeout_seconds=60, api_flavour="openai_chat",
        base_url="https://gateway.example", transport="direct",
    )
    base.update(changes)
    return RevisionSettings(**base)


class Store:
    """The reads ``freeze_connection`` makes, over dictionaries. ``reads`` records each call."""

    def __init__(self) -> None:
        self.connections: dict[str, ConnectionRecord] = {}
        self.revisions: dict[str, list[RevisionRecord]] = {}
        self.secrets: dict[str, list[SecretRecord]] = {}
        self.probes: dict[tuple[str, str | None], ProbeRecord] = {}
        self.route: RouteRecord | None = None
        self.reads: list[str] = []

    # --- the reads --------------------------------------------------------------------------

    def get_connection(self, session: Any, connection_id: str, *, lock: bool = False) -> Any:
        self.reads.append("get_connection")
        return self.connections.get(connection_id)

    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, RevisionRecord]:
        self.reads.append("current_revisions")
        return {
            cid: max(self.revisions[cid], key=lambda r: r.revision_no)
            for cid in connection_ids if self.revisions.get(cid)
        }

    def current_secrets(self, session: Any, connection_ids: Any) -> dict[str, list[SecretRecord]]:
        self.reads.append("current_secrets")
        return {cid: list(self.secrets.get(cid, ())) for cid in connection_ids}

    def latest_finished_probe(self, session: Any, revision_id: str, secret_id: Any) -> Any:
        self.reads.append("latest_finished_probe")
        return self.probes.get((revision_id, secret_id))

    def current_route(self, session: Any, work_kind: str) -> Any:
        self.reads.append("current_route")
        return self.route

    # --- seeding ----------------------------------------------------------------------------

    def connection(
        self, *, revisions: int = 1, archived: bool = False, probe: str | None = "ok",
        secret: bool = True, **settings: Any,
    ) -> str:
        """A connection with ``revisions`` revisions, a current key, and (by default) an ``ok``
        probe of its **current** revision on that key."""
        cid = _new_id()
        self.connections[cid] = ConnectionRecord(
            connection_id=cid, kind="http_api", display_name=f"Исполнитель {cid[-4:]}",
            created_at=NOW, created_by="usr_test",
            archived_at=NOW if archived else None, archived_by="usr_test" if archived else None,
        )
        self.revisions[cid] = [
            RevisionRecord(
                revision_id=f"rev_{cid[-6:]}_{number}", connection_id=cid, revision_no=number,
                created_at=NOW, created_by="usr_test", settings=_settings(**settings),
            )
            for number in range(1, revisions + 1)
        ]
        if secret:
            self.secrets[cid] = [SecretRecord(
                secret_id=f"sec_{cid[-6:]}", connection_id=cid, purpose="api_key", kid="k1",
                destination="d", last4="abcd", public_material=None, set_at=NOW, set_by="usr_test",
            )]
        if probe is not None and secret:
            current = self.revisions[cid][-1]
            self.probes[(current.revision_id, f"sec_{cid[-6:]}")] = ProbeRecord(
                probe_id=f"prb_{cid[-6:]}", connection_id=cid, revision_id=current.revision_id,
                secret_id=f"sec_{cid[-6:]}", state="finished", outcome=probe, reported_model=None,
                identity_basis=None, latency_ms=1, http_status=200, rate_check=None,
                observed_host_key=None, detail=None, requested_at=LATER, requested_by="usr_test",
                started_at=LATER, finished_at=LATER,
            )
        return cid

    def routed(self, primary: str, standby: str | None = None) -> None:
        self.route = RouteRecord(
            route_event_id="rte_1", work_kind=WORK_KIND, route_no=1,
            primary_connection_id=primary, standby_connection_id=standby, set_at=NOW,
            set_by="usr_test",
        )


@pytest.fixture
def store() -> Store:
    return Store()


def _freeze(store: Store, connection_id: str | None = None) -> FrozenConnection:
    return freeze_connection(
        object(), WORK_KIND, connection_id=connection_id, repository=store,  # type: ignore[arg-type]
    )


def _refusal(store: Store, connection_id: str) -> DomainError:
    with pytest.raises(DomainError) as caught:
        _freeze(store, connection_id)
    return caught.value


# --- a named connection is frozen ----------------------------------------------------------------


def test_a_named_connection_is_frozen_at_its_current_revision(store: Store) -> None:
    named = store.connection(revisions=3)
    frozen = _freeze(store, named)
    assert frozen.explicit is True
    assert frozen.connection_id == named == frozen.primary_connection_id
    assert frozen.revision_id == store.revisions[named][-1].revision_id, "the highest revision"
    assert frozen.revision_id != store.revisions[named][0].revision_id
    assert (frozen.pin_id, frozen.work_kind) == (PIN, WORK_KIND)
    assert frozen.standby_connection_id is None and frozen.reason is None
    assert frozen.used_standby is False


def test_a_named_connection_never_reads_the_route(store: Store) -> None:
    """Not 'reads it and ignores it': the route's table is not asked at all."""
    routed = store.connection()
    store.routed(routed, store.connection())
    named = store.connection()
    _freeze(store, named)
    assert "current_route" not in store.reads


def test_a_named_connection_is_frozen_although_the_route_names_another(store: Store) -> None:
    routed, named = store.connection(), store.connection()
    store.routed(routed)
    assert _freeze(store, named).connection_id == named
    assert _freeze(store, None).connection_id == routed


# --- every way to be unusable refuses, and nothing falls back -------------------------------------


def _usable_route(store: Store) -> None:
    """A route whose primary and standby both serve: the fallback a refusal must not reach."""
    store.routed(store.connection(), store.connection())


def test_an_unknown_connection_is_validation_failed_on_the_field(store: Store) -> None:
    _usable_route(store)
    refusal = _refusal(store, _new_id())
    assert refusal.code is ErrorCode.VALIDATION_FAILED
    assert dict(refusal.detail_fields) == {
        "field": "executor_connection_id", "constraint": "unknown_connection",
    }


@pytest.mark.parametrize("malformed", ["", "exc_", "exc_notaulid", "con_01M2545JSD15ETSNNV904X991J", " "])
def test_a_malformed_id_is_validation_failed_and_reaches_no_row(store: Store, malformed: str) -> None:
    _usable_route(store)
    store.reads.clear()
    refusal = _refusal(store, malformed)
    assert refusal.code is ErrorCode.VALIDATION_FAILED
    assert dict(refusal.detail_fields) == {"field": "executor_connection_id", "constraint": "pattern"}
    assert store.reads == [], "a malformed id is refused before any read"


def _unusable(store: Store, reason: str) -> str:
    if reason == "archived":
        return store.connection(archived=True)
    if reason == "kind_not_served":
        return store.connection(transport="carrier-pigeon")
    if reason == "not_probed":
        return store.connection(probe=None)
    if reason == "probe_failed":
        return store.connection(probe="credential_refused")
    if reason == "no_key":
        return store.connection(secret=False)
    if reason == "no_revision":
        cid = store.connection()
        store.revisions[cid] = []
        return cid
    raise AssertionError(reason)


@pytest.mark.parametrize("reason,word", [
    ("archived", "archived"),
    ("kind_not_served", "kind_not_served"),
    ("not_probed", "not_probed"),
    ("probe_failed", "not_probed"),
    ("no_key", "not_probed"),
    ("no_revision", "no_revision"),
])
def test_a_connection_that_cannot_serve_refuses_with_its_reason_and_never_falls_back(
    store: Store, reason: str, word: str,
) -> None:
    _usable_route(store)  # a usable primary AND a usable standby are right there
    refusal = _refusal(store, _unusable(store, reason))
    assert refusal.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(refusal.detail_fields) == {"dependency": "executor_connection"}
    assert f"({word})" in str(refusal)
    assert "current_route" not in store.reads, "no fallback means the route is not even read"


def test_a_probe_of_an_earlier_revision_does_not_make_the_current_one_usable(store: Store) -> None:
    """A new revision is unusable until it passes its own probe (the usability rule, T-1)."""
    named = store.connection(revisions=2, probe=None)
    old = store.revisions[named][0]
    store.probes[(old.revision_id, f"sec_{named[-6:]}")] = ProbeRecord(
        probe_id="prb_old", connection_id=named, revision_id=old.revision_id,
        secret_id=f"sec_{named[-6:]}", state="finished", outcome="ok", reported_model=None,
        identity_basis=None, latency_ms=1, http_status=200, rate_check=None,
        observed_host_key=None, detail=None, requested_at=LATER, requested_by="usr_test",
        started_at=LATER, finished_at=LATER,
    )
    assert "not_probed" in str(_refusal(store, named))


def test_a_kind_that_does_not_serve_the_work_is_refused_as_the_route_refuses_it(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    named = store.connection()
    monkeypatch.setattr(resolver, "SERVES", {WORK_KIND: frozenset({"pull"})})
    refusal = _refusal(store, named)
    assert refusal.code is ErrorCode.VALIDATION_FAILED
    assert dict(refusal.detail_fields) == {
        "field": "executor_connection_id", "constraint": "kind_not_routable",
    }


@pytest.mark.parametrize("reason", ["archived", "kind_not_served", "not_probed", "no_revision"])
def test_every_refusal_builds_an_envelope_the_catalogue_accepts(store: Store, reason: str) -> None:
    """The message is screened and the details are the code's own safe keys: nothing here would
    raise ``UnsafeDetailKey`` or ``UnsafeMessage`` when the handler renders it."""
    envelope = _refusal(store, _unusable(store, reason)).envelope("cor_1")
    assert envelope.error_code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(envelope.details) == {"dependency": "executor_connection"}
    unknown = _refusal(store, _new_id()).envelope("cor_2")
    assert unknown.error_code is ErrorCode.VALIDATION_FAILED


def test_no_refusal_carries_a_key_an_address_or_a_name(store: Store) -> None:
    named = store.connection(archived=True, base_url="https://secret-gateway.example")
    rendered = repr(_refusal(store, named).envelope("cor_3").as_dict())
    for leak in ("secret-gateway", "api_key", "sec_", store.connections[named].display_name, "abcd"):
        assert leak not in rendered, leak


# --- without a name, the route is what it always was -----------------------------------------------


def test_without_a_name_the_primary_serves_as_before(store: Store) -> None:
    primary = store.connection()
    store.routed(primary, store.connection())
    frozen = _freeze(store)
    assert (frozen.connection_id, frozen.explicit, frozen.reason) == (primary, False, None)
    assert frozen.standby_connection_id == store.route.standby_connection_id  # type: ignore[union-attr]


def test_without_a_name_an_unusable_primary_falls_to_the_standby_with_its_reason(store: Store) -> None:
    standby = store.connection()
    store.routed(store.connection(probe=None), standby)
    frozen = _freeze(store)
    assert (frozen.connection_id, frozen.explicit) == (standby, False)
    assert frozen.reason == "primary_not_probed" and frozen.used_standby is True


def test_without_a_name_and_without_a_usable_side_the_start_is_still_refused_as_route_missing(
    store: Store,
) -> None:
    store.routed(store.connection(archived=True))
    with pytest.raises(DomainError) as caught:
        _freeze(store)
    assert dict(caught.value.detail_fields) == {"dependency": "executor_route_missing"}


# --- the provider source's freeze seam -------------------------------------------------------------


def _providers() -> DatabaseProviders:
    return DatabaseProviders(ring=None, policy=object(), base_config=None, ceiling_usd=1.0)  # type: ignore[arg-type]


def _record_freezes(monkeypatch: pytest.MonkeyPatch, answer: FrozenConnection) -> list[tuple[tuple, dict]]:
    calls: list[tuple[tuple, dict]] = []

    def fake(*args: Any, **kwargs: Any) -> FrozenConnection:
        calls.append((args, kwargs))
        return answer

    monkeypatch.setattr(providers_module, "freeze_connection", fake)
    return calls


def _frozen(**changes: Any) -> FrozenConnection:
    base: dict[str, Any] = dict(
        revision_id="rev_1", connection_id="exc_primary", pin_id=PIN, work_kind=WORK_KIND,
        primary_connection_id="exc_primary", standby_connection_id=None,
    )
    base.update(changes)
    return FrozenConnection(**base)


def test_the_seam_without_a_name_makes_the_call_it_always_made(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_freezes(monkeypatch, _frozen())
    session = object()
    route = _providers().freeze(session)  # type: ignore[misc]
    assert calls == [((session, WORK_KIND), {})], "no connection_id keyword is passed"
    assert route.chosen_connection_id is None and route.revision_id == "rev_1"


def test_the_seam_with_a_name_asks_for_that_connection_and_reports_it_chosen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_freezes(monkeypatch, _frozen(
        connection_id="exc_named", primary_connection_id="exc_named", explicit=True,
    ))
    session = object()
    route = _providers().freeze(session, connection_id="exc_named")  # type: ignore[misc]
    assert calls == [((session, WORK_KIND), {"connection_id": "exc_named"})]
    assert route.chosen_connection_id == "exc_named"
    assert (route.primary_connection_id, route.standby_connection_id, route.standby_reason) == (
        None, None, None,
    ), "a named executor is not a standby"


def test_the_seam_reports_a_standby_as_before_and_as_not_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_freezes(monkeypatch, _frozen(
        connection_id="exc_standby", standby_connection_id="exc_standby", reason="primary_archived",
    ))
    route = _providers().freeze(object())  # type: ignore[misc]
    assert route.chosen_connection_id is None
    assert (route.primary_connection_id, route.standby_connection_id, route.standby_reason) == (
        "exc_primary", "exc_standby", "primary_archived",
    )


def test_the_run_of_a_revision_is_reported_by_connection_name_and_pin_only() -> None:
    from auditmanager.executors.queries import RunExecutor, executor_of_revision

    store = Store()
    cid = store.connection(archived=True)  # an archived connection still answers: the run was on it
    revision = store.revisions[cid][0]

    class _Repo(Store):
        def get_revision(self, session: Any, revision_id: str) -> Any:
            return revision if revision_id == revision.revision_id else None

    repo = _Repo()
    repo.connections, repo.revisions = store.connections, store.revisions
    found = executor_of_revision(object(), revision.revision_id, repo)  # type: ignore[arg-type]
    assert found == RunExecutor(
        connection_id=cid, display_name=store.connections[cid].display_name, pin_id=PIN,
    )
    assert set(RunExecutor.__dataclass_fields__) == {"connection_id", "display_name", "pin_id"}
    assert executor_of_revision(object(), "rev_missing", repo) is None  # type: ignore[arg-type]
