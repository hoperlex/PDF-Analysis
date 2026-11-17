"""`UIP-S12-01` (contract 1.56.0): ``listDecisions`` and «Все» carry the execution status of the finding, and ``listDecisions`` filters by it.

Through the shipped adapters over a real database, like ``test_decision_journal.py``: the status is set by the operation that sets
it (``setFindingExecutionStatus``) and read back through the journal, so the join and the filter are what the HTTP surface serves.
Every assertion about counts is scoped to the project the test made (``project_uid``), because the journal is deployment-wide and the
database may hold other suites' rows (``OPERATING_CONSTRAINTS.md`` section 9).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from w13_api_driver import Request, Surface, dispatch

from .test_decision_journal import Decided, _walk
from .test_query_surface import MixedRun, get, json_headers, ok

JOURNAL = "/decisions"
STATUSES = ("taken_into_account", "amended", "declined", "agreed")


def _set_status(router: Surface, finding: Any, status: str | None) -> dict[str, Any]:
    answer = dispatch(
        router,
        Request.build(
            "PUT", f"/findings/{finding.finding_uid}/execution-status",
            headers=json_headers(f"s1201-{uuid.uuid4().hex[:16]}"), body=json.dumps({"status": status}).encode("utf-8"),
        ),
    )
    assert answer.status == 200, answer.body
    return json.loads(answer.body)


def _scope(decided: Decided) -> str:
    return f"{JOURNAL}?project_uid={decided.run.run.project_uid}"


def _of(records: list[dict[str, Any]], finding: Any) -> list[dict[str, Any]]:
    return [record for record in records if record["finding_uid"] == finding.finding_uid]


def _with_statuses(router: Surface, session: Session) -> tuple[Decided, dict[str, Any]]:
    """The fixture's findings, decided, then two of them given a status: the accepted one ``amended``; a second one ``agreed``.

    The pending finding is not accepted, so it cannot take a status (`R-151g`); the rejected one cannot either. A second
    accepted finding is made by accepting the pending one.
    """
    from .test_decision_journal import _append

    decided = Decided(router, MixedRun(session))
    _append(router, decided.pending, "accept")
    _set_status(router, decided.accepted, "amended")
    _set_status(router, decided.pending, "agreed")
    return decided, {"amended": decided.accepted, "agreed": decided.pending, "none": decided.rejected}


def test_a_record_carries_the_status_of_its_finding_and_the_one_without_carries_neither_key(
    shipped_router: Surface, session: Session
) -> None:
    decided, by = _with_statuses(shipped_router, session)
    records = _walk(shipped_router, _scope(decided), limit=50)
    detail = {name: json.loads(get(shipped_router, f"/findings/{finding.finding_uid}").body) for name, finding in by.items()}

    for name in ("amended", "agreed"):
        mine = _of(records, by[name])
        assert mine, name
        for record in mine:
            assert record["execution_status"] == name
            # The same instant `getFinding` reports for the same finding: one table, read twice.
            assert record["execution_status_at"] == detail[name]["execution_status_at"]
    assert len(_of(records, by["amended"])) == 2, "both events of the finding, the comment included, read its status"
    for record in _of(records, by["none"]):
        assert "execution_status" not in record and "execution_status_at" not in record, "absent, never null"


def test_the_filter_keeps_one_status_or_several_and_total_counts_the_group(
    shipped_router: Surface, session: Session
) -> None:
    decided, by = _with_statuses(shipped_router, session)
    scope = _scope(decided)
    whole = ok(get(shipped_router, f"{scope}&limit=200"))
    # accepted: comment + accept (2, `amended`); pending, then accepted (2, `agreed`); rejected (1, no status)
    assert whole["total"] == 5, whole["total"]

    def group(query: str) -> dict[str, Any]:
        return ok(get(shipped_router, f"{scope}&{query}&limit=200"))

    amended = group("execution_status=amended")
    assert amended["total"] == 2 and {r["finding_uid"] for r in amended["items"]} == {by["amended"].finding_uid}
    agreed = group("execution_status=agreed")
    assert agreed["total"] == 2 and {r["finding_uid"] for r in agreed["items"]} == {by["agreed"].finding_uid}
    for empty in ("declined", "taken_into_account"):
        nothing = group(f"execution_status={empty}")
        assert nothing["items"] == [] and nothing["total"] == 0, empty

    # Several statuses, in either spelling and either order, are one list: the union of the groups.
    union = {r["decision_id"] for r in amended["items"]} | {r["decision_id"] for r in agreed["items"]}
    for query in (
        "execution_status=amended,agreed", "execution_status=agreed,amended",
        "execution_status=amended&execution_status=agreed", "execution_status=agreed,amended,agreed,declined",
    ):
        several = group(query)
        assert {r["decision_id"] for r in several["items"]} == union and several["total"] == 4, query

    # The finding with no status is in none of the groups, whatever is asked.
    asked = group(f"execution_status={','.join(STATUSES)}")
    assert by["none"].finding_uid not in {r["finding_uid"] for r in asked["items"]} and asked["total"] == 4

    # A group's count is its `total`, read with one record: the chip number of the knowledge base.
    for status, expected in (("amended", 2), ("agreed", 2), ("declined", 0), ("taken_into_account", 0)):
        counted = ok(get(shipped_router, f"{scope}&execution_status={status}&limit=1"))
        assert (len(counted["items"]), counted["total"]) == (min(expected, 1), expected), status


def test_the_filter_composes_and_its_cursor_walks_the_filtered_listing_without_loss_or_repeat(
    shipped_router: Surface, session: Session
) -> None:
    decided, by = _with_statuses(shipped_router, session)
    scope = _scope(decided)
    filtered = f"{scope}&execution_status=amended,agreed"
    whole = ok(get(shipped_router, f"{filtered}&limit=200"))
    walked = _walk(shipped_router, filtered, limit=1)
    assert [r["decision_id"] for r in walked] == [r["decision_id"] for r in whole["items"]]
    assert len({r["decision_id"] for r in walked}) == len(walked) == whole["total"] == 4

    assert {r["finding_uid"] for r in ok(get(shipped_router, f"{filtered}&verdict=accepted&limit=200"))["items"]} == {
        by["amended"].finding_uid, by["agreed"].finding_uid
    }
    assert ok(get(shipped_router, f"{filtered}&verdict=rejected&limit=200"))["items"] == []
    category = json.loads(get(shipped_router, f"/findings/{by['agreed'].finding_uid}").body)["category"]
    narrowed = ok(get(shipped_router, f"{filtered}&category={category}&limit=200"))
    assert narrowed["items"] and {r["category"] for r in narrowed["items"]} == {category}
    assert [r["decision_id"] for r in narrowed["items"]] == [r["decision_id"] for r in whole["items"] if r["category"] == category]


def test_a_value_outside_the_vocabulary_is_refused_and_the_empty_string_is_the_absent_parameter(
    shipped_router: Surface, session: Session
) -> None:
    decided, _ = _with_statuses(shipped_router, session)
    scope = _scope(decided)
    for value in ("done", "Agreed", "agreed,", "agreed,done", "accepted"):
        answer = get(shipped_router, f"{scope}&execution_status={value}")
        assert answer.status == 422, (value, answer.body)
        body = json.loads(answer.body)
        assert body["error_code"] == "validation_failed"
        assert (body["details"]["field"], body["details"]["constraint"]) == ("execution_status", "enum")
    assert ok(get(shipped_router, f"{scope}&execution_status=&limit=200"))["total"] == ok(get(shipped_router, f"{scope}&limit=200"))["total"]


def test_the_knowledge_base_all_carries_the_status_of_a_finding_entry(shipped_router: Surface, session: Session) -> None:
    decided, by = _with_statuses(shipped_router, session)
    entries = _walk(shipped_router, f"/knowledge-base/entries?project_uid={decided.run.run.project_uid}", limit=50)
    findings = [entry["finding"] for entry in entries if entry["kind"] == "finding"]
    assert len(findings) == 5
    carried = {f["finding_uid"]: f.get("execution_status") for f in findings}
    assert carried == {
        by["amended"].finding_uid: "amended", by["agreed"].finding_uid: "agreed", by["none"].finding_uid: None,
    }
    assert all("execution_status_at" in f for f in findings if f.get("execution_status"))
    assert all("execution_status" not in f and "execution_status_at" not in f for f in findings if f["finding_uid"] == by["none"].finding_uid)


def test_a_status_is_not_a_decision_setting_and_clearing_it_moves_no_verdict_entry_or_count(
    shipped_router: Surface, session: Session
) -> None:
    """`R-151g`: the journal, its ``total`` and the verdict of every entry are the same before the status and after it."""
    from .test_decision_journal import _append

    decided = Decided(shipped_router, MixedRun(session))
    _append(shipped_router, decided.pending, "accept")
    scope = _scope(decided)

    def shape() -> list[tuple[Any, ...]]:
        page = ok(get(shipped_router, f"{scope}&limit=200"))
        return [(page["total"], len(page["items"]))] + [
            (r["decision_id"], r["verdict"], r["current_verdict"], r["decision_event_count"], r["event_type"]) for r in page["items"]
        ]

    before = shape()
    for finding, status in ((decided.accepted, "declined"), (decided.pending, "agreed"), (decided.accepted, None)):
        _set_status(shipped_router, finding, status)
        assert shape() == before, f"{status!r} on {finding.finding_uid} moved the journal"
    # And a status never lets a finding the expert did not accept into a group.
    refused = dispatch(
        shipped_router,
        Request.build(
            "PUT", f"/findings/{decided.rejected.finding_uid}/execution-status",
            headers=json_headers(f"s1201-{uuid.uuid4().hex[:16]}"), body=json.dumps({"status": "agreed"}).encode("utf-8"),
        ),
    )
    assert refused.status == 422, refused.body
    assert ok(get(shipped_router, f"{scope}&execution_status=agreed&limit=200"))["total"] == 2
