"""Read an archive's directory the way an envelope has to: raw names, flags, attributes.

`zipfile` decodes names for you and hides the fields the bundle rules are about (the
encrypted flag is an attribute buried in `flag_bits`, the symbolic-link bit in
`external_attr`, the raw name is already gone). The validator needs the bytes as they are,
because the stem is compared on raw name bytes and a name that decodes two ways must be
seen both ways. So this reads the end-of-central-directory record, the ZIP64 records and
the central directory itself, and streams a member's bytes without ever trusting the sizes
the headers declare.

Anything the format does not allow raises `ArchiveError`; the validator maps that to
`bundle_unreadable`.
"""

from __future__ import annotations

import io
import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from . import zipwrite as zw

_LOCAL_SIGNATURE = b"PK\x03\x04"
_CENTRAL_SIGNATURE = b"PK\x01\x02"
_EOCD_SIGNATURE = b"PK\x05\x06"
_MAX_COMMENT = 0xFFFF
_EOCD_SIZE = 22
_LOCATOR_SIZE = 20

ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


class ArchiveError(ValueError):
    """The bytes are not an archive this reader can interpret."""


@dataclass(frozen=True)
class Entry:
    index: int
    name: bytes                   # exactly as the central directory holds it
    flags: int
    method: int
    crc: int
    compressed_size: int          # declared
    size: int                     # declared uncompressed size
    header_offset: int
    create_system: int
    external_attr: int
    extra: bytes

    @property
    def is_encrypted(self) -> bool:
        return bool(self.flags & zw.FLAG_ENCRYPTED)

    @property
    def is_symlink(self) -> bool:
        # The Unix mode lives in the high half of the external attributes, and only
        # means anything when the archive says a Unix system made the entry.
        mode = self.external_attr >> 16
        return self.create_system == zw.UNIX and (mode & 0o170000) == 0o120000


def parse_extra(extra: bytes) -> list[tuple[int, bytes]]:
    """Split an extra-field block into (header id, data) pairs."""
    fields: list[tuple[int, bytes]] = []
    position = 0
    while position < len(extra):
        if position + 4 > len(extra):
            raise ArchiveError("a truncated extra field")
        header_id, length = struct.unpack_from("<HH", extra, position)
        position += 4
        if position + length > len(extra):
            raise ArchiveError("an extra field longer than its block")
        fields.append((header_id, extra[position:position + length]))
        position += length
    return fields


def unicode_path(name: bytes, extra: bytes) -> str | None:
    """The Info-ZIP Unicode Path field's name, when present and still valid for `name`.

    The field is ignored when its CRC no longer matches the header name (the name was
    edited after the field was written) and when it is not UTF-8.
    """
    try:
        fields = parse_extra(extra)
    except ArchiveError:
        return None
    for header_id, data in fields:
        if header_id != zw.EXTRA_UNICODE_PATH or len(data) < 5 or data[0] != 1:
            continue
        if struct.unpack_from("<I", data, 1)[0] != zlib.crc32(name) & 0xFFFFFFFF:
            continue
        try:
            return data[5:].decode("utf-8")
        except UnicodeDecodeError:
            continue
    return None


def decode_display_name(name: bytes, flags: int, extra: bytes) -> str:
    """The name to show, never to rely on: UTF-8 if flag 11 is set, else the Info-ZIP
    Unicode Path field, else strict UTF-8, else cp866.

    cp866 maps every byte, so the last step cannot fail. A name flagged UTF-8 that is not
    valid UTF-8 is shown with replacement characters rather than refused: it is display
    only, and its raw bytes still take part in every comparison.
    """
    if flags & zw.FLAG_UTF8:
        return name.decode("utf-8", errors="replace")
    named = unicode_path(name, extra)
    if named is not None:
        return named
    try:
        return name.decode("utf-8")
    except UnicodeDecodeError:
        return name.decode("cp866")


