"""The build's files: one plan, one input file and one checkpoint file per batch.

A build directory (``.local/norms/builds/<content_key>/`` by convention) holds::

    plan.json                     the build identity and every batch's input digest
    inputs/batch-NNNNN.jsonl      the batch's chunks: computed key, text, paragraph layout
    vectors/batch-NNNNN.jsonl     the batch's windows and vectors (the checkpoint)
    vectors/batch-NNNNN.jsonl.sha256

The plan is written last by ``prepare``, after every input file, so a plan that exists names
only complete inputs. Batches are fixed by the plan: batch *k* is always the same chunks, in
canonical order ``(source_document_ref, ordinal)``, so a resumed build computes exactly the
batches an uninterrupted one would.

A checkpoint is written to ``*.tmp``, flushed and fsynced, renamed, and only then given its
SHA-256 sidecar, written the same way. A batch is **verified** when its sidecar exists, the
file's SHA-256 equals it, its header names this plan and this batch's inputs, its chunks are
the inputs' chunks in order, every window set is the chunk's full set (`D-127`) and every
vector is a unit float32 vector whose SHA-256 the file records. Anything less is not a
checkpoint: a restart reports it and computes the batch again. A kill can therefore land
anywhere — mid-batch, between the rename and the sidecar — and cost at most one batch.

Memory is bounded by one batch: every reader here yields one batch's records and holds no
other batch.
"""

from __future__ import annotations

import enum
import hashlib
import json
import os
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import vectors
from .digest import EmbeddingSetDigest
from .model import ChunkEmbedding, ChunkInput, EmbeddedWindow
from .profile import (
    EMBEDDING_PROFILE,
    MAX_TOKENS,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    OVERLAP_TOKENS,
    require_snapshot_id,
)
from .windowing import WindowFacts, WindowingRefused, verify_window_set

PLAN_FORMAT = "auditmanager-embedding-plan/1"
BATCH_FORMAT = "auditmanager-embedding-batch/1"
PLAN_FILE = "plan.json"
INPUTS_DIRECTORY = "inputs"
VECTORS_DIRECTORY = "vectors"
DEFAULT_BATCH_CHUNKS = 256
_BATCH_NAME = re.compile(r"^batch-\d{5}\.jsonl(\.sha256)?(\.tmp)?$")


class CheckpointRefused(RuntimeError):
    """The build directory cannot be used as asked; nothing was overwritten."""


@dataclass(frozen=True, slots=True)
class BuildIdentity:
    """What one build is of. Every file in the directory is bound to it."""

    norms_snapshot_id: str
    content_key: str
    chunking_profile: str
    embedding_profile: str = EMBEDDING_PROFILE
    model_repository: str = MODEL_REPOSITORY
    model_revision: str = MODEL_REVISION
    max_tokens: int = MAX_TOKENS
    overlap_tokens: int = OVERLAP_TOKENS

    def __post_init__(self) -> None:
        require_snapshot_id(self.norms_snapshot_id)
        if not self.content_key or not self.chunking_profile:
            raise ValueError("a build names its content key and chunking profile")

    def as_document(self) -> dict[str, Any]:
        return {
            "norms_snapshot_id": self.norms_snapshot_id,
            "content_key": self.content_key,
            "chunking_profile": self.chunking_profile,
            "embedding_profile": self.embedding_profile,
            "model_repository": self.model_repository,
            "model_revision": self.model_revision,
            "max_tokens": self.max_tokens,
            "overlap_tokens": self.overlap_tokens,
        }


@dataclass(frozen=True, slots=True)
class PlannedBatch:
    index: int
    chunk_count: int
    first: tuple[str, int]
    last: tuple[str, int]
    inputs_sha256: str

    @property
    def name(self) -> str:
        return f"batch-{self.index:05d}.jsonl"


@dataclass(frozen=True, slots=True)
class Plan:
    identity: BuildIdentity
    batch_chunks: int
    chunk_count: int
    batches: tuple[PlannedBatch, ...]
    sha256: str


