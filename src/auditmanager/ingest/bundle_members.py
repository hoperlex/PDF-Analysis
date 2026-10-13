"""Which members of an accepted bundle are stored, under which names, and what a fingerprint covers.

`W55B-INGEST-01` (plan section B3.4). The mapping from a bundle's member to the manifest
entry it becomes is one table, written once, so the publication, the fingerprint and the tests
read the same four rows:

========================== ================================== =========================== =================
member                     manifest role                      blob role                   media type
========================== ================================== =========================== =================
the PDF                    ``source.document``                ``source_document``         application/pdf
``_blocks.json``           ``source.structured_companion``    ``source_structured_..``    application/json
``_results.md``            ``source.markdown``                ``source_markdown``         text/markdown
``_stamp_audit.json``      ``source.stamp_audit``             ``source_stamp_audit``      application/json
========================== ================================== =========================== =================

``_results.html`` is **not** in the table: it is hashed while it is unpacked and dropped, never
stored, served or rendered -- but its digest is part of the command fingerprint, so a bundle
that differs only by its HTML is a different upload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from auditmanager.documents.public import (
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STAMP_AUDIT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STAMP_AUDIT,
    ROLE_SOURCE_STRUCTURED_COMPANION,
)
from auditmanager.storage.public import parse_blob_role

from .bundle_archive import (
    ROLE_BLOCKS,
    ROLE_PDF,
    ROLE_RESULTS_HTML,
    ROLE_RESULTS_MD,
    ROLE_STAMP_AUDIT,
    ExtractedBundle,
)

__all__ = ["STORED_MEMBERS", "StoredMember", "fingerprint_members", "source_filename_of"]


@dataclass(frozen=True, slots=True)
class StoredMember:
    """One row of the table above."""

    member: str
    manifest_role: str
    blob_role: str
    media_type: str


#: In manifest order of publication: the PDF first, then the companions. The stamp audit is
#: optional; the other three are present in every accepted bundle.
STORED_MEMBERS: Final[tuple[StoredMember, ...]] = (
    StoredMember(ROLE_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT, parse_blob_role(ROLE_SOURCE_DOCUMENT),
                 "application/pdf"),
    StoredMember(ROLE_BLOCKS, MANIFEST_ROLE_STRUCTURED_COMPANION,
                 parse_blob_role(ROLE_SOURCE_STRUCTURED_COMPANION), "application/json"),
    StoredMember(ROLE_RESULTS_MD, MANIFEST_ROLE_MARKDOWN, parse_blob_role(ROLE_SOURCE_MARKDOWN),
                 "text/markdown"),
    StoredMember(ROLE_STAMP_AUDIT, MANIFEST_ROLE_STAMP_AUDIT,
                 parse_blob_role(ROLE_SOURCE_STAMP_AUDIT), "application/json"),
)

_CONTROL: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1f\x7f]")
_MAX_NAME: Final[int] = 255


def source_filename_of(bundle: ExtractedBundle) -> str:
    """The PDF member's name, decoded, as a plain base name for display.

    The decoded name may carry a directory part (``dir/a.pdf`` is not refused by the archive
    rules), control characters or more than 255 characters; the version's ``source_filename``
    is a plain base name of at most 255 characters (``validate_source_filename``), so the last
    path component is taken, control characters become ``_`` and the length is cut. It is a
    display value: nothing resolves, compares or opens it.
    """
    shown = bundle.members[ROLE_PDF].display_name
    base = shown.rsplit("/", 1)[-1]
    cleaned = _CONTROL.sub("_", base).strip()
    return cleaned[:_MAX_NAME] or "document.pdf"


def fingerprint_members(bundle: ExtractedBundle) -> dict[str, str | None]:
    """Every member's digest, the HTML's included, ``None`` for an optional member absent."""
    digests: dict[str, str | None] = {}
    for role in (ROLE_PDF, ROLE_BLOCKS, ROLE_RESULTS_MD, ROLE_RESULTS_HTML, ROLE_STAMP_AUDIT):
        member = bundle.members.get(role)
        digests[role] = None if member is None else member.sha256
    return digests
