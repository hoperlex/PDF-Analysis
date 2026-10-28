"""Multipart staging: the value types, the token and the rules that need no store.

`CMP-STORAGE-PARTS-01`, ADR-0025 decision 10. One file of a comparison upload is staged as an S3
multipart upload, chunk by chunk, and published only after the whole object has been read back and
matched to the declared SHA-256 and size. The adapter's calls live in :mod:`auditmanager.storage.s3`;
this module holds what is true without a store, so it is proved without one.

The token
---------
A multipart upload is named by one opaque **upload token**. The caller mints it
(:func:`new_multipart_token`, pure and local -- no external effect), **persists it**, and only then
asks the store to begin: ``comparison_upload_file.multipart_token`` is written before the first part
and never again (the migration's trigger refuses a part row for a file with no token). A killed
process therefore leaves a token with an owner in the database and, at worst, an upload in the store
that the same token can abort. There is no window in which the store holds an upload that no row
names, which is why the abort sweep is database-owned and needs no listing of the bucket.

The token is the stem of the object key (``temporary/<token>``); the store derives the in-progress
upload from it and nothing else is persisted. It is never a business identity and never a key a
caller may build: only the ``mpu-`` plus 32 lowercase hex form this module mints is accepted, so a
token cannot be a path and cannot collide with the free-form handle of ``stage_temporary``.

Receipts
--------
:class:`UploadedPart` is what ``upload_part`` returns and what the caller records in
``comparison_upload_part`` (``size_bytes``, ``sha256`` and ``etag`` are the three facts the table
requires before a part is ``staged``). Completion takes those recorded parts back.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from .errors import (
    BlobMetadataInvalidError,
    MultipartPartError,
    MultipartPartsError,
    SizeMismatchError,
)

if TYPE_CHECKING:
    from .port import MultipartStaging

#: ``comparison_upload_part.part_number`` is ``BETWEEN 1 AND 10000`` (S3's own bound).
MULTIPART_PART_NUMBER_MAX: Final[int] = 10_000

#: ``comparison_upload_part.size_bytes`` is ``BETWEEN 1 AND 16 MiB`` (ADR-0025 decision 10: every
#: chunk is 16 MiB on the default proxy location, under its 32 MiB body cap).
MULTIPART_PART_BYTES_MAX: Final[int] = 16 * 1024 * 1024

#: ``comparison_upload_part.etag`` is ``char_length BETWEEN 1 AND 256``.
_ETAG_LENGTH_MAX: Final[int] = 256

MULTIPART_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^mpu-[0-9a-f]{32}$")
_SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


def new_multipart_token() -> str:
    """Mint a fresh opaque upload token. Pure and local: nothing is sent to any store.

    128 random bits, so two tokens never meet. The caller persists the result before it is used.
    """
    return f"mpu-{secrets.token_hex(16)}"


def parse_multipart_token(value: object) -> str:
    """Validate an untrusted string as a token this module could have minted."""
    if not isinstance(value, str) or not MULTIPART_TOKEN_PATTERN.fullmatch(value):
        raise BlobMetadataInvalidError(
            field="upload_token", constraint=MULTIPART_TOKEN_PATTERN.pattern
        )
    return value


def validate_part_number(value: object) -> int:
    """A part number is an integer from 1 to :data:`MULTIPART_PART_NUMBER_MAX`."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MULTIPART_PART_NUMBER_MAX
    ):
        raise MultipartPartError(
            field="part_number", constraint=f"integer from 1 to {MULTIPART_PART_NUMBER_MAX}"
        )
    return value


def validate_part_size(size: int) -> int:
    """A part holds from 1 byte to :data:`MULTIPART_PART_BYTES_MAX` bytes."""
    if not 1 <= size <= MULTIPART_PART_BYTES_MAX:
        raise MultipartPartError(
            field="part_size", constraint=f"1 to {MULTIPART_PART_BYTES_MAX} bytes"
        )
    return size


@dataclass(frozen=True, slots=True)
class UploadedPart:
    """What the store staged for one part: the three facts the caller records.

    ``size_bytes`` and ``sha256`` are computed by the adapter from the bytes it sent, never taken
    from the caller; ``etag`` is the store's opaque receipt for the part, without its quotes.
    """

    part_number: int
    size_bytes: int
    sha256: str
    etag: str


