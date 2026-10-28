"""The portal bundle's archive rules, applied while the members are taken out of the ZIP.

`W55B-INGEST-01` (plan section B3.1, owner ruling R-116). An upload is one ZIP holding the
portal's files for one PDF: exactly one ``<stem>.pdf``, ``<stem>_blocks.json`` and
``<stem>_results.md``, and optionally one ``<stem>_results.html`` (a digest only: it is
read through the hash and never kept) and one ``<stem>_stamp_audit.json``. This module is
the archive half of the admission envelope; :mod:`auditmanager.ingest.bundle_envelope`
judges what the members *say*.

Why the directory is read here and not by ``zipfile``
-----------------------------------------------------
The rules are about fields ``zipfile`` hides or rewrites: the raw name bytes (the shared stem
is compared on bytes, and a name that decodes two ways must be seen both ways), the
general-purpose flags (encryption, UTF-8), the Info-ZIP Unicode Path field, the external
attributes (a symbolic link is a mode bit) and the declared sizes. So the end record, the
ZIP64 records and the central directory are read directly, and a member's bytes are
inflated with ``zlib`` in chunks. ``zipfile`` is used by the tests, as the independent
reader the output is compared with. ZIP64 and data descriptors are accepted: the central
directory carries the sizes either way, and every size is judged within the size rules.

**The declared sizes are never trusted.** A header says how big a member is; the bytes that
come out say how big it is. Both are held to the bounds: the declared size first (a refusal
before a byte is unpacked), then the bytes counted while they are written, which is the
only check a lying header cannot get past. A member is written to a temporary file as it is
counted -- never into memory -- with a running SHA-256, so one pass gives the digest, the
size and the file the rest of the envelope reads.

Names are display only. A member's file in the temporary directory is named by its *role*,
never by the archive's name for it, so no name an archive carries can name a path here.

Order of the rules, cheapest first (each refusal answers a registered
``validation_failed`` constraint under ``field: "file"`` and never echoes a name):

0. the part is a ZIP (its magic); the end record is found; more than eight entries;
1. per entry, in directory order: a directory entry or ``__MACOSX/``, an unsafe name, a
   symbolic link, an encrypted member, a method other than stored or deflate; then names
   that repeat (after case folding and NFC), the member set, one stem;
2. the declared sizes (per member, then in total), then the declared compression ratios;
3. each member unpacked and counted: its actual bytes against the bounds and against its
   declaration, its CRC-32, and the ratio of those bytes to the compressed bytes the stream
   really used (a header may claim more than the stream holds).

Policies (`CMP-INGEST-ZIP-01`, ADR-0025 decision 12)
----------------------------------------------------
:func:`extract_bundle` takes an :class:`ArchivePolicy`. The mechanics above -- the end records,
the directory, the declared and the counted sizes, the ratio, the CRC and the digest -- are the
same for every kind of upload; a policy says only which entries a kind accepts
(:attr:`ArchivePolicy.judge`), how its refusals are named (:attr:`ArchivePolicy.translate`)
and how large a central directory it will read (:attr:`ArchivePolicy.max_directory_bytes`).
The default is :data:`PORTAL_POLICY`, which is every rule of this module as it was before the
parameter existed. The policy of a ZIP *set* (many PDFs in one archive) is written in
:mod:`auditmanager.ingest.comparison_zip`.
"""

from __future__ import annotations

import hashlib
import io
import struct
import tempfile
import unicodedata
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

from auditmanager.shared.errors import DomainError, ErrorCode

from .envelope import MAX_BYTES

__all__ = [
    "ACCEPTED_METHODS",
    "ArchiveEntry",
    "ArchivePolicy",
    "BundleLimits",
    "DEFAULT_LIMITS",
    "ExtractedBundle",
    "ExtractedMember",
    "MEMBER_BYTES",
    "PORTAL_POLICY",
    "ROLE_BLOCKS",
    "ROLE_PDF",
    "ROLE_RESULTS_HTML",
    "ROLE_RESULTS_MD",
    "ROLE_STAMP_AUDIT",
    "BLOCKS_MEMBER_BYTES",
    "STAMP_AUDIT_BYTES",
    "TEXT_MEMBER_BYTES",
    "ZIP_MAGICS",
    "decode_display_name",
    "duplicate_key",
    "extract_bundle",
    "is_unsafe_name",
    "looks_like_zip",
]

MiB: Final[int] = 1024 * 1024

#: The first bytes of a ZIP: a local header, an end record (an empty archive) or a spanning
#: marker. A bare PDF begins ``%PDF-``, so no PDF is ever mistaken for a ZIP by this test.
ZIP_MAGICS: Final[tuple[bytes, ...]] = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")

