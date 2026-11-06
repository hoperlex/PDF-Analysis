"""«График работ» on a real database (`UI-PARITY-P0P`, `R-152a`…`R-152h`).

Every read runs its SQL on the migrated schema; every command is keyed and appends events. The month's fact rule (a
document «Проверено экспертом» on the day of its last verdict) is executed here over a schema with no checked document;
a run with decided findings is the remaining part of `D-318`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository
from auditmanager.dispatch.public import assign_work, get_assignment
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
