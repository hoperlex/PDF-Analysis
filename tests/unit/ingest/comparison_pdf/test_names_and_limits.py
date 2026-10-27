"""`CMP-INGEST-01`: what a file name hints at, and the limits of ADR-0025 decision 9 as typed refusals.

A name is a hint for the proposal and never an identity (decision 10); a declared batch over a limit is refused
before the first part, with a registered reason and nothing created (decision 9). Each limit is shown failing: the
boundary value is accepted, one more is refused with *its own* constraint, and a mutation of the limit makes the
boundary test red (the mutation proofs are in the report).
"""

from __future__ import annotations

import pytest

from auditmanager.ingest.comparison_pdf import limits
from auditmanager.ingest.comparison_pdf.limits import (
    MAX_BATCH_BYTES,
    MAX_BATCH_PAGES,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_PROJECT_BYTES,
    MAX_SETS,
    PART_BYTES,
    DeclaredFile,
    check_declaration,
    parts_needed,
)
from auditmanager.ingest.comparison_pdf.names import group_key, name_hint, source_filename_of
from auditmanager.shared.errors import DomainError, ErrorCode


class TestNameHints:
    def test_the_original_hints_are_read(self) -> None:
        hint = name_hint("Чертежи ЭМ изм 3 (2).pdf")
        assert hint.file_number == 2 and hint.izm_in_name == 3
        assert hint.name_base == "чертежи эм"

    def test_a_bare_name_has_no_folder_and_a_path_has_one(self) -> None:
        assert name_hint("a.pdf").folder is None
        hint = name_hint("Корпус 1\\Раздел ЭМ/план.pdf")
        assert hint.folder == "корпус 1/раздел эм" and hint.file_name == "план.pdf"

    def test_a_folder_groups_before_a_name_and_the_two_kinds_never_collide(self) -> None:
        in_folder = name_hint("Папка/v1.pdf")
        assert group_key(in_folder) == group_key(name_hint("Папка/другое имя.pdf")) == "folder:папка"
        assert group_key(name_hint("папка.pdf")) == "name:папка"
        assert group_key(name_hint("папка.pdf")) != group_key(in_folder)

    def test_copies_of_one_name_share_a_base_whatever_their_numbers(self) -> None:
        assert name_hint("План (1).pdf").name_base == name_hint("План (2).pdf").name_base == "план"

    def test_a_display_name_is_stored_without_control_characters(self) -> None:
        from auditmanager.ingest.comparison_pdf.names import clean_display_name

        assert clean_display_name("  a\x00b\x1f.pdf \n") == "ab.pdf"
        assert clean_display_name("\x00\x01 ") == ""

    def test_the_stored_file_name_is_a_plain_base_name(self) -> None:
        assert source_filename_of("Папка/Под папка\\файл.pdf") == "файл.pdf"
        assert source_filename_of("x" * 300) == "x" * 255
        assert source_filename_of("..") == "document.pdf"
        assert source_filename_of("a\x00b.pdf") == "ab.pdf"


def _files(count: int, size: int = 10, pages: int | None = None, name: str = "f{}.pdf") -> list[DeclaredFile]:
    return [DeclaredFile(name.format(i), size, pages) for i in range(count)]


def _refusal(files: list[DeclaredFile], stored: int = 0) -> tuple[str | None, str | None]:
    with pytest.raises(DomainError) as caught:
        check_declaration(files, project_stored_bytes=stored)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    return caught.value.detail_fields.get("field"), caught.value.detail_fields.get("constraint")


