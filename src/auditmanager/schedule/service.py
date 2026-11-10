"""«График работ» (`UI-PARITY-P0P`, rulings `R-150y`, `R-151x`, `R-151y`, `R-152a`…`R-152h`, migration 0055).

**Done work** (`R-151x`) is a document reaching «Проверено экспертом» -- the ``checked`` state of the audit read model
(`R-150n`…`R-150u`): the current version of a document in use has a result run whose every finding is decided. The day it
happened is the day of the latest verdict on those findings, in the schedule's time zone, and it is credited to the
author of that verdict. It is derived from the current state, as the dashboard's counters are: a new version that is not
yet checked takes the document out of the facts again.

**The plan** (`R-151x`, `R-152a`, `R-152b`) is an engineer's number for a month, set by an administrator; without one, the
stored default (initially 20). It drives «Осталось» and «Выполнение %» and nothing else.

**The work calendar** (`R-152d`) is Saturday and Sunday off unless the administrator made a day a working day, and any
day the administrator made a day off; absences are per engineer and day.

**The reserve** (`R-150y`, `R-152e`…`R-152h`) places the open assignments of «Диспетчер» on days: each move is a new event
with its author, ``NULL`` is «без даты»; a move to another engineer is a reassignment through the dispatch boundary.
No daily limit (`R-152f`).

Roles: an administrator reads every engineer and writes everything here; an expert reads their own row (`R-151x`);
nobody else reads the schedule (it is the dispatcher's, closed to the viewer as «Диспетчер» is, `R-150w`).
"""

from __future__ import annotations

import calendar as _calendar
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT
from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey

__all__ = [
    "CALENDAR_KINDS",
    "PLAN_MAX",
    "ReserveCalendar",
    "ReserveItem",
    "ScheduleDay",
    "ScheduleEngineer",
    "ScheduleMonth",
    "ScheduleSettings",
    "read_reserve",
    "read_schedule_month",
    "schedule_assignments",
    "set_absences",
    "set_calendar_days",
    "set_plans",
    "set_settings",
]

PLAN_MAX: Final[int] = 999
CALENDAR_KINDS: Final[tuple[str, ...]] = ("day_off", "workday", "default")
RESERVE_DAYS_MAX: Final[int] = 92
_TERMINAL_KINDS: Final[tuple[str, ...]] = ("completed", "cancelled")