# -- the bounds -------------------------------------------------------------------------

#: Any one member's uncompressed size. The PDF is the largest member and its own bound is
#: the upload's (250 MiB, ``MAX_BYTES``): a smaller figure here would refuse a valid
#: maximal PDF. The other members are held far lower below, so this figure only governs the
#: PDF and the HTML (which is hashed and dropped, so its size costs time and no memory).
MEMBER_BYTES: Final[int] = MAX_BYTES

#: The members that are read into memory to be parsed -- ``_blocks.json`` and
#: ``_results.md``. Measured on the 674 portal documents of the norms corpus (the largest
#: has 500 pages): ``_results.md`` 7.6 KB per page at worst, 3.8 MB for 500 pages;
#: ``_blocks.json`` 1.1 KB per page, 0.55 MB for 500 pages. 16 MiB is more than four times
#: the worst markdown and thirty times the worst block list. It is also what bounds memory:
#: ``json.loads`` of a block list holds roughly ten times its size in Python objects.
TEXT_MEMBER_BYTES: Final[int] = 16 * MiB

#: ``_blocks.json`` on its own (`W55B-FIX`, X-6): parsing JSON costs a multiple of its size
#: before a single block is judged, up to about 25 times for a list of empty objects
#: (measured: 16 MiB, 404 MiB at the peak; 4 MiB, 100 MiB). Measured on real block lists:
#: the corpus' largest is 283 408 bytes (500 pages), the owner's export 77 152 bytes (30
#: pages, 129 blocks, 598 bytes a block); the largest real block serialises to 869 bytes.
#: 4 MiB is fourteen times the largest real list, and holds the bundle's block ceiling
#: (``bundle_envelope.MAX_BLOCKS``, 3 000) at 1.1 KB a block, the corpus' pretty-printed
#: density, with room to spare.
BLOCKS_MEMBER_BYTES: Final[int] = 4 * MiB

#: ``_stamp_audit.json`` is stored and parsed as JSON, never analysed. The corpus' largest is
#: 62 KB (547 bytes per page, 274 KB for 500 pages): 4 MiB is fifteen times that.
STAMP_AUDIT_BYTES: Final[int] = 4 * MiB

#: Plan section B3.1 and ``W55B-FREEZE-01``: the members' uncompressed bytes together, the
#: compression ratio of a member and of the archive, and the number of entries.
TOTAL_BYTES: Final[int] = 300 * MiB
MAX_RATIO: Final[int] = 100
MAX_ENTRIES: Final[int] = 8


@dataclass(frozen=True, slots=True)
class BundleLimits:
    """The bounds one extraction runs under. The defaults are the production values.

    A test lowers them to exercise a rule without writing hundreds of MiB; the constants
    above are asserted separately, so a lowered figure here never stands in for the real one.
    """

    member_bytes: int = MEMBER_BYTES
    text_member_bytes: int = TEXT_MEMBER_BYTES
    blocks_member_bytes: int = BLOCKS_MEMBER_BYTES
    stamp_audit_bytes: int = STAMP_AUDIT_BYTES
    total_bytes: int = TOTAL_BYTES
    ratio: int = MAX_RATIO
    entries: int = MAX_ENTRIES


DEFAULT_LIMITS: Final[BundleLimits] = BundleLimits()

# -- member roles -----------------------------------------------------------------------

ROLE_PDF: Final[str] = "pdf"
ROLE_BLOCKS: Final[str] = "blocks"
ROLE_RESULTS_MD: Final[str] = "results_md"
ROLE_RESULTS_HTML: Final[str] = "results_html"
ROLE_STAMP_AUDIT: Final[str] = "stamp_audit"

#: Matching is on the raw name bytes, never on a decoded name.
_ROLE_SUFFIX: Final[dict[str, bytes]] = {
    ROLE_PDF: b".pdf",
    ROLE_BLOCKS: b"_blocks.json",
    ROLE_RESULTS_MD: b"_results.md",
    ROLE_RESULTS_HTML: b"_results.html",
    ROLE_STAMP_AUDIT: b"_stamp_audit.json",
}
_REQUIRED_ROLES: Final[tuple[str, ...]] = (ROLE_PDF, ROLE_BLOCKS, ROLE_RESULTS_MD)
_OPTIONAL_ROLES: Final[tuple[str, ...]] = (ROLE_RESULTS_HTML, ROLE_STAMP_AUDIT)
#: The members that are read into memory and so carry the smaller bound.
_TEXT_ROLES: Final[frozenset[str]] = frozenset({ROLE_BLOCKS, ROLE_RESULTS_MD})

# -- ZIP structure ----------------------------------------------------------------------

