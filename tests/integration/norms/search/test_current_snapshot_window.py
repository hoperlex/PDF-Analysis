"""The current snapshot against PostgreSQL (`W55A-SEARCH-01`; window: PostgreSQL ``57230``).

`W55-PLAN.md` section A3.2 through the shipped ``NormsSearchAdapter`` (and the reader
``auditmanager.norms.public.current_snapshot`` that `W55A-PIN-01` uses):

* both qualification conditions, each refused naming the missing half, and
  ``listNormSnapshots.qualified`` agreeing with the setter in every state;
* a stale ``expected_current`` is ``conflict`` (``stale_current_snapshot``);
* an already-current target is a replay and writes nothing;
* one history row per change, listed newest first and paged;
* the history refuses UPDATE and DELETE.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import DBAPIError

from auditmanager.bootstrap.adapters import NormsSearchAdapter
from auditmanager.norms.public import current_snapshot
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.norms.search.conftest import ADMIN, Corpus

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые"
GOST = "ГОСТ_10140-2003__Межгосударственный_стандарт__Плиты"
OTHER_ADMIN = "usr_01M2545JSD15ETSNNV904X992S"


def _adapter(corpus: Corpus) -> NormsSearchAdapter:
    return NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)


def _listed(corpus: Corpus, snapshot: str):
    page = _adapter(corpus).list_snapshots(cursor=None, limit=200)
    return next(item for item in page.items if item.norms_snapshot_id == snapshot)


def _try_designate(corpus: Corpus, snapshot: str, expected: str | None) -> DomainError | None:
    try:
        _adapter(corpus).set_current_snapshot(
            norms_snapshot_id=snapshot, expected_current=expected, user_uid=ADMIN
        )
    except DomainError as error:
        return error
    return None


def _history(corpus: Corpus) -> int:
    return corpus.scalar("SELECT count(*) FROM norm_current_snapshot_event")


def test_qualified_agrees_with_the_setter_in_every_state(corpus: Corpus) -> None:
    snapshot = corpus.snapshot(documents=2)
    first = corpus.document(snapshot, SP54, ref="sp54")
    second = corpus.document(snapshot, GOST, ref="gost")

    def state(expected_kind: str | None, build_state: str) -> None:
        listed = _listed(corpus, snapshot)
        assert listed.build_state.value == build_state
        error = _try_designate(corpus, snapshot, None)
        if expected_kind is None:
            assert error is None
            assert listed.qualified is True
        else:
            assert error is not None and error.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
            assert dict(error.detail_fields) == {
                "reference_kind": expected_kind, "norms_snapshot_id": snapshot,
            }
            assert listed.qualified is False
            assert _history(corpus) == 0

    state("norm_embedding_build", "absent")
    # A reliability-aware chunk build alone is not a build.
    corpus.build(snapshot, embedding="")
    state("norm_embedding_build", "incomplete")
    # A complete build over the profile that joins unreliable text is not condition (a).
    corpus.build(snapshot, chunking="characters-v1:1200")
    state("norm_embedding_build", "incomplete")
    corpus.build(snapshot, chunking="characters-v2:1200")
    state("norm_source", "complete")
    corpus.bind_pdf(first)
    # A binding of another anchor is not the document's PDF.
    corpus.bind_pdf(second, b"%PDF-1.7 crop", anchor="not-the-source-ref")
    state("norm_source", "complete")
    corpus.bind_pdf(second)
    state(None, "complete")
    listed = _listed(corpus, snapshot)
    assert (listed.qualified, listed.current) == (True, True)
    assert _history(corpus) == 1


def test_a_stale_expected_current_is_a_conflict(corpus: Corpus) -> None:
    first, second = corpus.snapshot(), corpus.snapshot()
    for snapshot in (first, second):
        corpus.document(snapshot, SP54, ref="sp54")
        corpus.qualify(snapshot)
    assert _try_designate(corpus, first, None) is None
    for stale in (None, second):
        error = _try_designate(corpus, second, stale)
        assert error is not None
        assert (error.code, dict(error.detail_fields)) == (
            ErrorCode.CONFLICT, {"conflict_reason": "stale_current_snapshot"}
        )
    assert _history(corpus) == 1
    assert _try_designate(corpus, second, first) is None
    assert _history(corpus) == 2


def test_one_history_row_per_change_and_a_replay_writes_none(corpus: Corpus) -> None:
    snapshots = [corpus.snapshot() for _ in range(3)]
    for snapshot in snapshots:
        corpus.document(snapshot, SP54, ref="sp54")
        corpus.qualify(snapshot)
    adapter = _adapter(corpus)
    expected: str | None = None
    for snapshot in snapshots:
        designated = adapter.set_current_snapshot(
            norms_snapshot_id=snapshot, expected_current=expected, user_uid=ADMIN
        )
        assert designated.norms_snapshot_id == snapshot
        expected = snapshot
    replay = adapter.set_current_snapshot(
        norms_snapshot_id=snapshot, expected_current=None, user_uid=OTHER_ADMIN
    )
    assert replay.designated_by == ADMIN  # the designation answered, not a new one
    assert _history(corpus) == 3

    with corpus.session_factory() as session:
        current = current_snapshot(session)
    assert current is not None and current.norms_snapshot_id == snapshots[-1]
    assert current.designated_at == replay.designated_at

    first_page = adapter.list_snapshot_events(cursor=None, limit=2)
    rest = adapter.list_snapshot_events(cursor=first_page.page.next_cursor, limit=2)
    assert rest.page.next_cursor is None
    events = first_page.items + rest.items
    assert [(e.from_norms_snapshot_id, e.to_norms_snapshot_id) for e in events] == [
        (snapshots[1], snapshots[2]), (snapshots[0], snapshots[1]), (None, snapshots[0]),
    ]
    assert {e.actor_user_uid for e in events} == {ADMIN}


def test_an_unknown_target_is_not_found(corpus: Corpus) -> None:
    error = _try_designate(corpus, "ns_01ARZ3NDEKTSV4RRFFQ69G5FAV", None)
    assert error is not None
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.NOT_FOUND, {"aggregate_type": "NormsSnapshot"}
    )


def test_the_history_is_append_only(corpus: Corpus) -> None:
    snapshot = corpus.snapshot()
    corpus.document(snapshot, SP54, ref="sp54")
    corpus.qualify(snapshot)
    assert _try_designate(corpus, snapshot, None) is None
    for statement, parameters in (
        ("UPDATE norm_current_snapshot_event SET actor_user_uid = :a", {"a": OTHER_ADMIN}),
        ("DELETE FROM norm_current_snapshot_event", {}),
        ("DELETE FROM norm_current_snapshot", {}),
    ):
        with pytest.raises(DBAPIError):
            corpus.run(statement, **parameters)
    assert _history(corpus) == 1
