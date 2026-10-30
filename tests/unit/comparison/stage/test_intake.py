"""The first ZIP caller checks resources before asking the reader for members."""

from __future__ import annotations

import io
import hashlib
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

import pytest

from auditmanager.comparison.stage.intake import (
    MAX_RAW_ZIP_BYTES,
    MIN_FREE_RESERVE_BYTES,
    admit_stage_zip_stream,
    open_stage_zip,
)
from auditmanager.ingest.comparison_zip import SetMemberRefused
from auditmanager.shared.errors import DomainError, ErrorCode


PDF = Path("tests/e2e/pc01/journey/fixtures/w28-live/w28_own_document.pdf")


def archive(name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        writer.writestr(name, content)
    return output.getvalue()


def budget(raw_bytes: int) -> int:
    return raw_bytes + MIN_FREE_RESERVE_BYTES


@pytest.mark.parametrize(
    ("declared", "active", "free", "constraint", "dependency"),
    [
        (MAX_RAW_ZIP_BYTES + 1, 0, 10**12, f"raw_zip_bytes <= {MAX_RAW_ZIP_BYTES}", None),
        (1, 1, 10**12, None, "comparison_stage_zip_admission"),
        (1, 0, MIN_FREE_RESERVE_BYTES, None, "comparison_stage_zip_disk"),
    ],
)
def test_admission_refuses_before_reading_archive(
    monkeypatch: pytest.MonkeyPatch,
    declared: int,
    active: int,
    free: int,
    constraint: str | None,
    dependency: str | None,
) -> None:
    def must_not_extract(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an unadmitted archive reached the reader")

    monkeypatch.setattr("auditmanager.comparison.stage.intake.extract_pdf_set", must_not_extract)
    with pytest.raises(DomainError) as raised:
        open_stage_zip(
            io.BytesIO(b"x"), declared_bytes=declared,
            active_admissions=active, free_bytes=free,
        )
    if constraint:
        assert raised.value.code is ErrorCode.VALIDATION_FAILED
        assert raised.value.detail_fields["constraint"] == constraint
    else:
        assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert raised.value.detail_fields["dependency"] == dependency


def test_raw_size_mismatch_refuses_before_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_extract(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an undeclared raw size reached the reader")

    monkeypatch.setattr("auditmanager.comparison.stage.intake.extract_pdf_set", must_not_extract)
    with pytest.raises(DomainError) as raised:
        open_stage_zip(
            io.BytesIO(b"zip bytes"), declared_bytes=8,
            active_admissions=0, free_bytes=budget(8),
        )
    assert raised.value.detail_fields["constraint"] == "raw_zip_size_matches_declaration"


def test_first_caller_keeps_comparison_facts_and_cleans_temporary_members() -> None:
    raw = archive("drawings/site.pdf", PDF.read_bytes())
    with open_stage_zip(
        io.BytesIO(raw), declared_bytes=len(raw),
        active_admissions=0, free_bytes=budget(len(raw)),
    ) as extracted:
        assert len(extracted.members) == 1
        member = extracted.members[0]
        assert member.facts is not None
        assert member.facts.page_count >= 1
        assert member.path.is_file()
    assert not member.path.exists()


def test_first_caller_rejects_service_members() -> None:
    raw = archive("__MACOSX/._site.pdf", PDF.read_bytes())
    with pytest.raises(DomainError) as raised:
        open_stage_zip(
            io.BytesIO(raw), declared_bytes=len(raw),
            active_admissions=0, free_bytes=budget(len(raw)),
        )
    assert raised.value.detail_fields["constraint"] == "comparison_zip_member_kind"


def test_first_caller_rejects_macosx_unicode_path_alias() -> None:
    raw_name = b"ordinary.pdf"
    shown = "__MACOSX/._ordinary.pdf".encode("utf-8")
    unicode_path = struct.pack("<BI", 1, zlib.crc32(raw_name)) + shown
    output = io.BytesIO()
    entry = zipfile.ZipInfo(raw_name.decode("ascii"))
    entry.extra = struct.pack("<HH", 0x7075, len(unicode_path)) + unicode_path
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        writer.writestr(entry, PDF.read_bytes())
    raw = output.getvalue()
    with pytest.raises(DomainError) as raised:
        with admit_stage_zip_stream(
            NonSeekable(raw), declared_bytes=len(raw),
            declared_sha256=hashlib.sha256(raw).hexdigest(),
            active_admissions=0, free_bytes=budget(len(raw)),
        ):
            pytest.fail("a Unicode Path alias reached the candidate boundary")
    assert raised.value.detail_fields["constraint"] == "comparison_zip_member_kind"


class NonSeekable(io.BytesIO):
    def seek(self, *_args: object, **_kwargs: object) -> int:
        raise AssertionError("the staged object is a stream, not a seekable file")


def test_stream_caller_spools_a_bounded_verified_archive() -> None:
    raw = archive("project/site.pdf", PDF.read_bytes())
    with admit_stage_zip_stream(
        NonSeekable(raw), declared_bytes=len(raw),
        declared_sha256=hashlib.sha256(raw).hexdigest(),
        active_admissions=0, free_bytes=budget(len(raw)),
    ) as extracted:
        assert len(extracted.members) == 1
        member = extracted.members[0]
        assert member.facts is not None
        assert member.path.exists()
    assert not member.path.exists()


def test_padded_zip_cannot_cross_raw_byte_cap_before_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = archive("site.pdf", PDF.read_bytes())
    padded = raw + b"padding after ZIP directory"
    monkeypatch.setattr("auditmanager.comparison.stage.intake.MAX_RAW_ZIP_BYTES", len(raw))

    class Unread(NonSeekable):
        def read(self, *_args: object, **_kwargs: object) -> bytes:
            raise AssertionError("an oversized padded ZIP was read")

    with pytest.raises(DomainError) as raised:
        with admit_stage_zip_stream(
            Unread(padded), declared_bytes=len(padded),
            declared_sha256=hashlib.sha256(padded).hexdigest(),
            active_admissions=0, free_bytes=budget(len(padded)),
        ):
            pytest.fail("an oversized padded ZIP reached extraction")
    assert raised.value.detail_fields["constraint"] == f"raw_zip_bytes <= {len(raw)}"


@pytest.mark.parametrize(
    ("raw", "declared", "expected_sha", "constraint"),
    [
        (b"more than declared", 1, hashlib.sha256(b"m").hexdigest(), "raw_zip_size_matches_declaration"),
        (b"short", 6, hashlib.sha256(b"short").hexdigest(), "raw_zip_size_matches_declaration"),
        (b"same", 4, "0" * 64, "raw_zip_sha256_matches_declaration"),
    ],
)
def test_stream_caller_refuses_unverified_raw_bytes_before_extraction(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
    declared: int,
    expected_sha: str,
    constraint: str,
) -> None:
    def must_not_extract(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unverified raw bytes reached the ZIP reader")

    monkeypatch.setattr("auditmanager.comparison.stage.intake.extract_pdf_set", must_not_extract)
    with pytest.raises(DomainError) as raised:
        with admit_stage_zip_stream(
            NonSeekable(raw), declared_bytes=declared,
            declared_sha256=expected_sha, active_admissions=0,
            free_bytes=budget(declared),
        ):
            pass
    assert raised.value.detail_fields["constraint"] == constraint


def test_invalid_member_refuses_whole_stream_and_cleans_both_temporary_layers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    raw = archive("site.pdf", b"not a PDF")
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    with pytest.raises(SetMemberRefused):
        with admit_stage_zip_stream(
            NonSeekable(raw), declared_bytes=len(raw),
            declared_sha256=hashlib.sha256(raw).hexdigest(),
            active_admissions=0, free_bytes=budget(len(raw)),
        ):
            pytest.fail("an invalid PDF was published as an accepted set")
    assert list(tmp_path.iterdir()) == []
