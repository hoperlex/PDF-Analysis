"""«График работ» on a real database (`UI-PARITY-P0P`, `R-152a`…`R-152h`).

Every read runs its SQL on the migrated schema; every command is keyed and appends events. The month's fact rule (a
document «Проверено экспертом» on the day of its last verdict) is executed here over a schema with no checked document;
a run with decided findings is the remaining part of `D-318`.

The month's decision counter (`UIP-S14-01`, «принято / отклонено») is executed over findings that really passed the grounding
gate and proposals of a real pass, whose decisions are written with their author and their time by plain SQL (the ledgers
refuse UPDATE, so the only way to place a decision on a day is to insert it there). The expectations are literals, worked out
from the histories listed in the tests, never from the statement under test.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.bootstrap.adapters import ScheduleAdapter
from auditmanager.dispatch.public import assign_work, get_assignment
from auditmanager.findings import TextLayer
from auditmanager.schedule.public import (
    read_reserve,
    read_schedule_month,
    schedule_assignments,
    set_absences,
    set_calendar_days,
    set_plans,
    set_settings,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, DecisionId
from tests.integration.decisions.conftest import (  # type: ignore[import-not-found]
    PublishedRun,
    _text_layer_artifact,
)
from tests.integration.documents.seeding import Seeder  # type: ignore[import-not-found]
from tests.integration.optimisation.pass_seeding import Scaffold  # type: ignore[import-not-found]

accounts = AccountRepository()
NOVEMBER = date(2026, 11, 1)


def _roles(session: Session, uid: str) -> frozenset[str]:
    return accounts.roles_of(session, uid)


def _refused(session: Session, code: ErrorCode, call: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(session, **kwargs)
    session.rollback()
    assert caught.value.code is code, (caught.value.code, caught.value.detail_fields)
    return caught.value


def _count(session: Session, table: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608 - a test's own literal


def test_a_month_reads_the_default_plan_the_week_and_every_active_expert(session: Session, cast: Any) -> None:
    month = read_schedule_month(session, month=NOVEMBER, viewer_uid=cast.admin, viewer_roles=_roles(session, cast.admin))
    assert (month.settings.default_monthly_plan, month.settings.time_zone) == (20, "UTC")
    assert len(month.days) == 30
    off = {day.day for day in month.days if day.day_off}
    assert date(2026, 11, 1) in off and date(2026, 11, 7) in off and date(2026, 11, 2) not in off
    uids = {engineer.user_uid for engineer in month.engineers}
    # Every active account holding `expert` -- the cast's three and the account the migrations seed with both roles --
    # and nobody else: not the administrator without `expert`, not the account with no role.
    active_experts = set(session.execute(text(
        "SELECT u.user_uid FROM app_user u JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'expert' "
        "WHERE u.archived_at IS NULL"
    )).scalars())
    assert {cast.expert, cast.other_expert, cast.admin_expert} <= uids
    assert uids == active_experts
    assert cast.admin not in uids and cast.nobody not in uids
    assert all(engineer.plan == 20 and engineer.plan_is_default and engineer.fact == 0 for engineer in month.engineers)

    own = read_schedule_month(session, month=NOVEMBER, viewer_uid=cast.expert, viewer_roles=_roles(session, cast.expert))
    assert [engineer.user_uid for engineer in own.engineers] == [cast.expert]
    _refused(session, ErrorCode.PERMISSION_DENIED, read_schedule_month, month=NOVEMBER, viewer_uid=cast.nobody,
             viewer_roles=_roles(session, cast.nobody))


def test_plans_days_absences_and_settings_are_keyed_events(session: Session, cast: Any) -> None:
    admin = _roles(session, cast.admin)
    set_plans(session, month=NOVEMBER, plans=[(cast.expert, 12)], actor_uid=cast.admin, actor_roles=admin,
              idempotency_key="plan-1")
    session.commit()
    set_plans(session, month=NOVEMBER, plans=[(cast.expert, 12)], actor_uid=cast.admin, actor_roles=admin,
              idempotency_key="plan-1")
    set_plans(session, month=NOVEMBER, plans=[(cast.expert, 12)], actor_uid=cast.admin, actor_roles=admin,
              idempotency_key="plan-2")
    session.commit()
    assert _count(session, "schedule_plan_event") == 1, "a replay and an unchanged plan record nothing"

    set_calendar_days(session, days=[(date(2026, 11, 4), "day_off"), (date(2026, 11, 14), "workday")],
                      actor_uid=cast.admin, actor_roles=admin, idempotency_key="days-1")
    set_absences(session, engineer_uid=cast.other_expert, days=[(date(2026, 11, 10), True)], actor_uid=cast.admin,
                 actor_roles=admin, idempotency_key="absent-1")
    set_settings(session, default_monthly_plan=15, time_zone="Europe/Moscow", actor_uid=cast.admin, actor_roles=admin,
                 idempotency_key="settings-1")
    session.commit()

    month = read_schedule_month(session, month=NOVEMBER, viewer_uid=cast.admin, viewer_roles=admin)
    by_uid = {engineer.user_uid: engineer for engineer in month.engineers}
    assert (by_uid[cast.expert].plan, by_uid[cast.expert].plan_is_default) == (12, False)
    assert (by_uid[cast.other_expert].plan, by_uid[cast.other_expert].plan_is_default) == (15, True)
    assert by_uid[cast.other_expert].absences == (date(2026, 11, 10),)
    days = {day.day: day for day in month.days}
    assert days[date(2026, 11, 4)].day_off and days[date(2026, 11, 4)].override == "day_off"
    assert not days[date(2026, 11, 14)].day_off and days[date(2026, 11, 14)].override == "workday"
    assert month.settings.time_zone == "Europe/Moscow"

    set_calendar_days(session, days=[(date(2026, 11, 4), "default")], actor_uid=cast.admin, actor_roles=admin,
                      idempotency_key="days-2")
    session.commit()
    again = read_schedule_month(session, month=NOVEMBER, viewer_uid=cast.admin, viewer_roles=admin)
    assert not {day.day: day for day in again.days}[date(2026, 11, 4)].day_off

    _refused(session, ErrorCode.VALIDATION_FAILED, set_plans, month=NOVEMBER, plans=[(cast.nobody, 3)],
             actor_uid=cast.admin, actor_roles=admin, idempotency_key="plan-3")
    _refused(session, ErrorCode.VALIDATION_FAILED, set_settings, default_monthly_plan=20, time_zone="Mars/Olympus",
             actor_uid=cast.admin, actor_roles=admin, idempotency_key="settings-2")
    _refused(session, ErrorCode.PERMISSION_DENIED, set_plans, month=NOVEMBER, plans=[(cast.expert, 3)],
             actor_uid=cast.expert, actor_roles=_roles(session, cast.expert), idempotency_key="plan-4")


def test_the_reserve_places_moves_and_reassigns_open_assignments(session: Session, cast: Any) -> None:
    admin = _roles(session, cast.admin)
    record = assign_work(session, actor_uid=cast.admin, actor_roles=admin, project_uid=cast.project,
                         document_uid=cast.document, assignee_user_uid=cast.expert, note=None)
    session.commit()
    uid = record.assignment_uid

    reserve = read_reserve(session, start=date(2026, 11, 2), days=14, viewer_uid=cast.admin, viewer_roles=admin)
    items = dict(reserve.engineers)[cast.expert]
    assert [(item.assignment_uid, item.planned_on, item.document_uid) for item in items] == [(uid, None, cast.document)]

    schedule_assignments(session, moves=[(uid, date(2026, 11, 5), None)], actor_uid=cast.admin, actor_roles=admin,
                         idempotency_key="move-1")
    session.commit()
    schedule_assignments(session, moves=[(uid, date(2026, 11, 5), None)], actor_uid=cast.admin, actor_roles=admin,
                         idempotency_key="move-2")
    session.commit()
    assert _count(session, "work_assignment_schedule_event") == 1, "an unchanged date records nothing"

    schedule_assignments(session, moves=[(uid, date(2026, 11, 6), cast.other_expert)], actor_uid=cast.admin,
                         actor_roles=admin, idempotency_key="move-3")
    session.commit()
    moved = read_reserve(session, start=date(2026, 11, 2), days=14, viewer_uid=cast.admin, viewer_roles=admin)
    assert dict(moved.engineers)[cast.expert] == ()
    [placed] = dict(moved.engineers)[cast.other_expert]
    assert placed.planned_on == date(2026, 11, 6)
    detail = get_assignment(session, assignment_uid=uid, viewer_uid=cast.admin, viewer_roles=admin)
    assert "reassigned" in repr(detail), "the move to another expert is a reassignment in «Диспетчер»"

    own = read_reserve(session, start=date(2026, 11, 2), days=14, viewer_uid=cast.expert,
                       viewer_roles=_roles(session, cast.expert))
    assert [engineer for engineer, _items in own.engineers] == [cast.expert]

    _refused(session, ErrorCode.NOT_FOUND, schedule_assignments,
             moves=[("asg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B", date(2026, 11, 5), None)], actor_uid=cast.admin,
             actor_roles=admin, idempotency_key="move-4")
    _refused(session, ErrorCode.PERMISSION_DENIED, schedule_assignments, moves=[(uid, None, None)],
             actor_uid=cast.expert, actor_roles=_roles(session, cast.expert), idempotency_key="move-5")


# --- the month's decision counter (`UIP-S14-01`) ----------------------------------------------------------------------------

_INSERT_EVENT = text(
    "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, "
    "author_label, author_user_uid, recorded_at, carried_from_decision_id) "
    "VALUES (:id, :finding, :observation, :event_type, :verdict, :comment, 'Эксперт', :author, CAST(:at AS timestamptz), :carried)"
)
_VERDICT_OF = {"accept": "accepted", "reject": "rejected", "revoke": "pending", "comment": None}
_INSERT_COMMAND = text(
    "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
    "VALUES (:c, 'decide_optimisation_proposal', :k, :f)"
)
_INSERT_PROPOSAL_DECISION = text(
    "INSERT INTO optimisation_proposal_decision (proposal_decision_id, optimisation_proposal_id, seq, verdict, comment, "
    "actor_user_uid, command_id, decided_at, carried_from_decision_id) "
    "VALUES (:d, :q, (SELECT coalesce(max(seq), 0) + 1 FROM optimisation_proposal_decision WHERE optimisation_proposal_id = :q), "
    ":v, :comment, :actor, :cmd, CAST(:at AS timestamptz), :carried)"
)


class _Findings:
    """Findings that really passed the grounding gate, two to a published run, handed out one at a time."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._layer = TextLayer.from_artifact(_text_layer_artifact())
        self._free: list[tuple[str, str]] = []

    def take(self) -> tuple[str, str]:
        if not self._free:
            run = PublishedRun(self._session, self._layer)
            self._free = [(item.finding_uid, item.finding_observation_id) for item in run.publication.published]
        return self._free.pop(0)

    def decide(self, finding: tuple[str, str], kind: str, author: str | None, at: str, *, carried_from: str | None = None) -> str:
        """Append one event to the finding's ledger at ``at`` (the ledger refuses UPDATE, so this is the only way to date it)."""
        decision_id = str(DecisionId.new())
        self._session.execute(_INSERT_EVENT, {
            "id": decision_id, "finding": finding[0], "observation": finding[1], "event_type": kind,
            "verdict": _VERDICT_OF[kind], "comment": "Принято к сведению." if kind == "comment" else None,
            "author": author, "at": at, "carried": carried_from,
        })
        return decision_id


