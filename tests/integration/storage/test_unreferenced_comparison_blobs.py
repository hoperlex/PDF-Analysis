"""The report of published bytes that no table names (`CMP-STORAGE-PARTS-01`, ADR-0025 decision 10).

Against real PostgreSQL at the migration head. A comparison file is verified and published, and the
process dies before ``comparison_upload_file.blob_id`` is written: the Blob row is ``available`` and
nothing references it. ``audit_blob_references`` cannot see that (it starts from the references); the
report does, and each rule is shown failing on a database made to break it:

* a Blob that a source names -- each of the fifteen registered columns in turn -- is never reported;
* a Blob nothing names is reported, attributed to the comparison file whose declared bytes it has, or
  not attributed when no file explains it;
* the report refuses a database whose set of blob-referencing columns is not the closed set (a new
  reference would otherwise make a referenced Blob look orphaned) and one whose head is not pinned;
* it executes only SELECT statements;
* and the whole sequence a comparison upload will run -- declared Blob row, token, parts, completion with the
  ``before_publish`` checkpoint, ``available`` -- on the real MinIO and the real database, with the process
  "killed" before ``blob_id`` is written (the report names the file) and after (the report is empty and the
  reference audit passes).

The database comes from the lane's PostgreSQL (``DATABASE_URL``, read from the process environment or
the repository-root ``.env`` exactly as ``conftest.py`` reads the S3 names). Like the rest of this
directory it fails loudly when the service is absent and never skips.
"""

from __future__ import annotations

import os
import secrets
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import ProjectUid, new_ulid
from auditmanager.storage import ROLE_SOURCE_DOCUMENT, S3BlobStore
from auditmanager.storage.public import (
    BlobMetadataRepository,
    UploadedPart,
    declare_blob,
    derive_blob_id,
    new_multipart_token,
    sha256_of,
)
from scripts.recovery import blob_reference_audit as audit
from scripts.recovery.blob_reference_audit import (
    BlobReferenceAuditRefused,
    audit_blob_references,
    report_unreferenced_comparison_blobs,
)

ROOT = Path(__file__).resolve().parents[3]
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"

#: The registered sources, written out: adding one to the audit must change this list on purpose.
SOURCES = [
    ("analysis_artifact_publication", "blob_id"),
    ("comparison_page_profile", "preview_blob_id"),
    ("comparison_page_profile", "profile_blob_id"),
    ("comparison_page_profile", "thumbnail_blob_id"),
    # `0039_comparison_core` (the mask of a sheet-pair result; the integrator pinned it as 353cfac4) and
    # `0040_comparison_ai_reports` (a stored file of a report): two more Blob references.
    ("comparison_report_artifact", "blob_id"),
    ("comparison_sheet_pair_result", "mask_blob_id"),
    ("comparison_upload_file", "blob_id"),
    ("input_manifest_entry", "blob_id"),
    ("norm_custody_admission", "blob_id"),
    ("norm_custody_binding", "blob_id"),
    ("norm_retrieval_set", "catalogue_blob_id"),
    ("norm_retrieval_set", "set_blob_id"),
    ("price_list_revision", "blob_id"),
    # `0041_comparison_stage_core`: stage source files and validated PDF candidates.
    ("stage_upload_candidate", "pdf_blob_id"),
    ("stage_upload_file", "source_blob_id"),
]


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    dotenv = ROOT / ".env"
    if not url and dotenv.is_file():
        for raw in dotenv.read_text(encoding="utf-8").splitlines():
            name, sep, value = raw.strip().partition("=")
            if sep and name.strip() == "DATABASE_URL":
                url = value.strip().strip("\"'")
    if not url:
        pytest.fail(
            "DATABASE_URL is not set and the repository-root .env does not hold it. "
            "tests/integration/storage/test_unreferenced_comparison_blobs.py runs against a real "
            "PostgreSQL service and never falls back to a stand-in."
        )
    return url


@pytest.fixture(scope="module")
def maintenance() -> Iterator[Engine]:
    settings = DatabaseSettings(url=parse_database_url(_database_url()))
    engine = create_database_engine(
        DatabaseSettings(url=settings.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    try:
        yield engine
    finally:
        engine.dispose()


def _drop(maintenance: Engine, name: str) -> None:
    with maintenance.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                 "WHERE datname = :n AND pid <> pg_backend_pid()"),
            {"n": name},
        )
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


