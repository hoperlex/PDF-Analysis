"""The only module in this context that touches a filesystem.

The corpus is a read-only drop of 674 directories, ~5.1 GB, that `.gitignore` excludes — no
commit, diff or `git status` shows it, and a fresh clone does not have it. So its location is
not a repository path and is not inferred from `__file__`: it is passed in, and a caller that
does not know where the drop is gets an explicit refusal rather than an empty corpus.

Nothing here opens a file for writing. The drop is evidence; segmentation is a projection of
it and never writes back.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from .model import BlockBody, Chunk, CorpusTotals, Paragraph, SegmentationReport
from .chunking import DEFAULT_TARGET_CHARACTERS, join_into_chunks
from .degeneracy import is_degenerate
from .repair import RepairLedger, RepairOutcome, repaired_snapshot
from .rerecognition import PageToRecognise
from .segmentation import blocks, drawn_on, segment
from .snapshot import CorpusSnapshot, DocumentFingerprint, derive, fingerprint

RESULTS_FILENAME = "results.md"
BLOCKS_FILENAME = "blocks.json"
MANIFEST_FILENAME = "MANIFEST.json"


class CorpusUnavailable(RuntimeError):
    """The corpus directory is absent or does not look like a corpus.

    Explicit and loud: a silent fallback to zero documents would make every figure in a report
    a true statement about an empty set (`AGENTS.md` §4).
    """


class RepairProjectionMismatch(ValueError):
    """A repair ledger cannot be applied exactly to the corpus bytes it names."""


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    slug: str
    source_document_id: str
    markdown: str
    results_bytes: bytes


@dataclass(frozen=True, slots=True)
class CorpusManifestDocument:
    """Strict loader metadata from the drop's root manifest."""

    slug: str
    source_document_ref: str
    title: str
    doc_type: str
    pdf_page_count: int
    block_count: int


@dataclass(frozen=True, slots=True)
class ProjectedCorpusDocument:
    """One validated document ready for a transaction-scoped repository."""

    metadata: CorpusManifestDocument
    report: SegmentationReport
    paragraphs: tuple[Paragraph, ...]
    chunks: tuple[Chunk, ...]


@dataclass(frozen=True, slots=True)
class CorpusProjection:
    """A re-iterable, prevalidated view over one effective corpus snapshot."""

    root: Path
    snapshot: CorpusSnapshot
    base_content_key: str
    repair_count: int
    target_characters: int
    documents: tuple[tuple[Path, CorpusManifestDocument], ...]
    base_fingerprints: tuple[DocumentFingerprint, ...]
    replacements_by_document: Mapping[str, Mapping[str, str]]

    def iter_documents(self) -> Iterator[ProjectedCorpusDocument]:
        for (directory, metadata), expected in zip(
            self.documents, self.base_fingerprints, strict=True
        ):
            document = read_document(directory)
            _verify_fingerprint(document, expected)
            if document.source_document_id != metadata.source_document_ref:
                raise CorpusUnavailable(
                    f"{metadata.slug}: manifest source reference "
                    f"{metadata.source_document_ref!r} != blocks.json "
                    f"{document.source_document_id!r}"
                )
            paragraphs, report = segment(
                document.slug,
                document.markdown,
                replacements=self.replacements_by_document.get(document.slug),
            )
            if report.blocks != metadata.block_count:
                raise CorpusUnavailable(
                    f"{metadata.slug}: manifest block count {metadata.block_count} "
                    f"!= parsed {report.blocks}"
                )
            if report.page_headings > metadata.pdf_page_count:
                raise CorpusUnavailable(
                    f"{metadata.slug}: parsed {report.page_headings} page headings "
                    f"exceed manifest PDF page count {metadata.pdf_page_count}"
                )
            chunks = join_into_chunks(
                paragraphs, self.snapshot.content_key, self.target_characters
            )
            yield ProjectedCorpusDocument(metadata, report, paragraphs, chunks)



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


def _snapshot_with_fingerprints(
    directories: tuple[Path, ...],
) -> tuple[CorpusSnapshot, tuple[DocumentFingerprint, ...]]:
    fingerprints: list[DocumentFingerprint] = []
    for directory in directories:
        document = read_document(directory)
        fingerprints.append(
            fingerprint(
                slug=document.slug,
                source_document_id=document.source_document_id,
                results_md=document.results_bytes,
                drawn_on=drawn_on(document.markdown),
            )
        )
    return derive(fingerprints), tuple(fingerprints)


def _verify_fingerprint(document: CorpusDocument, expected: DocumentFingerprint) -> None:
    actual = fingerprint(
        slug=document.slug,
        source_document_id=document.source_document_id,
        results_md=document.results_bytes,
        drawn_on=drawn_on(document.markdown),
    )
    if actual != expected:
        raise CorpusUnavailable(f"{document.slug}: source changed since snapshot was derived")


