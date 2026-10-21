"""`D-158` -- the bulkhead of ``searchNorms``, with no database.

The measured half (ten slow searches against a real pool) is
``tests/integration/norms/search/test_search_bulkhead.py``; this file pins the counter, the typed
refusal, the slot's return on every exit, the relation of the cap to the pool, and that
``search()`` consults the process's bulkhead before it touches a connection.
"""

from __future__ import annotations

import dataclasses
import threading
import time

import pytest

from auditmanager.norms.search import service
from auditmanager.norms.search.capacity import (
    MAX_CONCURRENT_SEARCHES,
    SEARCH_BULKHEAD,
    SEARCH_CAPACITY_DEPENDENCY,
    SearchBulkhead,
)
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.errors import DomainError, ErrorCode


def _busy(bulkhead: SearchBulkhead) -> DomainError:
    with pytest.raises(DomainError) as caught:
        with bulkhead.admit():
            pytest.fail("a saturated bulkhead admitted a search")
    return caught.value


def test_it_admits_its_capacity_and_refuses_the_next_with_the_typed_error() -> None:
    bulkhead = SearchBulkhead(2)
    with bulkhead.admit(), bulkhead.admit():
        assert bulkhead.in_flight == 2
        refusal = _busy(bulkhead)
        assert refusal.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert refusal.detail_fields == {"dependency": SEARCH_CAPACITY_DEPENDENCY}
        assert refusal.envelope("cid").http_status == 503
        assert bulkhead.in_flight == 2, "a refusal must not take or leak a slot"
    assert bulkhead.in_flight == 0
    with bulkhead.admit():
        assert bulkhead.in_flight == 1


@pytest.mark.parametrize(
    "failure",
    [
        DomainError(ErrorCode.VALIDATION_FAILED, field="q", constraint="norms_search_too_broad"),
        RuntimeError("the driver failed"),
        KeyboardInterrupt(),
    ],
    ids=["a typed refusal", "an unexpected error", "an interrupt"],
)
def test_the_slot_comes_back_however_the_search_ends(failure: BaseException) -> None:
    bulkhead = SearchBulkhead(1)
    with pytest.raises(type(failure)):
        with bulkhead.admit():
            raise failure
    assert bulkhead.in_flight == 0
    with bulkhead.admit():
        pass


def test_a_refusal_never_waits_for_a_slot() -> None:
    bulkhead = SearchBulkhead(1)
    with bulkhead.admit():
        began = time.monotonic()
        _busy(bulkhead)
        assert time.monotonic() - began < 0.2, "a refused search must not queue behind a slot"


def test_under_contention_no_more_than_the_capacity_is_ever_inside() -> None:
    bulkhead = SearchBulkhead(MAX_CONCURRENT_SEARCHES)
    inside = 0
    peak = 0
    admitted = 0
    refused = 0
    guard = threading.Lock()
    start = threading.Barrier(64)

    def contend() -> None:
        nonlocal inside, peak, admitted, refused
        start.wait()
        try:
            with bulkhead.admit():
                with guard:
                    inside += 1
                    peak = max(peak, inside)
                    admitted += 1
                time.sleep(0.01)
                with guard:
                    inside -= 1
        except DomainError:
            with guard:
                refused += 1

    threads = [threading.Thread(target=contend) for _ in range(64)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert peak <= MAX_CONCURRENT_SEARCHES
    assert admitted >= 1 and admitted + refused == 64
    assert bulkhead.in_flight == 0


def test_a_slot_that_was_never_taken_cannot_be_given_back() -> None:
    with pytest.raises(AssertionError):
        SearchBulkhead(1).release()


@pytest.mark.parametrize("capacity", [0, -1])
def test_a_bulkhead_admits_at_least_one_search(capacity: int) -> None:
    with pytest.raises(ValueError):
        SearchBulkhead(capacity)


def test_the_cap_leaves_at_least_half_the_pool_to_every_other_operation() -> None:
    """The figure is a property of the pool beside it: shrink the pool or raise the cap until
    they disagree and this fails, instead of the next rehearsal finding out."""
    defaults = {f.name: f.default for f in dataclasses.fields(DatabaseSettings)}
    pool = defaults["pool_size"] + defaults["max_overflow"]
    assert pool == 10
    assert 2 * MAX_CONCURRENT_SEARCHES <= pool


class _NoConnection:
    """A session that fails the test if anything asks it for a connection."""

    def execute(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - the failure
        raise AssertionError("a refused search took a connection")


def test_search_is_refused_at_its_entry_before_any_statement() -> None:
    bulkhead = SearchBulkhead(1)
    with bulkhead.admit():
        with pytest.raises(DomainError) as caught:
            service.search(
                _NoConnection(),  # type: ignore[arg-type]
                q="лестницы", norms_snapshot_id=None, cursor=None, limit=10,
                timeout_ms=1000, bulkhead=bulkhead,
            )
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_search_uses_the_processs_bulkhead_when_none_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert service.SEARCH_BULKHEAD is SEARCH_BULKHEAD
    saturated = SearchBulkhead(1)
    monkeypatch.setattr(service, "SEARCH_BULKHEAD", saturated)
    with saturated.admit():
        with pytest.raises(DomainError) as caught:
            service.search(
                _NoConnection(),  # type: ignore[arg-type]
                q="лестницы", norms_snapshot_id=None, cursor=None, limit=10, timeout_ms=1000,
            )
    assert caught.value.detail_fields == {"dependency": SEARCH_CAPACITY_DEPENDENCY}


def test_a_search_that_needs_no_connection_is_refused_for_its_text_first() -> None:
    """The cheap refusals come before the slot, so a blank query never costs a slot or a 503."""
    bulkhead = SearchBulkhead(1)
    with bulkhead.admit():
        with pytest.raises(DomainError) as caught:
            service.search(
                _NoConnection(),  # type: ignore[arg-type]
                q="   ", norms_snapshot_id=None, cursor=None, limit=10,
                timeout_ms=1000, bulkhead=bulkhead,
            )
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
