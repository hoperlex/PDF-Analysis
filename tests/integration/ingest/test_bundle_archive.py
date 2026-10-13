"""The portal bundle's archive rules: one refusal test for each, and the ways round them.

`W55B-INGEST-01` (plan section B3.1). Every rule in the plan's list has an archive built to break
it and nothing else (``tools/fixtures/portal_bundle/archive_negatives.py``, 67 small ones and
three size-driven families), and each is judged by the product's own reader
(:mod:`auditmanager.ingest.bundle_archive`) and compared with two things that are not the
product: the constraint the fixture was *built* for, and the answer of the fixtures' own
reference validator, which shares no code with ``src/``. A negative that is refused for the
wrong reason proves nothing about its rule, so every comparison is on the constraint, not on
"refused".

What else is here, and why:

* the **declared and the actual size** are separate rules. A header that lies small must be
  caught by counting the bytes that come out (the zip-bomb disguise), and one that lies large
  must be refused on its word; each is shown at lowered bounds, and once at the production
  bound with the real constants;
* **names**: the four encodings decode to one display name, and the ruled order (flag 11, then
  ``0x7075``, then strict UTF-8, then cp866) is shown by inputs only that order can name;
* **ZIP64, data descriptors and real deflate** are accepted, and the members they yield equal
  what the standard library reads from the same archive;
* **nothing is kept that should not be**: the HTML is hashed and dropped; a refused archive
  leaves no temporary directory; the temporary directory of an accepted one is gone on close;
* **memory**: a bundle with a large member is taken apart without holding the member.

The module needs no database, no object store and no container, and says so by overriding the
two autouse fixtures this directory's ``conftest.py`` would otherwise start.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
import tempfile
import tracemalloc
import zipfile
import zlib
from pathlib import Path

import pytest

from auditmanager.ingest import bundle_archive as ba
from auditmanager.ingest.bundle_archive import (
    BundleLimits,
    decode_display_name,
    extract_bundle,
    looks_like_zip,
)
from auditmanager.ingest.bundle_envelope import admit_bundle
from auditmanager.shared.errors import DomainError, screen_message
from portal_bundle import archive_negatives as an  # tools/fixtures, on the path via conftest
from portal_bundle import positives, validate, zipwrite
from portal_bundle import portal_format as fmt
from portal_bundle.zipwrite import Member
from tests.integration.ingest.bundle_support import committed, judge, refusal_of

MiB = 1024 * 1024
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The bounds a test lowers so that a rule is crossed without writing hundreds of MiB. The
#: production figures are asserted on their own (``test_the_production_bounds_are_the_ruled_ones``).
LOW = BundleLimits(
    member_bytes=2 * MiB,
    text_member_bytes=MiB,
    stamp_audit_bytes=64 * 1024,
    total_bytes=3 * MiB,
)


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


#: The reference validator at the production bounds: the oracle each answer is compared with.
REFERENCE = validate.Limits(member_bytes=ba.MEMBER_BYTES, stamp_audit_bytes=ba.STAMP_AUDIT_BYTES)

#: The registered values of ``validation_failed``'s bundle classifier. Written out here, and
#: shown to be the contract's (``test_every_registered_bundle_constraint_has_a_test``).
REGISTERED_BUNDLE_CONSTRAINTS = frozenset({
    "portal_bundle_required", "bundle_unreadable", "bundle_entry_count",
    "bundle_directory_entry", "bundle_member_name", "bundle_symlink",
    "bundle_encrypted_member", "bundle_compression_method", "bundle_duplicate_member",
    "bundle_stem_mismatch", "bundle_member_set", "bundle_member_size", "bundle_total_size",
    "bundle_compression_ratio", "blocks_json_invalid", "blocks_page_count",
    "results_blocks_mismatch", "stamp_audit_invalid",
})

NEGATIVES = an.small_negatives()


# ---------------------------------------------------------------------------------------
# One refusal test per rule: the small archives
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("negative", NEGATIVES, ids=[n.name for n in NEGATIVES])
def test_each_small_negative_is_refused_for_exactly_the_rule_it_was_built_to_break(
    negative: an.Negative,
) -> None:
    field, constraint, admission = judge(negative.build())
    assert admission is None, f"{negative.name} was accepted"
    assert (field, constraint) == ("file", negative.constraint), (
        f"{negative.name} was built to break {negative.constraint}, the product says "
        f"{constraint} under {field}"
    )


@pytest.mark.parametrize("negative", NEGATIVES, ids=[n.name for n in NEGATIVES])
def test_the_product_and_the_reference_validator_refuse_for_the_same_rule(
    negative: an.Negative,
) -> None:
    """The validator under ``tools/fixtures`` is a second implementation of the same rules."""
    data = negative.build()
    reference = validate.validate(data, REFERENCE)
    _field, constraint, _admission = judge(data)
    assert reference.constraints, f"the reference accepted {negative.name}"
    assert constraint == reference.constraints[0], (
        f"{negative.name}: product {constraint}, reference {reference.constraints}"
    )


def test_every_registered_bundle_constraint_has_a_test() -> None:
    """The 18 values of the contract, each answered by at least one archive in this file."""
    notes = json.loads(
        (REPOSITORY_ROOT / "contracts" / "domain" / "v1" / "error-codes.json").read_text(
            encoding="utf-8"
        )
    )["codes"]["validation_failed"]["notes"]
    registered_text = " ".join(notes)
    for constraint in REGISTERED_BUNDLE_CONSTRAINTS:
        assert constraint in registered_text, f"{constraint} is not in the contract's notes"

    answered = {n.constraint for n in NEGATIVES} | set(an.SIZE_DRIVEN)
    assert answered == REGISTERED_BUNDLE_CONSTRAINTS, (
        f"no archive for {sorted(REGISTERED_BUNDLE_CONSTRAINTS - answered)}; "
        f"an archive for an unregistered value: {sorted(answered - REGISTERED_BUNDLE_CONSTRAINTS)}"
    )


# ---------------------------------------------------------------------------------------
# One refusal test per rule: the size rules, declared and actual
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("compress", ["stored", "deflate"])
def test_a_member_one_byte_over_the_bound_is_refused_whether_stored_or_deflated(
    tmp_path: Path, compress: str
) -> None:
    path = an.member_size(tmp_path / "m.zip", member_bytes=LOW.member_bytes, compress=compress)
    assert judge(path, LOW)[:2] == ("file", "bundle_member_size")


def test_a_member_exactly_at_the_bound_passes_the_size_rules(tmp_path: Path) -> None:
    """The boundary is inclusive: the bound itself is a size the product accepts, so the
    refusal above is for the *byte over* and not for a bound that was off by one. The PDF
    member is a header and zeros, so the archive then fails the content rules -- but not a
    size rule."""
    path = an.member_size(tmp_path / "at.zip", member_bytes=LOW.member_bytes - 1, compress="stored")
    field, constraint, _ = judge(path, LOW)
    assert constraint == "parseable_pdf", (field, constraint)


def test_two_members_inside_the_member_bound_that_pass_the_total_are_refused(
    tmp_path: Path,
) -> None:
    path = an.total_size(
        tmp_path / "t.zip", member_bytes=LOW.member_bytes, total_bytes=LOW.total_bytes
    )
    assert judge(path, LOW)[:2] == ("file", "bundle_total_size")


def test_a_ratio_above_the_bound_is_refused(tmp_path: Path) -> None:
    path = an.compression_ratio(tmp_path / "r.zip", size=MiB)
    assert judge(path, LOW)[:2] == ("file", "bundle_compression_ratio")


def test_the_archive_as_a_whole_is_held_to_the_ratio_too() -> None:
    """The declared members together against the archive's own size.

    No real archive can reach this alone (the archive is at least as large as its members'
    compressed bytes, so every member inside the ratio puts the total inside it), which is why
    the rule is shown on entries built for it: two members each exactly at 100 : 1, in an
    archive smaller than the compressed bytes they claim -- a directory that lies about where
    its data is. A reader that stopped at the per-member ratio would let it through."""
    entry = lambda index: ba._Entry(  # noqa: E731
        index, f"m{index}".encode(), 0, 8, 0, 10, 1000, 0, 3, 0, b""
    )
    chosen = {"pdf": entry(0), "blocks": entry(1)}
    assert all(not ba._ratio_exceeded(e.size, e.compressed_size, ba.MAX_RATIO) for e in chosen.values())
    with pytest.raises(DomainError) as refused:
        ba._judge_declared(chosen, 19, BundleLimits())
    assert dict(refused.value.detail_fields)["constraint"] == "bundle_compression_ratio"
    ba._judge_declared(chosen, 20, BundleLimits())          # 2000 against 20: exactly 100 : 1


def test_the_ratio_rule_is_above_the_bound_and_not_at_it() -> None:
    assert ba._ratio_exceeded(100 * 7, 7, ba.MAX_RATIO) is False
    assert ba._ratio_exceeded(100 * 7 + 1, 7, ba.MAX_RATIO) is True
    assert ba._ratio_exceeded(0, 0, ba.MAX_RATIO) is False


def test_a_header_that_declares_less_than_the_member_holds_is_caught_by_counting(
    tmp_path: Path,
) -> None:
    """The zip-bomb disguise: the header says 1000 bytes, the member unpacks to more than the
    bound. Only counting the bytes that come out can refuse it."""
    for compress in ("stored", "deflate"):
        path = an.size_lie_declared_small(
            tmp_path / f"{compress}.zip", actual_bytes=LOW.member_bytes + 4096,
            declared_bytes=1000, compress=compress,
        )
        assert judge(path, LOW)[:2] == ("file", "bundle_member_size"), compress


def test_a_header_that_declares_more_than_the_bound_is_refused_on_its_word(
    tmp_path: Path,
) -> None:
    path = an.size_lie_declared_large(
        tmp_path / "large.zip", actual_bytes=1000, declared_bytes=LOW.member_bytes + 1
    )
    assert judge(path, LOW)[:2] == ("file", "bundle_member_size")


def test_the_production_bound_refuses_a_header_that_declares_one_byte_over_it(
    tmp_path: Path,
) -> None:
    """The same rule at the real constant, cheaply: nothing near 250 MiB is unpacked."""
    path = an.size_lie_declared_large(
        tmp_path / "prod.zip", actual_bytes=1000, declared_bytes=ba.MEMBER_BYTES + 1
    )
    assert judge(path)[:2] == ("file", "bundle_member_size")


def test_the_production_bound_refuses_a_member_that_unpacks_past_it_whatever_the_header_says(
    tmp_path: Path,
) -> None:
    """The header says 1000 bytes, the deflate stream holds 250 MiB and a byte. The real
    constant is crossed by counting (about two seconds, a few hundred KiB of archive), the
    temporary directory is gone afterwards, and the answer is the size rule's."""
    path = an.size_lie_declared_small(
        tmp_path / "bomb.zip", actual_bytes=ba.MEMBER_BYTES + 1, declared_bytes=1000,
        compress="deflate",
    )
    assert path.stat().st_size < 2 * MiB, "the archive is not the small bomb it should be"
    spool = tmp_path / "spool"
    spool.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(tempfile, "tempdir", str(spool))
        assert judge(path)[:2] == ("file", "bundle_member_size")
    assert list(spool.iterdir()) == [], "the refused archive left its temporary files"