@pytest.fixture(scope="module")
def template(maintenance: Engine) -> Iterator[str]:
    """A database migrated to the head once for the module; each test gets a clone."""
    name = f"cmp_sp_tpl_{secrets.token_hex(6)}"
    with maintenance.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        url = DatabaseSettings(url=parse_database_url(_database_url())).url.set(database=name)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = "src"
        environment["DATABASE_URL"] = url.render_as_string(hide_password=False)
        done = subprocess.run(
            [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini",
             "upgrade", "head"],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=300,
        )
        assert done.returncode == 0, done.stdout + done.stderr
        yield name
    finally:
        _drop(maintenance, name)


@pytest.fixture
def session(maintenance: Engine, template: str) -> Iterator[Session]:
    name = f"cmp_sp_{secrets.token_hex(6)}"
    with maintenance.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
    settings = DatabaseSettings(
        url=DatabaseSettings(url=parse_database_url(_database_url())).url.set(database=name)
    )
    engine = create_database_engine(settings)
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
        _drop(maintenance, name)


def _sha(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode()).hexdigest()


def _blob(db: Session, label: str, *, size: int = 100, state: str = "available") -> str:
    """A Blob row of the given state, through the legal sequence of states."""
    sha = _sha(label)
    blob_id = str(derive_blob_id(sha256=sha, size=size))
    db.execute(
        text("INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
             "VALUES (:b, 'temporary', :s, :n, 'application/pdf')"),
        {"b": blob_id, "s": sha, "n": size},
    )
    for step in ("verifying", "available"):
        db.execute(text("UPDATE blob SET state = :s WHERE blob_id = :b"), {"s": step, "b": blob_id})
        if step == state:
            break
    return blob_id


def _upload(db: Session) -> tuple[str, str]:
    project = str(ProjectUid.new())
    db.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'cmp')"), {"p": project})
    command, upload = f"cmd_{new_ulid()}", f"cbt_{new_ulid()}"
    db.execute(
        text("INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
             "VALUES (:c, 'create_comparison_upload', :k, :f)"),
        {"c": command, "k": secrets.token_hex(8), "f": "a" * 64},
    )
    db.execute(
        text("INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, "
             "declared_bytes, actor_user_uid, actor_label, command_id) "
             "VALUES (:u, :p, 3, 300, :a, 'A', :c)"),
        {"u": upload, "p": project, "a": ACTOR, "c": command},
    )
    return project, upload


def _file(db: Session, upload: str, label: str, *, size: int = 100, blob: str | None = None) -> str:
    """A declared file; ``blob`` makes it verified with that Blob."""
    file = f"cuf_{new_ulid()}"
    db.execute(
        text("INSERT INTO comparison_upload_file (comparison_upload_file_id, comparison_upload_id, "
             "display_name, declared_size_bytes, declared_sha256, multipart_token) "
             "VALUES (:f, :u, 'a.pdf', :n, :s, :t)"),
        {"f": file, "u": upload, "n": size, "s": _sha(label), "t": "mpu-" + secrets.token_hex(16)},
    )
    if blob is not None:
        db.execute(
            text("UPDATE comparison_upload_file SET state = 'uploading' "
                 "WHERE comparison_upload_file_id = :f"),
            {"f": file},
        )
        db.execute(
            text("UPDATE comparison_upload_file SET state = 'verified', blob_id = :b "
                 "WHERE comparison_upload_file_id = :f"),
            {"b": blob, "f": file},
        )
    return file


def test_the_registered_sources_are_the_fifteen_the_report_checks() -> None:
    assert sorted((table, column) for _, table, column in audit._SOURCES) == SOURCES
    statement = str(audit._unreferenced_statement())
    for table, column in SOURCES:
        assert f"NOT EXISTS (SELECT 1 FROM public.{table} r WHERE r.{column} = b.blob_id)" in statement