_SETTINGS = text(
    "SELECT default_monthly_plan, time_zone FROM schedule_setting_event "
    "ORDER BY occurred_at DESC, setting_event_id DESC LIMIT 1"
)
_ENGINEERS = text(
    """
    SELECT u.user_uid FROM app_user u
    JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'expert'
    WHERE u.archived_at IS NULL
    """
)
_PLANS = text(
    """
    SELECT DISTINCT ON (engineer_user_uid) engineer_user_uid, planned
    FROM schedule_plan_event WHERE month = :month
    ORDER BY engineer_user_uid, occurred_at DESC, plan_event_id DESC
    """
)
_CALENDAR = text(
    """
    SELECT DISTINCT ON (day) day, kind FROM work_calendar_event
    WHERE day >= :start AND day < :stop ORDER BY day, occurred_at DESC, calendar_event_id DESC
    """
)
_ABSENCES = text(
    """
    SELECT engineer_user_uid, day FROM (
        SELECT DISTINCT ON (engineer_user_uid, day) engineer_user_uid, day, absent FROM engineer_absence_event
        WHERE day >= :start AND day < :stop
        ORDER BY engineer_user_uid, day, occurred_at DESC, absence_event_id DESC
    ) latest WHERE absent
    """
)
#: The ``checked`` documents of the audit read model (`dashboard/audit_state.py`, the same rules) whose latest verdict
#: falls in ``[:start, :stop)`` of the schedule's zone, with that verdict's author. The result run is the newest published or
#: partial run, as the audit state reads it.
_FACTS = text(
    """
    WITH current_docs AS (
        SELECT d.document_uid, d.display_title, d.project_uid, p.name AS project_name, v.version_uid
        FROM document d
        JOIN document_version v ON v.version_uid = d.current_version_uid
        JOIN project p ON p.project_uid = d.project_uid
        WHERE d.archived_at IS NULL
    ),
    result_run AS (
        SELECT DISTINCT ON (r.version_uid) r.version_uid, r.run_id
        FROM audit_run r
        WHERE r.state IN ('published', 'partial')
          AND r.version_uid IN (SELECT version_uid FROM current_docs)
        ORDER BY r.version_uid, r.created_at DESC, r.run_id DESC
    ),
    run_finding AS (
        SELECT rr.version_uid, o.finding_uid
        FROM result_run rr
        JOIN finding_observation o ON o.run_id = rr.run_id
        JOIN finding f ON f.finding_uid = o.finding_uid
        GROUP BY rr.version_uid, o.finding_uid
    ),
    checked AS (
        SELECT rf.version_uid FROM run_finding rf
        JOIN finding_current_verdict cv ON cv.finding_uid = rf.finding_uid
        GROUP BY rf.version_uid
        HAVING count(*) FILTER (WHERE cv.current_verdict IN ('pending', 'needs_manual_review')) = 0
    ),
    last_verdict AS (
        SELECT DISTINCT ON (rf.version_uid) rf.version_uid, e.author_user_uid, e.recorded_at
        FROM run_finding rf
        JOIN expert_decision_event e ON e.finding_uid = rf.finding_uid AND e.verdict IS NOT NULL
        WHERE rf.version_uid IN (SELECT version_uid FROM checked)
        ORDER BY rf.version_uid, e.recorded_at DESC, e.sequence_no DESC
    )
    SELECT cd.document_uid, cd.display_title, cd.project_uid, cd.project_name, lv.author_user_uid,
           (lv.recorded_at AT TIME ZONE :zone)::date AS day
    FROM current_docs cd
    JOIN last_verdict lv ON lv.version_uid = cd.version_uid
    WHERE lv.author_user_uid IS NOT NULL
      AND (lv.recorded_at AT TIME ZONE :zone)::date >= :start
      AND (lv.recorded_at AT TIME ZONE :zone)::date < :stop
    """
)
_OPEN_ASSIGNMENTS = text(
    """
    SELECT c.assignment_uid, c.current_assignee_user_uid, c.project_uid, p.name AS project_name, c.document_uid,
           d.display_title AS document_title, c.last_kind,
           (SELECT s.planned_on FROM work_assignment_schedule_event s WHERE s.assignment_uid = c.assignment_uid
             ORDER BY s.occurred_at DESC, s.schedule_event_id DESC LIMIT 1) AS planned_on
    FROM work_assignment_current c
    JOIN project p ON p.project_uid = c.project_uid
    LEFT JOIN document d ON d.document_uid = c.document_uid
    WHERE c.last_kind <> ALL (CAST(:terminal AS text[]))
    ORDER BY c.created_at, c.assignment_uid
    """
)
_ASSIGNMENT_KIND = text("SELECT last_kind FROM work_assignment_current WHERE assignment_uid = :assignment_uid")
_PLANNED = text(
    "SELECT planned_on FROM work_assignment_schedule_event WHERE assignment_uid = :assignment_uid "
    "ORDER BY occurred_at DESC, schedule_event_id DESC LIMIT 1"
)
_INSERT_SETTING = text(
    "INSERT INTO schedule_setting_event (setting_event_id, default_monthly_plan, time_zone, actor_user_uid) "
    "VALUES (:id, :plan, :zone, :actor)"
)
_INSERT_PLAN = text(
    "INSERT INTO schedule_plan_event (plan_event_id, engineer_user_uid, month, planned, actor_user_uid) "
    "VALUES (:id, :engineer, :month, :planned, :actor)"
)
_INSERT_DAY = text(
    "INSERT INTO work_calendar_event (calendar_event_id, day, kind, actor_user_uid) VALUES (:id, :day, :kind, :actor)"
)
_INSERT_ABSENCE = text(
    "INSERT INTO engineer_absence_event (absence_event_id, engineer_user_uid, day, absent, actor_user_uid) "
    "VALUES (:id, :engineer, :day, :absent, :actor)"
)
_INSERT_PLANNED = text(
    "INSERT INTO work_assignment_schedule_event (schedule_event_id, assignment_uid, planned_on, actor_user_uid) "
    "VALUES (:id, :assignment, :planned_on, :actor)"
)


