"""SELECT-only preflight for two explicitly named versions of one document set.

The glossary defines a Document as the logical drawing set. Version UIDs are
identities; the per-document ordinal only proves requested older-to-newer
order. This reader does not infer sheet links, authorize a comparison or read
content bytes. The caller owns the transaction and later approved-link state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import (
    DocumentUid,
    IdentityError,
    ProjectUid,
    VersionUid,
)


_SHA256: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
# W55B-SEAL-01 and migration 0021 admit 1..500 pages per published version.
MAX_VERSION_PAGES: Final[int] = 500
_VERSIONS = text("""
    SELECT v.version_uid, v.document_uid AS version_document_uid,
           d.document_uid AS set_document_uid, d.project_uid,
           v.version_ordinal, v.state, v.sha256, v.byte_size,
           v.page_count, v.media_type
    FROM document_version v
    JOIN document d ON d.document_uid = v.document_uid
    WHERE v.version_uid IN (:source_version_uid, :target_version_uid)
    ORDER BY v.version_uid
""")


class VersionPairRefused(ValueError):
    """The stored versions do not prove the explicitly requested set and order."""


@dataclass(frozen=True, slots=True)
class VersionFacts:
    version_uid: str
    document_uid: str
    project_uid: str
    version_ordinal: int
    sha256: str
    byte_size: int
    page_count: int
    media_type: str


@dataclass(frozen=True, slots=True)
class OrderedVersionPair:
    project_uid: str
    document_uid: str
    source: VersionFacts
    target: VersionFacts


def _identity(value: str, kind: type, label: str) -> str:
    try:
        return str(kind.parse(value))
    except (IdentityError, TypeError):
        raise VersionPairRefused(f"{label}_invalid") from None


def _version_facts(row: object, *, project_uid: str, document_uid: str) -> VersionFacts:
    if not hasattr(row, "__getitem__"):
        raise VersionPairRefused("version_row_invalid")
    try:
        version_uid = _identity(row["version_uid"], VersionUid, "stored_version_uid")
        version_document_uid = _identity(
            row["version_document_uid"], DocumentUid, "stored_document_uid"
        )
        set_document_uid = _identity(row["set_document_uid"], DocumentUid, "stored_set_uid")
        stored_project_uid = _identity(row["project_uid"], ProjectUid, "stored_project_uid")
        ordinal, state = row["version_ordinal"], row["state"]
        sha256, byte_size = row["sha256"], row["byte_size"]
        page_count, media_type = row["page_count"], row["media_type"]
    except (KeyError, TypeError):
        raise VersionPairRefused("version_row_invalid") from None
    if version_document_uid != set_document_uid or set_document_uid != document_uid:
        raise VersionPairRefused("version_set_mismatch")
    if stored_project_uid != project_uid:
        raise VersionPairRefused("version_project_mismatch")
    if state != "published":
        raise VersionPairRefused("version_not_published")
    if type(ordinal) is not int or ordinal < 1:
        raise VersionPairRefused("version_ordinal_invalid")
    if not isinstance(sha256, str) or _SHA256.fullmatch(sha256) is None:
        raise VersionPairRefused("version_digest_invalid")
    if type(byte_size) is not int or byte_size < 0:
        raise VersionPairRefused("version_byte_size_invalid")
    if type(page_count) is not int or not 1 <= page_count <= MAX_VERSION_PAGES:
        raise VersionPairRefused("version_page_count_invalid")
    if media_type != "application/pdf":
        raise VersionPairRefused("version_media_type_invalid")
    return VersionFacts(
        version_uid, set_document_uid, stored_project_uid, ordinal,
        sha256, byte_size, page_count, media_type,
    )


def read_ordered_version_pair(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    source_version_uid: str,
    target_version_uid: str,
) -> OrderedVersionPair:
    """Prove exact current project/set membership and source-before-target order.

    One SELECT sees both immutable version rows and the set's current project
    membership in one statement snapshot. The caller must keep a consistent
    transaction when it subsequently reads approved links or source bytes.
    """
    project = _identity(project_uid, ProjectUid, "project_uid")
    document = _identity(document_uid, DocumentUid, "document_uid")
    source_uid = _identity(source_version_uid, VersionUid, "source_version_uid")
    target_uid = _identity(target_version_uid, VersionUid, "target_version_uid")
    if source_uid == target_uid:
        raise VersionPairRefused("same_version")

    rows = session.execute(_VERSIONS, {
        "source_version_uid": source_uid,
        "target_version_uid": target_uid,
    }).mappings().all()
    if len(rows) != 2:
        raise VersionPairRefused("version_pair_incomplete")
    by_uid: dict[str, VersionFacts] = {}
    for row in rows:
        facts = _version_facts(row, project_uid=project, document_uid=document)
        if facts.version_uid in by_uid or facts.version_uid not in {source_uid, target_uid}:
            raise VersionPairRefused("version_pair_identity_mismatch")
        by_uid[facts.version_uid] = facts
    if set(by_uid) != {source_uid, target_uid}:
        raise VersionPairRefused("version_pair_identity_mismatch")
    source, target = by_uid[source_uid], by_uid[target_uid]
    if source.version_ordinal >= target.version_ordinal:
        raise VersionPairRefused("version_order_invalid")
    return OrderedVersionPair(project, document, source, target)


__all__ = [
    "MAX_VERSION_PAGES", "OrderedVersionPair", "VersionFacts", "VersionPairRefused",
    "read_ordered_version_pair",
]
