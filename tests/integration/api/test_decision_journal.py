"""``listDecisions``: the ledger read across findings, through the shipped adapters.

`R-24`. Before this operation the only cross-cutting view of the decision ledger was a
client-side walk over every run and every finding, and the owner ruled against it.

**Every test here drives ``shipped_router``**, which wires
``auditmanager.bootstrap.adapters.DecisionAdapter``. `W13-API` recorded what the other
choice cost: a category filter asserted through a fixture that filtered *in the test file*
stayed green while the shipped adapter took ``**_`` and dropped both filters.

**Every assertion here is relative, never absolute.** The journal is deployment-wide and
``OPERATING_CONSTRAINTS.md`` §9 measured what that means on this host: the database is
long-lived and the schema is append-only, so rows from previous runs and previous days are
in it. A test asserting *"the journal is exactly these four events"* would pass on an empty
instance and fail on a populated one **on its own**, which §9 is explicit is a defect in
the test and not interference. So each test seeds its own events and asserts about those.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterator, Mapping

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from w13_api_driver import Answer, Request, Surface, dispatch
from auditmanager.shared.identity import DecisionId

from .test_query_surface import MixedRun, decode, get, json_headers, ok

JOURNAL = "/decisions"


def _append(
    router: Surface, finding: Any, event_type: str, comment: str | None = None
) -> dict[str, Any]:
    """One event through ``appendDecision``, the way a reviewer's screen produces one."""
    body: dict[str, Any] = {
        "event_type": event_type,
        "finding_observation_id": finding.finding_observation_id,
    }
    if comment is not None:
        body["comment"] = comment
    answer = dispatch(
        router,
        Request.build(
            "POST",
            f"/findings/{finding.finding_uid}/decisions",
            headers=json_headers(f"journal-{uuid.uuid4().hex[:16]}"),
            body=json.dumps(body).encode("utf-8"),
        ),
    )
    assert answer.status == 201, answer.body
    return json.loads(answer.body)


