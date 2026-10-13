"""Constants and identifier derivation shared by every portal-bundle builder.

Everything that could vary from run to run is fixed here, so a builder cannot pick up a
clock, a PRNG or an environment value by accident: the timestamps are literals and the
identifiers are digests of the document stem and a running number.
"""

from __future__ import annotations

import base64
import hashlib

MiB = 1024 * 1024

# The portal's timestamps, as the real export writes them, held constant.
GENERATED_AT_JSON = "2026-07-24T07:45:12.069432Z"
GENERATED_AT_MARKDOWN = "2026-07-24 07:45:12 UTC"
BLOCK_CREATED_AT = "2026-07-07 07:36:38 UTC"
STAMP_AUDIT_GENERATED_AT = "2026-08-25T09:47:54.548970+00:00"

COORDINATE_SPACE = "normalized_page_top_left"
SCHEMA_VERSION = 1
RENDER_DPI = 300

# The real portal serves crops from a capability URL. A fixture must never point at a
# host that could answer, so the same path shape sits under the reserved `.invalid` TLD
# (RFC 2606): nothing resolves it, whatever fetches it by mistake.
CROP_URL_BASE = "https://portal.invalid/api/crops/"

# Freeze values (W55B-FREEZE-01, plan B3.1). The member size bound and the stamp-audit
# cap are not frozen: INGEST chooses them, so the validator takes them as arguments.
MAX_ENTRIES = 8
MAX_TOTAL_UNCOMPRESSED_BYTES = 300 * MiB
MAX_COMPRESSION_RATIO = 100
MAX_UPLOAD_BYTES = 250 * MiB
MIN_PAGES = 1
MAX_PAGES = 500

# Member roles by the suffix of the raw name. Matching is on bytes, never on a decoded
# name, because the stem is compared on the raw bytes too.
ROLE_PDF = "pdf"
ROLE_BLOCKS = "blocks"
ROLE_RESULTS_MD = "results_md"
ROLE_RESULTS_HTML = "results_html"
ROLE_STAMP_AUDIT = "stamp_audit"

ROLE_SUFFIX: dict[str, bytes] = {
    ROLE_PDF: b".pdf",
    ROLE_BLOCKS: b"_blocks.json",
    ROLE_RESULTS_MD: b"_results.md",
    ROLE_RESULTS_HTML: b"_results.html",
    ROLE_STAMP_AUDIT: b"_stamp_audit.json",
}
REQUIRED_ROLES = (ROLE_PDF, ROLE_BLOCKS, ROLE_RESULTS_MD)
OPTIONAL_ROLES = (ROLE_RESULTS_HTML, ROLE_STAMP_AUDIT)
# The order members are written in. Fixed, so two builds lay out the archive alike.
ROLE_ORDER = (ROLE_PDF, ROLE_BLOCKS, ROLE_RESULTS_MD, ROLE_RESULTS_HTML, ROLE_STAMP_AUDIT)

KIND_TEXT = "text"
KIND_IMAGE = "image"
KIND_STAMP = "stamp"
KINDS = (KIND_TEXT, KIND_IMAGE, KIND_STAMP)


def role_of(name: bytes) -> str | None:
    """The member role a raw name's suffix gives it, or None for an unknown suffix."""
    for role, suffix in ROLE_SUFFIX.items():
        if name.endswith(suffix):
            return role
    return None


def stem_of(name: bytes, role: str) -> bytes:
    return name[: len(name) - len(ROLE_SUFFIX[role])]


def _digest(label: str) -> bytes:
    return hashlib.sha256(label.encode("utf-8")).digest()


def block_id(stem: str, kind: str, number: int) -> str:
    """`blk_` and 32 hex digits, derived from the stem, the kind and a running number."""
    return "blk_" + hashlib.sha256(f"{stem}:{kind}:{number}".encode("utf-8")).hexdigest()[:32]


def document_id(stem: str) -> str:
    """The portal's own document id (`doc_` and 32 hex digits). The product ignores it."""
    return "doc_" + hashlib.sha256(f"{stem}:document".encode("utf-8")).hexdigest()[:32]


def crop_url(identifier: str) -> str:
    """A 20-character crop id in the portal's URL-safe alphabet, derived from the block."""
    token = base64.urlsafe_b64encode(_digest(f"crop:{identifier}")).decode("ascii")[:20]
    return CROP_URL_BASE + token


def page_px(points: float) -> int:
    """Rendered size of a PDF page dimension at the portal's 300 dpi."""
    return round(points * RENDER_DPI / 72)
