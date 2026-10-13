"""A portal bundle becomes one immutable version with every stored member, or nothing at all.

`W55B-INGEST-01` (plan sections B3.2 database, B3.4). Real PostgreSQL and real MinIO, as the
rest of this directory; every "what is in the bucket" and "what is in the table" assertion is
made with a plain boto3 client and raw SQL, never through the code under test.

What is asserted, and the failure each assertion exists to catch:

* the manifest lists **one entry per stored member** -- ``source.document``,
  ``source.structured_companion``, ``source.markdown`` and, when the bundle has one,
  ``source.stamp_audit`` -- and each entry's object is the member's own bytes;
* the version's own ``byte_size``, ``sha256`` and ``media_type`` stay **the PDF member's**;
* the three counts are stored together (a version published before the last step of the lane,
  as a bare PDF, carries all three NULL; the columns stay nullable for it);
* ``_results.html`` is **hashed and not stored**: no object, no blob row, no manifest entry;
* the **command fingerprint covers every member's digest, the HTML's included**, and nothing
  about how the archive was packed;
* **no version ever exists with a partial member set**: a failure staging, verifying,
  recording, publishing or committing leaves no version row and no manifest row, every staged
  temporary is removed, and what was published before the failure is the unattributed blobs
  ``Reconciler.report`` names;
* a **refused bundle leaves nothing** -- no object, no row, no command record.
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy import text

from auditmanager.documents import (
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STAMP_AUDIT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
)
from auditmanager.ingest import IngestService, Reconciler
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import StorageUnavailableError, derive_blob_id
from portal_bundle import archive_negatives as an  # tools/fixtures, on the path via conftest
from portal_bundle import positives, zipwrite
from portal_bundle.bundle import make_files, pack
from tests.integration.ingest.bundle_support import bundle_around, committed

TITLE = "Complete portal bundle"
UPLOAD_NAME = "ar_baseline.zip"

#: The four stored members of ``ar_baseline.zip``, by manifest role, and their archive names.
STORED = {
    MANIFEST_ROLE_SOURCE_DOCUMENT: "ar_baseline.pdf",
    MANIFEST_ROLE_STRUCTURED_COMPANION: "ar_baseline_blocks.json",
    MANIFEST_ROLE_MARKDOWN: "ar_baseline_results.md",
    MANIFEST_ROLE_STAMP_AUDIT: "ar_baseline_stamp_audit.json",
}


def upload(service, project, data, key, label="bundle", **overrides):
    arguments = {
        "project_uid": project.project_uid,
        "content": io.BytesIO(data),
        "source_filename": UPLOAD_NAME,
        "display_title": TITLE,
        "idempotency_key": key(label),
    }
    arguments.update(overrides)
    return service.upload_bundle(**arguments)


def zip_members(data: bytes) -> dict[str, bytes]:
    import zipfile

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def table_counts(engine) -> dict[str, int]:
    tables = ("project", "document", "document_version", "input_manifest_entry", "blob",
              "command_record")
    with engine.connect() as connection:
        return {
            table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
            for table in tables
        }


def canonical_keys(keys: list[str]) -> list[str]:
    return [k for k in keys if "tmp" not in k and "temporary" not in k]


# ---------------------------------------------------------------------------------------
# The accepted bundle
# ---------------------------------------------------------------------------------------


def test_a_complete_bundle_publishes_one_version_with_one_manifest_entry_per_stored_member(
    service, project, key, engine, store
) -> None:
    data = committed("ar_baseline.zip")
    members = zip_members(data)
    outcome = upload(service, project, data, key)
    version = outcome.version

    assert outcome.replayed is False
    assert sorted(e.role for e in version.manifest) == sorted(STORED), (
        "the manifest does not list exactly the four stored members"
    )
    for entry in version.manifest:
        wanted = members[STORED[entry.role]]
        assert entry.size_bytes == len(wanted), entry.role
        assert store.read(entry.blob_id) == wanted, f"{entry.role} is not the member's bytes"
        assert entry.blob_id == derive_blob_id(
            sha256=entry.sha256, size=entry.size_bytes
        )
    media = {e.role: e.media_type for e in version.manifest}
    assert media == {
        MANIFEST_ROLE_SOURCE_DOCUMENT: "application/pdf",
        MANIFEST_ROLE_STRUCTURED_COMPANION: "application/json",
        MANIFEST_ROLE_MARKDOWN: "text/markdown",
        MANIFEST_ROLE_STAMP_AUDIT: "application/json",
    }
    assert table_counts(engine)["input_manifest_entry"] == 4
    assert table_counts(engine)["blob"] == 4
    with engine.connect() as connection:
        states = {r[0] for r in connection.execute(text("SELECT state FROM blob"))}
    assert states == {"available"}


def test_the_versions_own_facts_stay_the_pdf_members(service, project, key, engine) -> None:
    data = committed("ar_baseline.zip")
    pdf = zip_members(data)["ar_baseline.pdf"]
    version = upload(service, project, data, key).version
    import hashlib

    assert version.sha256 == hashlib.sha256(pdf).hexdigest()
    assert version.byte_size == len(pdf)
    assert version.media_type == "application/pdf"
    assert version.page_count == 8
    assert version.source.sha256 == version.sha256


def test_the_display_name_is_the_pdf_members_and_the_title_defaults_to_it(
    service, project, key, engine
) -> None:
    data = positives.name_encoding("cp866")
    outcome = upload(service, project, data, key, display_title=None)
    with engine.connect() as connection:
        stored_name, title = connection.execute(
            text(
                "SELECT v.source_filename, d.display_title FROM document_version v "
                "JOIN document d USING (document_uid)"
            )
        ).one()
    assert stored_name == "Проект_АР.pdf"
    assert title == "Проект_АР.pdf", "a missing title is the PDF member's display name"
    assert outcome.version.display_title == "Проект_АР.pdf"


def test_a_member_name_with_a_directory_part_or_control_characters_is_a_plain_display_name(
    service, project, key, engine
) -> None:
    items = an.members(stem="dir/ba\x01d")
    data = zipwrite.build_zip(items)
    upload(service, project, data, key, display_title=None)
    with engine.connect() as connection:
        name = connection.execute(text("SELECT source_filename FROM document_version")).scalar_one()
    assert name == "ba_d.pdf"


def test_the_three_counts_are_stored_together_and_exposed_on_the_version_record(
    service, project, key, engine
) -> None:
    version = upload(service, project, committed("image_only_with_block.zip"), key).version
    assert version.text_character_count == 0
    assert version.textless_pages == (1, 2)
    assert version.recognised_character_count > 0
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT text_character_count, textless_pages, recognised_character_count "
                 "FROM document_version")
        ).one()
    assert (row[0], list(row[1]), row[2]) == (0, [1, 2], version.recognised_character_count)
    # ... and the same through every read path of the repository.
    assert service.get_version(version.version_uid).textless_pages == (1, 2)
    assert service.list_documents(project.project_uid)[0].textless_pages == (1, 2)
    document_uid = service.list_documents(project.project_uid)[0].document_uid
    assert service.list_versions(document_uid)[0].recognised_character_count == (
        version.recognised_character_count
    )


def test_a_version_without_text_layer_trouble_stores_an_empty_list_not_null(
    service, project, key, engine
) -> None:
    version = upload(service, project, committed("ar_baseline.zip"), key).version
    assert version.textless_pages == ()
    assert version.text_character_count > 0 and version.recognised_character_count == 0
    with engine.connect() as connection:
        value = connection.execute(text("SELECT textless_pages FROM document_version")).scalar_one()
    assert value == [], "an empty list must be stored as an empty list"


def test_a_bare_pdf_is_refused_with_portal_bundle_required_through_the_adapter(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    """The last step of the lane: the single-PDF entry is gone, and a bare PDF -- the very
    document that used to publish a version with no counts -- is refused where it used to be
    routed, with the registered constraint, its field and the Russian sentence on how to
    obtain the bundle. Nothing is stored, no row is written and no command is recorded."""
    from auditmanager.bootstrap.adapters import DocumentAdapter

    before_keys, before_counts = set(bucket_keys()), table_counts(engine)
    with pytest.raises(DomainError) as raised:
        DocumentAdapter(service).upload_document(
            project_uid=str(project.project_uid), content=io.BytesIO(baseline_pdf),
            source_filename="a.pdf", display_title="Bare", idempotency_key=str(key("bare")),
        )
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(raised.value.detail_fields) == {
        "field": "file", "constraint": "portal_bundle_required",
    }
    assert "комплект портала распознавания" in str(raised.value)
    assert set(bucket_keys()) == before_keys and table_counts(engine) == before_counts


def test_a_partial_set_of_counts_is_refused_before_a_statement_is_issued(
    service, project, session_factory
) -> None:
    from auditmanager.documents import DocumentRepository
    from auditmanager.shared.db import session_scope

    repository = DocumentRepository()
    with session_scope(session_factory) as session:
        document = repository.create_document(session, project.project_uid, "Partial")
        for bad in (
            {"text_character_count": 5},
            {"textless_pages": ()},
            {"recognised_character_count": 1, "text_character_count": 1},
        ):
            with pytest.raises(DomainError) as raised:
                repository.publish_version(
                    session, document_uid=document, media_type="application/pdf", byte_size=1,
                    sha256="0" * 64, page_count=1, source_filename="x.pdf", entries=(), **bad,
                )
            # `entries=()` would be refused too, but the counts are judged first.
            assert dict(raised.value.detail_fields)["field"] == "text_character_count"


def test_a_non_zip_is_refused_with_the_bundle_sentence_and_publishes_nothing(
    service, project, baseline_pdf, key, engine, bucket_keys
) -> None:
    before_keys, before_counts = set(bucket_keys()), table_counts(engine)
    for payload in (baseline_pdf, b"", b"plain text"):
        with pytest.raises(DomainError) as raised:
            upload(service, project, payload, key)
        assert raised.value.code is ErrorCode.VALIDATION_FAILED
        assert dict(raised.value.detail_fields) == {
            "field": "file", "constraint": "portal_bundle_required",
        }
        assert "ZIP" in str(raised.value)
    assert set(bucket_keys()) == before_keys and table_counts(engine) == before_counts


# ---------------------------------------------------------------------------------------
# The HTML rendering is a digest and nothing else
# ---------------------------------------------------------------------------------------


def test_the_html_is_hashed_and_never_stored(service, project, key, engine, bucket_keys, raw_s3,
                                               s3_settings) -> None:
    import hashlib

    data = committed("ar_baseline.zip")
    html = zip_members(data)["ar_baseline_results.html"]
    upload(service, project, data, key)

    # No manifest entry, no blob row, and no object anywhere holds the HTML.
    with engine.connect() as connection:
        digests = {r[0] for r in connection.execute(text("SELECT sha256 FROM blob"))}
        roles = {r[0] for r in connection.execute(text("SELECT role FROM input_manifest_entry"))}
    assert hashlib.sha256(html).hexdigest() not in digests
    assert not any("html" in role for role in roles)
    for object_key in bucket_keys():
        body = raw_s3.get_object(Bucket=s3_settings.bucket, Key=object_key)["Body"].read()
        assert body != html, f"{object_key} holds the HTML rendering"
        assert b"<!DOCTYPE html>" not in body or object_key.endswith("results.md"), object_key
    assert len(bucket_keys()) == 4, "exactly the four stored members are in the bucket"


# ---------------------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------------------


def _with_member_replaced(data: bytes, suffix: bytes, transform) -> bytes:
    """The same bundle with one member's bytes changed (the archive is rebuilt)."""
    import zipfile

    items = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            payload = archive.read(info)
            if info.filename.encode().endswith(suffix):
                payload = transform(payload)
            items.append(zipwrite.Member(info.filename.encode(), payload, method=8,
                                         flags=zipwrite.FLAG_UTF8))
    return zipwrite.build_zip(items)


