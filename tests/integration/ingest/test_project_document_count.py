"""`listProjects.document_count`, against real PostgreSQL. Owner ruling `R-10`.

The field was declared by the frozen `Project` schema and had no producer, so a project
list rendered `documents --`. `R-10` authorises filling it and nothing wider.

Four properties are asserted here, and each one was shown able to fail by mutating the
implementation until it went red -- the mutations are named in
`docs/program/reviews/W19-API.md` section 5:

1. the count belongs to **its own** project, not to a sibling and not to the database;
2. a project with no documents reports **0**, an ``int``, not a missing field and not
   ``None``;
3. it counts exactly what ``listDocuments`` returns, including the case the two
   definitions could disagree about -- a document with no published version;
4. the whole listing is **one statement**, however many projects there are.

Property 4 is asserted over the driver rather than over the source, because "one query"
is a claim about what reaches the database and reading the repository for a `for` loop
only proves that today's shape has no loop in the place the reader looked.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from auditmanager.documents import DocumentRepository
from auditmanager.ingest import IngestService

DISPLAY_TITLE = "Annual report 2026"
SOURCE_FILENAME = "annual_report_2026.pdf"


def _upload(service: IngestService, project_uid, content: bytes, key) -> Any:
    return service.upload_single_pdf(
        project_uid=project_uid,
        content=content,
        source_filename=SOURCE_FILENAME,
        display_title=DISPLAY_TITLE,
        idempotency_key=key("count"),
    )


def _counts(service: IngestService) -> dict[str, int]:
    return {str(row.project_uid): row.document_count for row in service.list_projects()}


@pytest.fixture
def statements(engine: Engine) -> Iterator[list[str]]:
    """Every SQL statement the application sends, captured at the driver seam.

    ``before_cursor_execute`` fires once per ``execute`` call on the connection, so a
    repository that ran one query per project would append one row per project here. The
    listener is registered on the shared session-scoped ``Engine`` and removed again, so
    it cannot leak into another test.
    """
    captured: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        captured.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield captured
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_a_project_with_no_documents_reports_zero_and_not_an_absence(
    service: IngestService,
) -> None:
    """`D-3`: zero is a measurement, absent is a different and weaker claim.

    ``0`` is also asserted to be an ``int`` and not ``None``, because ``ProjectView``
    omits the field when it is ``None`` and a silently omitted field renders as the same
    `documents --` this ruling exists to remove.
    """
    created = service.create_project("A project nobody has uploaded to")

    (listed,) = service.list_projects()

    assert listed.project_uid == created.project_uid
    assert listed.document_count == 0
    assert isinstance(listed.document_count, int)
    assert listed.document_count is not None


def test_each_project_counts_its_own_documents_and_not_its_neighbours(
    service: IngestService, baseline_pdf: bytes, key, track
) -> None:
    """Two projects, two different counts, and neither of them the total.

    The three numbers are deliberately distinct -- 2, 1 and 0 -- so no mutation can
    satisfy this by accident. A count keyed to the wrong parent swaps two of them; a
    count of the whole database reports 3 three times; a count that drops the ``WHERE``
    on the join reports the same number for every row.
    """
    busy = service.create_project("Two documents")
    quiet = service.create_project("One document")
    empty = service.create_project("No documents")

    for _ in range(2):
        track(_upload(service, busy.project_uid, baseline_pdf, key).version.source.blob_id)
    track(_upload(service, quiet.project_uid, baseline_pdf, key).version.source.blob_id)

    counts = _counts(service)

    assert counts[str(busy.project_uid)] == 2
    assert counts[str(quiet.project_uid)] == 1
    assert counts[str(empty.project_uid)] == 0
    assert sum(counts.values()) == 3, (
        "the three counts do not add up to the three documents in the database; "
        f"the listing reported {counts}"
    )


def test_the_count_is_exactly_what_list_documents_returns(
    service: IngestService, baseline_pdf: bytes, key, track, session_factory
) -> None:
    """The agreement, asserted where the two definitions could come apart.

    ``listDocuments`` INNER JOINs ``document`` to the version its ``current_version_uid``
    names, so **a document with no published version is not listed**. A count of
    ``document`` rows would therefore report "2 documents" above a list of one, and the
    screen would be showing a number nobody can click on.

    The unversioned row is inserted directly, because no path through the API can leave
    one behind today: ``_commit_publication`` creates the document and publishes its
    version inside a single transaction. That is exactly why the divergence has to be
    manufactured to be tested -- it is unreachable now, the column is nullable, and
    `D-17` says the restore path is not yet sound.
    """
    project = service.create_project("One published, one not")
    track(_upload(service, project.project_uid, baseline_pdf, key).version.source.blob_id)

    with session_factory() as session:
        session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, :t)"
            ),
            {
                "d": "doc_01M2T000000000000000000000",
                "p": str(project.project_uid),
                "t": "Created but never published",
            },
        )
        session.commit()

    with session_factory() as session:
        rows = session.execute(
            text("SELECT count(*) FROM document WHERE project_uid = :p"),
            {"p": str(project.project_uid)},
        ).scalar_one()
    assert rows == 2, "the fixture failed to create the unversioned document"

    (listed,) = service.list_projects()
    documents = service.list_documents(project.project_uid)

    assert len(documents) == 1, (
        "listDocuments returned the unversioned document, which would make this test "
        "assert the wrong agreement"
    )
    assert listed.document_count == len(documents) == 1, (
        f"document_count is {listed.document_count} and listDocuments returns "
        f"{len(documents)}; a screen would render a number above a shorter list"
    )


def test_the_whole_listing_costs_one_statement_however_many_projects(
    service: IngestService, baseline_pdf: bytes, key, track, statements: list[str]
) -> None:
    """One query, not N -- measured at the driver, not read off the source.

    Five projects with documents spread unevenly across them. A count fetched per project
    would send six statements and this would report six.
    """
    projects = [service.create_project(f"Project {n}") for n in range(5)]
    for project in projects[:3]:
        track(_upload(service, project.project_uid, baseline_pdf, key).version.source.blob_id)

    statements.clear()
    listed = service.list_projects()

    selects = [s for s in statements if s.upper().startswith("SELECT")]
    assert len(listed) == 5
    assert len(selects) == 1, (
        f"listing 5 projects sent {len(selects)} SELECTs, not 1:\n"
        + "\n".join(selects)
    )
    assert "count(" in selects[0].lower(), (
        "the single statement does not aggregate, so the count came from somewhere else: "
        + selects[0]
    )
    assert sorted(row.document_count for row in listed) == [0, 0, 1, 1, 1]


def test_the_repository_returns_the_count_on_the_row_it_measured(
    session_factory,
) -> None:
    """The lowest layer, directly: `_LIST_PROJECTS` projects a fourth column.

    ``ProjectListingRecord`` has no default for ``document_count``, so this cannot pass
    against a repository that forgot to select it -- construction would raise rather than
    hand back a ``None`` that the layers above would quietly omit.
    """
    repo = DocumentRepository()
    with session_factory() as session:
        repo.create_project(session, name="Measured at the bottom")
        session.commit()
        (listed,) = repo.list_projects(session)

    assert listed.document_count == 0
    assert type(listed).__name__ == "ProjectListingRecord"
