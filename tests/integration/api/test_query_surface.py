"""The four declared query parameters, against the adapters the application ships.

``contracts/api/v1/openapi.json`` declares ``cursor``, ``limit``, ``category`` and
``verdict``. ``src/auditmanager/api/README.md`` reported, as gap 5, that no query surface
accepted any of them. A caller that supplies a filter and has it ignored is worse off than
one whose filter is refused: the refusal is visible, and the silent pass is a page the
reviewer believes was filtered.

Every test here is written so that **a surface ignoring the parameter fails it**. That is
not automatic, and this suite has already paid for assuming it was:

* the category filter was asserted through ``DatabaseFindingAdapter``, a fixture that
  filters in the test file. It stayed green while the shipped ``FindingAdapter`` took
  ``**_`` and dropped both filters. So everything below runs on ``shipped_router``;
* a project-order assertion over rows created in one transaction asserts nothing, because
  ``project.created_at`` defaults to ``now()`` and ``now()`` is the *transaction*
  timestamp -- every project created inside the fixture's transaction carries the same
  value to the microsecond. The ordering fixture here therefore stamps distinct
  ``created_at`` values **whose order disagrees with the ``project_uid`` order**, and
  asserts that disagreement before asserting anything about the listing. A listing that
  ordered by identity instead of by time now produces a different sequence, which is the
  only reason the ordering assertion means something.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Any, Iterator, Mapping, Sequence

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.api.routers import Router, dispatch
from auditmanager.api.routers.http import Request, Response
from auditmanager.api.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT
from auditmanager.api.schemas.findings import FINDING_CATEGORIES, VERDICTS
from auditmanager.findings import TextLayer

from .conftest import (
    PAGE_ONE,
    PAGE_TWO,
    REPOSITORY_ROOT,
    PublishedRun,
    _text_layer_artifact,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ok(response: Response) -> dict[str, Any]:
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


def json_headers(key: str) -> dict[str, str]:
    return {"Idempotency-Key": key, "Content-Type": "application/json"}


def uids(page: Mapping[str, Any], field: str = "finding_uid") -> list[str]:
    return [item[field] for item in page["items"]]


def get(router: Router, target: str) -> Response:
    return dispatch(router, Request.build("GET", target))


def decode(cursor: str) -> Any:
    return json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))


# ---------------------------------------------------------------------------
# A project listing whose time order disagrees with its identity order
# ---------------------------------------------------------------------------


class Ladder:
    """Six projects whose ``created_at`` order is a permutation of their creation order.

    ``project_uid`` is a ULID, so creating six projects in a loop gives six identities in
    ascending order. If ``created_at`` also ascended with creation, then "newest first"
    and "highest identity first" would be the same sequence and an assertion could not
    tell them apart -- and ``ORDER BY created_at DESC, project_uid DESC`` would be
    indistinguishable from ``ORDER BY project_uid DESC``.

    So the stamps below are deliberately shuffled against creation order. Every
    ``created_at`` is in the future, which keeps these six strictly newer than any row a
    previous run committed, so they occupy the head of the global listing.
    """

    #: Seconds from now, in creation order. Newest-first is therefore
    #: index 2, 0, 4, 3, 5, 1 -- nothing like the identity order 5, 4, 3, 2, 1, 0.
    OFFSETS = (40, 10, 60, 30, 50, 20)

    def __init__(self, router: Router, session: Session) -> None:
        self.router = router
        self.session = session
        self.created: list[str] = []
        for index, offset in enumerate(self.OFFSETS):
            self.created.append(self._create(f"Лестница {index}"))
            self.session.execute(
                text(
                    "UPDATE project SET created_at = now() + make_interval(secs => :s) "
                    "WHERE project_uid = :p"
                ),
                {"s": float(offset), "p": self.created[-1]},
            )
        self.session.flush()

    def _create(self, name: str) -> str:
        body = json.dumps({"name": name}).encode("utf-8")
        created = ok(
            dispatch(
                self.router,
                Request.build(
                    "POST",
                    "/projects",
                    headers=json_headers(f"ladder-{uuid.uuid4().hex[:16]}"),
                    body=body,
                ),
            )
        )
        return created["project_uid"]

    def insert_at_the_head(self) -> str:
        """One more project, newer than all six. Used to disturb a live cursor."""
        created = self._create("Лестница — вставка")
        self.session.execute(
            text(
                "UPDATE project SET created_at = now() + make_interval(secs => 600) "
                "WHERE project_uid = :p"
            ),
            {"p": created},
        )
        self.session.flush()
        return created

    @property
    def newest_first(self) -> list[str]:
        order = sorted(range(len(self.OFFSETS)), key=lambda i: -self.OFFSETS[i])
        return [self.created[i] for i in order]

    @property
    def identity_first(self) -> list[str]:
        return sorted(self.created, reverse=True)


@pytest.fixture
def ladder(shipped_router: Router, session: Session) -> Ladder:
    built = Ladder(shipped_router, session)
    # The fixture must discriminate before any assertion leans on it. Six distinct
    # stamps, and a time order that is not the identity order: without both, every
    # ordering test below would pass against `ORDER BY project_uid DESC`.
    stamps = (
        session.execute(
            text("SELECT created_at FROM project WHERE project_uid = ANY(:p)"),
            {"p": built.created},
        )
        .scalars()
        .all()
    )
    assert len(set(stamps)) == len(built.created), (
        "the six projects share a created_at, so an ordering assertion over them would "
        "be an assertion about the tiebreaker: `now()` is the transaction timestamp"
    )
    assert built.newest_first != built.identity_first, (
        "time order and identity order agree, so this fixture cannot tell "
        "`ORDER BY created_at DESC` from `ORDER BY project_uid DESC`"
    )
    return built


def head(page: Mapping[str, Any], ladder: Ladder) -> list[str]:
    """The ladder's own projects, in the order the listing returned them."""
    mine = set(ladder.created)
    return [p for p in uids(page, "project_uid") if p in mine]