@dataclass(frozen=True, slots=True)
class ScheduleSettings:
    default_monthly_plan: int
    time_zone: str


@dataclass(frozen=True, slots=True)
class ScheduleDay:
    day: date
    day_off: bool
    #: ``day_off`` or ``workday`` when the administrator decided the day, ``None`` when the week's rule did.
    override: str | None = None


@dataclass(frozen=True, slots=True)
class DoneDocument:
    document_uid: str
    document_title: str
    project_uid: str
    project_name: str
    day: date


@dataclass(frozen=True, slots=True)
class ScheduleEngineer:
    user_uid: str
    plan: int
    plan_is_default: bool
    done: tuple[DoneDocument, ...]
    absences: tuple[date, ...]

    @property
    def fact(self) -> int:
        return len(self.done)


@dataclass(frozen=True, slots=True)
class ScheduleMonth:
    month: date
    settings: ScheduleSettings
    days: tuple[ScheduleDay, ...]
    engineers: tuple[ScheduleEngineer, ...]


@dataclass(frozen=True, slots=True)
class ReserveItem:
    assignment_uid: str
    project_uid: str
    project_name: str
    document_uid: str | None
    document_title: str | None
    status: str
    planned_on: date | None


@dataclass(frozen=True, slots=True)
class ReserveCalendar:
    start: date
    days: tuple[ScheduleDay, ...]
    #: Each engineer's open assignments, in creation order; ``planned_on`` ``None`` is «без даты».
    engineers: tuple[tuple[str, tuple[ReserveItem, ...]], ...] = field(default=())


def _settings(session: Session) -> ScheduleSettings:
    row = session.execute(_SETTINGS).one()
    return ScheduleSettings(default_monthly_plan=int(row[0]), time_zone=str(row[1]))


def _require_admin(roles: frozenset[str]) -> None:
    if ROLE_ADMIN not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED, aggregate_type="WorkSchedule", required_capability="role:admin")


def _readable_engineers(session: Session, viewer_uid: str, roles: frozenset[str]) -> list[str]:
    """Every active expert for an administrator; an expert reads their own row only (`R-151x`)."""
    if ROLE_ADMIN in roles:
        return sorted(str(row[0]) for row in session.execute(_ENGINEERS))
    if ROLE_EXPERT in roles:
        return [viewer_uid]
    raise DomainError(ErrorCode.PERMISSION_DENIED, aggregate_type="WorkSchedule", required_capability="role:admin|expert")


def _days(session: Session, start: date, stop: date) -> tuple[ScheduleDay, ...]:
    overrides = {row[0]: str(row[1]) for row in session.execute(_CALENDAR, {"start": start, "stop": stop})}
    days: list[ScheduleDay] = []
    day = start
    while day < stop:
        kind = overrides.get(day)
        weekend = day.weekday() >= 5
        day_off = kind == "day_off" or (weekend and kind != "workday")
        days.append(ScheduleDay(day=day, day_off=day_off, override=None if kind in (None, "default") else kind))
        day += timedelta(days=1)
    return tuple(days)


def _month_bounds(month: date) -> tuple[date, date]:
    start = month.replace(day=1)
    return start, start + timedelta(days=_calendar.monthrange(start.year, start.month)[1])


def read_schedule_month(session: Session, *, month: date, viewer_uid: str, viewer_roles: Iterable[str]) -> ScheduleMonth:
    """One month of «Выполнено»: the calendar, each readable engineer's plan, done documents and absences."""
    roles = frozenset(viewer_roles)
    engineers = _readable_engineers(session, viewer_uid, roles)
    settings = _settings(session)
    start, stop = _month_bounds(month)
    plans = {str(row[0]): int(row[1]) for row in session.execute(_PLANS, {"month": start})}
    done: dict[str, list[DoneDocument]] = defaultdict(list)
    for row in session.execute(_FACTS, {"start": start, "stop": stop, "zone": settings.time_zone}).mappings():
        done[str(row["author_user_uid"])].append(DoneDocument(
            document_uid=row["document_uid"], document_title=row["display_title"], project_uid=row["project_uid"],
            project_name=row["project_name"], day=row["day"],
        ))
    absences: dict[str, list[date]] = defaultdict(list)
    for row in session.execute(_ABSENCES, {"start": start, "stop": stop}):
        absences[str(row[0])].append(row[1])
    return ScheduleMonth(
        month=start, settings=settings, days=_days(session, start, stop),
        engineers=tuple(ScheduleEngineer(
            user_uid=uid, plan=plans.get(uid, settings.default_monthly_plan), plan_is_default=uid not in plans,
            done=tuple(sorted(done.get(uid, ()), key=lambda item: (item.day, item.document_uid))),
            absences=tuple(sorted(absences.get(uid, ()))),
        ) for uid in engineers),
    )


