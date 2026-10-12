"""Shared builders for the bundle suite: a synthetic drop, rows, a build and copy records.

Nothing here reads the real corpus. The drop is a few documents in the layout the real
drop's ``MANIFEST.json`` states (``<slug>/{document.pdf,blocks.json,results.md}``,
``<slug>/crops/<block_id>.pdf``, a root ``crops_index.json``), with the operator's
``SHA256SUMS`` written beside it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.digest import EmbeddingSetDigest
from auditmanager.norms.embedding.model import ChunkEmbedding, EmbeddedWindow
from auditmanager.norms.embedding.profile import DIMENSIONS, EMBEDDING_PROFILE
from auditmanager.norms.snapshot import (
    DocumentRow,
    ParagraphRow,
    SnapshotRow,
    SnapshotRows,
)
from auditmanager.shared.identity import (
    NormDocumentId,
    NormParagraphId,
    NormsSnapshotId,
)

ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / "infra/deploy/lib/forced-command.sh"
COPY_SERVE = ROOT / "infra/deploy/copy-serve.sh"
CHUNKING_PROFILE = "characters-v2:1200"


@dataclass
class DropDocument:
    slug: str
    source_ref: str
    #: ``(block_id, page_label, text)`` in block order.
    blocks: Sequence[tuple[str, int, str]]
    pdf: bytes
    #: ``block_id -> crop bytes``; a block absent here has no crop (a failed block).
    crops: dict[str, bytes] = field(default_factory=dict)
    doc_type: str = "СП"


def _markdown(document: DropDocument) -> str:
    parts = [
        (
            f"# Document: {document.slug}.pdf\n\nPath: normative/{document.slug}.pdf\n\n"
            "Generated: 2026-08-25 09:47:54 UTC\n"
        )
    ]
    page = None
    for number, (block_id, page_label, text) in enumerate(document.blocks, start=1):
        if page_label != page:
            parts.append(f"\n## Page {page_label}\n")
            page = page_label
        parts.append(
            f"\n### BLOCK #{number} [TEXT]: {block_id}\n\n"
            "> **Created:** 2026-08-25 09:22:54 UTC\n"
            f"> **Crop:** [Crop](https://example.invalid/crop/{number})\n\n{text}\n"
        )
    return "".join(parts)


def default_documents() -> list[DropDocument]:
    """Two documents, three crops, one crop byte-identical to another document's PDF."""
    shared = b"%PDF-1.7 shared bytes\n"
    return [
        DropDocument(
            slug="СП_001_13330_2026",
            source_ref="doc_" + "1" * 32,
            blocks=[
                ("blk_" + "a" * 32, 1, ("1.1. Первый пункт устанавливает требования к проектированию зданий.\n\n"
                                       "Дата сохранения: 23.07.2026")),
                ("blk_" + "b" * 32, 2, "2.1. Второй пункт уточняет порядок приёмки выполненных работ."),
            ],
            pdf=b"%PDF-1.7 document one\n",
            crops={"blk_" + "a" * 32: b"%PDF-1.7 crop a\n", "blk_" + "b" * 32: shared},
        ),
        DropDocument(
            slug="ГОСТ_2_2026",
            source_ref="doc_" + "2" * 32,
            blocks=[
                ("blk_" + "c" * 32, 1, ("3.1. Третий пункт описывает испытания при приёмке.\n\n"
                                       "Дата сохранения: 24.07.2026")),
            ],
            pdf=shared,
            crops={"blk_" + "c" * 32: b"%PDF-1.7 crop c\n"},
            doc_type="ГОСТ",
        ),
    ]


def write_drop(where: Path, documents: Sequence[DropDocument] | None = None) -> tuple[Path, Path]:
    """``(corpus root, operator SHA256SUMS)``."""
    documents = list(default_documents() if documents is None else documents)
    corpus = where / "corpus"
    corpus.mkdir(parents=True)
    index = []
    for document in documents:
        directory = corpus / document.slug
        (directory / "crops").mkdir(parents=True)
        (directory / "results.md").write_text(_markdown(document), encoding="utf-8")
        (directory / "blocks.json").write_text(
            json.dumps({"document_id": document.source_ref}), encoding="utf-8"
        )
        (directory / "document.pdf").write_bytes(document.pdf)
        for block_id, data in document.crops.items():
            (directory / "crops" / f"{block_id}.pdf").write_bytes(data)
            index.append({"slug": document.slug, "block_id": block_id, "page_index": 0,
                          "crop_url": "https://example.invalid/crop"})
    (corpus / "crops_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (corpus / "MANIFEST.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "slug": document.slug,
                        "document_id": document.source_ref,
                        "document_name": f"{document.slug}.pdf",
                        "doc_type": document.doc_type,
                        "pdf_pages": max(page for _b, page, _t in document.blocks),
                        "blocks_count": len(document.blocks),
                    }
                    for document in documents
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sums = where / "corpus-sums" / "SHA256SUMS"
    sums.parent.mkdir(parents=True)
    lines = []
    for path in sorted(p for p in corpus.rglob("*") if p.is_file()):
        relative = path.relative_to(corpus).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./{relative}\n")
    sums.write_text("".join(lines), encoding="utf-8")
    return corpus, sums


# --- rows and a build, without a database ----------------------------------------------


