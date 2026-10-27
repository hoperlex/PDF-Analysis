"""The archives a ZIP set must refuse: one refusal test for each way round the rules.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12). Every archive here is built to break one rule and
is judged by the product's reader under the set policy, with no PDF envelope (``envelope`` is
left ``None``: what is under test is the archive's rules, and each PDF check costs two child
processes -- the envelope has its own module, ``test_member_envelope.py``). Each test compares
the *constraint*, not "refused": an archive refused for the wrong reason proves nothing about
its rule. The helper ``refusal`` also requires the refusal to answer under ``field: "file"``, to
pass the error envelope's screen, and to leave no temporary directory behind (the autouse
fixture).

What is covered, and the mutation that turns each red (quoted, run and recorded in
``docs/program/CMP-INGEST-ZIP-01.md``):

* a bomb by ratio -- declared, and hidden by padding behind the stream -- and by absolute size,
  at the production figures (with headers that lie, so no gigabyte is written) and at lowered ones
  (with real bytes); a header that declares less than the member holds;
* a traversal, an absolute or drive-letter name, a backslash, and a name that only the Unicode
  Path field makes hostile;
* a symbolic link, an encrypted member (and an AES one), a method other than stored or deflate;
* a name that repeats, also after case folding and NFC;
* an archive inside an archive inside an archive, and the work that costs;
* a member that is not a PDF, an archive that holds nothing;
* too many entries, over every level together, and a central directory too large to read.
"""

from __future__ import annotations

import io
import random
import zlib

import pytest

from auditmanager.ingest.comparison_zip import (
    DEFAULT_SET_POLICY,
    SET_MAX_ENTRIES,
    SET_MEMBER_BYTES,
    SET_TOTAL_BYTES,
    SetPolicy,
    extract_pdf_set,
)
from tests.unit.ingest.comparison_zip import zip_builders as z
from tests.unit.ingest.comparison_zip.zip_builders import (  # noqa: F401  (the autouse fixture)
    MiB,
    PDF_HEADER,
    Fill,
    accept,
    build,
    deflated,
    directory,
    entry,
    nested,
    pdf,
    private_temporary_directory,
    refusal,
    spy_on_inflation,
    unicode_path,
    zw,
)

#: A policy low enough to cross its bounds with real bytes.
LOW = SetPolicy(member_bytes=2 * MiB, total_bytes=3 * MiB)

RATIO = "comparison_zip_compression_ratio"
MEMBER_SIZE = "comparison_zip_member_size"
TOTAL_SIZE = "comparison_zip_total_size"
NAME = "comparison_zip_member_name"
ENTRIES = "comparison_zip_entry_count"
UNREADABLE = "comparison_zip_unreadable"


# ---------------------------------------------------------------------------------------
# A bomb by ratio
# ---------------------------------------------------------------------------------------


def test_a_member_compressed_a_thousand_to_one_is_refused_by_ratio() -> None:
    bomb = build(deflated("a.pdf", Fill(8 * MiB, 0, PDF_HEADER)))
    assert len(bomb) < 64 * 1024, "the fixture is not a bomb: 8 MiB should fit in a few KiB"
    assert refusal(bomb) == RATIO


def test_a_member_compressing_sixty_to_one_is_not_a_bomb() -> None:
    """The bound is a ratio of 100: a member of 2 MiB that deflates to 35 KiB is let through, so
    the refusal above is for the ratio and not for any deflated member."""
    block = random.Random(1).randbytes(20_000)
    payload = PDF_HEADER + block * 104
    archive = build(deflated("a.pdf", payload))
    assert 30 < len(payload) / len(z.raw_deflate(payload)) < 99
    with accept(archive) as found:
        assert found.members[0].size == len(payload)


