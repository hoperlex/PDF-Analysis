"""`UIP-S03-02` (programme `UI-PARITY-R3`, owner ruling Г3-B) -- the order of ``listProjects``.

``listProjects`` takes the optional ``order``: ``published`` (the default, newest first, the order the operation always had) or
``name`` (by the first whole number written in the name ascending, then the names without a number, alphabetically with letter
case ignored, and the identity last). The first half of this module is the rule, on records and without a database; the second
is what the **served** operation answers over real rows, through the shipped ``ProjectAdapter``:

* the hand-written order of a set of names that exercises every clause of the rule (the number anywhere in the name, leading
  zeros, ten after nine, equal numbers, no number, case, a tie on the whole name decided by the identity);
* the cursor walks the listing in both orders without losing or repeating a row, under a live insert at the head of the order,
  and carries the last identity emitted and nothing else;
* ``published`` and the absent ``order`` are the same answer, byte for byte; an unknown order is ``422 validation_failed``;
* a cursor of the one order presented under the other is that listing's continuation, never a page from another listing.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import quote

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from w13_api_driver import Answer, Request, Surface, dispatch
from auditmanager.api.routers.projects import ProjectOrderParam
from auditmanager.documents.models import ProjectListingRecord
from auditmanager.documents.repository import PROJECT_ORDERS, order_project_listing
from auditmanager.shared.identity import ProjectUid

# ---------------------------------------------------------------------------
# The rule, on records
# ---------------------------------------------------------------------------

_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _records(*names: str) -> list[ProjectListingRecord]:
    """One record per name, ``created_at`` ascending with the arguments, identities in the same order."""
    uids = sorted(str(ProjectUid.new()) for _ in names)
    return [
        ProjectListingRecord(
            project_uid=ProjectUid(uid), name=name, created_at=_EPOCH + timedelta(minutes=index), document_count=0
        )
        for index, (uid, name) in enumerate(zip(uids, names))
    ]


def _names(order: str, *names: str) -> list[str]:
    return [record.name for record in order_project_listing(_records(*names), order)]


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        pytest.param(["10", "9", "007", "100"], ["007", "9", "10", "100"], id="numbers-compare-as-numbers"),
        pytest.param(["213-А", "5 Б", "5 А"], ["5 А", "5 Б", "213-А"], id="equal-numbers-by-the-name"),
        pytest.param(
            ["Школа 213", "213. Школа", "213-А"],
            ["213-А", "213. Школа", "Школа 213"],
            id="the-number-may-stand-anywhere-in-the-name",
        ),
        pytest.param(["Склад", "Гараж 3", "Ангар"], ["Гараж 3", "Ангар", "Склад"], id="no-number-after-every-number"),
        pytest.param(["склад", "Гараж", "Ангар", "ангар-2"], ["ангар-2", "Ангар", "Гараж", "склад"], id="letter-case-ignored"),
        pytest.param(
            ["Корпус 2, 213-А", "Корпус 10", "Корпус 3"],
            ["Корпус 2, 213-А", "Корпус 3", "Корпус 10"],
            id="only-the-first-number-counts",
        ),
        pytest.param(["  42 sp", "41", "43"], ["41", "  42 sp", "43"], id="leading-spaces"),
        pytest.param(
            ["99999999999999999999999", "99999999999999999999998", "1"],
            ["1", "99999999999999999999998", "99999999999999999999999"],
            id="a-number-longer-than-any-machine-integer",
        ),
        pytest.param(["٣ три", "2", "Z"], ["2", "Z", "٣ три"], id="only-ascii-digits-are-a-number"),
        pytest.param([], [], id="empty"),
    ],
)
def test_the_name_order_follows_the_rule(given: list[str], expected: list[str]) -> None:
    assert _names("name", *given) == expected


def test_a_tie_on_the_whole_name_is_decided_by_the_identity() -> None:
    """Two projects with the same name sort by ``project_uid`` whatever order they arrive in."""
    first, second = _records("Арбуз 4", "арбуз 4")
    assert str(first.project_uid) < str(second.project_uid)
    for arrival in ((first, second), (second, first)):
        assert [r.project_uid for r in order_project_listing(arrival, "name")] == [first.project_uid, second.project_uid]


def test_the_published_order_is_the_order_given() -> None:
    """``published`` is the repository statement's own order: it is neither sorted nor reversed here."""
    given = _records("Склад", "10", "9", "Ангар")
    assert order_project_listing(given, "published") == tuple(given)
    assert order_project_listing(list(reversed(given)), "published") == tuple(reversed(given))
    assert _names("name", "Склад", "10", "9", "Ангар") != [r.name for r in given], "the data set cannot tell the two orders apart"


def test_an_unknown_order_is_refused_not_answered_in_the_default_order() -> None:
    for bad in ("", "newest", "Name", "published ", "audit"):
        with pytest.raises(ValueError):
            order_project_listing(_records("a"), bad)