# ---------------------------------------------------------------------------
# listProjects: order, limit, cursor
# ---------------------------------------------------------------------------


def test_the_listing_is_newest_first_and_not_highest_identity_first(
    shipped_router: Router, ladder: Ladder
) -> None:
    """`listProjects` declares "newest first" and `Ladder` makes that a real claim."""
    page = ok(get(shipped_router, f"/projects?limit={len(ladder.created)}"))

    assert head(page, ladder) == ladder.newest_first, (
        "the listing is not in created_at DESC order; identity order would have been "
        f"{ladder.identity_first}"
    )
    assert head(page, ladder) != ladder.identity_first
    assert head(page, ladder) != list(reversed(ladder.newest_first))


def test_limit_bounds_the_page_and_the_listing_is_longer_than_the_page(
    shipped_router: Router, ladder: Ladder
) -> None:
    """A surface ignoring `limit` returns everything, so the page must be shorter."""
    whole = ok(get(shipped_router, "/projects?limit=200"))
    assert len(whole["items"]) > 2, "nothing to bound; the listing is already short"

    page = ok(get(shipped_router, "/projects?limit=2"))
    assert len(page["items"]) == 2, "limit did not bound the page"
    assert page["page"]["next_cursor"] is not None, "a bounded page reported no next page"
    assert uids(page, "project_uid") == uids(whole, "project_uid")[:2]


def test_the_cursor_walks_the_whole_listing_without_losing_or_repeating(
    shipped_router: Router, ladder: Ladder
) -> None:
    collected: list[str] = []
    cursor: str | None = None
    for _ in range(200):
        target = "/projects?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = ok(get(shipped_router, target))
        collected.extend(uids(page, "project_uid"))
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            break
    assert cursor is None, "the listing never reported a last page"

    whole = ok(get(shipped_router, "/projects?limit=200"))
    assert collected == uids(whole, "project_uid")
    assert len(collected) == len(set(collected)), "a project appeared on two pages"
    assert set(ladder.created) <= set(collected)