def test_the_ratio_is_judged_on_the_bytes_the_stream_used_not_on_what_the_header_claims() -> None:
    """The disguise the declared ratio cannot see: eight MiB of zeros deflate to a few KiB, and
    a megabyte of padding behind the stream makes the header claim eight to one."""
    zeros = PDF_HEADER + bytes(8 * MiB - len(PDF_HEADER))
    padded = z.raw_deflate(zeros) + bytes(range(256)) * 4096
    archive = z.with_method(
        build(entry("a.pdf", padded, declared_size=len(zeros), crc=zlib.crc32(zeros))),
        zw.DEFLATED,
    )
    assert len(archive) > MiB  # the header's own ratio is about eight: only the stream shows
    assert refusal(archive) == RATIO


def test_a_bomb_inside_a_nested_archive_is_refused_by_the_same_rule() -> None:
    archive = build(nested("inner.zip", deflated("a.pdf", Fill(8 * MiB, 0, PDF_HEADER))))
    assert refusal(archive) == RATIO


# ---------------------------------------------------------------------------------------
# A bomb by absolute size
# ---------------------------------------------------------------------------------------


def test_the_production_bounds_are_the_ruled_figures() -> None:
    assert SET_TOTAL_BYTES == 2 * 1024 * MiB, "ADR-0025 decision 12: 2 GiB in all"
    assert SET_MEMBER_BYTES == 250 * MiB, "the existing envelope's PDF bound"
    assert SET_MAX_ENTRIES == 1000
    assert DEFAULT_SET_POLICY == SetPolicy(
        entries=1000, total_bytes=2 * 1024 * MiB, member_bytes=250 * MiB, ratio=100,
        directory_bytes=4 * MiB, nesting_levels=1,
    )


def test_a_member_declared_over_the_production_member_bound_is_refused_without_unpacking_it() -> None:
    declared_over = build(entry("a.pdf", PDF_HEADER, declared_size=250 * MiB + 1))
    assert refusal(declared_over) == MEMBER_SIZE


def test_members_declared_over_two_gib_together_are_refused_at_the_production_figure() -> None:
    """Eleven members of 200 MiB each, every one inside the member bound, none holding more than
    nine bytes: the headers alone put the total at 2.15 GiB. No gigabyte is written for it."""
    eleven = build(
        *[entry(f"s{i}.pdf", PDF_HEADER, declared_size=200 * MiB) for i in range(11)]
    )
    assert refusal(eleven) == TOTAL_SIZE


def test_the_total_bound_is_inclusive_to_the_byte() -> None:
    """Exactly 2 GiB declared passes the total rule (and then meets the ratio rule, because the
    headers lie about nine bytes); one byte more is the total rule's."""
    sizes = [250 * MiB] * 8 + [48 * MiB]
    assert sum(sizes) == SET_TOTAL_BYTES
    at = build(*[entry(f"s{i}.pdf", PDF_HEADER, declared_size=s) for i, s in enumerate(sizes)])
    assert refusal(at) == RATIO
    sizes[-1] += 1
    over = build(*[entry(f"s{i}.pdf", PDF_HEADER, declared_size=s) for i, s in enumerate(sizes)])
    assert refusal(over) == TOTAL_SIZE


def test_a_member_one_byte_over_the_member_bound_is_refused_and_one_at_it_is_not() -> None:
    over = build(entry("a.pdf", Fill(2 * MiB + 1, 0, PDF_HEADER)))
    assert refusal(over, policy=LOW) == MEMBER_SIZE
    at = build(entry("a.pdf", Fill(2 * MiB, 0, PDF_HEADER)))
    with accept(at, policy=LOW) as found:
        assert found.members[0].size == 2 * MiB


def test_members_inside_the_member_bound_that_pass_the_total_are_refused() -> None:
    together = build(
        entry("a.pdf", Fill(2 * MiB, 0, PDF_HEADER)), entry("b.pdf", Fill(MiB + 1, 0, PDF_HEADER))
    )
    assert refusal(together, policy=LOW) == TOTAL_SIZE
    inside = build(
        entry("a.pdf", Fill(2 * MiB, 0, PDF_HEADER)), entry("b.pdf", Fill(MiB, 0, PDF_HEADER))
    )
    with accept(inside, policy=LOW) as found:
        assert found.bytes_seen == 3 * MiB