def read_reserve(
    session: Session, *, start: date, days: int, viewer_uid: str, viewer_roles: Iterable[str],
) -> ReserveCalendar:
    """«Календарь запаса»: the open assignments of each readable engineer over ``days`` days from ``start``."""
    if not 1 <= days <= RESERVE_DAYS_MAX:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="days", constraint="range")
    roles = frozenset(viewer_roles)
    engineers = _readable_engineers(session, viewer_uid, roles)
    items: dict[str, list[ReserveItem]] = defaultdict(list)
    from auditmanager.dispatch.public import STATUS_AFTER

    for row in session.execute(_OPEN_ASSIGNMENTS, {"terminal": list(_TERMINAL_KINDS)}).mappings():
        items[str(row["current_assignee_user_uid"])].append(ReserveItem(
            assignment_uid=row["assignment_uid"], project_uid=row["project_uid"], project_name=row["project_name"],
            document_uid=row["document_uid"], document_title=row["document_title"],
            status=STATUS_AFTER[row["last_kind"]],
            planned_on=row["planned_on"],
        ))
    return ReserveCalendar(
        start=start, days=_days(session, start, start + timedelta(days=days)),
        engineers=tuple((uid, tuple(items.get(uid, ()))) for uid in engineers),
    )


def _claim(session: Session, command_type: str, key: str, payload: dict, commands: CommandRepository | None):
    ledger = commands or CommandRepository()
    claimed = ledger.begin(session, command_type=command_type, idempotency_key=IdempotencyKey(key),
                           fingerprint=payload_fingerprint(payload))
    return ledger, claimed


def set_settings(
    session: Session, *, default_monthly_plan: int, time_zone: str, actor_uid: str, actor_roles: Iterable[str],
    idempotency_key: str, commands: CommandRepository | None = None,
) -> ScheduleSettings:
    """`R-152b`: the default monthly plan and the zone the schedule's days are cut in."""
    _require_admin(frozenset(actor_roles))
    if not 0 <= default_monthly_plan <= PLAN_MAX:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="default_monthly_plan", constraint="range")
    try:
        ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="time_zone", constraint="unknown_zone") from None
    ledger, claimed = _claim(session, "set_schedule_settings", idempotency_key,
                             {"default_monthly_plan": default_monthly_plan, "time_zone": time_zone}, commands)
    if isinstance(claimed, CommandStarted):
        if _settings(session) != ScheduleSettings(default_monthly_plan, time_zone):
            session.execute(_INSERT_SETTING, {"id": str(AuditEventId.new()), "plan": default_monthly_plan,
                                              "zone": time_zone, "actor": actor_uid})
        ledger.succeed(session, claimed.command_id, {"default_monthly_plan": default_monthly_plan})
    return _settings(session)


def set_plans(
    session: Session, *, month: date, plans: Sequence[tuple[str, int]], actor_uid: str, actor_roles: Iterable[str],
    idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """`R-151x`: an administrator sets engineers' plans for one month; an unchanged plan records nothing."""
    _require_admin(frozenset(actor_roles))
    start, _stop = _month_bounds(month)
    for engineer, planned in plans:
        if not 0 <= planned <= PLAN_MAX:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="planned", constraint="range")
    ledger, claimed = _claim(session, "set_schedule_plans", idempotency_key,
                             {"month": start.isoformat(), "plans": sorted([list(plan) for plan in plans])}, commands)
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    current = {str(row[0]): int(row[1]) for row in session.execute(_PLANS, {"month": start})}
    engineers = {str(row[0]) for row in session.execute(_ENGINEERS)}
    for engineer, planned in plans:
        if engineer not in engineers:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="user_uid", constraint="active_expert")
        if current.get(engineer) != planned:
            session.execute(_INSERT_PLAN, {"id": str(AuditEventId.new()), "engineer": engineer, "month": start,
                                           "planned": planned, "actor": actor_uid})
    ledger.succeed(session, claimed.command_id, {"month": start.isoformat()})


