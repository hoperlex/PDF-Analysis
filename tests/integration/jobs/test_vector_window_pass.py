"""`EMBED-01` (ADR-0029 decision 8, plan-v5 section 5): the night window's pass, against real PostgreSQL and a pretend host.

The pass is the shipped ``VectorWindowPass``; the host is the files of the exchange directory (``vector_window_support``) and the container's answer is
the REAL ``embed-texts`` answer of the norms package over a fake encoder. What is shown, each by a night that goes right next to one that does not:

* the backfill queues the cases that have no intent, once, deduplicated by the digest of the text, and not a forgotten case;
* **a night**: the window opens only with a live timer of the host, the stand drains, the batch goes out with one entry per distinct text, the answer
  comes back, the vectors are stored (digest, model revision, dimensions, unit norm) and the intents are done; the window closes and is not used twice;
* **draining holds the stand** (the hint offers no run) and waits for what runs; a window that ends before it finishes is SKIPPED, loudly;
* **every way a night can fail is a skip with its reason**, journalled and shown, and the intents stay for the next night: the container killed at its
  limit, stopped at the deadline, no image, an error, an answer this stand will not take, a timer that is silent, a window that ended while encoding;
* a text over 512 tokens becomes ``poisoned`` with its reason and is counted for the administrator; a vector that is not unit norm is retried and
  poisoned on the fifth failure; a case forgotten after the export takes no vector;
* a pause stops the window before it starts and stops the container if it already has; the queue fills regardless.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import JobRepository
from auditmanager.precedents.public import Exchange, VectorControlService, VectorWindowPass
from auditmanager.precedents.vectors import repository as store
from auditmanager.precedents.vectors.intents import build_finding_view, input_sha256

pytestmark = pytest.mark.usefixtures("quiet_queue")


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load("embed01_connection_limit_support", "connection_limit_support.py")
w = _load("embed01_vector_window_support", "vector_window_support.py")


@pytest.fixture(autouse=True)
def _control_back(sessions: sessionmaker[Session]) -> object:
    w.reset_control(sessions)
    with sessions() as session:
        assert store.running_work(session) == 0, "a suite left work running: the drain below would wait for it"
    yield
    w.reset_control(sessions)


@pytest.fixture
def exchange(tmp_path: Path) -> Exchange:
    (tmp_path / "ex").mkdir()
    return Exchange(tmp_path / "ex")


@pytest.fixture
def made(sessions: sessionmaker[Session], exchange: Exchange) -> Any:
    def build(**kwargs: Any) -> VectorWindowPass:
        return VectorWindowPass(sessions, exchange, interval_seconds=0, **kwargs)
    return build


def finding(tag: str) -> str:
    return f"Ночная находка {tag}: высота помещения менее нормы"


def view_digest(finding_text: str, recommendation: str = "Привести в соответствие.", category: str = "dimensions") -> str:
    return input_sha256(build_finding_view(category=category, finding_text=finding_text, recommendation_text=recommendation))


def open_the_night(vector_pass: VectorWindowPass, exchange: Exchange, at: datetime = w.INSIDE) -> None:
    """The host is alive, the window is open: the pass drains and exports in one call."""
    w.heartbeat(exchange.directory, at)
    vector_pass.run(at)


# -- the backfill ---------------------------------------------------------------------------------------------------------


def test_the_backfill_queues_each_case_once_deduplicates_by_digest_and_leaves_a_forgotten_case_out(
    engine: Engine, sessions: sessionmaker[Session], made: Any,
) -> None:
    tag = "backfill-1"
    first, same, other, gone = (w.add_case(engine, finding=finding(tag)), w.add_case(engine, finding=finding(tag)),
                                w.add_case(engine, finding=finding(tag + "-b")), w.add_case(engine, finding=finding(tag + "-c")))
    w.forget(engine, gone)
    vector_pass = made()
    vector_pass.run(w.NOON)
    found = w.intents_of(sessions, [first, same, other, gone])
    assert set(found) == {first, same, other}, "a forgotten case takes no new row"
    assert found[first]["state"] == "pending" and found[first]["digest"] == view_digest(finding(tag))
    assert found[first]["digest"] == found[same]["digest"] != found[other]["digest"], "the same text is the same digest"
    before = w.intents_of(sessions, [first, same, other])
    vector_pass.run(w.NOON)
    assert w.intents_of(sessions, [first, same, other]) == before, "the backfill is idempotent"


def test_the_queue_fills_while_the_vectors_are_paused(engine: Engine, sessions: sessionmaker[Session], made: Any) -> None:
    with sessions() as session:
        store.lock_control(session)
        store.set_paused(session, paused=True, actor=_admin(session))
        session.commit()
    case = w.add_case(engine, finding=finding("paused-fill"))
    made().run(w.NOON)
    assert w.intents_of(sessions, [case])[case]["state"] == "pending"


def _admin(session: Session) -> str:
    return str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())


# -- a night that goes right ---------------------------------------------------------------------------------------------------


def test_a_night_opens_drains_exports_imports_and_closes(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    tag = "night-1"
    cases = [w.add_case(engine, finding=finding(tag)), w.add_case(engine, finding=finding(tag)), w.add_case(engine, finding=finding(tag + "-b"))]
    mark = w.last_event_no(sessions)
    imported: list[str] = []
    vector_pass = made(after_import=lambda: imported.append("followed"))
    open_the_night(vector_pass, exchange)
    assert w.control(sessions)["state"] == "encoding"
    request = w.request_of(exchange.directory)
    ids = {item["id"] for item in request["texts"]}
    assert {view_digest(finding(tag)), view_digest(finding(tag + "-b"))} <= ids
    assert len(ids) == len(request["texts"]), "one entry per distinct text"
    assert int((exchange.directory / "deadline").read_text(encoding="ascii")) == int(datetime.fromisoformat("2026-11-11T06:00:00+05:00").timestamp())
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions) == {"paused": False, "state": "closed", "reason": None}
    assert [name for name, _ in w.journal(sessions, since=mark)] == ["window_draining", "window_encoding", "window_closed"]
    stored = w.embeddings_of(sessions, cases)
    assert set(stored) == set(cases)
    for case in cases:
        assert stored[case]["dims"] == 1024 and abs(stored[case]["norm"] - 1.0) <= 0.0001
        assert stored[case]["model"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert stored[cases[0]]["vector_digest"] == stored[cases[1]]["vector_digest"], "the two cases of one text have one vector"
    assert {v["state"] for v in w.intents_of(sessions, cases).values()} == {"done"}
    assert imported == ["followed"], "the pass over fresh runs follows an import"
    assert not [p.name for p in exchange.directory.iterdir() if p.name != "heartbeat"], "the worker clears the round"


def test_a_long_queue_is_several_rounds_of_one_night_and_each_round_is_kept_when_the_window_is_cut_short(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    with sessions() as session:   # the queue is this test's own: whatever other suites left is set aside
        session.execute(text(
            "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = 'test_cleanup', state_changed_at = clock_timestamp() "
            "WHERE state = 'pending'"))
        session.commit()
    cases = [w.add_case(engine, finding=finding(f"rounds-{index}")) for index in range(5)]
    vector_pass = made(round_limit=2)
    open_the_night(vector_pass, exchange)
    assert len(w.request_of(exchange.directory)["texts"]) == 2, "a round is bounded: the encoder keeps no partial answer"
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "encoding" and len(w.request_of(exchange.directory)["texts"]) == 2, "the next round is out in the same night"
    assert sum(1 for v in w.intents_of(sessions, cases).values() if v["state"] == "done") == 2, "the first round is kept"
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "encoding" and len(w.request_of(exchange.directory)["texts"]) == 1
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed", "nothing left: the window closes"
    assert {v["state"] for v in w.intents_of(sessions, cases).values()} == {"done"}


def test_a_window_with_too_little_left_does_not_start_another_round_and_a_failed_round_does_not_repeat(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    with sessions() as session:
        session.execute(text(
            "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = 'test_cleanup', state_changed_at = clock_timestamp() "
            "WHERE state = 'pending'"))
        session.commit()
    cases = [w.add_case(engine, finding=finding(f"late-round-{index}")) for index in range(3)]
    vector_pass = made(round_limit=2)
    open_the_night(vector_pass, exchange)
    w.host_answers(exchange.directory)
    nearly_over = datetime.fromisoformat("2026-11-11T05:50:00+05:00")   # ten minutes left: a round needs twenty
    vector_pass.run(nearly_over)
    assert w.control(sessions)["state"] == "closed"
    assert sorted(v["state"] for v in w.intents_of(sessions, cases).values()) == ["done", "done", "pending"], "the third waits for the next night"


def test_the_window_is_used_once_a_night_even_if_more_is_queued_after_it_closed(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("once"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed"
    late = w.add_case(engine, finding=finding("once-late"))
    w.heartbeat(exchange.directory, w.INSIDE)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed", "the stand is not stopped a second time the same night"
    assert w.intents_of(sessions, [late])[late]["state"] == "pending", "it waits for the next night"


def test_nothing_queued_opens_nothing(sessions: sessionmaker[Session], made: Any, exchange: Exchange) -> None:
    with sessions() as session:   # whatever other suites queued is set aside (a poisoned intent is a row, and this database is a throwaway)
        session.execute(text(
            "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = 'test_cleanup', state_changed_at = clock_timestamp() "
            "WHERE state = 'pending'"))
        session.commit()
    w.heartbeat(exchange.directory, w.INSIDE)
    step = made().run(w.INSIDE).last
    assert step.what == "nothing queued" and w.control(sessions)["state"] == "closed", "a night with nothing to encode does not stop the stand"


def test_outside_the_window_the_machine_is_idle(engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange) -> None:
    w.add_case(engine, finding=finding("outside"))
    w.heartbeat(exchange.directory, w.NOON)
    step = made().run(w.NOON).last
    assert step.what == "outside the window" and w.control(sessions)["state"] == "closed"


# -- draining holds the stand --------------------------------------------------------------------------------------------------


def test_draining_offers_no_run_waits_for_the_running_one_and_exports_when_it_ends(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("drain"))
    running = support.queue_run(sessions, None)
    authority = support.claim(sessions, running)
    try:
        vector_pass = made()
        open_the_night(vector_pass, exchange)
        assert w.control(sessions)["state"] == "draining", "a run is running: the stand waits for it"
        waiting = support.queue_run(sessions, None)
        try:
            with sessions() as session:
                assert JobRepository().next_queued_run(session) is None, "and takes no new run meanwhile"
            vector_pass.run(w.INSIDE)
            assert w.control(sessions)["state"] == "draining" and not exchange.has_request()
            support.finish(sessions, authority)
            vector_pass.run(w.INSIDE)
            assert w.control(sessions)["state"] == "encoding" and exchange.has_request()
            with sessions() as session:
                assert JobRepository().next_queued_run(session) is None, "still none while the encoder runs"
        finally:
            support.cancel(sessions, waiting)
    finally:
        support.cancel(sessions, running)


def test_a_window_that_ends_before_the_running_work_does_is_skipped_loudly(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange, caplog: pytest.LogCaptureFixture,
) -> None:
    case = w.add_case(engine, finding=finding("late-drain"))
    running = support.queue_run(sessions, None)
    support.claim(sessions, running)
    mark = w.last_event_no(sessions)
    try:
        vector_pass = made()
        open_the_night(vector_pass, exchange)
        assert w.control(sessions)["state"] == "draining"
        with caplog.at_level(logging.ERROR):
            vector_pass.run(w.AFTER)
        assert w.control(sessions) == {"paused": False, "state": "skipped", "reason": "runs_did_not_finish"}
        assert w.journal(sessions, since=mark)[-1] == ("window_skipped", "runs_did_not_finish")
        assert any("skipped" in record.message and "runs_did_not_finish" in record.message for record in caplog.records), "loud in the log too"
        assert not exchange.has_request()
        assert w.intents_of(sessions, [case])[case]["state"] == "pending", "the intents stay"
    finally:
        support.cancel(sessions, running)


# -- every way a night fails is a skip with its reason ---------------------------------------------------------------------------


@pytest.mark.parametrize(("status", "reason"), [
    (137, "encoder_out_of_memory"), (124, "encoder_timed_out"), (127, "encoder_image_missing"), (2, "encoder_failed"), (1, "encoder_failed"),
])
def test_a_container_that_did_not_finish_skips_the_window_with_its_reason_and_the_intents_stay(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange, caplog: pytest.LogCaptureFixture, status: int, reason: str,
) -> None:
    case = w.add_case(engine, finding=finding(f"fail-{status}"))
    mark = w.last_event_no(sessions)
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    w.host_answers(exchange.directory, exit_code=status, stderr="Killed")
    with caplog.at_level(logging.ERROR):
        vector_pass.run(w.INSIDE)
    assert w.control(sessions) == {"paused": False, "state": "skipped", "reason": reason}
    assert w.journal(sessions, since=mark)[-1] == ("window_skipped", reason)
    assert w.intents_of(sessions, [case])[case] == {"state": "pending", "attempts": 0, "reason": None, "digest": view_digest(finding(f"fail-{status}"))}
    assert not w.embeddings_of(sessions, [case])
    assert any(reason in record.message for record in caplog.records)
    assert not [p.name for p in exchange.directory.iterdir() if p.name != "heartbeat"]
    with sessions() as session:
        assert store.count_intents(session)[0] >= 1, "visible to the administrator as a queue that did not drain"


def test_the_next_night_repeats_what_a_skipped_one_left(engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange) -> None:
    case = w.add_case(engine, finding=finding("repeat"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    w.host_answers(exchange.directory, exit_code=137)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "skipped"
    next_night = datetime.fromisoformat("2026-11-12T02:00:00+05:00")
    w.heartbeat(exchange.directory, next_night)
    vector_pass.run(next_night)
    assert w.control(sessions)["state"] == "encoding"
    w.host_answers(exchange.directory)
    vector_pass.run(next_night)
    assert w.control(sessions)["state"] == "closed" and w.intents_of(sessions, [case])[case]["state"] == "done"


def test_a_silent_timer_skips_the_window_before_it_stops_the_stand(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("silent"))
    vector_pass = made()
    vector_pass.run(w.INSIDE)   # no heartbeat at all
    assert w.control(sessions) == {"paused": False, "state": "skipped", "reason": "host_timer_silent"}
    w.reset_control(sessions)
    w.heartbeat(exchange.directory, w.INSIDE, age_seconds=3600)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["reason"] == "host_timer_silent", "a heartbeat an hour old is a timer that is off"
    w.reset_control(sessions)
    w.heartbeat(exchange.directory, w.INSIDE, age_seconds=30)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "encoding"


def test_a_window_that_ends_while_the_container_runs_is_skipped_and_the_host_is_told_to_stop(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("overrun"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    vector_pass.run(w.AFTER)
    assert w.control(sessions) == {"paused": False, "state": "skipped", "reason": "window_ended_while_encoding"}
    assert (exchange.directory / "abort").exists(), "the host stops the container by this file"


def test_an_answer_this_stand_will_not_take_is_skipped_and_nothing_of_it_is_stored(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    case = w.add_case(engine, finding=finding("refused"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)

    def another_profile(response: dict[str, Any]) -> None:
        response["embedding_profile"] = "bge-m3-dense-v2"

    w.host_answers(exchange.directory, tamper=another_profile)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions) == {"paused": False, "state": "skipped", "reason": "import_refused"}
    assert not w.embeddings_of(sessions, [case]) and w.intents_of(sessions, [case])[case]["state"] == "pending"


def test_a_restarted_worker_picks_the_round_up_where_it_was(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    case = w.add_case(engine, finding=finding("restart"))
    open_the_night(made(), exchange)
    assert w.control(sessions)["state"] == "encoding"
    w.host_answers(exchange.directory)
    made().run(w.INSIDE)   # a new pass object: nothing is remembered but the database and the files
    assert w.control(sessions)["state"] == "closed" and w.intents_of(sessions, [case])[case]["state"] == "done"


def test_a_round_whose_request_went_missing_is_written_again(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("lost-request"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    (exchange.directory / "request.json").unlink()
    (exchange.directory / "deadline").unlink()
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "encoding" and exchange.has_request()


# -- what the answer holds ---------------------------------------------------------------------------------------------------------


def test_a_text_over_five_hundred_twelve_tokens_becomes_poisoned_with_its_reason_and_is_counted_for_the_administrator(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    long_case = w.add_case(engine, finding=finding("long"))
    short_case = w.add_case(engine, finding=finding("short"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    w.host_answers(exchange.directory, over_limit=[view_digest(finding("long"))])
    with sessions() as session:
        before = store.count_intents(session)[1]
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed"
    found = w.intents_of(sessions, [long_case, short_case])
    assert found[long_case]["state"] == "poisoned" and found[long_case]["reason"] == "token_limit_exceeded"
    assert found[short_case]["state"] == "done"
    assert set(w.embeddings_of(sessions, [long_case, short_case])) == {short_case}, "a text is never cut to fit"
    with sessions() as session:
        assert store.count_intents(session)[1] == before + 1
    service = VectorControlService(sessions, roles_of=lambda _s, _u: frozenset({"admin"}))
    assert service.get_vector_control(user_uid="usr_01ARZ3NDEKTSV4RRFFQ69G5FAV")["poisoned_intents"] >= 1


def test_a_vector_that_is_not_unit_norm_is_retried_and_poisoned_on_the_fifth_failure(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    case = w.add_case(engine, finding=finding("norm"))
    digest = view_digest(finding("norm"))
    vector_pass = made()
    for attempt in range(1, 6):
        night = datetime.fromisoformat(f"2026-11-{11 + attempt:02d}T02:00:00+05:00")
        w.heartbeat(exchange.directory, night)
        vector_pass.run(night)
        assert w.control(sessions)["state"] == "encoding"

        def not_unit(response: dict[str, Any]) -> None:
            import base64
            import hashlib
            import struct
            for entry in response["vectors"]:
                values = [2.0 * v for v in struct.unpack("!1024f", base64.b64decode(entry["vector"]))]
                packed = struct.pack("!1024f", *values)
                entry["vector"] = base64.b64encode(packed).decode("ascii")
                entry["vector_sha256"] = hashlib.sha256(packed).hexdigest()

        w.host_answers(exchange.directory, tamper=not_unit)
        vector_pass.run(night)
        found = w.intents_of(sessions, [case])[case]
        assert w.control(sessions)["state"] == "closed"
        assert found["attempts"] == attempt and not w.embeddings_of(sessions, [case])
        assert found["state"] == ("poisoned" if attempt == 5 else "pending")
    assert found["reason"] == "attempts_exhausted" and found["digest"] == digest


def test_a_case_forgotten_after_the_export_takes_no_vector_and_the_others_do(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    gone, kept = w.add_case(engine, finding=finding("gone")), w.add_case(engine, finding=finding("kept"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    w.forget(engine, gone)
    w.host_answers(exchange.directory)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed"
    assert not w.embeddings_of(sessions, [gone]) and set(w.embeddings_of(sessions, [kept])) == {kept}
    assert not w.intents_of(sessions, [gone])


# -- the pause -------------------------------------------------------------------------------------------------------------------


def test_a_pause_before_the_night_keeps_the_window_from_opening(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("pause-before"))
    with sessions() as session:
        store.lock_control(session)
        store.set_paused(session, paused=True, actor=_admin(session))
        session.commit()
    mark = w.last_event_no(sessions)
    open_the_night(made(), exchange)
    assert w.control(sessions) == {"paused": True, "state": "closed", "reason": None}
    assert w.journal(sessions, since=mark) == [], "the stand was never stopped: no window opened and closed again"


def test_a_pause_during_the_drain_closes_the_window_and_gives_the_stand_back(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    w.add_case(engine, finding=finding("pause-drain"))
    running = support.queue_run(sessions, None)
    support.claim(sessions, running)
    try:
        vector_pass = made()
        open_the_night(vector_pass, exchange)
        assert w.control(sessions)["state"] == "draining"
        with sessions() as session:
            store.lock_control(session)
            store.set_paused(session, paused=True, actor=_admin(session))
            session.commit()
        vector_pass.run(w.INSIDE)
        assert w.control(sessions)["state"] == "closed"
    finally:
        support.cancel(sessions, running)


def test_a_pause_while_the_container_runs_tells_the_host_to_stop_and_imports_nothing(
    engine: Engine, sessions: sessionmaker[Session], made: Any, exchange: Exchange,
) -> None:
    case = w.add_case(engine, finding=finding("pause-encode"))
    vector_pass = made()
    open_the_night(vector_pass, exchange)
    with sessions() as session:
        store.lock_control(session)
        store.set_paused(session, paused=True, actor=_admin(session))
        session.commit()
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "encoding" and (exchange.directory / "abort").exists(), "the host is told; the stand waits for its word"
    w.host_answers(exchange.directory, exit_code=130)
    vector_pass.run(w.INSIDE)
    assert w.control(sessions)["state"] == "closed" and not w.embeddings_of(sessions, [case])
    assert w.intents_of(sessions, [case])[case]["state"] == "pending"
