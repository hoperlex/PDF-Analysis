"""Values carried out of the corpus segmentation.

Everything here is frozen and hashable so that a pipeline run can be compared with another
run byte for byte. No value derives anything from a set, a dict ordering or a clock: an
identifier that changes between two runs over the same bytes would make the determinism
proof vacuous rather than failing it.
"""

from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, field


class ParagraphKind(enum.Enum):
    """What the markdown said a paragraph was.

    Kept rather than collapsed into a boolean because a retrieval layer weights a section
    heading differently from a table row, and because dropping headings at segmentation —
    which is what the `R-16` figures imply was done — loses the clause title that names the
    body paragraph underneath it.
    """

    BODY = "body"
    HEADING = "heading"
    TABLE_ROW = "table_row"


class SourceAttribution(enum.Enum):
    """Where a document came from, as the document itself says.

    `R-17` states provenance as one footnote naming one source. That footnote is accurate for
    the 657 documents carrying a ConsultantPlus marker and inaccurate for the other 17, and
    nothing downstream can tell them apart unless the distinction is a field.
    """

    CONSULTANT_PLUS = "consultant_plus"
    UNATTRIBUTED = "unattributed"


@dataclass(frozen=True, slots=True)
class Paragraph:
    """One substantive paragraph of a normative document.

    `char_offset` is an offset into the document's *recognised text* — the concatenation of
    block bodies in block order, defined in `segmentation.recognised_text`. It is deliberately
    an offset into the source rather than into the surviving text: the noise filter is a
    judgement and will be revised, and an offset measured after filtering would silently move
    every anchor in the corpus when it is.
    """

    document_slug: str
    page_label: int
    block_id: str
    ordinal: int
    char_offset: int
    char_length: int
    kind: ParagraphKind
    clause_number: str | None
    text: str

    @property
    def is_numbered_clause(self) -> bool:
        return self.clause_number is not None


@dataclass(frozen=True, slots=True)
class Chunk:
    """One retrieval unit: consecutive paragraphs joined up to a character target.

    A chunk may span a page boundary, and does so often: a norm's clause routinely continues
    across a page break, and the ConsultantPlus export cuts mid-sentence there. `page_first`
    and `page_last` are what the expert is shown — one page crop per page in the span.
    """

    snapshot_id: str
    document_slug: str
    ordinal: int
    page_first: int
    page_last: int
    char_offset: int
    char_length: int
    paragraph_count: int
    clause_numbers: tuple[str, ...]
    text: str

    @property
    def contains_clause(self) -> bool:
        return bool(self.clause_numbers)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SegmentationReport:
    """Counts from one document's parse.

    These are the measurement, not a debug aid: `R-16` quotes a corpus-wide discard rate and
    a substantive-paragraph total, and a later wave has to be able to re-derive both without
    re-reading 5.1 GB by hand.
    """

    document_slug: str
    pages: int
    blocks: int
    recognised_characters: int
    candidates: int
    discarded_publisher_noise: int
    discarded_repeated_offcut: int
    substantive: int
    numbered_clauses: int
    headings: int
    table_rows: int
    substantive_characters: int
    drawn_on: str | None
    attribution: SourceAttribution

    @property
    def discarded(self) -> int:
        return self.discarded_publisher_noise + self.discarded_repeated_offcut


@dataclass(frozen=True, slots=True)
class CorpusTotals:
    """The same counts summed over a corpus. Addition only, so it cannot disagree with the parts."""

    documents: int = 0
    pages: int = 0
    blocks: int = 0
    recognised_characters: int = 0
    candidates: int = 0
    discarded_publisher_noise: int = 0
    discarded_repeated_offcut: int = 0
    substantive: int = 0
    numbered_clauses: int = 0
    headings: int = 0
    table_rows: int = 0
    substantive_characters: int = 0
    chunks: int = 0
    chunk_characters: int = 0
    attribution: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    @property
    def discarded(self) -> int:
        return self.discarded_publisher_noise + self.discarded_repeated_offcut
