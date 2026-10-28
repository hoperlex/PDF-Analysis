"""Archives for the ZIP-set tests, built header by header (`CMP-INGEST-ZIP-01`).

Not a test module. Python's ``zipfile`` writes only what a well-behaved archiver writes; the
archives a ZIP set must refuse are the ones no archiver writes -- a header that lies about a
size, an entry flagged as a symbolic link, an encrypted flag on plain bytes, a name that
decodes two ways. The repository already has a writer where every header field is the caller's
(``tools/fixtures/portal_bundle/zipwrite.py``, the one the portal bundle's negatives are built
with); it is loaded here by its path, so nothing is put on ``sys.path`` and this directory
needs no ``conftest.py``.

``refusal`` and ``accept`` are the two ways a test judges an archive, and both check the same
two things the reader owes every caller: a refusal names one of the registered constraints and
leaves no temporary directory behind, and the temporary directories live in a directory the
test owns (the fixture below), so "nothing is left" is a fact about this test and not about a
shared ``/tmp`` another process is also writing to.
"""

from __future__ import annotations

import importlib.util
import io
import struct
import sys
import tempfile
import zlib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest.comparison_zip import (
    CONSTRAINTS,
    DEFAULT_SET_POLICY,
    ExtractedSet,
    SetPolicy,
    extract_pdf_set,
)
from auditmanager.shared.errors import DomainError

MiB = 1024 * 1024
GiB = 1024 * MiB
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: The repository's header-level ZIP writer (``Member``, ``Fill``, ``build_zip``, the constants).
zw = _load(
    "cmp_zip_tests_zipwrite",
    REPOSITORY_ROOT / "tools" / "fixtures" / "portal_bundle" / "zipwrite.py",
)
Member = zw.Member
Fill = zw.Fill

PDF_HEADER = b"%PDF-1.7\n"
VS1 = REPOSITORY_ROOT / "fixtures" / "comparison" / "vs1"
AR_NEGATIVE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "negative"


def real_pdf(n: int = 1) -> bytes:
    """One of the five committed comparison PDFs (six pages each): a PDF the envelope accepts."""
    return (VS1 / f"v{n}.pdf").read_bytes()


# -- a private temporary directory per test ----------------------------------------------


@pytest.fixture(autouse=True)
def private_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """The reader's temporary directories are made here, and none may outlive the test.

    A test that keeps an accepted set open closes it before it ends; a test that is refused
    never had one. Either way this directory is empty at the end, which is the fact "a
    refusal keeps nothing" is.
    """
    work = tmp_path / "scratch"
    work.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(work))
    yield work
    leftovers = sorted(path.name for path in work.iterdir())
    assert not leftovers, f"temporary directories outlived the test: {leftovers}"


# -- members -------------------------------------------------------------------------------


def name_of(text: str | bytes) -> tuple[bytes, int]:
    """A name as the header holds it, and the UTF-8 flag an archiver sets for a non-ASCII one."""
    if isinstance(text, bytes):
        return text, 0
    raw = text.encode("utf-8")
    return raw, (zw.FLAG_UTF8 if any(byte > 0x7F for byte in raw) else 0)


def entry(name: str | bytes, payload: bytes | Any = b"", **fields: Any) -> Any:
    """One stored entry; ``fields`` are any ``Member`` field (flags, declared_size, ...)."""
    raw, flag = name_of(name)
    fields["flags"] = fields.get("flags", 0) | flag
    return Member(raw, payload, **fields)


def pdf(name: str | bytes, tag: bytes = b"") -> Any:
    """A member that is named like a PDF and begins like one (the archive rules read no more)."""
    return entry(name, PDF_HEADER + tag)


def deflated(name: str | bytes, payload: bytes | Any, **fields: Any) -> Any:
    """A really compressed entry (zlib, level 6)."""
    return entry(name, payload, method=zw.DEFLATED, deflate="zlib", **fields)


def directory(name: str | bytes) -> Any:
    return entry(name, b"", external_attr=zw.DIRECTORY)