class BatchState(enum.Enum):
    VERIFIED = "verified"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class BatchStatus:
    batch: PlannedBatch
    state: BatchState
    reason: str = ""
    window_count: int = 0


# --- serialisation ---------------------------------------------------------------------------


def _line(document: Any) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _input_document(chunk: ChunkInput) -> dict[str, Any]:
    return {
        "document_ref": chunk.document_ref,
        "chunk_ordinal": chunk.chunk_ordinal,
        "text": chunk.text,
        "paragraph_ordinal_first": chunk.paragraph_ordinal_first,
        "paragraph_ordinal_last": chunk.paragraph_ordinal_last,
        "paragraph_lengths": list(chunk.paragraph_lengths),
    }


def _chunk_input(document: dict[str, Any]) -> ChunkInput:
    return ChunkInput(
        document_ref=str(document["document_ref"]),
        chunk_ordinal=int(document["chunk_ordinal"]),
        text=str(document["text"]),
        paragraph_ordinal_first=int(document["paragraph_ordinal_first"]),
        paragraph_ordinal_last=int(document["paragraph_ordinal_last"]),
        paragraph_lengths=tuple(int(value) for value in document["paragraph_lengths"]),
    )


def _window_document(window: EmbeddedWindow) -> dict[str, Any]:
    return {
        "window_ordinal": window.window_ordinal,
        "char_offset": window.char_offset,
        "char_length": window.char_length,
        "token_count": window.token_count,
        "paragraph_ordinal_first": window.paragraph_ordinal_first,
        "paragraph_ordinal_last": window.paragraph_ordinal_last,
        "input_sha256": window.input_sha256,
        "embedding_sha256": window.embedding_sha256,
        "vector": vectors.to_base64(window.vector),
    }


def _embedded_window(document: dict[str, Any]) -> EmbeddedWindow:
    window = EmbeddedWindow(
        window_ordinal=int(document["window_ordinal"]),
        char_offset=int(document["char_offset"]),
        char_length=int(document["char_length"]),
        token_count=int(document["token_count"]),
        paragraph_ordinal_first=int(document["paragraph_ordinal_first"]),
        paragraph_ordinal_last=int(document["paragraph_ordinal_last"]),
        input_sha256=str(document["input_sha256"]),
        vector=vectors.from_base64(str(document["vector"])),
    )
    if window.embedding_sha256 != document["embedding_sha256"]:
        raise CheckpointRefused("a vector's bytes do not match its recorded SHA-256")
    vectors.require_unit(window.vector)
    return window


def facts(window: EmbeddedWindow) -> WindowFacts:
    return WindowFacts(
        window_ordinal=window.window_ordinal,
        char_offset=window.char_offset,
        char_length=window.char_length,
        token_count=window.token_count,
        paragraph_ordinal_first=window.paragraph_ordinal_first,
        paragraph_ordinal_last=window.paragraph_ordinal_last,
        input_sha256=window.input_sha256,
    )


# --- durable writes --------------------------------------------------------------------------


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_atomically(path: Path, chunks: Iterable[bytes]) -> str:
    """Write, flush, fsync and rename into place; return the SHA-256 of the bytes written."""
    temporary = path.with_name(path.name + ".tmp")
    digest = hashlib.sha256()
    with open(temporary, "wb") as handle:
        for chunk in chunks:
            digest.update(chunk)
            handle.write(chunk)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)
    return digest.hexdigest()


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".sha256")


# --- the plan -------------------------------------------------------------------------------


def _plan_document(identity: BuildIdentity, batch_chunks: int, batches: Sequence[PlannedBatch]) -> dict[str, Any]:
    return {
        "format": PLAN_FORMAT,
        "identity": identity.as_document(),
        "batch_chunks": batch_chunks,
        "chunk_count": sum(batch.chunk_count for batch in batches),
        "batches": [
            {
                "index": batch.index,
                "chunk_count": batch.chunk_count,
                "first": list(batch.first),
                "last": list(batch.last),
                "inputs": f"{INPUTS_DIRECTORY}/{batch.name}",
                "inputs_sha256": batch.inputs_sha256,
            }
            for batch in batches
        ],
    }


