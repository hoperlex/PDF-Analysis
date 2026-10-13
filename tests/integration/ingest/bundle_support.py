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


def bundle_around(pdf: bytes, stem: str = "member", **options: Any) -> bytes:
    """The three required members around ``pdf``, whatever ``pdf`` is.

    The block list and the markdown are those of the AR baseline document, so a PDF that is
    broken (not a PDF, encrypted, too many pages) is refused for the PDF member's own rule
    before either is read -- which is the point of using this for it. ``options`` reach
    ``portal_bundle.bundle.make_files`` (e.g. ``html=True``).
    """
    import dataclasses

    from portal_bundle import bundle as builders
    from portal_bundle import zipwrite

    baseline = (REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf").read_bytes()
    files = dataclasses.replace(builders.make_files(baseline, stem, **options), pdf=pdf)
    return zipwrite.build_zip(builders.pack(files))


def bundle_for(pdf: bytes, stem: str = "document", **options: Any) -> bytes:
    """A minimal bundle (PDF, block list, markdown) built around ``pdf`` from its own text.

    One TEXT block per page that has a text layer, carrying that text; for a PDF the fixtures'
    independent reader can read. Use ``bundle_around`` for a PDF that is broken, or that is the
    AR baseline with something appended.
    """
    from portal_bundle import bundle as builders
    from portal_bundle import zipwrite

    return zipwrite.build_zip(builders.pack(builders.make_files(pdf, stem, **options)))
