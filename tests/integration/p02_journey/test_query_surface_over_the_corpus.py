"""The journey view's query surface, over a populated table rather than three rows.

``W2-API`` proved its four declared query parameters against data that discriminates, and
its own cursor walk was repaired in this wave after it turned out to assert a property of
a small table. That repair is upstream of here. What nobody has checked is the surface a
*reader of a journey* uses: the findings of one run, filtered and paged, while the
database holds every other run this programme has ever executed against the same
instance.

Two vacuity traps are in scope and are attacked explicitly.

**A filter that is accepted and ignored.** ``FindingAdapter.list_run_findings`` once took
``**_`` and swallowed ``category`` and ``verdict`` entirely, so ``?category=...`` returned
the whole run and looked like it had worked. A test that asserts only "the filtered page
is non-empty and every item matches" passes against that adapter whenever the filter
value happens to be the only one present. So every filter test here asserts three things
together: the filtered set is a **strict** subset, it is **exactly** the members of the
unfiltered set that match, and a value legitimately absent from this run returns an empty
page rather than everything.

**A cursor that is accepted and ignored.** A surface that ignored ``cursor`` would return
page one forever. A walk that merely collected "enough" items would never notice. So the
walk here is bounded, asserts termination, asserts no item is seen twice, and asserts the
union is exactly the unfiltered set.

The population is real and is measured rather than assumed: the suite asserts that the
``finding_observation`` table holds many times this run's findings before it believes any
of the results below. The run under test is driven through the same public surfaces as
the rest of this tree, and every request goes through the real ``Router`` over the real
``FindingAdapter`` the composition root wires -- not the suite-local ``FindingPort``
double in ``tests/integration/api``, which cannot tell whether the shipped adapter agrees
with it.
Mutation evidence
-----------------
Every guard below was shown to fail, against a copy of ``src/`` outside the worktree,
proved to be the imported tree, and reverted afterwards.

==== ============================================================ ==========================
 id   mutation                                                     guards it reddened
==== ============================================================ ==========================
 M10  ``FindingAdapter.list_run_findings`` accepts ``category``     both filter guards,
      and ``verdict`` and drops them -- the defect that was there    filters-compose
      before
 M11  ``paginate`` ignores the cursor and always returns page one   one-per-page walk,
                                                                    cursor-stable
 M12  ``published_findings`` loses its ``run_id`` predicate         run-filter-narrows, and
                                                                    three others
 M14  an enum value outside the closed set is dropped instead of    outside-the-enum
      refused
 M15  the router filters **after** ``paginate`` rather than before  walk-under-a-filter
 M16  ``paginate``'s exhaustion test becomes ``>`` instead of       last-page-no-cursor
      ``>=``
 M19  ``_finding_sort_key`` returns ``(category,)`` -- a key that   cursor-key-total-order,
      is no longer a total order over the run                       one-per-page walk,
                                                                    cursor-stable
==== ============================================================ ==========================

``test_the_population_is_not_a_fixture_of_three_rows`` guards this module's premise rather
than any line of product code, so no source mutation can redden it. It was shown to fail
the only way it can be made to: the module was copied to the scratch tree with
``NEIGHBOUR_RUNS = 0`` and run against a freshly migrated, empty database
(``audit_w2qa_empty``). It failed there with "the run's findings are the whole table;
nothing was narrowed" -- ``assert 3 < 3`` -- while eight of this module's ten guards still
passed, which is also the evidence that nothing here depends on residue from a peer suite.

M15 is the one worth naming. Filtering after paging returns short pages, and at
``limit=1`` it drops a filtered-out row's page entirely; every other guard in this file
stays green under it, and only the walk under a filter goes red.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.repository import UserRepository as UserAccessRepository
from auditmanager.api.routers import build_router
from auditmanager.bootstrap.adapters import CredentialAdapter
from auditmanager.api.schemas.models import FindingCategory, Verdict
from auditmanager.bootstrap.adapters import (
    CsvExportAdapter,
    DecisionAdapter,
    FindingAdapter,
    RunAdapter,
)
from auditmanager.runs import InlineCarrier

#: How many extra runs this module publishes into the same tables before it asks the
#: query surface anything. Not a realistic corpus on its own -- the point is that it is
#: *more than one run's worth*, so a surface that ignored ``run_id`` or a cursor that
#: indexed the whole table instead of the filtered sequence cannot pass by accident. The
#: true population is whatever the instance has accumulated, and is asserted rather than
#: assumed in :func:`test_the_population_is_not_a_fixture_of_three_rows`.
NEIGHBOUR_RUNS = 6


def _credential_signer() -> Any:
    """This suite's signer, built from the same secret its credential is minted with."""
    from auditmanager.api.security import API_TOKEN_VARIABLE as _VARIABLE, build_signer

    signer = build_signer({_VARIABLE: _DEPLOYMENT_SECRET})
    assert signer is not None, "this suite's own secret derives a signing key"
    return signer


