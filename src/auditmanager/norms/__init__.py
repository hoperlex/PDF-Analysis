"""The normative corpus: drawn, dated, attributed, segmented into retrievable chunks."""

from .chunking import DEFAULT_TARGET_CHARACTERS, join_into_chunks
from .model import (
    Chunk,
    CorpusTotals,
    Paragraph,
    ParagraphKind,
    SegmentationReport,
    SourceAttribution,
)
from .segmentation import attribution, drawn_on, recognised_text, segment
from .snapshot import CorpusSnapshot, DocumentFingerprint, derive, fingerprint

__all__ = [
    "Chunk",
    "CorpusSnapshot",
    "CorpusTotals",
    "DEFAULT_TARGET_CHARACTERS",
    "DocumentFingerprint",
    "Paragraph",
    "ParagraphKind",
    "SegmentationReport",
    "SourceAttribution",
    "attribution",
    "derive",
    "drawn_on",
    "fingerprint",
    "join_into_chunks",
    "recognised_text",
    "segment",
]