_LOCAL_SIGNATURE: Final[bytes] = b"PK\x03\x04"
_CENTRAL_SIGNATURE: Final[bytes] = b"PK\x01\x02"
_EOCD_SIGNATURE: Final[bytes] = b"PK\x05\x06"
_EOCD64_SIGNATURE: Final[int] = 0x06064B50
_EOCD64_LOCATOR_SIGNATURE: Final[int] = 0x07064B50
_MAX_COMMENT: Final[int] = 0xFFFF
_EOCD_SIZE: Final[int] = 22
_LOCATOR_SIZE: Final[int] = 20
_CENTRAL_HEADER_SIZE: Final[int] = 46
#: The most one central-directory entry can hold: its fixed part, a name, an extra field and
#: a comment, each at most 65 535 bytes. A directory larger than this many entries could
#: hold is not one this reader reads: it is refused before it is loaded.
_MAX_ENTRY_BYTES: Final[int] = _CENTRAL_HEADER_SIZE + 3 * 0xFFFF

_FLAG_ENCRYPTED: Final[int] = 0x0001
_FLAG_STRONG_ENCRYPTION: Final[int] = 0x0040
_FLAG_UTF8: Final[int] = 0x0800
_STORED: Final[int] = 0
_DEFLATED: Final[int] = 8
_UNIX: Final[int] = 3
_EXTRA_ZIP64: Final[int] = 0x0001
_EXTRA_UNICODE_PATH: Final[int] = 0x7075
_MODE_TYPE_MASK: Final[int] = 0o170000
_MODE_SYMLINK: Final[int] = 0o120000

#: How much of a member is inflated and written at a time.
_PIECE: Final[int] = 1 << 16

_FIELD: Final[str] = "file"

# -- the refusals -----------------------------------------------------------------------

#: One fixed sentence per registered constraint. No name, size or byte of the archive is
#: ever put in one: ``validation_failed`` carries classifiers, not the caller's input.
_MESSAGES: Final[dict[str, str]] = {
    "portal_bundle_required": (
        "Загрузите комплект портала распознавания: ZIP-архив с PDF-документом и файлами "
        "блоков и распознанного текста, которые формирует портал. Отдельный PDF не принимается."
    ),
    "bundle_unreadable": "The archive could not be read as a ZIP file.",
    "bundle_entry_count": "The archive holds more entries than a portal bundle can.",
    "bundle_directory_entry": "The archive holds a directory entry, which a portal bundle never does.",
    "bundle_member_name": "A member of the archive has a name that is not a plain file name.",
    "bundle_symlink": "A member of the archive is a symbolic link.",
    "bundle_encrypted_member": "A member of the archive is encrypted.",
    "bundle_compression_method": "A member of the archive uses a compression method other than stored or deflate.",
    "bundle_duplicate_member": "Two members of the archive have the same name.",
    "bundle_stem_mismatch": "The members of the archive do not share one file name stem.",
    "bundle_member_set": (
        "The archive does not hold exactly the members of a portal bundle: one PDF, one "
        "block list and one recognised-text file, and optionally the HTML rendering and the "
        "stamp audit."
    ),
    "bundle_member_size": "A member of the archive is larger than a portal bundle allows.",
    "bundle_total_size": "The members of the archive together are larger than a portal bundle allows.",
    "bundle_compression_ratio": "The archive is compressed more than a portal bundle allows.",
    "blocks_json_invalid": "The portal block list is not valid.",
    "blocks_page_count": "The portal block list does not describe the PDF's pages.",
    "blocks_count": "The portal block list holds more blocks than a portal bundle may.",
    "results_blocks_mismatch": (
        "The recognised-text file and the portal block list disagree about the blocks."
    ),
    "stamp_audit_invalid": "The stamp audit is not valid JSON or is larger than it may be.",
}


def refuse(constraint: str, message: str | None = None) -> DomainError:
    """The one refusal this package raises for the bundle: ``field: "file"``."""
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=message if message is not None else _MESSAGES[constraint],
        field=_FIELD,
        constraint=constraint,
    )


class _ArchiveError(ValueError):
    """The bytes are not an archive this reader can interpret (mapped to bundle_unreadable)."""


# -- the extracted bundle ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtractedMember:
    """One member as it was counted while it was unpacked.

    ``path`` is the temporary file holding its bytes, or ``None`` for the HTML rendering,
    which is hashed and not kept. ``display_name`` is for display only.
    """

    role: str
    display_name: str
    size: int
    sha256: str
    path: Path | None