class TestWhatIsReported:
    def test_an_empty_database_reports_nothing(self, session: Session) -> None:
        report = report_unreferenced_comparison_blobs(session)
        assert (report.attributed, report.unattributed, report.total_bytes) == ((), (), 0)

    def test_a_published_blob_that_an_open_file_declared_is_attributed_to_it(
        self, session: Session
    ) -> None:
        """The crash this report exists for: published, then killed before ``blob_id`` was written."""
        _, upload = _upload(session)
        file = _file(session, upload, "the-file", size=4321)
        orphan = _blob(session, "the-file", size=4321)

        report = report_unreferenced_comparison_blobs(session)

        assert report.unattributed == ()
        assert [(b.blob_id, b.size_bytes, b.comparison_upload_file_ids) for b in report.attributed] == [
            (orphan, 4321, (file,))
        ]
        assert report.attributed[0].sha256 == _sha("the-file")
        assert report.attributed[0].media_type == "application/pdf"
        assert report.total_bytes == 4321

    def test_two_open_files_of_identical_bytes_are_both_named(self, session: Session) -> None:
        _, upload = _upload(session)
        first = _file(session, upload, "twin")
        second = _file(session, upload, "twin")
        _blob(session, "twin")

        (found,) = report_unreferenced_comparison_blobs(session).attributed

        assert found.comparison_upload_file_ids == tuple(sorted((first, second)))

    def test_a_blob_no_file_declared_is_listed_unattributed(self, session: Session) -> None:
        stray = _blob(session, "nobody-declared-this", size=7)

        report = report_unreferenced_comparison_blobs(session)

        assert report.attributed == ()
        assert [(b.blob_id, b.comparison_upload_file_ids) for b in report.unattributed] == [(stray, ())]

    def test_a_blob_that_is_not_available_is_not_reported(self, session: Session) -> None:
        _blob(session, "half-published", state="verifying")
        assert report_unreferenced_comparison_blobs(session).unattributed == ()

    def test_a_file_that_already_holds_its_blob_does_not_explain_a_second_blob(
        self, session: Session
    ) -> None:
        """Only a file with no ``blob_id`` is open; a verified one has its Blob and it is referenced."""
        _, upload = _upload(session)
        held = _blob(session, "verified-file")
        _file(session, upload, "verified-file", blob=held)

        report = report_unreferenced_comparison_blobs(session)
        assert (report.attributed, report.unattributed) == ((), ())

    def test_a_blob_a_verified_comparison_file_names_is_not_reported(self, session: Session) -> None:
        """Mutation proof: the ``comparison_upload_file`` clause removed from the statement."""
        _, upload = _upload(session)
        held = _blob(session, "named-by-a-file")
        _file(session, upload, "named-by-a-file", blob=held)

        report = report_unreferenced_comparison_blobs(session)

        assert (report.attributed, report.unattributed) == ((), ())

    def test_stage_source_and_pdf_candidate_blobs_are_not_reported_as_orphans(
        self, session: Session,
    ) -> None:
        source = _blob(session, "stage-source")
        candidate_blob = _blob(session, "stage-candidate")
        project = str(ProjectUid.new())
        command, upload, file_id, candidate = (
            f"{prefix}_{new_ulid()}" for prefix in ("cmd", "stu", "suf", "suc")
        )
        session.execute(text(
            "INSERT INTO project (project_uid, name) VALUES (:p, 'stage')"), {"p": project})
        session.execute(text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, "
            "payload_fingerprint) VALUES (:c, 'create_stage_upload', :k, :sha)"),
            {"c": command, "k": secrets.token_hex(8), "sha": "a" * 64})
        session.execute(text(
            "INSERT INTO stage_upload (stage_upload_id, project_uid, declared_files, "
            "declared_bytes, actor_user_uid, command_id, state) "
            "VALUES (:u, :p, 1, 100, :a, :c, 'completed')"),
            {"u": upload, "p": project, "a": ACTOR, "c": command})
        session.execute(text(
            "INSERT INTO stage_upload_file (stage_upload_file_id, stage_upload_id, media_kind, "
            "display_name, declared_size_bytes, declared_sha256, source_blob_id, state) "
            "VALUES (:f, :u, 'zip', 'bundle.zip', 100, :sha, :b, 'ready')"),
            {"f": file_id, "u": upload, "sha": _sha("stage-source"), "b": source})
        session.execute(text(
            "INSERT INTO stage_upload_candidate (stage_upload_candidate_id, stage_upload_file_id, "
            "member_number, display_name, pdf_blob_id) "
            "VALUES (:candidate, :f, 1, 'sheet.pdf', :b)"),
            {"candidate": candidate, "f": file_id, "b": candidate_blob})

        report = report_unreferenced_comparison_blobs(session)
        assert (report.attributed, report.unattributed) == ((), ())
        counts = dict(audit_blob_references(session).source_counts)
        assert counts["stage_upload_file"] == counts["stage_upload_candidate"] == 1

    def test_a_blob_a_manifest_entry_names_is_not_reported(self, session: Session) -> None:
        """Content-addressed: the same bytes uploaded as a portal bundle are referenced, not orphaned."""
        from auditmanager.shared.identity import DocumentUid, VersionUid

        project, document, version = str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
        blob = _blob(session, "portal-bytes")
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'p')"), {"p": project})
        session.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'D')"),
            {"d": document, "p": project},
        )
        session.execute(
            text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                 "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 100, :s, 1)"),
            {"v": version, "d": document, "s": _sha("portal-bytes")},
        )
        session.execute(
            text("INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, "
                 "media_type) VALUES (:v, 'source.document', :b, :s, 100, 'application/pdf')"),
            {"v": version, "b": blob, "s": _sha("portal-bytes")},
        )

        report = report_unreferenced_comparison_blobs(session)

        assert (report.attributed, report.unattributed) == ((), ())

    def test_the_listing_is_ordered_by_blob_id_in_each_part(self, session: Session) -> None:
        ids = [_blob(session, f"stray-{n}", size=n + 1) for n in range(5)]
        listed = [b.blob_id for b in report_unreferenced_comparison_blobs(session).unattributed]
        assert listed == sorted(ids)