def test_the_cursor_is_stable_across_an_insert_at_the_head(
    shipped_router: Router, ladder: Ladder
) -> None:
    """The claim that separates a real cursor from an offset.

    Page one is taken, then a project newer than everything is created, so the whole
    listing shifts down by one. A cursor carrying an offset resumes at position two of a
    list that has a new element at position zero and re-serves the second project. A
    cursor carrying the last key emitted resumes after that key, whatever moved.

    Both readings are spelled out in the assertion, because "the page is right" is not
    a claim anyone can check against a defect they cannot see.
    """
    first = ok(get(shipped_router, "/projects?limit=2"))
    assert uids(first, "project_uid") == ladder.newest_first[:2]
    cursor = first["page"]["next_cursor"]
    assert cursor

    inserted = ladder.insert_at_the_head()
    shifted = ok(get(shipped_router, "/projects?limit=3"))
    assert uids(shifted, "project_uid")[0] == inserted, (
        "the insert did not land at the head, so this test disturbs nothing"
    )

    resumed = ok(get(shipped_router, f"/projects?limit=2&cursor={cursor}"))
    by_key = ladder.newest_first[2:4]
    by_offset = [inserted, *ladder.newest_first][2:4]
    assert by_key != by_offset, "the insert did not shift the window; nothing is proved"
    assert uids(resumed, "project_uid") == by_key, (
        "the cursor resumed by position, not by key: an offset cursor would have "
        f"returned {by_offset}"
    )
    assert ladder.newest_first[1] not in uids(resumed, "project_uid"), (
        "the project already served on page one came back on page two"
    )


def test_the_cursor_carries_the_emitted_key_and_nothing_else(
    shipped_router: Router, ladder: Ladder, session: Session
) -> None:
    """Opaque means it carries no address a caller could compute with.

    `project` has no serial column, so the leak to look for is a *position*: a page
    index, a row offset, a count. The token is compared against the page it continues --
    every part of it must already be in that body -- and then checked for anything that
    reads as a number.
    """
    page = ok(get(shipped_router, "/projects?limit=3"))
    cursor = page["page"]["next_cursor"]
    assert cursor

    decoded = decode(cursor)
    assert isinstance(decoded, list) and all(isinstance(part, str) for part in decoded)
    assert decoded == [page["items"][-1]["project_uid"]], (
        f"the token carries something other than the last emitted key: {decoded}"
    )
    body = json.dumps(page, ensure_ascii=False)
    for part in decoded:
        assert part in body, f"the token carries {part!r}, which the page never returned"
        assert not part.lstrip("-").isdigit(), f"the token carries a bare number: {part!r}"

    # And a position really exists to have been leaked: the page starts three rows into
    # a longer listing, so "3" and "2" are values an offset cursor would have carried.
    whole = ok(get(shipped_router, "/projects?limit=200"))
    assert len(whole["items"]) > 3
    assert "3" not in decoded and 3 not in decoded


@pytest.mark.parametrize("bad", ["0", "201", "-1", "abc", "1.5", ""])
def test_a_limit_outside_the_frozen_bounds_is_refused(
    shipped_router: Router, ladder: Ladder, bad: str
) -> None:
    response = get(shipped_router, f"/projects?limit={bad}")
    if bad == "":
        # An empty value is the absent value, and the frozen default applies.
        assert response.status == 200
        assert len(json.loads(response.body)["items"]) <= DEFAULT_LIMIT
        return
    assert response.status == 422, (bad, response.body)
    assert json.loads(response.body)["error_code"] == "validation_failed"


def test_a_forged_project_cursor_is_refused_rather_than_restarting_the_listing(
    shipped_router: Router, ladder: Ladder
) -> None:
    """Silently restarting at the top reads to a caller as data loss, not as an error."""
    for forged in ("not-a-token", base64.urlsafe_b64encode(b'{"offset": 2}').decode()):
        response = get(shipped_router, f"/projects?cursor={forged}")
        assert response.status == 422, (forged, response.body)
        assert json.loads(response.body)["error_code"] == "validation_failed"