@pytest.mark.parametrize("method", ["stored", "deflated"])
def test_a_header_that_declares_less_than_the_member_holds_is_refused_as_soon_as_it_is_passed(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """The disguise of a zip bomb: 1 000 bytes declared, 32 MiB inside. The count of what comes
    out is the only check a lying header cannot get past, and it is held to the declaration, so
    the refusal comes a piece after the declared size and not after 32 MiB."""
    produced = spy_on_inflation(monkeypatch)
    body = Fill(32 * MiB, 0, PDF_HEADER)
    member = (
        entry("a.pdf", body, declared_size=1000)
        if method == "stored"
        else deflated("a.pdf", body, declared_size=1000)
    )
    assert refusal(build(member)) == MEMBER_SIZE
    assert produced[0] <= 1000 + 64 * 1024, f"{produced[0]} bytes came out before the refusal"


def test_a_header_that_declares_more_than_the_member_holds_is_refused() -> None:
    lie = build(entry("a.pdf", Fill(4000, 0, PDF_HEADER), declared_size=5000))
    assert refusal(lie) == UNREADABLE


# ---------------------------------------------------------------------------------------
# Path traversal and absolute names
# ---------------------------------------------------------------------------------------

TRAVERSAL = [
    b"../evil.pdf",
    b"a/../../evil.pdf",
    b"a/b/../../../evil.pdf",
    b"a/..",
    b"../",
    b"stage/../../outside.pdf",
]
ABSOLUTE = [
    b"/evil.pdf",
    b"/etc/cron.d/evil.pdf",
    b"C:\\evil.pdf",
    b"c:evil.pdf",
    b"Z:/evil.pdf",
    b"\\\\server\\share\\evil.pdf",
    b"a\\b.pdf",
    b"a/b\\c.pdf",
]


@pytest.mark.parametrize("name", TRAVERSAL, ids=[n.decode() for n in TRAVERSAL])
def test_a_traversal_name_is_refused(name: bytes) -> None:
    assert refusal(build(pdf("ok.pdf"), pdf(name))) == NAME


@pytest.mark.parametrize("name", ABSOLUTE, ids=[n.decode() for n in ABSOLUTE])
def test_an_absolute_drive_letter_or_backslash_name_is_refused(name: bytes) -> None:
    assert refusal(build(pdf("ok.pdf"), pdf(name))) == NAME


def test_a_traversal_in_a_directory_entry_is_refused_too() -> None:
    assert refusal(build(pdf("ok.pdf"), directory(b"../d/"))) == NAME


def test_a_traversal_inside_a_nested_archive_is_refused() -> None:
    assert refusal(build(nested("inner.zip", pdf("../evil.pdf")))) == NAME


def test_a_name_that_only_the_unicode_path_field_makes_hostile_is_refused() -> None:
    """The header name is harmless; the Info-ZIP Unicode Path field -- which many readers show
    instead -- says ``../../evil.pdf``. A hint that is a traversal is refused all the same."""
    extra = unicode_path(b"ok.pdf", "../../evil.pdf")
    hostile = entry("ok.pdf", PDF_HEADER, local_extra=extra, central_extra=extra)
    assert refusal(build(hostile)) == NAME
    absolute = unicode_path(b"ok.pdf", "/etc/evil.pdf")
    assert refusal(
        build(entry("ok.pdf", PDF_HEADER, local_extra=absolute, central_extra=absolute))
    ) == NAME


def test_a_benign_unicode_path_is_shown_and_accepted() -> None:
    extra = unicode_path(b"ok.pdf", "Раздел 1/чертёж.pdf")
    archive = build(entry("ok.pdf", PDF_HEADER, local_extra=extra, central_extra=extra))
    with accept(archive) as found:
        assert found.members[0].display_name == "Раздел 1/чертёж.pdf"


# ---------------------------------------------------------------------------------------
# Symbolic links, encryption, methods
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["link.pdf", "stage/link.pdf", "link.zip", "folder/"])
def test_a_symbolic_link_member_is_refused(name: str) -> None:
    link = entry(name, b"/etc/passwd", external_attr=zw.SYMLINK)
    assert refusal(build(pdf("ok.pdf"), link)) == "comparison_zip_symlink"


