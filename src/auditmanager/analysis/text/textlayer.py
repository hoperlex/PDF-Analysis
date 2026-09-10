"""Reading ``prepared.text_layer``, and the one document-global character sequence.

``P02_SEAMS.md`` section 4.1 is the rule this module exists to hold:

* the sequence is every page's text concatenated in ascending page order, with **no
  separator between pages**;
* offsets are **Unicode code points** after the one declared normalization, not bytes
  and not UTF-16 code units;
* the normalization is applied once, by ``source_preparation``. **No later stage
  normalizes again**, so nothing in this package calls ``unicodedata.normalize``.

The corpus is Russian. Every quotation contains non-ASCII characters, so a byte offset
misplaces every anchor while still looking plausible in a test written in English.
In Python ``text[char_start:char_end]`` on the concatenated sequence *is* the
definition, and an ``.encode()`` anywhere near an offset calculation is the bug.

``B2`` owns this artifact; this module only reads it, and fails closed on an
``artifact_version`` it was not written against rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping, Sequence

from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.shared.errors import DomainError, ErrorCode

ARTIFACT_ROLE: Final[str] = "prepared.text_layer"
SUPPORTED_ARTIFACT_VERSION: Final[str] = "1.0.0"


def _invalid(reason: str, message: str) -> DomainError:
    """A refusal of a stage input. Carries no document text and no path."""
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message=message,
        stage_id=STAGE_ID,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class Page:
    """One page's slice of the document-global sequence."""

    page_number: int
    char_start: int
    char_end: int
    text: str

    def contains(self, char_start: int, char_end: int) -> bool:
        """Whether a document-global interval lies wholly inside this page."""
        return self.char_start <= char_start and char_end <= self.char_end


@dataclass(frozen=True, slots=True)
class TextLayer:
    """A validated ``prepared.text_layer`` plus its document-global sequence."""

    version_uid: str
    normalization_id: str
    pages: tuple[Page, ...]
    document_text: str

    @property
    def page_numbers(self) -> tuple[int, ...]:
        return tuple(page.page_number for page in self.pages)

    @property
    def total_char_count(self) -> int:
        return len(self.document_text)

    def page(self, page_number: int) -> Page | None:
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def slice(self, char_start: int, char_end: int) -> str:
        """The document-global slice. The definition of an offset, in one place."""
        return self.document_text[char_start:char_end]


def load_text_layer(document: Mapping[str, Any]) -> TextLayer:
    """Validate ``prepared.text_layer`` and build the document-global sequence.

    Every invariant section 4.3 lets a consumer rely on is checked here rather than
    assumed, because an offset computed against a text layer that violates one of them
    is wrong in a way no later test detects: it still resolves, just to the wrong span.
    """
    role = document.get("artifact_role")
    if role != ARTIFACT_ROLE:
        raise _invalid("artifact_role_unexpected", "the stage input is not a text layer artifact")
    version = document.get("artifact_version")
    if version != SUPPORTED_ARTIFACT_VERSION:
        # Fail closed on an unexpected artifact_version; never guess.
        raise _invalid(
            "artifact_version_unsupported",
            "the text layer artifact declares a version this stage was not written against",
        )

    normalization = document.get("normalization") or {}
    normalization_id = normalization.get("id")
    if not isinstance(normalization_id, str) or not normalization_id:
        raise _invalid("normalization_undeclared", "the text layer declares no normalization")

    raw_pages: Sequence[Mapping[str, Any]] = document.get("pages") or ()
    if not raw_pages:
        raise _invalid("text_layer_empty", "the text layer carries no pages")

    pages: list[Page] = []
    expected_start = 0
    previous_number: int | None = None
    for raw in raw_pages:
        page = Page(
            page_number=int(raw["page_number"]),
            char_start=int(raw["char_start"]),
            char_end=int(raw["char_end"]),
            text=str(raw["text"]),
        )
        if previous_number is not None and page.page_number != previous_number + 1:
            raise _invalid(
                "page_sequence_broken", "text layer pages are not contiguous and gapless"
            )
        if page.char_start != expected_start:
            raise _invalid(
                "page_offsets_discontiguous",
                "a text layer page does not begin where the previous page ended",
            )
        if page.char_end - page.char_start != len(page.text):
            # len() counts code points. This is the check that catches a producer
            # that measured its own spans in bytes.
            raise _invalid(
                "page_span_length_mismatch",
                "a text layer page span does not match its text length in code points",
            )
        pages.append(page)
        previous_number = page.page_number
        expected_start = page.char_end

    if pages[0].char_start != 0:
        raise _invalid("page_offsets_discontiguous", "the first text layer page does not start at zero")

    declared_total = document.get("total_char_count")
    if declared_total is not None and int(declared_total) != expected_start:
        raise _invalid(
            "total_char_count_mismatch",
            "the declared total character count disagrees with the page spans",
        )

    return TextLayer(
        version_uid=str(document.get("version_uid", "")),
        normalization_id=normalization_id,
        pages=tuple(pages),
        # No separator. Section 4.1 is explicit, and a newline here would shift every
        # anchor after page one by the number of pages before it.
        document_text="".join(page.text for page in pages),
    )
