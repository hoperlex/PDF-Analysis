"""One-shot deploy loader: python -m auditmanager.releases.load."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import auditmanager

from auditmanager.releases.notes import read_notes
from auditmanager.releases.product_version import read_product_version
from auditmanager.releases.repository import load_notes
from auditmanager.shared.db import (
    DatabaseSettings,
    create_database_engine,
    create_session_factory,
    parse_database_url,
)


def main() -> int:
    try:
        version = read_product_version()
        root = Path(auditmanager.__file__).resolve().parents[2]
        notes = read_notes(root / "release-notes")
        url = os.environ.get("DATABASE_URL", "")
        engine = create_database_engine(DatabaseSettings(url=parse_database_url(url)))
        try:
            report = load_notes(
                create_session_factory(engine), notes=notes, product_version=version
            )
        finally:
            engine.dispose()
    except (FileNotFoundError, ValueError) as exc:
        print(f"release-notes: {exc}", file=sys.stderr)
        return 2
    print(
        "release-notes: "
        f"inserted={len(report.inserted)} appended={len(report.appended)} "
        f"unchanged={len(report.unchanged)} older={len(report.older_revision)} "
        f"future_untouched={len(report.future_untouched)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