def test_a_member_made_by_another_system_is_not_taken_for_a_link() -> None:
    """The mode bits mean something only when a Unix system made the entry: the same attribute on
    an entry made by MS-DOS is an attribute word, not a link."""
    other = entry("a.pdf", PDF_HEADER, external_attr=zw.SYMLINK, create_system=0)
    with accept(build(other)) as found:
        assert len(found.members) == 1


@pytest.mark.parametrize(
    ("flags", "method"),
    [
        (zw.FLAG_ENCRYPTED, 0),
        (zw.FLAG_ENCRYPTED | 0x40, 0),
        (0x40, 0),
        (zw.FLAG_ENCRYPTED, 99),
        (zw.FLAG_ENCRYPTED, 8),
    ],
    ids=["traditional", "strong", "strong-flag-alone", "winzip-aes", "traditional-deflated"],
)
def test_an_encrypted_member_is_refused(flags: int, method: int) -> None:
    """The encryption rule comes before the method rule: an AES member (method 99) is
    *encrypted*, which is what its user needs to hear."""
    encrypted = entry("secret.pdf", b"\x01" * 40, flags=flags, method=method)
    assert refusal(build(pdf("ok.pdf"), encrypted)) == "comparison_zip_encrypted_member"


def test_an_encrypted_member_of_a_nested_archive_is_refused() -> None:
    inner = entry("secret.pdf", b"\x01" * 40, flags=zw.FLAG_ENCRYPTED)
    assert refusal(build(nested("inner.zip", inner))) == "comparison_zip_encrypted_member"


@pytest.mark.parametrize("method", [1, 6, 9, 12, 14, 93, 99])
def test_a_method_other_than_stored_or_deflate_is_refused(method: int) -> None:
    odd = entry("a.pdf", PDF_HEADER, method=method)
    assert refusal(build(odd)) == "comparison_zip_compression_method"


# ---------------------------------------------------------------------------------------
# Names that repeat
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("a.pdf", "a.pdf"),
        ("a.pdf", "A.PDF"),
        ("Stage/Plan.pdf", "stage/plan.PDF"),
        ("\u00e9.pdf", "e\u0301.pdf"),                       # é precomposed and decomposed
        ("\u0422\u0430\u0439\u0433\u0430.pdf", "\u0422\u0430\u0438\u0306\u0433\u0430.pdf"),  # й
        ("straße.pdf", "STRASSE.pdf"),                        # a case fold that changes length
    ],
    ids=["exact", "case", "folder-and-case", "nfc-latin", "nfc-cyrillic", "casefold-sharp-s"],
)
def test_a_name_that_repeats_is_refused_also_after_case_folding_and_nfc(
    first: str, second: str
) -> None:
    assert refusal(build(pdf(first), pdf(second))) == "comparison_zip_duplicate_member"


def test_a_name_that_repeats_inside_a_nested_archive_is_refused() -> None:
    inner = nested("inner.zip", pdf("a.pdf"), pdf("A.pdf"))
    assert refusal(build(inner)) == "comparison_zip_duplicate_member"


def test_two_members_that_share_only_their_base_name_are_two_members() -> None:
    """A name is not an identity: ``A/plan.pdf`` and ``B/plan.pdf``, and the same name inside a
    nested archive, are different members with different places in the set."""
    archive = build(
        pdf("A/plan.pdf", b"1"), pdf("B/plan.pdf", b"2"), nested("C.zip", pdf("plan.pdf", b"3"))
    )
    with accept(archive) as found:
        assert [m.base_name for m in found.members] == ["plan.pdf"] * 3
        assert len({m.sha256 for m in found.members}) == 3
        assert [m.ordinal for m in found.members] == [0, 1, 2]