def synthetic_rows(documents: Sequence[DropDocument] | None = None) -> SnapshotRows:
    documents = list(default_documents() if documents is None else documents)
    snapshot_id = str(NormsSnapshotId.new())
    key = "undated+2d.0123456789ab"
    document_rows = []
    paragraph_rows = []
    for document in documents:
        document_id = str(NormDocumentId.new())
        document_rows.append(
            DocumentRow(
                norm_document_id=document_id,
                source_document_ref=document.source_ref,
                slug=document.slug,
                title=f"{document.slug}.pdf",
                doc_type=document.doc_type,
                drawn_on=None,
                source_attribution="unattributed",
                pdf_page_count=2,
                block_count=len(document.blocks),
                page_heading_count=1,
                recognised_characters=100,
                paragraph_count=len(document.blocks),
            )
        )
        for ordinal, (block_id, page, text) in enumerate(document.blocks):
            paragraph_rows.append(
                ParagraphRow(
                    norm_paragraph_id=str(NormParagraphId.new()),
                    norm_document_id=document_id,
                    ordinal=ordinal,
                    page_label=page,
                    block_ref=block_id,
                    char_offset=0,
                    char_length=len(text),
                    kind="clause",
                    clause_number=None,
                    text=text,
                    text_reliability="reliable",
                )
            )
    return SnapshotRows(
        snapshot=SnapshotRow(
            norms_snapshot_id=snapshot_id,
            content_key=key,
            base_content_key=key,
            content_digest="ab" * 32,
            drawn_from=None,
            drawn_to=None,
            undated_documents=len(documents),
            document_count=len(documents),
            repair_count=0,
            unreliable_count=0,
            segmentation_profile="markdown-v1",
        ),
        documents=tuple(document_rows),
        paragraphs=tuple(paragraph_rows),
    )


def unit_vector(seed: int) -> bytes:
    raw = hashlib.shake_256(f"vector-{seed}".encode()).digest(DIMENSIONS)
    values = [(byte - 127.5) / 127.5 for byte in raw]
    norm = sum(value * value for value in values) ** 0.5
    return vectors.pack([value / norm for value in values])


def synthetic_chunks(references: Sequence[str], per_document: int = 2) -> list[ChunkEmbedding]:
    chunks = []
    seed = 0
    for reference in sorted(references):
        for ordinal in range(per_document):
            windows = []
            for window in range(1 + ordinal % 2):
                seed += 1
                windows.append(
                    EmbeddedWindow(
                        window_ordinal=window,
                        char_offset=window * 10,
                        char_length=20,
                        token_count=12,
                        paragraph_ordinal_first=0,
                        paragraph_ordinal_last=0,
                        input_sha256=hashlib.sha256(f"input-{seed}".encode()).hexdigest(),
                        vector=unit_vector(seed),
                    )
                )
            chunks.append(ChunkEmbedding(reference, ordinal, tuple(windows)))
    return chunks


def chunks_digest(content_key: str, chunks: Sequence[ChunkEmbedding]) -> str:
    digest = EmbeddingSetDigest(
        content_key=content_key, chunking_profile=CHUNKING_PROFILE, embedding_profile=EMBEDDING_PROFILE
    )
    for chunk in chunks:
        for window in chunk.windows:
            digest.add(chunk.document_ref, chunk.chunk_ordinal, window)
    return digest.hexdigest()


# --- copy records ----------------------------------------------------------------------


def utc(offset_seconds: int = 0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset_seconds))


def record_fields(
    *,
    kind: str = "test_data_waiver",
    state: str = "open",
    purpose: str = "import",
    attested: bool = True,
    quiesced_offset: int = -60,
    expires_offset: int = 3600,
    real_data_marker: bool = False,
    migration_head: str = "0019_execution_workers",
    fingerprint: dict | None = None,
    rejected_blob_count: int = 0,
) -> dict:
    """A copy record's fields as `W54-STAND-COPY-01` §3.2 lays them out."""
    waiver = attestation = dump = None
    if kind == "test_data_waiver" and attested:
        waiver = {"statement": "test data only", "attested_at": utc(-60), "expires_at": utc(expires_offset)}
    if kind == "copy":
        dump = {"file": "db.dump", "size_bytes": 1234, "sha256": "d" * 64}
        if attested:
            attestation = {"dump_sha256": "d" * 64, "restore_report_sha256": "c" * 64, "attested_at": utc(-30)}
    return {
        "record_version": 1,
        "kind": kind, "stamp": "20261012T180000Z", "state": state, "purpose": purpose, "target_sha": None,
        "instance": "an-instance", "deployed_tree": "e" * 40, "migration_head": migration_head,
        "opened_at": utc(quiesced_offset), "quiesced_at": utc(quiesced_offset),
        "writers_present": ["web", "api", "worker"], "writers_stopped": ["web", "api", "worker"],
        "dump": dump,
        "fingerprint": fingerprint or {"algorithm": "stand-fingerprint-v1", "sha256": "f" * 64, "tables": {}},
        "rejected_blob_count": rejected_blob_count, "inventory": None, "attestation": attestation,
        "waiver": waiver, "real_data_marker": real_data_marker, "restored_at": None, "closed_at": None,
    }


def record_text(fields: dict) -> str:
    """The record in ``lib/forced-command.sh``'s canonical layout (one key per line)."""
    lines = [f'  "{key}": {json.dumps(value)}' for key, value in fields.items()]
    return "{\n" + ",\n".join(lines) + "\n}\n"


def fingerprint_document(fingerprint) -> dict:
    return {
        "algorithm": "stand-fingerprint-v1",
        "sha256": fingerprint.sha256,
        "tables": {name: {"rows": table.rows, "sha256": table.sha256} for name, table in fingerprint.tables.items()},
    }


def bash_lib(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in bash with ``lib/forced-command.sh`` sourced; ``$@`` are ``args``."""
    return subprocess.run(
        ["bash", "-c", f'set -euo pipefail; FC_NAME=suite; . "$0"; {script}', str(LIB), *args],
        capture_output=True, text=True, timeout=60, check=False,
    )
