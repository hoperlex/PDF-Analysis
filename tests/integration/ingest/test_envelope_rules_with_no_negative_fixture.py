"""Three envelope rules that no test could redden, found by sweeping the whole surface.

`W6-CERT` observed that emptying ``PDF_MAGIC`` left criterion 10 green. Checking it first
showed that was not a gap: ``tests/integration/ingest`` reddens on both of its cases, and
the e2e suite staying green is the division of labour working -- the journey test checks the
journey, the rule test checks the rule.

But the question it raised was worth asking of every rule rather than that one, so each
constant and branch in ``ingest/envelope.py`` was mutated in turn against both suites.
Three survived with nothing red:

* ``MIN_PAGES 1 -> 0`` -- no test offers a document with no pages at all;
* ``MAX_SOURCE_FILENAME 255 -> 100000`` -- no test offers an over-long name;
* deleting the ``non_empty`` file-name check entirely -- no test offers a blank name.

All three are on the criterion-10 surface, which `PROTOTYPE_PROFILE.md` §8 certifies as
unsupported input being "shown explicitly with no fallback". Each is reachable through the
twelve operations: a name is a caller-supplied string, and a PDF with no pages is 311 bytes.

The fourth finding is why the file-name rules survived at all. The traversal test asserts
``details["field"] == "source_filename"`` and stops there, so it passes whichever of the
three name rules fired. Field is not reason; these assert the ``constraint``.
"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.errors.envelope import screen_message

from tests.integration.ingest.test_negative_envelope import counts  # type: ignore[import-not-found]

#: Pinned as literals, deliberately, and this is the second finding of the wave.
#:
#: The first version of these tests imported ``MIN_PAGES`` and ``MAX_SOURCE_FILENAME`` and
#: built the expected constraint from them. Both sides of the comparison then moved together
#: under mutation: raising ``MAX_SOURCE_FILENAME`` to 100000 also lengthened the name the
#: test sent, so it was still refused and the test still passed. The assertion was derived
#: from the thing it was meant to check.
#:
#: The independent authority is the schema, which the module's own comment cites:
#: ``ck_document_version_page_count CHECK (page_count BETWEEN 1 AND 30)``. A change to the
#: envelope constant that does not also change the migration is a disagreement worth a red
#: test, and literals are what make that visible.
PAGE_COUNT_CONSTRAINT = "1 <= page_count <= 30"
FILENAME_LIMIT = 255
FILENAME_CONSTRAINT = f"char_length <= {FILENAME_LIMIT}"


def _pdf_with_no_pages() -> bytes:
    """A real PDF carrying zero pages. `pypdf` writes one in 311 bytes.

    Built rather than committed as a fixture: `build_pc02_corpus.py` fixes the negative
    set at 2-4 documents and the AR corpus is frozen evidence, so adding bytes to either
    would invalidate a measurement already taken. A test can make its own bytes.
    """
    writer = PdfWriter()
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _refusal(raised: pytest.ExceptionInfo[DomainError]) -> dict:
    return dict(raised.value.envelope("corr_envelope_rule").details)


def test_the_case_really_does_discriminate(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    """The precondition: the same call succeeds with a good document and a plain name.

    Without it, every refusal below could be caused by a broken fixture and would still
    look like the rule working.
    """
    published = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename="baseline.pdf",
        display_title="Admissible",
        idempotency_key=key("envelope-rule-control"),
    )
    assert published is not None


def test_a_pdf_with_no_pages_is_refused_by_the_page_count_rule(
    service, project, key, engine, bucket_keys
) -> None:
    """``MIN_PAGES`` exists for this and nothing exercised it.

    The upper bound has a fixture (`too_many_pages.pdf`); the lower bound had none, so
    lowering `MIN_PAGES` to 0 changed no test's answer.
    """
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=_pdf_with_no_pages(),
            source_filename="no-pages.pdf",
            display_title="No pages",
            idempotency_key=key("no-pages"),
        )

    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert _refusal(raised) == {
        "field": "page_count",
        "constraint": PAGE_COUNT_CONSTRAINT,
    }
    assert set(bucket_keys()) == before
    assert counts(engine)["blob"] == 0, "a refused document left a blob behind"


def test_a_blank_source_file_name_is_refused_as_non_empty(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    """Deleting this check entirely reddened nothing, because no test sent a blank name."""
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename="   ",
            display_title="Blank name",
            idempotency_key=key("blank-name"),
        )

    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert _refusal(raised) == {"field": "source_filename", "constraint": "non_empty"}
    assert set(bucket_keys()) == before
    assert counts(engine)["blob"] == 0


def test_an_over_long_source_file_name_is_refused_by_its_own_length_rule(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    """One character past the limit, so the boundary itself is what is being read.

    A name of some arbitrary huge length would also be refused by `plain_base_name` if the
    padding happened to contain a separator. The name here is a plain base name in every
    other respect, so only the length rule can refuse it.
    """
    name = "a" * (FILENAME_LIMIT + 1 - len(".pdf")) + ".pdf"
    assert len(name) == FILENAME_LIMIT + 1
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=project.project_uid,
            content=baseline_pdf,
            source_filename=name,
            display_title="Long name",
            idempotency_key=key("long-name"),
        )

    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert _refusal(raised) == {
        "field": "source_filename",
        "constraint": FILENAME_CONSTRAINT,
    }
    # The rejected name must not be echoed back, and the message must survive the same
    # screen every caller-visible message does -- a 256-character name is exactly the kind
    # of caller input that ends up quoted into a message by accident.
    message = raised.value.envelope("corr_long_name").message
    screen_message(message)
    assert name not in message
    assert set(bucket_keys()) == before
    assert counts(engine)["blob"] == 0


def test_a_name_at_the_limit_is_accepted(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    """The other side of the boundary, so the rule is a limit and not a prohibition.

    Without this, `char_length <= 255` could be implemented as `< 255`, or as refusing any
    name over some smaller number, and the test above would not notice.
    """
    name = "a" * (FILENAME_LIMIT - len(".pdf")) + ".pdf"
    assert len(name) == FILENAME_LIMIT
    published = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=baseline_pdf,
        source_filename=name,
        display_title="Name at the limit",
        idempotency_key=key("name-at-limit"),
    )
    assert published is not None