def test_two_entries_that_share_one_local_header_are_refused() -> None:
    """The overlap a quine bomb is made of: the second entry's directory record points at the
    first entry's data. Different names make the local header name the wrong member."""
    overlapped = z.with_shared_local_header(build(pdf("a.pdf"), pdf("b.pdf")))
    assert refusal(overlapped) == UNREADABLE
    same_name = z.with_shared_local_header(build(pdf("a.pdf"), pdf("a.pdf")))
    assert refusal(same_name) == "comparison_zip_duplicate_member"


# ---------------------------------------------------------------------------------------
# Nesting
# ---------------------------------------------------------------------------------------


def test_an_archive_inside_an_archive_is_accepted_and_its_pdfs_are_numbered_in_place() -> None:
    archive = build(pdf("a.pdf", b"a"), nested("stage.zip", pdf("x.pdf", b"x"), pdf("y.pdf", b"y")),
                    pdf("b.pdf", b"b"))
    with accept(archive) as found:
        assert z.listing(found) == [
            (0, 0, "a.pdf", len(PDF_HEADER) + 1),
            (1, 1, "stage/x.pdf", len(PDF_HEADER) + 1),
            (2, 1, "stage/y.pdf", len(PDF_HEADER) + 1),
            (3, 0, "b.pdf", len(PDF_HEADER) + 1),
        ]


def test_an_archive_inside_an_archive_inside_an_archive_is_refused() -> None:
    deep = build(nested("one.zip", nested("two.zip", pdf("a.pdf"))))
    assert refusal(deep) == "comparison_zip_nested_depth"


