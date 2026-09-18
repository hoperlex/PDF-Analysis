"""`listDocuments`, `listVersions` and `listRuns`, and the cost `RunStatus` now carries.

`W18-SEAL`, under owner ruling `R-5`. `DEBT_REGISTER.md` **D-16** and **D-21**.

Every test here is written so that a plausible wrong implementation fails it. The three
listings are one shape -- a `GET` of a child collection, newest first, paged by an opaque
cursor -- so the three ways such a thing goes wrong are the three things asserted:

* **the wrong rows.** A listing that ignores its path parameter returns a superset and
  looks like it worked. Each fixture therefore builds a *sibling* -- a second project, a
  second document, a second version -- whose rows must not appear, and asserts the listing
  is a proper non-empty subset of what exists.
* **the wrong page.** A `limit` that is accepted and ignored, or a cursor that silently
  restarts the listing, reads to a caller as a complete answer. The walk below resumes
  through every page and requires each row exactly once, against an oracle read from the
  rows rather than from a second call to the listing.
* **the wrong order.** Rows created inside one transaction share `now()` to the
  microsecond, so a fixture that does not stamp distinct times cannot tell
  `ORDER BY created_at DESC` from `ORDER BY uid DESC`. Every fixture here stamps distinct
  times **whose order disagrees with the identity order**, and asserts the disagreement
  before any ordering assertion leans on it.

And the fourth thing, which is not about paging at all: **an unknown parent is `404`, not
an empty page.** "This project has nothing in it yet" is a different answer from "there is
no such project", and a caller acts on them differently.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from w13_api_driver import Answer, Request, Surface, dispatch
from auditmanager.api.routers import build_router
from auditmanager.shared.identity import (
    AnalysisProfileId,
    BlobId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

from .conftest import (
    DatabaseFindingAdapter,
    IngestDocumentAdapter,
    LedgerDecisionAdapter,
    SeamExportAdapter,
)


def ok(response: Answer) -> dict[str, Any]:
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


def get(router: Surface, path: str) -> Answer:
    return dispatch(router, Request.build("GET", path))


def uids(page: Mapping[str, Any], key: str) -> list[str]:
    return [item[key] for item in page["items"]]


def walk(router: Surface, target: str, key: str, *, limit: int = 1) -> list[str]:
    """Page the whole listing `limit` rows at a time and collect the identities.

    The separator between pages is the server's own `next_cursor`, so a cursor that
    silently restarted the listing shows up here as a repeated identity and a walk that
    does not terminate -- which the bound below turns into a failure rather than a hang.
    """
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(50):
        suffix = f"&cursor={cursor}" if cursor else ""
        page = ok(get(router, f"{target}?limit={limit}{suffix}"))
        seen.extend(uids(page, key))
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            return seen
    raise AssertionError(f"{target} did not terminate in 50 pages: {seen}")


# ---------------------------------------------------------------------------
# The fixture: two projects, two documents, two versions, and rows on each side
# ---------------------------------------------------------------------------

#: Seconds back from `now()`, one per row. Deliberately **not** monotonic in the order the
#: rows are created, so the time order and the identity order disagree -- see the module
#: docstring. `Ladder` in `test_query_surface.py` establishes the same property for
#: projects, and for the same reason.
_OFFSETS = (30, 90, 60, 10, 120)


class Catalogue:
    """One project of three documents, one document of three versions, one version of
    three runs -- and a sibling of each, holding rows that must never be listed."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.project_uid = str(ProjectUid.new())
        self.other_project_uid = str(ProjectUid.new())
        self._project(self.project_uid, "Проект А")
        self._project(self.other_project_uid, "Проект Б")

        # Three documents in the project, each with exactly one published version --
        # which is what the twelve operations produce, because `uploadDocument` creates
        # the document and its first version together.
        self.documents: list[str] = []
        self.current_versions: list[str] = []
        for index in range(3):
            document_uid = str(DocumentUid.new())
            self._document(document_uid, self.project_uid, f"АР {index}")
            version_uid = self._version(document_uid, ordinal=1, offset=_OFFSETS[index])
            self._point_at(document_uid, version_uid)
            self.documents.append(document_uid)
            self.current_versions.append(version_uid)

        # A document in the *other* project. It must not appear in this project's listing.
        self.other_document_uid = str(DocumentUid.new())
        self._document(self.other_document_uid, self.other_project_uid, "Чужой АР")
        self.other_version_uid = self._version(
            self.other_document_uid, ordinal=1, offset=45
        )
        self._point_at(self.other_document_uid, self.other_version_uid)

        # A fourth document carrying three versions. `listVersions` is asserted on this
        # one; `listDocuments` must show only the version it currently points at.
        self.versioned_document_uid = str(DocumentUid.new())
        self._document(self.versioned_document_uid, self.project_uid, "АР, три версии")
        self.versions: list[str] = [
            self._version(
                self.versioned_document_uid, ordinal=ordinal, offset=_OFFSETS[ordinal - 1]
            )
            for ordinal in (1, 2, 3)
        ]
        self._point_at(self.versioned_document_uid, self.versions[-1])

        # Three runs on the first document's version, and one on a sibling version.
        self.run_version_uid = self.current_versions[0]
        self.runs = [
            self._run(self.run_version_uid, offset=_OFFSETS[index]) for index in range(3)
        ]
        self.other_run = self._run(self.current_versions[1], offset=15)
        self.session.flush()

    # -- rows ---------------------------------------------------------------

    def _project(self, project_uid: str, name: str) -> None:
        self.session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, :n)"),
            {"p": project_uid, "n": name},
        )

    def _document(self, document_uid: str, project_uid: str, title: str) -> None:
        self.session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, :t)"
            ),
            {"d": document_uid, "p": project_uid, "t": title},
        )

    def _version(self, document_uid: str, *, ordinal: int, offset: int) -> str:
        version_uid = str(VersionUid.new())
        digest = hashlib.sha256(version_uid.encode("utf-8")).hexdigest()
        self.session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, "
                "version_ordinal, media_type, byte_size, sha256, page_count, "
                "published_at) VALUES (:v, :d, :o, 'application/pdf', 1024, :s, 2, "
                "now() - CAST(:age AS interval))"
            ),
            {
                "v": version_uid,
                "d": document_uid,
                "o": ordinal,
                "s": digest,
                "age": f"{offset} seconds",
            },
        )
        # The frozen `DocumentVersion` declares `input_manifest` required, so every
        # version here carries one: a listing whose rows had no manifest would not be the
        # shape the contract declares, and the N+1 the page-wide manifest query replaces
        # would be invisible without one.
        #
        # The blob is walked `temporary -> verifying -> available` rather than inserted
        # in its terminal state, because `am_guard_state_transition` refuses the shortcut
        # -- a row reached by a write the schema would not have allowed is not evidence.
        blob_id = str(BlobId.new())
        self.session.execute(
            text("INSERT INTO blob (blob_id, state) VALUES (:b, 'temporary')"),
            {"b": blob_id},
        )
        for state in ("verifying", "available"):
            self.session.execute(
                text(
                    "UPDATE blob SET state = :s, sha256 = :h, size_bytes = 1024, "
                    "media_type = 'application/pdf' WHERE blob_id = :b"
                ),
                {"s": state, "h": digest, "b": blob_id},
            )
        self.session.execute(
            text(
                "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, "
                "size_bytes, media_type) VALUES (:v, 'source_document', :b, :s, 1024, "
                "'application/pdf')"
            ),
            {"v": version_uid, "b": blob_id, "s": digest},
        )
        return version_uid

    def _point_at(self, document_uid: str, version_uid: str) -> None:
        self.session.execute(
            text(
                "UPDATE document SET current_version_uid = :v WHERE document_uid = :d"
            ),
            {"v": version_uid, "d": document_uid},
        )

    def _run(self, version_uid: str, *, offset: int) -> str:
        run_id = str(RunId.new())
        project_uid = self.session.execute(
            text(
                "SELECT d.project_uid FROM document_version v "
                "JOIN document d ON d.document_uid = v.document_uid "
                "WHERE v.version_uid = :v"
            ),
            {"v": version_uid},
        ).scalar_one()
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest, created_at) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, "
                "now() - CAST(:age AS interval))"
            ),
            {
                "r": run_id,
                "p": project_uid,
                "v": version_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
                "s": hashlib.sha256(run_id.encode("utf-8")).hexdigest(),
                "age": f"{offset} seconds",
            },
        )
        return run_id

    # -- oracles, read from the rows and never from the listing --------------

    def newest_first(self, sql: str, params: Mapping[str, Any], key: str) -> list[str]:
        return [row[0] for row in self.session.execute(text(sql), params).all()]