class ExtractedBundle:
    """The members of one accepted archive, as files in a private temporary directory.

    Close it (or use it as a context manager) to remove the directory. It is created inside
    :func:`extract_bundle` and removed there when the extraction is refused.
    """

    __slots__ = ("members", "_directory")

    def __init__(
        self, members: dict[str, ExtractedMember], directory: tempfile.TemporaryDirectory[str]
    ) -> None:
        self.members = members
        self._directory = directory

    def open(self, role: str) -> BinaryIO:
        path = self.members[role].path
        if path is None:
            raise KeyError(role)
        return path.open("rb")

    def read_bytes(self, role: str) -> bytes:
        path = self.members[role].path
        if path is None:
            raise KeyError(role)
        return path.read_bytes()

    def close(self) -> None:
        self._directory.cleanup()

    def __enter__(self) -> ExtractedBundle:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


# -- entries ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Entry:
    index: int
    name: bytes                  # exactly as the central directory holds it
    flags: int
    method: int
    crc: int
    compressed_size: int         # declared
    size: int                    # declared uncompressed size
    header_offset: int
    create_system: int
    external_attr: int
    extra: bytes

    @property
    def is_encrypted(self) -> bool:
        return bool(self.flags & _FLAG_ENCRYPTED) or bool(self.flags & _FLAG_STRONG_ENCRYPTION)

    @property
    def is_symlink(self) -> bool:
        # The Unix mode lives in the high half of the external attributes and only means
        # something when the archive says a Unix system made the entry.
        mode = self.external_attr >> 16
        return self.create_system == _UNIX and (mode & _MODE_TYPE_MASK) == _MODE_SYMLINK


def role_of(name: bytes) -> str | None:
    """The member role a raw name's suffix gives it, or ``None`` for an unknown suffix."""
    for role, suffix in _ROLE_SUFFIX.items():
        if name.endswith(suffix):
            return role
    return None


def _stem_of(name: bytes, role: str) -> bytes:
    return name[: len(name) - len(_ROLE_SUFFIX[role])]


def _parse_extra(extra: bytes) -> list[tuple[int, bytes]]:
    fields: list[tuple[int, bytes]] = []
    position = 0
    while position < len(extra):
        if position + 4 > len(extra):
            raise _ArchiveError("a truncated extra field")
        header_id, length = struct.unpack_from("<HH", extra, position)
        position += 4
        if position + length > len(extra):
            raise _ArchiveError("an extra field longer than its block")
        fields.append((header_id, extra[position : position + length]))
        position += length
    return fields


def _unicode_path(name: bytes, extra: bytes) -> str | None:
    """The Info-ZIP Unicode Path field's name, when present and still valid for ``name``.

    The field is ignored when its CRC-32 no longer matches the header name (the name was
    edited after the field was written), when its version is not 1 and when it is not UTF-8.
    """
    try:
        fields = _parse_extra(extra)
    except _ArchiveError:
        return None
    for header_id, data in fields:
        if header_id != _EXTRA_UNICODE_PATH or len(data) < 5 or data[0] != 1:
            continue
        if struct.unpack_from("<I", data, 1)[0] != zlib.crc32(name) & 0xFFFFFFFF:
            continue
        try:
            return data[5:].decode("utf-8")
        except UnicodeDecodeError:
            continue
    return None


def decode_display_name(name: bytes, flags: int, extra: bytes) -> str:
    """The name to show, never to rely on.

    UTF-8 when general-purpose flag 11 is set; else the Info-ZIP Unicode Path extra field
    (``0x7075``) when it is valid for this header name; else strict UTF-8; else cp866.
    cp866 maps every byte, so the last step cannot fail. A name flagged UTF-8 that is not
    valid UTF-8 is shown with replacement characters and not refused: it is display only,
    and its raw bytes still take part in every comparison.
    """
    if flags & _FLAG_UTF8:
        return name.decode("utf-8", errors="replace")
    named = _unicode_path(name, extra)
    if named is not None:
        return named
    try:
        return name.decode("utf-8")
    except UnicodeDecodeError:
        return name.decode("cp866")


# -- the reader -------------------------------------------------------------------------


