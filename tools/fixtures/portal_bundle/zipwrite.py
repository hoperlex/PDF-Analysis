"""A hand-rolled, deterministic ZIP writer in which every header field is the caller's.

Python's `zipfile` cannot write what the bundle rules have to be tested against: a
cp866 name, an Info-ZIP Unicode Path extra field, a symbolic-link attribute, an encrypted
flag on plain bytes, a header that lies about a size, a compression method it does not
know. Those are exactly the archives the ingest envelope must refuse, so the writer here
puts each field where the caller says and checks nothing about whether it makes sense.
Valid output is verified separately, by reading it back with `zipfile` in the tests.

Determinism, which is the point of a fixture:

*   One fixed DOS timestamp; no clock, no PRNG, no environment.
*   Members and the central directory are written in the order given.
*   Method 8 has two compressors. `stored_blocks` hand-encodes the deflate stream as
    stored blocks, so its bytes depend on nothing but this file; `zlib` really compresses
    (needed for archives with a high ratio) at a fixed level, but its bytes are only as
    stable as the zlib build. Committed bundles use the first; the second is for archives
    built at test time and never hashed.

Members stream: a payload is a sequence of chunks and a file target is back-patched, so an
archive with a multi-hundred-MiB member is written without holding it in memory.
"""

from __future__ import annotations

import io
import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

STORED = 0
DEFLATED = 8

FLAG_ENCRYPTED = 0x0001
FLAG_DESCRIPTOR = 0x0008
FLAG_UTF8 = 0x0800

