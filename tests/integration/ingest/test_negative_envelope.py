"""Every out-of-envelope input is refused by the rule it breaks, and publishes nothing.

Each fixture in ``fixtures/synthetic/ar/negative`` violates exactly one rule, so these
tests assert the *specific* ``constraint`` rather than merely that something failed. A
test that only asserted ``validation_failed`` would pass against a probe that rejected
everything for the wrong reason.

"Nothing was published" is proved from outside the code under test: the bucket is read
with a plain boto3 client and the tables are counted with raw SQL.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.ingest import MAX_BYTES, MAX_PAGES, MIN_PAGES
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message

#: fixture name -> (field, constraint) the probe must attribute the refusal to.
NEGATIVE_CASES = [
    ("not_a_pdf.txt", "content", "pdf_magic_bytes"),
    ("companion_archive.zip", "content", "pdf_magic_bytes"),
    ("oversize.pdf", "content", f"byte_size <= {MAX_BYTES}"),
    ("encrypted.pdf", "content", "not_encrypted"),
    ("too_many_pages.pdf", "page_count", f"{MIN_PAGES} <= page_count <= {MAX_PAGES}"),
    ("image_only.pdf", "page_text", "every_page_has_extractable_text"),
]


def counts(engine) -> dict[str, int]:
    tables = (
        "project",
        "document",
        "document_version",
        "input_manifest_entry",
        "blob",
        "command_record",
    )
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"SELECT count(*) FROM {table}")  # noqa: S608 - fixed table names
            ).scalar_one()
            for table in tables
        }


@pytest.mark.parametrize(("fixture", "field", "constraint"), NEGATIVE_CASES)
def test_negative_fixture_is_refused_by_its_own_rule_and_publishes_nothing(
    service, project, negative_pdf, key, engine, bucket_keys, fixture, field, constraint
) -> None:
    before_keys = set(bucket_keys())
    before_counts = counts(engine)
    assert before_counts["project"] == 1, "the project fixture should be the only row"

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=negative_pdf(fixture),
            source_filename=fixture,
            display_title="Rejected upload",
            idempotency_key=key("negative"),
        )

    failure = raised.value
    envelope = failure.envelope("corr_negative_case")

    # Refused by the rule it violates, not merely refused.
    assert failure.code is ErrorCode.VALIDATION_FAILED
    assert envelope.details["field"] == field
    assert envelope.details["constraint"] == constraint

    # `retryable` is pinned by the catalog, never by this slice.
    assert envelope.retryable is False
    assert envelope.http_status == 422

    # The refusal never echoes the input. The fixture name is a file name, which the
    # contract lists among the values that are never identities.
    screen_message(envelope.message)
    assert fixture not in envelope.message
    assert fixture not in str(envelope.details)

    # Nothing was created anywhere: no canonical object, no temporary residue, and no
    # row in any table this command writes -- including no command record, because the
    # probe answers before the key is claimed.
    assert set(bucket_keys()) == before_keys
    assert counts(engine) == before_counts


def test_empty_payload_is_refused(service, project, key, engine, bucket_keys) -> None:
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=b"",
            source_filename="empty.pdf",
            display_title="Empty",
            idempotency_key=key("empty"),
        )
    envelope = raised.value.envelope("corr_empty")
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert envelope.details == {"field": "content", "constraint": "non_empty"}
    assert set(bucket_keys()) == before
    assert counts(engine)["blob"] == 0


#: name -> the rule that must refuse it. The constraint is part of the case, not an
#: afterthought: asserting only ``field == "source_filename"`` passes whichever of the three
#: name rules fired, which is how deleting the ``non_empty`` check survived a mutation sweep
#: -- a blank name still reached ``plain_base_name``, because the pattern requires at least
#: one character, and the test could not tell the two answers apart.
TRAVERSAL_CASES = [
    ("../../etc/passwd", "plain_base_name"),
    ("nested/report.pdf", "plain_base_name"),
    ("back\\slash.pdf", "plain_base_name"),
    ("..", "plain_base_name"),
    ("   ", "non_empty"),
]


@pytest.mark.parametrize(("source_filename", "constraint"), TRAVERSAL_CASES)
def test_traversal_shaped_file_names_are_refused_without_being_echoed(
    service, project, baseline_pdf, key, engine, bucket_keys, source_filename, constraint
) -> None:
    """``GJ-01-FC-03``. The name is refused by its own rule and never appears in the answer."""
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=source_filename,
            display_title="Traversal attempt",
            idempotency_key=key("traversal"),
        )

    envelope = raised.value.envelope("corr_traversal")
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert envelope.details["field"] == "source_filename"
    assert envelope.details["constraint"] == constraint, (
        "the refusal names a different rule than the one this name breaks; field alone "
        f"does not distinguish them: {envelope.details}"
    )
    screen_message(envelope.message)
    if source_filename.strip():
        assert source_filename.strip() not in envelope.message
    assert set(bucket_keys()) == before
    assert counts(engine)["blob"] == 0


def test_probe_runs_before_the_target_is_even_looked_up(
    service, negative_pdf, key, engine, bucket_keys
) -> None:
    """A bad payload aimed at a project that does not exist is a payload refusal.

    This is what "before any publication" means concretely: the envelope is answered
    before the command touches the database at all, so the refusal cannot depend on
    anything having been read, locked or claimed.
    """
    from auditmanager.shared.identity import ProjectUid

    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=ProjectUid.new(),
            content=negative_pdf("image_only.pdf"),
            source_filename="image_only.pdf",
            display_title="Nowhere",
            idempotency_key=key("nowhere"),
        )

    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert raised.value.envelope("c").details["field"] == "page_text"
    assert set(bucket_keys()) == before
    assert counts(engine)["command_record"] == 0


def test_no_ocr_path_exists_for_a_page_without_text(
    service, project, negative_pdf, key
) -> None:
    """The image-only document is a refusal, never a different extraction path.

    Asserted at the source as well as at the boundary: no module in this slice imports
    or names an OCR engine, so there is nothing for a later change to switch on.
    """
    from pathlib import Path

    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=negative_pdf("image_only.pdf"),
            source_filename="image_only.pdf",
            display_title="Scanned",
            idempotency_key=key("ocr"),
        )
    assert raised.value.envelope("c").details["constraint"] == (
        "every_page_has_extractable_text"
    )

    root = Path(__file__).resolve().parents[3] / "src" / "auditmanager"
    banned = ("pytesseract", "tesseract", "easyocr", "paddleocr", "ocrmypdf")
    for module in sorted((root / "ingest").rglob("*.py")) + sorted(
        (root / "documents").rglob("*.py")
    ):
        body = module.read_text(encoding="utf-8").lower()
        for name in banned:
            # The prose in envelope.py says the word OCR; an *import* of one is what
            # would matter, so this looks for the engines by name.
            assert name not in body, f"{module.name} names an OCR engine: {name}"