class _Archive:
    """An archive opened on a seekable handle; nothing is read twice and nothing whole."""

    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        self.size = handle.seek(0, io.SEEK_END)
        #: The compressed bytes the last :meth:`read_chunks` really consumed (a deflate stream
        #: ends where it ends, whatever the header says), valid once that generator is spent.
        self.consumed = 0
        self.declared_count, self._directory_size, self._directory_offset = self._locate()

    def _read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise _ArchiveError("a read outside the file")
        self._handle.seek(offset)
        data = self._handle.read(length)
        if len(data) != length:
            raise _ArchiveError("the file ends inside a structure")
        return data

    def _locate(self) -> tuple[int, int, int]:
        """(entry count, directory size, directory offset) from the end records."""
        tail_length = min(self.size, _EOCD_SIZE + _MAX_COMMENT)
        tail = self._read(self.size - tail_length, tail_length)
        position = tail.rfind(_EOCD_SIGNATURE)
        if position < 0 or position + _EOCD_SIZE > len(tail):
            raise _ArchiveError("no end-of-central-directory record")
        (_sig, disk, directory_disk, on_disk, total, directory_size, directory_offset,
         comment_length) = struct.unpack_from("<IHHHHIIH", tail, position)
        if position + _EOCD_SIZE + comment_length > len(tail):
            raise _ArchiveError("the archive comment runs past the end of the file")
        if disk != 0 or directory_disk != 0 or on_disk != total:
            raise _ArchiveError("a multi-disk archive")
        end_record = self.size - tail_length + position
        if total == 0xFFFF or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
            total, directory_size, directory_offset = self._locate_zip64(end_record)
        if directory_offset + directory_size > end_record:
            raise _ArchiveError("the central directory overlaps the end records")
        return total, directory_size, directory_offset

    def _locate_zip64(self, end_record: int) -> tuple[int, int, int]:
        if end_record < _LOCATOR_SIZE:
            raise _ArchiveError("a ZIP64 marker without a ZIP64 locator")
        locator = self._read(end_record - _LOCATOR_SIZE, _LOCATOR_SIZE)
        signature, _disk, record_offset, _disks = struct.unpack("<IIQI", locator)
        if signature != _EOCD64_LOCATOR_SIGNATURE:
            raise _ArchiveError("a ZIP64 marker without a ZIP64 locator")
        record = self._read(record_offset, 56)
        (signature, _size, _made, _needed, disk, directory_disk, on_disk, total,
         directory_size, directory_offset) = struct.unpack("<IQHHIIQQQQ", record)
        if signature != _EOCD64_SIGNATURE:
            raise _ArchiveError("the ZIP64 end record is missing")
        if disk != 0 or directory_disk != 0 or on_disk != total:
            raise _ArchiveError("a multi-disk archive")
        return total, directory_size, directory_offset

    def load_entries(self) -> tuple[_Entry, ...]:
        """Parse the central directory; its length must agree with its entry count.

        The count has been judged by the caller by now, so the directory read here is at
        most a few entries; a size that no such directory could have is refused first.
        """
        if self._directory_size > self.declared_count * _MAX_ENTRY_BYTES:
            raise _ArchiveError("the central directory is larger than its entries can be")
        blob = self._read(self._directory_offset, self._directory_size)
        entries: list[_Entry] = []
        position = 0
        for index in range(self.declared_count):
            if position + _CENTRAL_HEADER_SIZE > len(blob):
                raise _ArchiveError(f"entry {index}: a truncated directory header")
            if blob[position : position + 4] != _CENTRAL_SIGNATURE:
                raise _ArchiveError(f"entry {index}: no central directory signature")
            (_sig, made_by, _needed, flags, method, _time, _date, crc, csize, usize,
             name_length, extra_length, comment_length, _disk, _internal, external,
             offset) = struct.unpack_from("<IHHHHHHIIIHHHHHII", blob, position)
            position += _CENTRAL_HEADER_SIZE
            end = position + name_length + extra_length + comment_length
            if end > len(blob):
                raise _ArchiveError(f"entry {index}: a truncated directory entry")
            name = blob[position : position + name_length]
            extra = blob[position + name_length : position + name_length + extra_length]
            position = end
            csize, usize, offset = _zip64_values(index, extra, csize, usize, offset)
            entries.append(
                _Entry(index, name, flags, method, crc, csize, usize, offset,
                       made_by >> 8, external, extra)
            )
        if position != len(blob):
            raise _ArchiveError("the central directory is longer than its entries")
        return tuple(entries)

    def data_offset(self, entry: _Entry) -> int:
        """Where the member's data starts, after checking its local header agrees."""
        header = self._read(entry.header_offset, 30)
        if header[:4] != _LOCAL_SIGNATURE:
            raise _ArchiveError(f"entry {entry.index}: no local header signature")
        name_length, extra_length = struct.unpack_from("<HH", header, 26)
        if self._read(entry.header_offset + 30, name_length) != entry.name:
            raise _ArchiveError(f"entry {entry.index}: the local header names another member")
        start = entry.header_offset + 30 + name_length + extra_length
        if start + entry.compressed_size > self._directory_offset:
            raise _ArchiveError(f"entry {entry.index}: the data runs into the directory")
        return start

    def read_chunks(self, entry: _Entry) -> Iterator[bytes]:
        """The member's bytes, inflated, in pieces of at most ``_PIECE`` bytes.

        How much comes out is not decided by the declared sizes: a caller counts what
        actually arrives, which is the only honest figure.
        """
        if entry.method not in (_STORED, _DEFLATED):
            raise _ArchiveError(f"entry {entry.index}: compression method {entry.method}")
        start = self.data_offset(entry)
        remaining = entry.compressed_size
        position = start
        self.consumed = 0
        if entry.method == _STORED:
            while remaining > 0:
                data = self._read(position, min(_PIECE, remaining))
                position += len(data)
                remaining -= len(data)
                self.consumed += len(data)
                yield data
            return
        inflater = zlib.decompressobj(-15)
        fed = 0
        try:
            while remaining > 0 and not inflater.eof:
                data = self._read(position, min(_PIECE, remaining))
                position += len(data)
                remaining -= len(data)
                fed += len(data)
                pending = data
                while pending:
                    out = inflater.decompress(pending, _PIECE)
                    if out:
                        yield out
                    if inflater.eof:
                        # The stream is over. When it ends exactly where the output limit does,
                        # zlib keeps the bytes behind it as ``unconsumed_tail`` as well as in
                        # ``unused_data``; feeding that tail back would never produce a byte and
                        # never end -- and would grow ``unused_data`` by the tail each time.
                        break
                    pending = inflater.unconsumed_tail
                    if not out and not pending:
                        break
            while not inflater.eof:
                out = inflater.flush(_PIECE)
                if not out:
                    break
                yield out
        except zlib.error:
            raise _ArchiveError(f"entry {entry.index}: the deflate data is corrupt") from None
        if not inflater.eof:
            raise _ArchiveError(f"entry {entry.index}: the deflate stream does not end")
        # Bytes the header claimed for the member but the stream did not use are not compressed
        # data: they must not lower the ratio.
        self.consumed = fed - len(inflater.unused_data)


