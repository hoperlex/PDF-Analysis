"""`CMP-INGEST-01`: what ``DocumentRepository.publish_version`` refuses for the new kind of version, typed.

The database refuses the same things with a constraint violation; the repository refuses them first, with the typed
``validation_failed`` a caller can answer, so a driver error is never what a reviewer reads.
"""

from __future__ import annotations

import pytest

from auditmanager.documents.public import (
    MANIFEST_ROLE_COMPARISON_PDF,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    UPLOAD_KIND_COMPARISON_PDF,
    DocumentRepository,
    ManifestEntry,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ProjectUid
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role
from tests.integration.ingest.comparison_pdf.support import sha256


def _published(session, *, role: str):
    digest = sha256(b"documents rules")
    blob_id = derive_blob_id(sha256=digest, size=10)
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(blob_id=blob_id, upload_token="mpu-" + "2" * 32, sha256=digest, size=10,
                                                role=parse_blob_role("comparison_pdf"), media_type="application/pdf"))
    blobs.mark_available(session, blob_id)
    return ManifestEntry(role, blob_id, digest, 10, "application/pdf"), digest


class TestAComparisonVersionIsRefusedWhatItCannotHold:
    def _call(self, session_factory, project, **overrides):
        with session_factory() as session:
            documents = DocumentRepository()
            document = documents.create_document(session, ProjectUid.parse(str(project.project_uid)), "документ")
            entry, digest = _published(session, role=MANIFEST_ROLE_COMPARISON_PDF)
            arguments = dict(document_uid=document, media_type="application/pdf", byte_size=10, sha256=digest, page_count=1,
                             source_filename="a.pdf", entries=(entry,), upload_kind=UPLOAD_KIND_COMPARISON_PDF)
            arguments.update(overrides)
            return documents.publish_version(session, **arguments)

    def test_it_publishes_without_the_portal_bundles_counts(self, session_factory, project) -> None:
        assert self._call(session_factory, project) is not None

    def test_it_holds_none_of_the_portal_bundles_counts(self, session_factory, project) -> None:
        refused = None
        with pytest.raises(DomainError) as caught:
            self._call(session_factory, project, text_character_count=5, textless_pages=(), recognised_character_count=0)
        refused = caught.value
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert refused.detail_fields["constraint"] == "a comparison-only version holds no portal bundle counts"

    def test_a_kind_outside_the_two_is_refused(self, session_factory, project) -> None:
        with pytest.raises(DomainError) as caught:
            self._call(session_factory, project, upload_kind="something_else")
        assert (caught.value.detail_fields["field"], caught.value.detail_fields["constraint"]) == ("upload_kind", "enum")

    def test_the_default_kind_is_the_portal_bundle_every_earlier_caller_meant(self, session_factory, project) -> None:
        with session_factory() as session:
            documents = DocumentRepository()
            document = documents.create_document(session, ProjectUid.parse(str(project.project_uid)), "портальный")
            entry, digest = _published(session, role=MANIFEST_ROLE_SOURCE_DOCUMENT)
            uid = documents.publish_version(
                session, document_uid=document, media_type="application/pdf", byte_size=10, sha256=digest, page_count=1,
                source_filename="a.pdf", entries=(entry,))
            assert documents.get_version(session, uid).upload_kind == "portal_bundle"