@pytest.fixture
def catalogue(session: Session) -> Catalogue:
    built = Catalogue(session)
    # The fixture has to discriminate before any assertion leans on it.
    stamps = (
        session.execute(
            text(
                "SELECT published_at FROM document_version WHERE version_uid = ANY(:v)"
            ),
            {"v": built.current_versions},
        )
        .scalars()
        .all()
    )
    assert len(set(stamps)) == len(built.current_versions), (
        "the documents' current versions share a published_at, so an ordering assertion "
        "over them would be an assertion about the tiebreaker"
    )
    by_time = [
        uid
        for uid, _ in sorted(
            zip(built.current_versions, stamps), key=lambda pair: pair[1], reverse=True
        )
    ]
    assert by_time != sorted(built.current_versions, reverse=True), (
        "time order and identity order agree, so this fixture cannot tell "
        "`ORDER BY published_at DESC` from `ORDER BY version_uid DESC`"
    )
    return built


@pytest.fixture
def listing_router(
    ingest: Any, session: Session, session_factory: sessionmaker[Session]
) -> Surface:
    """The surface with the **shipped** document and run adapters behind it.

    `test_query_surface.py` states the reason at length and it applies here exactly: a
    fixture adapter that filters proves only that the fixture filters. `DocumentPort` here
    is `IngestDocumentAdapter` over the real `IngestService` -- which is what the shipped
    `DocumentAdapter` is too, one delegation deeper -- and `RunPort` is the shipped
    `RunAdapter`, so `cost_micros` reaches the wire through the code the application runs.

    `RunAdapter`'s provider collaborators are `None` on purpose: nothing this module
    drives starts a run, and passing a fake provider would make it possible to.
    """
    from auditmanager.bootstrap.adapters import RunAdapter

    return Surface(
        build_router(
            projects=_UnusedProjectPort(),
            documents=IngestDocumentAdapter(ingest, session),
            runs=RunAdapter(
                session_factory,
                blob_store=None,
                adapter=None,
                provider_config=None,
                provider_mode="recorded",
                analysis_profile_id=str(AnalysisProfileId.new()),
                prompt_bundle_id=str(PromptBundleId.new()),
            ),
            findings=DatabaseFindingAdapter(session),
            decisions=LedgerDecisionAdapter(session),
            exports=SeamExportAdapter(session),
        )
    )


