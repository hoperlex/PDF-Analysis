"""Build the profiles of a stored version and read them back (`CMP-PROFILE-01`), against PostgreSQL and MinIO.

The version is a published ``document_version`` whose source PDF is a real blob; the build is the function the
queue will call. The synthetic corpus' answer key is the oracle for what the stored profile must say. What is
proved here and not in the unit tests: the rows and the three blobs of each page are written in the order the
journal needs and are all ``available``; a second build writes nothing; two builds at once write one row a page; a
failed page is a typed row and does not stop its version (and can be built again on request); a page over the
pixel cap is stored refused and never rendered; the reader returns the bytes and the typed profile; the tile
levels that are not stored are rendered in a child.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy import text

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.runner import SubprocessChildRunner
from auditmanager.comparison.profile.tiles import TileRenderer
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

PNG = b"\x89PNG\r\n\x1a\n"
MIB = 1024 * 1024


def _unique_pdf(directory: Path, pages: int = 2) -> Path:
    """A PDF whose pages have never been seen by the lane's object store (blobs are content-addressed: a page
    that an earlier run published is ``available`` already, and would hide a blob left in flight)."""
    from reportlab.pdfgen import canvas

    path = directory / f"unique-{uuid.uuid4().hex}.pdf"
    sheet = canvas.Canvas(str(path), pagesize=(595.28, 841.89))
    for number in range(pages):
        sheet.drawString(72, 700, f"unique {uuid.uuid4()} page {number}")
        sheet.showPage()
    sheet.save()
    return path


def _reader(session_factory, blob_store) -> PageProfileReader:
    return PageProfileReader(session_factory, blob_store, tiles=TileRenderer())


def test_a_version_is_profiled_page_by_page_and_read_back_as_its_key_says(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir, vs1_key
) -> None:
    key = next(v for v in vs1_key["versions"] if v["id"] == "V4")  # six pages, one of them a scan
    version = seed_version(fixtures_dir / "vs1" / "v4.pdf", key["page_count"])
    report = build_version_page_profiles(session_factory, blob_store, version)

    assert (report.page_count, len(report.pages), report.skipped, report.complete) == (6, 6, 0, True)
    assert [page.status for page in report.pages] == ["ready"] * 6 and all(page.created for page in report.pages)
    rows = rows_of(version)
    assert [row.page_number for row in rows] == [1, 2, 3, 4, 5, 6]
    assert len({row.content_key for row in rows}) == 6
    assert all(row.profile_blob_id and row.preview_blob_id and row.thumbnail_blob_id for row in rows)

    reader = _reader(session_factory, blob_store)
    profiles = reader.read_version_profiles(version)
    assert [p.row.page_number for p in profiles] == [1, 2, 3, 4, 5, 6]
    for profile, page_key in zip(profiles, key["pages"], strict=True):
        assert profile.scan is page_key["scan"] and profile.has_text_layer is page_key["text_layer"]
        assert round(profile.width_pt, 1) == round(page_key["width_pt"], 1)
        assert len(profile.annotations) == len(page_key["annotations"])
        if page_key["text_layer"]:
            assert profile.stamp.sheet_number == page_key["sheet_no"] and profile.stamp.sheet_title == page_key["title"]
            assert profile.stamp.designation == page_key["stamp"]["designation"]
            assert profile.words and profile.lines and profile.content_merkle
        else:
            assert (profile.words, profile.stamp.sheet_number, profile.stamp.sheet_title) == ((), None, None)
        mask = profile.ink_mask
        assert mask is not None and (mask.dpi, mask.as_array().shape) == (36, (mask.height_px, mask.width_px))
        assert 0.0 < mask.ink_ratio < 0.5 and profile.raster[0] == 200


def test_every_blob_a_row_names_is_available_and_none_is_left_in_flight(
    session_factory, blob_store, seed_version, rows_of, tmp_path
) -> None:
    """The audit of ``blob_reference_audit`` requires every blob a page profile names to be ``available``; the
    journal (declared, verifying, available) ends there for each of the three blobs of each page. The pages are
    new to the store, so a blob left in an earlier state cannot be hidden by an earlier run's publication."""
    version = seed_version(_unique_pdf(tmp_path), 2)
    build_version_page_profiles(session_factory, blob_store, version)
    rows = rows_of(version)
    named = {blob for row in rows for blob in (row.profile_blob_id, row.preview_blob_id, row.thumbnail_blob_id)}
    assert len(named) == 6
    with session_scope(session_factory) as session:
        states = {
            blob: state
            for blob, state in session.execute(text("SELECT blob_id, state FROM blob WHERE blob_id = ANY(:ids)"), {"ids": sorted(named)}).all()
        }
    assert states == {blob: "available" for blob in named}


