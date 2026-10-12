"""Operator commands of the embedder.

::

    # host, the repository's virtualenv, DATABASE_URL naming the promotion database
    python -m auditmanager.norms.embedding prepare --snapshot <ns_id> \\
        --chunking-profile characters-v2:1200 --checkpoint .local/norms/builds/<content_key>

    # inside the norms-worker image, --network none (infra/norms-worker/run-build.sh)
    python -m auditmanager.norms.embedding build --snapshot <ns_id> \\
        --chunking-profile characters-v2:1200 --checkpoint /checkpoint [--max-batches N]

    # host again, once every batch is verified
    python -m auditmanager.norms.embedding load --snapshot <ns_id> \\
        --chunking-profile characters-v2:1200 --checkpoint .local/norms/builds/<content_key>

    python -m auditmanager.norms.embedding status --checkpoint <dir>
    python -m auditmanager.norms.embedding embed-texts --in <request.json> --out <response.json>
    python -m auditmanager.norms.embedding self-test

Exit status: 0 done; 2 refused (nothing overwritten, the message names why); 75 (``EX_TEMPFAIL``)
from ``build`` when ``--max-batches`` left batches for the next window.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .builder import run_build
from .checkpoint import (
    DEFAULT_BATCH_CHUNKS,
    BatchState,
    CheckpointRefused,
    batch_status,
    read_plan,
)
from .encoder import EncoderRefused
from .profile import require_snapshot_id
from .texts import EmbedTextsRefused
from .vectors import VectorRefused
from .windowing import WindowingRefused

EXIT_REFUSED = 2
EXIT_RESUME = 75

_REFUSALS: tuple[type[BaseException], ...] = (
    CheckpointRefused,
    EmbedTextsRefused,
    EncoderRefused,
    VectorRefused,
    WindowingRefused,
)


def _snapshot(value: str) -> str:
    try:
        return require_snapshot_id(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.norms.embedding",
        description="Resumable bge-m3-dense-v1 embedding of normative chunks.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "build", "load"):
        command = commands.add_parser(name)
        command.add_argument("--snapshot", type=_snapshot, required=True)
        command.add_argument("--chunking-profile", required=True)
        command.add_argument("--checkpoint", type=Path, required=True)
        if name == "prepare":
            command.add_argument("--batch-chunks", type=int, default=DEFAULT_BATCH_CHUNKS)
        if name == "build":
            command.add_argument("--max-batches", type=int)
    status = commands.add_parser("status")
    status.add_argument("--checkpoint", type=Path, required=True)
    texts = commands.add_parser("embed-texts")
    texts.add_argument("--in", dest="request", type=Path, required=True)
    texts.add_argument("--out", dest="response", type=Path, required=True)
    commands.add_parser("self-test")
    return parser


def _prepare(args: argparse.Namespace) -> int:
    from auditmanager.shared.db.session import session_scope
    from auditmanager.shared.identity import NormsSnapshotId

    from ..embedding_repository import NormEmbeddingConflict
    from .operations import prepare

    try:
        with session_scope() as session:
            plan, created = prepare(
                session,
                args.checkpoint,
                snapshot_id=NormsSnapshotId.parse(args.snapshot),
                chunking_profile=args.chunking_profile,
                batch_chunks=args.batch_chunks,
            )
            # prepare only reads; nothing of this transaction is kept.
            session.rollback()
    except NormEmbeddingConflict as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        json.dumps(
            {
                "created": created,
                "plan_sha256": plan.sha256,
                "content_key": plan.identity.content_key,
                "chunks": plan.chunk_count,
                "batches": len(plan.batches),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load(args: argparse.Namespace) -> int:
    from auditmanager.shared.db.session import session_scope
    from auditmanager.shared.identity import NormsSnapshotId

    from ..embedding_repository import NormEmbeddingConflict
    from .operations import load

    try:
        with session_scope() as session:
            result = load(
                session,
                args.checkpoint,
                snapshot_id=NormsSnapshotId.parse(args.snapshot),
                chunking_profile=args.chunking_profile,
            )
    except NormEmbeddingConflict as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    build = result.build
    print(
        json.dumps(
            {
                "created": build.created,
                "chunk_count": build.chunk_count,
                "window_count": build.window_count,
                "embedding_set_sha256": build.embedding_set_sha256,
            },
            indent=2,
        )
    )
    return 0


def _build(args: argparse.Namespace) -> int:
    from .checkpoint import require_identity
    from .encoder import BgeM3Encoder, require_offline

    # Refuse a wrong directory before the model takes its half minute to load.
    require_offline()
    require_identity(
        read_plan(args.checkpoint),
        norms_snapshot_id=args.snapshot,
        chunking_profile=args.chunking_profile,
    )
    progress = run_build(
        args.checkpoint,
        BgeM3Encoder.load(),
        norms_snapshot_id=args.snapshot,
        chunking_profile=args.chunking_profile,
        max_batches=args.max_batches,
        report=lambda line: print(line, flush=True),
    )
    return 0 if progress.complete else EXIT_RESUME


def _status(args: argparse.Namespace) -> int:
    plan = read_plan(args.checkpoint)
    counts = {state: 0 for state in BatchState}
    for batch in plan.batches:
        status = batch_status(args.checkpoint, plan, batch)
        counts[status.state] += 1
        if status.state is BatchState.INVALID:
            print(f"batch {batch.index}: invalid ({status.reason})")
    print(
        json.dumps(
            {
                "content_key": plan.identity.content_key,
                "chunking_profile": plan.identity.chunking_profile,
                "plan_sha256": plan.sha256,
                "batches": len(plan.batches),
                **{state.value: count for state, count in counts.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _embed_texts(args: argparse.Namespace) -> int:
    from .encoder import BgeM3Encoder
    from .texts import run

    response = run(BgeM3Encoder.load(), args.request, args.response)
    print(f"embed-texts: {len(response['vectors'])} vectors written to {args.response}")
    return 0


def _self_test(_: argparse.Namespace) -> int:
    from .encoder import BgeM3Encoder
    from .selftest import run_self_test

    print(run_self_test(BgeM3Encoder.load()))
    return 0


_COMMANDS = {
    "prepare": _prepare,
    "build": _build,
    "load": _load,
    "status": _status,
    "embed-texts": _embed_texts,
    "self-test": _self_test,
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _COMMANDS[args.command](args)
    except _REFUSALS as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
