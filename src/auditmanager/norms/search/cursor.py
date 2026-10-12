"""Continuation tokens for the norms reads (`W55-PLAN.md` section A3.4).

`W55A-SEARCH-01`. Every token is opaque to a client and carries **a position and nothing
else**: never a row number, an offset or a count. A search token also carries a binding --
the first 128 bits of SHA-256 over ``(q, snapshot)`` -- so a token issued for one query or
one snapshot is refused for another, rather than resuming somewhere meaningless. A token
that does not decode, or that names another query, is ``validation_failed`` on ``cursor``
(``format``): the caller is not continuing *this* listing.

The shape is base64url of a compact JSON array whose first element names the token's kind
and version. The length stays far below the contract's ``Cursor`` maximum (512): no part is
unbounded text -- the designation position is the document's identity, not its tokens.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DesignationPosition",
    "EventPosition",
    "MAX_CURSOR_CHARACTERS",
    "MAX_ORDINAL",
    "ParagraphPosition",
    "RankPosition",
    "SnapshotPosition",
    "decode_event_cursor",
    "decode_paragraph_cursor",
    "decode_search_cursor",
    "decode_snapshot_cursor",
    "encode_event_cursor",
    "encode_paragraph_cursor",
    "encode_search_cursor",
    "encode_snapshot_cursor",
    "query_binding",
    "rank_bits",
    "rank_from_bits",
]

#: ``#/components/schemas/Cursor``: 1..512 characters.
MAX_CURSOR_CHARACTERS: Final[int] = 512

#: The largest ``ordinal`` a token may carry: ``norm_paragraph.ordinal`` is a PostgreSQL
#: ``integer``. A larger one names no paragraph, and bound as ``CAST(... AS integer)`` it
#: would fail the statement (SQLSTATE 22003) instead of being refused here (`W55A-FIX`,
#: JUDGE-X M1).
MAX_ORDINAL: Final[int] = 2**31 - 1

_ULID: Final[str] = "[0-9A-HJKMNP-TV-Z]{26}"
_NPAR: Final[re.Pattern[str]] = re.compile(rf"^npar_{_ULID}$")
_NDOC: Final[re.Pattern[str]] = re.compile(rf"^ndoc_{_ULID}$")
_NS: Final[re.Pattern[str]] = re.compile(rf"^ns_{_ULID}$")
_EVT: Final[re.Pattern[str]] = re.compile(rf"^evt_{_ULID}$")
_BINDING: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")
_BITS: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{8}$")


def _refused() -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The cursor parameter is not a continuation token of this listing.",
        field="cursor",
        constraint="format",
    )


def _encode(parts: list[Any]) -> str:
    raw = json.dumps(parts, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(token) > MAX_CURSOR_CHARACTERS:  # pragma: no cover - bounded by construction
        raise RuntimeError("a norms cursor outgrew the contract's Cursor maximum")
    return token


def _decode(token: str, kind: str, length: int) -> list[Any]:
    if not isinstance(token, str) or not token or len(token) > MAX_CURSOR_CHARACTERS:
        raise _refused()
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        parts = json.loads(raw.decode("ascii"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise _refused() from None
    if not isinstance(parts, list) or len(parts) != length or parts[0] != kind:
        raise _refused()
    if _encode(parts) != token:
        # One position, one spelling: a re-padded or re-ordered token is not ours.
        raise _refused()
    return parts


def _string(value: Any, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise _refused()
    return value


def _ordinal(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_ORDINAL:
        raise _refused()
    return value


# --- the search ----------------------------------------------------------------------------


def query_binding(q: str, norms_snapshot_id: str) -> str:
    """What a search token is bound to: the query text and the snapshot it searched."""
    material = json.dumps([q, norms_snapshot_id], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def rank_bits(rank: float) -> str:
    """The exact ``float4`` bits of a ``ts_rank_cd`` value, as eight hex digits."""
    return struct.pack(">f", rank).hex()


def rank_from_bits(bits: str) -> float:
    (value,) = struct.unpack(">f", bytes.fromhex(bits))
    return value


@dataclass(frozen=True, slots=True)
class RankPosition:
    """The last hit of a ranked page: its rank (``float4``, exact) and paragraph."""

    rank: float
    norm_paragraph_id: str


@dataclass(frozen=True, slots=True)
class DesignationPosition:
    """The last hit of an ordered page: its document, ``ordinal`` and paragraph."""

    norm_document_id: str
    ordinal: int
    norm_paragraph_id: str


def encode_search_cursor(binding: str, position: RankPosition | DesignationPosition) -> str:
    if isinstance(position, RankPosition):
        return _encode(["s1r", binding, rank_bits(position.rank), position.norm_paragraph_id])
    return _encode([
        "s1d", binding, position.norm_document_id, position.ordinal,
        position.norm_paragraph_id,
    ])


def decode_search_cursor(
    token: str, *, binding: str, ranked: bool
) -> RankPosition | DesignationPosition:
    """The position ``token`` resumes after, refused unless it was issued for ``binding``."""
    if ranked:
        parts = _decode(token, "s1r", 4)
        _string(parts[2], _BITS)
        position: RankPosition | DesignationPosition = RankPosition(
            rank_from_bits(parts[2]), _string(parts[3], _NPAR)
        )
    else:
        parts = _decode(token, "s1d", 5)
        position = DesignationPosition(
            _string(parts[2], _NDOC), _ordinal(parts[3]), _string(parts[4], _NPAR)
        )
    if _string(parts[1], _BINDING) != binding:
        raise _refused()
    return position


# --- the document's paragraphs -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParagraphPosition:
    norm_document_id: str
    ordinal: int


def encode_paragraph_cursor(position: ParagraphPosition) -> str:
    return _encode(["p1", position.norm_document_id, position.ordinal])


def decode_paragraph_cursor(token: str, *, norm_document_id: str) -> ParagraphPosition:
    parts = _decode(token, "p1", 3)
    if _string(parts[1], _NDOC) != norm_document_id:
        raise _refused()
    return ParagraphPosition(parts[1], _ordinal(parts[2]))


# --- the snapshots and their history -------------------------------------------------------


def _instant(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_instant(value: Any) -> datetime:
    """An instant exactly as :func:`_instant` spells it, or a refusal.

    An instant at the edge of :class:`datetime`'s range with an offset -- year 1 at ``+05:00``,
    year 9999 at ``-05:00`` -- parses, but has no UTC spelling: ``astimezone`` raises
    ``OverflowError``. No token this module issued names one, so it is refused like any other
    foreign token rather than escaping as an internal error (`W55A-FIX`, JUDGE-X M1).
    """
    if not isinstance(value, str):
        raise _refused()
    try:
        parsed = datetime.fromisoformat(value)
        canonical = None if parsed.tzinfo is None else _instant(parsed)
    except (ValueError, OverflowError):
        raise _refused() from None
    if canonical != value:
        raise _refused()
    return parsed


@dataclass(frozen=True, slots=True)
class SnapshotPosition:
    created_at: datetime
    norms_snapshot_id: str


def encode_snapshot_cursor(position: SnapshotPosition) -> str:
    return _encode(["n1", _instant(position.created_at), position.norms_snapshot_id])


def decode_snapshot_cursor(token: str) -> SnapshotPosition:
    parts = _decode(token, "n1", 3)
    return SnapshotPosition(_parse_instant(parts[1]), _string(parts[2], _NS))


@dataclass(frozen=True, slots=True)
class EventPosition:
    changed_at: datetime
    event_id: str


def encode_event_cursor(position: EventPosition) -> str:
    return _encode(["e1", _instant(position.changed_at), position.event_id])


def decode_event_cursor(token: str) -> EventPosition:
    parts = _decode(token, "e1", 3)
    return EventPosition(_parse_instant(parts[1]), _string(parts[2], _EVT))
