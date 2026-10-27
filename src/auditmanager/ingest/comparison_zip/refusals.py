"""How a ZIP set is refused: the constraint names, their sentences, and the renaming of the
portal reader's own refusals.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12; decision 25: «a new reason under an existing code
is the default»). Every refusal is ``validation_failed`` with ``field: "file"`` and one of the
:data:`CONSTRAINTS` below -- the code the portal bundle uses, with reasons of this kind of
upload's own, because the remedy differs: a portal bundle is told to fetch the portal's files,
a ZIP set is told what is wrong with the set.

**No refusal carries a name, a size or a byte of the archive.** Each sentence is fixed, and the
``DomainError`` envelope screens it as a message all the same.

The shared reader (:mod:`auditmanager.ingest.bundle_archive`) raises the portal bundle's
constraints for the rules it applies to every kind of upload (the end records, the entry count,
the declared and the counted sizes, the ratio). :func:`translate` renames those, and refuses
(as a defect, loudly) to pass a portal constraint that has no counterpart here: an unnamed
refusal would be a silent fallback.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["CONSTRAINTS", "FIELD", "message_of", "refuse_set", "translate"]

#: Every refusal of a ZIP set is about the uploaded file.
FIELD: Final[str] = "file"

_MESSAGES: Final[dict[str, str]] = {
    "comparison_zip_unreadable": "The upload could not be read as a ZIP archive.",
    "comparison_zip_entry_count": "The archive holds more entries than a ZIP set can.",
    "comparison_zip_member_name": "A member of the archive has a name that is not a plain relative name.",
    "comparison_zip_symlink": "A member of the archive is a symbolic link.",
    "comparison_zip_encrypted_member": "A member of the archive is encrypted.",
    "comparison_zip_compression_method": (
        "A member of the archive uses a compression method other than stored or deflate."
    ),
    "comparison_zip_duplicate_member": "Two members of the archive have the same name.",
    "comparison_zip_member_kind": (
        "A member of the archive is neither a PDF document nor, at the first level, a ZIP archive."
    ),
    "comparison_zip_nested_depth": "The archive holds an archive inside an archive that is itself inside it.",
    "comparison_zip_member_size": "A member of the archive is larger than a ZIP set allows.",
    "comparison_zip_total_size": "The members of the archive together are larger than a ZIP set allows.",
    "comparison_zip_compression_ratio": "The archive is compressed more than a ZIP set allows.",
    "comparison_zip_empty": "The archive holds no PDF document.",
}

#: The registered reasons of a ZIP set, in the order the rules are applied.
CONSTRAINTS: Final[tuple[str, ...]] = tuple(_MESSAGES)

#: The portal reader's constraint -> this kind of upload's. Only the rules the shared reader
#: applies to every policy appear: the ones its judge applies for the portal alone (a directory
#: entry, a stem, the member set, the block list, the stamp audit) cannot be raised under this
#: policy, and an attempt to pass one on is a defect, not a refusal.
_FROM_PORTAL: Final[dict[str, str]] = {
    "portal_bundle_required": "comparison_zip_unreadable",
    "bundle_unreadable": "comparison_zip_unreadable",
    "bundle_entry_count": "comparison_zip_entry_count",
    "bundle_member_name": "comparison_zip_member_name",
    "bundle_symlink": "comparison_zip_symlink",
    "bundle_encrypted_member": "comparison_zip_encrypted_member",
    "bundle_compression_method": "comparison_zip_compression_method",
    "bundle_duplicate_member": "comparison_zip_duplicate_member",
    "bundle_member_size": "comparison_zip_member_size",
    "bundle_total_size": "comparison_zip_total_size",
    "bundle_compression_ratio": "comparison_zip_compression_ratio",
}


def message_of(constraint: str) -> str:
    """The fixed sentence of a registered constraint."""
    return _MESSAGES[constraint]


def refuse_set(constraint: str) -> DomainError:
    """The one refusal this package raises: ``validation_failed``, ``field: "file"``."""
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=_MESSAGES[constraint],
        field=FIELD,
        constraint=constraint,
    )


def translate(error: DomainError) -> DomainError:
    """The set's refusal for one the shared reader raised.

    A refusal that already names one of :data:`CONSTRAINTS` passes unchanged. A portal
    constraint is renamed through the table above. Anything else is a defect of the reader or
    of the table, and is raised as one rather than passed to a caller under a name that does
    not describe it.
    """
    if error.code is not ErrorCode.VALIDATION_FAILED:
        return error
    constraint = error.detail_fields.get("constraint")
    if constraint in _MESSAGES:
        return error
    renamed = _FROM_PORTAL.get(str(constraint))
    if renamed is None:
        raise RuntimeError("the archive reader raised a refusal that a ZIP set does not name")
    return refuse_set(renamed)
