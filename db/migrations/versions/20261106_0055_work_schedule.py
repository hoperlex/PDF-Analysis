"""0055 -- «График работ»: plans, the work calendar, absences and planned dates (`UI-PARITY-P0P`, `R-152a`…`R-152h`).

The original's «График работ» shows each engineer's done work per day of a month against a monthly plan, and a
«Календарь запаса» of work placed on days. The owner ruled what of it we keep (`R-150y`, `R-151x`, `R-151y`, `R-152a`…h).
Every table here is an append-only journal (``am_immutable_row``): the current value of a key is its latest event, so a
change is never lost and always names who made it (`R-151x`: plan changes keep history; `R-152h`: a planned date is an
event of the assignment's history).

``schedule_setting_event``
    The installation's default monthly plan (`R-152b`, initially 20) and the time zone the schedule's days are cut in.
    One seed row is written here with no actor: the stored default the owner ruled, before any administrator set one.
``schedule_plan_event``
    An engineer's plan for one month (a month is its first day), set by an administrator (`R-151x`).
``work_calendar_event``
    A day the administrator made a day off or a working day; ``default`` returns it to the week's rule (Saturday and
    Sunday off, `R-152d`).
``engineer_absence_event``
    A day an engineer is absent or is not any more (`R-152d`).
``work_assignment_schedule_event``
    The planned date of an assignment of «Диспетчер», or ``NULL`` for «без даты» (`R-152e`, `R-152h`). Kept apart from
    ``work_assignment_event``, whose latest row is the assignment's state: a planned date is not a state.

Every account column is a RESTRICT reference to ``app_user`` with the ``0049`` identity check, registered in
``access/references.py``. Downgrade drops the five tables; the schedule's history is lost.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0055_work_schedule"
down_revision: str | None = "0054_finding_execution_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
TABLES: tuple[str, ...] = (
    "work_assignment_schedule_event",
    "engineer_absence_event",
    "work_calendar_event",
    "schedule_plan_event",
    "schedule_setting_event",
)


def _account(column: str, table: str, *, nullable: bool = False) -> str:
    null = "NULL" if nullable else "NOT NULL"
    check = f"{column} IS NULL OR {column} ~ '^usr_{ULID}$'" if nullable else f"{column} ~ '^usr_{ULID}$'"
    return (
        f"{column} text {null} CONSTRAINT fk_{table}_{column} REFERENCES app_user (user_uid) ON DELETE RESTRICT "
        f"CONSTRAINT ck_{table}_{column}_format CHECK ({check})"
    )


def _event_id(column: str, table: str) -> str:
    return f"{column} text PRIMARY KEY CONSTRAINT ck_{table}_{column}_format CHECK ({column} ~ '^evt_{ULID}$')"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE schedule_setting_event (
            {_event_id("setting_event_id", "schedule_setting_event")},
            default_monthly_plan integer NOT NULL
                CONSTRAINT ck_schedule_setting_event_default_monthly_plan CHECK (default_monthly_plan BETWEEN 0 AND 999),
            time_zone text NOT NULL
                CONSTRAINT ck_schedule_setting_event_time_zone CHECK (char_length(time_zone) BETWEEN 1 AND 64),
            {_account("actor_user_uid", "schedule_setting_event", nullable=True)},
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute(
        "INSERT INTO schedule_setting_event (setting_event_id, default_monthly_plan, time_zone, actor_user_uid) "
        "VALUES ('evt_00000000000000000000000000', 20, 'UTC', NULL)"
    )
    op.execute(f"""
        CREATE TABLE schedule_plan_event (
            {_event_id("plan_event_id", "schedule_plan_event")},
            {_account("engineer_user_uid", "schedule_plan_event")},
            month date NOT NULL CONSTRAINT ck_schedule_plan_event_month CHECK (extract(day FROM month) = 1),
            planned integer NOT NULL CONSTRAINT ck_schedule_plan_event_planned CHECK (planned BETWEEN 0 AND 999),
            {_account("actor_user_uid", "schedule_plan_event")},
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_schedule_plan_event_month ON schedule_plan_event (month, engineer_user_uid)")
    op.execute(f"""
        CREATE TABLE work_calendar_event (
            {_event_id("calendar_event_id", "work_calendar_event")},
            day date NOT NULL,
            kind text NOT NULL CONSTRAINT ck_work_calendar_event_kind CHECK (kind IN ('day_off', 'workday', 'default')),
            {_account("actor_user_uid", "work_calendar_event")},
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_work_calendar_event_day ON work_calendar_event (day)")
    op.execute(f"""
        CREATE TABLE engineer_absence_event (
            {_event_id("absence_event_id", "engineer_absence_event")},
            {_account("engineer_user_uid", "engineer_absence_event")},
            day date NOT NULL,
            absent boolean NOT NULL,
            {_account("actor_user_uid", "engineer_absence_event")},
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_engineer_absence_event_day ON engineer_absence_event (day, engineer_user_uid)")
    op.execute(f"""
        CREATE TABLE work_assignment_schedule_event (
            {_event_id("schedule_event_id", "work_assignment_schedule_event")},
            assignment_uid text NOT NULL
                CONSTRAINT fk_work_assignment_schedule_event_assignment
                    REFERENCES work_assignment (assignment_uid) ON DELETE RESTRICT,
            planned_on date NULL,
            {_account("actor_user_uid", "work_assignment_schedule_event")},
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute(
        "CREATE INDEX ix_work_assignment_schedule_event_assignment "
        "ON work_assignment_schedule_event (assignment_uid)"
    )
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    op.execute(
        "COMMENT ON TABLE work_assignment_schedule_event IS "
        "'R-152h: the planned date of an assignment of «Диспетчер» (NULL: без даты); the latest event is current.'"
    )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TABLE {table}")
