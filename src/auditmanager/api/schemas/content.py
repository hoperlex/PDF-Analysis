"""Streamed content: one requested byte range, and what a port hands back to stream.

`W55A-SEAL-01` (`W55-PLAN.md` section A3.5; owner ruling R-115). The PDF streams --
``streamDocumentVersionContent`` and ``streamNormDocumentContent`` -- both honour one
``Range``. This module is the shape between their routers and their ports, and nothing
else: it reaches no database, no object store and no clock.

* :class:`ByteRange` is the **syntax** of one ``Range`` header, parsed before the port is
  called. Resolving it against a size is :meth:`ByteRange.resolve`, called by the port once
  it knows the object's size and **before** it opens the object, so an unsatisfiable range
  stays the ``422`` it has always been and a storage failure stays a typed ``500``/``503``
  rather than a broken stream.
* :class:`StreamedContent` is what a port returns: the size, the window it serves (``None``
  for the whole object) and an iterator of chunks of at most :data:`CONTENT_CHUNK_BYTES`.
  The iterator is consumed by
  :class:`~auditmanager.api.routers.wire.StreamingWireResponse` after the status line is
  sent, so everything that can still refuse must have refused before it is returned.

The integrity rule (R-115) belongs to the port's implementation, not to this shape: a full
read hashes while streaming and holds back its last chunk until the digest matches, and on a
mismatch stops short, so the client receives fewer bytes than ``Content-Length``; a ranged
read relies on recorded verification.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CONTENT_CHUNK_BYTES",
    "PDF_MEDIA_TYPE",
    "ByteRange",
    "StreamedContent",
]

#: The largest chunk an implementation yields. Bounded so a ranged or full read never holds
#: an object in memory; 256 KiB keeps the number of ASGI sends per megabyte small.
CONTENT_CHUNK_BYTES: Final[int] = 256 * 1024

PDF_MEDIA_TYPE: Final[str] = "application/pdf"

#: ``bytes=<first>-<last>`` with an optional open end. A multi-range request is not served:
#: the frozen 206 declares one ``application/pdf`` body, and a multipart/byteranges response
#: would not be that shape.
_RANGE: Final[re.Pattern[str]] = re.compile(r"^bytes=(\d*)-(\d*)$")


@dataclass(frozen=True, slots=True)
class ByteRange:
    """One requested range: ``first``/``last`` inclusive, either open, never both.

    ``first is None`` is a suffix range (the final ``last`` bytes); ``last is None`` is an
    open end.
    """

    first: int | None
    last: int | None

    @classmethod
    def parse(cls, header: str) -> ByteRange:
        """The syntax only. A malformed header is ``validation_failed`` (``format``)."""
        match = _RANGE.match(header.strip())
        if match is None:
            raise _refused("format")
        first, last = match.group(1), match.group(2)
        if first == "" and last == "":
            raise _refused("format")
        return cls(int(first) if first else None, int(last) if last else None)

    def resolve(self, size: int) -> tuple[int, int]:
        """The inclusive window this range selects from ``size`` bytes.

        An unsatisfiable range is ``validation_failed`` (``unsatisfiable``) rather than a
        silent full body: a viewer that asked for page 40 of a 30-page document has a bug,
        and answering with the whole file hides it behind a much larger download.
        """
        if self.first is None:
            length = self.last or 0
            if length == 0:
                raise _refused("unsatisfiable")
            start, end = max(0, size - length), size - 1
        else:
            start = self.first
            end = size - 1 if self.last is None else min(self.last, size - 1)
        if size == 0 or start >= size or start > end:
            raise _refused("unsatisfiable")
        return start, end


@dataclass(frozen=True, slots=True)
class StreamedContent:
    """What a content port returns: everything the status line needs, and the body."""

    media_type: str
    #: The whole object's size in bytes, which a ``206`` states after the slash.
    total_size: int
    #: The inclusive window served, or ``None`` for the whole object (``200``).
    window: tuple[int, int] | None
    chunks: Iterator[bytes]

    @property
    def content_length(self) -> int:
        if self.window is None:
            return self.total_size
        return self.window[1] - self.window[0] + 1


def _refused(constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The Range header is not a single satisfiable byte range.",
        field="Range",
        constraint=constraint,
    )
