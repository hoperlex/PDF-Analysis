"""Emptying a throwaway norms database between tests (`W55A-FIX`).

Migration ``0020`` refuses TRUNCATE on ``norm_current_snapshot`` and on its history, also when
a TRUNCATE of ``norms_snapshot ... CASCADE`` reaches them: row triggers do not fire on
TRUNCATE, so without that refusal the history could be erased whole (JUDGE-X M4). The
custody, bundle and search suites each own a throwaway database and still need an empty one
per test, so :func:`truncate_tables` lifts the two refusals for its own TRUNCATE only -- by the
table owner's ``ALTER TABLE ... DISABLE TRIGGER``, which no DML can do -- inside the caller's
transaction, and enables them again before that transaction ends. A rollback restores them
too. On a database below ``0020`` there is nothing to lift.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sqlalchemy import Connection, text

#: ``0020``'s statement-level TRUNCATE refusals, by table.
TRUNCATE_REFUSALS: Final[tuple[tuple[str, str], ...]] = (
    ("norm_current_snapshot", "trg_norm_current_snapshot_no_truncate"),
    ("norm_current_snapshot_event", "trg_norm_current_snapshot_event_no_truncate"),
)


def truncate_tables(connection: Connection, tables: Sequence[str]) -> None:
    """``TRUNCATE TABLE <tables> CASCADE`` with ``0020``'s refusals lifted for it alone."""
    installed = set(
        connection.execute(
            text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgname = ANY(:names)"),
            {"names": [trigger for _table, trigger in TRUNCATE_REFUSALS]},
        ).scalars()
    )
    lifted = [(table, trigger) for table, trigger in TRUNCATE_REFUSALS if trigger in installed]
    for table, trigger in lifted:
        connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
    connection.execute(text(f"TRUNCATE TABLE {', '.join(tables)} CASCADE"))
    for table, trigger in lifted:
        connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
    if lifted:
        states = set(
            connection.execute(
                text("SELECT tgenabled FROM pg_trigger WHERE tgname = ANY(:names)"),
                {"names": [trigger for _table, trigger in lifted]},
            ).scalars()
        )
        assert states == {"O"}, f"a TRUNCATE refusal was left disabled: {states!r}"