def _records(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(page["items"])


def _ids(page: Mapping[str, Any]) -> list[str]:
    return [item["decision_id"] for item in page["items"]]


def _walk(router: Surface, target: str, limit: int = 2) -> list[dict[str, Any]]:
    """Every record of a listing, one page at a time, following the cursor."""
    collected: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(200):  # a bound, so a cursor that never advances fails rather than hangs
        joiner = "&" if "?" in target else "?"
        suffix = "" if cursor is None else f"&cursor={cursor}"
        page = ok(get(router, f"{target}{joiner}limit={limit}{suffix}"))
        collected.extend(page["items"])
        cursor = page["page"]["next_cursor"]
        if cursor is None:
            return collected
    raise AssertionError("the cursor did not terminate")


class Decided:
    """Three findings of one run, decided differently, and nothing else touched.

    The shape is what makes the filters testable. One finding is accepted *and* commented,
    one is rejected, one is only commented and so stays ``pending``:

    * the accepted finding carries **two** events, one of which carries no verdict at all,
      which is the case that tells ``v.current_verdict`` from ``e.verdict``;
    * the three findings carry three different current verdicts, so every value of the
      filter is a proper, non-empty and distinct subset;
    * the run publishes both frozen categories, so the category filter has the same
      property.
    """

    def __init__(self, router: Surface, run: MixedRun) -> None:
        self.run = run
        ordered = sorted(run.findings, key=lambda f: f.finding_uid)
        self.accepted, self.rejected, self.pending = ordered
        self.events: list[str] = [
            _append(router, self.accepted, "comment", "к принятому")["event"]["decision_id"],
            _append(router, self.accepted, "accept")["event"]["decision_id"],
            _append(router, self.rejected, "reject")["event"]["decision_id"],
            _append(router, self.pending, "comment", "пока без вердикта")["event"][
                "decision_id"
            ],
        ]

    @property
    def mine(self) -> set[str]:
        return set(self.events)

    def of(self, finding: Any, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [r for r in records if r["finding_uid"] == finding.finding_uid]


@pytest.fixture
def decided(shipped_router: Surface, session: Session) -> Decided:
    built = Decided(shipped_router, MixedRun(session))
    verdicts = {
        item["finding_uid"]: item["current_verdict"]
        for item in ok(get(shipped_router, f"/runs/{built.run.run_id}/findings?limit=200"))[
            "items"
        ]
    }
    # The fixture discriminates before anything leans on it. Without three distinct
    # verdicts, a verdict filter cannot be told from a passthrough.
    assert len(set(verdicts.values())) == 3, verdicts
    assert len(built.mine) == 4, "four events, four identities"
    return built


# =====================================================================================
# What the journal carries
# =====================================================================================


def test_the_journal_carries_every_appended_event_across_findings(
    shipped_router: Surface, decided: Decided
) -> None:
    """The whole point: one call, and decisions on three different findings are in it.

    ``listDecisionHistory`` needs a ``finding_uid`` and answers for that finding only, so
    reaching these four events through it means three calls the caller can only make if it
    already knows the three identities.
    """
    records = _walk(shipped_router, JOURNAL)
    found = {r["decision_id"] for r in records}
    assert decided.mine <= found, f"the journal is missing {sorted(decided.mine - found)}"
    assert len({r["finding_uid"] for r in records if r["decision_id"] in decided.mine}) == 3


def test_a_record_carries_the_finding_context_it_was_recorded_against(
    shipped_router: Surface, decided: Decided
) -> None:
    """Every derived property, checked against the operation that already publishes it.

    Not against the fixture's own variables: the finding surface is the other side of the
    same database, so a projection that read the wrong column disagrees with it here.
    """
    detail = json.loads(
        get(shipped_router, f"/findings/{decided.accepted.finding_uid}").body
    )
    records = [
        r
        for r in _walk(shipped_router, JOURNAL)
        if r["finding_uid"] == decided.accepted.finding_uid
    ]
    assert len(records) == 2, "the accepted finding carries a comment and an accept"

    for record in records:
        assert record["project_uid"] == detail["project_uid"]
        assert record["run_id"] == detail["run_id"]
        assert record["category"] == detail["category"]
        assert record["finding_text"] == detail["observation"]["finding_text"]
        assert record["current_verdict"] == detail["current_verdict"] == "accepted"
        assert record["decision_event_count"] == detail["decision_event_count"] == 2
        assert record["author_label"] == "local-reviewer"

    by_type = {r["event_type"]: r for r in records}
    assert by_type["comment"]["verdict"] is None, (
        "a comment carries no verdict; a record that copied the finding's current verdict "
        "into the event's would make the two indistinguishable"
    )
    assert by_type["accept"]["verdict"] == "accepted"
    assert by_type["comment"]["comment"] == "к принятому"


def test_the_record_never_carries_the_servers_row_sequence(
    shipped_router: Surface, decided: Decided
) -> None:
    """`P02_SEAMS.md` §5.3: not in a field, and not inside a cursor."""
    page = ok(get(shipped_router, f"{JOURNAL}?limit=1"))
    assert "sequence_no" not in page["items"][0]
    key = decode(page["page"]["next_cursor"])
    assert len(key) == 2 and key[1].startswith("dec_"), key
    assert not any(str(part).isdigit() for part in key[:1] if str(part).isdigit() is True)


# =====================================================================================
# Order and paging
# =====================================================================================


def test_the_journal_is_newest_first(shipped_router: Surface, decided: Decided) -> None:
    """The reverse of ``listDecisionHistory``, deliberately.

    A journal is read from what just happened; a finding's history is read forward from
    the first thing said about it. The two orders are opposite and this asserts the one the
    contract declares for *this* operation, against the order the events were appended in.
    """
    records = _walk(shipped_router, JOURNAL)
    positions = {r["decision_id"]: index for index, r in enumerate(records)}
    mine = [positions[identity] for identity in decided.events]
    assert mine == sorted(mine, reverse=True), (
        f"appended in order {decided.events} and listed at positions {mine}; "
        "the journal is not newest first"
    )
    stamps = [r["recorded_at"] for r in records]
    assert stamps == sorted(stamps, reverse=True), "the page is not ordered by its own key"


def test_the_order_is_by_time_and_not_by_identity(
    shipped_router: Surface, decided: Decided, session: Session
) -> None:
    """The discrimination the fixture above cannot make, and why it is written this way.

    ``recorded_at`` defaults to ``clock_timestamp()`` and ``decision_id`` is a ULID, so
    events appended in sequence ascend in *both* keys and ``ORDER BY recorded_at DESC``
    cannot be told from ``ORDER BY decision_id DESC``. The ledger refuses ``UPDATE`` with
    ``AM002`` -- which is the property ``ledger.py`` exists to keep -- so the stamps cannot
    be shuffled afterwards the way `Ladder` shuffles ``project.created_at``.

    They are therefore chosen **at insert time**: two events whose time order is the
    opposite of their identity order. A listing keyed on the identity returns them the
    other way round and fails here.
    """
    older, newer = sorted(DecisionId.new().value for _ in range(2))
    finding = decided.pending
    for identity, offset in ((older, 400.0), (newer, 200.0)):
        session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, comment, author_label, "
                "recorded_at) VALUES (:d, :f, :o, 'comment', NULL, :c, 'local-reviewer', "
                "now() + make_interval(secs => :s))"
            ),
            {
                "d": identity,
                "f": finding.finding_uid,
                "o": finding.finding_observation_id,
                "c": "порядок",
                "s": offset,
            },
        )
    session.flush()

    # The identity order and the time order now disagree: `older` sorts first by identity
    # and last by time. Assert that, before asserting anything about the listing.
    assert older < newer
    records = _walk(shipped_router, JOURNAL)
    positions = {r["decision_id"]: index for index, r in enumerate(records)}
    assert positions[older] < positions[newer], (
        "the journal returned the lower identity later, so it is ordered by identity "
        "rather than by time"
    )