def _render_plan(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _batched(chunks: Iterable[ChunkInput], batch_chunks: int) -> Iterator[list[ChunkInput]]:
    batch: list[ChunkInput] = []
    previous: tuple[str, int] | None = None
    for chunk in chunks:
        if previous is not None and not chunk.key > previous:
            raise CheckpointRefused(f"chunk {chunk.key!r} is out of canonical order after {previous!r}")
        previous = chunk.key
        batch.append(chunk)
        if len(batch) == batch_chunks:
            yield batch
            batch = []
    if batch:
        yield batch


def prepare_plan(
    directory: Path,
    identity: BuildIdentity,
    chunks: Iterable[ChunkInput],
    *,
    batch_chunks: int = DEFAULT_BATCH_CHUNKS,
) -> tuple[Plan, bool]:
    """Write the inputs and the plan, or confirm an equal plan already there.

    Returns ``(plan, created)``. An existing plan is never overwritten: the chunks are
    re-hashed batch by batch without writing, and a plan that differs in any byte is refused,
    so a directory's checkpoints are never silently re-bound to other inputs.
    """
    if batch_chunks <= 0:
        raise ValueError("batch_chunks must be positive")
    directory.mkdir(parents=True, exist_ok=True)
    plan_path = directory / PLAN_FILE
    inputs = directory / INPUTS_DIRECTORY
    existing = plan_path.exists()
    if not existing:
        inputs.mkdir(exist_ok=True)
        for stale in inputs.iterdir():
            if _BATCH_NAME.match(stale.name):
                stale.unlink()
    batches: list[PlannedBatch] = []
    for index, batch in enumerate(_batched(chunks, batch_chunks)):
        for chunk in batch:
            if chunk.paragraph_ordinal_last - chunk.paragraph_ordinal_first + 1 != len(chunk.paragraph_lengths):
                raise CheckpointRefused(f"chunk {chunk.key!r} paragraph layout does not match its span")
        lines = [_line(_input_document(chunk)) for chunk in batch]
        planned_name = f"batch-{index:05d}.jsonl"
        if existing:
            digest = hashlib.sha256(b"".join(lines)).hexdigest()
        else:
            digest = write_atomically(inputs / planned_name, lines)
        batches.append(PlannedBatch(index, len(batch), batch[0].key, batch[-1].key, digest))
    if not batches:
        raise CheckpointRefused("a build over zero chunks is never complete")
    rendered = _render_plan(_plan_document(identity, batch_chunks, batches))
    if existing:
        stored = plan_path.read_bytes()
        if stored != rendered:
            raise CheckpointRefused(
                f"{plan_path} describes another build; use a new directory or remove this one "
                "by hand after checking what it holds"
            )
        return read_plan(directory), False
    write_atomically(plan_path, [rendered])
    return read_plan(directory), True


def read_plan(directory: Path) -> Plan:
    plan_path = directory / PLAN_FILE
    if not plan_path.is_file():
        raise CheckpointRefused(f"{plan_path} does not exist; run prepare first")
    raw = plan_path.read_bytes()
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise CheckpointRefused(f"{plan_path} is not JSON") from exc
    if document.get("format") != PLAN_FORMAT:
        raise CheckpointRefused(f"{plan_path} is not a {PLAN_FORMAT} plan")
    identity = BuildIdentity(**document["identity"])
    batches = tuple(
        PlannedBatch(
            index=int(entry["index"]),
            chunk_count=int(entry["chunk_count"]),
            first=(str(entry["first"][0]), int(entry["first"][1])),
            last=(str(entry["last"][0]), int(entry["last"][1])),
            inputs_sha256=str(entry["inputs_sha256"]),
        )
        for entry in document["batches"]
    )
    if [batch.index for batch in batches] != list(range(len(batches))) or not batches:
        raise CheckpointRefused(f"{plan_path} batches are not 0..n-1")
    if sum(batch.chunk_count for batch in batches) != int(document["chunk_count"]):
        raise CheckpointRefused(f"{plan_path} chunk count disagrees with its batches")
    if _render_plan(_plan_document(identity, int(document["batch_chunks"]), batches)) != raw:
        raise CheckpointRefused(f"{plan_path} is not in canonical form")
    return Plan(
        identity=identity,
        batch_chunks=int(document["batch_chunks"]),
        chunk_count=int(document["chunk_count"]),
        batches=batches,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def require_identity(plan: Plan, *, norms_snapshot_id: str, chunking_profile: str) -> None:
    identity = plan.identity
    if (identity.norms_snapshot_id, identity.chunking_profile) != (norms_snapshot_id, chunking_profile):
        raise CheckpointRefused(
            f"the plan is for {identity.norms_snapshot_id} / {identity.chunking_profile}, "
            f"not {norms_snapshot_id} / {chunking_profile}"
        )
    expected = BuildIdentity(
        norms_snapshot_id=identity.norms_snapshot_id,
        content_key=identity.content_key,
        chunking_profile=identity.chunking_profile,
    )
    if identity != expected:
        raise CheckpointRefused(
            f"the plan names embedding profile {identity.embedding_profile} "
            f"{identity.model_repository}@{identity.model_revision} "
            f"{identity.max_tokens}/{identity.overlap_tokens}; this embedder is {expected!r}"
        )


def read_inputs(directory: Path, batch: PlannedBatch) -> list[ChunkInput]:
    path = directory / INPUTS_DIRECTORY / batch.name
    if not path.is_file():
        raise CheckpointRefused(f"input {path} is missing")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != batch.inputs_sha256:
        raise CheckpointRefused(f"input {path} does not match the plan's SHA-256")
    chunks = [_chunk_input(json.loads(line)) for line in raw.decode("utf-8").splitlines()]
    if len(chunks) != batch.chunk_count or chunks[0].key != batch.first or chunks[-1].key != batch.last:
        raise CheckpointRefused(f"input {path} does not hold the plan's chunks")
    return chunks


# --- checkpoints -----------------------------------------------------------------------------


def _vectors_path(directory: Path, batch: PlannedBatch) -> Path:
    return directory / VECTORS_DIRECTORY / batch.name


def write_batch(
    directory: Path, plan: Plan, batch: PlannedBatch, embeddings: Sequence[ChunkEmbedding]
) -> str:
    """Write one verified-on-read checkpoint, sidecar last; return its SHA-256."""
    target = _vectors_path(directory, batch)
    target.parent.mkdir(exist_ok=True)
    for leftover in (_sidecar(target), target):
        if leftover.exists():
            leftover.unlink()
    header = {
        "format": BATCH_FORMAT,
        "plan_sha256": plan.sha256,
        "batch": batch.index,
        "inputs_sha256": batch.inputs_sha256,
        "embedding_profile": plan.identity.embedding_profile,
        "model_revision": plan.identity.model_revision,
        "chunk_count": len(embeddings),
        "window_count": sum(len(item.windows) for item in embeddings),
    }
    lines = [_line(header)]
    lines.extend(
        _line(
            {
                "document_ref": item.document_ref,
                "chunk_ordinal": item.chunk_ordinal,
                "windows": [_window_document(window) for window in item.windows],
            }
        )
        for item in embeddings
    )
    digest = write_atomically(target, lines)
    write_atomically(_sidecar(target), [f"{digest}  {target.name}\n".encode("ascii")])
    return digest


def read_batch(directory: Path, plan: Plan, batch: PlannedBatch) -> list[ChunkEmbedding]:
    """One fully verified checkpoint, or :class:`CheckpointRefused` naming what is wrong."""
    target = _vectors_path(directory, batch)
    sidecar = _sidecar(target)
    if not target.is_file():
        raise FileNotFoundError(target)
    if not sidecar.is_file():
        raise CheckpointRefused(f"{target.name} has no SHA-256 sidecar (interrupted write)")
    recorded = sidecar.read_text(encoding="ascii").split()
    if recorded != [_sha256_of(target), target.name]:
        raise CheckpointRefused(f"{target.name} does not match its SHA-256 sidecar")
    lines = target.read_bytes().decode("utf-8").splitlines()
    if not lines:
        raise CheckpointRefused(f"{target.name} is empty")
    header = json.loads(lines[0])
    expected_header = {
        "format": BATCH_FORMAT,
        "plan_sha256": plan.sha256,
        "batch": batch.index,
        "inputs_sha256": batch.inputs_sha256,
        "embedding_profile": plan.identity.embedding_profile,
        "model_revision": plan.identity.model_revision,
    }
    for name, value in expected_header.items():
        if header.get(name) != value:
            raise CheckpointRefused(f"{target.name} header {name}={header.get(name)!r}, expected {value!r}")
    inputs = read_inputs(directory, batch)
    embeddings: list[ChunkEmbedding] = []
    for line, chunk in zip(lines[1:], inputs, strict=False):
        document = json.loads(line)
        item = ChunkEmbedding(
            document_ref=str(document["document_ref"]),
            chunk_ordinal=int(document["chunk_ordinal"]),
            windows=tuple(_embedded_window(window) for window in document["windows"]),
        )
        if item.key != chunk.key:
            raise CheckpointRefused(f"{target.name} holds chunk {item.key!r} where the plan has {chunk.key!r}")
        try:
            verify_window_set(
                label=f"{target.name} chunk {chunk.key!r}",
                text=chunk.text,
                paragraph_ordinal_first=chunk.paragraph_ordinal_first,
                paragraph_ordinal_last=chunk.paragraph_ordinal_last,
                paragraph_lengths=chunk.paragraph_lengths,
                windows=[facts(window) for window in item.windows],
            )
        except WindowingRefused as exc:
            raise CheckpointRefused(str(exc)) from exc
        embeddings.append(item)
    if len(lines) - 1 != len(inputs) or len(embeddings) != len(inputs):
        raise CheckpointRefused(f"{target.name} holds {len(lines) - 1} chunks, the plan {len(inputs)}")
    if header.get("chunk_count") != len(embeddings) or header.get("window_count") != sum(
        len(item.windows) for item in embeddings
    ):
        raise CheckpointRefused(f"{target.name} header counts disagree with its body")
    return embeddings


def batch_status(directory: Path, plan: Plan, batch: PlannedBatch) -> BatchStatus:
    try:
        embeddings = read_batch(directory, plan, batch)
    except FileNotFoundError:
        return BatchStatus(batch, BatchState.MISSING)
    except (CheckpointRefused, vectors.VectorRefused, ValueError, KeyError, TypeError) as exc:
        return BatchStatus(batch, BatchState.INVALID, reason=str(exc))
    return BatchStatus(
        batch, BatchState.VERIFIED, window_count=sum(len(item.windows) for item in embeddings)
    )


def iter_verified(directory: Path, plan: Plan) -> Iterator[ChunkEmbedding]:
    """Every chunk's windows, batch by batch, each batch verified before its first chunk."""
    for batch in plan.batches:
        try:
            embeddings = read_batch(directory, plan, batch)
        except FileNotFoundError as exc:
            raise CheckpointRefused(f"batch {batch.index} has no checkpoint; the build is incomplete") from exc
        yield from embeddings


def checkpoint_digest(directory: Path, plan: Plan) -> tuple[str, int, int]:
    """``(embedding-set digest, chunk count, window count)`` over every verified checkpoint."""
    digest = EmbeddingSetDigest(
        content_key=plan.identity.content_key,
        chunking_profile=plan.identity.chunking_profile,
        embedding_profile=plan.identity.embedding_profile,
    )
    chunks = 0
    for item in iter_verified(directory, plan):
        chunks += 1
        for window in item.windows:
            digest.add(item.document_ref, item.chunk_ordinal, window)
    return digest.hexdigest(), chunks, digest.windows
