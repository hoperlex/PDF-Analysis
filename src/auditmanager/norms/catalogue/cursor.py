"""The catalogue's continuation token, in the norms search tokens' style.

`W57B-NORMS-CATALOGUE-XLSX-01`. Like :mod:`auditmanager.norms.search.cursor`, a token is
base64url of a compact JSON array -- its kind and version, a **binding** and a position --
and carries no row number, offset or count. The binding is the first 128 bits of SHA-256 over
``(q, kind, snapshot)``: a token issued for one filter or one snapshot is refused for another
rather than resuming somewhere meaningless. The position is the last listed document's
identity; the listing's order is total (designation key, then identity) and a snapshot's rows
never change, so the next page starts exactly after it. A token that does not decode, names
another listing or names a document outside it is ``validation_failed`` on ``cursor``
(``format``), the search tokens' refusal.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any, Final

from auditmanager.shared.errors import DomainError, ErrorCode

from ..search.cursor import MAX_CURSOR_CHARACTERS

__all__ = ["catalogue_binding", "decode_catalogue_cursor", "encode_catalogue_cursor", "refused"]

_KIND: Final[str] = "c1"
_NDOC: Final[re.Pattern[str]] = re.compile(r"^ndoc_[0-9A-HJKMNP-TV-Z]{26}$")
_BINDING: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")


def refused() -> DomainError:
    """The search tokens' refusal, word for word."""
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The cursor parameter is not a continuation token of this listing.",
        field="cursor",
        constraint="format",
    )


def catalogue_binding(q: str | None, kind: str | None, norms_snapshot_id: str) -> str:
    """What a catalogue token is bound to: the filters as given and the snapshot listed."""
    material = json.dumps([q, kind, norms_snapshot_id], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def encode_catalogue_cursor(binding: str, norm_document_id: str) -> str:
    raw = json.dumps([_KIND, binding, norm_document_id], separators=(",", ":"), ensure_ascii=True)
    token = base64.urlsafe_b64encode(raw.encode("ascii")).decode("ascii").rstrip("=")
    if len(token) > MAX_CURSOR_CHARACTERS:  # pragma: no cover - bounded by construction
        raise RuntimeError("a catalogue cursor outgrew the contract's Cursor maximum")
    return token


def decode_catalogue_cursor(token: str, *, binding: str) -> str:
    """The document identity ``token`` resumes after, refused unless issued for ``binding``."""
    if not isinstance(token, str) or not token or len(token) > MAX_CURSOR_CHARACTERS:
        raise refused()
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        parts: Any = json.loads(raw.decode("ascii"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise refused() from None
    if (
        not isinstance(parts, list)
        or len(parts) != 3
        or parts[0] != _KIND
        or not isinstance(parts[1], str)
        or not _BINDING.fullmatch(parts[1])
        or not isinstance(parts[2], str)
        or not _NDOC.fullmatch(parts[2])
    ):
        raise refused()
    if encode_catalogue_cursor(parts[1], parts[2]) != token:
        # One position, one spelling: a re-padded or re-ordered token is not ours.
        raise refused()
    if parts[1] != binding:
        raise refused()
    return parts[2]
