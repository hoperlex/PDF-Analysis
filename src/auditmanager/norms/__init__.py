"""The normative corpus: drawn, dated, attributed, segmented into retrievable chunks."""

from .chunking import DEFAULT_TARGET_CHARACTERS, join_into_chunks
from .degeneracy import DegeneracySignal, DegeneracyVerdict, inspect, is_degenerate
from .model import (
    BlockBody,
    Chunk,
    CorpusTotals,
    Paragraph,
    ParagraphKind,
    SegmentationReport,
    SourceAttribution,
)
from .repair import (
    LEDGER_VERSION,
    PageRepair,
    RepairAttempt,
    RepairLedger,
    RepairOutcome,
    ledger_of,
    repaired_snapshot,
)
from .rerecognition import (
    MAX_ATTEMPTS,
    MINIMUM_REPLACEMENT_CHARACTERS,
    RECOGNITION_SYSTEM_PROMPT,
    PageRecogniser,
    PageToRecognise,
    RecognisedPage,
    rerecognise,
)
from .segmentation import attribution, blocks, drawn_on, recognised_text, segment
from .snapshot import CorpusSnapshot, DocumentFingerprint, derive, fingerprint

__all__ = [
    "LEDGER_VERSION",
    "MAX_ATTEMPTS",
    "MINIMUM_REPLACEMENT_CHARACTERS",
    "RECOGNITION_SYSTEM_PROMPT",
    "BlockBody",
    "Chunk",
    "CorpusSnapshot",
    "CorpusTotals",
    "DEFAULT_TARGET_CHARACTERS",
    "DegeneracySignal",
    "DegeneracyVerdict",
    "DocumentFingerprint",
    "PageRecogniser",
    "PageRepair",
    "PageToRecognise",
    "Paragraph",
    "ParagraphKind",
    "RecognisedPage",
    "RepairAttempt",
    "RepairLedger",
    "RepairOutcome",
    "SegmentationReport",
    "SourceAttribution",
    "attribution",
    "blocks",
    "derive",
    "drawn_on",
    "fingerprint",
    "inspect",
    "is_degenerate",
    "join_into_chunks",
    "ledger_of",
    "recognised_text",
    "repaired_snapshot",
    "rerecognise",
    "segment",
]
