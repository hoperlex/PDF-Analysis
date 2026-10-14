"""The PDF member's name carries no control or format character to the screen (`W55B-FIX`, X-10).

`W55B-JUDGE-X` X-10: the version's ``source_filename`` -- and the document's title when the
upload names none -- comes from the PDF member's name, or from the Info-ZIP Unicode Path
field, which an archive may set to any text. Only C0 and DEL were replaced, so a
right-to-left override (U+202E) reached the title and reversed the extension a reader saw.
Every ``Cc`` and ``Cf`` code point now becomes ``_``.

Each case runs the archive reader on a real archive, so the name is the one the product
decoded, and the scrub is :func:`~auditmanager.ingest.bundle_members.source_filename_of`'s.
The module needs no database.
"""

from __future__ import annotations

import io
import unicodedata

import pytest

from auditmanager.ingest.bundle_archive import extract_bundle
from auditmanager.ingest.bundle_members import source_filename_of
from portal_bundle import archive_negatives as an  # tools/fixtures, on the path via conftest
from portal_bundle import zipwrite


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


def _shown(stem: str) -> str:
    data = zipwrite.build_zip(an.members(stem=stem))
    with extract_bundle(io.BytesIO(data)) as bundle:
        return source_filename_of(bundle)


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("отчёт‮fdp.exe", "отчёт_fdp.exe.pdf"),          # RIGHT-TO-LEFT OVERRIDE (Cf)
        ("a⁦b⁩c", "a_b_c.pdf"),                       # an isolate and its end (Cf)
        ("a​b﻿c", "a_b_c.pdf"),                       # zero width space, BOM (Cf)
        ("a\u0085b\u009fc", "a_b_c.pdf"),                       # C1 controls (Cc)
        ("ba\x01d", "ba_d.pdf"),                                # C0, as before
        ("Проект_АР", "Проект_АР.pdf"),                         # nothing to scrub
    ],
)
def test_no_control_or_format_character_reaches_the_display_name(stem: str, expected: str) -> None:
    shown = _shown(stem)
    assert shown == expected
    assert not [ch for ch in shown if unicodedata.category(ch) in ("Cc", "Cf")]
