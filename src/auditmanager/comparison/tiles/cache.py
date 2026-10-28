"""A byte-budgeted LRU in which a key is loaded once at a time.

`CMP-VIEWER-01`. A viewer asks for a dozen tiles of one pair in the same instant; each needs the same mask and the same
few archives. Without a cache every request would download and inflate them again; without single-flight a dozen
threads would do it at once and hold a dozen copies. The cache is bounded by BYTES (a 2A0 mask is 40 MB), an entry
larger than the whole budget is returned but not kept, and a loader that raises caches nothing.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

__all__ = ["ByteCache"]

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class _Flight:
    __slots__ = ("done",)

    def __init__(self) -> None:
        self.done = threading.Event()


class ByteCache(Generic[K, V]):
    def __init__(self, capacity_bytes: int) -> None:
        self._capacity = capacity_bytes
        self._lock = threading.Lock()
        self._entries: OrderedDict[K, tuple[V, int]] = OrderedDict()
        self._flights: dict[K, _Flight] = {}
        self._bytes = 0
        self.loads = 0

    @property
    def size_bytes(self) -> int:
        with self._lock:
            return self._bytes

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def get_or_load(self, key: K, loader: Callable[[], tuple[V, int]]) -> V:
        """The value of ``key``, loading it with ``loader() -> (value, size in bytes)`` if no thread has."""
        while True:
            with self._lock:
                entry = self._entries.get(key)
                if entry is not None:
                    self._entries.move_to_end(key)
                    return entry[0]
                flight = self._flights.get(key)
                if flight is None:
                    flight = self._flights[key] = _Flight()
                    mine = True
                else:
                    mine = False
            if not mine:
                flight.done.wait()
                continue  # the loader finished (or failed): look again, and load it ourselves if it left nothing
            try:
                value, size = loader()
                with self._lock:
                    self.loads += 1
                    if size <= self._capacity:
                        self._entries[key] = (value, size)
                        self._bytes += size
                        while self._bytes > self._capacity:
                            _, (_, evicted) = self._entries.popitem(last=False)
                            self._bytes -= evicted
                return value
            finally:
                with self._lock:
                    self._flights.pop(key, None)
                flight.done.set()