def _zip64_values(
    index: int, extra: bytes, csize: int, usize: int, offset: int
) -> tuple[int, int, int]:
    """Resolve the 0xFFFFFFFF markers from the ZIP64 field, in the field's own order."""
    if 0xFFFFFFFF not in (csize, usize, offset):
        return csize, usize, offset
    data = next((d for i, d in _parse_extra(extra) if i == _EXTRA_ZIP64), None)
    if data is None:
        raise _ArchiveError(f"entry {index}: a ZIP64 marker without a ZIP64 field")
    position = 0

    def take() -> int:
        nonlocal position
        if position + 8 > len(data):
            raise _ArchiveError(f"entry {index}: a truncated ZIP64 field")
        (value,) = struct.unpack_from("<Q", data, position)
        position += 8
        return value

    if usize == 0xFFFFFFFF:
        usize = take()
    if csize == 0xFFFFFFFF:
        csize = take()
    if offset == 0xFFFFFFFF:
        offset = take()
    return csize, usize, offset


# -- the rules --------------------------------------------------------------------------


def looks_like_zip(handle: BinaryIO) -> bool:
    """Whether the handle's first bytes are a ZIP's. The handle is left at its start."""
    handle.seek(0)
    head = handle.read(4)
    handle.seek(0)
    return head in ZIP_MAGICS


def _is_directory_like(name: bytes) -> bool:
    return name.endswith(b"/") or name.startswith(b"__MACOSX/")


def _is_unsafe_name(name: bytes) -> bool:
    """An absolute, drive-letter, backslash or ``..`` name."""
    return (
        name.startswith(b"/")
        or b"\\" in name
        or (len(name) >= 2 and name[1:2] == b":" and name[:1].isalpha())
        or b".." in name.split(b"/")
    )


def _duplicate_key(entry: _Entry) -> str:
    shown = decode_display_name(entry.name, entry.flags, entry.extra)
    folded = unicodedata.normalize("NFC", shown).casefold()
    return unicodedata.normalize("NFC", folded)


def _judge_entries(entries: tuple[_Entry, ...]) -> dict[str, _Entry]:
    """Rules about single entries, then about the set. Returns the member for each role."""
    for entry in entries:
        name = entry.name
        if _is_directory_like(name):
            raise refuse("bundle_directory_entry")
        if _is_unsafe_name(name):
            raise refuse("bundle_member_name")
        if entry.is_symlink:
            raise refuse("bundle_symlink")
        if entry.is_encrypted:
            raise refuse("bundle_encrypted_member")
        if entry.method not in (_STORED, _DEFLATED):
            raise refuse("bundle_compression_method")

    seen: set[str] = set()
    for entry in entries:
        key = _duplicate_key(entry)
        if key in seen:
            raise refuse("bundle_duplicate_member")
        seen.add(key)

    by_role: dict[str, list[_Entry]] = {}
    for entry in entries:
        role = role_of(entry.name)
        if role is None:
            raise refuse("bundle_member_set")
        by_role.setdefault(role, []).append(entry)
    for role in _REQUIRED_ROLES:
        if len(by_role.get(role, [])) != 1:
            raise refuse("bundle_member_set")
    for role in _OPTIONAL_ROLES:
        if len(by_role.get(role, [])) > 1:
            raise refuse("bundle_member_set")

    chosen = {role: found[0] for role, found in by_role.items()}
    stems = {_stem_of(entry.name, role) for role, entry in chosen.items()}
    if len(stems) > 1:
        raise refuse("bundle_stem_mismatch")
    return chosen


