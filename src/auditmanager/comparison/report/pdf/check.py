"""The check of a written PDF (`CMP-VC-REPORT-01`).

The original checks its PDF with PyMuPDF (``md_report/pdf.py:349-418``, ``:600-681``); PyMuPDF is AGPL and ``OD-01`` excludes it, so this port
reads the file with ``pypdf`` (BSD, pinned in ``pyproject.toml``). What is checked is what the original checked and the contract adds: A4
portrait, the Cyrillic font **embedded**, every page carries the label that the text is model output not confirmed by an engineer and the
recall line, every transition of the report is in the text, no service markup or identifier is in the text, no replacement character. A report
whose PDF does not pass is failed with ``pdf_check_failed``; the file is not stored.
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence
from typing import Any, Final

from pypdf import PdfReader

__all__ = ["check_pdf"]

#: Service markers that must not reach a person (pdf.py:399-411, :593-597), checked for both kinds.
_MARKERS: Final[tuple[str, ...]] = ("**", "<b>", "</", "```", '{"', "md_from", "claim_id", "transition_id")
_CLIENT_FORBIDDEN: Final[tuple[str, ...]] = (
    r"\b[ФF]\d{4}\b", r"Реестр", r"Приложение", r"\.md\b", r"gpt-|codex|Sol\b", r"стр\. PDF", r"md_from", r"\bT\d{2}\b", r"claim",
    r"и ещё \d",
)
_A4 = (595.3, 841.9)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def check_pdf(
    content: bytes, *, label: str, recall: str, transitions: Sequence[str], client: bool, code: str,
) -> dict[str, Any]:
    """``{"ok", "problems", "pages"}``; ``problems`` are plain sentences, never page content beyond the checked words."""
    problems: list[str] = []
    reader = PdfReader(io.BytesIO(content))
    pages = len(reader.pages)
    text_all = ""
    for number, page in enumerate(reader.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if abs(width - _A4[0]) > 2 or abs(height - _A4[1]) > 2:
            problems.append(f"page {number}: not A4 portrait ({width:.0f}x{height:.0f})")
        text = page.extract_text() or ""
        text_all += text + "\n"
        flat = _squash(text)
        if _squash(label) not in flat:
            problems.append(f"page {number}: the unconfirmed-by-an-engineer label is missing")
        if _squash(recall) not in flat:
            problems.append(f"page {number}: the recall line is missing")
        if len(text.strip()) < 40:
            problems.append(f"page {number}: almost empty")
    if b"/FontFile2" not in content:
        problems.append("the Cyrillic font is not embedded")
    flat_all = _squash(text_all)
    for item in transitions:
        if _squash(item) not in flat_all:
            problems.append(f"the transition {item} is not in the text of the PDF")
    for marker in _MARKERS:
        if marker in text_all:
            problems.append(f"service markup or identifier in the text of the PDF: «{marker}»")
    if client:
        for pattern in _CLIENT_FORBIDDEN:
            found = re.search(pattern, text_all)
            if found:
                problems.append(f"a service word in the PDF for the customer: «{found.group(0)}»")
    if "⁇" in text_all or "�" in text_all:
        problems.append("a replacement character in the text (an unreadable letter)")
    if code and _squash(code) not in flat_all:
        problems.append("the cipher is not in the text of the PDF")
    return {"ok": not problems, "problems": problems, "pages": pages}