def test_the_same_bundle_again_is_a_replay_and_creates_nothing(
    service, project, key, engine
) -> None:
    data = committed("ar_baseline.zip")
    idempotency = key("replay")
    first = upload(service, project, data, key, idempotency_key=idempotency)
    before = table_counts(engine)
    second = upload(service, project, data, key, idempotency_key=idempotency)
    assert (first.replayed, second.replayed) == (False, True)
    assert second.version.version_uid == first.version.version_uid
    assert table_counts(engine) == before


def test_the_same_members_packed_differently_are_the_same_upload(
    service, project, key
) -> None:
    """Compression, member order and the name encoding are not part of the payload."""
    idempotency = key("repacked")
    files = make_files(an.base_files().pdf, an.STEM, html=True, stamp_audit=True)
    first = zipwrite.build_zip(pack(files))
    second = zipwrite.build_zip(pack(files, stored=True)[::-1])
    assert first != second
    one = upload(service, project, first, key, idempotency_key=idempotency)
    two = upload(service, project, second, key, idempotency_key=idempotency)
    assert two.replayed is True and two.version.version_uid == one.version.version_uid


@pytest.mark.parametrize(
    ("what", "change"),
    [
        ("the HTML rendering", lambda d: _with_member_replaced(d, b"_results.html", lambda b: b + b"<!-- x -->")),
        ("the stamp audit", lambda d: _with_member_replaced(d, b"_stamp_audit.json", lambda b: b" " + b)),
        ("the block list", lambda d: _with_member_replaced(d, b"_blocks.json", lambda b: b + b"\n")),
        ("the markdown", lambda d: _with_member_replaced(d, b"_results.md", lambda b: b + b"\n")),
    ],
)
def test_a_bundle_that_differs_in_any_one_member_under_the_same_key_is_a_conflict(
    service, project, key, engine, what, change
) -> None:
    """The HTML is not stored and is in the fingerprint all the same: a client that reuses a
    key after changing it learns so, instead of being handed the first upload back."""
    data = committed("ar_baseline.zip")
    idempotency = key("conflict")
    upload(service, project, data, key, idempotency_key=idempotency)
    before = table_counts(engine)
    with pytest.raises(DomainError) as raised:
        upload(service, project, change(data), key, idempotency_key=idempotency)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE, what
    assert table_counts(engine) == before


