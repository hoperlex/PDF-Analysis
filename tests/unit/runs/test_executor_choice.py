"""`EXEC-PAR-START-01`: the run-start command honours a named executor, and a repeat keeps it.

Container-free, in the manner of ``tests/integration/runs/test_w55a_pin_offline.py``: the
ledger, the run and document repositories, the session and the route freezer are fakes that
record what they were handed. What is proved here:

* **absent is today's start.** The freezer is called as ``freeze(session)`` -- no keyword -- the
  fingerprint is the literal captured from the base tree, and no choice event is written;
* **present is a different payload.** The fingerprint the ledger sees carries the choice, so the
  same key with another executor is a conflict and not a replay; the same executor replays;
* **a refusal writes nothing.** A freezer that refuses (unknown, archived, not probed) is raised
  *before* the key is claimed: no ledger call, no run, no event;
* **no fallback.** A named executor with no freezer to honour it, and a freezer that answers a
  connection other than the one named, are refused rather than run on something else;
* **the choice is journaled** once, with identities only, beside the run it belongs to;
* **a repeat keeps the executor.** ``reaudit_run`` freezes the connection the source named, not
  the route; it journals the same choice for the new run; its fingerprint is unchanged; a
  refusal or a missing freezer writes nothing;
* the replay of a known key consults no freezer and (for a repeat) reads no journal.

What PostgreSQL does with the same rows is in ``tests/integration/runs/test_executor_choice.py``.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.ingest.public import CommandReplay, CommandStarted, payload_fingerprint
from auditmanager.runs.commands import reaudit_run, start_audit_run, start_run_fingerprint
from auditmanager.runs.provider import FrozenRoute
from auditmanager.runs.repository import EXECUTOR_CHOSEN_EVENT, RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROFILE = "ap_01M2545JSD15ETSNNV904X991A"
BUNDLE = "pb_01M2545JSD15ETSNNV904X991P"
BLOB = "blob_sha256_" + "ab" * 32
SOURCE_RUN = "run_01M2545JSD15ETSNNV904X991K"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
COMMAND = "cmd_01M2545JSD15ETSNNV904X991C"
NAMED = "exc_01M2545JSD15ETSNNV904X991N"
OTHER = "exc_01M2545JSD15ETSNNV904X992N"
ROUTED_REVISION = "exr_ROUTED"

#: ``start_run_fingerprint(...)`` for the request below on the base tree ``a3e83f39``, before this
#: lane: what a ``command_record`` accepted before the field existed holds. Captured, not derived.
BASE_FINGERPRINT = "62bde5d8d311ce2d73c60ed4c870c7ff03602ff6b540c2bf2ec2e5074fb7f061"
BASIS = "edb5162bab84b32ec352ffa4785cc7ab02625c7b92a88c78bec5ccdca2a8c031"


class Ledger:
    """``CommandRepository``: records every call, replays a key it is told is known."""

    def __init__(self, replay_run: str | None = None) -> None:
        self.fingerprints: list[str] = []
        self.finds = 0
        self.succeeded: list[dict[str, Any]] = []
        self._replay_run = replay_run

    def find(self, session: Any, *, command_type: str, idempotency_key: Any) -> Any:
        self.finds += 1
        if self._replay_run is None:
            return None
        return SimpleNamespace(outcome={"run_id": self._replay_run})

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any,
              fingerprint: Any) -> Any:
        self.fingerprints.append(str(fingerprint))
        if self._replay_run is not None:
            return CommandReplay(CommandId(COMMAND), {"run_id": self._replay_run})
        return CommandStarted(CommandId(COMMAND))

    def succeed(self, session: Any, command_id: Any, outcome: dict[str, Any]) -> None:
        self.succeeded.append(dict(outcome))


class Runs:
    """``RunRepository``: records ``create``; answers the source run and its journal."""

    def __init__(self, source: Any = None, source_choice: str | None = None) -> None:
        self.created: list[dict[str, Any]] = []
        self.journal_reads: list[str] = []
        self._source = source
        self._source_choice = source_choice

    def create(self, session: Any, **row: Any) -> None:
        self.created.append(row)

    def get(self, session: Any, run_id: str) -> Any:
        assert self._source is not None and run_id == self._source.run_id
        return self._source

    def find(self, session: Any, run_id: str) -> Any:
        return None

    def chosen_executor_connection(self, session: Any, run_id: str) -> str | None:
        self.journal_reads.append(run_id)
        return self._source_choice

    def advance(self, session: Any, **_: Any) -> None:
        return None


class Documents:
    def get_version(self, session: Any, version_uid: Any) -> Any:
        assert str(version_uid) == VERSION
        return SimpleNamespace(
            project_uid=PROJECT, text_character_count=None,
            manifest=(SimpleNamespace(role="source.document", blob_id=BLOB),),
        )


class Jobs:
    def enqueue(self, session: Any, *, run_id: str) -> None:
        return None


class Session:
    """Answers the repeat's raw reads (row lock, busy check) and records the journal inserts."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        if str(statement).lstrip().startswith("INSERT INTO audit_event"):
            self.events.append({**parameters, "payload": json.loads(parameters["payload"])})
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class Freezer:
    """The route freezer seam. ``calls`` holds the keywords of each call: ``{}`` is the route's
    call, ``{"connection_id": ...}`` a named one. ``honour=False`` models a freezer that
    ignores the keyword and answers the route."""

    def __init__(self, *, refusal: DomainError | None = None, honour: bool = True) -> None:
        self.calls: list[dict[str, Any]] = []
        self._refusal = refusal
        self._honour = honour

    def __call__(self, session: Any, **kwargs: Any) -> FrozenRoute:
        self.calls.append(dict(kwargs))
        if self._refusal is not None:
            raise self._refusal
        named = kwargs.get("connection_id")
        if named is not None and self._honour:
            return FrozenRoute(
                revision_id=f"exr_OF_{named[-4:]}", input_budget_characters=10**9,
                chosen_connection_id=named,
            )
        return FrozenRoute(revision_id=ROUTED_REVISION, input_budget_characters=10**9)


