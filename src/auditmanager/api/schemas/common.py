"""Shared wire concerns: timestamps, page envelopes and the opaque cursor.

Every name here exists because ``contracts/api/v1/openapi.json`` declares a shape and
something has to produce exactly it. Nothing in this package reaches a database, a
service or an environment variable: a schema module turns a value into the frozen wire
shape and does nothing else.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final, Mapping, Sequence

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DEFAULT_LIMIT",
    "MAX_CURSOR",
    "MAX_LIMIT",
    "MIN_LIMIT",
    "Page",
    "decode_cursor",
    "encode_cursor",
    "page_body",
    "paginate",
    "timestamp",
]

#: ``#/components/parameters/Limit``: minimum 1, maximum 200, default 50. The bounds are
#: enforced by the declared ``limit`` query parameter -- see
#: :data:`auditmanager.api.routers.declarations.LimitParam`, which is also what puts them in
#: the served document. These are the same three numbers, named, for a reader of this
#: module: nothing here computes a bound from them.
MIN_LIMIT: Final[int] = 1
MAX_LIMIT: Final[int] = 200
DEFAULT_LIMIT: Final[int] = 50

#: ``#/components/schemas/Cursor``: 1..512 characters.
MAX_CURSOR: Final[int] = 512


def timestamp(value: datetime) -> str:
    """Render a timestamp as the frozen ``format: date-time``.

    A naive value is read as UTC rather than as local time: the database columns are
    ``timestamptz`` and a naive datetime reaching here means a driver handed one back
    without its zone, never that the instant was local.
    """
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def encode_cursor(sort_key: Sequence[str]) -> str:
    """Encode a page's last sort key as the opaque continuation token.

    It carries the **sort key and nothing else**, which is what the frozen ``Cursor``
    schema promises. In particular it never carries a row number or a sequence value:
    ``P02_SEAMS.md`` section 2.2 lists "database row number or sequence value exposed to
    a client" among the things that are never an identity, and section 5.3 repeats it
    for the decision ledger specifically.

    Base64url of a compact JSON array. Not encryption and not claimed to be: it is
    opaque to a client because a client has no reason to read it, not because reading it
    would reveal anything.
    """
    payload = json.dumps(list(sort_key), separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(raw: str) -> tuple[str, ...]:
    """Decode a continuation token, or refuse it as ``validation_failed``.

    A client never constructs one, so a token that does not decode is a malformed
    request rather than an empty page. Returning an empty page would silently restart
    the listing from the beginning, which reads to a caller as data loss.
    """
    if not raw or len(raw) > MAX_CURSOR:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The cursor parameter is not a continuation token from this API.",
            field="cursor",
            constraint="format",
        )
    padded = raw + "=" * (-len(raw) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The cursor parameter is not a continuation token from this API.",
            field="cursor",
            constraint="format",
        ) from None
    if not isinstance(decoded, list) or not all(isinstance(part, str) for part in decoded):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The cursor parameter is not a continuation token from this API.",
            field="cursor",
            constraint="format",
        )
    return tuple(decoded)


@dataclass(frozen=True, slots=True)
class Page:
    """One page of a growing list, and the token that continues it."""

    items: tuple[Any, ...]
    next_cursor: str | None


def paginate(
    rows: Sequence[Any],
    *,
    limit: int,
    cursor: str | None,
    sort_key: Any,
) -> Page:
    """Cut one page out of an ordered sequence.

    ``sort_key`` maps a row to its ordering tuple; the cursor carries the last one
    emitted, and the next page resumes at the row after it. Ordering is the caller's --
    this function never sorts, because the order is the producing query's contract and
    re-sorting here would hide a query that stopped honouring it.

    Resumption **locates** the cursor's key rather than comparing against it. A
    comparison would silently assume ascending order and quietly return the wrong page
    for a descending listing -- and the frozen document orders projects *newest first*,
    so that assumption would be wrong on the very first operation. Locating the key
    works for either direction, and a key that is no longer present yields an empty
    page rather than a page from the wrong end.
    """
    start = 0
    if cursor is not None:
        after = decode_cursor(cursor)
        start = len(rows)
        for index, row in enumerate(rows):
            if tuple(sort_key(row)) == after:
                start = index + 1
                break
    window = tuple(rows[start : start + limit])
    exhausted = start + limit >= len(rows)
    next_cursor = None if exhausted or not window else encode_cursor(sort_key(window[-1]))
    return Page(items=window, next_cursor=next_cursor)


def page_body(items: Sequence[Mapping[str, Any]], next_cursor: str | None) -> dict[str, Any]:
    """The ``{items, page: {next_cursor}}`` envelope every list response carries."""
    return {"items": list(items), "page": {"next_cursor": next_cursor}}
