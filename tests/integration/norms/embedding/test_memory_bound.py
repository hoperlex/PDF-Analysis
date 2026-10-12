"""Memory is bounded by the batch, not by the build: every phase holds one batch at a time.

Shown by counting — the encoder never receives more than one batch's windows, inputs are read
one batch ahead of nothing, the loader's iterator reads a checkpoint only when its first chunk
is wanted — and by measuring: the traced peak of a build four times longer stays within a
small margin of the shorter build's peak.
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

from auditmanager.norms.embedding import builder, checkpoint
from auditmanager.norms.embedding.builder import run_build
from auditmanager.norms.embedding.checkpoint import (
    iter_verified,
    prepare_plan,
    read_plan,
)
from tests.integration.norms.embedding.support import (
    CHUNKING_PROFILE,
    SNAPSHOT_ID,
    FakeEncoder,
    chunk_set,
    identity,
)

BATCH = 4


def _prepared(directory: Path, chunks: int) -> None:
    prepare_plan(directory, identity(), chunk_set(chunks), batch_chunks=BATCH)


def _run(directory: Path, encoder: FakeEncoder) -> None:
    run_build(
        directory,
        encoder,
        norms_snapshot_id=SNAPSHOT_ID,
        chunking_profile=CHUNKING_PROFILE,
        report=lambda _line: None,
    )


def test_the_encoder_gets_one_batch_and_inputs_are_read_one_batch_at_a_time(tmp_path: Path, monkeypatch) -> None:
    directory = tmp_path / "build"
    _prepared(directory, 20)
    plan = read_plan(directory)
    read: list[int] = []
    encoded_after: list[int] = []
    real_read_inputs = builder.read_inputs

    def counting(directory_, batch):
        read.append(batch.index)
        return real_read_inputs(directory_, batch)

    class Watching(FakeEncoder):
        def encode(self, texts):
            encoded_after.append(len(read))
            return super().encode(texts)

    monkeypatch.setattr(builder, "read_inputs", counting)
    encoder = Watching()
    _run(directory, encoder)
    assert read == list(range(len(plan.batches)))
    assert encoded_after == list(range(1, len(plan.batches) + 1))
    windows_per_batch = []
    for batch in plan.batches:
        windows_per_batch.append(sum(len(item.windows) for item in checkpoint.read_batch(directory, plan, batch)))
    assert encoder.calls == windows_per_batch


def test_the_loaders_iterator_reads_a_checkpoint_only_when_its_chunks_are_wanted(tmp_path: Path, monkeypatch) -> None:
    directory = tmp_path / "build"
    _prepared(directory, 20)
    _run(directory, FakeEncoder())
    plan = read_plan(directory)
    read: list[int] = []
    real_read_batch = checkpoint.read_batch

    def counting(directory_, plan_, batch):
        read.append(batch.index)
        return real_read_batch(directory_, plan_, batch)

    monkeypatch.setattr(checkpoint, "read_batch", counting)
    stream = iter_verified(directory, plan)
    next(stream)
    assert read == [0]
    for _ in range(BATCH):
        next(stream)
    assert read == [0, 1]


def _peak(directory: Path, chunks: int) -> int:
    _prepared(directory, chunks)
    tracemalloc.start()
    try:
        _run(directory, FakeEncoder())
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_four_times_longer_build_does_not_raise_the_peak(tmp_path: Path) -> None:
    short = _peak(tmp_path / "short", 4 * BATCH * 3)
    long = _peak(tmp_path / "long", 4 * BATCH * 12)
    assert long < short * 1.25, (short, long)