# ---------------------------------------------------------------------------
# listRunFindings: category and verdict
# ---------------------------------------------------------------------------

QUOTE_PAGE_ONE = "Степень огнестойкости здания — II."
QUOTE_PAGE_TWO = "Степень огнестойкости здания — III."
QUOTE_PLACEHOLDER = "Тип заполнения — уточнить."


def _observations(page_two_start: int) -> list[dict[str, Any]]:
    """Three grounded observations: two contradictions and one placeholder.

    Two of one category and one of the other, so a category filter has a *proper,
    non-empty* subset to return in both directions. One finding of each would let a
    surface that returned "the first finding" pass.
    """

    def evidence(page: int, quote: str) -> list[dict[str, Any]]:
        start = (
            PAGE_ONE.index(quote)
            if page == 1
            else page_two_start + PAGE_TWO.index(quote)
        )
        return [
            {
                "evidence_ordinal": 0,
                "page_number": page,
                "quote": quote,
                "char_start": start,
                "char_end": start + len(quote),
            }
        ]

    return [
        {
            "observation_ordinal": 0,
            "category": "internal_contradiction",
            "finding_text": "Степень огнестойкости на листе 1.",
            "recommendation_text": "Согласовать степень огнестойкости.",
            "evidence": evidence(1, QUOTE_PAGE_ONE),
        },
        {
            "observation_ordinal": 1,
            "category": "internal_contradiction",
            "finding_text": "Степень огнестойкости на листе 2.",
            "recommendation_text": "Согласовать степень огнестойкости.",
            "evidence": evidence(2, QUOTE_PAGE_TWO),
        },
        {
            "observation_ordinal": 2,
            "category": "explicit_placeholder",
            "finding_text": "Тип заполнения не определён.",
            "recommendation_text": "Указать тип заполнения.",
            "evidence": evidence(2, QUOTE_PLACEHOLDER),
        },
    ]


class MixedRun:
    """A published run carrying findings in both frozen categories."""

    def __init__(self, session: Session) -> None:
        self.run = PublishedRun(session, observations=_grounded_observations())
        published = self.run.publication.published
        assert len(published) == 3, f"the gate published {len(published)}, not three"
        self.findings = list(published)

    @property
    def run_id(self) -> str:
        return self.run.run_id


def _grounded_observations() -> list[dict[str, Any]]:
    """Build the payload against the same text layer ``PublishedRun`` will use."""
    layer = TextLayer.from_artifact(_text_layer_artifact())
    page_two = layer.page(2)
    assert page_two is not None
    return _observations(page_two.char_start)


@pytest.fixture
def mixed_run(session: Session) -> MixedRun:
    return MixedRun(session)


def _category_of(router: Router, run_id: str) -> dict[str, str]:
    page = ok(get(router, f"/runs/{run_id}/findings?limit=200"))
    return {item["finding_uid"]: item["category"] for item in page["items"]}


def test_the_category_filter_returns_a_proper_non_empty_subset(
    shipped_router: Router, mixed_run: MixedRun
) -> None:
    categories = _category_of(shipped_router, mixed_run.run_id)
    assert len(categories) == 3
    contradictions = {
        uid for uid, c in categories.items() if c == "internal_contradiction"
    }
    placeholders = {uid for uid, c in categories.items() if c == "explicit_placeholder"}
    # The discrimination this test rests on: both sides non-empty, neither the whole.
    assert len(contradictions) == 2 and len(placeholders) == 1

    for value, expected in (
        ("internal_contradiction", contradictions),
        ("explicit_placeholder", placeholders),
    ):
        page = ok(
            get(shipped_router, f"/runs/{mixed_run.run_id}/findings?category={value}")
        )
        assert set(uids(page)) == expected, (
            f"category={value} returned {uids(page)}; a surface ignoring the filter "
            f"would have returned all {len(categories)}"
        )
        assert len(page["items"]) < len(categories)


