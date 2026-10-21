"""A concurrency cap for ``searchNorms``, so one operation cannot take the API's whole pool.

`D-158` (`W55A-JUDGE-X` M6). ``searchNorms`` runs on the API's connection pool -- five
connections plus five of overflow, with a 30 s ``pool_timeout`` (``shared/db/config.py``).
A broad query (a negation no index serves) runs until ``AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS``
cancels it, so ten of them hold every connection for that whole time. Every other operation
then waits for a connection and fails after 30 s.

The cap is a **bulkhead**: at most :data:`MAX_CONCURRENT_SEARCHES` searches hold a connection at
once in one API process, and the next one is refused at the entry, before it takes a
connection, as the existing typed ``dependency_unavailable`` (``503``, retryable, declared by
``searchNorms``), with ``details.dependency: "norms_search_capacity"``. It **never waits**:
a waiting search is a parked worker thread that the API's other synchronous operations need,
and a queue in front of a pool is how the pool's own timeout comes back as a longer one. The
shape is :class:`~auditmanager.api.routers.multipart.UploadGate`'s: admit or refuse.

The bound is four of ten. Six connections stay for everything else -- a refused search holds
none -- and four is enough that one reviewer's typing, with a few requests in flight, is not
refused. It is a constant and not a setting: a setting would be a new environment variable and
a change to ``bootstrap/settings.py``, and the figure is a property of the pool beside it.
``tests/unit/norms/test_search_capacity.py`` fails when the pool is shrunk or the cap raised
until the two disagree.

State is per process, as the pool is. A second API process has its own pool and its own cap.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MAX_CONCURRENT_SEARCHES",
    "SEARCH_BULKHEAD",
    "SEARCH_CAPACITY_DEPENDENCY",
    "SearchBulkhead",
]

#: Searches that may hold a connection at once in one API process. Of a pool of ten.
MAX_CONCURRENT_SEARCHES: Final[int] = 4

#: ``details.dependency`` of the refusal: a stable class name and never a count, as
#: ``upload_capacity`` is for uploads.
SEARCH_CAPACITY_DEPENDENCY: Final[str] = "norms_search_capacity"


class SearchBulkhead:
    """A counter of searches in flight that never waits: it admits or it refuses."""

    __slots__ = ("capacity", "_in_flight", "_lock")

    def __init__(self, capacity: int = MAX_CONCURRENT_SEARCHES) -> None:
        if capacity < 1:
            raise ValueError("a search bulkhead admits at least one search")
        self.capacity = capacity
        self._in_flight = 0
        self._lock = threading.Lock()

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def try_acquire(self) -> bool:
        with self._lock:
            if self._in_flight >= self.capacity:
                return False
            self._in_flight += 1
            return True

    def release(self) -> None:
        with self._lock:
            assert self._in_flight > 0, "a search slot was released that was never taken"
            self._in_flight -= 1

    @contextmanager
    def admit(self) -> Iterator[None]:
        """Hold a slot for the body, or raise the typed busy refusal before it runs.

        The slot is given back however the body ends: a result, a typed refusal, a
        cancelled statement or any other exception.
        """
        if not self.try_acquire():
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=SEARCH_CAPACITY_DEPENDENCY
            )
        try:
            yield
        finally:
            self.release()


#: The one bulkhead of this process's searches.
SEARCH_BULKHEAD: Final[SearchBulkhead] = SearchBulkhead()
