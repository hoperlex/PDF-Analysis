"""Rows for the read-model suites (`SECTION-READ-MODEL-01`): projects, document sets and
versions with and without an expert's classification, on a migrated PostgreSQL.

Projects, documents, the classification and the expert go through their owning boundaries
(``documents``, ``access``). A *version* is written by one INSERT of exactly the columns
``document_version`` requires: a published version normally carries a stored PDF and a
manifest, which neither the dashboard's count nor the section membership reads, and a suite
that stored real Blobs to prove a join would be asserting the storage adapter instead.
The current-head pointer is moved by the same UPDATE ``publish_version`` ends with.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.identity import ProjectUid, VersionUid

PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal

_INSERT_VERSION = text(
    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
    "media_type, byte_size, sha256, page_count) "
    "VALUES (:version_uid, :document_uid, "
    "  (SELECT coalesce(max(version_ordinal), 0) + 1 FROM document_version "
    "   WHERE document_uid = :document_uid), "
    "  'application/pdf', 1024, :sha256, :page_count)"
)
_POINT_AT = text(
    "UPDATE document SET current_version_uid = :version_uid WHERE document_uid = :document_uid"
)


class Seeder:
    """Build a deployment's documents, one call per fact, on the session given."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.documents = DocumentRepository()
        self._serial = 0
        self._expert: str | None = None

    @property
    def expert(self) -> str:
        """The confirming expert, created on first use."""
        if self._expert is None:
            users = UserRepository()
            accounts = AccountRepository()
            uid = str(users.create_user(self.session, "anna@example.com", PASSWORD).user_uid)
            accounts.complete_profile(
                self.session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
            )
            accounts.grant_role(self.session, user_uid=uid, role="expert", granted_by=None)
            self._expert = uid
        return self._expert

    def project(self, name: str) -> str:
        return str(self.documents.create_project(self.session, name).project_uid)

    def document(self, project_uid: str, title: str, *, legacy_section: str | None = None) -> str:
        """A set. ``legacy_section`` is the old document-level label, never a confirmation."""
        return str(
            self.documents.create_document(
                self.session, ProjectUid.parse(project_uid), title, legacy_section
            )
        )

    def version(
        self,
        document_uid: str,
        *,
        classified: tuple[str, str] | None = None,
        current: bool = True,
        pages: int = 3,
    ) -> str:
        """Publish the set's next version; confirm ``(stage, section)`` on it if given.

        ``current=False`` leaves the head where it was -- a version published and not (yet)
        the one the set shows.
        """
        self._serial += 1
        version_uid = str(VersionUid.new())
        self.session.execute(
            _INSERT_VERSION,
            {
                "version_uid": version_uid,
                "document_uid": document_uid,
                "sha256": hashlib.sha256(f"version-{self._serial}".encode()).hexdigest(),
                "page_count": pages,
            },
        )
        if current:
            self.session.execute(_POINT_AT, {"version_uid": version_uid, "document_uid": document_uid})
        if classified is not None:
            stage, section = classified
            written = self.documents.insert_classification(
                self.session,
                version_uid=VersionUid(version_uid),
                project_stage=stage,
                section_code=section,
                confirmed_by_user_uid=self.expert,
            )
            assert written is not None
        return version_uid

    def point_at(self, document_uid: str, version_uid: str) -> None:
        """Move the set's head to ``version_uid`` (a published version of that set)."""
        self.session.execute(_POINT_AT, {"version_uid": version_uid, "document_uid": document_uid})

    def commit(self) -> None:
        self.session.commit()