def _ratio_exceeded(size: int, compressed: int, ratio: int) -> bool:
    return size > ratio * compressed


def _judge_declared(
    chosen: dict[str, _Entry], archive_size: int, limits: BundleLimits
) -> None:
    """The sizes the headers declare: refused before a byte is unpacked."""
    for role, entry in chosen.items():
        if entry.size > limits.member_bytes:
            raise refuse("bundle_member_size")
        if role in _TEXT_ROLES and entry.size > limits.text_member_bytes:
            raise refuse("bundle_member_size")
        if role == ROLE_BLOCKS and entry.size > limits.blocks_member_bytes:
            raise refuse("bundle_member_size")
        if role == ROLE_STAMP_AUDIT and entry.size > limits.stamp_audit_bytes:
            raise refuse("stamp_audit_invalid")
    declared_total = sum(entry.size for entry in chosen.values())
    if declared_total > limits.total_bytes:
        raise refuse("bundle_total_size")
    for entry in chosen.values():
        if _ratio_exceeded(entry.size, entry.compressed_size, limits.ratio):
            raise refuse("bundle_compression_ratio")
    if _ratio_exceeded(declared_total, archive_size, limits.ratio):
        raise refuse("bundle_compression_ratio")


def _display_stem_name(entry: _Entry) -> str:
    return decode_display_name(entry.name, entry.flags, entry.extra)


def _unpack(
    archive: _Archive,
    chosen: dict[str, _Entry],
    directory: Path,
    limits: BundleLimits,
) -> dict[str, ExtractedMember]:
    """Gate 3: every member unpacked, with the bytes that actually come out counted.

    **The member's own declaration is a size bound, held piece by piece** (`W55B-FIX`, X-5).
    Before this, a 245 KB archive whose header declared a 4 000-byte PDF inflated 240 MiB to
    disk and was refused only then. A member that has produced more bytes than its header
    declared is refused at once, with the constraint of the size rule for its role
    (``bundle_member_size``; ``stamp_audit_invalid`` for the stamp audit) -- the answer such a
    disguise always got once its count crossed the role's bound, now given at the declared
    size plus one piece. Every declaration has already been held to the bounds and to the
    ratio against its declared compressed size, which must lie inside the archive
    (:func:`_judge_declared`, :meth:`_Archive.data_offset`), so the work on any member is at
    most its declaration plus one piece: at most the member bound plus one piece, and at most
    a hundred times the archive plus one piece.
    The counted member, text, stamp and total bounds below can therefore no longer be the
    first to speak; they stay as a second line. A member that produces *fewer* bytes than
    declared is still ``bundle_unreadable``.

    **The ratio is the whole member's**, judged once it is out, against the compressed bytes
    its stream really used. `W55B-FIX` first held it for every prefix as well; that refused
    members the frozen bound admits -- a PDF that opens with an unfiltered white raster has a
    prefix of hundreds to one and a whole of a few to one (`W55B-JUDGE-X` X-11, ``p12``) --
    and bounded no work the declaration does not already bound. FIX-2 removed it.
    """
    members: dict[str, ExtractedMember] = {}
    total = 0
    for role, entry in chosen.items():
        digest = hashlib.sha256()
        actual = 0
        crc = 0
        target = directory / role
        sink: BinaryIO | None = None if role == ROLE_RESULTS_HTML else target.open("wb")
        try:
            for chunk in archive.read_chunks(entry):
                actual += len(chunk)
                total += len(chunk)
                if actual > limits.member_bytes:
                    raise refuse("bundle_member_size")
                if role in _TEXT_ROLES and actual > limits.text_member_bytes:
                    raise refuse("bundle_member_size")
                if role == ROLE_BLOCKS and actual > limits.blocks_member_bytes:
                    raise refuse("bundle_member_size")
                if role == ROLE_STAMP_AUDIT and actual > limits.stamp_audit_bytes:
                    raise refuse("stamp_audit_invalid")
                if total > limits.total_bytes:
                    raise refuse("bundle_total_size")
                if actual > entry.size:
                    raise refuse(
                        "stamp_audit_invalid" if role == ROLE_STAMP_AUDIT else "bundle_member_size"
                    )
                crc = zlib.crc32(chunk, crc)
                digest.update(chunk)
                if sink is not None:
                    sink.write(chunk)
        except _ArchiveError:
            raise refuse("bundle_unreadable") from None
        finally:
            if sink is not None:
                sink.close()
        if actual != entry.size or crc & 0xFFFFFFFF != entry.crc:
            raise refuse("bundle_unreadable")
        # The ratio of what really came out to what the stream really used. The declared
        # ratio (``_judge_declared``) cannot see a header that claims more compressed bytes
        # than the stream holds, with padding behind it, to hide a bomb's ratio.
        if _ratio_exceeded(actual, archive.consumed, limits.ratio):
            raise refuse("bundle_compression_ratio")
        members[role] = ExtractedMember(
            role=role,
            display_name=_display_stem_name(entry),
            size=actual,
            sha256=digest.hexdigest(),
            path=None if sink is None else target,
        )
    return members


