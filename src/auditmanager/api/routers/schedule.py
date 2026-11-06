"""«График работ» (`UI-PARITY-P0P`, contract 1.31.0): the month, the reserve, and the administrator's writes.

Every rule is ``auditmanager.schedule``'s; the router reads the subject and hands it on. The writes are keyed: one
``Idempotency-Key`` is one command, a repeat answers what the first did.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import Field

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import SchedulePort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_schedule_routes"]

_TAGS = ["schedule"]

MonthParam = Annotated[
    Annotated[str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")],
    Query(description="The month, `YYYY-MM`."),
]
StartParam = Annotated[date, Query(description="The first day of the reserve shown.")]
DaysParam = Annotated[Annotated[int, Field(ge=1, le=92)], Query(description="How many days from `start`.")]


def build_schedule_routes(router: APIRouter, schedule: SchedulePort) -> None:

    @router.get(
        "/work-schedule", operation_id="getWorkSchedule", tags=_TAGS, status_code=200,
        response_model=models.WorkScheduleMonth,
        responses={**success(200, "The month of «Выполнено»."), **envelope_responses(401, 403, 422, 500, 503)},
        description=(
            "`UI-PARITY-P0P` (contract 1.31.0, rulings `R-151x`, `R-152a`…`R-152d`): one month of «График работ» -- the "
            "days (Saturday and Sunday off unless the administrator decided otherwise), and for each active expert the "
            "month's plan (`plan_is_default` when the stored default applies), the documents that became «Проверено "
            "экспертом» in the month credited to the author of their last verdict (`done`, `fact`) and the absent days. "
            "An administrator reads every active expert; an expert reads their own row. `role:admin|expert`."
        ),
    )
    def get_work_schedule(subject: CurrentSubject, month: MonthParam) -> WireResponse:
        answer = schedule.read_month(month=month, user_uid=subject.user_uid)
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_none=True)))

    @router.get(
        "/work-schedule/reserve", operation_id="getWorkScheduleReserve", tags=_TAGS, status_code=200,
        response_model=models.WorkScheduleReserve,
        responses={**success(200, "«Календарь запаса» over the days asked."), **envelope_responses(401, 403, 422, 500, 503)},
        description=(
            "`UI-PARITY-P0P` (rulings `R-150y`, `R-152e`, `R-152f`): «Календарь запаса» -- each active expert's open "
            "assignments of «Диспетчер» with their planned date (absent: «без даты»), over `days` days from `start`, and "
            "the calendar of those days. No daily limit. An administrator reads every expert; an expert their own. "
            "`role:admin|expert`."
        ),
    )
    def get_work_schedule_reserve(subject: CurrentSubject, start: StartParam, days: DaysParam = 28) -> WireResponse:
        answer = schedule.read_reserve(start=start, days=days, user_uid=subject.user_uid)
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_none=True)))

    @router.put(
        "/work-schedule/settings", operation_id="setWorkScheduleSettings", tags=_TAGS, status_code=200,
        response_model=models.WorkScheduleSettings,
        responses={**success(200, "The settings after the command."), **envelope_responses(401, 403, 409, 422, 500, 503)},
        description=(
            "`R-152b`: the default monthly plan of an engineer without one (0..999, initially 20) and the IANA time zone "
            "the schedule's days are cut in (`constraint: unknown_zone` for another). Keyed; `role:admin`."
        ),
    )
    def set_work_schedule_settings(
        subject: CurrentSubject, body: models.WorkScheduleSettings, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        answer = schedule.set_settings(
            default_monthly_plan=body.default_monthly_plan, time_zone=body.time_zone,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(answer.model_dump(mode="json")))

    @router.put(
        "/work-schedule/plans", operation_id="setWorkSchedulePlans", tags=_TAGS, status_code=200,
        response_model=models.WorkScheduleMonth,
        responses={**success(200, "The month after the command."), **envelope_responses(401, 403, 409, 422, 500, 503)},
        description=(
            "`R-151x`, `R-152a`: an administrator sets engineers' plans (0..999) for one month; each change is kept in the "
            "plan's history, an unchanged plan records nothing, a user who is not an active expert is `422` "
            "(`constraint: active_expert`). Answers the month. Keyed; `role:admin`."
        ),
    )
    def set_work_schedule_plans(
        subject: CurrentSubject, body: models.SetWorkSchedulePlansRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        answer = schedule.set_plans(
            month=body.month, plans=[(plan.user_uid, plan.planned) for plan in body.plans],
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_none=True)))

    @router.put(
        "/work-calendar/days", operation_id="setWorkCalendarDays", tags=_TAGS, status_code=204,
        responses={**success(204, "The days were recorded."), **envelope_responses(401, 403, 409, 422, 500, 503)},
        description=(
            "`R-152d`: the administrator makes days days off (`day_off`) or working days (`workday`), or returns them to "
            "the week's rule (`default`). Every change is kept. Keyed; `role:admin`."
        ),
    )
    def set_work_calendar_days(
        subject: CurrentSubject, body: models.SetWorkCalendarDaysRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        schedule.set_calendar_days(
            days=[(change.day, change.kind) for change in body.days], user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return WireResponse(204, (), b"")

    @router.put(
        "/work-schedule/absences", operation_id="setEngineerAbsences", tags=_TAGS, status_code=204,
        responses={**success(204, "The absences were recorded."), **envelope_responses(401, 403, 409, 422, 500, 503)},
        description=(
            "`R-152d`: an administrator marks an active expert's days absent or clears them. Every change is kept. "
            "Keyed; `role:admin`."
        ),
    )
    def set_engineer_absences(
        subject: CurrentSubject, body: models.SetEngineerAbsencesRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        schedule.set_absences(
            engineer_uid=body.user_uid, days=[(change.day, change.absent) for change in body.days],
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return WireResponse(204, (), b"")

    @router.post(
        "/work-schedule/reserve/moves", operation_id="scheduleAssignments", tags=_TAGS, status_code=204,
        responses={**success(204, "The moves were recorded."), **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
        description=(
            "`R-152g`, `R-152h`: move one or several open assignments to a day (`planned_on` absent: «без даты») and, with "
            "`assignee_user_uid`, to another active expert (a reassignment in the assignment's history). Each move is a "
            "new event with its author; an unchanged date records nothing. Keyed; `role:admin`."
        ),
    )
    def schedule_assignments(
        subject: CurrentSubject, body: models.ScheduleAssignmentsRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        schedule.schedule_assignments(
            moves=[(move.assignment_uid, move.planned_on, move.assignee_user_uid) for move in body.moves],
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return WireResponse(204, (), b"")
