"""`CMP-INGEST-01`: declaring a batch -- the limits of ADR-0025 decision 9, refused before any row exists.

Each refusal is read from the tables: **nothing was created** (no batch, no file, no command record). Each limit is tested at
its boundary on the real database; the active-batch limits and the project's stored bytes are the ones only a database
can answer, so they are here and not in the unit suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, UPLOAD_KIND_COMPARISON_PDF, DocumentRepository, ManifestEntry
from auditmanager.ingest.comparison_pdf.public import (
    MAX_BATCH_BYTES,
    MAX_FILES,
    MAX_PROJECT_BYTES,
    ComparisonUploadService,
    DeclaredFileRequest,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ProjectUid, new_ulid
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, derive_blob_id, parse_blob_role
from tests.integration.ingest.comparison_pdf.support import LABEL, create, declare, sha256, table

SHA = "a" * 64


def _declare(service: ComparisonUploadService, project_uid: str, files, *, user: str, key: str = "k1", label: str = LABEL):
    return service.create_upload(project_uid=project_uid, files=files, user_uid=user, actor_label=label, idempotency_key=key)


def _counts(factory: sessionmaker[Session]) -> list[int]:
    with factory() as session:
        return [
            table(session, f"SELECT count(*) FROM {name}")[0][0]
            for name in ("comparison_upload", "comparison_upload_file", "comparison_upload_set", "command_record")
        ]


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


class TestADeclaredBatch:
    def test_it_names_the_batch_the_part_size_and_every_file_declared(self, comparison, project, user) -> None:
        files = {"a.pdf": b"%PDF-1.7 one", "a.pdf ": b"%PDF-1.7 two"}  # two files with the same name hint
        view = create(comparison, str(project.project_uid), files, user=user)
        assert view.state == "uploading" and view.part_size_bytes == 16 * 1024 * 1024
        assert (view.declared_files, view.declared_bytes) == (2, sum(len(d) for d in files.values()))
        assert [(f.state, f.parts_staged, f.set_id) for f in view.files or ()] == [("declared", 0, None)] * 2
        # A name is a hint: two files may share it and each has its own identity.
        assert len({f.file_id for f in view.files or ()}) == 2
        assert view.upload_id.startswith("cbt_") and all(f.file_id.startswith("cuf_") for f in view.files or ())

    def test_nothing_is_stored_and_no_token_exists_yet(self, comparison, project, user, session_factory, bucket_keys) -> None:
        create(comparison, str(project.project_uid), {"a.pdf": b"%PDF-1.7 x"}, user=user)
        with session_factory() as session:
            assert table(session, "SELECT multipart_token, blob_id FROM comparison_upload_file") == [(None, None)]
            assert table(session, "SELECT count(*) FROM comparison_upload_part") == [(0,)]
        assert bucket_keys() == []

    def test_a_repeat_under_the_same_key_answers_the_first_batch(self, comparison, project, user, session_factory) -> None:
        first = create(comparison, str(project.project_uid), {"a.pdf": b"%PDF-1.7 x"}, user=user)
        again = create(comparison, str(project.project_uid), {"a.pdf": b"%PDF-1.7 x"}, user=user)
        assert again.upload_id == first.upload_id and [f.file_id for f in again.files or ()] == [f.file_id for f in first.files or ()]
        assert _counts(session_factory) == [1, 1, 0, 1]

    def test_the_same_key_for_other_files_is_refused_and_creates_nothing(self, comparison, project, user, session_factory) -> None:
        create(comparison, str(project.project_uid), {"a.pdf": b"%PDF-1.7 x"}, user=user)
        refused = _refused(lambda: create(comparison, str(project.project_uid), {"b.pdf": b"%PDF-1.7 y"}, user=user))
        assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert _counts(session_factory) == [1, 1, 0, 1]

    def test_an_unknown_project_is_not_found_and_nothing_is_written(self, comparison, user, session_factory) -> None:
        refused = _refused(lambda: _declare(comparison, f"prj_{new_ulid()}", [declare("a.pdf", b"x")], user=user))
        assert refused.code is ErrorCode.NOT_FOUND and refused.detail_fields == {"aggregate_type": "Project"}
        assert _counts(session_factory) == [0, 0, 0, 0]


class TestDecisionNineBeforeTheFirstPart:
    """A batch over a limit is refused with its registered reason and **nothing is created**."""

    def _one(self, comparison, project, user, session_factory, files):
        refused = _refused(lambda: _declare(comparison, str(project.project_uid), files, user=user))
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert _counts(session_factory) == [0, 0, 0, 0], "a refused declaration left a row behind"
        return refused.detail_fields["field"], refused.detail_fields["constraint"]

    def test_more_than_ten_thousand_files(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest(f"Папка/f{i}.pdf", 1, SHA) for i in range(MAX_FILES + 1)]
        assert self._one(comparison, project, user, session_factory, files) == ("files", "comparison_files_limit")

    def test_ten_thousand_files_are_accepted(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest(f"Папка/f{i}.pdf", 1, SHA) for i in range(MAX_FILES)]
        view = _declare(comparison, str(project.project_uid), files, user=user)
        assert view.declared_files == MAX_FILES and len(view.files or ()) == MAX_FILES

    def test_a_batch_that_groups_into_more_than_a_hundred_sets(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest(f"Раздел {i}/f.pdf", 1, SHA) for i in range(101)]
        assert self._one(comparison, project, user, session_factory, files) == ("files", "comparison_sets_limit")

    def test_declared_bytes_above_eight_gib(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest("Папка/a.pdf", MAX_BATCH_BYTES // 40, SHA) for _ in range(41)]
        assert self._one(comparison, project, user, session_factory, files) == ("files", "comparison_batch_bytes_limit")

    def test_declared_pages_above_ten_thousand(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest(f"Папка/f{i}.pdf", 1, SHA, 500) for i in range(21)]
        assert self._one(comparison, project, user, session_factory, files) == ("files", "comparison_batch_pages_limit")

    def test_a_file_over_the_envelopes_size_is_refused_on_its_content(self, comparison, project, user, session_factory) -> None:
        files = [DeclaredFileRequest("a.pdf", 250 * 1024 * 1024 + 1, SHA)]
        assert self._one(comparison, project, user, session_factory, files) == ("content", f"byte_size <= {250 * 1024 * 1024}")

    def test_a_refusal_never_echoes_the_file_name(self, comparison, project, user) -> None:
        refused = _refused(lambda: _declare(comparison, str(project.project_uid),
                           [DeclaredFileRequest("секретный файл.pdf", 250 * 1024 * 1024 + 1, SHA)], user=user))
        assert "секретный" not in repr(refused.detail_fields) and "секретный" not in str(refused)


def _store_bytes(factory: sessionmaker[Session], project_uid: str, size: int, *, title: str = "уже в проекте") -> None:
    """The project already stores ``size`` bytes: one published comparison version whose blob is that long.

    A blob row is enough for the database (it never reads the object); no object is written."""
    digest = sha256(new_ulid().encode())
    blob_id = derive_blob_id(sha256=digest, size=size)
    with factory() as session:
        repo = BlobMetadataRepository()
        verified = VerifiedBlob(
            blob_id=blob_id, upload_token="mpu-" + "0" * 32, sha256=digest, size=size,
            role=parse_blob_role("comparison_pdf"), media_type="application/pdf",
        )
        repo.record_verified(session, verified)
        repo.mark_available(session, blob_id)
        documents = DocumentRepository()
        document = documents.create_document(session, ProjectUid.parse(project_uid), title)
        documents.publish_version(
            session, document_uid=document, media_type="application/pdf", byte_size=size, sha256=digest, page_count=1,
            source_filename="a.pdf",
            entries=(ManifestEntry(MANIFEST_ROLE_COMPARISON_PDF, blob_id, digest, size, "application/pdf"),),
            upload_kind=UPLOAD_KIND_COMPARISON_PDF,
        )
        session.commit()


class TestTheProjectsStoredBytes:
    def test_stored_plus_declared_over_eight_gib_is_refused_and_exactly_eight_is_accepted(
        self, comparison, project, user, session_factory
    ) -> None:
        _store_bytes(session_factory, str(project.project_uid), MAX_PROJECT_BYTES - 100)
        refused = _refused(lambda: _declare(comparison, str(project.project_uid), [DeclaredFileRequest("a.pdf", 101, SHA)], user=user))
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("files", "comparison_project_bytes_limit")
        view = _declare(comparison, str(project.project_uid), [DeclaredFileRequest("a.pdf", 100, SHA)], user=user, key="k2")
        assert view.declared_bytes == 100

    def test_a_blob_named_by_two_versions_is_stored_once(self, comparison, project, user, session_factory) -> None:
        digest = sha256(b"one blob")
        blob_id = derive_blob_id(sha256=digest, size=1000)
        with session_factory() as session:
            repo = BlobMetadataRepository()
            repo.record_verified(session, VerifiedBlob(blob_id=blob_id, upload_token="mpu-" + "1" * 32, sha256=digest, size=1000,
                                                       role=parse_blob_role("comparison_pdf"), media_type="application/pdf"))
            repo.mark_available(session, blob_id)
            documents = DocumentRepository()
            for title in ("один", "два"):
                document = documents.create_document(session, ProjectUid.parse(str(project.project_uid)), title)
                documents.publish_version(
                    session, document_uid=document, media_type="application/pdf", byte_size=1000, sha256=digest,
                    page_count=1, source_filename="a.pdf",
                    entries=(ManifestEntry(MANIFEST_ROLE_COMPARISON_PDF, blob_id, digest, 1000, "application/pdf"),),
                    upload_kind=UPLOAD_KIND_COMPARISON_PDF,
                )
            session.commit()
        with session_factory() as session:
            assert ComparisonUploadService_repo().project_stored_bytes(session, str(project.project_uid)) == 1000

    def test_another_projects_bytes_are_not_this_projects(self, comparison, project, user, service, session_factory) -> None:
        other = service.create_project("другой проект")
        _store_bytes(session_factory, str(other.project_uid), MAX_PROJECT_BYTES)
        view = _declare(comparison, str(project.project_uid), [DeclaredFileRequest("a.pdf", 1, SHA)], user=user)
        assert view.declared_files == 1

    def test_what_a_batch_in_flight_declared_counts_against_the_project(self, comparison, project, user, session_factory) -> None:
        whole, rest = divmod(MAX_PROJECT_BYTES - 10, 250 * 1024 * 1024)
        big = [DeclaredFileRequest(f"Папка/f{i}.pdf", 250 * 1024 * 1024, SHA) for i in range(whole)]
        _declare(comparison, str(project.project_uid), [*big, DeclaredFileRequest("Папка/rest.pdf", rest, SHA)], user=user)
        refused = _refused(lambda: _declare(
            comparison, str(project.project_uid), [DeclaredFileRequest("b.pdf", 11, SHA)], user=f"usr_{new_ulid()}", key="k2"))
        assert refused.detail_fields["constraint"] == "comparison_project_bytes_limit"


def ComparisonUploadService_repo():  # noqa: N802 - a tiny accessor, named for what it returns
    from auditmanager.ingest.comparison_pdf.public import ComparisonUploadRepository

    return ComparisonUploadRepository()


class TestActiveBatches:
    """One active batch per account and two per installation (one worker slot, ADR-0025 decision 9)."""

    def _conflict(self, call) -> None:
        refused = _refused(call)
        assert refused.code is ErrorCode.CONFLICT and refused.detail_fields["conflict_reason"] == "comparison_upload_active"

    def test_a_second_batch_of_one_account_is_a_conflict(self, comparison, project, user, session_factory) -> None:
        create(comparison, str(project.project_uid), {"a.pdf": b"x"}, user=user)
        self._conflict(lambda: create(comparison, str(project.project_uid), {"b.pdf": b"y"}, user=user, key="k2"))
        assert _counts(session_factory)[:2] == [1, 1]

    def test_a_third_batch_of_the_installation_is_a_conflict_whoever_asks(self, comparison, project, user) -> None:
        other, third = f"usr_{new_ulid()}", f"usr_{new_ulid()}"
        create(comparison, str(project.project_uid), {"a.pdf": b"x"}, user=user)
        create(comparison, str(project.project_uid), {"b.pdf": b"y"}, user=other, key="k2")
        self._conflict(lambda: create(comparison, str(project.project_uid), {"c.pdf": b"z"}, user=third, key="k3"))

    @pytest.mark.parametrize("state", ["completed", "cancelled"])
    def test_a_finished_batch_frees_its_slot(self, comparison, project, user, session_factory, state) -> None:
        from sqlalchemy import text

        first = create(comparison, str(project.project_uid), {"a.pdf": b"x"}, user=user)
        with session_factory() as session:
            # The batch operations of `CMP-INGEST-02` end a batch; here its terminal state is written directly,
            # along the edges the migration declares (a batch is proposed before it is completed).
            for step in (["proposed"] if state == "completed" else []) + [state]:
                session.execute(
                    text("UPDATE comparison_upload SET state = :s, terminal_at = CASE WHEN :s IN ('completed', 'cancelled') "
                         "THEN now() END WHERE comparison_upload_id = :i"),
                    {"s": step, "i": first.upload_id},
                )
            session.commit()
        again = create(comparison, str(project.project_uid), {"b.pdf": b"y"}, user=user, key="k2")
        assert again.upload_id != first.upload_id

    def test_two_requests_at_once_cannot_both_take_the_slot(self, comparison, project, user, session_factory) -> None:
        from concurrent.futures import ThreadPoolExecutor

        def attempt(number: int):
            try:
                return create(comparison, str(project.project_uid), {f"f{number}.pdf": b"x" * (number + 1)}, user=user, key=f"race-{number}")
            except DomainError as refused:
                return refused

        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(attempt, range(4)))
        assert sum(1 for item in outcomes if not isinstance(item, DomainError)) == 1
        assert all(item.detail_fields["conflict_reason"] == "comparison_upload_active" for item in outcomes if isinstance(item, DomainError))