class TestWhatIsRefused:
    def test_a_database_with_another_head_is_refused(self, session: Session) -> None:
        session.execute(text("UPDATE alembic_version SET version_num = '0037_analysis_presets'"))
        with pytest.raises(BlobReferenceAuditRefused, match="migration head differs"):
            report_unreferenced_comparison_blobs(session)

    def test_a_new_column_that_references_a_blob_is_refused(self, session: Session) -> None:
        """Mutation proof: the catalog check removed (the new reference would be invisible)."""
        session.execute(text("ALTER TABLE project ADD COLUMN stray_blob_id text REFERENCES blob (blob_id)"))
        with pytest.raises(BlobReferenceAuditRefused, match="Blob reference catalog differs"):
            report_unreferenced_comparison_blobs(session)

    def test_a_blob_row_whose_identity_disagrees_with_its_content_is_refused(
        self, session: Session
    ) -> None:
        wrong = "blob_" + "0" * 26
        session.execute(
            text("INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
                 "VALUES (:b, 'temporary', :s, 9, 'application/pdf')"),
            {"b": wrong, "s": _sha("x")},
        )
        for step in ("verifying", "available"):
            session.execute(text("UPDATE blob SET state = :s WHERE blob_id = :b"), {"s": step, "b": wrong})
        with pytest.raises(BlobReferenceAuditRefused, match="disagrees with content identity"):
            report_unreferenced_comparison_blobs(session)


class TestItOnlyReads:
    def test_every_statement_it_sends_is_a_select(self, session: Session) -> None:
        _, upload = _upload(session)
        _file(session, upload, "f")
        _blob(session, "f")
        sent: list[str] = []
        original = session.execute

        def recording(statement: Any, *args: Any, **kwargs: Any) -> Any:
            sent.append(str(statement).strip())
            return original(statement, *args, **kwargs)

        session.execute = recording  # type: ignore[method-assign]
        try:
            report_unreferenced_comparison_blobs(session)
        finally:
            session.execute = original  # type: ignore[method-assign]

        assert len(sent) == 4  # the head, the catalog, the open files, the unreferenced Blobs
        assert all(statement.upper().startswith("SELECT") for statement in sent)

    def test_the_database_is_unchanged_after_a_report(self, session: Session) -> None:
        _blob(session, "left-alone")
        before = session.execute(text("SELECT count(*), max(updated_at) FROM blob")).one()
        report_unreferenced_comparison_blobs(session)
        assert session.execute(text("SELECT count(*), max(updated_at) FROM blob")).one() == before


