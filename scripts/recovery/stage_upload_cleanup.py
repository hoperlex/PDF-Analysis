"""Reconcile cancelled stage-upload multipart tokens after an interrupted API process.

Run with the application's DATABASE_URL and S3_* environment. The database's
cancelled rows and immutable tokens are the work list; no bucket listing or
path supplied by a user is used. Safe to repeat after any interruption.
"""

from __future__ import annotations

import argparse

from auditmanager.comparison.public import StageUploadLifecycleService
from auditmanager.shared.db import get_session_factory
from auditmanager.storage.public import S3BlobStore, S3StorageSettings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args(argv)
    if not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be from 1 to 1000")
    store = S3BlobStore(S3StorageSettings.from_env())
    service = StageUploadLifecycleService(get_session_factory(), store)
    count = service.sweep_cancelled(limit=args.page_size)
    print(f"stage-upload-cleanup: reconciled {count} cancelled batches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