def _unusable() -> DomainError:
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="the chosen executor connection cannot serve",
        dependency="executor_connection",
    )


def _start(
    ledger: Ledger, runs: Runs, session: Session, freezer: Freezer | None, **named: Any,
) -> Any:
    return start_audit_run(
        session, version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", idempotency_key="choice-1", commands=ledger, runs=runs,
        documents=Documents(), norms_snapshot=lambda s: None, connection_route=freezer, **named,
    )


# --- the fingerprint ---------------------------------------------------------------------------


def _fingerprint(executor: str | None = None) -> str:
    return str(start_run_fingerprint(
        version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", input_basis_digest_value=BASIS, executor_connection_id=executor,
    ))


def test_without_a_choice_the_fingerprint_is_the_one_every_earlier_key_holds() -> None:
    assert _fingerprint() == BASE_FINGERPRINT
    assert _fingerprint() == str(payload_fingerprint({
        "analysis_profile_id": PROFILE, "frozen_input_digest": BASIS,
        "prompt_bundle_id": BUNDLE, "provider_mode": "recorded", "version_uid": VERSION,
    }))


def test_a_choice_is_part_of_the_payload() -> None:
    assert len({_fingerprint(), _fingerprint(NAMED), _fingerprint(OTHER)}) == 3
    assert _fingerprint(NAMED) == _fingerprint(NAMED)
    assert _fingerprint(NAMED) == str(payload_fingerprint({
        "analysis_profile_id": PROFILE, "frozen_input_digest": BASIS,
        "prompt_bundle_id": BUNDLE, "provider_mode": "recorded", "version_uid": VERSION,
        "executor_connection_id": NAMED,
    }))


# --- startRun, no choice -----------------------------------------------------------------------


def test_an_unchosen_start_calls_the_freezer_as_it_always_did_and_journals_no_choice() -> None:
    ledger, runs, session, freezer = Ledger(), Runs(), Session(), Freezer()
    _start(ledger, runs, session, freezer)
    assert freezer.calls == [{}], "the route's call: no connection_id keyword"
    assert ledger.fingerprints == [BASE_FINGERPRINT]
    (row,) = runs.created
    assert row["connection_revision_id"] == ROUTED_REVISION
    assert session.events == [], "a routed run has no choice event"


def test_an_unchosen_start_on_the_environment_source_has_no_freezer_and_no_revision() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    _start(ledger, runs, session, None)
    (row,) = runs.created
    assert row["connection_revision_id"] is None and session.events == []
    assert ledger.fingerprints == [BASE_FINGERPRINT]


# --- startRun, a named executor ------------------------------------------------------------------