def test_the_router_declares_exactly_the_orders_the_boundary_knows() -> None:
    declared = [
        part
        for part in ProjectOrderParam.__metadata__  # type: ignore[attr-defined]
        if getattr(part, "json_schema", None) is not None
    ]
    assert len(declared) == 1
    assert declared[0].json_schema == {"type": "string", "enum": list(PROJECT_ORDERS), "default": "published"}


# ---------------------------------------------------------------------------
# The served operation, over real rows
# ---------------------------------------------------------------------------

#: The names the served tests create, in the order ``order=name`` has to return them. «Арбуз» and «арбуз» are one name once case is
#: ignored, so they are told apart by identity (asserted separately, because a ULID's order within one millisecond is random).
EXPECTED_NAME_ORDER = [
    "007 корпус",
    "7",
    "Склад 9",
    "Склад 10",
    "213-А",
    "213. Школа",
    "Школа 213",
    "без числа",
    "Бор",
    "ёлка",
]
TIED = ("Арбуз", "арбуз")


def get(router: Surface, target: str) -> Answer:
    return dispatch(router, Request.build("GET", target))


def ok(response: Answer) -> dict[str, Any]:
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


def uids(page: Mapping[str, Any]) -> list[str]:
    return [item["project_uid"] for item in page["items"]]


def decode(cursor: str) -> Any:
    return json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))


def _create(router: Surface, name: str) -> str:
    created = dispatch(
        router,
        Request.build(
            "POST",
            "/projects",
            headers={"Idempotency-Key": f"order-{uuid.uuid4().hex[:20]}", "Content-Type": "application/json"},
            body=json.dumps({"name": name}).encode("utf-8"),
        ),
    )
    assert created.status == 201, created.body
    return json.loads(created.body)["project_uid"]


def _walk(router: Surface, order: str, *, limit: int, disturb: Any = None) -> list[str]:
    """The whole listing by its own cursors. ``disturb`` is called once, with the cursor in hand, after the page at the middle."""
    collected: list[str] = []
    cursor: str | None = None
    disturbed = disturb is None
    for _ in range(10_000):
        target = f"/projects?order={order}&limit={limit}" + (f"&cursor={quote(cursor)}" if cursor else "")
        page = ok(get(router, target))
        assert len(page["items"]) <= limit
        collected += uids(page)
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            return collected
        if not disturbed and len(collected) >= 6:
            disturb()
            disturbed = True
    raise AssertionError("the listing did not end")


class Named:
    """The projects of ``EXPECTED_NAME_ORDER`` and the tied pair, created in a shuffled order inside the suite's transaction."""

    def __init__(self, router: Surface, session: Session) -> None:
        self.router = router
        self.session = session
        arrival = [
            "Школа 213", "ёлка", "7", "Склад 10", TIED[1], "без числа", "213. Школа", "Бор", "Склад 9", "213-А", TIED[0],
            "007 корпус",
        ]
        self.uid = {name: _create(router, name) for name in arrival}
        # Distinct creation instants in a shuffled order: `now()` is the transaction's clock, so the projects would share one
        # `created_at`, and the newest-first order would be decided by the identity alone.
        for index, name in enumerate(arrival):
            session.execute(
                text("UPDATE project SET created_at = now() + make_interval(secs => :s) WHERE project_uid = :p"),
                {"s": float(10 * (index + 1)), "p": self.uid[name]},
            )
        session.flush()

    @property
    def expected(self) -> list[str]:
        """The uids in ``order=name``. The tied pair is the first of the names without a number (casefold «арбуз» comes before
        «без числа», «бор» and «ёлка»), and its two members are told apart by identity."""
        tied = sorted(self.uid[name] for name in TIED)
        return [
            *(self.uid[name] for name in EXPECTED_NAME_ORDER[:7]),
            *tied,
            *(self.uid[name] for name in EXPECTED_NAME_ORDER[7:]),
        ]

    @property
    def newest_first(self) -> list[str]:
        order = [
            "Школа 213", "ёлка", "7", "Склад 10", TIED[1], "без числа", "213. Школа", "Бор", "Склад 9", "213-А", TIED[0],
            "007 корпус",
        ]
        return [self.uid[name] for name in reversed(order)]


@pytest.fixture
def named(shipped_router: Surface, session: Session) -> Named:
    built = Named(shipped_router, session)
    assert built.expected != built.newest_first, "the data set cannot tell the name order from the default"
    return built


def _mine(listing: list[str], named: Named) -> list[str]:
    owned = set(named.uid.values())
    return [uid for uid in listing if uid in owned]


def test_the_name_order_is_the_hand_written_one(shipped_router: Surface, named: Named) -> None:
    walked = _walk(shipped_router, "name", limit=200)
    assert _mine(walked, named) == named.expected