class TestDecisionNineLimits:
    def test_the_numbers_are_the_adrs(self) -> None:
        assert (MAX_FILES, MAX_SETS, MAX_BATCH_PAGES) == (10_000, 100, 10_000)
        assert MAX_BATCH_BYTES == MAX_PROJECT_BYTES == 8 * 1024**3
        assert PART_BYTES == 16 * 1024 * 1024 and MAX_FILE_BYTES == 250 * 1024 * 1024

    def test_files_at_the_limit_pass_and_one_more_is_refused(self) -> None:
        # 100 name groups keep the sets limit out of this test: every file shares one folder.
        same_folder = [DeclaredFile(f"Папка/f{i}.pdf", 1) for i in range(10_000)]
        check_declaration(same_folder, project_stored_bytes=0)
        assert _refusal(same_folder + [DeclaredFile("Папка/last.pdf", 1)]) == ("files", "comparison_files_limit")

    def test_sets_are_counted_on_the_name_groups(self) -> None:
        check_declaration(_files(100), project_stored_bytes=0)
        assert _refusal(_files(101)) == ("files", "comparison_sets_limit")

    def test_the_sets_limit_is_the_groups_not_the_files(self) -> None:
        many_in_few = [DeclaredFile(f"Папка {i % 50}/f{i}.pdf", 1) for i in range(1000)]
        check_declaration(many_in_few, project_stored_bytes=0)

    def test_declared_bytes_at_the_limit_pass_and_one_more_is_refused(self) -> None:
        # Files of the envelope's own size bound: 8 GiB is 32.77 of them.
        eight_gib, file_bytes = 8 * 1024**3, 250 * 1024 * 1024
        whole = eight_gib // file_bytes
        files = [DeclaredFile(f"Папка/f{i}.pdf", file_bytes) for i in range(whole)]
        files.append(DeclaredFile("Папка/rest.pdf", eight_gib - whole * file_bytes))
        check_declaration(files, project_stored_bytes=0)
        files.append(DeclaredFile("Папка/one.pdf", 1))
        assert _refusal(files) == ("files", "comparison_batch_bytes_limit")

    def test_declared_pages_at_the_limit_pass_and_one_more_is_refused(self) -> None:
        pages = [DeclaredFile(f"Папка/f{i}.pdf", 1, 500) for i in range(20)]  # 10 000 pages
        check_declaration(pages, project_stored_bytes=0)
        assert _refusal(pages + [DeclaredFile("Папка/x.pdf", 1, 1)]) == ("files", "comparison_batch_pages_limit")

    def test_the_project_bytes_are_what_it_stores_plus_what_is_declared(self) -> None:
        eight_gib = 8 * 1024**3
        check_declaration(_files(1, size=100), project_stored_bytes=eight_gib - 100)
        assert _refusal(_files(1, size=100), stored=eight_gib - 99) == ("files", "comparison_project_bytes_limit")

    def test_one_file_over_the_envelopes_size_is_refused_on_its_content(self) -> None:
        check_declaration([DeclaredFile("a.pdf", 250 * 1024 * 1024)], project_stored_bytes=0)
        assert _refusal([DeclaredFile("a.pdf", 250 * 1024 * 1024 + 1)]) == ("content", "byte_size <= 262144000")

    def test_the_first_limit_on_the_list_is_the_one_reported(self) -> None:
        both = [DeclaredFile(f"Папка/f{i}.pdf", 1) for i in range(MAX_FILES + 1)]
        assert _refusal(both, stored=MAX_PROJECT_BYTES)[1] == "comparison_files_limit"

    def test_a_refusal_never_echoes_a_file_name(self) -> None:
        with pytest.raises(DomainError) as caught:
            check_declaration([DeclaredFile("секретное имя.pdf", MAX_FILE_BYTES + 1)], project_stored_bytes=0)
        assert "секретное" not in repr(caught.value.detail_fields) and "секретное" not in str(caught.value)


class TestParts:
    @pytest.mark.parametrize(
        ("size", "parts"),
        [(1, 1), (PART_BYTES, 1), (PART_BYTES + 1, 2), (2 * PART_BYTES, 2), (250 * 1024 * 1024, 16)],
    )
    def test_every_part_but_the_last_is_one_part_long(self, size: int, parts: int) -> None:
        assert parts_needed(size) == parts

    def test_an_empty_file_has_no_parts(self) -> None:
        with pytest.raises(ValueError):
            parts_needed(0)

    def test_a_largest_file_needs_far_fewer_parts_than_the_store_allows(self) -> None:
        assert limits.parts_needed(MAX_FILE_BYTES) <= 10_000
