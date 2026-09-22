"""The only module in this context that touches a filesystem.

The corpus is a read-only drop of 674 directories, ~5.1 GB, that `.gitignore` excludes — no
commit, diff or `git status` shows it, and a fresh clone does not have it. So its location is
not a repository path and is not inferred from `__file__`: it is passed in, and a caller that
does not know where the drop is gets an explicit refusal rather than an empty corpus.

Nothing here opens a file for writing. The drop is evidence; segmentation is a projection of
it and never writes back.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .model import Chunk, CorpusTotals, Paragraph, SegmentationReport
from .chunking import DEFAULT_TARGET_CHARACTERS, join_into_chunks
from .segmentation import drawn_on, segment
from .snapshot import CorpusSnapshot, DocumentFingerprint, derive, fingerprint

RESULTS_FILENAME = "results.md"
BLOCKS_FILENAME = "blocks.json"


class CorpusUnavailable(RuntimeError):
    """The corpus directory is absent or does not look like a corpus.

    Explicit and loud: a silent fallback to zero documents would make every figure in a report
    a true statement about an empty set (`AGENTS.md` §4).
    """


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    slug: str
    source_document_id: str
    markdown: str
    results_bytes: bytes


def document_directories(root: Path) -> tuple[Path, ...]:
    """Every document directory under the corpus root, in a fixed order.

    Sorted, because a filesystem walk has no guaranteed order and the snapshot digest and the
    chunk ordinals both depend on this sequence.
    """
    if not root.is_dir():
        raise CorpusUnavailable(f"corpus root is not a directory: {root}")
    found = sorted(
        (path for path in root.iterdir() if path.is_dir() and (path / RESULTS_FILENAME).is_file()),
        key=lambda path: path.name,
    )
    if not found:
        raise CorpusUnavailable(f"corpus root holds no document directories: {root}")
    return tuple(found)


def read_document(directory: Path) -> CorpusDocument:
    results = directory / RESULTS_FILENAME
    raw = results.read_bytes()
    source_document_id = ""
    blocks = directory / BLOCKS_FILENAME
    if blocks.is_file():
        source_document_id = str(json.loads(blocks.read_text(encoding="utf-8")).get("document_id", ""))
    return CorpusDocument(
        slug=directory.name,
        source_document_id=source_document_id,
        markdown=raw.decode("utf-8"),
        results_bytes=raw,
    )


def snapshot_of(root: Path) -> CorpusSnapshot:
    """Derive the snapshot identifier of the corpus at `root`."""
    fingerprints: list[DocumentFingerprint] = []
    for directory in document_directories(root):
        document = read_document(directory)
        fingerprints.append(
            fingerprint(
                slug=document.slug,
                source_document_id=document.source_document_id,
                results_md=document.results_bytes,
                drawn_on=drawn_on(document.markdown),
            )
        )
    return derive(fingerprints)


def segment_corpus(
    root: Path,
    snapshot_id: str,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
) -> Iterator[tuple[SegmentationReport, tuple[Paragraph, ...], tuple[Chunk, ...]]]:
    """Segment every document under `root`, in document-directory order."""
    for directory in document_directories(root):
        document = read_document(directory)
        paragraphs, report = segment(document.slug, document.markdown)
        chunks = join_into_chunks(paragraphs, snapshot_id, target_characters)
        yield report, paragraphs, chunks


def totals(reports_and_chunks: Iterator[tuple[SegmentationReport, tuple[Paragraph, ...], tuple[Chunk, ...]]]) -> CorpusTotals:
    """Sum a corpus run. Addition only: a total here cannot disagree with its parts."""
    accumulated = {
        "documents": 0, "page_headings": 0, "blocks": 0, "recognised_characters": 0, "candidates": 0,
        "discarded_publisher_noise": 0, "discarded_repeated_offcut": 0, "substantive": 0,
        "numbered_clauses": 0, "headings": 0, "table_rows": 0, "substantive_characters": 0,
        "chunks": 0, "chunk_characters": 0,
    }
    attribution: dict[str, int] = {}
    for report, _paragraphs, chunks in reports_and_chunks:
        accumulated["documents"] += 1
        for name in (
            "page_headings", "blocks", "recognised_characters", "candidates",
            "discarded_publisher_noise", "discarded_repeated_offcut", "substantive",
            "numbered_clauses", "headings", "table_rows", "substantive_characters",
        ):
            accumulated[name] += getattr(report, name)
        accumulated["chunks"] += len(chunks)
        accumulated["chunk_characters"] += sum(len(chunk.text) for chunk in chunks)
        key = report.attribution.value
        attribution[key] = attribution.get(key, 0) + 1
    return CorpusTotals(attribution=tuple(sorted(attribution.items())), **accumulated)
