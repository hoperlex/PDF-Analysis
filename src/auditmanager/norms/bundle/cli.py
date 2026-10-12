"""Operator commands of the promotion bundle (`W54-PLAN.md` §3.5).

::

    # this host, the repository's virtualenv, DATABASE_URL naming the promotion database
    python -m auditmanager.norms.bundle export --snapshot <ns_id> \\
        --chunking-profile characters-v2:1200 --corpus .local/norms/corpus \\
        --drop-sums .local/norms/corpus-sums/<date>/SHA256SUMS \\
        [--ledger .local/norms/repairs/<date>/ledger.json] --out .local/norms/bundles
    python -m auditmanager.norms.bundle verify <bundle dir>

    # the stand, only through the inbound key (receive-bundle.sh runs these, fixed)
    python -m auditmanager.norms.bundle import /bundles/<KEY> --copy-record /run/copy-record.json
    python -m auditmanager.norms.bundle report /bundles/<KEY> --copy-record /run/copy-record.json
    python -m auditmanager.norms.bundle requeue /bundles/<KEY>

Exit status: 0 done (``report``: a full match and no custody incident); 1 ``report`` found a
difference or a custody incident; 2 refused (``bundle: REFUSED [<reason>]: …`` on stderr,
nothing written by the refused step) -- including an object store or database that cannot
be configured or reached (``blob_store_unavailable``, ``database_unavailable``,
`W54-JUDGE-A` F5); 75 the import is not finished (an admission is pending or poisoned; the
bundle is kept, run ``import`` again, after ``requeue`` for poisoned ones).

``import`` and ``report`` both open the object store: ``report`` runs the custody reconciler
before its comparison (`W54-JUDGE-A` F2), because the inbound key discards ``objects/`` after
a report that exits 0.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from auditmanager.shared.db.errors import DatabaseError
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import BlobStore, StorageError

from .errors import EXIT_OK, EXIT_REFUSED, BundleRefused
from .layout import MANIFEST_NAME, verify_bundle
from .manifest import parse_manifest
from .stand import Stand, import_bundle, report_bundle, requeue_bundle

StandFactory = Callable[[bool], Stand]


def blob_store_from_environment() -> BlobStore:
    """The stand's S3/MinIO store, configured like the api service's.

    The adapter lives in the storage context; ALR-05 lets this context reach it only
    through ``auditmanager.storage.public``. Until that module exports ``S3BlobStore`` and
    ``S3StorageSettings`` (one line, the integrator's; `W54-BUNDLE-01` report §5), ``import``
    refuses here, loudly, rather than reaching past the boundary.
    """
    try:
        from auditmanager.storage.public import (  # type: ignore[attr-defined]
            S3BlobStore,
            S3StorageSettings,
        )
    except ImportError:
        raise BundleRefused(
            "blob_store_unavailable",
            "auditmanager.storage.public does not export S3BlobStore and S3StorageSettings, so "
            "the import cannot reach the object store (W54-BUNDLE-01 report §5, integrator step 1)",
        ) from None
    store = S3BlobStore(S3StorageSettings.from_env())
    store.check_access()
    return store


def stand_from_environment(with_store: bool) -> Stand:
    from auditmanager.shared.db import get_engine, get_session_factory

    return Stand(
        session_factory=get_session_factory(),
        engine=get_engine(),
        store=blob_store_from_environment() if with_store else None,
    )


def _export(args: argparse.Namespace) -> int:
    from auditmanager.shared.db.session import session_scope

    from .export import export_bundle

    with session_scope() as session:
        result = export_bundle(
            session,
            snapshot_id=args.snapshot,
            chunking_profile=args.chunking_profile,
            corpus=args.corpus,
            drop_sums=args.drop_sums,
            ledger=args.ledger,
            out=args.out,
            copy_objects=args.copy_objects,
            without_build=args.without_build,
        )
        session.rollback()
    manifest = result.manifest
    print(f"bundle: {result.directory}{'' if result.created else ' (already exported, unchanged)'}")
    print(f"content_key: {manifest.content_key}")
    print(f"bundle_digest: {result.directory.name.rsplit('+', 1)[1]}")
    print(f"row_digest: {manifest.row_digest}")
    print(
        "build: "
        + ("absent (the importer refuses this bundle)" if manifest.build is None else manifest.build.embedding_set_sha256)
    )
    counts = manifest.counts
    print(
        f"counts: documents {counts.documents}, paragraphs {counts.paragraphs} "
        f"({counts.unreliable_paragraphs} unreliable), chunks {counts.chunks}, windows {counts.windows}, "
        f"objects {counts.objects} ({manifest.object_bytes} bytes), slots {counts.slots}"
    )
    print(f"binding_digest: {manifest.binding_digest}")
    print(f"db_growth_bytes: {manifest.db_growth_bytes}")
    return EXIT_OK


def _verify(args: argparse.Namespace) -> int:
    bundle = verify_bundle(args.bundle)
    manifest = parse_manifest((args.bundle / MANIFEST_NAME).read_bytes())
    manifest.check_against(bundle)
    print(f"verified: {args.bundle.name} ({len(bundle.sums)} files, every byte re-hashed)")
    return EXIT_OK


def main(argv: Sequence[str] | None = None, *, stand_factory: StandFactory | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m auditmanager.norms.bundle")
    commands = parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export", help="write a verified bundle (this host)")
    export.add_argument("--snapshot", required=True)
    export.add_argument("--chunking-profile", required=True)
    export.add_argument("--corpus", required=True, type=Path)
    export.add_argument("--drop-sums", required=True, type=Path)
    export.add_argument("--ledger", type=Path)
    export.add_argument("--out", required=True, type=Path)
    export.add_argument("--copy-objects", action="store_true")
    export.add_argument("--without-build", action="store_true")

    verify = commands.add_parser("verify", help="re-hash a bundle and check its manifest")
    verify.add_argument("bundle", type=Path)

    for name in ("import", "report"):
        command = commands.add_parser(name)
        command.add_argument("bundle", type=Path)
        command.add_argument("--copy-record", required=True, type=Path)
    requeue = commands.add_parser("requeue")
    requeue.add_argument("bundle", type=Path)

    args = parser.parse_args(argv)
    build_stand = stand_factory or stand_from_environment
    try:
        if args.command == "export":
            return _export(args)
        if args.command == "verify":
            return _verify(args)
        if args.command == "import":
            return import_bundle(args.bundle, copy_record=args.copy_record, stand=build_stand(True))
        if args.command == "report":
            return report_bundle(args.bundle, copy_record=args.copy_record, stand=build_stand(True))
        return requeue_bundle(args.bundle, stand=build_stand(False))
    except BundleRefused as exc:
        print(f"bundle: REFUSED [{exc.reason}]: {exc.message}", file=sys.stderr)
        return EXIT_REFUSED
    except DomainError as exc:
        reason = getattr(exc, "reason", None) or exc.code.value
        print(f"bundle: REFUSED [{reason}]: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except DatabaseError as exc:
        print(f"bundle: REFUSED [database_unavailable]: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except StorageError as exc:
        # The settings (`StorageConfigurationError`), a missing bucket, an outage or an
        # integrity failure: all render key-free (`storage.errors`), and none is a report
        # mismatch, which is what exit 1 would say.
        print(f"bundle: REFUSED [blob_store_unavailable]: {exc}", file=sys.stderr)
        return EXIT_REFUSED


__all__ = ["blob_store_from_environment", "main", "stand_from_environment"]
