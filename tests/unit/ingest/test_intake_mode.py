"""The intake mode: ADR quotas by default, the lifted ones only when the deployment says so.

`REVIEW-FIX-BOUNDS-1102`. ``AUDITMANAGER_INTAKE_RELAXED`` is read by one function
(``auditmanager.ingest.intake_mode.intake_relaxed``), once per process, when a module that
declares a quota is imported. So the module constants are measured in a child process per mode.
Three families of figures are pinned: the *quotas* move with the flag; the *sandbox* -- the
reader's memory and clock, the ZIP's ratio and sizes, the free disk, the body cap -- does not; and
the counts an upload no longer bounds (`PDF-READER-ROOM-01`) are the representation limits in both.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import auditmanager
from auditmanager.ingest import intake_mode

SOURCE = Path(auditmanager.__file__).resolve().parents[1]
MiB = 1024 * 1024
GiB = 1024 * MiB
INT = 2**31 - 1
LONG = 2**63 - 1

_PROBE = """
import dataclasses, json
from auditmanager.analysis.stages.pdf_precheck import PdfPrecheckLimits
from auditmanager.api.routers import multipart
from auditmanager.comparison.stage import limits as stage
from auditmanager.ingest import bundle_archive as archive, bundle_envelope as bundle, envelope
from auditmanager.ingest.comparison_pdf import envelope as comparison, limits as batch, zip_import
from auditmanager.ingest.comparison_zip import policy
precheck = dataclasses.asdict(PdfPrecheckLimits())
set_policy = dataclasses.asdict(policy.DEFAULT_SET_POLICY)
print(json.dumps({
    "quota": {
        "envelope.MAX_BYTES": envelope.MAX_BYTES, "envelope.MAX_PAGES": envelope.MAX_PAGES,
        "bundle.MAX_BLOCKS_PER_PAGE": bundle.MAX_BLOCKS_PER_PAGE, "bundle.MAX_BLOCKS": bundle.MAX_BLOCKS,
        "bundle.MAX_IMAGE_BLOCKS": bundle.MAX_IMAGE_BLOCKS,
        "comparison.page_elements": comparison.COMPARISON_POLICY.page_elements,
        "comparison.document_elements": comparison.COMPARISON_POLICY.document_elements,
        "comparison.page_characters": comparison.COMPARISON_POLICY.page_characters,
        "comparison.document_characters": comparison.COMPARISON_POLICY.document_characters,
        "comparison.max_bytes": comparison.COMPARISON_POLICY.max_bytes,
        "comparison.max_pages": comparison.COMPARISON_POLICY.max_pages,
        "batch.MAX_FILES": batch.MAX_FILES, "batch.MAX_SETS": batch.MAX_SETS,
        "batch.MAX_BATCH_BYTES": batch.MAX_BATCH_BYTES, "batch.MAX_BATCH_PAGES": batch.MAX_BATCH_PAGES,
        "batch.MAX_PROJECT_BYTES": batch.MAX_PROJECT_BYTES, "batch.MAX_FILE_BYTES": batch.MAX_FILE_BYTES,
        "set.entries": set_policy["entries"],
        "zip_import.MAX_ARCHIVE_BYTES": zip_import.MAX_ARCHIVE_BYTES, "zip_import.MAX_PDFS": zip_import.MAX_PDFS,
        "stage.RAW_BATCH_BYTES": stage.RAW_BATCH_BYTES, "stage.MAX_FILES": stage.MAX_FILES,
        "precheck.max_pages": precheck["max_pages"],
    },
    "unbounded": {
        "envelope.PAGE_ELEMENTS_MAX": envelope.PAGE_ELEMENTS_MAX,
        "envelope.PAGE_CHARACTERS_MAX": envelope.PAGE_CHARACTERS_MAX,
        "envelope.DOCUMENT_ELEMENTS_MAX": envelope.DOCUMENT_ELEMENTS_MAX,
        "envelope.DOCUMENT_CHARACTERS_MAX": envelope.DOCUMENT_CHARACTERS_MAX,
        "precheck.max_page_characters": precheck["max_page_characters"],
        "precheck.max_document_characters": precheck["max_document_characters"],
    },
    "sandbox": {
        "envelope.PDF_MEMBER_BYTES": envelope.PDF_MEMBER_BYTES,
        "envelope.READER_ADDRESS_SPACE": envelope.READER_ADDRESS_SPACE,
        "envelope.READER_SECONDS": envelope.READER_SECONDS,
        "comparison.address_space": comparison.COMPARISON_POLICY.address_space,
        "comparison.seconds": comparison.COMPARISON_POLICY.seconds,
        "archive.MEMBER_BYTES": archive.MEMBER_BYTES, "archive.TEXT_MEMBER_BYTES": archive.TEXT_MEMBER_BYTES,
        "archive.BLOCKS_MEMBER_BYTES": archive.BLOCKS_MEMBER_BYTES,
        "archive.STAMP_AUDIT_BYTES": archive.STAMP_AUDIT_BYTES, "archive.TOTAL_BYTES": archive.TOTAL_BYTES,
        "archive.MAX_RATIO": archive.MAX_RATIO, "archive.MAX_ENTRIES": archive.MAX_ENTRIES,
        "set.total_bytes": set_policy["total_bytes"], "set.member_bytes": set_policy["member_bytes"],
        "set.ratio": set_policy["ratio"], "set.directory_bytes": set_policy["directory_bytes"],
        "set.nesting_levels": set_policy["nesting_levels"],
        "zip_import.MAX_EXPANDED_BYTES": zip_import.MAX_EXPANDED_BYTES,
        "multipart.UPLOAD_MAX_BODY": multipart.UPLOAD_MAX_BODY,
        "precheck.address_space_bytes": precheck["address_space_bytes"],
        "precheck.cpu_seconds": precheck["cpu_seconds"], "precheck.wall_seconds": precheck["wall_seconds"],
        "precheck.startup_seconds": precheck["startup_seconds"],
        "precheck.page_seconds": precheck["page_seconds"],
        "precheck.max_line_bytes": precheck["max_line_bytes"],
        "precheck.max_output_bytes": precheck["max_output_bytes"],
    },
}))
"""

#: ADR-0025 and the portal envelope (R-116): what applies unless the deployment is relaxed.
ADR_QUOTAS = {
    "envelope.MAX_BYTES": 250 * MiB, "envelope.MAX_PAGES": 500,
    "bundle.MAX_BLOCKS_PER_PAGE": 100, "bundle.MAX_BLOCKS": 3_000, "bundle.MAX_IMAGE_BLOCKS": 1_000,
    "comparison.page_elements": 1_000_000, "comparison.document_elements": 8_000_000,
    "comparison.page_characters": 200_000, "comparison.document_characters": 20_000_000,
    "comparison.max_bytes": 250 * MiB, "comparison.max_pages": 500,
    "batch.MAX_FILES": 10_000, "batch.MAX_SETS": 100, "batch.MAX_BATCH_BYTES": 8 * GiB,
    "batch.MAX_BATCH_PAGES": 10_000, "batch.MAX_PROJECT_BYTES": 8 * GiB, "batch.MAX_FILE_BYTES": 250 * MiB,
    "set.entries": 1_000,
    "zip_import.MAX_ARCHIVE_BYTES": 16 * MiB, "zip_import.MAX_PDFS": 100,
    "stage.RAW_BATCH_BYTES": 2 * GiB, "stage.MAX_FILES": 1_000,
    "precheck.max_pages": 500,
}

#: What ``af581631`` set and the relaxed deployment restores.
LIFTED_QUOTAS = {
    "envelope.MAX_BYTES": LONG, "envelope.MAX_PAGES": INT,
    "bundle.MAX_BLOCKS_PER_PAGE": INT, "bundle.MAX_BLOCKS": INT, "bundle.MAX_IMAGE_BLOCKS": INT,
    "comparison.page_elements": LONG, "comparison.document_elements": LONG,
    "comparison.page_characters": INT, "comparison.document_characters": INT,
    "comparison.max_bytes": LONG, "comparison.max_pages": INT,
    "batch.MAX_FILES": INT, "batch.MAX_SETS": INT, "batch.MAX_BATCH_BYTES": LONG,
    "batch.MAX_BATCH_PAGES": INT, "batch.MAX_PROJECT_BYTES": LONG, "batch.MAX_FILE_BYTES": LONG,
    "set.entries": INT,
    "zip_import.MAX_ARCHIVE_BYTES": LONG, "zip_import.MAX_PDFS": INT,
    "stage.RAW_BATCH_BYTES": LONG, "stage.MAX_FILES": INT,
    "precheck.max_pages": INT,
}

#: `PDF-READER-ROOM-01` (owner, 2026-11-11): what an upload no longer counts, in either mode. Each is
#: the representation limit its count is held in; the reader's sandbox (above) is what bounds the work,
#: and the run's precheck mirrors the upload so that it does not refuse a document the upload admitted.
UNBOUNDED = {
    "envelope.PAGE_ELEMENTS_MAX": LONG, "envelope.PAGE_CHARACTERS_MAX": INT,
    "envelope.DOCUMENT_ELEMENTS_MAX": LONG, "envelope.DOCUMENT_CHARACTERS_MAX": INT,
    "precheck.max_page_characters": INT, "precheck.max_document_characters": INT,
}

#: Finite in both modes: the reader's memory and clock (portal and comparison), the archive readers'
#: sizes and ratio, the free-disk reservation of a ZIP import, the API's body cap and the precheck child.
SANDBOX = {
    "envelope.PDF_MEMBER_BYTES": 250 * MiB, "envelope.READER_ADDRESS_SPACE": 2 * GiB,
    "envelope.READER_SECONDS": 120,
    "comparison.address_space": 768 * MiB, "comparison.seconds": 120,
    "archive.MEMBER_BYTES": 250 * MiB, "archive.TEXT_MEMBER_BYTES": 16 * MiB,
    "archive.BLOCKS_MEMBER_BYTES": 4 * MiB, "archive.STAMP_AUDIT_BYTES": 4 * MiB,
    "archive.TOTAL_BYTES": 300 * MiB, "archive.MAX_RATIO": 100, "archive.MAX_ENTRIES": 8,
    "set.total_bytes": 2 * GiB, "set.member_bytes": 250 * MiB, "set.ratio": 100,
    "set.directory_bytes": 4 * MiB, "set.nesting_levels": 1,
    "zip_import.MAX_EXPANDED_BYTES": 256 * MiB,
    "multipart.UPLOAD_MAX_BODY": 251 * MiB,
    "precheck.address_space_bytes": 1536 * MiB, "precheck.cpu_seconds": 1200,
    "precheck.wall_seconds": 1800, "precheck.startup_seconds": 45, "precheck.page_seconds": 180,
    "precheck.max_line_bytes": 32 * MiB, "precheck.max_output_bytes": 256 * MiB,
}


def measure(mode: str) -> dict[str, dict[str, float]]:
    environment = {**os.environ, "PYTHONPATH": str(SOURCE), intake_mode.RELAXED_ENV: mode}
    finished = subprocess.run([sys.executable, "-c", _PROBE], env=environment, capture_output=True,
                              text=True, check=False, timeout=300)
    assert finished.returncode == 0, finished.stderr[-2000:]
    return json.loads(finished.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def strict() -> dict[str, dict[str, float]]:
    return measure("0")


@pytest.fixture(scope="module")
def relaxed() -> dict[str, dict[str, float]]:
    return measure("1")


def test_the_default_deployment_applies_the_adr_quotas(strict: dict) -> None:
    assert strict["quota"] == ADR_QUOTAS


def test_a_relaxed_deployment_takes_the_lifted_quotas(relaxed: dict) -> None:
    assert relaxed["quota"] == LIFTED_QUOTAS


def test_the_sandbox_is_finite_by_default(strict: dict) -> None:
    assert strict["sandbox"] == SANDBOX


def test_the_flag_does_not_move_the_sandbox(strict: dict, relaxed: dict) -> None:
    assert relaxed["sandbox"] == strict["sandbox"] == SANDBOX


def test_what_an_upload_no_longer_counts_is_unbounded_in_both_modes(strict: dict, relaxed: dict) -> None:
    assert strict["unbounded"] == relaxed["unbounded"] == UNBOUNDED


def test_every_quota_the_flag_lifts_is_a_quota_the_adr_bounds(strict: dict, relaxed: dict) -> None:
    assert set(ADR_QUOTAS) == set(LIFTED_QUOTAS) == set(strict["quota"])
    assert all(relaxed["quota"][name] > strict["quota"][name] for name in ADR_QUOTAS)


def test_an_unset_flag_is_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(intake_mode.RELAXED_ENV, raising=False)
    assert intake_mode.intake_relaxed() is False
    assert intake_mode.quota(5, 9) == 5


@pytest.mark.parametrize("value, expected", [("0", False), ("", False), ("off", False), ("false", False),
                                             ("1", True), (" 1 ", True), ("on", True), ("TRUE", True)])
def test_the_flag_reads_as_on_or_off(monkeypatch: pytest.MonkeyPatch, value: str, expected: bool) -> None:
    monkeypatch.setenv(intake_mode.RELAXED_ENV, value)
    assert intake_mode.intake_relaxed() is expected
    assert intake_mode.quota(5, 9) == (9 if expected else 5)


@pytest.mark.parametrize("value", ["2", "yes", "relaxed", "-1", "01"])
def test_a_value_that_is_neither_on_nor_off_is_refused_not_guessed(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(intake_mode.RELAXED_ENV, value)
    with pytest.raises(ValueError, match=intake_mode.RELAXED_ENV):
        intake_mode.intake_relaxed()


def test_a_misspelt_flag_stops_the_process_that_reads_it() -> None:
    environment = {**os.environ, "PYTHONPATH": str(SOURCE), intake_mode.RELAXED_ENV: "yes"}
    finished = subprocess.run([sys.executable, "-c", "import auditmanager.ingest.envelope"], env=environment,
                              capture_output=True, text=True, check=False, timeout=120)
    assert finished.returncode != 0 and intake_mode.RELAXED_ENV in finished.stderr


def test_only_the_intake_mode_module_reads_the_flag() -> None:
    readers = [path.relative_to(SOURCE).as_posix() for path in sorted(SOURCE.rglob("*.py"))
               if intake_mode.RELAXED_ENV in path.read_text(encoding="utf-8")
               and path.name != "intake_mode.py"]
    # Other modules may name the variable in a docstring or comment, never read it.
    for relative in readers:
        text = (SOURCE / relative).read_text(encoding="utf-8")
        assert "os.environ" not in text and "getenv" not in text, relative


_READ = """
import json, sys
from auditmanager.ingest import envelope
from auditmanager.ingest.comparison_pdf.envelope import inspect_comparison_pdf
from auditmanager.shared.errors import DomainError
data = open(sys.argv[1], "rb").read()
answer = {}
for name, read in (("portal", lambda: envelope.inspect_pdf(data, require_text=False)),
                   ("comparison", lambda: inspect_comparison_pdf(data))):
    try:
        answer[name] = read().page_count
    except DomainError as refusal:
        answer[name] = refusal.detail_fields["constraint"]
print(json.dumps(answer))
"""


def read_501_pages(tmp_path: Path, mode: str) -> dict[str, int | str]:
    from tests.unit.ingest.comparison_pdf.test_reading import _TEXT, _pdf

    document = tmp_path / "long.pdf"
    document.write_bytes(_pdf(501, _TEXT))
    environment = {**os.environ, "PYTHONPATH": str(SOURCE), intake_mode.RELAXED_ENV: mode}
    finished = subprocess.run([sys.executable, "-c", _READ, str(document)], env=environment,
                              capture_output=True, text=True, check=False, timeout=300)
    assert finished.returncode == 0, finished.stderr[-2000:]
    return json.loads(finished.stdout.strip().splitlines()[-1])


def test_a_501_page_pdf_is_refused_by_default_and_read_when_relaxed(tmp_path: Path) -> None:
    """The relaxed path still passes: the same bytes, the same readers, one flag."""
    refused = "1 <= page_count <= 500"
    assert read_501_pages(tmp_path, "0") == {"portal": refused, "comparison": refused}
    assert read_501_pages(tmp_path, "1") == {"portal": 501, "comparison": 501}
