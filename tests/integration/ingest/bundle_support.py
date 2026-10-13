"""Shared helpers for the portal-bundle tests of this directory (`W55B-INGEST-01`).

Not a test module. It judges an archive with the product's own reader and envelope and says
which registered constraint refused it -- the one fact every refusal test compares -- and it
hands out the committed bundles and the generators' archives by name. ``tools/fixtures`` is
put on the path by this directory's ``conftest.py``.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from auditmanager.ingest.bundle_archive import BundleLimits, extract_bundle
from auditmanager.ingest.bundle_envelope import BundleAdmission, admit_bundle
from auditmanager.shared.errors import DomainError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BUNDLES = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles"


def committed(name: str) -> bytes:
    """The bytes of one committed bundle, e.g. ``committed("ar_baseline.zip")``."""
    return (BUNDLES / name).read_bytes()


def refusal_of(error: DomainError) -> tuple[str, str, str]:
    """(field, constraint, message) of a ``validation_failed`` the envelope raised."""
    fields: dict[str, Any] = dict(error.detail_fields)
    return str(fields.get("field")), str(fields.get("constraint")), str(error)


def judge(
    source: bytes | Path, limits: BundleLimits | None = None
) -> tuple[str | None, str | None, BundleAdmission | None]:
    """Run the archive rules and the content rules on an upload.

    Returns ``(field, constraint, admission)``: the refusal's field and constraint and no
    admission, or ``(None, None, admission)`` for a bundle that is accepted. Nothing but
    ``DomainError`` is caught: anything else is a defect the test must see.
    """
    handle = io.BytesIO(source) if isinstance(source, bytes) else source.open("rb")
    try:
        kwargs = {} if limits is None else {"limits": limits}
        try:
            with extract_bundle(handle, **kwargs) as bundle:
                return None, None, admit_bundle(bundle)
        except DomainError as refused:
            field, constraint, _message = refusal_of(refused)
            return field, constraint, None
    finally:
        handle.close()