@dataclass(frozen=True, slots=True)
class ArchivePolicy:
    """The policy parameter of :func:`extract_bundle` (`CMP-INGEST-ZIP-01`).

    ``judge`` takes every entry of the central directory, in directory order, and returns the
    members to unpack, keyed by the name this policy gives each (the key names the member's
    temporary file, never the archive's name for it). It raises :func:`refuse` for an entry or
    a set it does not accept.

    ``translate``, when given, turns every :class:`DomainError` the extraction raises into the
    refusal this policy answers with, so a kind of upload need not borrow the portal bundle's
    constraint names or sentences. ``None`` leaves every refusal as raised.

    ``max_directory_bytes``, when given, refuses an archive whose central directory is larger,
    before it is read into memory. The portal bundle does not need it (eight entries bound the
    directory to about 1.5 MiB); a policy that allows many entries does.
    """

    judge: Callable[[tuple[_Entry, ...]], dict[str, _Entry]]
    translate: Callable[[DomainError], DomainError] | None = None
    max_directory_bytes: int | None = None


#: The portal bundle's rules, exactly: :func:`_judge_entries`, no renaming, no extra bound.
PORTAL_POLICY: Final[ArchivePolicy] = ArchivePolicy(judge=_judge_entries)

#: What a policy's ``judge`` is handed and what it may reuse so that every kind of upload
#: applies the same name, duplicate and method rules as the portal bundle does.
ArchiveEntry = _Entry
ACCEPTED_METHODS: Final[tuple[int, ...]] = (_STORED, _DEFLATED)
is_unsafe_name = _is_unsafe_name
duplicate_key = _duplicate_key


def extract_bundle(
    handle: BinaryIO,
    *,
    limits: BundleLimits = DEFAULT_LIMITS,
    policy: ArchivePolicy = PORTAL_POLICY,
) -> ExtractedBundle:
    """Apply every archive rule to the upload and take its members out as temporary files.

    ``handle`` is a seekable binary handle on the whole upload, which is left where the
    reader left it (the caller rewinds before reading it again). Raises
    ``validation_failed`` (``field: "file"``, a registered ``constraint``) for anything a
    portal bundle is not, having kept nothing: the temporary directory is removed before the
    refusal leaves. On success the caller owns the returned bundle and must close it.

    ``policy`` is the kind of upload the archive must be (:class:`ArchivePolicy`); the default
    is the portal bundle, whose behaviour this parameter does not change.
    """
    if policy.translate is None:
        return _extract(handle, limits, policy)
    try:
        return _extract(handle, limits, policy)
    except DomainError as refused:
        raise policy.translate(refused) from None


def _extract(
    handle: BinaryIO, limits: BundleLimits, policy: ArchivePolicy
) -> ExtractedBundle:
    if not looks_like_zip(handle):
        raise refuse("portal_bundle_required")
    directory = tempfile.TemporaryDirectory(prefix="auditmanager-bundle-")
    try:
        try:
            archive = _Archive(handle)
            if archive.declared_count > limits.entries:
                raise refuse("bundle_entry_count")
            if (
                policy.max_directory_bytes is not None
                and archive._directory_size > policy.max_directory_bytes
            ):
                raise refuse("bundle_unreadable")
            entries = archive.load_entries()
        except _ArchiveError:
            raise refuse("bundle_unreadable") from None
        chosen = policy.judge(entries)
        _judge_declared(chosen, archive.size, limits)
        members = _unpack(archive, chosen, Path(directory.name), limits)
        return ExtractedBundle(members, directory)
    except BaseException:
        directory.cleanup()
        raise