def test_a_bundle_without_the_optional_members_is_not_the_one_with_them(
    service, project, key
) -> None:
    idempotency = key("optional")
    upload(service, project, committed("ar_baseline.zip"), key, idempotency_key=idempotency)
    with pytest.raises(DomainError) as raised:
        upload(service, project, committed("ar_baseline_minimal.zip"), key,
               idempotency_key=idempotency)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_different_upload_name_or_project_under_the_same_key_is_a_conflict(
    service, project, key
) -> None:
    idempotency = key("name")
    data = committed("ar_baseline_minimal.zip")
    upload(service, project, data, key, idempotency_key=idempotency)
    with pytest.raises(DomainError) as raised:
        upload(service, project, data, key, idempotency_key=idempotency, source_filename="other.zip")
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_refused_bare_pdf_does_not_burn_the_key_a_bundle_then_uses(
    service, project, baseline_pdf, key, engine
) -> None:
    """A bare PDF sent through the adapter used to publish under a key and make a bundle under
    the same key a conflict. Now the refusal records no command, so the key is still free: the
    bundle that follows under it publishes, and a replay of it is the same version."""
    from auditmanager.bootstrap.adapters import DocumentAdapter

    idempotency = key("mixed")
    with pytest.raises(DomainError) as raised:
        DocumentAdapter(service).upload_document(
            project_uid=str(project.project_uid), content=io.BytesIO(baseline_pdf),
            source_filename="a.pdf", display_title="Bare", idempotency_key=str(idempotency),
        )
    assert dict(raised.value.detail_fields)["constraint"] == "portal_bundle_required"
    assert table_counts(engine)["command_record"] == 0

    first = upload(service, project, committed("ar_baseline.zip"), key, idempotency_key=idempotency)
    again = upload(service, project, committed("ar_baseline.zip"), key, idempotency_key=idempotency)
    assert not first.replayed and again.replayed
    assert again.version.version_uid == first.version.version_uid