@pytest.mark.parametrize("declared", [None, 10], ids=["honest header", "header lies small"])
@pytest.mark.parametrize("suffix", [b"_blocks.json", b"_results.md"])
def test_a_block_list_or_markdown_over_the_memory_bound_is_refused_as_a_member_size(
    tmp_path: Path, suffix: bytes, declared: int | None
) -> None:
    """The two members that are read into memory are held far lower than the PDF, by their
    declared size and by the bytes counted when the header says less."""
    items = an.members()
    target = next(i for i in items if i.name.endswith(suffix))
    target.payload = b"x" * (LOW.text_member_bytes + 1)
    target.declared_size = declared
    path = tmp_path / "text.zip"
    zipwrite.write_zip(path, items)
    assert judge(path, LOW)[:2] == ("file", "bundle_member_size")


def test_the_stamp_audit_cap_holds_declared_and_counted() -> None:
    cap = LOW.stamp_audit_bytes
    assert judge(an.stamp_audit_over_cap(cap), LOW)[:2] == ("file", "stamp_audit_invalid")
    # A header that lies small about a stamp audit larger than its cap.
    items = an.members()
    big = b'{"pad": "' + b"x" * (cap + 10) + b'"}'
    items.append(Member(b"bundle_stamp_audit.json", big, method=8, declared_size=50))
    data = zipwrite.build_zip(items)
    assert judge(data, LOW)[:2] == ("file", "stamp_audit_invalid")
    # One byte under the cap is not refused for its size.
    assert judge(an.stamp_audit_over_cap(cap - 2), LOW)[:2] == (None, None)