def test_a_chain_of_archives_is_stopped_at_the_second_level_and_never_unpacked_further(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forty-two levels would be forty-two unpackings: the third is never started."""
    from auditmanager.ingest.comparison_zip import reader

    opened: list[int] = []
    original = reader.extract_bundle

    def counting(handle, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(1)
        return original(handle, **kwargs)

    monkeypatch.setattr(reader, "extract_bundle", counting)
    archive = pdf("a.pdf")
    chain = build(archive)
    for level in range(6):
        chain = build(entry(f"level{level}.zip", chain))
    assert refusal(chain) == "comparison_zip_nested_depth"
    assert len(opened) == 2


def test_a_policy_that_allows_no_nesting_refuses_the_first() -> None:
    archive = build(pdf("a.pdf"), nested("stage.zip", pdf("x.pdf")))
    assert refusal(archive, policy=SetPolicy(nesting_levels=0)) == "comparison_zip_nested_depth"


def test_a_policy_cannot_allow_more_than_one_level() -> None:
    with pytest.raises(ValueError, match="at most one level"):
        SetPolicy(nesting_levels=2)


def test_a_zip_that_is_not_one_is_refused_as_unreadable_and_a_zip_named_pdf_is_never_opened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert refusal(build(entry("fake.zip", b"PK this is not an archive"))) == UNREADABLE
    # A ZIP named ``.pdf`` is a PDF member, never expanded: with no envelope it is carried as the
    # bytes it is, and the real envelope (``test_member_envelope.py``) refuses it for its header.
    hidden = build(entry("trick.pdf", build(pdf("inside.pdf"))))
    with accept(hidden) as found:
        assert [m.display_name for m in found.members] == ["trick.pdf"]


# ---------------------------------------------------------------------------------------
# Members that are not PDFs
# ---------------------------------------------------------------------------------------

NOT_PDF = [
    "notes.txt", "plan.docx", "setup.exe", "no_extension", "a.pdf.exe", "a.exe.pdf.txt",
    ".DS_Store", "Thumbs.db", "pack.7z", "pack.rar", "pack.tar.gz", "pack.gz", "image.png",
    "drawing.dwg", "x.pdf ", "x.pdf.", "xpdf",
]


@pytest.mark.parametrize("name", NOT_PDF)
def test_a_member_that_is_not_a_pdf_is_refused(name: str) -> None:
    assert refusal(build(pdf("ok.pdf"), entry(name, b"data"))) == "comparison_zip_member_kind"


def test_macos_resource_forks_are_refused_not_skipped() -> None:
    """``__MACOSX/._a.pdf`` is named like a PDF and is not one; a ``__MACOSX/`` folder entry is
    no folder of the user's. Both are refused, as the portal bundle refuses them."""
    fork = build(pdf("a.pdf"), entry("__MACOSX/._a.pdf", b"\x00\x05\x16\x07"))
    assert refusal(fork) == "comparison_zip_member_kind"
    assert refusal(build(pdf("a.pdf"), directory("__MACOSX/"))) == "comparison_zip_member_kind"


def test_a_directory_entry_that_holds_bytes_is_refused() -> None:
    assert refusal(build(pdf("a.pdf"), entry("folder/", b"data"))) == "comparison_zip_member_kind"


def test_directory_entries_are_structure_and_the_suffix_is_case_blind() -> None:
    archive = build(
        directory("Stage/"), directory("Stage/Sub/"), pdf("Stage/A.PDF", b"1"),
        pdf("Stage/Sub/b.Pdf", b"2"), nested("Stage/c.ZIP", pdf("d.pdf", b"3")),
    )
    with accept(archive) as found:
        assert [m.display_name for m in found.members] == [
            "Stage/A.PDF", "Stage/Sub/b.Pdf", "Stage/c/d.pdf"
        ]
        assert found.entries_seen == 5 + 1


def test_an_archive_that_holds_no_pdf_is_refused() -> None:
    assert refusal(build()) == "comparison_zip_empty"
    assert refusal(build(directory("a/"), directory("a/b/"))) == "comparison_zip_empty"
    assert refusal(build(nested("empty.zip"))) == "comparison_zip_empty"


@pytest.mark.parametrize(
    "garbage",
    [b"", b"%PDF-1.7\n%%EOF", b"PK\x03\x04" + b"\x00" * 10, b"PK\x05\x06" + b"\xff" * 18, b"Rar!\x1a\x07"],
    ids=["empty", "a-pdf", "truncated-local-header", "bad-end-record", "rar"],
)
def test_bytes_that_are_not_a_zip_are_refused_as_unreadable(garbage: bytes) -> None:
    assert refusal(garbage) == UNREADABLE


def test_a_truncated_archive_is_refused_as_unreadable() -> None:
    whole = build(pdf("a.pdf"), pdf("b.pdf"))
    assert refusal(whole[: len(whole) // 2]) == UNREADABLE


# ---------------------------------------------------------------------------------------
# Too many entries; a directory too large to read
# ---------------------------------------------------------------------------------------


def test_one_entry_over_the_production_limit_is_refused_and_the_limit_itself_is_not() -> None:
    over = build(*[pdf(f"d{i:04d}.pdf", b"x") for i in range(SET_MAX_ENTRIES + 1)])
    assert refusal(over) == ENTRIES
    at = build(*[pdf(f"d{i:04d}.pdf", b"x") for i in range(SET_MAX_ENTRIES)])
    with accept(at) as found:
        assert len(found.members) == SET_MAX_ENTRIES


def test_directory_entries_count_against_the_limit() -> None:
    policy = SetPolicy(entries=4)
    assert refusal(build(directory("a/"), directory("b/"), directory("c/"), pdf("a/x.pdf"),
                         pdf("b/y.pdf")), policy=policy) == ENTRIES
    with accept(build(directory("a/"), directory("b/"), pdf("a/x.pdf"), pdf("b/y.pdf")),
                policy=policy) as found:
        assert found.entries_seen == 4


def test_the_limit_is_over_every_level_together() -> None:
    """Three entries in the archive (two PDFs and a ZIP), three in the ZIP: six in all."""
    archive = build(pdf("a.pdf", b"a"), pdf("b.pdf", b"b"),
                    nested("n.zip", pdf("x.pdf", b"x"), pdf("y.pdf", b"y"), pdf("w.pdf", b"w")))
    assert refusal(archive, policy=SetPolicy(entries=5)) == ENTRIES
    with accept(archive, policy=SetPolicy(entries=6)) as found:
        assert found.entries_seen == 6


def test_the_total_is_over_every_level_together_and_counts_the_container() -> None:
    """The nested archive's own bytes are unpacked to disk before they are read, so they come out
    of the budget, and so do the bytes of what is inside it. A megabyte of PDF in a ZIP, beside
    a megabyte of PDF, cannot be read in three MiB."""
    inner = nested("n.zip", entry("x.pdf", Fill(MiB + 200_000, 0, PDF_HEADER)))
    archive = build(entry("a.pdf", Fill(MiB, 0, PDF_HEADER)), inner)
    policy = SetPolicy(member_bytes=2 * MiB, total_bytes=3 * MiB)
    assert refusal(archive, policy=policy) == TOTAL_SIZE
    roomy = SetPolicy(member_bytes=2 * MiB, total_bytes=4 * MiB)
    with accept(archive, policy=roomy) as found:
        assert found.bytes_seen >= 2 * MiB + 2 * 200_000


def test_an_end_record_that_claims_more_entries_than_the_limit_is_refused_before_the_directory() -> None:
    lying = z.with_entry_count(build(pdf("a.pdf")), 5000)
    assert refusal(lying) == ENTRIES


def test_a_central_directory_over_the_policy_bound_is_refused_before_it_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three entries with a 2 000-byte comment each: a directory of six kilobytes. The bound on
    the entry count alone would let a thousand such entries make the reader load two megabytes;
    the policy's directory bound refuses it by its size, without loading it."""
    from auditmanager.ingest import bundle_archive

    loaded: list[int] = []
    original = bundle_archive._Archive.load_entries

    def spy(self):  # type: ignore[no-untyped-def]
        loaded.append(1)
        return original(self)

    monkeypatch.setattr(bundle_archive._Archive, "load_entries", spy)
    commented = build(*[entry(f"d{i}.pdf", PDF_HEADER, comment=b"c" * 2000) for i in range(3)])
    assert refusal(commented, policy=SetPolicy(directory_bytes=4096)) == UNREADABLE
    assert not loaded, "the directory was loaded before its size was judged"
    with accept(commented, policy=SetPolicy(directory_bytes=8192)) as found:
        assert len(found.members) == 3
    assert loaded


# ---------------------------------------------------------------------------------------
# Everything above, together: a refusal is one of the registered reasons, and the portal's own
# names never leak through the set policy.
# ---------------------------------------------------------------------------------------


def test_no_portal_constraint_name_ever_leaves_the_set_reader() -> None:
    hostile = [
        build(entry("a.pdf", Fill(8 * MiB, 0, PDF_HEADER), method=8, deflate="zlib")),
        build(pdf("../a.pdf")), build(pdf("a.pdf"), pdf("A.pdf")),
        build(entry("a.pdf", b"x", flags=1)), build(entry("a.pdf", b"x", method=12)),
        build(entry("a.pdf", b"x", external_attr=zw.SYMLINK)), build(entry("a.txt", b"x")),
        b"not a zip at all", build(), z.with_entry_count(build(pdf("a.pdf")), 5000),
        build(*[pdf(f"{i}.pdf") for i in range(SET_MAX_ENTRIES + 1)]),
        build(entry("a.pdf", PDF_HEADER, declared_size=250 * MiB + 1)),
    ]
    seen = {refusal(archive) for archive in hostile}
    assert seen <= set(z.CONSTRAINTS)
    assert not any(constraint.startswith("bundle_") for constraint in seen)
    assert len(seen) == 11, sorted(seen)


def test_the_reader_leaves_the_handle_for_the_caller_to_close() -> None:
    handle = io.BytesIO(build(pdf("a.pdf")))
    with extract_pdf_set(handle, envelope=None) as found:
        assert len(found.members) == 1
    assert not handle.closed