class _UnusedProjectPort:
    """`build_router` needs six ports; this module drives none of the project ones."""

    def create_project(self, **_: Any) -> Any:  # pragma: no cover - never called
        raise AssertionError("this suite does not drive createProject")

    def list_projects(self) -> Sequence[Any]:  # pragma: no cover - never called
        raise AssertionError("this suite does not drive listProjects")


@pytest.fixture
def counting_router(ingest: Any, session: Session) -> Surface:
    """`listProjects` and `listDocuments` on one surface, both over shipped adapters.

    `W19-API`, owner ruling `R-10`. The two operations have to agree about what a document
    is, and the only way to assert that is to ask both of them in one process against one
    set of rows. `ProjectPort` is the shipped `bootstrap.adapters.ProjectAdapter` -- not
    the suite's `IngestProjectAdapter` copy in `conftest.py` -- because a count forwarded
    by a fixture proves that the fixture forwards it.
    """
    from auditmanager.bootstrap.adapters import ProjectAdapter

    return Surface(
        build_router(
            projects=ProjectAdapter(ingest),
            documents=IngestDocumentAdapter(ingest, session),
            runs=_Unused(),
            findings=_Unused(),
            decisions=_Unused(),
            exports=_Unused(),
        )
    )


class _Unused:
    """Four ports this fixture's two operations never reach."""

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - never called
        raise AssertionError(f"counting_router does not drive {name}")