@pytest.fixture(scope="module")
def router(session_factory):
    """The real router over the shipped adapters."""
    return build_router(
        projects=None,
        documents=None,
        runs=RunAdapter(
            session_factory,
            blob_store=None,
            adapter=None,
            provider_config=None,
            provider_mode="recorded",
            analysis_profile_id="unused",
            prompt_bundle_id="unused",
            # `D-20`. Nothing here starts a run, so nothing is ever submitted. The
            # carrier is required rather than defaulted precisely so this reads as a
            # decision: an inline one would execute on this thread if anything did.
            carrier=InlineCarrier(),
        ),
        findings=FindingAdapter(session_factory),
        decisions=DecisionAdapter(session_factory),
        exports=CsvExportAdapter(session_factory),
        # `W39-REVOKE`. The seam reads the account's credential generation on every
        # guarded request, through the port the router carries, so a router built with none
        # refuses everything -- correctly, since an application that cannot tell a live
        # credential from a revoked one must fail closed. The shipped adapter is wired here
        # rather than a stub, because it is the object the composition root wires and it is
        # the one that answers for the account `static_token()` provisioned.
        credentials=CredentialAdapter(
            session_factory,
            users=UserAccessRepository(),
            signer=_credential_signer(),
        ),
    )


@pytest.fixture(scope="module")
def corpus(journey_harness, session_factory, blob_store, recorded_adapter, provider_config):
    """One run under test, and :data:`NEIGHBOUR_RUNS` more beside it in the same tables.

    The neighbours are real runs over real versions, not rows poked into ``finding``.
    They exist so that "the findings of run X" is a genuinely narrowing question: a
    surface that returned every published finding would be caught here and would not be
    caught by a suite whose database held one run.
    """
    h = journey_harness
    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("qs"))
        run_id = h.run_from_seed(
            session,
            seed,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            declared_provider_mode="recorded",
            run_key=h.new_key("qs-run"),
        )
        neighbours = [
            h.run_from_seed(
                session,
                seed,
                blob_store=blob_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
                declared_provider_mode="recorded",
                run_key=h.new_key(f"qs-neighbour-{index}"),
            )
            for index in range(NEIGHBOUR_RUNS)
        ]
        session.commit()
        yield {**seed, "run_id": run_id, "neighbours": neighbours}


def _get(router: Any, target: str) -> dict[str, Any]:
    response = _request(router, target)
    assert response.status_code == 200, (target, response.status_code, response.content)
    return json.loads(response.content)

#: `T-6`. The deployment secret this module configures, as a literal; the credential it
#: presents is minted from it below.
_DEPLOYMENT_SECRET = "p02-journey-static-token"

_STATIC_TOKEN_CACHE: str | None = None


def _static_token() -> str:
    """A credential this lane's API accepts, for an account this lane really has.

    **Lazy and memoised on purpose.** It opens a database connection, and doing that at
    import time would turn a lane whose services are not up into a *collection* error --
    which reads as a broken suite rather than as an absent lane.

    `W39-REVOKE`: a credential is refused unless the account it names exists and still
    accepts that credential's generation, so this suite's old habit of minting for an
    identity it invented is now presenting something the seam is correct to reject. The row
    is written, the epoch is read back out of it, and the credential is minted from what the
    database says. See ``tests/support/accounts.py``.
    """
    global _STATIC_TOKEN_CACHE
    if _STATIC_TOKEN_CACHE is None:
        from am_test_accounts import provisioned_credential

        _STATIC_TOKEN_CACHE = provisioned_credential(_DEPLOYMENT_SECRET, "p02-query-suite")
    return _STATIC_TOKEN_CACHE



