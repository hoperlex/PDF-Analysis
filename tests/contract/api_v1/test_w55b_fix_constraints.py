"""Every constraint the upload envelope raises is registered, and every one registered is raised.

`W55B-FIX`. `W55B-JUDGE-Y` Y-4: ingest raised three constraints for the PDF member and the
upload's name -- ``parseable_pdf``, ``non_empty``, ``plain_base_name`` -- that the catalogue
note of ``contracts/domain/v1/error-codes.json`` did not name. The repairs of `W55B-FIX` add
four more: ``blocks_count`` (X-4), ``pdf_page_content``, ``pdf_document_content`` and
``pdf_reader_limits`` (X-1). Each is checked both ways:

* the catalogue note of ``validation_failed`` names it as a word;
* a module of ``auditmanager.ingest`` raises it -- its name is a string literal there,
  written once, which is how every refusal of the envelope is made.

The list is written out, not read from either side, so removing a constraint from the note or
from the code is a red here and not a quiet agreement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ERRORS = json.loads((ROOT / "contracts/domain/v1/error-codes.json").read_text(encoding="utf-8"))
INGEST = ROOT / "src" / "auditmanager" / "ingest"

#: (constraint, the field it is answered under).
FIX_CONSTRAINTS = (
    ("parseable_pdf", "content"),
    ("non_empty", "content"),
    ("plain_base_name", "source_filename"),
    ("blocks_count", "file"),
    ("pdf_page_content", "content"),
    ("pdf_document_content", "content"),
    ("pdf_reader_limits", "content"),
)


def _notes() -> str:
    return " ".join(ERRORS["codes"]["validation_failed"]["notes"])


def _ingest_sources() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(INGEST.glob("*.py")))


@pytest.mark.parametrize(("constraint", "field"), FIX_CONSTRAINTS, ids=[c for c, _ in FIX_CONSTRAINTS])
def test_the_constraint_is_registered_in_the_catalogue_note(constraint: str, field: str) -> None:
    assert re.search(rf"\b{constraint}\b", _notes()), constraint
    assert re.search(rf"\b{field}\b", _notes()), field


@pytest.mark.parametrize(("constraint", "field"), FIX_CONSTRAINTS, ids=[c for c, _ in FIX_CONSTRAINTS])
def test_the_constraint_is_raised_by_the_upload_envelope(constraint: str, field: str) -> None:
    assert f'"{constraint}"' in _ingest_sources(), f"no module of auditmanager.ingest raises {constraint}"


def test_the_ceilings_the_note_states_are_the_codes() -> None:
    """The note states the ceilings in prose; the figures there are the product's."""
    from auditmanager.ingest import bundle_envelope, envelope

    notes = _notes()
    for figure in (
        f"more than {bundle_envelope.MAX_BLOCKS_PER_PAGE} blocks on one page",
        "more than 3 000 in all",
        "more than 1 000 IMAGE blocks",
        "more than 400 000 drawing elements",
        "more than 200 000 characters",
        "more than 8 000 000 drawing elements or 20 000 000 characters in all",
        "512 MiB of address space or 60 s",
    ):
        assert figure in notes, figure
    assert (bundle_envelope.MAX_BLOCKS, bundle_envelope.MAX_IMAGE_BLOCKS) == (3_000, 1_000)
    assert (envelope.PAGE_ELEMENTS_MAX, envelope.PAGE_CHARACTERS_MAX) == (400_000, 200_000)
    assert (envelope.DOCUMENT_ELEMENTS_MAX, envelope.DOCUMENT_CHARACTERS_MAX) == (8_000_000, 20_000_000)
    assert (envelope.READER_ADDRESS_SPACE, envelope.READER_SECONDS) == (512 * 1024 * 1024, 60)