class _Proposals:
    """Optimisation proposals of one real pass, the pass scaffolding being the dashboard suite's; decisions are placed by hand."""

    def __init__(self, session: Session, cast: Any, monkeypatch: pytest.MonkeyPatch, count: int) -> None:
        self._session = session
        # The scaffold's own expert is an account it creates by a login the cast already holds; the cast's stands in for it.
        monkeypatch.setattr(Seeder, "expert", property(lambda _self: cast.admin_expert))
        scaffold = Scaffold(session)
        version = scaffold.seed.version(cast.document, classified=("R", "AR"))  # a pass pins a classified version
        run = scaffold.run(cast.project, version)
        pass_id = scaffold.pass_(cast.project, cast.document, version, run, ((),) * count, started="2026-11-01T10:00:00+00",
                                 generator="gen-1")
        self._free = [str(row[0]) for row in session.execute(text(
            "SELECT optimisation_proposal_id FROM optimisation_proposal WHERE optimisation_pass_id = :p ORDER BY ordinal"
        ), {"p": pass_id})]

    def take(self) -> str:
        return self._free.pop(0)

    def decide(self, proposal: str, verdict: str, actor: str, at: str, *, carried_from: str | None = None) -> str:
        command = str(CommandId.new())
        digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
        self._session.execute(_INSERT_COMMAND, {"c": command, "k": command, "f": digest})
        decision_id = f"opd_{digest[:26].upper()}"
        self._session.execute(_INSERT_PROPOSAL_DECISION, {
            "d": decision_id, "q": proposal, "v": verdict, "comment": "Уточнить" if verdict == "revise" else None,
            "actor": actor, "cmd": command, "at": at, "carried": carried_from,
        })
        return decision_id