# 2026-07-24 07:45:12, packed the way MS-DOS packs it (two-second resolution).
DOS_DATE = ((2026 - 1980) << 9) | (7 << 5) | 24
DOS_TIME = (7 << 11) | (45 << 5) | (12 // 2)

UNIX = 3
REGULAR_FILE = 0o100644 << 16
DIRECTORY = (0o040755 << 16) | 0x10
SYMLINK = 0o120777 << 16

EXTRA_ZIP64 = 0x0001
EXTRA_UNICODE_PATH = 0x7075

_LOCAL = 0x04034B50
_CENTRAL = 0x02014B50
_EOCD = 0x06054B50
_EOCD64 = 0x06064B50
_EOCD64_LOCATOR = 0x07064B50
_DESCRIPTOR = 0x08074B50
_SENTINEL32 = 0xFFFFFFFF
_SENTINEL16 = 0xFFFF

CHUNK = 1 << 20


class Payload(Protocol):
    """Bytes that can be produced chunk by chunk, with a known total size."""

    @property
    def size(self) -> int: ...

    def chunks(self) -> Iterator[bytes]: ...


@dataclass(frozen=True)
class Data:
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def chunks(self) -> Iterator[bytes]:
        if self.data:
            yield self.data


@dataclass(frozen=True)
class Fill:
    """`size` bytes of one repeated byte, after an optional literal prefix.

    The prefix counts toward the size. Zeros deflate to roughly a thousandth of their
    length, which is how a test writes a member that is hundreds of MiB when unpacked
    into a file of a few hundred KiB.
    """

    size: int
    byte: int = 0
    prefix: bytes = b""

    def chunks(self) -> Iterator[bytes]:
        if len(self.prefix) > self.size:
            raise ValueError("the prefix is longer than the payload")
        if self.prefix:
            yield self.prefix
        remaining = self.size - len(self.prefix)
        block = bytes([self.byte]) * min(CHUNK, remaining) if remaining else b""
        while remaining > 0:
            piece = block if remaining >= len(block) else block[:remaining]
            yield piece
            remaining -= len(piece)


@dataclass(frozen=True)
class FromFile:
    path: Path

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    def chunks(self) -> Iterator[bytes]:
        with self.path.open("rb") as handle:
            while chunk := handle.read(CHUNK):
                yield chunk


@dataclass
class Member:
    """One archive entry and every header field a test may want to set."""

    name: bytes
    payload: bytes | Payload = b""
    method: int = STORED
    deflate: str = "stored_blocks"        # method 8 only: "stored_blocks" or "zlib"
    flags: int = 0                        # OR-ed in: FLAG_ENCRYPTED / FLAG_DESCRIPTOR / FLAG_UTF8
    zip64: bool = False
    local_extra: bytes = b""
    central_extra: bytes = b""
    external_attr: int = REGULAR_FILE
    create_system: int = UNIX
    declared_size: int | None = None      # a header that lies about the uncompressed size
    declared_compressed_size: int | None = None
    crc: int | None = None                # a header that carries the wrong CRC
    comment: bytes = b""


def deflate_stored_blocks(data: bytes) -> bytes:
    """A valid raw deflate stream made only of stored blocks (no zlib involved)."""
    compressor = _StoredBlocks()
    return compressor.compress(data) + compressor.flush()


class _StoredBlocks:
    """Streaming stored-block deflate. The last block is the one `flush` writes, so a
    block is held back until more input proves it is not final."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    @staticmethod
    def _block(data: bytes | bytearray, final: bool) -> bytes:
        n = len(data)
        return bytes([1 if final else 0]) + struct.pack("<HH", n, n ^ 0xFFFF) + bytes(data)

    def compress(self, chunk: bytes) -> bytes:
        self._buffer += chunk
        out = bytearray()
        while len(self._buffer) > 0xFFFF:
            out += self._block(self._buffer[:0xFFFF], final=False)
            del self._buffer[:0xFFFF]
        return bytes(out)

    def flush(self) -> bytes:
        return self._block(self._buffer, final=True)


class _Passthrough:
    def compress(self, chunk: bytes) -> bytes:
        return chunk

    def flush(self) -> bytes:
        return b""


class _Zlib:
    def __init__(self) -> None:
        # Raw deflate, level 6, default strategy: fixed, so one build repeats itself.
        self._z = zlib.compressobj(6, zlib.DEFLATED, -15, 8, zlib.Z_DEFAULT_STRATEGY)

    def compress(self, chunk: bytes) -> bytes:
        return self._z.compress(chunk)

    def flush(self) -> bytes:
        return self._z.flush()


def _compressor(member: Member):
    if member.method == DEFLATED:
        if member.deflate == "stored_blocks":
            return _StoredBlocks()
        if member.deflate == "zlib":
            return _Zlib()
        raise ValueError(f"unknown deflate mode {member.deflate!r}")
    # Stored, and any method this writer does not know: the payload is written as is.
    return _Passthrough()


def unicode_path_extra(header_name: bytes, utf8_name: bytes) -> bytes:
    """The Info-ZIP Unicode Path extra field (0x7075) for a header name.

    Version 1, the CRC-32 of the name as the header carries it (a reader ignores the
    field if the header name was edited since), then the name in UTF-8.
    """
    body = bytes([1]) + struct.pack("<I", zlib.crc32(header_name) & 0xFFFFFFFF) + utf8_name
    return struct.pack("<HH", EXTRA_UNICODE_PATH, len(body)) + body


def _as_payload(payload: bytes | Payload) -> Payload:
    return Data(payload) if isinstance(payload, (bytes, bytearray)) else payload


def _pack32(value: int, what: str) -> int:
    if not 0 <= value <= _SENTINEL32:
        raise ValueError(f"{what} {value} needs ZIP64 (set Member.zip64)")
    return value


def _local_header(m: Member, crc: int, csize: int, usize: int) -> bytes:
    descriptor = bool(m.flags & FLAG_DESCRIPTOR)
    extra = m.local_extra
    if m.zip64:
        # A ZIP64 local header carries both sizes in its extra field; with a data
        # descriptor they are zero there, as they are in the header proper.
        values = (0, 0) if descriptor else (usize, csize)
        extra = struct.pack("<HHQQ", EXTRA_ZIP64, 16, *values) + extra
        header_sizes = (_SENTINEL32, _SENTINEL32)
    elif descriptor:
        header_sizes = (0, 0)
    else:
        header_sizes = (_pack32(csize, "compressed size"), _pack32(usize, "size"))
    return struct.pack(
        "<IHHHHHIIIHH", _LOCAL, 45 if m.zip64 else 20, m.flags, m.method,
        DOS_TIME, DOS_DATE, 0 if descriptor else crc, header_sizes[0], header_sizes[1],
        len(m.name), len(extra),
    ) + m.name + extra


def _descriptor(crc: int, csize: int, usize: int, zip64: bool) -> bytes:
    if zip64:
        return struct.pack("<IIQQ", _DESCRIPTOR, crc, csize, usize)
    return struct.pack("<IIII", _DESCRIPTOR, crc, _pack32(csize, "compressed size"),
                       _pack32(usize, "size"))


def _central_header(m: Member, crc: int, csize: int, usize: int, offset: int) -> bytes:
    extra = m.central_extra
    if m.zip64:
        extra = struct.pack("<HHQQ", EXTRA_ZIP64, 16, usize, csize) + extra
        header_sizes = (_SENTINEL32, _SENTINEL32)
    else:
        header_sizes = (_pack32(csize, "compressed size"), _pack32(usize, "size"))
    version = 45 if m.zip64 else 20
    return struct.pack(
        "<IHHHHHHIIIHHHHHII", _CENTRAL, (m.create_system << 8) | version, version,
        m.flags, m.method, DOS_TIME, DOS_DATE, crc, header_sizes[0], header_sizes[1],
        len(m.name), len(extra), len(m.comment), 0, 0, m.external_attr,
        _pack32(offset, "local header offset"),
    ) + m.name + extra + m.comment


@dataclass
class _Written:
    member: Member
    crc: int
    csize: int
    usize: int
    offset: int


def _emit(out: BinaryIO, m: Member) -> _Written:
    offset = out.tell()
    descriptor = bool(m.flags & FLAG_DESCRIPTOR)
    out.write(_local_header(m, 0, 0, 0))       # a placeholder of the final length

    payload = _as_payload(m.payload)
    compressor = _compressor(m)
    crc = 0
    usize = 0
    csize = 0
    for chunk in payload.chunks():
        crc = zlib.crc32(chunk, crc)
        usize += len(chunk)
        packed = compressor.compress(chunk)
        csize += len(packed)
        out.write(packed)
    tail = compressor.flush()
    csize += len(tail)
    out.write(tail)

    crc &= 0xFFFFFFFF
    if m.crc is not None:
        crc = m.crc
    if m.declared_size is not None:
        usize = m.declared_size
    if m.declared_compressed_size is not None:
        csize = m.declared_compressed_size

    if descriptor:
        out.write(_descriptor(crc, csize, usize, m.zip64))
    else:
        end = out.tell()
        out.seek(offset)
        out.write(_local_header(m, crc, csize, usize))
        out.seek(end)
    return _Written(m, crc, csize, usize, offset)


def _finish(out: BinaryIO, written: list[_Written], zip64_end: bool, comment: bytes) -> None:
    directory_offset = out.tell()
    for w in written:
        out.write(_central_header(w.member, w.crc, w.csize, w.usize, w.offset))
    directory_size = out.tell() - directory_offset
    count = len(written)
    if zip64_end:
        record_offset = out.tell()
        out.write(struct.pack("<IQHHIIQQQQ", _EOCD64, 44, 45, 45, 0, 0, count, count,
                              directory_size, directory_offset))
        out.write(struct.pack("<IIQI", _EOCD64_LOCATOR, 0, record_offset, 1))
        fields = (_SENTINEL16, _SENTINEL32, _SENTINEL32)
    else:
        fields = (count, directory_size, directory_offset)
    out.write(struct.pack("<IHHHHIIH", _EOCD, 0, 0, fields[0], fields[0], fields[1],
                          fields[2], len(comment)) + comment)


def build_zip(members: list[Member], *, zip64_end: bool = False, comment: bytes = b"") -> bytes:
    """Build an archive in memory. For members too large for that, use `write_zip`."""
    out = io.BytesIO()
    _finish(out, [_emit(out, m) for m in members], zip64_end, comment)
    return out.getvalue()


def write_zip(path: Path, members: list[Member], *, zip64_end: bool = False,
              comment: bytes = b"") -> None:
    """Write an archive to a file, streaming each member and back-patching its header."""
    with path.open("wb") as out:
        _finish(out, [_emit(out, m) for m in members], zip64_end, comment)