def test_the_verdict_filter_reads_the_projection_and_not_the_row(
    shipped_router: Router, mixed_run: MixedRun
) -> None:
    """Three findings, three different projected verdicts, one per filter value.

    `verdict` is not a column on the finding: it is the projection over the decision
    ledger. Moving two of the three and leaving one alone makes every one of the three
    values a proper, non-empty and *distinct* subset, so a surface that ignored the
    parameter, or read a stored column, fails all three.
    """
    ordered = sorted(mixed_run.findings, key=lambda f: f.finding_uid)
    rejected, accepted, pending = ordered

    for finding, event in ((rejected, "reject"), (accepted, "accept")):
        response = dispatch(
            shipped_router,
            Request.build(
                "POST",
                f"/findings/{finding.finding_uid}/decisions",
                headers=json_headers(f"verdict-{uuid.uuid4().hex[:16]}"),
                body=json.dumps(
                    {
                        "event_type": event,
                        "finding_observation_id": finding.finding_observation_id,
                    }
                ).encode("utf-8"),
            ),
        )
        assert response.status == 201, response.body

    everything = ok(get(shipped_router, f"/runs/{mixed_run.run_id}/findings?limit=200"))
    projected = {
        item["finding_uid"]: item["current_verdict"] for item in everything["items"]
    }
    assert len(set(projected.values())) == 3, (
        f"the three findings do not carry three different verdicts: {projected}; "
        "with fewer, a verdict filter cannot be told from a passthrough"
    )

    for value, expected in (
        ("rejected", rejected.finding_uid),
        ("accepted", accepted.finding_uid),
        ("pending", pending.finding_uid),
    ):
        page = ok(
            get(shipped_router, f"/runs/{mixed_run.run_id}/findings?verdict={value}")
        )
        assert uids(page) == [expected], (
            f"verdict={value} returned {uids(page)}, expected exactly {[expected]}"
        )


def test_the_two_filters_compose_and_compose_with_paging(
    shipped_router: Router, mixed_run: MixedRun
) -> None:
    categories = _category_of(shipped_router, mixed_run.run_id)
    contradictions = sorted(
        uid for uid, c in categories.items() if c == "internal_contradiction"
    )
    assert len(contradictions) == 2

    collected: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        target = f"/runs/{mixed_run.run_id}/findings?category=internal_contradiction&limit=1"
        if cursor:
            target += f"&cursor={cursor}"
        page = ok(get(shipped_router, target))
        assert len(page["items"]) == 1
        collected.extend(uids(page))
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            break

    assert cursor is None
    assert sorted(collected) == contradictions, (
        "paging inside a filtered listing lost or repeated a finding, or let an "
        f"explicit_placeholder through: {collected}"
    )

    both = ok(
        get(
            shipped_router,
            f"/runs/{mixed_run.run_id}/findings"
            "?category=explicit_placeholder&verdict=pending",
        )
    )
    assert len(both["items"]) == 1
    assert both["items"][0]["category"] == "explicit_placeholder"

    neither = ok(
        get(
            shipped_router,
            f"/runs/{mixed_run.run_id}/findings"
            "?category=explicit_placeholder&verdict=rejected",
        )
    )
    assert neither["items"] == [], "the two filters were not ANDed"


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("category", "invented"),
        ("category", "Internal_Contradiction"),
        ("category", "pending"),
        ("verdict", "maybe"),
        ("verdict", "Accepted"),
        ("verdict", "internal_contradiction"),
    ],
)
def test_a_value_outside_the_frozen_vocabulary_is_refused_not_answered_empty(
    shipped_router: Router, mixed_run: MixedRun, parameter: str, value: str
) -> None:
    """An empty page answers a different question from the one that was asked.

    "This run has no findings of that kind" and "that kind does not exist" are not the
    same answer, and a reviewer cannot tell them apart from an empty list. Note the
    cross-vocabulary cases: a `verdict` value offered as a `category` must be refused
    too, or the two enums are really one.
    """
    response = get(
        shipped_router, f"/runs/{mixed_run.run_id}/findings?{parameter}={value}"
    )
    assert response.status == 422, (parameter, value, response.body)
    body = json.loads(response.body)
    assert body["error_code"] == "validation_failed"
    assert body["details"]["field"] == parameter
    assert value not in json.dumps(body, ensure_ascii=False), (
        "the refusal echoed the caller's value back inside the envelope"
    )


