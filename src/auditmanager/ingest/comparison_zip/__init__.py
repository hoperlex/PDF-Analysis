"""A safe reader for ZIP sets of whole stages: many PDFs in one archive.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12, plan `R3-17`). Reached as
``auditmanager.ingest.comparison_zip`` from inside the ``ingest`` context::

    from auditmanager.ingest.comparison_zip import extract_pdf_set

    with open("stage.zip", "rb") as upload:
        with extract_pdf_set(upload) as found:        # raises DomainError / SetMemberRefused
            for member in found.members:
                member.ordinal, member.sha256, member.size   # identity
                member.display_name                         # a hint, never identity
                with found.open(member) as pdf: ...         # the temporary file

The portal bundle's archive reader (:mod:`auditmanager.ingest.bundle_archive`) does the work
under a policy; this package is the set policy, its refusals, and the reader that composes
the two levels of a set. See :mod:`~auditmanager.ingest.comparison_zip.policy` for the bounds
and :mod:`~auditmanager.ingest.comparison_zip.reader` for the flow.
"""

from __future__ import annotations

from auditmanager.ingest.bundle_archive import looks_like_zip

from .policy import (
    DEFAULT_SET_POLICY,
    SET_DIRECTORY_BYTES,
    SET_MAX_ENTRIES,
    SET_MAX_NESTING,
    SET_MAX_RATIO,
    SET_MEMBER_BYTES,
    SET_TOTAL_BYTES,
    SetPolicy,
)
from .reader import (
    MAX_HINT,
    ExtractedSet,
    SetMember,
    SetMemberRefused,
    extract_pdf_set,
    inspect_pdf_member,
)
from .refusals import CONSTRAINTS, FIELD

__all__ = [
    "CONSTRAINTS",
    "DEFAULT_SET_POLICY",
    "ExtractedSet",
    "FIELD",
    "MAX_HINT",
    "SET_DIRECTORY_BYTES",
    "SET_MAX_ENTRIES",
    "SET_MAX_NESTING",
    "SET_MAX_RATIO",
    "SET_MEMBER_BYTES",
    "SET_TOTAL_BYTES",
    "SetMember",
    "SetMemberRefused",
    "SetPolicy",
    "extract_pdf_set",
    "inspect_pdf_member",
    "looks_like_zip",
]