def test_document_count_is_the_length_of_the_list_it_sits_above(
    counting_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """`R-10`, and the defect it would be to ship the field carelessly.

    The catalogue holds four documents in one project and one in a sibling, so the two
    counts are different from each other and neither is the total -- a count keyed to the
    wrong parent, or to the whole `document` table, cannot satisfy this.

    Then the case where the two definitions come apart: a document with no published
    version. `listDocuments` INNER JOINs on `current_version_uid` and does not list it
    (`test_a_document_with_no_published_version_is_not_listed` is the assertion of that),
    so a `document_count` that counted `document` rows would render "5 documents" above a
    list of four. The count is asserted **equal to the length of the page**, not to a
    literal, so the two can never drift apart without this going red.
    """
    orphan = str(DocumentUid.new())
    session.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'Создан, не опубликован')"
        ),
        {"d": orphan, "p": catalogue.project_uid},
    )
    session.flush()

    rows = session.execute(
        text("SELECT count(*) FROM document WHERE project_uid = :p"),
        {"p": catalogue.project_uid},
    ).scalar_one()
    assert rows == 5, (
        "the fixture does not hold the unversioned document, so the divergence this "
        "test exists for is not present"
    )

    listing = ok(get(counting_router, "/projects?limit=200"))
    counts = {item["project_uid"]: item for item in listing["items"]}

    for project_uid in (catalogue.project_uid, catalogue.other_project_uid):
        assert project_uid in counts, f"{project_uid} is missing from the project page"
        item = counts[project_uid]
        assert "document_count" in item, (
            f"{project_uid} carries no document_count; the field is declared and this is "
            "the `documents --` R-10 exists to remove"
        )
        page = ok(get(counting_router, f"/projects/{project_uid}/documents?limit=200"))
        assert item["document_count"] == len(page["items"]), (
            f"{project_uid} reports {item['document_count']} documents above a list of "
            f"{len(page['items'])}"
        )

    assert counts[catalogue.project_uid]["document_count"] == 4
    assert counts[catalogue.other_project_uid]["document_count"] == 1


# ---------------------------------------------------------------------------
# The rows each listing returns
# ---------------------------------------------------------------------------


def test_list_documents_returns_this_project_and_not_the_next_one(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    """A listing that ignored its path parameter would return the other project's
    document too, and would look like it had worked."""
    page = ok(
        get(listing_router, f"/projects/{catalogue.project_uid}/documents?limit=200")
    )
    returned = set(uids(page, "document_uid"))
    assert returned == set(catalogue.documents) | {catalogue.versioned_document_uid}
    assert catalogue.other_document_uid not in returned, (
        "the listing returned a document belonging to another project"
    )
    assert {item["project_uid"] for item in page["items"]} == {catalogue.project_uid}


def test_list_documents_shows_the_version_the_document_currently_points_at(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    """One row per document, carrying the current version and not every version.

    The document with three versions is the case that discriminates: a listing that
    joined `document_version` on `document_uid` rather than on `current_version_uid`
    returns three rows for it, and the count alone would not say so.
    """
    page = ok(
        get(listing_router, f"/projects/{catalogue.project_uid}/documents?limit=200")
    )
    rows = {item["document_uid"]: item for item in page["items"]}
    assert len(page["items"]) == len(rows), "a document appeared more than once"
    assert rows[catalogue.versioned_document_uid]["version_uid"] == catalogue.versions[-1]
    assert rows[catalogue.versioned_document_uid]["version_ordinal"] == 3


def test_a_document_with_no_published_version_is_not_listed(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """There is nothing a caller could open, stream or start a run against.

    Unreachable through the twelve operations -- `uploadDocument` writes the document and
    its first version in one transaction -- and reachable in the schema, which is where a
    listing has to be right.
    """
    empty = str(DocumentUid.new())
    session.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'Пустой')"
        ),
        {"d": empty, "p": catalogue.project_uid},
    )
    session.flush()
    page = ok(
        get(listing_router, f"/projects/{catalogue.project_uid}/documents?limit=200")
    )
    assert empty not in set(uids(page, "document_uid"))
    assert page["items"], "the listing is empty, so the absence above proves nothing"


