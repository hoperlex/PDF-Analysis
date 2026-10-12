"""A build killed between or inside batches resumes to the same digest, recomputing only what it lost.

Every case runs the real plan, checkpoint and build code over files in ``tmp_path`` with the
fake encoder; only the model is replaced. One case kills a forked build with ``SIGKILL`` while
it is inside a batch — no clean-up runs — and resumes it in this process.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
from pathlib import Path

import pytest

from auditmanager.norms.embedding.builder import run_build
from auditmanager.norms.embedding.checkpoint import (
    BatchState,
    CheckpointRefused,
    batch_status,
    checkpoint_digest,
    prepare_plan,
    read_plan,
    write_atomically,
)
from tests.integration.norms.embedding.support import (
    CHUNKING_PROFILE,
    SNAPSHOT_ID,
    FakeEncoder,
    chunk_set,
    identity,
)

CHUNKS = 23
BATCH = 5  # five batches: 5, 5, 5, 5, 3


def _prepared(directory: Path) -> None:
    plan, created = prepare_plan(directory, identity(), chunk_set(CHUNKS), batch_chunks=BATCH)
    assert created and len(plan.batches) == 5 and plan.chunk_count == CHUNKS


def _build(directory: Path, encoder: FakeEncoder | None = None, **options):
    lines: list[str] = []
    progress = run_build(
        directory,
        encoder or FakeEncoder(),
        norms_snapshot_id=SNAPSHOT_ID,
        chunking_profile=CHUNKING_PROFILE,
        report=lines.append,
        **options,
    )
    return progress, lines


@pytest.fixture
def reference(tmp_path: Path) -> str:
    directory = tmp_path / "reference"
    _prepared(directory)
    progress, _ = _build(directory)
    assert progress.complete and progress.computed == 5
    return progress.digest


def test_an_uninterrupted_build_verifies_every_batch_and_a_rerun_computes_nothing(tmp_path: Path, reference: str) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    first, _ = _build(directory)
    encoder = FakeEncoder()
    again, lines = _build(directory, encoder)
    assert first.digest == again.digest == reference
    assert (again.verified_before, again.computed, encoder.calls) == (5, 0, [])
    assert again.window_count > CHUNKS and again.chunk_count == CHUNKS
    assert lines[-1].startswith("all 5 batches verified")


def _killed_child(directory: str, ready, kill_batch: int) -> None:
    class Stalling(FakeEncoder):
        def encode(self, texts):
            if len(self.calls) == kill_batch:
                ready.send("inside")
                signal.pause()
            return super().encode(texts)

    run_build(
        Path(directory),
        Stalling(),
        norms_snapshot_id=SNAPSHOT_ID,
        chunking_profile=CHUNKING_PROFILE,
        report=lambda _line: None,
    )


def test_a_build_killed_inside_a_batch_resumes_to_the_same_digest(tmp_path: Path, reference: str) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe()
    process = context.Process(target=_killed_child, args=(str(directory), child, 2))
    process.start()
    try:
        assert parent.poll(30), "the build never reached the third batch"
        assert parent.recv() == "inside"
        os.kill(process.pid, signal.SIGKILL)
    finally:
        process.join(30)
    assert process.exitcode == -signal.SIGKILL

    plan = read_plan(directory)
    states = [batch_status(directory, plan, batch).state for batch in plan.batches]
    assert states == [BatchState.VERIFIED] * 2 + [BatchState.MISSING] * 3

    encoder = FakeEncoder()
    resumed, _ = _build(directory, encoder)
    assert resumed.digest == reference
    assert (resumed.verified_before, resumed.computed, len(encoder.calls)) == (2, 3, 3)


def test_a_kill_between_the_rename_and_the_sidecar_costs_that_batch_only(
    tmp_path: Path, reference: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    from auditmanager.norms.embedding import checkpoint

    written: list[Path] = []

    def dying(path: Path, chunks):
        if path.name.endswith(".sha256") and len(written) == 1:
            raise KeyboardInterrupt("killed after the rename, before the sidecar")
        if path.name.endswith(".sha256"):
            written.append(path)
        return write_atomically(path, chunks)

    monkeypatch.setattr(checkpoint, "write_atomically", dying)
    with pytest.raises(KeyboardInterrupt):
        _build(directory)
    monkeypatch.undo()

    plan = read_plan(directory)
    second = batch_status(directory, plan, plan.batches[1])
    assert second.state is BatchState.INVALID and "sidecar" in second.reason

    encoder = FakeEncoder()
    resumed, lines = _build(directory, encoder)
    assert resumed.digest == reference
    assert (resumed.verified_before, resumed.computed) == (1, 4)
    assert any("batch 1: checkpoint invalid" in line for line in lines)


def test_a_corrupted_checkpoint_is_reported_and_computed_again(tmp_path: Path, reference: str) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    _build(directory)
    target = directory / "vectors" / "batch-00003.jsonl"
    body = bytearray(target.read_bytes())
    body[-10] ^= 0x01
    target.write_bytes(bytes(body))

    encoder = FakeEncoder()
    resumed, lines = _build(directory, encoder)
    assert resumed.digest == reference
    assert (resumed.verified_before, resumed.computed, len(encoder.calls)) == (4, 1, 1)
    assert any("batch 3: checkpoint invalid" in line and "sidecar" in line for line in lines)


def test_a_checkpoint_that_matches_its_sidecar_but_not_the_plan_is_not_verified(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    _build(directory)
    plan = read_plan(directory)
    # A checkpoint copied in from another batch: internally consistent, wrong batch.
    source = directory / "vectors" / "batch-00000.jsonl"
    target = directory / "vectors" / "batch-00001.jsonl"
    digest = write_atomically(target, [source.read_bytes()])
    write_atomically(target.with_name(target.name + ".sha256"), [f"{digest}  {target.name}\n".encode()])
    status = batch_status(directory, plan, plan.batches[1])
    assert status.state is BatchState.INVALID and "header batch" in status.reason


def test_max_batches_ends_a_window_and_the_next_window_finishes(tmp_path: Path, reference: str) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    first, lines = _build(directory, max_batches=2)
    assert (first.computed, first.remaining, first.digest) == (2, 3, None)
    assert lines[-1] == "3 of 5 batches remain; run build again to resume"
    second, _ = _build(directory, max_batches=2)
    assert (second.verified_before, second.computed, second.remaining) == (2, 2, 1)
    third, _ = _build(directory)
    assert third.complete and third.digest == reference


def test_the_checkpoints_digest_is_the_builds(tmp_path: Path, reference: str) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    _build(directory)
    digest, chunks, windows = checkpoint_digest(directory, read_plan(directory))
    assert (digest, chunks) == (reference, CHUNKS) and windows > CHUNKS


def test_an_equal_prepare_is_a_no_op_and_another_is_refused(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    _build(directory)
    before = sorted((path.name, path.stat().st_mtime_ns) for path in (directory / "vectors").iterdir())
    _, created = prepare_plan(directory, identity(), chunk_set(CHUNKS), batch_chunks=BATCH)
    assert not created
    assert sorted((path.name, path.stat().st_mtime_ns) for path in (directory / "vectors").iterdir()) == before
    with pytest.raises(CheckpointRefused, match="another build"):
        prepare_plan(directory, identity(), chunk_set(CHUNKS, seed=9), batch_chunks=BATCH)
    with pytest.raises(CheckpointRefused, match="another build"):
        prepare_plan(directory, identity(), chunk_set(CHUNKS), batch_chunks=BATCH + 1)


def test_prepare_refuses_chunks_out_of_order_and_an_empty_set(tmp_path: Path) -> None:
    chunks = chunk_set(6)
    with pytest.raises(CheckpointRefused, match="canonical order"):
        prepare_plan(tmp_path / "a", identity(), [chunks[1], chunks[0]], batch_chunks=2)
    with pytest.raises(CheckpointRefused, match="canonical order"):
        prepare_plan(tmp_path / "b", identity(), [chunks[0], chunks[0]], batch_chunks=2)
    with pytest.raises(CheckpointRefused, match="zero chunks"):
        prepare_plan(tmp_path / "c", identity(), [], batch_chunks=2)
    assert not (tmp_path / "a" / "plan.json").exists()


def test_a_build_for_another_snapshot_or_profile_is_refused(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    with pytest.raises(CheckpointRefused, match="the plan is for"):
        run_build(directory, FakeEncoder(), norms_snapshot_id="ns_" + "1" * 26, chunking_profile=CHUNKING_PROFILE)
    with pytest.raises(CheckpointRefused, match="the plan is for"):
        run_build(directory, FakeEncoder(), norms_snapshot_id=SNAPSHOT_ID, chunking_profile="characters-v2:1000")


def test_an_edited_input_file_stops_the_build(tmp_path: Path) -> None:
    directory = tmp_path / "build"
    _prepared(directory)
    target = directory / "inputs" / "batch-00002.jsonl"
    target.write_bytes(target.read_bytes().replace(b"doc-", b"dok-", 1))
    with pytest.raises(CheckpointRefused, match="plan's SHA-256"):
        _build(directory)