def test_the_images_and_tiles_are_served_stored_for_levels_2_and_up_and_rendered_below(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir
) -> None:
    version = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, version)
    a1 = rows_of(version)[4]
    reader = _reader(session_factory, blob_store)
    profile_id = a1.comparison_page_profile_id

    preview, thumbnail = reader.read_preview(profile_id), reader.read_thumbnail(profile_id)
    assert preview.startswith(PNG) and len(preview) == 187156, "the byte count of MEASURE-RENDER-01 for this sheet"
    assert thumbnail.startswith(PNG) and len(thumbnail) == 11933

    # Stored: level 2, 3, 4. Rendered on request in a child: level 0, 1.
    for level, column, row in ((2, 3, 2), (3, 1, 1), (4, 0, 0), (1, 6, 4), (0, 12, 9), (0, 5, 5)):
        tile = reader.read_tile(profile_id, level=level, column=column, row=row)
        assert tile.startswith(PNG), (level, column, row)
    # Not in the pyramid: not_found, never an empty tile.
    for level, column, row in ((0, 13, 0), (1, 0, 5), (2, 4, 0), (5, 0, 0)):
        with pytest.raises(DomainError) as raised:
            reader.read_tile(profile_id, level=level, column=column, row=row)
        assert raised.value.code is ErrorCode.NOT_FOUND


def test_a_second_build_writes_nothing_and_two_builds_at_once_write_one_row_a_page(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir
) -> None:
    version = seed_version(fixtures_dir / "vs1" / "v2.pdf", 6)
    reports: list = []

    def build() -> None:
        reports.append(build_version_page_profiles(session_factory, blob_store, version, pages={1, 2, 3}))

    threads = [threading.Thread(target=build) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(reports) == 2
    rows = rows_of(version)
    assert [row.page_number for row in rows] == [1, 2, 3], "one row a page however many builders"
    created = sum(1 for report in reports for page in report.pages if page.created)
    assert created == 3, "each row was created exactly once; the other builder saw a conflict and read the row"
    ids_before = [row.comparison_page_profile_id for row in rows]

    rest = build_version_page_profiles(session_factory, blob_store, version)
    assert (len(rest.pages), rest.skipped, rest.complete) == (3, 3, True)
    again = build_version_page_profiles(session_factory, blob_store, version)
    assert (again.pages, again.skipped, again.complete) == ((), 6, True)
    assert [row.comparison_page_profile_id for row in rows_of(version)][:3] == ids_before


def test_a_page_that_ends_without_a_result_is_a_typed_row_and_the_version_goes_on(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir
) -> None:
    version = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    squeezed = limits.ChildLimits(144 * MIB, 300, 600.0)  # the A1 plan needs 196 MiB, an A3 sheet 92
    report = build_version_page_profiles(session_factory, blob_store, version, render_limits=squeezed)
    assert [page.status for page in report.pages] == ["ready", "ready", "ready", "ready", "needs_review", "ready"]
    failed = rows_of(version)[4]
    assert (failed.status, failed.reason) == ("needs_review", "RENDER_FAILED")
    assert (failed.profile_blob_id, failed.preview_blob_id, failed.thumbnail_blob_id) == (None, None, None)
    reader = _reader(session_factory, blob_store)
    with pytest.raises(DomainError) as raised:
        reader.read_preview(failed.comparison_page_profile_id)
    assert raised.value.code is ErrorCode.NOT_FOUND, "a page with no preview has none: 404, not an empty image"
    data = reader.read_page_profile(failed.comparison_page_profile_id)
    assert data.words == () and data.ink_mask is None and data.row.summary["failure"]["stage"] == "render"

    # A second build leaves the failed page as it is; a build that asks to retry builds it, and only it.
    before = [row.comparison_page_profile_id for row in rows_of(version)]
    assert build_version_page_profiles(session_factory, blob_store, version).pages == ()
    retried = build_version_page_profiles(session_factory, blob_store, version, retry_failed=True)
    assert [(page.page_number, page.status) for page in retried.pages] == [(5, "ready")] and retried.replaced_failed == 1
    after = [row.comparison_page_profile_id for row in rows_of(version)]
    assert after[:4] == before[:4] and after[5] == before[5] and after[4] != before[4]
    assert rows_of(version)[4].profile_blob_id is not None
    # Nothing that is evidence is ever removed: asking to retry a version with no failed page deletes nothing.
    untouched = build_version_page_profiles(session_factory, blob_store, version, retry_failed=True)
    assert (untouched.replaced_failed, untouched.pages) == (0, ())
    assert [row.comparison_page_profile_id for row in rows_of(version)] == after


def test_a_page_over_the_pixel_cap_is_stored_refused_and_never_rendered(
    session_factory, blob_store, seed_version, rows_of, tmp_path
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=12000, height=12000)
    writer.add_blank_page(width=595, height=842)
    path = tmp_path / "with-a-huge-page.pdf"
    with open(path, "wb") as sink:
        writer.write(sink)
    version = seed_version(path, 3)

    seen: list[str] = []

    class Spy:
        def __init__(self) -> None:
            self.real = SubprocessChildRunner()

        def run(self, settings, child_limits):
            seen.append(f"{settings['mode']}:{settings['page']}")
            return self.real.run(settings, child_limits)

    report = build_version_page_profiles(session_factory, blob_store, version, runner=Spy())
    assert [page.status for page in report.pages] == ["ready", "refused", "ready"]
    assert "render:1" in seen and "extract:1" not in seen, "the extraction child was never started for the huge page"
    row = rows_of(version)[1]
    assert (row.status, row.reason) == ("refused", "PAGE_TOO_LARGE")
    assert (row.profile_blob_id, row.preview_blob_id, row.thumbnail_blob_id) == (None, None, None)
    data = _reader(session_factory, blob_store).read_page_profile(row.comparison_page_profile_id)
    assert (data.width_pt, data.words, data.ink_mask) == (12000.0, (), None)


def test_a_version_that_is_unknown_or_has_no_source_document_is_refused(
    session_factory, blob_store, seed_version, fixtures_dir
) -> None:
    with pytest.raises(DomainError) as raised:
        build_version_page_profiles(session_factory, blob_store, "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert raised.value.code is ErrorCode.NOT_FOUND
    bare = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6, with_manifest=False)
    with pytest.raises(DomainError) as raised:
        build_version_page_profiles(session_factory, blob_store, bare)
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_a_listing_pages_by_page_number_and_an_unknown_version_is_not_found(
    session_factory, blob_store, seed_version, fixtures_dir
) -> None:
    version = seed_version(fixtures_dir / "vs1" / "v3.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, version)
    reader = _reader(session_factory, blob_store)
    first, more = reader.list_profiles(version, after_page=0, limit=4)
    assert ([row.page_number for row in first], more) == ([1, 2, 3, 4], True)
    second, more = reader.list_profiles(version, after_page=4, limit=4)
    assert ([row.page_number for row in second], more) == ([5, 6], False)
    with pytest.raises(DomainError) as raised:
        reader.list_profiles("ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", after_page=0, limit=10)
    assert raised.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError):
        reader.get_profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")


def test_a_row_is_frozen_and_its_blob_references_are_write_once(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir
) -> None:
    """The lane relies on the schema's guards (`0038`): after the insert nothing about a profile changes."""
    version = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, version, pages={1})
    row = rows_of(version)[0]
    for statement in (
        "UPDATE comparison_page_profile SET status = 'needs_review', reason = 'X' WHERE comparison_page_profile_id = :i",
        "UPDATE comparison_page_profile SET profile = '{}'::jsonb WHERE comparison_page_profile_id = :i",
        "UPDATE comparison_page_profile SET preview_blob_id = thumbnail_blob_id WHERE comparison_page_profile_id = :i",
    ):
        with pytest.raises(Exception):  # noqa: B017 - a database error whatever the driver calls it
            with session_scope(session_factory) as session:
                session.execute(text(statement), {"i": row.comparison_page_profile_id})
    assert rows_of(version)[0].status == "ready"


