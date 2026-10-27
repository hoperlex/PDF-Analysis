"""`CMP-INGEST-01`: reading a plain PDF for comparison -- the envelope policy and the stamp reader, in ceilinged children.

No database and no object store: the two programs run over real PDFs. The synthetic corpus
(``fixtures/comparison/vs1``) is read against **its answer key**, which was authored beside the sheets and is not the
output of this reader: the designation, the highest «Изм.» of each version, its date, its page count and the scan page.

The comparison envelope differs from the portal envelope in figures only (ADR-0025 decision 11, addendum item 3): a page
of 450 000 drawing elements -- under the 536 426 of the real set, over the portal's 400 000 -- is admitted here and refused
there, and the portal envelope's own figures are asserted unchanged. A page with no text layer is admitted and said so
(a scan is compared as an image). Every refusal keeps the field, constraint and message of the portal's own.
"""

from __future__ import annotations

import io
import json
import time
import zlib
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import envelope as portal
from auditmanager.ingest.comparison_pdf import child, stamp_reader
from auditmanager.ingest.comparison_pdf.envelope import (
    COMPARISON_POLICY,
    ComparisonEnvelopePolicy,
    inspect_comparison_pdf,
)
from auditmanager.ingest.comparison_pdf.reading import ZONE_HEIGHT_MM, ZONE_WIDTH_MM, read_pdf
from auditmanager.shared.errors import DomainError

ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "fixtures" / "comparison"
NEGATIVE = ROOT / "fixtures" / "synthetic" / "ar" / "negative"
KEY = json.loads((CORPUS / "vs1" / "answer_key.json").read_text(encoding="utf-8"))
MiB = 1024 * 1024


def _pdf(pages: int, content: bytes, *, rotate: int = 0, media: str = "0 0 595 842", crop: str | None = None) -> bytes:
    packed = zlib.compress(content, 9)
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [" + media.encode() + b"] "
        + (b"/CropBox [" + crop.encode() + b"] " if crop else b"")
        + (b"/Rotate %d " % rotate if rotate else b"")
        + b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % (5 + i) for i in range(pages)) + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed) + packed + b"\nendstream",
        *([page] * pages),
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


_TEXT = b"BT /F1 9 Tf 10 10 Td (a line of text for the layer, well over fifty characters) Tj ET\n"
#: 225 000 paths of two segments: 450 000 drawing elements on one page, in 6.7 KB. Above the portal envelope's
#: 400 000, below the 536 426 of the real set's heaviest page (`MEASURE-RENDER-01` section 3, finding 9).
PATHS_450K = b"0 0 m 1 1 l S " * 225_000
PATHS = _TEXT + b"0 0 m 1 1 l S " * 40_000
TEXT_BOMB = b"BT /F1 1 Tf 0 0 Td " + b"(AAAAAAAAAAAAAAAA) Tj " * 500_000 + b"ET"


def _refusal(call: Any) -> dict[str, Any]:
    with pytest.raises(DomainError) as refused:
        call()
    return dict(refused.value.detail_fields) | {"message": str(refused.value)}


class TestTheCorpusAgainstItsAnswerKey:
    @pytest.mark.parametrize("version", KEY["versions"], ids=[v["id"] for v in KEY["versions"]])
    def test_every_version_is_read_as_the_key_says(self, version: dict[str, Any]) -> None:
        reading = read_pdf((CORPUS / version["file"]).open("rb"))
        stamp = reading.stamp
        assert stamp.designation == KEY["designation"] == version["designation"]
        assert f"Изм.{stamp.revision_number}" == version["label"]
        assert stamp.release_date == date(*reversed([int(part) for part in version["date"].split(".")]))
        assert stamp.page_count == version["page_count"] == reading.facts.page_count
        assert stamp.project_stage == "R"  # every sheet states «Стадия Р»
        assert stamp.section_code == "EOM"  # the mark ЭМ
        scans = tuple(page["page"] for page in version["pages"] if not page["text_layer"])
        assert stamp.textless_pages == scans

    def test_the_scan_page_is_listed_and_contributes_no_stamp(self) -> None:
        v4 = next(v for v in KEY["versions"] if v["id"] == "V4")
        stamp = read_pdf((CORPUS / v4["file"]).open("rb")).stamp
        assert stamp.textless_pages == (4,) and stamp.stamped_pages == 5
        # Five of six pages carry the designation: the scan said nothing, and was not guessed.
        assert stamp.designation_votes == ((KEY["designation"], 5),)

    def test_the_second_corpus_is_read_too(self) -> None:
        old = read_pdf((CORPUS / "sp1" / "old_p.pdf").open("rb")).stamp
        assert (old.designation, old.project_stage, old.section_code) == ("СИНТ-02-АР", "P", "AR")
        new = read_pdf((CORPUS / "sp1" / "new_r1.pdf").open("rb")).stamp
        assert (new.designation, new.project_stage) == ("СИНТ-02-АР.1", "R")

    def test_a_reader_given_bytes_or_a_handle_answers_the_same(self) -> None:
        path = CORPUS / "vs1" / "v1.pdf"
        assert read_pdf(path.read_bytes()).stamp == read_pdf(path.open("rb")).stamp


