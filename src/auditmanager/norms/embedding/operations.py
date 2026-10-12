"""The two database phases of a build: ``prepare`` before the image runs, ``load`` after.

Both run on the host with the repository's own virtualenv, against the promotion database
(``DATABASE_URL``); the image phase between them (``builder.run_build``) has no database and
no network. This module imports SQLAlchemy through the repository, so the in-image entry
points import it only for these two commands.

* ``prepare`` reads the snapshot's chunk set in canonical order, one streamed cursor, and
  writes the plan and the per-batch input files. It writes nothing to the database.
* ``load`` verifies every checkpoint, then hands them, one batch at a time, to
  :meth:`NormEmbeddingRepository.ensure_build` inside **one** transaction that ends with the
  completion row; the embedding-set digest the database recomputes must equal the
  checkpoints'. A failure anywhere rolls the whole build back.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormsSnapshotId

from ..embedding_repository import (
    NormEmbeddingConflict,
    NormEmbeddingRepository,
    StoredEmbeddingBuild,
)
from .checkpoint import (
    DEFAULT_BATCH_CHUNKS,
    BatchState,
    BuildIdentity,
    CheckpointRefused,
    Plan,
    batch_status,
    checkpoint_digest,
    iter_verified,
    prepare_plan,
    read_plan,
    require_identity,
)


@dataclass(frozen=True, slots=True)
class LoadResult:
    build: StoredEmbeddingBuild
    checkpoint_digest: str


def prepare(
    session: Session,
    directory: Path,
    *,
    snapshot_id: NormsSnapshotId,
    chunking_profile: str,
    batch_chunks: int = DEFAULT_BATCH_CHUNKS,
) -> tuple[Plan, bool]:
    repository = NormEmbeddingRepository(session)
    subject = repository.build_subject(snapshot_id, chunking_profile)
    identity = BuildIdentity(
        norms_snapshot_id=str(snapshot_id),
        content_key=subject.content_key,
        chunking_profile=chunking_profile,
    )
    plan, created = prepare_plan(
        directory,
        identity,
        repository.iter_chunk_inputs(snapshot_id, chunking_profile),
        batch_chunks=batch_chunks,
    )
    if plan.chunk_count != subject.chunk_count:
        raise CheckpointRefused(
            f"the plan holds {plan.chunk_count} chunks, the chunk build {subject.chunk_count}"
        )
    return plan, created


def load(
    session: Session,
    directory: Path,
    *,
    snapshot_id: NormsSnapshotId,
    chunking_profile: str,
) -> LoadResult:
    plan = read_plan(directory)
    require_identity(plan, norms_snapshot_id=str(snapshot_id), chunking_profile=chunking_profile)
    unverified = [
        status
        for status in (batch_status(directory, plan, batch) for batch in plan.batches)
        if status.state is not BatchState.VERIFIED
    ]
    if unverified:
        first = unverified[0]
        raise CheckpointRefused(
            f"{len(unverified)} of {len(plan.batches)} batches are not verified (first: batch "
            f"{first.batch.index}, {first.state.value} {first.reason}); run build to finish them"
        )
    expected, _, _ = checkpoint_digest(directory, plan)
    repository = NormEmbeddingRepository(session)
    subject = repository.build_subject(snapshot_id, chunking_profile)
    if subject.content_key != plan.identity.content_key:
        raise CheckpointRefused(
            f"the plan is for content key {plan.identity.content_key!r}, the snapshot holds "
            f"{subject.content_key!r}"
        )
    build = repository.ensure_build(
        snapshot_id=snapshot_id,
        chunking_profile=chunking_profile,
        chunks=iter_verified(directory, plan),
    )
    if build.embedding_set_sha256 != expected:
        raise NormEmbeddingConflict(
            f"the database digest {build.embedding_set_sha256} differs from the checkpoints' {expected}"
        )
    return LoadResult(build=build, checkpoint_digest=expected)