def test_the_cursor_walks_the_journal_without_losing_or_repeating_an_event(
    shipped_router: Surface, decided: Decided
) -> None:
    whole = ok(get(shipped_router, f"{JOURNAL}?limit=200"))
    walked = _walk(shipped_router, JOURNAL, limit=1)
    assert _ids(whole) == [r["decision_id"] for r in walked][: len(_ids(whole))]
    identities = [r["decision_id"] for r in walked]
    assert len(identities) == len(set(identities)), "an event was returned twice"
    assert decided.mine <= set(identities)


def test_a_cursor_this_api_did_not_issue_is_refused(shipped_router: Surface) -> None:
    """Refused, not restarted. An empty page would read to a caller as data loss."""
    answer = get(shipped_router, f"{JOURNAL}?cursor=not-a-continuation-token")
    assert answer.status == 422, answer.body
    assert json.loads(answer.body)["error_code"] == "validation_failed"


# =====================================================================================
# The two filters, which narrow the finding and not the event
# =====================================================================================


def test_the_verdict_filter_reads_the_projection_and_not_the_event(
    shipped_router: Surface, decided: Decided
) -> None:
    """The case that separates the two readings of ``verdict``.

    The accepted finding carries a **comment** event, whose own ``verdict`` is ``null``.
    ``?verdict=accepted`` must return it, because the parameter narrows the finding. A
    surface that filtered on the event's verdict would return the accept and drop the
    comment, and every other test here would stay green.
    """
    accepted = _walk(shipped_router, f"{JOURNAL}?verdict=accepted")
    identities = {r["decision_id"] for r in accepted}

    expected = set(decided.events[:2])  # the comment and the accept, same finding
    assert expected <= identities, (
        f"missing {sorted(expected - identities)}; the comment event on an accepted "
        "finding is the one a filter on the event's own verdict would drop"
    )
    assert {r["current_verdict"] for r in accepted} == {"accepted"}
    assert decided.events[2] not in identities, "a rejected finding's event leaked in"
    assert decided.events[3] not in identities, "a pending finding's event leaked in"

    # The control: unfiltered carries all four, so the filter is a proper subset and not
    # a listing that happens to be short.
    everything = {r["decision_id"] for r in _walk(shipped_router, JOURNAL)}
    assert decided.mine <= everything