def test_a_member_that_is_identical_to_another_shares_its_blob_and_both_roles_are_listed(
    service, project, key, engine
) -> None:
    """A stamp audit whose bytes equal the block list's: one object, two manifest entries."""
    files = make_files(an.base_files().pdf, an.STEM)
    items = pack(files)
    items.append(zipwrite.Member(f"{an.STEM}_stamp_audit.json".encode(), items[1].payload, method=8))
    outcome = upload(service, project, zipwrite.build_zip(items), key)
    by_role = {e.role: e for e in outcome.version.manifest}
    assert by_role[MANIFEST_ROLE_STAMP_AUDIT].blob_id == by_role[MANIFEST_ROLE_STRUCTURED_COMPANION].blob_id
    assert table_counts(engine)["input_manifest_entry"] == 4
    assert table_counts(engine)["blob"] == 3


# ---------------------------------------------------------------------------------------
# A refused bundle leaves nothing
# ---------------------------------------------------------------------------------------

REFUSED = {
    "an archive rule": lambda: an.symlink(),
    "a size rule": lambda: an.entry_count(9),
    "the PDF member": lambda: committed("encrypted.zip"),
    "the page rule": lambda: committed("image_only.zip"),
    "the block list": lambda: an.blocks_json_invalid("bad_block_id"),
    "the markdown": lambda: an.markdown_missing_a_header(),
    "the stamp audit": lambda: an.stamp_audit_not_json(),
    "not a PDF at all": lambda: bundle_around(b"this is not a pdf"),
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_refused_bundle_leaves_no_object_no_row_and_no_command_record(
    service, project, key, engine, bucket_keys, name, tmp_path, monkeypatch
) -> None:
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before_keys, before_counts = set(bucket_keys()), table_counts(engine)
    with pytest.raises(DomainError) as raised:
        upload(service, project, REFUSED[name](), key)
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert set(bucket_keys()) == before_keys, "a refused bundle reached the store"
    assert table_counts(engine) == before_counts, "a refused bundle wrote a row"
    assert list(tmp_path.iterdir()) == [], "a refused bundle left temporary files"


def test_an_accepted_bundle_leaves_no_temporary_files_either(
    service, project, key, tmp_path, monkeypatch
) -> None:
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    upload(service, project, committed("ar_baseline.zip"), key)
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------------------
# No version with a partial member set
# ---------------------------------------------------------------------------------------


class FailingAt:
    """A store that really does everything, except fail the n-th call of one operation."""

    def __init__(self, inner, operation: str, nth: int, error=StorageUnavailableError) -> None:
        self._inner, self.operation, self.nth, self.error = inner, operation, nth, error
        self.calls: dict[str, int] = {}

    def __getattr__(self, name):
        attribute = getattr(self._inner, name)
        if name != self.operation:
            return attribute

        def counted(*args, **kwargs):
            self.calls[name] = self.calls.get(name, 0) + 1
            if self.calls[name] == self.nth:
                raise self.error()
            return attribute(*args, **kwargs)

        return counted


@pytest.mark.parametrize("operation", ["stage_temporary", "verify_temporary"])
@pytest.mark.parametrize("nth", [1, 2, 4])
def test_a_failure_while_staging_or_verifying_leaves_no_version_no_row_and_no_residue(
    store, session_factory, project, key, engine, bucket_keys, operation, nth
) -> None:
    flaky = FailingAt(store, operation, nth)
    service = IngestService(flaky, session_factory=session_factory)
    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        upload(service, project, committed("ar_baseline.zip"), key)
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    counts = table_counts(engine)
    assert counts["document_version"] == 0 and counts["input_manifest_entry"] == 0
    assert counts["document"] == 0
    assert counts["blob"] == 0, "no breadcrumb is written before every member is verified"
    assert set(bucket_keys()) == before, (
        f"staged temporaries survived a failure of {operation} #{nth}: "
        f"{sorted(set(bucket_keys()) - before)}"
    )
    with engine.connect() as connection:
        state, code = connection.execute(text("SELECT state, error_code FROM command_record")).one()
    assert (state, code) == ("failed", "dependency_unavailable")


@pytest.mark.parametrize("nth", [1, 2, 3, 4])
def test_a_failure_while_publishing_leaves_no_version_and_the_reconciler_names_the_blobs(
    store, session_factory, project, key, engine, bucket_keys, nth
) -> None:
    """Members 1..nth-1 are canonical objects with a ``verifying`` row; nothing binds them.
    The report lists exactly the four blobs, those that exist and those that do not, as
    unattributed -- adoptable by a retry, never mistaken for a version's."""
    flaky = FailingAt(store, "publish", nth)
    service = IngestService(flaky, session_factory=session_factory)
    reconciler = Reconciler(store, session_factory=session_factory)
    with pytest.raises(DomainError):
        upload(service, project, committed("ar_baseline.zip"), key)

    counts = table_counts(engine)
    assert counts["document_version"] == 0 and counts["input_manifest_entry"] == 0
    assert counts["document"] == 0
    assert counts["blob"] == 4
    report = reconciler.report()
    assert report.missing_objects == ()
    assert len(report.unattributed_blobs) == 4
    present = [item for item in report.unattributed_blobs if item.object_present]
    assert len(present) == nth - 1, "exactly the members published before the failure exist"
    assert {item.recorded_state for item in report.unattributed_blobs} == {"verifying"}
    # No temporary object survives: what is in the bucket is canonical only.
    assert len(bucket_keys()) == nth - 1


def test_a_failure_in_the_last_transaction_leaves_published_blobs_and_no_version(
    store, session_factory, project, key, engine, bucket_keys, monkeypatch
) -> None:
    from auditmanager.documents import DocumentRepository

    def refuse(self, session, **kwargs):
        raise DomainError(ErrorCode.INTERNAL_ERROR)

    monkeypatch.setattr(DocumentRepository, "publish_version", refuse)
    service = IngestService(store, session_factory=session_factory)
    with pytest.raises(DomainError):
        upload(service, project, committed("ar_baseline.zip"), key)

    counts = table_counts(engine)
    assert counts["document_version"] == 0 and counts["input_manifest_entry"] == 0
    assert counts["document"] == 0, "the document row of a failed publication must roll back"
    with engine.connect() as connection:
        states = {r[0] for r in connection.execute(text("SELECT state FROM blob"))}
    assert states == {"verifying"}, "no blob became available without its version"
    assert len(Reconciler(store, session_factory=session_factory).report().unattributed_blobs) == 4


def test_a_retry_after_a_failed_publication_adopts_the_published_members(
    store, session_factory, project, key, engine, bucket_keys
) -> None:
    flaky = FailingAt(store, "publish", 3)
    failing = IngestService(flaky, session_factory=session_factory)
    with pytest.raises(DomainError):
        upload(failing, project, committed("ar_baseline.zip"), key, label="first")
    published = set(bucket_keys())
    assert len(published) == 2

    healthy = IngestService(store, session_factory=session_factory)
    outcome = upload(healthy, project, committed("ar_baseline.zip"), key, label="second")
    assert len(outcome.version.manifest) == 4
    assert published <= set(bucket_keys()), "the retry wrote the first two members again"
    assert len(bucket_keys()) == 4
    assert Reconciler(store, session_factory=session_factory).report().is_clean


# ---------------------------------------------------------------------------------------
# Reconciliation over a bundle's version
# ---------------------------------------------------------------------------------------


def test_verify_version_checks_every_stored_member_and_names_a_tampered_one(
    store, session_factory, service, project, key, raw_s3, s3_settings
) -> None:
    from auditmanager.storage import _object_layout as layout  # noqa: PLC2701

    version = upload(service, project, committed("ar_baseline.zip"), key).version
    reconciler = Reconciler(store, session_factory=session_factory)
    reconciler.verify_version(version.version_uid)
    assert reconciler.report().is_clean

    markdown = next(e for e in version.manifest if e.role == MANIFEST_ROLE_MARKDOWN)
    head = raw_s3.head_object(Bucket=s3_settings.bucket, Key=layout.canonical_key(markdown.blob_id))
    tampered = b"x" * markdown.size_bytes
    raw_s3.put_object(
        Bucket=s3_settings.bucket, Key=layout.canonical_key(markdown.blob_id), Body=tampered,
        Metadata=head["Metadata"], ContentType=head["ContentType"],
    )
    with pytest.raises(DomainError) as raised:
        reconciler.verify_version(version.version_uid)
    assert raised.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(raised.value.detail_fields)["role"] == MANIFEST_ROLE_MARKDOWN
