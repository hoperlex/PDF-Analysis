"""The PDF envelope, applied to every member of a ZIP set (`CMP-INGEST-ZIP-01`).

The archive rules are in ``test_adversarial_archives.py`` and run with no envelope; here the
envelope runs, with the real one (``inspect_pdf``: a child process for PDFium and another for
the stages' readers) on the committed comparison PDFs, so the tests are few and each is worth
its two processes. What is shown:

* a member's PDF is read by the *existing* envelope, with its facts kept on the member;
* a member that fails it refuses the whole set with the envelope's own ``field``, ``constraint``
  and message, and says which member -- by ordinal, never by name -- (:class:`SetMemberRefused`);
* a ZIP named ``.pdf`` is a PDF that fails the envelope, not an archive that is opened;
* the archive's cheap rules come first: an archive refusal wins over a bad PDF, and no PDF is
  read for an archive that is refused;
* the check is a parameter: a caller's own envelope is called, and ``None`` runs none;
* a fault that is the server's (not a refusal of the caller's file) propagates as itself, and
  leaves nothing behind.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from auditmanager.ingest import envelope as envelope_module
from auditmanager.ingest.comparison_zip import (
    SetMemberRefused,
    extract_pdf_set,
    inspect_pdf_member,
    reader,
)
from auditmanager.ingest.envelope import inspect_pdf
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.ingest.comparison_zip import zip_builders as z
from tests.unit.ingest.comparison_zip.zip_builders import (  # noqa: F401  (the autouse fixture)
    AR_NEGATIVE,
    accept,
    build,
    entry,
    nested,
    pdf,
    private_temporary_directory,
    real_pdf,
    refusal,
    zw,
)


def _fields(refused: DomainError) -> tuple[str, str]:
    fields = dict(refused.detail_fields)
    return str(fields["field"]), str(fields["constraint"])


def _refused_member(archive: bytes, **options: Any) -> SetMemberRefused:
    with pytest.raises(SetMemberRefused) as caught:
        extract_pdf_set(io.BytesIO(archive), **options)
    return caught.value


def test_every_pdf_of_a_set_is_read_by_the_existing_envelope_and_keeps_its_facts() -> None:
    archive = build(
        entry("stage/v1.pdf", real_pdf(1)),
        entry("stage/v2.pdf", real_pdf(2)),
        nested("proj.zip", entry("v4.pdf", real_pdf(4))),
    )
    with extract_pdf_set(io.BytesIO(archive)) as found:
        assert [m.facts.page_count for m in found.members if m.facts] == [6, 6, 6]
        assert [m.facts.byte_size == m.size for m in found.members if m.facts] == [True] * 3
        # the same facts the envelope gives the bare file
        direct = inspect_pdf(real_pdf(4), require_text=False)
        assert found.members[2].facts == direct


def test_the_default_envelope_is_the_existing_one_with_the_text_rule_left_to_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def spy(handle: BinaryIO, *, require_text: bool) -> Any:
        calls.append(require_text)
        return inspect_pdf(handle, require_text=require_text)

    monkeypatch.setattr(reader, "inspect_pdf", spy)
    with extract_pdf_set(io.BytesIO(build(entry("a.pdf", real_pdf(1))))) as found:
        assert found.members[0].facts is not None
    assert calls == [False]
    assert extract_pdf_set.__kwdefaults__["envelope"] is inspect_pdf_member  # type: ignore[index]


@pytest.mark.parametrize(
    ("payload", "constraint"),
    [
        (b"this is not a pdf", "pdf_magic_bytes"),
        (b"", "non_empty"),
        (zw.build_zip([zw.Member(b"inner.pdf", b"%PDF-1.7\n")]), "pdf_magic_bytes"),
        (real_pdf(1)[:2000], "parseable_pdf"),
        ((AR_NEGATIVE / "encrypted.pdf").read_bytes(), "not_encrypted"),
    ],
    ids=["text", "empty", "a-zip-named-pdf", "truncated", "encrypted"],
)
def test_a_pdf_that_fails_the_envelope_refuses_the_set_with_the_envelopes_own_refusal(
    payload: bytes, constraint: str
) -> None:
    archive = build(entry("good.pdf", real_pdf(1)), entry("bad.pdf", payload))
    refused = _refused_member(archive)
    assert _fields(refused) == ("content", constraint)
    assert refused.member_ordinal == 1

    # It *is* the envelope's refusal: same code, details and sentence, nothing added to them.
    with pytest.raises(DomainError) as direct:
        inspect_pdf(payload, require_text=False)
    assert refused.code == direct.value.code
    assert dict(refused.detail_fields) == dict(direct.value.detail_fields)
    assert str(refused) == str(direct.value)
    refused.envelope("correlation")  # the envelope's screen: no name, no path


def test_the_member_is_named_by_ordinal_and_a_nested_member_has_its_place_in_the_set() -> None:
    archive = build(
        entry("a.pdf", real_pdf(1)),
        nested("n.zip", entry("b.pdf", real_pdf(2)), entry("c.pdf", b"not a pdf at all")),
    )
    refused = _refused_member(archive)
    assert refused.member_ordinal == 2
    assert "c.pdf" not in str(refused) and "n.zip" not in str(refused)


def test_the_archive_rules_come_first_and_no_pdf_is_read_for_a_refused_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(handle: BinaryIO) -> Any:
        raise AssertionError("the envelope was run for an archive that is refused")

    archive = build(
        entry("bad.pdf", b"not a pdf"),
        nested("n.zip", entry("link.pdf", b"/etc/passwd", external_attr=zw.SYMLINK)),
    )
    assert refusal(archive, envelope=forbidden) == "comparison_zip_symlink"


def test_a_caller_may_pass_its_own_envelope_and_it_is_called_once_per_member_in_order() -> None:
    seen: list[int] = []

    def mine(handle: BinaryIO) -> str:
        seen.append(len(handle.read()))
        return "facts"

    archive = build(pdf("a.pdf", b"1"), pdf("b.pdf", b"22"), nested("n.zip", pdf("c.pdf", b"333")))
    with extract_pdf_set(io.BytesIO(archive), envelope=mine) as found:  # type: ignore[arg-type]
        assert [m.facts for m in found.members] == ["facts"] * 3
    assert seen == [len(z.PDF_HEADER) + n for n in (1, 2, 3)]


def test_a_caller_envelope_that_refuses_names_the_member() -> None:
    def picky(handle: BinaryIO) -> str:
        if handle.read().endswith(b"2"):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, message="Too many drawing elements.",
                field="content", constraint="pdf_page_content",
            )
        return "ok"

    archive = build(pdf("a.pdf", b"1"), pdf("b.pdf", b"2"), pdf("c.pdf", b"3"))
    refused = _refused_member(archive, envelope=picky)  # type: ignore[arg-type]
    assert _fields(refused) == ("content", "pdf_page_content")
    assert refused.member_ordinal == 1


def test_no_envelope_runs_none_and_leaves_the_facts_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("the envelope ran")

    monkeypatch.setattr(reader, "inspect_pdf", forbidden)
    with accept(build(pdf("a.pdf"), pdf("b.pdf")), envelope=None) as found:
        assert [m.facts for m in found.members] == [None, None]
    # ... and the check a caller defers is the very function the reader would have run
    with extract_pdf_set(io.BytesIO(build(entry("a.pdf", real_pdf(1)))), envelope=None) as found:
        with found.open(found.members[0]) as handle:
            assert envelope_module.inspect_pdf(handle, require_text=False).page_count == 6


def test_a_fault_that_is_not_a_refusal_propagates_as_itself_and_leaves_nothing_behind() -> None:
    class Boom(RuntimeError):
        pass

    def broken(handle: BinaryIO) -> Any:
        raise Boom("the reader process did not start")

    with pytest.raises(Boom):
        extract_pdf_set(io.BytesIO(build(pdf("a.pdf"))), envelope=broken)  # type: ignore[arg-type]
    # (the autouse fixture asserts the temporary directories are gone)


def test_the_set_is_refused_whole_when_one_pdf_fails_even_if_the_rest_are_sound(
    private_temporary_directory: Path,
) -> None:
    archive = build(*[entry(f"v{n}.pdf", real_pdf(n)) for n in (1, 2, 3)],
                    entry("zz.pdf", b"junk"))
    refused = _refused_member(archive)
    assert refused.member_ordinal == 3
    assert not list(private_temporary_directory.iterdir())