def snapshot_of(root: Path) -> CorpusSnapshot:
    """Derive the snapshot identifier of the corpus at `root`."""
    snapshot, _fingerprints = _snapshot_with_fingerprints(document_directories(root))
    return snapshot


def segment_corpus(
    root: Path,
    snapshot_id: str,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    *,
    repair_ledger: RepairLedger | None = None,
) -> Iterator[tuple[SegmentationReport, tuple[Paragraph, ...], tuple[Chunk, ...]]]:
    """Segment every document under ``root`` under one verified text identity.

    The supplied snapshot identifier is checked against the source bytes before the first
    document is yielded, and each document's fingerprint is checked again when it is read
    for projection. When a repair ledger is present, every ledger row is also checked
    against the raw block's key, page, character count and SHA-256 before any replacement
    is made. A partially applicable ledger is refused rather than projected partly.
    """
    directories = document_directories(root)
    base_snapshot, fingerprints = _snapshot_with_fingerprints(directories)
    effective_snapshot = (
        base_snapshot
        if repair_ledger is None
        else repaired_snapshot(base_snapshot, repair_ledger)
    )
    if snapshot_id != effective_snapshot.snapshot_id:
        raise RepairProjectionMismatch(
            f"projection snapshot {snapshot_id!r} does not identify the effective corpus "
            f"{effective_snapshot.snapshot_id!r}"
        )

    replacements_by_document = _validated_replacements(root, repair_ledger)
    for directory, expected in zip(directories, fingerprints, strict=True):
        document = read_document(directory)
        _verify_fingerprint(document, expected)
        paragraphs, report = segment(
            document.slug,
            document.markdown,
            replacements=replacements_by_document.get(document.slug),
        )
        chunks = join_into_chunks(paragraphs, snapshot_id, target_characters)
        yield report, paragraphs, chunks


def _validated_replacements(
    root: Path, repair_ledger: RepairLedger | None
) -> dict[str, dict[str, str]]:
    """Return applied replacements only after every ledger row matches its source block."""
    if repair_ledger is None:
        return {}

    directories = {directory.name: directory for directory in document_directories(root)}
    source_blocks: dict[str, dict[str, BlockBody]] = {}
    replacements: dict[str, dict[str, str]] = {}

    for repair in repair_ledger.repairs:
        directory = directories.get(repair.document_slug)
        if directory is None:
            raise RepairProjectionMismatch(
                f"repair names document absent from the corpus: {repair.document_slug}"
            )
        if repair.document_slug not in source_blocks:
            document = read_document(directory)
            source_blocks[repair.document_slug] = {
                block.block_id: block for block in blocks(document.markdown)
            }
        source = source_blocks[repair.document_slug].get(repair.block_id)
        if source is None:
            raise RepairProjectionMismatch(
                f"repair names block absent from {repair.document_slug}: {repair.block_id}"
            )

        actual_sha256 = hashlib.sha256(source.text.encode("utf-8")).hexdigest()
        mismatches: list[str] = []
        if repair.page_label != source.page_label:
            mismatches.append(f"page {repair.page_label} != {source.page_label}")
        if repair.original_characters != len(source.text):
            mismatches.append(
                f"characters {repair.original_characters} != {len(source.text)}"
            )
        if repair.original_sha256 != actual_sha256:
            mismatches.append(
                f"original_sha256 {repair.original_sha256} != {actual_sha256}"
            )
        if mismatches:
            raise RepairProjectionMismatch(
                f"{repair.document_slug}/{repair.block_id}: repair does not match source: "
                + "; ".join(mismatches)
            )

        if repair.outcome is RepairOutcome.REPAIRED:
            # PageRepair's constructor makes a missing replacement impossible. Keep the
            # assertion local so the type narrowing does not become an implicit fallback.
            if repair.replacement is None:
                raise RepairProjectionMismatch(
                    f"{repair.document_slug}/{repair.block_id}: repaired row has no text"
                )
            replacements.setdefault(repair.document_slug, {})[
                repair.block_id
            ] = repair.replacement

    return replacements