class TestThePolicy:
    def test_the_portal_envelope_is_unchanged(self) -> None:
        assert portal.PAGE_ELEMENTS_MAX == 400_000
        assert portal.PAGE_CHARACTERS_MAX == 200_000
        assert portal.DOCUMENT_ELEMENTS_MAX == 8_000_000
        assert portal.DOCUMENT_CHARACTERS_MAX == 20_000_000
        assert portal.READER_ADDRESS_SPACE == 512 * MiB and portal.READER_SECONDS == 60
        assert portal.MAX_BYTES == 250 * MiB and (portal.MIN_PAGES, portal.MAX_PAGES) == (1, 500)

    def test_the_comparison_figures_are_the_recorded_ones(self) -> None:
        policy = COMPARISON_POLICY
        assert policy.page_elements == 1_000_000  # 1.86 x the real set's 536 426
        assert policy.page_elements > 536_426 > portal.PAGE_ELEMENTS_MAX
        assert policy.address_space == 768 * MiB  # decision 8's default ceiling
        assert (policy.max_bytes, policy.min_pages, policy.max_pages) == (250 * MiB, 1, 500)
        assert policy.page_characters == portal.PAGE_CHARACTERS_MAX
        assert policy.document_elements == portal.DOCUMENT_ELEMENTS_MAX
        assert policy.document_characters == portal.DOCUMENT_CHARACTERS_MAX

    def test_a_page_of_450000_elements_is_admitted_here_and_refused_by_the_portal(self) -> None:
        data = _pdf(1, PATHS_450K)
        assert _refusal(lambda: portal.inspect_pdf(data, require_text=False))["constraint"] == "pdf_page_content"
        facts = inspect_comparison_pdf(data)
        assert facts.page_count == 1 and facts.page_has_layer == (False,)

    def test_the_element_limit_is_the_policys_not_a_constant_of_the_reader(self) -> None:
        tight = ComparisonEnvelopePolicy(**{**_fields(COMPARISON_POLICY), "page_elements": 1_000})
        found = _refusal(lambda: inspect_comparison_pdf(_pdf(1, b"0 0 m 1 1 l S " * 2_000), policy=tight))
        assert (found["field"], found["constraint"]) == ("content", "pdf_page_content")

    def test_a_page_with_no_text_layer_is_admitted_where_the_portal_demands_one(self) -> None:
        scan = (NEGATIVE / "image_only.pdf").read_bytes()
        assert _refusal(lambda: portal.inspect_pdf(scan, require_text=True))["constraint"] == "every_page_has_extractable_text"
        reading = read_pdf(scan)
        assert reading.stamp.textless_pages == tuple(range(1, reading.facts.page_count + 1))
        assert reading.stamp.designation is None and reading.stamp.stamped_pages == 0


def _fields(policy: ComparisonEnvelopePolicy) -> dict[str, Any]:
    return {name: getattr(policy, name) for name in policy.__slots__}


class TestRefusalsKeepTheirWords:
    """A refusal is the portal's own: one fault, one wording, whichever door it came through."""

    @pytest.mark.parametrize(
        "make",
        [
            lambda: (NEGATIVE / "encrypted.pdf").read_bytes(),
            lambda: (NEGATIVE / "not_a_pdf.txt").read_bytes(),
            lambda: b"",
            lambda: _pdf(1, b"")[:200],
            lambda: _pdf(501, _TEXT),
        ],
        ids=["encrypted", "not-a-pdf", "empty", "truncated", "501-pages"],
    )
    def test_the_same_field_constraint_and_message_as_the_portal(self, make: Any) -> None:
        data = make()
        expected = _refusal(lambda: portal.inspect_pdf(data, require_text=False))
        assert _refusal(lambda: inspect_comparison_pdf(data)) == expected

    def test_an_oversize_file_is_refused_before_a_parse(self, tmp_path: Path) -> None:
        path = tmp_path / "huge.pdf"
        with path.open("wb") as out:
            out.write(b"%PDF-1.7\n")
            out.truncate(COMPARISON_POLICY.max_bytes + 1)
        with path.open("rb") as handle:
            found = _refusal(lambda: inspect_comparison_pdf(handle))
        assert (found["field"], found["constraint"]) == ("content", f"byte_size <= {250 * MiB}")

    def test_the_encrypted_document_is_refused_by_the_stamp_reader_too(self) -> None:
        found = _refusal(lambda: read_pdf((NEGATIVE / "encrypted.pdf").read_bytes()))
        assert found["constraint"] == "not_encrypted"