class _Built:
    """Just enough of ``Application`` for ``create_asgi_app`` to take a router as given.

    Two attributes since `D-20`: the router, and the carrier the served application
    publishes as ``app.state.run_carrier``. Nothing in this module starts a run, so
    nothing is ever submitted to it -- it is a real carrier rather than ``None`` so that
    a test which did start one would get a finished run instead of an ``AttributeError``
    three frames from the cause.
    """

    __slots__ = ("router", "carrier")

    def __init__(self, router: Any) -> None:
        from auditmanager.runs import InlineCarrier

        self.router = router
        self.carrier = InlineCarrier()


def _client(router: Any) -> Any:
    """An ASGI client over the real application, wrapping the shipped-adapter router.

    Re-pointed by `W13-API`: ``Request.build`` plus ``dispatch`` are gone with
    ``routers/http.py``. This module's question is unchanged -- does the *shipped* adapter
    answer the same thing the suite adapters do -- and it is now asked over the transport
    that actually serves.
    """
    from starlette.testclient import TestClient

    from auditmanager.api.app import create_asgi_app
    from auditmanager.api.security import API_TOKEN_VARIABLE

    app = create_asgi_app(
        environ={API_TOKEN_VARIABLE: _DEPLOYMENT_SECRET}, application=_Built(router)
    )
    return TestClient(app, raise_server_exceptions=False)


def _request(router: Any, target: str) -> Any:
    return _client(router).get(
        target, headers={"Authorization": f"Bearer {_static_token()}"}
    )



def _ids(body: dict[str, Any]) -> list[str]:
    return [item["finding_uid"] for item in body["items"]]