# ---------------------------------------------------------------------------------------
# The shape of the directory
# ---------------------------------------------------------------------------------------


def test_eight_entries_pass_the_count_and_nine_do_not() -> None:
    nine = judge(an.entry_count(9))
    assert nine[:2] == ("file", "bundle_entry_count")
    eight = judge(an.entry_count(8))
    assert eight[:2] == ("file", "bundle_member_set"), (
        "eight entries are over no count rule; the three extras are unknown members"
    )


def test_the_count_is_judged_before_the_directory_is_parsed() -> None:
    """An end record that claims nine entries is refused as nine entries even when the
    directory behind it is not nine entries of anything -- the count is read first."""
    data = bytearray(an.entry_count(9))
    end = data.rfind(b"PK\x05\x06")
    data[end + 8 : end + 12] = (200).to_bytes(2, "little") * 2
    assert judge(bytes(data))[:2] == ("file", "bundle_entry_count")


def test_a_directory_larger_than_its_entries_can_be_is_never_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An end record that says one entry and a 200 MiB directory is refused before a read of
    that size is made: the largest read is the tail, a local header and one piece."""
    path = tmp_path / "huge-directory.zip"
    size = 201 * MiB
    end = struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, 1, 1, 200 * MiB, 0, 0)
    with path.open("wb") as out:
        out.write(b"PK\x03\x04")
        out.truncate(size - len(end))
        out.seek(size - len(end))
        out.write(end)
    lengths: list[int] = []
    real = ba._Archive._read

    def spy(self: object, offset: int, length: int) -> bytes:
        lengths.append(length)
        return real(self, offset, length)  # type: ignore[arg-type]

    monkeypatch.setattr(ba._Archive, "_read", spy)
    assert judge(path)[:2] == ("file", "bundle_unreadable")
    assert lengths and max(lengths) <= MiB, f"a read of {max(lengths)} bytes was made"


def test_the_magic_is_a_zip_local_header_an_empty_archive_or_a_spanning_marker() -> None:
    assert ba.ZIP_MAGICS == (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    for head, expected in [
        (b"PK\x03\x04rest", True), (b"PK\x05\x06rest", True), (b"PK\x07\x08rest", True),
        (b"%PDF-1.7", False), (b"", False), (b"PK\x03", False), (b"7z\xbc\xaf", False),
    ]:
        handle = io.BytesIO(head)
        assert looks_like_zip(handle) is expected, head
        assert handle.tell() == 0, "the sniff must leave the handle at its start"


# ---------------------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------------------

#: A member name in each of the encodings the display rule decodes.
STEM = "Проект_АР"


@pytest.mark.parametrize("encoding", ["utf8_flag", "infozip_unicode", "utf8_plain", "cp866"])
def test_the_four_name_encodings_decode_to_one_display_name(encoding: str) -> None:
    data = positives.name_encoding(encoding)
    with extract_bundle(io.BytesIO(data)) as bundle:
        assert bundle.members["pdf"].display_name == f"{STEM}.pdf"
        assert bundle.members["blocks"].display_name == f"{STEM}_blocks.json"


def test_the_display_name_is_decoded_in_the_ruled_order() -> None:
    """Each input is one only the named step can name: the steps are told apart because the
    later ones would give a different answer."""
    unicode_path = lambda raw, shown, *, crc=None: struct.pack(  # noqa: E731
        "<HHBI", 0x7075, 5 + len(shown), 1, zlib.crc32(raw) if crc is None else crc
    ) + shown

    # Flag 11 beats a Unicode Path field that names something else.
    raw = "П.pdf".encode("utf-8")
    assert decode_display_name(raw, 0x0800, unicode_path(raw, b"Z.pdf")) == "П.pdf"

    # The field beats strict UTF-8 and cp866 when the header name is not UTF-8 at all.
    raw = b"abc\xff.pdf"
    assert decode_display_name(raw, 0, unicode_path(raw, b"xyz.pdf")) == "xyz.pdf"
    # ... but not when its CRC no longer matches the name it was written for,
    assert decode_display_name(raw, 0, unicode_path(raw, b"xyz.pdf", crc=1)) == raw.decode("cp866")
    # ... and not when its version is not 1.
    stale = unicode_path(raw, b"xyz.pdf").replace(b"\x01" + struct.pack("<I", zlib.crc32(raw)),
                                                 b"\x02" + struct.pack("<I", zlib.crc32(raw)))
    assert decode_display_name(raw, 0, stale) == raw.decode("cp866")

    # Strict UTF-8 comes before cp866.
    raw = "Проект.pdf".encode("utf-8")
    assert decode_display_name(raw, 0, b"") == "Проект.pdf"
    # And cp866 is the last resort: these bytes are not UTF-8.
    raw = "Проект.pdf".encode("cp866")
    assert decode_display_name(raw, 0, b"") == "Проект.pdf"
    # A name flagged UTF-8 that is not UTF-8 is shown with replacement characters, not refused.
    assert "�" in decode_display_name(b"\xff.pdf", 0x0800, b"")


# ---------------------------------------------------------------------------------------
# Valid archives that look unusual, and the independent reader
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(positives.POSITIVES))
def test_a_valid_bundle_in_any_of_these_shapes_is_accepted_and_reads_as_the_standard_library_does(
    name: str,
) -> None:
    """ZIP64 fields, data descriptors, real deflate, every optional member, a polygon block and
    the four name encodings: accepted, and each stored member's bytes are those the standard
    library reads from the same archive under the same role."""
    data = positives.POSITIVES[name]()
    assert judge(data)[:2] == (None, None), name
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        independent = {
            fmt.role_of(info.filename.encode("utf-8")): archive.read(info)
            for info in archive.infolist()
        }
    with extract_bundle(io.BytesIO(data)) as bundle:
        assert set(bundle.members) == set(independent), name
        for role, member in bundle.members.items():
            assert member.size == len(independent[role]), (name, role)
            assert member.sha256 == hashlib.sha256(independent[role]).hexdigest(), (name, role)
            if member.path is not None:
                assert member.path.read_bytes() == independent[role], (name, role)


def test_the_html_is_hashed_and_dropped_and_the_directory_holds_the_other_four() -> None:
    data = committed("ar_baseline.zip")
    with extract_bundle(io.BytesIO(data)) as bundle:
        html = bundle.members["results_html"]
        assert html.path is None, "the HTML rendering was kept"
        assert html.sha256 == hashlib.sha256(
            zipfile.ZipFile(io.BytesIO(data)).read("ar_baseline_results.html")
        ).hexdigest()
        directory = next(
            m.path.parent for m in bundle.members.values() if m.path is not None
        )
        assert sorted(p.name for p in directory.iterdir()) == [
            "blocks", "pdf", "results_md", "stamp_audit",
        ], "the temporary directory holds something besides the four stored members"
        # The file for a member is named by its role, never by the archive's name for it.
        assert all(m.path.name == role for role, m in bundle.members.items() if m.path)
    assert not directory.exists(), "closing the bundle left its directory behind"


def test_a_refused_archive_leaves_no_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    for negative in NEGATIVES:
        judge(negative.build())
    assert list(tmp_path.iterdir()) == [], "a refusal left temporary files behind"


def test_extraction_holds_a_large_member_in_a_small_fraction_of_its_size() -> None:
    """A 48 MiB PDF member (stored, incompressible) is written to disk as it is counted. The
    Python-level peak stays under 8 MiB: no ``bytes`` of the member is ever built."""
    base = an.base_files()
    padded = base.pdf + b"%" + bytes(range(256)) * 4 * 1024 * 48
    items = an.members()
    items[0] = Member(b"bundle.pdf", padded, method=0)
    data = zipwrite.build_zip(items)
    handle = io.BytesIO(data)
    tracemalloc.start()
    try:
        with extract_bundle(handle) as bundle:
            _current, peak = tracemalloc.get_traced_memory()
            assert bundle.members["pdf"].size == len(padded)
    finally:
        tracemalloc.stop()
    assert peak < 8 * MiB, f"extracting a {len(padded)}-byte member peaked at {peak} bytes"


# ---------------------------------------------------------------------------------------
# What a refusal says
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("negative", NEGATIVES, ids=[n.name for n in NEGATIVES])
def test_a_refusal_is_a_screened_sentence_that_echoes_nothing_of_the_archive(
    negative: an.Negative,
) -> None:
    data = negative.build()
    with pytest.raises(DomainError) as raised:
        with extract_bundle(io.BytesIO(data)) as bundle:
            admit_bundle(bundle)
    field, constraint, message = refusal_of(raised.value)
    assert field == "file"
    screen_message(message)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = [info.orig_filename for info in archive.infolist()]
    except zipfile.BadZipFile:
        names = []
    for name in names:
        assert len(name) < 4 or name not in message, (negative.name, name, message)


def test_the_bare_pdf_sentence_says_how_to_obtain_the_bundle_in_russian() -> None:
    with pytest.raises(DomainError) as raised:
        with extract_bundle(io.BytesIO(an.bare_pdf())):
            pass
    message = refusal_of(raised.value)[2]
    assert "ZIP" in message and "портал" in message and "PDF" in message
    assert refusal_of(raised.value)[:2] == ("file", "portal_bundle_required")


def test_the_production_bounds_are_the_ruled_ones() -> None:
    from auditmanager.ingest.envelope import MAX_BYTES

    assert ba.MEMBER_BYTES == MAX_BYTES == 250 * MiB
    assert ba.TOTAL_BYTES == 300 * MiB
    assert ba.MAX_RATIO == 100 and ba.MAX_ENTRIES == 8
    assert ba.TEXT_MEMBER_BYTES == 16 * MiB
    assert ba.STAMP_AUDIT_BYTES == 4 * MiB
    # The two bounds FIXTURES left to this lane keep its committed oracle true.
    assert ba.TEXT_MEMBER_BYTES >= 250_000 and ba.STAMP_AUDIT_BYTES >= 4_000
    assert ba.DEFAULT_LIMITS == BundleLimits()
    for name in ("ar_baseline", "ar_baseline_minimal", "ar_baseline_ocr_defects", "pages_31"):
        assert judge(committed(f"{name}.zip"))[:2] == (None, None), name