def _decisions(session: Session, admin: str, month: date) -> dict[str, tuple[int, int]]:
    """Every engineer's (accepted, rejected) of ``month``, as an administrator reads them."""
    record = read_schedule_month(session, month=month, viewer_uid=admin, viewer_roles=_roles(session, admin))
    return {engineer.user_uid: (engineer.accepted_count, engineer.rejected_count) for engineer in record.engineers}


def test_the_month_counts_the_decisions_that_stand_and_not_the_carried_withdrawn_or_foreign_ones(
    session: Session, cast: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Findings and proposals together; the author of the standing decision is credited; three kinds of decision are not counted.

    Not counted for the engineer, each with a decision of the same kind beside it that is: a decision **carried over** from an
    earlier version (the same act as its source, `carried_from_decision_id`), a **withdrawn** one (the latest verdict is a
    revoke), and **another expert's** (counted for its author only). A red here means one of the three reached the counter.
    """
    a, b = cast.expert, cast.other_expert
    findings, proposals = _Findings(session), _Proposals(session, cast, monkeypatch, count=8)

    # The ordinary case: a finding accepted, a finding rejected, a proposal accepted, a proposal rejected -- by A, in November.
    findings.decide(findings.take(), "accept", a, "2026-11-03T10:00:00+00")
    findings.decide(findings.take(), "reject", a, "2026-11-04T10:00:00+00")
    proposals.decide(proposals.take(), "accept", a, "2026-11-05T10:00:00+00")
    proposals.decide(proposals.take(), "reject", a, "2026-11-06T10:00:00+00")
    # A revision is neither: the proposal is asked to be changed, not taken or refused.
    proposals.decide(proposals.take(), "revise", a, "2026-11-06T11:00:00+00")

    # CARRIED: B decided on the earlier version in October (that decision counts, in October); A confirmed the carryover in
    # November onto the later version's finding and proposal (those copies are not decisions of A's).
    source_finding, source_proposal = findings.take(), proposals.take()
    source_finding_decision = findings.decide(source_finding, "accept", b, "2026-10-12T10:00:00+00")
    source_proposal_decision = proposals.decide(source_proposal, "accept", b, "2026-10-12T10:00:00+00")
    findings.decide(findings.take(), "accept", a, "2026-11-07T10:00:00+00", carried_from=source_finding_decision)
    proposals.decide(proposals.take(), "accept", a, "2026-11-08T10:00:00+00", carried_from=source_proposal_decision)

    # WITHDRAWN: A accepted a finding and rejected a proposal, then withdrew both -- nothing stands. A finding accepted,
    # withdrawn by B and accepted again by A stands once.
    withdrawn_finding = findings.take()
    findings.decide(withdrawn_finding, "accept", a, "2026-11-09T10:00:00+00")
    findings.decide(withdrawn_finding, "revoke", a, "2026-11-10T10:00:00+00")
    withdrawn_proposal = proposals.take()
    proposals.decide(withdrawn_proposal, "reject", a, "2026-11-09T10:00:00+00")
    proposals.decide(withdrawn_proposal, "revoke", a, "2026-11-10T10:00:00+00")
    decided_again = findings.take()
    findings.decide(decided_again, "accept", a, "2026-11-11T10:00:00+00")
    findings.decide(decided_again, "revoke", b, "2026-11-12T10:00:00+00")
    findings.decide(decided_again, "accept", a, "2026-11-13T10:00:00+00")

    # FOREIGN: B's decisions are B's. A finding A accepted and B then rejected stands as B's rejection and is not A's acceptance.
    findings.decide(findings.take(), "accept", b, "2026-11-14T10:00:00+00")
    proposals.decide(proposals.take(), "reject", b, "2026-11-14T10:00:00+00")
    overruled = findings.take()
    findings.decide(overruled, "accept", a, "2026-11-15T10:00:00+00")
    findings.decide(overruled, "reject", b, "2026-11-16T10:00:00+00")

    # A comment carries no verdict: it does not unseat the acceptance beside it. A decision changed by its own author counts
    # once, as what stands. An event from before accounts existed (no author) is credited to nobody.
    commented = findings.take()
    findings.decide(commented, "accept", a, "2026-11-17T10:00:00+00")
    findings.decide(commented, "comment", a, "2026-11-18T10:00:00+00")
    changed = findings.take()
    findings.decide(changed, "accept", a, "2026-11-18T12:00:00+00")
    findings.decide(changed, "reject", a, "2026-11-19T10:00:00+00")
    findings.decide(findings.take(), "accept", None, "2026-11-20T10:00:00+00")
    session.commit()

    november = _decisions(session, cast.admin, NOVEMBER)
    # A: accepted -- the finding of the 3rd, the proposal of the 5th, the finding decided again on the 13th, the commented one;
    # rejected -- the finding of the 4th, the proposal of the 6th, the one changed to a rejection.
    assert november[a] == (4, 3), "carried, withdrawn, foreign, revised or comment-only decisions must not be counted for A"
    # B: accepted -- the finding of the 14th; rejected -- the proposal of the 14th and the finding that overruled A's acceptance.
    assert november[b] == (1, 2)
    # Nobody else decided anything; the account-less event is credited to no engineer.
    assert {uid: pair for uid, pair in november.items() if uid not in (a, b)} == {
        uid: (0, 0) for uid in november if uid not in (a, b)
    }
    assert cast.admin_expert in november and cast.nobody not in november
    assert (sum(pair[0] for pair in november.values()), sum(pair[1] for pair in november.values())) == (5, 5)

    # The sources of the carryover are decisions of October, counted there and only there: the copies were not counted twice.
    october = _decisions(session, cast.admin, date(2026, 10, 1))
    assert october[b] == (2, 0) and october[a] == (0, 0)
    assert all(pair == (0, 0) for uid, pair in october.items() if uid not in (a, b))
    assert all(pair == (0, 0) for pair in _decisions(session, cast.admin, date(2026, 12, 1)).values())

    # An expert reads their own row alone, with the same two numbers; a counter does not depend on who asks.
    own = read_schedule_month(session, month=NOVEMBER, viewer_uid=a, viewer_roles=_roles(session, a))
    assert [(item.user_uid, item.accepted_count, item.rejected_count) for item in own.engineers] == [(a, 4, 3)]


def test_the_month_and_the_day_are_cut_in_the_schedules_time_zone(session: Session, cast: Any) -> None:
    """The same decisions fall in other months once the administrator sets another zone; the boundaries are the zone's midnight."""
    a, admin = cast.expert, _roles(session, cast.admin)
    findings = _Findings(session)
    findings.decide(findings.take(), "accept", a, "2026-10-31T21:30:00+00")  # 00:30 on 1 November in Moscow, still October in UTC
    findings.decide(findings.take(), "reject", a, "2026-11-30T20:59:59+00")  # 23:59:59 on 30 November in Moscow
    findings.decide(findings.take(), "accept", a, "2026-11-30T21:00:00+00")  # 00:00:00 on 1 December in Moscow
    session.commit()

    assert _decisions(session, cast.admin, date(2026, 10, 1))[a] == (1, 0)  # the schedule's zone is UTC
    assert _decisions(session, cast.admin, NOVEMBER)[a] == (1, 1)
    assert _decisions(session, cast.admin, date(2026, 12, 1))[a] == (0, 0)

    set_settings(session, default_monthly_plan=20, time_zone="Europe/Moscow", actor_uid=cast.admin, actor_roles=admin,
                 idempotency_key="zone-1")
    session.commit()
    assert _decisions(session, cast.admin, date(2026, 10, 1))[a] == (0, 0)
    assert _decisions(session, cast.admin, NOVEMBER)[a] == (1, 1), (
        "the late-October acceptance is November's in Moscow; the 21:00 one is not"
    )
    assert _decisions(session, cast.admin, date(2026, 12, 1))[a] == (1, 0)


def test_the_answer_carries_both_numbers_for_every_engineer_and_zeros_for_one_without_decisions(
    session: Session, cast: Any,
) -> None:
    """The wire shape: ``accepted_count`` and ``rejected_count`` on every engineer of the answer, built by the shipped adapter."""
    findings = _Findings(session)
    findings.decide(findings.take(), "accept", cast.expert, "2026-11-03T10:00:00+00")
    findings.decide(findings.take(), "reject", cast.expert, "2026-11-04T10:00:00+00")
    findings.decide(findings.take(), "reject", cast.expert, "2026-11-05T10:00:00+00")
    session.commit()

    adapter = ScheduleAdapter(sessionmaker(bind=session.get_bind(), expire_on_commit=False))
    wire = adapter.read_month(month="2026-11", user_uid=cast.admin).model_dump(mode="json", exclude_none=True)
    counted = {item["user_uid"]: (item["accepted_count"], item["rejected_count"]) for item in wire["engineers"]}
    assert counted[cast.expert] == (1, 2)
    assert counted[cast.other_expert] == (0, 0), "an engineer without decisions has both numbers, zero"
    assert all(set(item) >= {"accepted_count", "rejected_count"} for item in wire["engineers"])
