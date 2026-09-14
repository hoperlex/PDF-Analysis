"""The accepted path: one PDF becomes one immutable version with its manifest.

Against real PostgreSQL and real MinIO. Every "what is in the bucket" assertion is made
with a plain boto3 client rather than through the adapter, so a bug in the adapter's own
inspection cannot make one of these pass.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest
from sqlalchemy import text

from auditmanager.documents.models import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.documents import ROLE_SOURCE_DOCUMENT
from auditmanager.ingest import ACCEPTED_MEDIA_TYPE, IngestService
from auditmanager.shared.errors import DomainError, ErrorCode, screen_message
from auditmanager.storage import derive_blob_id

SOURCE_FILENAME = "annual_report_2026.pdf"
DISPLAY_TITLE = "Annual report 2026"


def upload(service: IngestService, project, content, key, **overrides):
    arguments = {
        "project_uid": project.project_uid,
        "content": content,
        "source_filename": SOURCE_FILENAME,
        "display_title": DISPLAY_TITLE,
        "idempotency_key": key("baseline"),
    }
    arguments.update(overrides)
    return service.upload_single_pdf(**arguments)


def test_project_is_created_and_listed(service: IngestService) -> None:
    created = service.create_project("Kitchen refurbishment")
    listed = service.list_projects()

    assert created.name == "Kitchen refurbishment"
    assert [item.project_uid for item in listed] == [created.project_uid]
    assert service.get_project(created.project_uid) == created


def test_baseline_publishes_one_version_and_one_available_blob(
    service, project, baseline_pdf, key, engine, bucket_keys, track, store
) -> None:
    expected_sha = hashlib.sha256(baseline_pdf).hexdigest()
    before = set(bucket_keys())

    outcome = upload(service, project, baseline_pdf, key)
    version = outcome.version
    track(version.source.blob_id)

    assert outcome.replayed is False
    assert version.sha256 == expected_sha
    assert version.byte_size == len(baseline_pdf)
    assert version.page_count == 8
    assert version.media_type == ACCEPTED_MEDIA_TYPE
    assert version.project_uid == project.project_uid

    # Exactly one manifest row, and it addresses the bytes by derived identity.
    assert len(version.manifest) == 1
    entry = version.source
    assert entry.role == MANIFEST_ROLE_SOURCE_DOCUMENT
    assert entry.sha256 == expected_sha
    assert entry.size_bytes == len(baseline_pdf)
    assert entry.media_type == ACCEPTED_MEDIA_TYPE
    assert entry.blob_id == derive_blob_id(sha256=expected_sha, size=len(baseline_pdf))

    # One row in each table, and the blob is available with its content facts recorded.
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM document_version")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM input_manifest_entry")).scalar_one() == 1
        state, sha256, size, media_type = connection.execute(
            text("SELECT state, sha256, size_bytes, media_type FROM blob")
        ).one()
    assert state == "available"
    assert sha256 == expected_sha
    assert int(size) == len(baseline_pdf)
    assert media_type == ACCEPTED_MEDIA_TYPE

    # Exactly one new object, and the staged copy is gone: no temporary residue.
    added = set(bucket_keys()) - before
    assert len(added) == 1, added
    assert not [item for item in added if item.startswith("temporary/")]

    # The bytes are readable by identity alone and are byte-identical.
    assert store.read(entry.blob_id) == baseline_pdf
    assert service.read_source_bytes(version.version_uid) == baseline_pdf


def test_manifest_query_is_the_seam_b5_consumes(
    service, project, baseline_pdf, key, track
) -> None:
    outcome = upload(service, project, baseline_pdf, key)
    track(outcome.version.source.blob_id)

    manifest = service.manifest_for(outcome.version.version_uid)

    assert manifest == outcome.version.manifest
    assert [entry.role for entry in manifest] == [MANIFEST_ROLE_SOURCE_DOCUMENT]


def test_return_value_carries_no_filename_ordinal_key_or_path(
    service, project, baseline_pdf, key, track, engine
) -> None:
    """Opaque identity, mechanically checked over the whole returned object graph.

    ``docs/program/P02_SEAMS.md`` section 2.2 lists a file name, an object key, a path
    and a display ordinal among the values that are never identities. This walks every
    field of everything the command returns and asserts none of them is present, by
    field name and by value.
    """
    outcome = upload(service, project, baseline_pdf, key)
    track(outcome.version.source.blob_id)

    # `version_ordinal` is deliberately NOT in this set. Foundation invariant 3 says a
    # display ordinal is not an *identifier*; it does not say it may not be shown, and the
    # frozen `DocumentVersion` schema in contracts/api/v1 lists it as **required**.
    # Withholding it left getDocumentVersion and uploadDocument unable to emit a conformant
    # body from this surface at all - B6 found that, and it blocked Gate C. The invariant is
    # enforced where it actually bites, by `test_no_version_is_resolved_by_its_ordinal`:
    # nothing looks a version up by ordinal, so the ordinal is a label, never a key.
    #
    # `display_title` left this set for the same reason and a narrower one: invariant 3 names
    # path, object key, filename and display ordinal, and a display title is none of them.
    # The frozen `DocumentVersion` schema declares it, and `B7`'s upload panel had no way to
    # show a reviewer the title they had just typed. `source_filename` stays forbidden - that
    # one IS a filename, and it is the field the invariant is actually about.
    forbidden_names = {
        "bucket",
        "current_version_uid",
        "file_name",
        "filename",
        "key",
        "object_key",
        "path",
        "source_filename",
        "uri",
        "url",
    }
    seen_values: list[object] = []

    def walk(value: object) -> None:
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            for field in dataclasses.fields(value):
                assert field.name not in forbidden_names, (
                    f"{type(value).__name__}.{field.name} is a non-identity the "
                    "contract forbids in a public return value"
                )
                walk(getattr(value, field.name))
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
            return
        seen_values.append(value)

    walk(outcome)

    rendered = [str(item) for item in seen_values]
    assert SOURCE_FILENAME not in rendered, (
        "the source filename crossed the boundary; invariant 3 names it directly"
    )
    # DISPLAY_TITLE is deliberately expected to be present. It is the label the uploader
    # typed, the frozen DocumentVersion schema declares it, and a reviewer has no other way
    # to see the title they gave the document. Asserting its absence was asserting that a
    # feature must not work.
    assert DISPLAY_TITLE in rendered, (
        "the display title is withheld, so nothing can show a reviewer the title they typed"
    )

    # Every string in the returned graph would survive the envelope screen -- the guard
    # that refuses a path, an object key, a URL, a credential, SQL or a stack frame.
    for item in rendered:
        if item:
            screen_message(item)

    # The values really are stored -- this is omission from the projection, not a
    # failure to record them.
    with engine.connect() as connection:
        stored_filename, stored_ordinal = connection.execute(
            text("SELECT source_filename, version_ordinal FROM document_version")
        ).one()
    assert stored_filename == SOURCE_FILENAME
    assert int(stored_ordinal) == 1


def test_second_version_of_one_document_gets_the_next_ordinal(
    service, project, baseline_pdf, key, track, engine
) -> None:
    first = upload(service, project, baseline_pdf, key)
    track(first.version.source.blob_id)

    # Different bytes, so a different blob identity, appended to the same document.
    altered = baseline_pdf + b"\n% a trailing comment\n"
    second = service.upload_single_pdf(
        project_uid=project.project_uid,
        content=altered,
        source_filename="annual_report_2026_rev2.pdf",
        display_title=DISPLAY_TITLE,
        idempotency_key=key("second"),
        document_uid=first.version.document_uid,
    )
    track(second.version.source.blob_id)

    assert second.version.document_uid == first.version.document_uid
    assert second.version.version_uid != first.version.version_uid
    assert second.version.source.blob_id != first.version.source.blob_id

    with engine.connect() as connection:
        ordinals = [
            int(row[0])
            for row in connection.execute(
                text(
                    "SELECT version_ordinal FROM document_version "
                    "WHERE document_uid = :d ORDER BY version_ordinal"
                ),
                {"d": str(first.version.document_uid)},
            )
        ]
        current = connection.execute(
            text("SELECT current_version_uid FROM document WHERE document_uid = :d"),
            {"d": str(first.version.document_uid)},
        ).scalar_one()

    assert ordinals == [1, 2]
    # `document` is a mutable aggregate: the pointer moves while both version rows stay.
    assert current == str(second.version.version_uid)


def test_identical_content_under_a_new_key_reuses_the_blob(
    service, project, baseline_pdf, key, track, bucket_keys, engine
) -> None:
    """``blob_id`` is derived from ``(sha256, size)``, so identical bytes deduplicate."""
    first = upload(service, project, baseline_pdf, key)
    track(first.version.source.blob_id)
    after_first = set(bucket_keys())

    second = upload(service, project, baseline_pdf, key, idempotency_key=key("again"))
    track(second.version.source.blob_id)

    assert second.version.version_uid != first.version.version_uid
    assert second.version.source.blob_id == first.version.source.blob_id
    assert set(bucket_keys()) == after_first, "identical content wrote a second object"

    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT count(*) FROM document_version")).scalar_one()
            == 2
        )


def test_unknown_project_is_refused_before_anything_is_published(
    service, baseline_pdf, key, bucket_keys, engine
) -> None:
    from auditmanager.shared.identity import ProjectUid

    before = set(bucket_keys())
    with pytest.raises(DomainError) as raised:
        service.upload_single_pdf(
            project_uid=ProjectUid.new(),
            content=baseline_pdf,
            source_filename=SOURCE_FILENAME,
            display_title=DISPLAY_TITLE,
            idempotency_key=key("orphan-project"),
        )

    assert raised.value.code is ErrorCode.NOT_FOUND
    assert set(bucket_keys()) == before
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM blob")).scalar_one() == 0
        assert (
            connection.execute(text("SELECT count(*) FROM command_record")).scalar_one()
            == 0
        ), "a bad target burned an idempotency key"


def test_no_version_is_resolved_by_its_ordinal() -> None:
    """The ordinal is a label, never a key.

    This is what foundation invariant 3 actually forbids. `version_ordinal` may be shown -
    the frozen contract requires it on `DocumentVersion` - but nothing may address a
    version by it. A `WHERE version_ordinal = ...` anywhere in the package would mean the
    ordinal had become an identifier.

    The allocation query `max(version_ordinal) + 1` is excluded: it computes the next
    label, it does not resolve a version.
    """
    import pathlib
    import re

    package = pathlib.Path(__file__).resolve().parents[3] / "src" / "auditmanager"
    sources = [p for p in package.rglob("*.py")]
    assert len(sources) > 20, "the sweep found too few sources to be meaningful"

    resolving = re.compile(r"version_ordinal\s*=\s*:|WHERE[^\n]*version_ordinal\s*=", re.I)
    offenders = [
        str(p.relative_to(package))
        for p in sources
        if resolving.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"a version is being resolved by its ordinal in: {offenders}"


def test_projects_are_listed_newest_first(session_factory) -> None:  # noqa: ANN001
    """`listProjects` declares "newest first"; the repository returned oldest first.

    Two claims, deliberately separated. Creation order inside one `created_at` tick is not
    recoverable - a ULID is monotonic across milliseconds, not within one - so what the
    contract guarantees is descending time, and what the tiebreaker buys is a total, stable
    order for a cursor to page over.

    The timestamps are spread explicitly. The first version of this test created four
    projects in a loop and asserted the returned stamps were descending; all four landed in
    the same millisecond, every stamp was equal, and the assertion held for **any** order -
    it stayed green against an ORDER BY created_at ASC. A test that cannot fail is worse
    than no test, because it reports a guarantee nobody is providing.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    from auditmanager.documents import DocumentRepository

    repo = DocumentRepository()
    base = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    with session_factory() as session:
        created = [repo.create_project(session, name=f"Проект {n}") for n in range(4)]
        for offset, record in enumerate(created):
            session.execute(
                text("UPDATE project SET created_at = :t WHERE project_uid = :p"),
                {"t": base + timedelta(minutes=offset), "p": str(record.project_uid)},
            )
        session.commit()
        listed = repo.list_projects(session)
        again = repo.list_projects(session)

    stamps = [p.created_at for p in listed]
    assert len(set(stamps)) == len(stamps), (
        "the fixture failed to spread the timestamps, so this test cannot discriminate"
    )
    assert stamps == sorted(stamps, reverse=True), (
        f"projects are not newest first by created_at: {stamps}"
    )
    assert [str(p.project_uid) for p in listed] == [str(p.project_uid) for p in again], (
        "the order is not stable across two calls, so a cursor cannot page over it"
    )