def test_the_published_order_is_newest_first_and_the_default(shipped_router: Surface, named: Named) -> None:
    explicit = get(shipped_router, "/projects?limit=200&order=published")
    default = get(shipped_router, "/projects?limit=200")
    assert explicit.status == default.status == 200
    assert explicit.body == default.body, "`order=published` is not the default answer"
    assert _mine(uids(json.loads(default.body)), named) == named.newest_first


def test_the_items_of_both_orders_have_the_same_shape(shipped_router: Surface, named: Named) -> None:
    by_name = ok(get(shipped_router, "/projects?limit=200&order=name"))
    default = ok(get(shipped_router, "/projects?limit=200"))
    assert {item["project_uid"]: item for item in by_name["items"]} == {item["project_uid"]: item for item in default["items"]}


@pytest.mark.parametrize("bad", ["newest", "audit", "Name", "NAME", "", "name,published", "1"])
def test_an_unknown_order_is_refused(shipped_router: Surface, named: Named, bad: str) -> None:
    response = get(shipped_router, f"/projects?order={quote(bad)}")
    assert response.status == 422, (bad, response.body)
    assert json.loads(response.body)["error_code"] == "validation_failed"


@pytest.mark.parametrize("order", ["published", "name"])
def test_the_cursor_walks_the_listing_exactly_once_under_a_live_insert(
    shipped_router: Surface, named: Named, session: Session, order: str
) -> None:
    """Nothing lost, nothing repeated, in either order -- while a project is created where it sorts first.

    The head of ``published`` is a project newer than all; the head of ``name`` is a project named «0 вставка» (the number 0 is
    below every number the other names carry). Each is created after the walk has passed its sixth row, so every row already
    behind the cursor is shifted by one under an offset cursor and re-served; a cursor that carries the last identity emitted
    resumes after it, whatever moved.
    """
    before = set(
        session.execute(text("SELECT project_uid FROM project")).scalars().all()
    )
    inserted: list[str] = []

    def disturb() -> None:
        uid = _create(shipped_router, "0 вставка")
        if order == "published":
            session.execute(
                text("UPDATE project SET created_at = now() + make_interval(secs => 100000) WHERE project_uid = :p"), {"p": uid}
            )
            session.flush()
        inserted.append(uid)

    walked = _walk(shipped_router, order, limit=3, disturb=disturb)

    assert len(inserted) == 1, "the walk was never disturbed"
    assert len(walked) == len(set(walked)), "a project appeared on two pages"
    assert set(walked) >= before, "the walk lost a project that existed before it began"
    assert set(walked) - before <= set(inserted), "the walk served a project nobody created"
    assert inserted[0] not in walked, "a project created above the resume point was served below it"
    # And it is the listing's own order: what the walk served, in the order it served it, is that order restricted to those rows.
    if order == "name":
        assert _mine(walked, named) == named.expected
    else:
        assert _mine(walked, named) == named.newest_first


@pytest.mark.parametrize("order", ["published", "name"])
def test_the_cursor_carries_the_last_identity_and_nothing_else(shipped_router: Surface, named: Named, order: str) -> None:
    page = ok(get(shipped_router, f"/projects?limit=3&order={order}"))
    cursor = page["page"]["next_cursor"]
    assert cursor
    assert decode(cursor) == [page["items"][-1]["project_uid"]], decode(cursor)


def test_a_cursor_of_one_order_under_the_other_is_that_listings_continuation(
    shipped_router: Surface, named: Named
) -> None:
    """Documented behaviour of the contract (as for ``listDocuments``): the cursor locates its row in the listing it is used with."""
    whole = _walk(shipped_router, "name", limit=200)
    published = ok(get(shipped_router, "/projects?limit=3"))
    cursor = published["page"]["next_cursor"]
    assert cursor
    after = uids(published)[-1]
    resumed = ok(get(shipped_router, f"/projects?order=name&limit=200&cursor={quote(cursor)}"))
    assert uids(resumed) == whole[whole.index(after) + 1 :][:200]


def test_the_unknown_cursor_of_the_name_order_is_still_refused_when_forged(shipped_router: Surface, named: Named) -> None:
    response = get(shipped_router, "/projects?order=name&cursor=not-a-token")
    assert response.status == 422, response.body
    assert json.loads(response.body)["error_code"] == "validation_failed"


def test_a_project_without_documents_is_listed_in_the_name_order_with_its_counters(
    shipped_router: Surface, named: Named
) -> None:
    """The order moves rows and changes none of them: every item keeps ``document_count`` and ``audit_counts``."""
    page = ok(get(shipped_router, "/projects?order=name&limit=200"))
    mine = [item for item in page["items"] if item["project_uid"] in set(named.uid.values())]
    assert len(mine) == len(named.uid)
    for item in mine:
        assert item["document_count"] == 0
        assert item["audit_counts"]["document_count"] == 0
