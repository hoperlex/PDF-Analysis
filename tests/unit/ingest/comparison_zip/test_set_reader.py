"""What an accepted ZIP set gives its caller, and how its names are kept in their place.

`CMP-INGEST-ZIP-01`. The refusals are in ``test_adversarial_archives.py`` and
``test_member_envelope.py``; this module is the other half of the contract:

* **the reader reads what the standard library reads.** Archives written by ``zipfile`` (stored,
  deflated, ZIP64, with data descriptors, with folders) give members whose bytes, digests and
  names equal ``zipfile``'s, in the archive's order;
* **names are hints, never identity.** A member is its ordinal, its digest and its size. Renaming
  a member changes nothing a caller may rely on, two members with one content have one digest,
  and no name -- not a folder, not a token planted in it, not a traversal the Unicode Path field
  tried to smuggle -- reaches a path: the files are named by key in a directory the reader made;
* **the hint is safe to show**: control, format and separator characters and the Hangul fillers
  are replaced, the length is cut, and the scrub is the portal bundle's own;
* **cleanup**: closing removes every directory (once, or twice), a nested archive's own file is
  gone as soon as it was read, and the directories carry the name the stale-temporaries sweep
  looks for, so a crashed worker's are collected;
* **the table of refusal names is total**: every refusal the shared reader can raise under this
  policy has a name here, and every sentence passes the error envelope's screen.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import random
import re
import zipfile
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import bundle_archive
from auditmanager.ingest.bundle_members import _showable
from auditmanager.ingest.comparison_zip import (
    CONSTRAINTS,
    MAX_HINT,
    SetPolicy,
    extract_pdf_set,
    looks_like_zip,
    refusals,
)
from auditmanager.jobs.temporaries import DIRECTORY_NAME
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from tests.unit.ingest.comparison_zip import zip_builders as z
from tests.unit.ingest.comparison_zip.zip_builders import (  # noqa: F401  (the autouse fixture)
    MiB,
    PDF_HEADER,
    accept,
    build,
    directory,
    entry,
    nested,
    pdf,
    private_temporary_directory,
    unicode_path,
)


class _Unseekable(io.RawIOBase):
    """A write-only stream: ``zipfile`` then writes data descriptors after each member."""

    def __init__(self) -> None:
        self.buffer = io.BytesIO()

    def writable(self) -> bool:
        return True

    def write(self, data: Any) -> int:
        return self.buffer.write(data)


def _by_zipfile(files: dict[str, bytes], *, compression: int, zip64: bool = False,
                descriptors: bool = False) -> bytes:
    stream: Any = _Unseekable() if descriptors else io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        for name, data in files.items():
            if name.endswith("/"):
                archive.writestr(name, b"")
            else:
                with archive.open(name, "w", force_zip64=zip64) as member:
                    member.write(data)
    return (stream.buffer if descriptors else stream).getvalue()


def _text(seed: int, size: int) -> bytes:
    """Compressible, but nowhere near a bomb: about three to one."""
    return bytes(random.Random(seed).choices(b"abcdefgh ", k=size))


FILES = {
    "stage/": b"",
    "stage/A.pdf": PDF_HEADER + _text(1, 30_000),
    "stage/Подпапка/Б.pdf": PDF_HEADER + _text(2, 54_000),
    "stage/empty-ish.PDF": PDF_HEADER,
    "top.pdf": PDF_HEADER + bytes(range(256)) * 40,
}


@pytest.mark.parametrize(
    ("compression", "zip64", "descriptors"),
    [
        (zipfile.ZIP_STORED, False, False),
        (zipfile.ZIP_DEFLATED, False, False),
        (zipfile.ZIP_DEFLATED, True, False),
        (zipfile.ZIP_DEFLATED, False, True),
        (zipfile.ZIP_STORED, True, True),
    ],
    ids=["stored", "deflated", "zip64", "data-descriptors", "stored-zip64-descriptors"],
)
def test_the_members_equal_what_the_standard_library_reads(
    compression: int, zip64: bool, descriptors: bool
) -> None:
    archive = _by_zipfile(FILES, compression=compression, zip64=zip64, descriptors=descriptors)
    expected = [(name, data) for name, data in FILES.items() if not name.endswith("/")]
    with zipfile.ZipFile(io.BytesIO(archive)) as reference:
        assert [info.filename for info in reference.infolist() if not info.is_dir()] == [
            name for name, _ in expected
        ]
    with accept(archive) as found:
        assert [(m.display_name, m.size, m.sha256) for m in found.members] == [
            (name, len(data), hashlib.sha256(data).hexdigest()) for name, data in expected
        ]
        assert [found.open(m).read() for m in found.members] == [data for _, data in expected]
        assert found.entries_seen == len(FILES)


def test_the_same_archive_read_twice_gives_the_same_set() -> None:
    archive = build(pdf("b.pdf", b"2"), directory("d/"), pdf("d/a.pdf", b"1"),
                    nested("n.zip", pdf("c.pdf", b"3")))
    with accept(archive) as first, accept(archive) as second:
        assert z.listing(first) == z.listing(second)
        assert [m.sha256 for m in first.members] == [m.sha256 for m in second.members]
        assert first.entries_seen == second.entries_seen
        assert first.bytes_seen == second.bytes_seen


def test_the_handle_may_be_a_real_file_and_is_not_closed_by_the_reader(tmp_path: Path) -> None:
    path = tmp_path / "stage.zip"
    path.write_bytes(build(pdf("a.pdf"), nested("n.zip", pdf("b.pdf"))))
    with path.open("rb") as handle:
        assert looks_like_zip(handle)
        with extract_pdf_set(handle, envelope=None) as found:
            assert len(found.members) == 2
        assert not handle.closed
        assert handle.read(2) != b""  # still readable, wherever the reader left it


# ---------------------------------------------------------------------------------------
# Names are hints
# ---------------------------------------------------------------------------------------


def test_two_names_for_one_content_are_two_members_with_one_digest() -> None:
    with accept(build(pdf("a.pdf", b"same"), pdf("copy of a.pdf", b"same"))) as found:
        first, second = found.members
        assert (first.ordinal, second.ordinal) == (0, 1)
        assert first.sha256 == second.sha256 and first.size == second.size
        assert first.path != second.path


def test_renaming_a_member_changes_its_hint_and_nothing_else() -> None:
    before = build(pdf("alpha.pdf", b"one"), pdf("beta.pdf", b"two"))
    after = build(pdf("zzz/renamed/one.pdf", b"one"), pdf("beta.pdf", b"two"))
    with accept(before) as old, accept(after) as new:
        assert [(m.ordinal, m.size, m.sha256) for m in old.members] == [
            (m.ordinal, m.size, m.sha256) for m in new.members
        ]
        assert [m.display_name for m in old.members] != [m.display_name for m in new.members]


def test_no_name_reaches_a_path(private_temporary_directory: Path) -> None:
    """Tokens planted in the names -- in the file names, in folders, in a nested archive's name,
    in the Unicode Path field -- appear in no path the reader made, and every file is named by
    its key."""
    extra = unicode_path(b"hidden.pdf", "UNICODETOKEN/x.pdf")
    archive = build(
        pdf("FILETOKEN.pdf", b"1"), pdf("FOLDERTOKEN/inner.pdf", b"2"),
        nested("ZIPTOKEN.zip", pdf("INNERTOKEN.pdf", b"3")),
        entry("hidden.pdf", PDF_HEADER + b"4", local_extra=extra, central_extra=extra),
    )
    with accept(archive) as found:
        paths = [p for p in private_temporary_directory.rglob("*")]
        assert paths, "the reader made no files"
        for path in paths:
            relative = str(path.relative_to(private_temporary_directory))
            assert "TOKEN" not in relative, relative
        files = [p for p in paths if p.is_file()]
        assert all(re.fullmatch(r"pdf_\d{5}", p.name) for p in files), [p.name for p in files]
        assert len(files) == 4 == len(found.members)
        assert any("UNICODETOKEN" in m.display_name for m in found.members)  # ... as a hint only
        assert all(m.path.is_relative_to(private_temporary_directory) for m in found.members)


def test_the_container_of_a_nested_archive_is_gone_once_it_has_been_read(
    private_temporary_directory: Path,
) -> None:
    archive = build(pdf("a.pdf"), nested("n.zip", pdf("b.pdf")), nested("m.zip", pdf("c.pdf")))
    with accept(archive) as found:
        names = sorted(p.name for p in private_temporary_directory.rglob("*") if p.is_file())
        assert len(names) == 3 == len(found.members)
        assert not [n for n in names if n.startswith("zip_")], names


def test_a_set_directory_is_one_the_stale_temporaries_sweep_collects(
    private_temporary_directory: Path,
) -> None:
    with accept(build(pdf("a.pdf"), nested("n.zip", pdf("b.pdf")))):
        directories = [p for p in private_temporary_directory.iterdir()]
        assert len(directories) == 2  # the archive's, and the nested archive's
        assert all(DIRECTORY_NAME.match(p.name) for p in directories), [p.name for p in directories]


def test_closing_removes_the_directories_and_may_be_done_twice(
    private_temporary_directory: Path,
) -> None:
    found = accept(build(pdf("a.pdf"), nested("n.zip", pdf("b.pdf"))))
    assert list(private_temporary_directory.iterdir())
    found.close()
    assert not list(private_temporary_directory.iterdir())
    found.close()


# ---------------------------------------------------------------------------------------
# The hint is safe to show
# ---------------------------------------------------------------------------------------

HOSTILE_CODE_POINTS = [
    "‮", "‭", "⁦", "⁩", "​", "﻿", " ", " ", "\x00",
    "\x07", "\x1b", "\x7f", "\u0085", "ᅟ", "ᅠ", "ㅤ", "ﾠ", "\n", "\t",
]


@pytest.mark.parametrize("char", HOSTILE_CODE_POINTS, ids=[f"U+{ord(c):04X}" for c in HOSTILE_CODE_POINTS])
def test_a_hint_never_carries_a_character_a_screen_or_a_log_would_act_on(char: str) -> None:
    """The scrub is the portal bundle's (``_showable``): a right-to-left override before
    ``fdp.exe`` would show ``exe.pdf``."""
    archive = build(pdf(f"report{char}fdp.exe.pdf"))
    with accept(archive) as found:
        shown = found.members[0].display_name
    assert shown == _showable(f"report{char}fdp.exe.pdf").strip()
    assert char not in shown


def test_a_hint_is_cut_and_a_base_name_never_blank() -> None:
    extra = unicode_path(b"x.pdf", "d/" + "n" * 5000 + ".pdf")
    long = entry("x.pdf", PDF_HEADER, local_extra=extra, central_extra=extra)
    folder_only = unicode_path(b"y.pdf", "only/a/folder/")
    blank = entry("y.pdf", PDF_HEADER, local_extra=folder_only, central_extra=folder_only)
    with accept(build(long, blank)) as found:
        first, second = found.members
        assert len(first.display_name) == MAX_HINT
        assert len(first.base_name) <= 255
        assert second.display_name == "only/a/folder/"
        assert second.base_name == "document.pdf" and second.folder == "only/a/folder"


def test_folder_and_base_name_split_the_hint_and_a_nested_archive_counts_as_one_folder() -> None:
    archive = build(
        pdf("root.pdf", b"0"), pdf("A/B/deep.pdf", b"1"), nested("stage/pack.zip", pdf("x.pdf", b"2"))
    )
    with accept(archive) as found:
        assert [(m.folder, m.base_name) for m in found.members] == [
            ("", "root.pdf"), ("A/B", "deep.pdf"), ("stage/pack", "x.pdf")
        ]
        assert [m.level for m in found.members] == [0, 0, 1]


# ---------------------------------------------------------------------------------------
# The policy and the table of refusals
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [{"entries": -1}, {"total_bytes": -1}, {"member_bytes": -1}, {"directory_bytes": -1},
     {"ratio": 0}, {"nesting_levels": -1}, {"nesting_levels": 2}],
)
def test_a_policy_with_a_nonsense_bound_cannot_be_made(bad: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        SetPolicy(**bad)


def test_every_reason_has_one_sentence_that_passes_the_error_screen() -> None:
    assert len(CONSTRAINTS) == len(set(CONSTRAINTS)) == 13
    assert all(c.startswith("comparison_zip_") for c in CONSTRAINTS)
    sentences = [refusals.message_of(c) for c in CONSTRAINTS]
    assert len(set(sentences)) == len(sentences)
    for constraint, sentence in zip(CONSTRAINTS, sentences):
        assert screen_message(sentence) == sentence
        error = refusals.refuse_set(constraint)
        assert error.code is ErrorCode.VALIDATION_FAILED
        assert dict(error.detail_fields) == {"field": "file", "constraint": constraint}
        assert str(error) == sentence
        assert error.envelope("c").as_dict()["details"] == {"field": "file", "constraint": constraint}


def test_the_translation_renames_the_portals_reasons_and_passes_its_own_through() -> None:
    portal = bundle_archive.refuse("bundle_member_size")
    renamed = refusals.translate(portal)
    assert dict(renamed.detail_fields)["constraint"] == "comparison_zip_member_size"
    assert str(renamed) != str(portal)
    own = refusals.refuse_set("comparison_zip_empty")
    assert refusals.translate(own) is own
    other = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE)
    assert refusals.translate(other) is other


def test_a_portal_reason_that_has_no_name_here_is_a_defect_and_not_a_refusal() -> None:
    for unnamed in ("bundle_directory_entry", "bundle_stem_mismatch", "bundle_member_set",
                    "blocks_json_invalid", "stamp_audit_invalid", "something_new"):
        with pytest.raises(RuntimeError, match="does not name"):
            refusals.translate(bundle_archive.refuse(unnamed, "x"))


def test_every_refusal_the_shared_reader_can_raise_under_this_policy_is_named() -> None:
    """The reader's judge is the policy's; the rest -- ``_extract``, ``_judge_declared``,
    ``_unpack`` -- is shared. Whatever those can refuse with must be in the table, or a hostile
    archive would reach ``translate`` and be answered with a server fault. (A reason added to
    them later fails here, before it fails for a user.)"""
    tree = ast.parse(inspect.getsource(bundle_archive))
    shared = {"_extract", "_judge_declared", "_unpack"}
    raised: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in shared:
            for call in ast.walk(node):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id == "refuse" and call.args
                        and isinstance(call.args[0], ast.Constant)):
                    raised.add(str(call.args[0].value))
    assert {"bundle_unreadable", "bundle_entry_count", "bundle_member_size",
            "bundle_total_size", "bundle_compression_ratio", "portal_bundle_required"} <= raised
    # The stamp audit is a member role of the portal bundle; a set's keys are never one.
    portal_only = {"stamp_audit_invalid"}
    named = set(refusals._FROM_PORTAL)
    assert raised - portal_only <= named, sorted(raised - portal_only - named)
    roles = {bundle_archive.ROLE_PDF, bundle_archive.ROLE_BLOCKS, bundle_archive.ROLE_RESULTS_MD,
             bundle_archive.ROLE_RESULTS_HTML, bundle_archive.ROLE_STAMP_AUDIT}
    with accept(build(pdf("a.pdf"), nested("n.zip", pdf("b.pdf")))) as found:
        assert not roles & {m.path.name for m in found.members}
