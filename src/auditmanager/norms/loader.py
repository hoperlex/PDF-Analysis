"""Atomic, idempotent loading of a normative corpus into PostgreSQL — projected or imported.

Two entry points, one boundary each:

- :func:`load_corpus` projects the drop (and an optional repair ledger) and mints a fresh
  opaque id for the snapshot, every document and every paragraph. This is how the promotion
  database gets its rows (`W54-PLAN.md` §3.2).
- :func:`import_snapshot` inserts rows that already carry their ids, exactly as given, and
  derives the named chunk profiles from them. This is how a verified bundle's rows reach
  another database without a second identity being minted (§3.5 step 3).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.shared.db.session import session_scope
from auditmanager.shared.identity import NormsSnapshotId

from .chunking import (
    CHUNKING_PROFILE_VERSION,
    CHUNKING_VERSIONS,
    DEFAULT_CHUNKING_VERSION,
    DEFAULT_TARGET_CHARACTERS,
    RELIABLE_CHUNKING_PROFILE_VERSION,
    ChunkingRefused,
    parse_chunking_profile,
)
from .corpus_source import open_corpus_projection
from .repair import RepairLedger
from .repository import (
    NormsProjectionConflict,
    NormsRepository,
    SnapshotImportConflict,
    SnapshotRowsInvalid,
    StoredCorpusCounts,
    validate_snapshot_rows,
)
from .snapshot import SnapshotRows


@dataclass(frozen=True, slots=True)
class CorpusLoadResult:
    norms_snapshot_id: NormsSnapshotId
    content_key: str
    chunking_profile: str
    created: bool
    counts: StoredCorpusCounts
    unreliable_count: int
    row_digest: str


@dataclass(frozen=True, slots=True)
class SnapshotImportResult:
    norms_snapshot_id: NormsSnapshotId
    content_key: str
    created: bool
    row_digest: str
    counts: tuple[tuple[str, StoredCorpusCounts], ...]


def load_corpus(
    session: Session,
    root: Path,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    *,
    repair_ledger: RepairLedger | None = None,
    chunking_version: str = DEFAULT_CHUNKING_VERSION,
) -> CorpusLoadResult:
    """Load one effective corpus, leaving commit or rollback to the caller.

    A SAVEPOINT protects callers that catch a validation error: no partial snapshot rows remain
    pending in their outer transaction. The command performs no object-store or provider side
    effect, so this one database boundary is the entire atomic unit.

    The snapshot row carries ``unreliable_count`` and every paragraph its
    ``text_reliability`` (`F-4`); ``characters-v1`` is refused when anything is unreliable.
    An exact replay reuses every stored id; a replay naming a chunk profile the stored
    snapshot lacks builds that profile from the stored canonical paragraphs.
    """
    projection = open_corpus_projection(
        root,
        target_characters=target_characters,
        repair_ledger=repair_ledger,
        chunking_version=chunking_version,
    )
    profile = projection.chunking_profile
    repository = NormsRepository(session)

    with session.begin_nested():
        snapshot_id, created = repository.ensure_snapshot(projection)
        if created:
            repository.admit_chunking_profile(snapshot_id, profile)
            documents = paragraphs = chunks = 0
            for projected in projection.iter_documents():
                chunks += repository.insert_document(snapshot_id, projected, profile)
                documents += 1
                paragraphs += len(projected.paragraphs)
            if documents != projection.snapshot.document_count:
                raise NormsProjectionConflict(
                    f"snapshot claims {projection.snapshot.document_count} documents, "
                    f"loader projected {documents}"
                )
            repository.finish_chunk_build(
                snapshot_id,
                profile,
                target_characters,
                chunks,
            )
            expected = StoredCorpusCounts(documents, paragraphs, chunks)
            stored = repository.counts(snapshot_id, profile)
            if stored != expected:
                raise NormsProjectionConflict(
                    f"stored counts {stored!r} do not match projected counts {expected!r}"
                )
        else:
            if not repository.has_chunk_build(snapshot_id, profile):
                repository.build_chunks_from_stored(
                    snapshot_id, projection.snapshot.content_key, profile
                )
            stored = repository.counts(snapshot_id, profile)
            if stored.documents != projection.snapshot.document_count:
                raise NormsProjectionConflict(
                    f"stored snapshot {snapshot_id} has {stored.documents} documents; "
                    f"content key claims {projection.snapshot.document_count}"
                )
        digest = repository.stored_row_digest(snapshot_id)

    return CorpusLoadResult(
        norms_snapshot_id=snapshot_id,
        content_key=projection.snapshot.content_key,
        chunking_profile=profile,
        created=created,
        counts=stored,
        unreliable_count=projection.unreliable_count,
        row_digest=digest,
    )


def import_snapshot(
    session: Session,
    rows: SnapshotRows,
    *,
    chunking_profiles: Sequence[str],
    expected_row_digest: str | None = None,
) -> SnapshotImportResult:
    """Insert one snapshot's rows with the ids they carry, in the caller's transaction.

    Before any write: the rows are validated as one snapshot; their digest must equal
    ``expected_row_digest`` when given (the manifest's); every named chunk profile must be
    admissible (``characters-v1`` is refused when ``unreliable_count > 0``).

    Then exactly one of three outcomes:

    - **exact replay** — the stored snapshot has this id *and* this key, and its recomputed
      row digest equals the rows'. Every named profile must already be built; nothing is
      written and ``created`` is false;
    - **conflict** (:class:`SnapshotImportConflict`, nothing written) — the key is stored under
      another id, the id under another key, equal ids with other rows, a missing profile on
      replay, or any document or paragraph id already held by another snapshot;
    - **insert** — every row with its own id, private keys minted and remapped; each profile
      built from the inserted paragraphs; then the stored digest is recomputed and must equal
      the rows', or the SAVEPOINT rolls everything back.
    """
    validate_snapshot_rows(rows)
    digest = rows.row_digest
    if expected_row_digest is not None and digest != expected_row_digest:
        raise SnapshotRowsInvalid(
            f"row digest {digest} does not equal the expected {expected_row_digest}"
        )
    profiles = tuple(chunking_profiles)
    if not profiles or len(set(profiles)) != len(profiles):
        raise SnapshotRowsInvalid(f"chunk profiles must be named once each: {profiles!r}")
    for profile in profiles:
        try:
            version, _target = parse_chunking_profile(profile)
        except ValueError as exc:
            raise SnapshotRowsInvalid(str(exc)) from exc
        if version == CHUNKING_PROFILE_VERSION and rows.snapshot.unreliable_count > 0:
            raise ChunkingRefused(
                f"{profile} over {rows.snapshot.content_key!r} is refused: the snapshot carries "
                f"{rows.snapshot.unreliable_count} unreliable block(s); import "
                f"{RELIABLE_CHUNKING_PROFILE_VERSION} instead"
            )

    snapshot = rows.snapshot
    snapshot_id = NormsSnapshotId.parse(snapshot.norms_snapshot_id)
    repository = NormsRepository(session)
    with session.begin_nested():
        by_id = repository.snapshot_row(snapshot_id)
        by_key = repository.snapshot_row_by_key(snapshot.content_key)
        if by_id is not None or by_key is not None:
            reasons = []
            if by_key is not None and by_key.norms_snapshot_id != snapshot.norms_snapshot_id:
                reasons.append(f"the key is held by {by_key.norms_snapshot_id}")
            if by_id is not None and by_id.content_key != snapshot.content_key:
                reasons.append(f"the id names key {by_id.content_key!r}")
            if reasons:
                raise SnapshotImportConflict(
                    f"import of {snapshot.norms_snapshot_id} / {snapshot.content_key!r} is "
                    "refused: " + "; ".join(reasons)
                )
            stored_digest = repository.stored_row_digest(snapshot_id)
            if stored_digest != digest:
                raise SnapshotImportConflict(
                    f"{snapshot.norms_snapshot_id} is stored with row digest {stored_digest}; "
                    f"the import carries {digest}"
                )
            counts = []
            for profile in profiles:
                if not repository.has_chunk_build(snapshot_id, profile):
                    raise SnapshotImportConflict(
                        f"replay of {snapshot.norms_snapshot_id}: profile {profile!r} is not built"
                    )
                counts.append((profile, repository.counts(snapshot_id, profile)))
            return SnapshotImportResult(snapshot_id, snapshot.content_key, False, digest, tuple(counts))

        clashes = repository.foreign_child_ids(rows)
        if clashes:
            raise SnapshotImportConflict(
                f"{len(clashes)} child id(s) belong to another snapshot, first {clashes[0]}"
            )
        repository.insert_snapshot_rows(rows)
        counts = []
        for profile in profiles:
            built = repository.build_chunks_from_stored(snapshot_id, snapshot.content_key, profile)
            stored = repository.counts(snapshot_id, profile)
            if stored != StoredCorpusCounts(len(rows.documents), len(rows.paragraphs), built):
                raise NormsProjectionConflict(
                    f"imported counts {stored!r} do not match the rows for {profile!r}"
                )
            counts.append((profile, stored))
        stored_digest = repository.stored_row_digest(snapshot_id)
        if stored_digest != digest:
            raise NormsProjectionConflict(
                f"stored row digest {stored_digest} != imported {digest}"
            )
    return SnapshotImportResult(snapshot_id, snapshot.content_key, True, digest, tuple(counts))


def main(argv: list[str] | None = None) -> int:
    """Operator command: project a corpus and commit it once to configured PostgreSQL."""
    parser = argparse.ArgumentParser(
        prog="auditmanager.norms.loader",
        description="Atomically load one deterministic normative-corpus projection.",
    )
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument(
        "--target-characters", type=int, default=DEFAULT_TARGET_CHARACTERS
    )
    parser.add_argument(
        "--chunking-version", choices=CHUNKING_VERSIONS, default=DEFAULT_CHUNKING_VERSION
    )
    args = parser.parse_args(argv)

    ledger = None
    if args.ledger is not None:
        if not args.ledger.is_file():
            parser.error(f"repair ledger is not a file: {args.ledger}")
        ledger = RepairLedger.from_document(
            json.loads(args.ledger.read_text(encoding="utf-8"))
        )

    with session_scope() as session:
        result = load_corpus(
            session,
            args.corpus,
            target_characters=args.target_characters,
            repair_ledger=ledger,
            chunking_version=args.chunking_version,
        )
    print(
        json.dumps(
            {
                "norms_snapshot_id": str(result.norms_snapshot_id),
                "content_key": result.content_key,
                "chunking_profile": result.chunking_profile,
                "created": result.created,
                "unreliable_count": result.unreliable_count,
                "row_digest": result.row_digest,
                "documents": result.counts.documents,
                "paragraphs": result.counts.paragraphs,
                "chunks": result.counts.chunks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