def set_calendar_days(
    session: Session, *, days: Sequence[tuple[date, str]], actor_uid: str, actor_roles: Iterable[str],
    idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """`R-152d`: days off and working days the administrator decides; ``default`` returns a day to the week's rule."""
    _require_admin(frozenset(actor_roles))
    if any(kind not in CALENDAR_KINDS for _day, kind in days):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="kind", constraint="enum")
    ledger, claimed = _claim(session, "set_work_calendar_days", idempotency_key,
                             {"days": sorted([[day.isoformat(), kind] for day, kind in days])}, commands)
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    for day, kind in days:
        session.execute(_INSERT_DAY, {"id": str(AuditEventId.new()), "day": day, "kind": kind, "actor": actor_uid})
    ledger.succeed(session, claimed.command_id, {"days": len(days)})


def set_absences(
    session: Session, *, engineer_uid: str, days: Sequence[tuple[date, bool]], actor_uid: str,
    actor_roles: Iterable[str], idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """`R-152d`: an engineer's absent days, marked or cleared by an administrator."""
    _require_admin(frozenset(actor_roles))
    ledger, claimed = _claim(session, "set_engineer_absences", idempotency_key, {
        "engineer": engineer_uid, "days": sorted([[day.isoformat(), absent] for day, absent in days]),
    }, commands)
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    if engineer_uid not in {str(row[0]) for row in session.execute(_ENGINEERS)}:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="user_uid", constraint="active_expert")
    for day, absent in days:
        session.execute(_INSERT_ABSENCE, {"id": str(AuditEventId.new()), "engineer": engineer_uid, "day": day,
                                          "absent": absent, "actor": actor_uid})
    ledger.succeed(session, claimed.command_id, {"days": len(days)})


def schedule_assignments(
    session: Session, *, moves: Sequence[tuple[str, date | None, str | None]], actor_uid: str,
    actor_roles: Iterable[str], idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """`R-152g`, `R-152h`: place or move assignments on days (``None``: «без даты»), several at once; a move to another
    engineer reassigns through the dispatch boundary first. An unchanged date records nothing."""
    from auditmanager.dispatch.public import AGGREGATE_TYPE, MACHINE, STATUS_AFTER, transition_assignment

    roles = frozenset(actor_roles)
    _require_admin(roles)
    for assignment_uid, _planned_on, _assignee in moves:
        kind = session.execute(_ASSIGNMENT_KIND, {"assignment_uid": assignment_uid}).scalar_one_or_none()
        if kind is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)
        if kind in _TERMINAL_KINDS:
            # A closed assignment is not in the reserve; its date is history and is not moved.
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                message="a closed assignment is not placed on a day",
                machine=MACHINE,
                current_state=STATUS_AFTER[kind],
                requested_state=STATUS_AFTER[kind],
            )
    ledger, claimed = _claim(session, "schedule_assignments", idempotency_key, {"moves": sorted([
        [uid, None if day is None else day.isoformat(), assignee] for uid, day, assignee in moves
    ])}, commands)
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    for assignment_uid, planned_on, assignee in moves:
        if assignee is not None:
            record = transition_assignment(
                session, assignment_uid=assignment_uid, kind="reassigned", actor_uid=actor_uid, actor_roles=roles,
                reason="Перенесено в «Графике работ»", new_assignee_user_uid=assignee,
            )
            del record
        current = session.execute(_PLANNED, {"assignment_uid": assignment_uid}).scalar_one_or_none()
        if current != planned_on:
            session.execute(_INSERT_PLANNED, {"id": str(AuditEventId.new()), "assignment": assignment_uid,
                                              "planned_on": planned_on, "actor": actor_uid})
    ledger.succeed(session, claimed.command_id, {"moves": len(moves)})