def test_list_versions_returns_this_document_and_not_a_sibling(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    page = ok(
        get(
            listing_router,
            f"/documents/{catalogue.versioned_document_uid}/versions?limit=200",
        )
    )
    assert uids(page, "version_uid") == list(reversed(catalogue.versions)), (
        "versions come back newest first, by the document's own publication order"
    )
    assert [item["version_ordinal"] for item in page["items"]] == [3, 2, 1]
    assert catalogue.other_version_uid not in set(uids(page, "version_uid"))
    assert set(uids(page, "version_uid")).isdisjoint(catalogue.current_versions), (
        "the listing returned versions of another document"
    )


def test_list_runs_returns_this_versions_runs_and_not_a_siblings(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    page = ok(get(listing_router, f"/versions/{catalogue.run_version_uid}/runs?limit=200"))
    returned = set(uids(page, "run_id"))
    assert returned == set(catalogue.runs)
    assert catalogue.other_run not in returned, (
        "the listing returned a run belonging to another version"
    )
    assert {item["version_uid"] for item in page["items"]} == {catalogue.run_version_uid}


def test_a_run_in_a_listing_is_the_same_body_as_the_run_read_on_its_own(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    """One resource, one shape. A lighter list item would be a second shape to drift."""
    page = ok(get(listing_router, f"/versions/{catalogue.run_version_uid}/runs?limit=200"))
    for item in page["items"]:
        single = ok(get(listing_router, f"/runs/{item['run_id']}"))
        assert item == single, (
            f"{item['run_id']} reads differently in a listing than on its own"
        )


# ---------------------------------------------------------------------------
# The order, and the page
# ---------------------------------------------------------------------------


def test_the_listings_are_newest_first_and_not_highest_identity_first(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """The fixture's times disagree with its identities, so this can tell them apart."""
    documents = ok(
        get(listing_router, f"/projects/{catalogue.project_uid}/documents?limit=200")
    )
    expected = catalogue.newest_first(
        "SELECT v.version_uid FROM document d "
        "JOIN document_version v ON v.version_uid = d.current_version_uid "
        "WHERE d.project_uid = :p ORDER BY v.published_at DESC, v.version_uid DESC",
        {"p": catalogue.project_uid},
        "version_uid",
    )
    assert uids(documents, "version_uid") == expected
    assert expected != sorted(expected, reverse=True), (
        "the oracle's time order equals its identity order, so the assertion above "
        "would pass against ORDER BY version_uid DESC"
    )

    runs = ok(get(listing_router, f"/versions/{catalogue.run_version_uid}/runs?limit=200"))
    expected_runs = catalogue.newest_first(
        "SELECT run_id FROM audit_run WHERE version_uid = :v "
        "ORDER BY created_at DESC, run_id DESC",
        {"v": catalogue.run_version_uid},
        "run_id",
    )
    assert uids(runs, "run_id") == expected_runs
    assert expected_runs != sorted(expected_runs, reverse=True)


@pytest.mark.parametrize("limit", [1, 2])
def test_the_walk_returns_every_row_exactly_once(
    listing_router: Surface, catalogue: Catalogue, limit: int
) -> None:
    """The oracle is the single maximal call; the walk is the thing under test.

    A cursor that restarted the listing repeats a row here. A `limit` accepted and
    ignored returns everything on the first page and terminates with the right set --
    which is why the page *sizes* are asserted too.
    """
    for target, key in (
        (f"/projects/{catalogue.project_uid}/documents", "version_uid"),
        (f"/documents/{catalogue.versioned_document_uid}/versions", "version_uid"),
        (f"/versions/{catalogue.run_version_uid}/runs", "run_id"),
    ):
        whole = uids(ok(get(listing_router, f"{target}?limit=200")), key)
        walked = walk(listing_router, target, key, limit=limit)
        assert walked == whole, f"{target}: the walk and the single call disagree"
        assert len(walked) == len(set(walked)), f"{target}: a row came back twice"
        first = ok(get(listing_router, f"{target}?limit={limit}"))
        assert len(first["items"]) == min(limit, len(whole)), (
            f"{target}: limit={limit} returned {len(first['items'])} items"
        )


def test_a_cursor_that_is_not_one_of_ours_is_refused_and_not_an_empty_page(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    """Returning an empty page would silently restart the listing from the beginning,
    which reads to a caller as data loss."""
    for target in (
        f"/projects/{catalogue.project_uid}/documents",
        f"/documents/{catalogue.versioned_document_uid}/versions",
        f"/versions/{catalogue.run_version_uid}/runs",
    ):
        answer = get(listing_router, f"{target}?cursor=not-a-cursor")
        assert answer.status == 422, (target, answer.status, answer.body)
        body = json.loads(answer.body)
        assert body["error_code"] == "validation_failed", body
        assert body["details"]["field"] == "cursor", body


# ---------------------------------------------------------------------------
# An unknown parent is 404, never an empty page
# ---------------------------------------------------------------------------


def test_an_unknown_parent_is_not_found_and_never_an_empty_page(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    for target, aggregate in (
        (f"/projects/{ProjectUid.new()}/documents", "Project"),
        (f"/documents/{DocumentUid.new()}/versions", "Document"),
        (f"/versions/{VersionUid.new()}/runs", "DocumentVersion"),
    ):
        answer = get(listing_router, target)
        assert answer.status == 404, (target, answer.status, answer.body)
        body = json.loads(answer.body)
        assert body["error_code"] == "not_found", body
        assert body["retryable"] is False, body
        # Which aggregate was not found, and therefore *which* of the two reads the
        # listing makes failed. Three operations answering one undifferentiated 404
        # would leave a caller unable to tell an unknown project from an unknown
        # document, and the catalog already carries the key that says so.
        assert body["details"]["aggregate_type"] == aggregate, body


def test_a_parent_that_exists_and_holds_nothing_is_an_empty_page_and_not_a_404(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """The other half of the rule above. Without this, `404` for everything would pass."""
    page = ok(get(listing_router, f"/versions/{catalogue.other_version_uid}/runs"))
    assert page["items"] == []
    assert page["page"]["next_cursor"] is None

    bare = str(ProjectUid.new())
    session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:p, 'Пустой проект')"),
        {"p": bare},
    )
    session.flush()
    empty = ok(get(listing_router, f"/projects/{bare}/documents"))
    assert empty["items"] == []


# ---------------------------------------------------------------------------
# `D-21` — what the run cost, and where the figure comes from
# ---------------------------------------------------------------------------


def _model_call(
    session: Session,
    run_id: str,
    *,
    cost_micros: int | None,
    cost_basis: str,
) -> str:
    from auditmanager.shared.identity import ModelCallId

    model_call_id = str(ModelCallId.new())
    session.execute(
        text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
            "model_identity, provider_mode, request_sha256, response_sha256, "
            "cost_micros, cost_basis, status) "
            "VALUES (:m, :r, 'text_analysis', 'anthropic', 'model-x', 'recorded', "
            ":h, :h, :c, :b, 'succeeded')"
        ),
        {
            "m": model_call_id,
            "r": run_id,
            "h": hashlib.sha256(model_call_id.encode("utf-8")).hexdigest(),
            "c": cost_micros,
            "b": cost_basis,
        },
    )
    session.flush()
    return model_call_id


def test_a_run_that_made_no_provider_call_reports_no_cost_at_all(
    listing_router: Surface, catalogue: Catalogue
) -> None:
    """Absent, not zero. "It cost nothing" and "nothing was spent here" are different
    claims, and `D-3` is this programme's record of what inventing the flattering one
    costs."""
    body = ok(get(listing_router, f"/runs/{catalogue.runs[0]}"))
    assert "cost_micros" not in body, body
    assert "cost_basis" not in body, body
    assert "model_call_count" not in body, body


def test_a_run_whose_calls_were_free_reports_a_cost_of_zero(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """The other half of the rule above: without it, omitting the field always would
    pass. A replayed call really does cost nothing and really did happen."""
    run_id = catalogue.runs[0]
    _model_call(session, run_id, cost_micros=0, cost_basis="measured")
    body = ok(get(listing_router, f"/runs/{run_id}"))
    assert body["cost_micros"] == 0
    assert body["model_call_count"] == 1
    assert body["cost_basis"] == "measured"


def test_the_figure_is_the_sum_over_every_attempt_and_not_the_last_one(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """`D-15`'s span, made explicit on the wire.

    A run can make several model calls -- the executor retries under **one** meter, so a
    retry cannot buy a fresh ceiling (`OD-03`). The published figure spans all of them,
    and `model_call_count` is what lets a reader see that it did. An implementation that
    published the last call's cost passes every assertion but the first one here.
    """
    run_id = catalogue.runs[0]
    _model_call(session, run_id, cost_micros=12_500, cost_basis="measured")
    _model_call(session, run_id, cost_micros=26_000, cost_basis="measured")

    body = ok(get(listing_router, f"/runs/{run_id}"))
    assert body["cost_micros"] == 38_500, (
        "the published figure is not the sum over both attempts"
    )
    assert body["cost_micros"] != 26_000, "the last attempt's cost was published instead"
    assert body["model_call_count"] == 2
    assert body["cost_basis"] == "measured"


def test_one_estimated_attempt_makes_the_whole_figure_estimated(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """The rule `D-15` says `stage_result.metrics` does **not** follow.

    There, `cost_basis` describes the last response and `cost_usd` sums every attempt, so
    a run whose first attempt was estimated and whose second was measured publishes a sum
    over both wearing the word `measured`. This contract does not inherit that: the basis
    is an aggregate over the calls the figure spans, and the order they were made in
    cannot change it -- which is what the second half of this test asserts.
    """
    run_id = catalogue.runs[0]
    _model_call(session, run_id, cost_micros=10_000, cost_basis="estimated")
    _model_call(session, run_id, cost_micros=20_000, cost_basis="measured")
    body = ok(get(listing_router, f"/runs/{run_id}"))
    assert body["cost_basis"] == "estimated", (
        "the last call's basis was published, which is the D-15 defect on the wire"
    )
    assert body["cost_micros"] == 30_000

    other = catalogue.runs[1]
    _model_call(session, other, cost_micros=20_000, cost_basis="measured")
    _model_call(session, other, cost_micros=10_000, cost_basis="estimated")
    reversed_order = ok(get(listing_router, f"/runs/{other}"))
    assert reversed_order["cost_basis"] == "estimated"
    assert reversed_order["cost_micros"] == 30_000


def test_a_call_with_no_recorded_cost_cannot_leave_the_total_called_measured(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """`model_call.cost_micros` is nullable, and `sum` skips a NULL silently.

    Without this rule the run below publishes `10000` -- a short total -- with the word
    `measured` attached to it, which is worse than publishing nothing.
    """
    run_id = catalogue.runs[0]
    _model_call(session, run_id, cost_micros=10_000, cost_basis="measured")
    _model_call(session, run_id, cost_micros=None, cost_basis="measured")
    body = ok(get(listing_router, f"/runs/{run_id}"))
    assert body["cost_basis"] == "estimated", body
    assert body["model_call_count"] == 2, "the unpriced call was not counted"
    assert body["cost_micros"] == 10_000


def test_another_runs_cost_never_reaches_this_run(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """A sum with a forgotten `WHERE run_id` reads as a plausible larger number."""
    mine, theirs = catalogue.runs[0], catalogue.other_run
    _model_call(session, mine, cost_micros=7_000, cost_basis="measured")
    _model_call(session, theirs, cost_micros=900_000, cost_basis="measured")
    body = ok(get(listing_router, f"/runs/{mine}"))
    assert body["cost_micros"] == 7_000, body
    assert body["model_call_count"] == 1


def test_the_cost_a_listing_shows_is_the_cost_the_run_shows(
    listing_router: Surface, catalogue: Catalogue, session: Session
) -> None:
    """`PA-01` criterion 4 asks for cost *visible*, and a screen reaches a run either way."""
    run_id = catalogue.runs[0]
    _model_call(session, run_id, cost_micros=38_500, cost_basis="measured")
    page = ok(get(listing_router, f"/versions/{catalogue.run_version_uid}/runs?limit=200"))
    listed = {item["run_id"]: item for item in page["items"]}[run_id]
    assert listed["cost_micros"] == 38_500
    assert listed == ok(get(listing_router, f"/runs/{run_id}"))
