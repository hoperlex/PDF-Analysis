"""`D-158` -- ten slow searches must not hold the API's whole connection pool.

``searchNorms`` runs on the API's pool: five connections plus five of overflow
(``shared/db/config.py``). A broad query holds its connection until ``statement_timeout`` cancels
it, so ten of them starve every other operation until the pool's own timeout (30 s in the
shipped settings, 2 s here so the control does not take half a minute). The bulkhead
(``norms/search/capacity.py``) admits four and refuses the rest *before* they take a
connection.

The scenario is real: a real PostgreSQL at the migration head, a real current snapshot, an
engine with the shipped pool shape, and the real ``search()`` entry. Only the *duration* is
arranged -- each admitted search sleeps inside the database, on its own connection, before
running its real statement -- because a broad query that is slow on purpose needs a corpus of
a size this suite does not build. The control runs the same ten searches through a bulkhead as
wide as the pool and shows the starvation the cap prevents, so the measurement can fail.
"""

from __future__ import annotations

import dataclasses
import threading
import time
from dataclasses import dataclass, field

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import TimeoutError as PoolTimeout

from auditmanager.norms.search import service
from auditmanager.norms.search.capacity import (
    MAX_CONCURRENT_SEARCHES,
    SEARCH_BULKHEAD,
    SEARCH_CAPACITY_DEPENDENCY,
    SearchBulkhead,
)
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.norms.search.conftest import Corpus

SEARCHES = 10
#: How long an admitted search holds its connection, and how long the pool lets another
#: operation wait for one. The hold outlasts the wait, so an uncapped pool starves the probe.
HOLD_SECONDS = 4.0
POOL_TIMEOUT_SECONDS = 1


@dataclass
class _Search:
    started: float = 0.0
    elapsed: float = 0.0
    hits: int | None = None
    error: DomainError | None = None
    thread: threading.Thread | None = None


@dataclass
class _Scenario:
    searches: list[_Search] = field(default_factory=list)
    probe_seconds: float = 0.0
    probe_error: BaseException | None = None
    probe_rows: int | None = None
    refused_checked_out: int | None = None


def _seed(corpus: Corpus) -> None:
    snapshot = corpus.snapshot()
    document = corpus.document(snapshot, "СП_54_13330_2022__Свод_правил__Здания_жилые")
    corpus.paragraph(document, "7.1.4 Лестницы жилых зданий должны иметь ограждения", ordinal=0)
    corpus.designate(snapshot)


def _saturate(engine: Engine, bulkhead: SearchBulkhead, monkeypatch: pytest.MonkeyPatch) -> _Scenario:
    real_rows = service._search_rows

    def slow_rows(session, parsed, snapshot, after, limit):
        # The sleep runs in the database, on the search's own connection, inside its
        # transaction: the connection is held exactly as a slow statement holds it.
        session.execute(text("SELECT pg_sleep(:seconds)"), {"seconds": HOLD_SECONDS})
        return real_rows(session, parsed, snapshot, after, limit)

    monkeypatch.setattr(service, "_search_rows", slow_rows)
    factory = create_session_factory(engine)
    scenario = _Scenario(searches=[_Search() for _ in range(SEARCHES)])

    def one(slot: _Search) -> None:
        slot.started = time.monotonic()
        try:
            with factory() as session:
                page = service.search(
                    session, q="лестницы", norms_snapshot_id=None, cursor=None, limit=10,
                    timeout_ms=30_000, bulkhead=bulkhead,
                )
                slot.hits = len(page.items)
        except DomainError as exc:
            slot.error = exc
        finally:
            slot.elapsed = time.monotonic() - slot.started

    for slot in scenario.searches:
        slot.thread = threading.Thread(target=one, args=(slot,))
        slot.thread.start()

    admitted = min(bulkhead.capacity, SEARCHES)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        refused = sum(1 for s in scenario.searches if s.error is not None)
        if engine.pool.checkedout() >= admitted and refused >= SEARCHES - admitted:
            break
        time.sleep(0.02)
    scenario.refused_checked_out = engine.pool.checkedout()

    # Another operation, at the same instant: the API's next request wants a connection.
    began = time.monotonic()
    try:
        with engine.connect() as connection:
            scenario.probe_rows = connection.execute(text("SELECT 1")).scalar_one()
    except PoolTimeout as exc:
        scenario.probe_error = exc
    scenario.probe_seconds = time.monotonic() - began

    for slot in scenario.searches:
        assert slot.thread is not None
        slot.thread.join(60)
        assert not slot.thread.is_alive(), "a search never finished"
    return scenario


@pytest.fixture
def pooled(search_database: DatabaseSettings, corpus: Corpus) -> Engine:
    """An engine with the API's pool shape (5 + 5) and a short pool timeout."""
    _seed(corpus)
    settings = dataclasses.replace(
        search_database, pool_size=5, max_overflow=5, pool_timeout=POOL_TIMEOUT_SECONDS
    )
    assert (settings.pool_size, settings.max_overflow) == (5, 5)
    engine = create_database_engine(settings)
    try:
        yield engine
    finally:
        engine.dispose()


def test_the_cap_leaves_the_pool_to_other_operations(
    pooled: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    bulkhead = SearchBulkhead()  # the shipped capacity, on a fresh counter
    assert bulkhead.capacity == MAX_CONCURRENT_SEARCHES == SEARCH_BULKHEAD.capacity

    scenario = _saturate(pooled, bulkhead, monkeypatch)

    served = [s for s in scenario.searches if s.error is None]
    refused = [s for s in scenario.searches if s.error is not None]
    assert len(served) == MAX_CONCURRENT_SEARCHES, [s.error for s in refused]
    assert all(s.hits == 1 for s in served), "an admitted search must still return its real hits"
    assert len(refused) == SEARCHES - MAX_CONCURRENT_SEARCHES
    for slot in refused:
        assert slot.error is not None
        assert slot.error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert slot.error.detail_fields == {"dependency": SEARCH_CAPACITY_DEPENDENCY}
        # Refused at the entry: no connection was taken and none was waited for.
        assert slot.elapsed < 1.0, slot.elapsed
    # While the admitted four held their connections the pool had six left, and another
    # operation got one at once instead of waiting out the pool timeout.
    assert scenario.refused_checked_out == MAX_CONCURRENT_SEARCHES
    assert scenario.probe_error is None, scenario.probe_error
    assert scenario.probe_rows == 1
    assert scenario.probe_seconds < 0.5, scenario.probe_seconds
    assert bulkhead.in_flight == 0, "a slot was not given back"


def test_control_without_the_cap_ten_searches_starve_the_pool(
    pooled: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect, measured: a bulkhead as wide as the pool is no cap, and the eleventh
    connection request fails after the pool timeout while the searches hold all ten."""
    scenario = _saturate(pooled, SearchBulkhead(SEARCHES), monkeypatch)

    assert all(s.error is None for s in scenario.searches), [s.error for s in scenario.searches]
    assert scenario.refused_checked_out == SEARCHES
    assert isinstance(scenario.probe_error, PoolTimeout), scenario.probe_error
    assert scenario.probe_seconds >= POOL_TIMEOUT_SECONDS * 0.9, scenario.probe_seconds