class TestTheSequenceAComparisonUploadWillRun:
    """The storage lane's whole contract with ``CMP-INGEST-01``, on real services."""

    MIB = 1024 * 1024
    FIRST = b"1" * (5 * MIB)
    LAST = b"%%EOF-tail\n" * 100
    WHOLE = FIRST + LAST

    def _sequence(self, store: S3BlobStore, session: Session, blobs: list) -> dict[str, Any]:
        repo = BlobMetadataRepository()
        sha, size = sha256_of(self.WHOLE), len(self.WHOLE)
        declared = declare_blob(
            sha256=sha, size=size, role=ROLE_SOURCE_DOCUMENT, media_type="application/pdf"
        )
        # 1. The first part: the declared Blob row and the token are committed before any byte moves.
        repo.record_declared(session, declared)
        _, upload = _upload(session)
        token = new_multipart_token()
        file = f"cuf_{new_ulid()}"
        session.execute(
            text("INSERT INTO comparison_upload_file (comparison_upload_file_id, comparison_upload_id, "
                 "display_name, declared_size_bytes, declared_sha256, multipart_token) "
                 "VALUES (:f, :u, 'a.pdf', :n, :s, :t)"),
            {"f": file, "u": upload, "n": size, "s": sha, "t": token},
        )
        session.execute(
            text("UPDATE comparison_upload_file SET state = 'uploading' "
                 "WHERE comparison_upload_file_id = :f"), {"f": file},
        )
        session.commit()
        # 2. The parts: a row before the bytes, the receipt recorded after.
        store.begin_multipart(token)
        receipts: list[UploadedPart] = []
        for number, body in enumerate((self.FIRST, self.LAST), start=1):
            session.execute(
                text("INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number) "
                     "VALUES (:f, :n)"), {"f": file, "n": number},
            )
            receipt = store.upload_part(token, number, body)
            session.execute(
                text("UPDATE comparison_upload_part SET state = 'staged', size_bytes = :z, "
                     "sha256 = :h, etag = :e WHERE comparison_upload_file_id = :f AND part_number = :n"),
                {"z": receipt.size_bytes, "h": receipt.sha256, "e": receipt.etag, "f": file, "n": number},
            )
            receipts.append(receipt)
        session.commit()
        # 3. The completion, with the checkpoint the durable store has: `verifying` before publication.
        published = store.complete_multipart(
            token, receipts,
            declared_sha256=sha, declared_size=size, role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
            before_publish=lambda verified: (repo.record_verified(session, verified), session.commit()),
        )
        blobs.append(published.blob_id)
        repo.mark_available(session, published.blob_id)
        session.commit()
        return {"file": file, "published": published, "token": token}

    def test_a_kill_before_blob_id_is_written_is_visible_and_the_end_state_audits_clean(
        self, store: S3BlobStore, session: Session, blobs: list
    ) -> None:
        done = self._sequence(store, session, blobs)
        file, published = done["file"], done["published"]
        assert published.blob_id == derive_blob_id(sha256=sha256_of(self.WHOLE), size=len(self.WHOLE))

        # The process died here: the object is canonical and `available`, `blob_id` is still NULL.
        report = report_unreferenced_comparison_blobs(session)
        assert [(b.blob_id, b.comparison_upload_file_ids) for b in report.attributed] == [
            (published.blob_id, (file,))
        ]
        assert report.unattributed == ()

        # The completion finishes: the file is verified with its Blob and the parts are completed.
        session.execute(
            text("UPDATE comparison_upload_file SET state = 'verified', blob_id = :b "
                 "WHERE comparison_upload_file_id = :f"), {"b": published.blob_id, "f": file},
        )
        session.execute(
            text("UPDATE comparison_upload_part SET state = 'completed' "
                 "WHERE comparison_upload_file_id = :f"), {"f": file},
        )
        session.commit()

        after = report_unreferenced_comparison_blobs(session)
        assert (after.attributed, after.unattributed) == ((), ())
        counts = dict(audit_blob_references(session).source_counts)
        assert counts["comparison_upload_file"] == 1

    def test_the_retry_after_the_kill_publishes_nothing_twice(
        self, store: S3BlobStore, session: Session, blobs: list, bucket_keys: Any
    ) -> None:
        """Completing a file whose bytes are already published reuses the Blob (idempotent by content)."""
        first = self._sequence(store, session, blobs)
        token = new_multipart_token()
        store.begin_multipart(token)
        receipts = [
            store.upload_part(token, 1, self.FIRST),
            store.upload_part(token, 2, self.LAST),
        ]
        again = store.complete_multipart(
            token, receipts,
            declared_sha256=sha256_of(self.WHOLE), declared_size=len(self.WHOLE),
            role=ROLE_SOURCE_DOCUMENT, media_type="application/pdf",
        )
        assert again.blob_id == first["published"].blob_id
        assert [k for k in bucket_keys() if k.startswith("temporary/")] == []