def _required_text(document: Mapping[str, object], key: str, slug: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CorpusUnavailable(f"{slug}: manifest field {key!r} must be non-empty text")
    return value


def _required_positive_int(document: Mapping[str, object], key: str, slug: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CorpusUnavailable(f"{slug}: manifest field {key!r} must be a positive integer")
    return value


def _manifest_documents(
    root: Path, directories: tuple[Path, ...]
) -> tuple[tuple[Path, CorpusManifestDocument], ...]:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise CorpusUnavailable(f"corpus root has no {MANIFEST_FILENAME}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CorpusUnavailable(f"cannot read corpus manifest: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        raise CorpusUnavailable("corpus manifest must contain a documents array")

    by_slug: dict[str, CorpusManifestDocument] = {}
    for raw in payload["documents"]:
        if not isinstance(raw, dict):
            raise CorpusUnavailable("each corpus manifest document must be an object")
        slug_value = raw.get("slug")
        slug = slug_value if isinstance(slug_value, str) and slug_value else "<unknown>"
        slug = _required_text(raw, "slug", slug)
        if slug in by_slug:
            raise CorpusUnavailable(f"corpus manifest repeats document slug {slug!r}")
        by_slug[slug] = CorpusManifestDocument(
            slug=slug,
            source_document_ref=_required_text(raw, "document_id", slug),
            title=_required_text(raw, "document_name", slug),
            doc_type=_required_text(raw, "doc_type", slug),
            pdf_page_count=_required_positive_int(raw, "pdf_pages", slug),
            block_count=_required_positive_int(raw, "blocks_count", slug),
        )

    directory_by_slug = {directory.name: directory for directory in directories}
    missing = sorted(set(directory_by_slug) - set(by_slug))
    extra = sorted(set(by_slug) - set(directory_by_slug))
    if missing or extra:
        raise CorpusUnavailable(
            "manifest and corpus directories disagree: "
            f"missing metadata={missing[:5]!r}, extra metadata={extra[:5]!r}"
        )

    ordered = tuple((directory, by_slug[directory.name]) for directory in directories)
    for directory, metadata in ordered:
        source_ref = read_document(directory).source_document_id
        if source_ref != metadata.source_document_ref:
            raise CorpusUnavailable(
                f"{metadata.slug}: manifest source reference "
                f"{metadata.source_document_ref!r} != blocks.json {source_ref!r}"
            )
    return ordered


def open_corpus_projection(
    root: Path,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    *,
    repair_ledger: RepairLedger | None = None,
) -> CorpusProjection:
    """Validate the source and return a re-iterable effective corpus projection."""
    if target_characters <= 0:
        raise ValueError("target_characters must be positive")
    directories = document_directories(root)
    base_snapshot, fingerprints = _snapshot_with_fingerprints(directories)
    effective_snapshot = (
        base_snapshot
        if repair_ledger is None
        else repaired_snapshot(base_snapshot, repair_ledger)
    )
    replacements = _validated_replacements(root, repair_ledger)
    return CorpusProjection(
        root=root,
        snapshot=effective_snapshot,
        base_content_key=base_snapshot.content_key,
        repair_count=0 if repair_ledger is None else len(repair_ledger.applied),
        target_characters=target_characters,
        documents=_manifest_documents(root, directories),
        base_fingerprints=fingerprints,
        replacements_by_document=replacements,
    )


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


CROPS_DIRNAME = "crops"


def crop_path(root: Path, document_slug: str, block_id: str) -> Path:
    """Where the pipeline put the single-page PDF for one block.

    `corpus/<slug>/crops/<block_id>.pdf`, the layout the drop's own `MANIFEST.json` states
    and which it reports complete: `expected 28246, fetched 28246, missing 0`.
    """
    return root / document_slug / CROPS_DIRNAME / f"{block_id}.pdf"


def read_crop(root: Path, document_slug: str, block_id: str) -> bytes:
    """The crop's bytes, or an explicit refusal.

    A missing crop is loud. `AGENTS.md` §4 forbids a silent fallback, and re-recognising a
    page from *nothing* would produce an answer with no source — which is the shape of the
    defect being repaired rather than a repair of it.
    """
    path = crop_path(root, document_slug, block_id)
    if not path.is_file():
        raise CorpusUnavailable(
            f"{document_slug}/{block_id}: no crop at {CROPS_DIRNAME}/{block_id}.pdf"
        )
    return path.read_bytes()


def degenerate_pages(root: Path) -> Iterator[PageToRecognise]:
    """Every block in the corpus whose text is not the document's, with its crop.

    In document-directory order and then block order, so a partially completed run resumes at
    a determinate place. The check is `degeneracy.inspect`; what it finds and why is that
    module's subject, not this one's.
    """
    for directory in document_directories(root):
        document = read_document(directory)
        for block in blocks(document.markdown):
            if not is_degenerate(block.text):
                continue
            yield PageToRecognise(
                document_slug=document.slug,
                block_id=block.block_id,
                page_label=block.page_label,
                original_text=block.text,
                crop=read_crop(root, document.slug, block.block_id),
            )