def test_the_source_is_digest_checked_on_the_way_to_the_child_and_no_child_is_started_for_it(
    session_factory, blob_store, seed_version, fixtures_dir
) -> None:
    """A version whose recorded digest is not the digest of its blob is refused before any page child runs."""
    version = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6, manifest_sha256="0" * 64)
    started: list[str] = []

    class Spy:
        def run(self, settings, child_limits):
            started.append(settings["mode"])
            raise AssertionError("no child may start")

    with pytest.raises(DomainError) as raised:
        build_version_page_profiles(session_factory, blob_store, version, runner=Spy())
    assert raised.value.code in (ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR)
    assert started == []


def test_a_tile_child_that_ends_without_a_result_is_dependency_unavailable_and_serves_no_tile(
    session_factory, blob_store, seed_version, rows_of, fixtures_dir
) -> None:
    version = seed_version(fixtures_dir / "vs1" / "v1.pdf", 6)
    build_version_page_profiles(session_factory, blob_store, version, pages={5})
    profile_id = rows_of(version)[0].comparison_page_profile_id
    starved = PageProfileReader(
        session_factory, blob_store, tiles=TileRenderer(tile_limits=limits.ChildLimits(40 * MIB, 300, 30.0))
    )
    with pytest.raises(DomainError) as raised:
        starved.read_tile(profile_id, level=0, column=0, row=0)
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(raised.value.detail_fields) == {"dependency": "page_tile_render"}
    # A stored level does not need a child at all: the same starved reader still serves it.
    assert starved.read_tile(profile_id, level=3, column=0, row=0).startswith(PNG)