def test_a_named_start_freezes_that_connection_and_hands_the_ledger_a_payload_with_the_choice() -> None:
    ledger, runs, session, freezer = Ledger(), Runs(), Session(), Freezer()
    _start(ledger, runs, session, freezer, executor_connection_id=NAMED)
    assert freezer.calls == [{"connection_id": NAMED}]
    assert ledger.fingerprints == [_fingerprint(NAMED)] != [BASE_FINGERPRINT]
    (row,) = runs.created
    assert row["connection_revision_id"] == f"exr_OF_{NAMED[-4:]}"


def test_the_same_key_with_another_executor_reaches_the_ledger_as_another_payload() -> None:
    ledger = Ledger()
    for named in (None, NAMED, OTHER, NAMED):
        _start(ledger, Runs(), Session(), Freezer(), executor_connection_id=named)
    assert ledger.fingerprints == [
        BASE_FINGERPRINT, _fingerprint(NAMED), _fingerprint(OTHER), _fingerprint(NAMED),
    ]
    assert len(set(ledger.fingerprints)) == 3, "same executor twice is one payload; the rest differ"


def test_a_named_start_journals_the_choice_once_with_identities_only() -> None:
    runs, session = Runs(), Session()
    started = _start(Ledger(), runs, session, Freezer(), executor_connection_id=NAMED)
    (event,) = session.events
    assert event["event_type"] == EXECUTOR_CHOSEN_EVENT == "audit_run.executor_chosen"
    assert (event["aggregate_type"], event["aggregate_id"]) == ("AuditRun", started.run_id)
    assert event["payload"] == {
        "run_id": started.run_id, "connection_id": NAMED, "revision_id": f"exr_OF_{NAMED[-4:]}",
    }


def test_the_journal_event_is_a_product_event_the_purge_classifies() -> None:
    from scripts.recovery import product_purge

    assert EXECUTOR_CHOSEN_EVENT.startswith(product_purge.PRODUCT_EVENT_PREFIXES)
    assert not EXECUTOR_CHOSEN_EVENT.startswith(product_purge.KEEP_EVENT_PREFIXES)


# --- startRun, refusals write nothing -------------------------------------------------------------


def test_a_refusing_freezer_stops_the_start_before_the_key_is_claimed() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, Freezer(refusal=_unusable()), executor_connection_id=NAMED)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert ledger.fingerprints == [] and ledger.succeeded == []
    assert runs.created == [] and session.events == []


def test_a_named_executor_with_no_freezer_is_refused_not_run_on_the_processs_own_adapter() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, None, executor_connection_id=NAMED)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(caught.value.detail_fields) == {"dependency": "executor_connection"}
    assert ledger.fingerprints == [] and runs.created == [] and session.events == []


def test_a_freezer_that_answers_another_connection_than_the_one_named_is_a_wiring_fault() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(ValueError, match="did not freeze the connection"):
        _start(ledger, runs, session, Freezer(honour=False), executor_connection_id=NAMED)
    assert ledger.fingerprints == [] and runs.created == [] and session.events == []


def test_a_replayed_named_start_consults_no_freezer_and_writes_nothing() -> None:
    ledger, runs, session, freezer = Ledger(replay_run=SOURCE_RUN), Runs(), Session(), Freezer()
    started = _start(ledger, runs, session, freezer, executor_connection_id=NAMED)
    assert started.replayed is True and started.run_id == SOURCE_RUN
    assert freezer.calls == [] and runs.created == [] and session.events == []
    assert ledger.fingerprints == [_fingerprint(NAMED)], "the ledger still compares the choice"


def test_a_replayed_named_start_is_answered_even_when_this_process_has_no_freezer() -> None:
    """A client retrying an accepted start is told what happened, not that the source changed."""
    started = _start(Ledger(replay_run=SOURCE_RUN), Runs(), Session(), None, executor_connection_id=NAMED)
    assert started.replayed is True


# --- reauditRun ----------------------------------------------------------------------------------


def _source() -> Any:
    return SimpleNamespace(
        run_id=SOURCE_RUN, project_uid=PROJECT, version_uid=VERSION, state="failed",
        frozen_input_digest="c" * 64, norms_snapshot_id=None,
    )


def _repeat(
    ledger: Ledger, runs: Runs, session: Session, freezer: Freezer | None,
) -> Any:
    return reaudit_run(
        session, source_run_id=SOURCE_RUN, roles=frozenset({"expert"}),
        idempotency_key="repeat-1", analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", runs=runs, jobs=Jobs(), commands=ledger, documents=Documents(),
        norms_snapshot=lambda s: None, connection_route=freezer,
        # The served path always passes the budget (`test_the_served_application_always_passes_a_
        # budget`); it is what makes the repeat consult the journal when no freezer is wired.
        input_budget_characters=10**9,
    )