class Archive:
    """An archive opened for reading from bytes or a file; nothing is read twice."""

    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        handle.seek(0, io.SEEK_END)
        self.size = handle.tell()
        self.declared_count, self._directory_size, self._directory_offset = self._locate()
        self.entries: tuple[Entry, ...] = ()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Archive":
        return cls(io.BytesIO(data))

    @classmethod
    def from_path(cls, path: Path) -> "Archive":
        handle = path.open("rb")
        try:
            return cls(handle)
        except BaseException:
            handle.close()
            raise

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "Archive":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ArchiveError("a read outside the file")
        self._handle.seek(offset)
        data = self._handle.read(length)
        if len(data) != length:
            raise ArchiveError("the file ends inside a structure")
        return data

    def _locate(self) -> tuple[int, int, int]:
        """(entry count, directory size, directory offset) from the end records."""
        tail_length = min(self.size, _EOCD_SIZE + _MAX_COMMENT)
        tail = self._read(self.size - tail_length, tail_length)
        position = tail.rfind(_EOCD_SIGNATURE)
        if position < 0 or position + _EOCD_SIZE > len(tail):
            raise ArchiveError("no end-of-central-directory record")
        (_sig, disk, directory_disk, on_disk, total, directory_size, directory_offset,
         comment_length) = struct.unpack_from("<IHHHHIIH", tail, position)
        if position + _EOCD_SIZE + comment_length > len(tail):
            raise ArchiveError("the archive comment runs past the end of the file")
        if disk != 0 or directory_disk != 0 or on_disk != total:
            raise ArchiveError("a multi-disk archive")
        end_record = self.size - tail_length + position
        needs_zip64 = (total == 0xFFFF or directory_size == 0xFFFFFFFF
                       or directory_offset == 0xFFFFFFFF)
        if needs_zip64:
            total, directory_size, directory_offset = self._locate_zip64(end_record)
        if directory_offset + directory_size > end_record:
            raise ArchiveError("the central directory overlaps the end records")
        return total, directory_size, directory_offset

    def _locate_zip64(self, end_record: int) -> tuple[int, int, int]:
        if end_record < _LOCATOR_SIZE:
            raise ArchiveError("a ZIP64 marker without a ZIP64 locator")
        locator = self._read(end_record - _LOCATOR_SIZE, _LOCATOR_SIZE)
        signature, _disk, record_offset, _disks = struct.unpack("<IIQI", locator)
        if signature != zw._EOCD64_LOCATOR:
            raise ArchiveError("a ZIP64 marker without a ZIP64 locator")
        record = self._read(record_offset, 56)
        (signature, _size, _made, _needed, disk, directory_disk, on_disk, total,
         directory_size, directory_offset) = struct.unpack("<IQHHIIQQQQ", record)
        if signature != zw._EOCD64:
            raise ArchiveError("the ZIP64 end record is missing")
        if disk != 0 or directory_disk != 0 or on_disk != total:
            raise ArchiveError("a multi-disk archive")
        return total, directory_size, directory_offset

    def load_entries(self) -> tuple[Entry, ...]:
        """Parse the central directory; the entry count must agree with its size."""
        blob = self._read(self._directory_offset, self._directory_size)
        entries: list[Entry] = []
        position = 0
        for index in range(self.declared_count):
            if blob[position:position + 4] != _CENTRAL_SIGNATURE:
                raise ArchiveError(f"entry {index}: no central directory signature")
            if position + 46 > len(blob):
                raise ArchiveError(f"entry {index}: a truncated directory header")
            (_sig, made_by, _needed, flags, method, _time, _date, crc, csize, usize,
             name_length, extra_length, comment_length, _disk, _internal, external,
             offset) = struct.unpack_from("<IHHHHHHIIIHHHHHII", blob, position)
            position += 46
            end = position + name_length + extra_length + comment_length
            if end > len(blob):
                raise ArchiveError(f"entry {index}: a truncated directory entry")
            name = blob[position:position + name_length]
            extra = blob[position + name_length:position + name_length + extra_length]
            position = end
            csize, usize, offset = self._zip64_values(index, extra, csize, usize, offset)
            entries.append(Entry(index, name, flags, method, crc, csize, usize, offset,
                                 made_by >> 8, external, extra))
        if position != len(blob):
            raise ArchiveError("the central directory is longer than its entries")
        self.entries = tuple(entries)
        return self.entries

    @staticmethod
    def _zip64_values(index: int, extra: bytes, csize: int, usize: int,
                      offset: int) -> tuple[int, int, int]:
        """Resolve the 0xFFFFFFFF markers from the ZIP64 field, in the field's own order."""
        if 0xFFFFFFFF not in (csize, usize, offset):
            return csize, usize, offset
        data = next((d for i, d in parse_extra(extra) if i == zw.EXTRA_ZIP64), None)
        if data is None:
            raise ArchiveError(f"entry {index}: a ZIP64 marker without a ZIP64 field")
        position = 0

        def take() -> int:
            nonlocal position
            if position + 8 > len(data):
                raise ArchiveError(f"entry {index}: a truncated ZIP64 field")
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

    def _data_start(self, entry: Entry) -> int:
        header = self._read(entry.header_offset, 30)
        if header[:4] != _LOCAL_SIGNATURE:
            raise ArchiveError(f"entry {entry.index}: no local header signature")
        name_length, extra_length = struct.unpack_from("<HH", header, 26)
        if self._read(entry.header_offset + 30, name_length) != entry.name:
            raise ArchiveError(f"entry {entry.index}: the local header names another member")
        start = entry.header_offset + 30 + name_length + extra_length
        if start + entry.compressed_size > self._directory_offset:
            raise ArchiveError(f"entry {entry.index}: the data runs into the directory")
        return start

    def read_chunks(self, entry: Entry, piece: int = 1 << 16) -> Iterator[bytes]:
        """The member's bytes, decompressed, in chunks of at most `piece` bytes.

        The declared sizes are not used to decide how much to read beyond the compressed
        length: a caller counts what actually comes out, which is the only honest figure.
        """
        if entry.method not in (zw.STORED, zw.DEFLATED):
            raise ArchiveError(f"entry {entry.index}: compression method {entry.method}")
        start = self._data_start(entry)
        remaining = entry.compressed_size
        if entry.method == zw.STORED:
            position = start
            while remaining > 0:
                data = self._read(position, min(piece, remaining))
                position += len(data)
                remaining -= len(data)
                yield data
            return
        inflater = zlib.decompressobj(-15)
        position = start
        try:
            while remaining > 0 and not inflater.eof:
                data = self._read(position, min(piece, remaining))
                position += len(data)
                remaining -= len(data)
                pending = data
                while pending:
                    out = inflater.decompress(pending, piece)
                    if out:
                        yield out
                    pending = inflater.unconsumed_tail
                    if not out and not pending:
                        break
            while not inflater.eof:
                out = inflater.flush(piece)
                if not out:
                    break
                yield out
        except zlib.error as exc:
            raise ArchiveError(f"entry {entry.index}: the deflate data is corrupt ({exc})") from None
        if not inflater.eof:
            raise ArchiveError(f"entry {entry.index}: the deflate stream does not end")