class TestTheChildren:
    def test_a_text_bomb_over_the_element_limit_is_refused_by_that_rule_in_seconds(self) -> None:
        bomb = b"BT /F1 1 Tf 0 0 Td " + b"(AAAAAAAAAAAAAAAA) Tj " * (COMPARISON_POLICY.page_elements + 1) + b"ET"
        started = time.monotonic()
        found = _refusal(lambda: inspect_comparison_pdf(_pdf(30, bomb)))
        assert found["constraint"] == "pdf_page_content" and time.monotonic() - started < 30

    def test_a_text_bomb_under_the_element_limit_is_stopped_by_the_ceiling_not_by_the_api(self) -> None:
        """500 000 strings pass the element rule (1 000 000 here, 400 000 for the portal), and the 8 M characters
        on the page are more than 768 MiB can hold: the child is ended by the kernel and the document is refused
        ``pdf_reader_limits``. The API process's own memory is untouched either way."""
        import resource

        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        started = time.monotonic()
        found = _refusal(lambda: inspect_comparison_pdf(_pdf(30, TEXT_BOMB)))
        assert found["constraint"] in ("pdf_reader_limits", "pdf_page_content")
        assert time.monotonic() - started < 60
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 - before < 64

    def test_a_short_clock_stops_a_slow_document(self) -> None:
        short = ComparisonEnvelopePolicy(**{**_fields(COMPARISON_POLICY), "seconds": 1})
        found = _refusal(lambda: inspect_comparison_pdf(_pdf(500, PATHS), policy=short))
        assert found["constraint"] == "pdf_reader_limits"

    def test_a_child_that_never_answers_is_killed_and_the_document_refused(self, tmp_path: Path) -> None:
        stalled = tmp_path / "stalled.py"
        stalled.write_text('import time\nprint("ready", flush=True)\ntime.sleep(600)\n')
        with open(CORPUS / "vs1" / "v1.pdf", "rb") as handle:
            started = time.monotonic()
            found = _refusal(lambda: child.run_child(stalled, handle.fileno(), {}, wall_seconds=2))
        assert found["constraint"] == "pdf_reader_limits" and time.monotonic() - started < 10

    def test_a_child_that_never_starts_is_the_servers_fault(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="did not start"):
            child.run_child(tmp_path / "absent.py", 0, {}, wall_seconds=5)

    def test_a_child_gets_no_secret_of_the_api(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("AUDITMANAGER_API_TOKEN", "a-secret-the-child-must-not-see")
        spy = tmp_path / "spy.py"
        spy.write_text(
            "import json, os\nprint('ready', flush=True)\n"
            "print(json.dumps({'leaked': sorted(set(os.environ) - {'PATH', 'LC_CTYPE'})}), flush=True)\n"
        )
        assert child.run_child(spy, 0, {}, wall_seconds=10) == {"leaked": []}

    def test_a_child_answering_something_else_is_the_servers_fault(self, tmp_path: Path) -> None:
        odd = tmp_path / "odd.py"
        odd.write_text("print('ready', flush=True)\nprint('not json', flush=True)\n")
        with pytest.raises(RuntimeError, match="answered something else"):
            child.run_child(odd, 0, {}, wall_seconds=10)

    def test_the_stamp_child_is_started_with_this_policys_ceilings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[dict[str, Any]] = []
        real = child.run_child

        def spy(program: Path, descriptor: int, settings: dict[str, Any], *, wall_seconds: int) -> dict[str, Any]:
            seen.append({"program": program.name, "wall": wall_seconds, **settings})
            return real(program, descriptor, settings, wall_seconds=wall_seconds)

        monkeypatch.setattr("auditmanager.ingest.comparison_pdf.reading.run_child", spy)
        monkeypatch.setattr("auditmanager.ingest.comparison_pdf.envelope.run_child", spy)
        read_pdf((CORPUS / "vs1" / "v1.pdf").read_bytes())
        assert [item["program"] for item in seen] == ["pdf_reader.py", "stamp_reader.py"]
        assert all(item["address_space"] == 768 * MiB and item["cpu_seconds"] == 120 and item["wall"] == 120 for item in seen)
        assert seen[0]["page_elements"] == 1_000_000 and seen[0]["require_text"] is False


class TestTheStampZoneFollowsTheDisplayedPage:
    """The title block is at the lower right of the sheet **as shown**, whatever ``/Rotate`` and the CropBox say."""

    ZONE_W, ZONE_H = ZONE_WIDTH_MM * 72 / 25.4, ZONE_HEIGHT_MM * 72 / 25.4

    @staticmethod
    def _native_of_displayed(pdf: bytes, device: tuple[float, float]) -> tuple[float, float]:
        """Where PDFium itself puts a point of the displayed page in the page's own space (no formula of ours)."""
        import ctypes

        import pypdfium2 as pdfium
        import pypdfium2.raw as raw

        document = pdfium.PdfDocument(pdf)
        try:
            page = document[0]
            width, height = page.get_size()
            x, y = ctypes.c_double(), ctypes.c_double()
            # ``FPDF_DeviceToPage`` takes device coordinates with the origin at the top left, y downwards.
            raw.FPDF_DeviceToPage(
                page.raw, 0, 0, int(width), int(height), 0, int(device[0]), int(device[1]),
                ctypes.byref(x), ctypes.byref(y),
            )
            return x.value, y.value
        finally:
            document.close()

    @pytest.mark.parametrize("rotate", [0, 90, 180, 270])
    @pytest.mark.parametrize("crop", [None, "20 30 1180 1670"], ids=["media-box", "inset-crop-box"])
    def test_a_designation_at_the_displayed_lower_right_is_read_and_a_decoy_elsewhere_is_not(
        self, rotate: int, crop: str | None
    ) -> None:
        # A large sheet, so that the three decoy corners lie well outside a 205 x 70 mm zone.
        blank = _pdf(1, b"", rotate=rotate, crop=crop, media="0 0 1200 1700")
        import pypdfium2 as pdfium

        probe = pdfium.PdfDocument(blank)
        width, height = probe[0].get_size()
        probe.close()
        # Four points of the displayed page: the title block's corner, and the other three corners.
        wanted = self._native_of_displayed(blank, (width - 120, height - 80))
        decoys = [
            self._native_of_displayed(blank, point)
            for point in ((80, 80), (width - 120, 80), (80, height - 80), (width / 2, height / 2))
        ]
        # The line must read left to right on the *displayed* page: its native direction is the display's turned back.
        a, b, c, d = {0: (1, 0, 0, 1), 90: (0, 1, -1, 0), 180: (-1, 0, 0, -1), 270: (0, -1, 1, 0)}[rotate]
        ops = b"BT /F1 9 Tf %d %d %d %d %f %f Tm (ABC-01-EM) Tj ET\n" % (a, b, c, d, wanted[0], wanted[1])
        for number, (x, y) in enumerate(decoys):
            ops += b"BT /F1 9 Tf %d %d %d %d %f %f Tm (DEC%d-77-ZZ) Tj ET\n" % (a, b, c, d, x, y, number)
        reading = read_pdf(_pdf(1, ops, rotate=rotate, crop=crop, media="0 0 1200 1700"))
        assert reading.stamp.designation == "ABC-01-EM", (rotate, crop, reading.stamp)
        assert dict(reading.stamp.designation_votes) == {"ABC-01-EM": 1}

    def test_the_zone_of_an_unrotated_page_is_the_lower_right_corner(self) -> None:
        left, bottom, right, top = stamp_reader.native_zone((0.0, 0.0, 595.0, 842.0, 0), self.ZONE_W, self.ZONE_H)
        assert (right, bottom) == (595.0, 0.0)
        assert right - left == pytest.approx(self.ZONE_W) and top - bottom == pytest.approx(self.ZONE_H)

    def test_a_sheet_smaller_than_the_zone_is_read_whole(self) -> None:
        assert stamp_reader.native_zone((0.0, 0.0, 100.0, 50.0, 0), self.ZONE_W, self.ZONE_H) == (0.0, 0.0, 100.0, 50.0)

    def test_a_quarter_turn_swaps_the_zones_sides_and_moves_its_corner(self) -> None:
        l, b, r, t = stamp_reader.native_zone((0.0, 0.0, 1000.0, 2000.0, 90), self.ZONE_W, self.ZONE_H)
        assert (r, t) == (1000.0, 2000.0) and r - l == pytest.approx(self.ZONE_H) and t - b == pytest.approx(self.ZONE_W)
        l, b, r, t = stamp_reader.native_zone((0.0, 0.0, 1000.0, 2000.0, 270), self.ZONE_W, self.ZONE_H)
        assert (l, b) == (0.0, 0.0) and r - l == pytest.approx(self.ZONE_H)
        l, b, r, t = stamp_reader.native_zone((0.0, 0.0, 1000.0, 2000.0, 180), self.ZONE_W, self.ZONE_H)
        assert (l, t) == (0.0, 2000.0) and r - l == pytest.approx(self.ZONE_W)

    def test_the_zone_is_the_originals_205_by_70_millimetres(self) -> None:
        assert (ZONE_WIDTH_MM, ZONE_HEIGHT_MM) == (205.0, 70.0)
