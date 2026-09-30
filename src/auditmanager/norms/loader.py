"""Atomic, idempotent loading of a validated normative corpus into PostgreSQL."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormsSnapshotId
from auditmanager.shared.db.session import session_scope

from .chunking import DEFAULT_TARGET_CHARACTERS, chunking_profile
from .corpus_source import open_corpus_projection
from .repair import RepairLedger
from .repository import NormsProjectionConflict, NormsRepository, StoredCorpusCounts


@dataclass(frozen=True, slots=True)
class CorpusLoadResult:
    norms_snapshot_id: NormsSnapshotId
    content_key: str
    chunking_profile: str
    created: bool
    counts: StoredCorpusCounts


def load_corpus(
    session: Session,
    root: Path,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    *,
    repair_ledger: RepairLedger | None = None,
) -> CorpusLoadResult:
    """Load one effective corpus, leaving commit or rollback to the caller.

    A SAVEPOINT protects callers that catch a validation error: no partial snapshot rows remain
    pending in their outer transaction. The command performs no object-store or provider side
    effect, so this one database boundary is the entire atomic unit.
    """
    projection = open_corpus_projection(
        root,
        target_characters=target_characters,
        repair_ledger=repair_ledger,
    )
    profile = chunking_profile(target_characters)
    repository = NormsRepository(session)

    with session.begin_nested():
        snapshot_id, created = repository.ensure_snapshot(projection)
        if created:
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
            stored = repository.counts(snapshot_id, profile)
            if stored.documents != projection.snapshot.document_count:
                raise NormsProjectionConflict(
                    f"stored snapshot {snapshot_id} has {stored.documents} documents; "
                    f"content key claims {projection.snapshot.document_count}"
                )

    return CorpusLoadResult(
        norms_snapshot_id=snapshot_id,
        content_key=projection.snapshot.content_key,
        chunking_profile=profile,
        created=created,
        counts=stored,
    )


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
        )
    print(
        json.dumps(
            {
                "norms_snapshot_id": str(result.norms_snapshot_id),
                "content_key": result.content_key,
                "chunking_profile": result.chunking_profile,
                "created": result.created,
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