def _page(body: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    return body["items"], body["page"]["next_cursor"]


@pytest.fixture(scope="module")
def verdicts(corpus, session_factory, router):
    """Split the run's findings across three verdicts, through the real ledger.

    Asserted rather than assumed afterwards: if the run ever publishes a different number
    of findings this fixture must fail loudly instead of quietly leaving every finding
    ``pending``, which would make every verdict filter below trivially satisfiable.
    """
    from auditmanager.decisions import record_decision
    from auditmanager.findings import published_findings

    with session_factory() as session:
        rows = published_findings(session, corpus["run_id"])
        assert len(rows) >= 3, (
            f"the run published {len(rows)} findings; this module needs at least three "
            "to split across verdicts, and a smaller run would make the filters vacuous"
        )
        record_decision(
            session,
            finding_uid=str(rows[0].finding_uid),
            finding_observation_id=str(rows[0].finding_observation_id),
            event_type="accept",
            comment="w2-qa: accepted for the verdict filter",
            author_label="reviewer-1",
        )
        record_decision(
            session,
            finding_uid=str(rows[1].finding_uid),
            finding_observation_id=str(rows[1].finding_observation_id),
            event_type="reject",
            comment="w2-qa: rejected for the verdict filter",
            author_label="reviewer-1",
        )
        session.commit()
        return {
            "accepted": str(rows[0].finding_uid),
            "rejected": str(rows[1].finding_uid),
            "pending": [str(r.finding_uid) for r in rows[2:]],
        }


# ---------------------------------------------------------------------------
# The population the rest of this file depends on
# ---------------------------------------------------------------------------


def test_the_population_is_not_a_fixture_of_three_rows(corpus, session):
    """Measure the table before trusting anything asserted against it.

    ``OPERATING_CONSTRAINTS.md`` §9: the database is long-lived and append-only, so a
    test that assumes a small table fails on its own against the accumulated population.
    The inverse is the trap here -- a query test that *passes* only because the table is
    small proves nothing. This asserts the table is genuinely larger than the answer, so
    a failure to narrow would be visible.
    """
    total = session.execute(text("SELECT count(*) FROM finding_observation")).scalar_one()
    mine = session.execute(
        text("SELECT count(*) FROM finding_observation WHERE run_id = :r"),
        {"r": corpus["run_id"]},
    ).scalar_one()
    runs = session.execute(
        text("SELECT count(DISTINCT run_id) FROM finding_observation")
    ).scalar_one()

    assert mine >= 3, mine
    assert runs > NEIGHBOUR_RUNS, (
        f"only {runs} runs have published findings; the neighbours this module drove are "
        "missing, so 'the findings of one run' is not a narrowing question here"
    )
    assert total >= mine * 4, (
        f"the table holds {total} observations against this run's {mine}; a query surface "
        "that ignored run_id could still look correct at that ratio"
    )


def test_the_run_filter_narrows_to_this_run_and_no_other(corpus, router, session):
    body = _get(router, f"/runs/{corpus['run_id']}/findings?limit=200")
    items, _ = _page(body)
    expected = {
        row[0]
        for row in session.execute(
            text("SELECT DISTINCT finding_uid FROM finding_observation WHERE run_id = :r"),
            {"r": corpus["run_id"]},
        )
    }
    assert {item["finding_uid"] for item in items} == expected
    assert len(items) < session.execute(
        text("SELECT count(*) FROM finding_observation")
    ).scalar_one(), "the run's findings are the whole table; nothing was narrowed"


# ---------------------------------------------------------------------------
# A filter narrows, and is not merely accepted
# ---------------------------------------------------------------------------


def test_the_verdict_filter_narrows_and_is_exactly_the_matching_subset(
    corpus, router, verdicts
):
    """Strict subset, exact membership, and an empty answer for an absent value.

    All three together. A surface that dropped the parameter passes "every item matches"
    whenever the run happens to hold one verdict, and passes "non-empty" always; only the
    strictness and the absent-value case can tell it apart from one that filters.
    """
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    by_verdict: dict[str, set[str]] = {}
    for item in everything:
        by_verdict.setdefault(item["current_verdict"], set()).add(item["finding_uid"])
    assert len(by_verdict) >= 2, (
        f"the run's findings all carry one verdict ({sorted(by_verdict)}); no verdict "
        "filter can discriminate on this data and the test would be vacuous"
    )

    for verdict in sorted(member.value for member in Verdict):
        items, _ = _page(
            _get(router, f"/runs/{corpus['run_id']}/findings?limit=200&verdict={verdict}")
        )
        got = {item["finding_uid"] for item in items}
        expected = by_verdict.get(verdict, set())
        assert got == expected, (
            f"?verdict={verdict} returned {sorted(got)}; the run's findings carrying that "
            f"verdict are {sorted(expected)}"
        )
        assert all(item["current_verdict"] == verdict for item in items)
        if expected:
            assert got < {item["finding_uid"] for item in everything}, (
                f"?verdict={verdict} did not narrow: it returned the whole run"
            )

    absent = next(v for v in sorted(member.value for member in Verdict) if v not in by_verdict)
    items, cursor = _page(
        _get(router, f"/runs/{corpus['run_id']}/findings?limit=200&verdict={absent}")
    )
    assert items == [], (
        f"?verdict={absent} is not present in this run and must return an empty page, "
        f"not {len(items)} findings"
    )
    assert cursor is None


def test_the_category_filter_narrows_and_is_exactly_the_matching_subset(corpus, router):
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    by_category: dict[str, set[str]] = {}
    for item in everything:
        by_category.setdefault(item["category"], set()).add(item["finding_uid"])

    present = sorted(by_category)
    assert present, "the run published nothing; there is no category to filter on"

    for category in sorted(member.value for member in FindingCategory):
        items, _ = _page(
            _get(router, f"/runs/{corpus['run_id']}/findings?limit=200&category={category}")
        )
        got = {item["finding_uid"] for item in items}
        assert got == by_category.get(category, set()), (
            f"?category={category} returned {sorted(got)}"
        )
        assert all(item["category"] == category for item in items)

    if len(present) == 1:
        absent = next(c for c in sorted(member.value for member in FindingCategory) if c != present[0])
        items, _ = _page(
            _get(router, f"/runs/{corpus['run_id']}/findings?limit=200&category={absent}")
        )
        assert items == [], (
            f"?category={absent} does not occur in this run and must return nothing; "
            f"returning {len(items)} findings means the parameter was accepted and dropped"
        )


def test_the_two_filters_compose(corpus, router, verdicts):
    """A run's findings filtered by category *and* verdict at once.

    Composition is where a filter applied to a copy of the wrong sequence shows up: each
    filter alone can look right while the pair returns their union rather than their
    intersection.
    """
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    accepted = [i for i in everything if i["finding_uid"] == verdicts["accepted"]]
    assert accepted, "the accepted finding is not in the run's list"
    category = accepted[0]["category"]

    target = (
        f"/runs/{corpus['run_id']}/findings?limit=200"
        f"&category={category}&verdict=accepted"
    )
    items, _ = _page(_get(router, target))
    expected = {
        i["finding_uid"]
        for i in everything
        if i["category"] == category and i["current_verdict"] == "accepted"
    }
    assert {i["finding_uid"] for i in items} == expected
    assert all(
        i["category"] == category and i["current_verdict"] == "accepted" for i in items
    )


def test_a_value_outside_the_enum_is_refused_rather_than_answered_empty(corpus, router):
    """``validation_failed``, not an empty page.

    An empty page reads as "this run has no findings of that kind", which is a different
    and wrong answer to "that kind does not exist" -- and it is the answer a surface that
    silently dropped an unrecognised value would give.

    The status comes off the frozen catalog rather than being spelled ``422`` here: the
    code is the contract, and hard-coding the number would let the two drift apart
    silently.
    """
    from auditmanager.shared.errors import ErrorCode

    expected_status = ErrorCode.VALIDATION_FAILED.http_status
    for parameter, value in (("category", "not_a_category"), ("verdict", "not_a_verdict")):
        response = _request(
            router, f"/runs/{corpus['run_id']}/findings?{parameter}={value}"
        )
        assert response.status_code == expected_status, (
            parameter,
            response.status_code,
            response.content,
        )
        body = json.loads(response.content)
        assert body["error_code"] == "validation_failed", body
        assert body["details"]["field"] == parameter, body
        assert body["retryable"] is False, body


# ---------------------------------------------------------------------------
# A cursor walk that a passthrough cannot survive
# ---------------------------------------------------------------------------


def _walk(router: Any, target: str, *, limit: int, bound: int = 200) -> list[str]:
    """Page through ``target`` and return the finding uids in order.

    Bounded, because the failure this exists to catch is a surface that ignores the
    cursor and returns page one forever. An unbounded walk against that surface hangs;
    a bounded one fails with the count it reached, which is a readable failure.
    """
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(bound):
        suffix = f"&cursor={cursor}" if cursor else ""
        body = _get(router, f"{target}&limit={limit}{suffix}")
        items, cursor = _page(body)
        seen.extend(item["finding_uid"] for item in items)
        if cursor is None:
            return seen
        assert items, "a page carrying a continuation cursor returned no items"
    raise AssertionError(
        f"the walk did not terminate within {bound} pages ({len(seen)} items collected); "
        "the cursor parameter is being accepted and ignored"
    )


def test_a_cursor_walk_at_one_per_page_covers_the_run_exactly_once(corpus, router):
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    expected = [item["finding_uid"] for item in everything]
    assert len(expected) >= 3, len(expected)

    walked = _walk(router, f"/runs/{corpus['run_id']}/findings?", limit=1)
    assert walked == expected, (
        "the one-per-page walk did not reproduce the single-page listing; "
        f"walk={walked} listing={expected}"
    )
    assert len(set(walked)) == len(walked) or len(set(expected)) != len(expected), (
        "an item was returned on two different pages"
    )


def test_a_cursor_walk_under_a_filter_covers_only_the_filtered_set(
    corpus, router, verdicts
):
    """The page boundary is cut out of the *filtered* sequence, not the full one.

    The failure this catches is real and specific: filtering after paging returns short
    pages and, at ``limit=1``, drops every filtered-out row's page entirely. A test that
    only walked the unfiltered listing would never see it.
    """
    target = f"/runs/{corpus['run_id']}/findings?verdict=pending"
    listed, _ = _page(_get(router, f"{target}&limit=200"))
    expected = [item["finding_uid"] for item in listed]
    assert expected, "no finding is pending; this walk would be vacuous"

    assert _walk(router, f"{target}&", limit=1) == expected


def test_the_cursor_is_stable_across_rows_inserted_elsewhere(
    corpus, journey_harness, session_factory, blob_store, recorded_adapter,
    provider_config, router,
):
    """A cursor taken before an insert still resumes at the right place afterwards.

    The insert is a whole new run, published into the same ``finding`` and
    ``finding_observation`` tables through the real execution path, because that is the
    insert this system actually performs. The cursor is opaque and encodes a sort key
    rather than an offset, so it must survive rows arriving anywhere else in the table --
    an offset-based cursor would skip or repeat items here, and would look perfectly
    correct on a database holding one run.
    """
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    expected = [item["finding_uid"] for item in everything]
    assert len(expected) >= 3

    first = _get(router, f"/runs/{corpus['run_id']}/findings?limit=1")
    page_one, cursor = _page(first)
    assert cursor is not None
    assert [i["finding_uid"] for i in page_one] == expected[:1]

    before = session_factory().execute(
        text("SELECT count(*) FROM finding_observation")
    ).scalar_one()
    h = journey_harness
    with session_factory() as session:
        h.run_from_seed(
            session,
            {"version_uid": corpus["version_uid"]},
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            declared_provider_mode="recorded",
            run_key=h.new_key("qs-insert"),
        )
        session.commit()
    after = session_factory().execute(
        text("SELECT count(*) FROM finding_observation")
    ).scalar_one()
    assert after > before, (
        "no rows were inserted, so this test proves nothing about stability across an "
        f"insert ({before} -> {after})"
    )

    resumed = _walk(router, f"/runs/{corpus['run_id']}/findings?cursor={cursor}&", limit=1)
    assert resumed == expected[1:], (
        "the cursor did not resume where it left off after rows were inserted elsewhere; "
        f"resumed={resumed} expected={expected[1:]}"
    )
    assert [i["finding_uid"] for i in page_one] + resumed == expected


def test_the_last_page_carries_no_continuation_cursor(corpus, router):
    everything, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))
    count = len(everything)
    _, exact = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit={count}"))
    assert exact is None, (
        "a page that exhausted the sequence offered a continuation cursor; a client "
        "following it would ask for a page that does not exist"
    )
    items, more = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit={count - 1}"))
    assert len(items) == count - 1
    assert more is not None, "a page that left an item behind offered no way to reach it"