def test_the_category_filter_returns_a_proper_non_empty_subset(
    shipped_router: Surface, decided: Decided
) -> None:
    categories = {
        item["finding_uid"]: item["category"]
        for item in ok(get(shipped_router, f"/runs/{decided.run.run_id}/findings?limit=200"))[
            "items"
        ]
    }
    assert len(set(categories.values())) == 2, categories

    seen: set[str] = set()
    for value in sorted(set(categories.values())):
        records = _walk(shipped_router, f"{JOURNAL}?category={value}")
        assert records, f"category={value} returned nothing at all"
        assert {r["category"] for r in records} == {value}, (
            "a surface ignoring the filter would have returned every category"
        )
        seen |= {r["decision_id"] for r in records} & decided.mine
    assert seen == decided.mine, (
        "the two categories do not partition the seeded events, so one of them was "
        f"filtered out of both pages: {sorted(decided.mine - seen)}"
    )


def test_the_two_filters_compose(shipped_router: Surface, decided: Decided) -> None:
    detail = json.loads(
        get(shipped_router, f"/findings/{decided.accepted.finding_uid}").body
    )
    target = f"{JOURNAL}?category={detail['category']}&verdict=accepted"
    records = _walk(shipped_router, target)
    assert set(decided.events[:2]) <= {r["decision_id"] for r in records}
    for record in records:
        assert record["category"] == detail["category"]
        assert record["current_verdict"] == "accepted"


def test_a_value_outside_the_frozen_vocabulary_is_refused_not_answered_empty(
    shipped_router: Surface,
) -> None:
    for parameter, value in (("category", "нет_такой"), ("verdict", "approved")):
        answer = get(shipped_router, f"{JOURNAL}?{parameter}={value}")
        assert answer.status == 422, (parameter, answer.body)
        assert json.loads(answer.body)["error_code"] == "validation_failed"


def test_an_in_vocabulary_value_that_matches_nothing_is_an_empty_page_not_a_refusal(
    shipped_router: Surface, decided: Decided
) -> None:
    """``needs_manual_review`` is in the closed union and has no PC-01 producer.

    No finding can carry it, so this is the one filter value that is certainly empty on
    any instance -- which is what makes it assertable on a deployment-wide listing.
    """
    page = ok(get(shipped_router, f"{JOURNAL}?verdict=needs_manual_review&limit=200"))
    assert page["items"] == []
    assert page["page"]["next_cursor"] is None


# =====================================================================================
# The seam
# =====================================================================================


def test_the_journal_refuses_a_caller_holding_no_credential(
    shipped_router: Surface,
) -> None:
    """`R-3`'s seam, on the first operation whose path addresses no parent.

    Worth its own case beside ``test_authorization.py``'s register: on every other listing
    a missing credential and an unknown parent both produce a refusal, so a 401 that had
    silently become a 404 would still look like a refusal. This path has no parent, so
    ``404`` here would mean the operation had stopped existing.
    """
    answer = dispatch(shipped_router, Request.build("GET", JOURNAL), credential=None)
    assert answer.status == 401, answer.body
    body = json.loads(answer.body)
    assert body["error_code"] == "authentication_required"
    assert body["retryable"] is False


def test_an_empty_journal_is_an_empty_page_and_never_not_found(
    shipped_router: Surface,
) -> None:
    """There is no identity in the path, so there is nothing that can be missing.

    Driven through the filter that certainly matches nothing rather than by emptying the
    database, which no test may do: the ledger refuses ``DELETE`` with ``AM002``, and that
    refusal is the property ``ledger.py`` exists to keep.
    """
    answer = get(shipped_router, f"{JOURNAL}?verdict=needs_manual_review")
    assert answer.status == 200, answer.body
    assert json.loads(answer.body) == {"items": [], "page": {"next_cursor": None}}