def check_parts_for_completion(
    parts: Sequence[UploadedPart], *, declared_size: int
) -> tuple[UploadedPart, ...]:
    """The parts offered for completion, proved whole and ordered, or a typed refusal.

    Refuses before the store is asked to assemble anything:

    * no parts, a number that repeats, a gap, or numbers not ascending from 1
      (:class:`MultipartPartsError`);
    * a part outside ``1..16 MiB`` or with an empty or oversized receipt (:class:`MultipartPartsError`);
    * parts whose sizes do not add up to the declared size of the file (:class:`SizeMismatchError`,
      ``storage_integrity_error``: the bytes cannot be the declared bytes).
    """
    offered = tuple(parts)
    if not offered or not all(isinstance(part, UploadedPart) for part in offered):
        raise MultipartPartsError(
            field="parts", constraint="a non-empty sequence of staged parts"
        )
    if [part.part_number for part in offered] != list(range(1, len(offered) + 1)):
        raise MultipartPartsError(
            field="parts",
            constraint="ascending part numbers from 1 with no gap and no repeat",
        )
    for part in offered:
        if (
            isinstance(part.size_bytes, bool)
            or not isinstance(part.size_bytes, int)
            or not 1 <= part.size_bytes <= MULTIPART_PART_BYTES_MAX
            or not isinstance(part.etag, str)
            or not 1 <= len(part.etag) <= _ETAG_LENGTH_MAX
            or not isinstance(part.sha256, str)
            or not _SHA256_PATTERN.fullmatch(part.sha256)
        ):
            raise MultipartPartsError(
                field="parts", constraint="each part staged with its size, SHA-256 and ETag"
            )
    total = sum(part.size_bytes for part in offered)
    if total != declared_size:
        raise SizeMismatchError(expected_size=declared_size, actual_size=total)
    return offered


@dataclass(frozen=True, slots=True)
class MultipartSweepReport:
    """What one :func:`abort_multipart_sweep` call found, token by token.

    ``aborted`` -- an in-progress upload, or an assembled object nobody verified, was removed.
    ``absent`` -- the store held nothing for the token (aborted before, completed and published,
    or never begun). ``rejected`` -- the string is not a token this module mints; the store was
    not asked about it, so one bad row cannot block the rest of a sweep.
    """

    aborted: tuple[str, ...]
    absent: tuple[str, ...]
    rejected: tuple[str, ...]

    @property
    def handled(self) -> int:
        return len(self.aborted) + len(self.absent) + len(self.rejected)


def abort_multipart_sweep(
    store: MultipartStaging, upload_tokens: Iterable[str]
) -> MultipartSweepReport:
    """Abort the uploads these tokens name. The function a comparison work handler calls.

    **The database owns the decision.** The caller has already chosen the tokens -- the files whose
    batch was cancelled, whose upload expired or failed -- and has already moved those rows out of
    the states that accept a part (a part for an aborted file is refused by the state machine, and
    the store refuses it too: :meth:`MultipartStaging.upload_part` raises
    :class:`~auditmanager.storage.errors.TemporaryBlobLostError` once the upload is gone). This
    function touches the store only: it does not select tokens and it writes no row.

    Idempotent: a token already aborted, or whose file was completed and published, is ``absent``
    and nothing happens. It **never removes a published blob** -- completed bytes leave only
    through the operator's project erase (ADR-0025 decision 10).

    A store-wide fault (:class:`StorageUnavailableError`, a refused credential, a missing bucket)
    is **raised**, not recorded per token: a work handler treats it as a failed attempt and retries
    the same tokens, which is safe because every step is idempotent. A repeated token is handled once.
    """
    aborted: list[str] = []
    absent: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for token in upload_tokens:
        if isinstance(token, str):
            if token in seen:
                continue
            seen.add(token)
        try:
            parse_multipart_token(token)
        except BlobMetadataInvalidError:
            rejected.append(token if isinstance(token, str) else repr(token))
            continue
        (aborted if store.abort_multipart(token) else absent).append(token)
    return MultipartSweepReport(tuple(aborted), tuple(absent), tuple(rejected))


__all__ = [
    "MULTIPART_PART_BYTES_MAX",
    "MULTIPART_PART_NUMBER_MAX",
    "MULTIPART_TOKEN_PATTERN",
    "MultipartSweepReport",
    "UploadedPart",
    "abort_multipart_sweep",
    "check_parts_for_completion",
    "new_multipart_token",
    "parse_multipart_token",
    "validate_part_number",
    "validate_part_size",
]