REPEAT_FINGERPRINT = str(payload_fingerprint(
    {"reaudit_of_run_id": SOURCE_RUN, "frozen_input_digest": "c" * 64}
))


def test_a_repeat_of_a_routed_run_follows_todays_route() -> None:
    ledger, runs, session, freezer = Ledger(), Runs(_source()), Session(), Freezer()
    _repeat(ledger, runs, session, freezer)
    assert freezer.calls == [{}]
    (row,) = runs.created
    assert row["connection_revision_id"] == ROUTED_REVISION and session.events == []
    assert ledger.fingerprints == [REPEAT_FINGERPRINT]


def test_a_repeat_of_a_named_run_freezes_the_same_connection_and_not_the_route() -> None:
    ledger, runs, session, freezer = Ledger(), Runs(_source(), NAMED), Session(), Freezer()
    started = _repeat(ledger, runs, session, freezer)
    assert freezer.calls == [{"connection_id": NAMED}]
    assert runs.journal_reads == [SOURCE_RUN]
    (row,) = runs.created
    assert row["connection_revision_id"] == f"exr_OF_{NAMED[-4:]}"
    assert row["reaudit_of_run_id"] == SOURCE_RUN
    assert ledger.fingerprints == [REPEAT_FINGERPRINT], "the repeat's payload is unchanged"
    (event,) = session.events
    assert event["event_type"] == EXECUTOR_CHOSEN_EVENT and event["aggregate_id"] == started.run_id
    assert event["payload"]["connection_id"] == NAMED, "so a repeat of the repeat keeps it too"


def test_a_repeat_whose_connection_can_no_longer_serve_is_refused_and_writes_nothing() -> None:
    ledger, runs, session = Ledger(), Runs(_source(), NAMED), Session()
    freezer = Freezer(refusal=_unusable())
    with pytest.raises(DomainError) as caught:
        _repeat(ledger, runs, session, freezer)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert freezer.calls == [{"connection_id": NAMED}], "asked for the named one and nothing else"
    assert ledger.fingerprints == [] and runs.created == [] and session.events == []


def test_a_repeat_of_a_named_run_with_no_freezer_is_refused_not_run_on_the_environment_adapter() -> None:
    ledger, runs, session = Ledger(), Runs(_source(), NAMED), Session()
    with pytest.raises(DomainError) as caught:
        _repeat(ledger, runs, session, None)
    assert dict(caught.value.detail_fields) == {"dependency": "executor_connection"}
    assert ledger.fingerprints == [] and runs.created == [] and session.events == []


def test_a_replayed_repeat_reads_no_journal_and_consults_no_freezer() -> None:
    ledger, runs, session, freezer = (
        Ledger(replay_run="run_01M2545JSD15ETSNNV904X993K"), Runs(_source(), NAMED), Session(),
        Freezer(),
    )
    started = _repeat(ledger, runs, session, freezer)
    assert started.replayed is True
    assert runs.journal_reads == [] and freezer.calls == [] and runs.created == []


# --- the journal reader ----------------------------------------------------------------------------


def test_the_journal_reader_asks_for_this_runs_choice_event_and_nothing_else() -> None:
    seen: list[tuple[str, dict[str, Any]]] = []

    class _Result:
        def __init__(self, value: Any) -> None:
            self._value = value

        def scalar_one_or_none(self) -> Any:
            return self._value

    class _Session:
        def __init__(self, value: Any) -> None:
            self._value = value

        def execute(self, statement: Any, parameters: Any) -> Any:
            seen.append((str(statement), dict(parameters)))
            return _Result(self._value)

    assert RunRepository().chosen_executor_connection(_Session(NAMED), SOURCE_RUN) == NAMED  # type: ignore[arg-type]
    assert RunRepository().chosen_executor_connection(_Session(None), SOURCE_RUN) is None  # type: ignore[arg-type]
    sql, parameters = seen[0]
    assert parameters == {"run_id": SOURCE_RUN, "event_type": EXECUTOR_CHOSEN_EVENT}
    assert "aggregate_type = 'AuditRun'" in sql and "aggregate_id = :run_id" in sql
    assert "event_type = :event_type" in sql