def build(*members: Any, **options: Any) -> bytes:
    return zw.build_zip(list(members), **options)


def nested(name: str | bytes, *members: Any) -> Any:
    """An entry that is itself a ZIP of ``members`` (stored)."""
    return entry(name, build(*members))


def unicode_path(header_name: bytes, shown: str) -> bytes:
    """The Info-ZIP Unicode Path field that makes a reader show ``shown`` for ``header_name``."""
    return zw.unicode_path_extra(header_name, shown.encode("utf-8"))


def with_method(archive: bytes, method: int) -> bytes:
    """``archive`` with the compression method of every local and central header rewritten.

    The payload stays as it was written, so a stored payload that *is* a raw deflate stream
    becomes a deflated member whose header claims more compressed bytes than its stream uses.
    """
    data = bytearray(archive)
    position = 0
    while (position := data.find(b"PK\x03\x04", position)) >= 0:
        struct.pack_into("<H", data, position + 8, method)
        position += 4
    position = 0
    while (position := data.find(b"PK\x01\x02", position)) >= 0:
        struct.pack_into("<H", data, position + 10, method)
        position += 4
    return bytes(data)


def with_entry_count(archive: bytes, count: int) -> bytes:
    """``archive`` whose end record claims ``count`` entries (it has no comment)."""
    data = bytearray(archive)
    end = data.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", data, end + 8, count, count)
    return bytes(data)


def with_shared_local_header(archive: bytes) -> bytes:
    """``archive`` whose second central entry points at the first entry's local header and data
    (the overlap a quine bomb is made of)."""
    data = bytearray(archive)
    first = data.find(b"PK\x01\x02")
    second = data.find(b"PK\x01\x02", first + 4)
    (offset,) = struct.unpack_from("<I", data, first + 42)
    struct.pack_into("<I", data, second + 42, offset)
    return bytes(data)


def raw_deflate(payload: bytes) -> bytes:
    compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
    return compressor.compress(payload) + compressor.flush()


# -- judging ---------------------------------------------------------------------------------


def refusal(
    archive: bytes,
    *,
    policy: SetPolicy = DEFAULT_SET_POLICY,
    envelope: Callable[..., Any] | None = None,
) -> str:
    """The constraint an archive is refused with. An accepted archive fails the test.

    The constraint is checked against the registered ones, the field against ``file``, and
    the refusal against the envelope's screen -- the three things a caller depends on.
    """
    try:
        found = extract_pdf_set(io.BytesIO(archive), policy=policy, envelope=envelope)
    except DomainError as refused:
        fields = dict(refused.detail_fields)
        assert fields.get("field") == "file", fields
        constraint = str(fields.get("constraint"))
        assert constraint in CONSTRAINTS, f"{constraint} is not a registered reason of a ZIP set"
        refused.envelope("test-correlation")  # screens the message and the details
        return constraint
    found.close()
    raise AssertionError("the archive was accepted")


def accept(
    archive: bytes,
    *,
    policy: SetPolicy = DEFAULT_SET_POLICY,
    envelope: Callable[..., Any] | None = None,
) -> ExtractedSet:
    """An accepted set (the caller closes it, or uses it as a context manager)."""
    return extract_pdf_set(io.BytesIO(archive), policy=policy, envelope=envelope)


def spy_on_inflation(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """``[n]``: the bytes the reader has inflated or copied out of members so far."""
    from auditmanager.ingest import bundle_archive

    produced = [0]
    original = bundle_archive._Archive.read_chunks

    def spy(self: Any, entry: Any) -> Iterator[bytes]:
        for chunk in original(self, entry):
            produced[0] += len(chunk)
            yield chunk

    monkeypatch.setattr(bundle_archive._Archive, "read_chunks", spy)
    return produced


def listing(found: ExtractedSet) -> list[tuple[int, int, str, int]]:
    """``(ordinal, level, display name, size)`` of every member."""
    return [(m.ordinal, m.level, m.display_name, m.size) for m in found.members]