def test_an_in_vocabulary_value_that_matches_nothing_is_an_empty_page_not_a_refusal(
    shipped_router: Router, mixed_run: MixedRun
) -> None:
    """The counterpart: 422 is about the vocabulary, never about emptiness."""
    page = ok(get(shipped_router, f"/runs/{mixed_run.run_id}/findings?verdict=accepted"))
    assert page["items"] == []
    assert page["page"]["next_cursor"] is None


# ---------------------------------------------------------------------------
# The declarations and the implementation cannot drift apart unnoticed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def contract() -> dict[str, Any]:
    path = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(document: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    while "$ref" in node:
        target: Any = document
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def _declared_query_parameters(document: Mapping[str, Any]) -> dict[str, set[str]]:
    declared: dict[str, set[str]] = {}
    for operations in document["paths"].values():
        for operation in operations.values():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            names = {
                _resolve(document, parameter)["name"]
                for parameter in operation.get("parameters", ())
                if _resolve(document, parameter)["in"] == "query"
            }
            if names:
                declared[operation["operationId"]] = names
    return declared


class _RecordingQuery(Mapping[str, Sequence[str]]):
    """A query mapping that remembers which names were looked up."""

    def __init__(self, values: Mapping[str, Sequence[str]]) -> None:
        self._values = dict(values)
        self.read: set[str] = set()

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        self.read.add(key)
        return self._values.get(key, default)

    def __getitem__(self, key: str) -> Sequence[str]:
        self.read.add(key)
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


def test_every_declared_query_parameter_is_read_by_the_router_that_declares_it(
    shipped_router: Router, mixed_run: MixedRun, ladder: Ladder, contract: dict[str, Any]
) -> None:
    """The guard against the defect this session exists for.

    The four parameters were declared in the frozen document, exposed by the generated
    client and read by nothing. A behavioural test per parameter catches that only for
    the parameters someone remembered to test; this catches it for every query parameter
    the document declares, including ones added later, by watching what the handler
    actually looks up.
    """
    declared = _declared_query_parameters(contract)
    assert declared, "no query parameters found in the frozen document"

    targets = {
        "listProjects": "/projects",
        "listRunFindings": f"/runs/{mixed_run.run_id}/findings",
        "listDecisionHistory": (
            f"/findings/{mixed_run.findings[0].finding_uid}/decisions"
        ),
    }
    assert set(targets) == set(declared), (
        "an operation declaring query parameters is not driven here: "
        f"{sorted(set(declared) ^ set(targets))}"
    )

    unread: dict[str, set[str]] = {}
    for operation_id, names in declared.items():
        recorder = _RecordingQuery({name: ["1"] for name in ()})
        request = Request(method="GET", path=targets[operation_id], query=recorder)
        response = dispatch(shipped_router, request)
        assert response.status == 200, (operation_id, response.body)
        missing = names - recorder.read
        if missing:
            unread[operation_id] = missing

    assert unread == {}, (
        "the router declares these query parameters and never even reads them, so a "
        f"caller supplying one has it silently ignored: {unread}"
    )


def test_the_filter_vocabularies_are_the_frozen_ones(contract: dict[str, Any]) -> None:
    """`category` and `verdict` take their values from the document, not from here."""
    schemas = contract["components"]["schemas"]
    assert set(schemas["FindingCategory"]["enum"]) == set(FINDING_CATEGORIES)
    assert set(schemas["Verdict"]["enum"]) == set(VERDICTS)
    assert len(FINDING_CATEGORIES) == 2 and len(VERDICTS) == 4


def test_the_limit_bounds_are_the_frozen_ones(contract: dict[str, Any]) -> None:
    schema = contract["components"]["parameters"]["Limit"]["schema"]
    assert (schema["minimum"], schema["maximum"], schema["default"]) == (
        MIN_LIMIT,
        MAX_LIMIT,
        DEFAULT_LIMIT,
    )


def test_the_committed_client_was_generated_from_this_contract() -> None:
    """The backend gate refuses a contract the committed client was not generated from.

    `web/tests/guards/frontend-lock.guard.test.ts` already checks this, in the frontend
    suite. It is repeated here because the contract and the router are changed in the
    same commit and the frontend suite is a separate command: an edit to
    `contracts/api/v1/openapi.json` that nobody regenerated from should redden the suite
    that sits next to it, not only the one somebody might run later.
    """
    contract_path = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
    lock = json.loads(
        (REPOSITORY_ROOT / "web" / "FRONTEND_LOCK.json").read_text(encoding="utf-8")
    )
    snapshot = REPOSITORY_ROOT / "web" / "openapi" / "openapi.json"

    digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert digest == lock["openapi"]["sha256"], (
        "the frozen document has moved since the client was generated from it. "
        "Regenerate: npm --prefix web run api:generate, and reseal web/FRONTEND_LOCK.json"
    )
    assert (
        hashlib.sha256(snapshot.read_bytes()).hexdigest()
        == lock["openapi"]["snapshot_sha256"]
    )
    assert snapshot.read_bytes() == contract_path.read_bytes(), (
        "the generator's snapshot is not the contract it claims to mirror"
    )


def test_the_generated_client_declares_the_query_parameters_the_contract_does(
    contract: dict[str, Any],
) -> None:
    """A parameter in the document that the client cannot send is a dead declaration."""
    source = (
        REPOSITORY_ROOT
        / "web"
        / "src"
        / "shared"
        / "api"
        / "generated"
        / "operations.gen.ts"
    ).read_text(encoding="utf-8")

    missing: list[str] = []
    for operation_id, names in _declared_query_parameters(contract).items():
        block = source.split(f"// {operation_id} - ", 1)
        assert len(block) == 2, f"{operation_id} is not in the generated client"
        # The header is `// ---` / `// <operationId> - <METHOD> <path>` / `// ---`, so
        # the operation's own section is what sits between the separator that closes
        # its header and the one that opens the next operation's.
        parts = block[1].split("// ------")
        assert len(parts) > 2, f"{operation_id} has no delimited section"
        section = parts[1]
        for name in names:
            if f"{name}?:" not in section and f"{name}:" not in section:
                missing.append(f"{operation_id}.{name}")
    assert missing == [], (
        f"the contract declares these query parameters and the client cannot send "
        f"them: {missing}"
    )


def test_this_suite_really_drives_the_shipped_adapters(shipped_router: Router) -> None:
    """The anti-vacuity of the fixture itself.

    Everything above is worth exactly as much as the claim that `shipped_router` is
    wired to `auditmanager.bootstrap.adapters` rather than to this package's fixtures.
    If someone re-points it at `DatabaseFindingAdapter` to make a failure go away, the
    filter tests keep passing and stop meaning anything. So the wiring is asserted.
    """
    from auditmanager.bootstrap import adapters as shipped

    modules = {
        route.operation_id: type(
            route.handler.__closure__[  # type: ignore[index]
                route.handler.__code__.co_freevars.index(name)
            ].cell_contents
        ).__module__
        for route, name in _bound_ports(shipped_router)
    }
    for operation_id in ("listProjects", "listRunFindings", "listDecisionHistory"):
        assert modules[operation_id] == shipped.__name__, (
            f"{operation_id} is not wired to the shipped adapter but to "
            f"{modules[operation_id]}"
        )


def _bound_ports(router: Router) -> list[tuple[Any, str]]:
    """Each list route, paired with the closure name holding its port."""
    wanted = {
        "listProjects": "projects",
        "listRunFindings": "findings",
        "listDecisionHistory": "decisions",
    }
    found = []
    for route in router.routes:
        name = wanted.get(route.operation_id)
        if name is None:
            continue
        assert name in (route.handler.__code__.co_freevars or ()), (
            f"{route.operation_id} does not close over {name!r}"
        )
        found.append((route, name))
    assert len(found) == len(wanted)
    return found