def test_the_cursor_key_is_a_total_order_over_the_run_even_though_the_sequence_is_not_sorted_by_it(
    corpus, router, session
):
    """What actually makes the page walk safe, asserted for the first time.

    ``paginate`` **locates** the cursor's key in the sequence rather than comparing
    against it, so the sequence need not be sorted by that key -- but the key must be
    unique within the sequence, or a resumption lands on the wrong row and the walk
    silently skips or repeats. Nothing asserted that uniqueness, and it is the load-
    bearing property: the listing is ordered by ``finding_observation_id`` alone while the
    cursor key is ``(finding_uid, finding_observation_id)``.

    Recorded here because those two are **not** the same order, contrary to the docstring
    on ``_finding_sort_key``:

        "The same key family the CSV sorts on (P02_SEAMS.md section 6), so a page
        boundary and a CSV row order cannot disagree about what 'next' means."

    They do disagree. ``published_findings`` orders by ``o.finding_observation_id``; the
    CSV query orders by ``f.finding_uid COLLATE "C", o.finding_observation_id COLLATE
    "C"``; and ``finding_uid`` and ``finding_observation_id`` are independently allocated
    ULIDs, so within one millisecond their random tails disagree. Measured on this
    instance at 4182b44: 31 of 416 runs list their grounded observations in a different
    order through the API than through the CSV, with collation ruled out as the cause (0
    runs differ on collation alone). It is a presentation inconsistency and not a paging
    defect -- which is precisely why the uniqueness below is what needs guarding, and is
    reported rather than repaired. Owned by the ``api`` and ``findings`` trees.
    """
    listing, _ = _page(_get(router, f"/runs/{corpus['run_id']}/findings?limit=200"))

    # The cursors the surface itself emits, not a key this test re-derives: each is the
    # encoded sort key of one row, so their uniqueness is a property of
    # `_finding_sort_key` over this run's data rather than of a tuple assembled here.
    cursors: list[str] = []
    cursor: str | None = None
    for _ in range(len(listing) + 2):
        suffix = f"&cursor={cursor}" if cursor else ""
        _, cursor = _page(
            _get(router, f"/runs/{corpus['run_id']}/findings?limit=1{suffix}")
        )
        if cursor is None:
            break
        cursors.append(cursor)
    assert len(set(cursors)) == len(cursors), (
        f"the surface emitted the same cursor for two different rows: {cursors}. "
        "paginate locates the key rather than comparing it, so a repeated key resumes at "
        "the first match and the walk skips every row between them"
    )
    assert len(cursors) == len(listing) - 1, (
        f"a run of {len(listing)} findings paged one at a time emitted {len(cursors)} "
        "continuation cursors; it should emit one fewer than it has rows"
    )

    walked = _walk(router, f"/runs/{corpus['run_id']}/findings?", limit=1)
    assert walked == [item["finding_uid"] for item in listing], (
        "the walk and the listing disagree, which is what a non-unique cursor key causes"
    )
