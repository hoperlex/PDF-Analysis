"""The encode phase: window and embed every planned batch that has no verified checkpoint.

This is what ``python -m auditmanager.norms.embedding build`` runs inside the norms-worker
image, with the network absent. It reads only the build directory and writes only its
``vectors/`` checkpoints; it opens no database connection. A restart skips every verified
batch, so the ≈ 14 h corpus build spans as many night windows as it needs, and ``--max-batches``
ends a window's share cleanly. The batches are fixed by the plan, and each batch is encoded in
one call over the same windows in the same order, so a resumed build writes exactly the bytes
an uninterrupted one would.

At most one batch — its inputs, its windows and its vectors — is held at a time.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .checkpoint import (
    BatchState,
    Plan,
    PlannedBatch,
    batch_status,
    checkpoint_digest,
    facts,
    read_inputs,
    read_plan,
    require_identity,
    write_batch,
)
from .model import ChunkEmbedding, ChunkInput, EmbeddedWindow
from .windowing import input_digest, paragraph_span, verify_window_set, window_spans


class Encoder(Protocol):
    """A tokenizer plus a model. ``encode`` returns one packed unit float32 vector per text."""

    tokenizer: Any

    def encode(self, texts: Sequence[str]) -> Sequence[bytes]: ...


@dataclass(frozen=True, slots=True)
class BuildProgress:
    batches: int
    verified_before: int
    computed: int
    remaining: int
    digest: str | None
    chunk_count: int
    window_count: int

    @property
    def complete(self) -> bool:
        return self.remaining == 0


def embed_batch(encoder: Encoder, chunks: Sequence[ChunkInput]) -> list[ChunkEmbedding]:
    """Window every chunk of one batch, embed all its windows in one call, check every set."""
    planned: list[tuple[ChunkInput, list[tuple[int, int, int]]]] = []
    texts: list[str] = []
    for chunk in chunks:
        spans, _, _ = window_spans(encoder.tokenizer, chunk.text)
        planned.append((chunk, [(span.char_start, span.char_end, span.token_count) for span in spans]))
        texts.extend(chunk.text[start:end] for start, end, _ in planned[-1][1])
    packed = list(encoder.encode(texts))
    if len(packed) != len(texts):
        raise RuntimeError(f"the encoder returned {len(packed)} vectors for {len(texts)} windows")
    result: list[ChunkEmbedding] = []
    position = 0
    for chunk, spans in planned:
        windows = []
        for ordinal, (start, end, token_count) in enumerate(spans):
            first, last = paragraph_span(
                chunk.paragraph_lengths, chunk.paragraph_ordinal_first, start, end
            )
            windows.append(
                EmbeddedWindow(
                    window_ordinal=ordinal,
                    char_offset=start,
                    char_length=end - start,
                    token_count=token_count,
                    paragraph_ordinal_first=first,
                    paragraph_ordinal_last=last,
                    input_sha256=input_digest(texts[position]),
                    vector=packed[position],
                )
            )
            position += 1
        embedding = ChunkEmbedding(chunk.document_ref, chunk.chunk_ordinal, tuple(windows))
        verify_window_set(
            label=f"chunk {chunk.key!r}",
            text=chunk.text,
            paragraph_ordinal_first=chunk.paragraph_ordinal_first,
            paragraph_ordinal_last=chunk.paragraph_ordinal_last,
            paragraph_lengths=chunk.paragraph_lengths,
            windows=[facts(window) for window in embedding.windows],
        )
        result.append(embedding)
    return result


def _compute(directory: Path, plan: Plan, batch: PlannedBatch, encoder: Encoder) -> None:
    embeddings = embed_batch(encoder, read_inputs(directory, batch))
    write_batch(directory, plan, batch, embeddings)
    written = batch_status(directory, plan, batch)
    if written.state is not BatchState.VERIFIED:
        raise RuntimeError(f"batch {batch.index} was written but does not verify: {written.reason}")


def run_build(
    directory: Path,
    encoder: Encoder,
    *,
    norms_snapshot_id: str,
    chunking_profile: str,
    max_batches: int | None = None,
    report: Callable[[str], None] = print,
) -> BuildProgress:
    plan = read_plan(directory)
    require_identity(plan, norms_snapshot_id=norms_snapshot_id, chunking_profile=chunking_profile)
    if max_batches is not None and max_batches < 0:
        raise ValueError("max_batches cannot be negative")
    verified_before = computed = 0
    pending = 0
    for batch in plan.batches:
        status = batch_status(directory, plan, batch)
        if status.state is BatchState.VERIFIED:
            verified_before += 1
            continue
        if max_batches is not None and computed >= max_batches:
            pending += 1
            continue
        if status.state is BatchState.INVALID:
            report(f"batch {batch.index}: checkpoint invalid ({status.reason}); computing it again")
        _compute(directory, plan, batch, encoder)
        computed += 1
        report(
            f"batch {batch.index + 1}/{len(plan.batches)} written: {batch.chunk_count} chunks "
            f"({verified_before + computed} of {len(plan.batches)} verified)"
        )
    digest = None
    chunk_count = window_count = 0
    if pending == 0:
        digest, chunk_count, window_count = checkpoint_digest(directory, plan)
        report(
            f"all {len(plan.batches)} batches verified: {chunk_count} chunks, {window_count} "
            f"windows, embedding-set digest {digest}"
        )
    else:
        report(f"{pending} of {len(plan.batches)} batches remain; run build again to resume")
    return BuildProgress(
        batches=len(plan.batches),
        verified_before=verified_before,
        computed=computed,
        remaining=pending,
        digest=digest,
        chunk_count=chunk_count,
        window_count=window_count,
    )
