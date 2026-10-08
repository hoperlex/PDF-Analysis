"""Read the one product version from the file shipped with the API."""

from __future__ import annotations

from pathlib import Path

import auditmanager

from auditmanager.releases.versioning import canonical_semver_sort_key


def read_product_version() -> str:
    """Return the exact canonical version line, refusing absent or malformed data.

    A single terminal LF is accepted as a file terminator. No whitespace,
    CRLF, extra line or build metadata is normalized away.
    """
    root = Path(auditmanager.__file__).resolve().parents[2]
    raw = (root / "VERSION").read_bytes()
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    try:
        version = raw.decode("ascii")
    except UnicodeDecodeError:
        raise ValueError("noncanonical product VERSION: non-ASCII bytes") from None
    canonical_semver_sort_key(version)
    return version
