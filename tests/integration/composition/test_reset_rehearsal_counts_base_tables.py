"""`D-39` -- the wipe rehearsal's total, driven against a real PostgreSQL.

`R-4`: the owner ruled that **real client documents may be uploaded and must be wiped at
the end of the pilot**, so `reset.sh --dry-run` is the screen an operator reads before
agreeing to destroy them. `D-24` closed on the claim that its figures are exact. They were
not: the total summed `finding_current_verdict`, a VIEW that is one row per `finding`, so
every row it contributed was a projection of rows the line above it had already counted.
Measured by `W24-CERT2` as `total: 104 rows in 17 tables` over 100 rows in 16 base tables,
and again by `W26-OPS` before the repair as `total: 37 rows in 17 tables` over 33 rows in
16 base tables with a 4-row view.

**Why this file needs a database and does not read the script's text.** The defect is in
what one SQL statement computes, and an assertion about the characters of that statement
would pass the moment somebody wrote a different wrong one. `test_reset_script_refusals.py`
beside this file is the no-stack suite and stays that way; this is the arithmetic, driven.
The statement is EXTRACTED from `reset.sh` rather than copied here, so a repair that edits
the script and forgets this file reddens, and a repair that edits this file and forgets the
script cannot pass.

**Nothing here is created and nothing is destroyed.** Everything runs inside one
transaction that always rolls back: PostgreSQL's DDL is transactional, so the probe table
and the probe view exist for the length of the statement and never afterwards. The lane's
own schema is read, never written -- which is also what makes the case non-vacuous, since
the real seventeenth name is in it.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

ROOT = Path(__file__).resolve().parents[3]
RESET = ROOT / "infra/deploy/reset.sh"

#: The view the defect was found on, and the reason this suite is not vacuous: it is in
#: the lane's own migrated schema, so the probe objects below are not the only view here.
REAL_VIEW = "finding_current_verdict"

#: The probe. Three rows in a base table and a view that projects all three, which is
#: `finding` and `finding_current_verdict` in miniature -- a total that summed both would
#: say six.
PROBE_TABLE = "w26_ops_probe_rows"
PROBE_VIEW = "w26_ops_probe_view"
PROBE_ROWS = 3


def _count_rows_sql() -> str:
    """`COUNT_ROWS_SQL` as `reset.sh` assigns it, read out of the script itself."""
    source = RESET.read_text(encoding="utf-8")
    opening = 'COUNT_ROWS_SQL="'
    start = source.index(opening) + len(opening)
    end = source.index('"', start)
    sql = source[start:end]
    assert "information_schema.tables" in sql, sql
    assert "count(*)" in sql, "the rehearsal no longer counts anything"
    return sql


@pytest.fixture()
def rehearsal() -> Iterator[Connection]:
    """One connection on the lane's database, in a transaction that always rolls back."""
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. This case drives reset.sh's own counting statement "
            "against a real PostgreSQL; it never falls back and never skips itself."
        )
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(
            text(f"CREATE TABLE public.{PROBE_TABLE} (n integer NOT NULL)")
        )
        connection.execute(
            text(f"INSERT INTO public.{PROBE_TABLE} (n) SELECT generate_series(1, {PROBE_ROWS})")
        )
        connection.execute(
            text(f"CREATE VIEW public.{PROBE_VIEW} AS SELECT n FROM public.{PROBE_TABLE}")
        )
        yield connection
    finally:
        # Always. The probe objects are gone whether the case passed or failed, and this
        # suite has therefore written nothing to the lane's schema.
        transaction.rollback()
        connection.close()
        engine.dispose()


def _lines(connection: Connection) -> list[str]:
    """The rehearsal's screen, exactly as `psql --tuples-only --no-align` prints it.

    Through psycopg's OWN cursor with no parameters, so the statement reaches the server
    character for character as `psql` sends it. SQLAlchemy's `exec_driver_sql` passes an
    empty parameter set, and psycopg then reads the `%I` inside `format(...)` as a
    placeholder and refuses the query -- a transformation of the text under test is
    exactly what this file must not do.
    """
    with connection.connection.cursor() as cursor:
        cursor.execute(_count_rows_sql())
        return [row[0] for row in cursor.fetchall()]


def _kinds(connection: Connection) -> dict[str, str]:
    return {
        name: kind
        for name, kind in connection.exec_driver_sql(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).fetchall()
    }


def _counted(connection: Connection, name: str) -> int:
    return int(connection.exec_driver_sql(f'SELECT count(*) FROM public."{name}"').scalar_one())


class TestTheTotalCountsBaseTablesOnly:
    def test_the_total_is_the_base_tables_and_not_the_views(self, rehearsal: Connection) -> None:
        """`D-39` itself. The figures are computed from the same snapshot, so this is an
        equality and not a literal to be re-measured whenever the lane's data moves."""
        kinds = _kinds(rehearsal)
        base = {name for name, kind in kinds.items() if kind == "BASE TABLE"}
        views = {name for name, kind in kinds.items() if kind != "BASE TABLE"}
        assert PROBE_VIEW in views and REAL_VIEW in views, kinds
        base_rows = sum(_counted(rehearsal, name) for name in base)
        view_rows = sum(_counted(rehearsal, name) for name in views)

        total = _lines(rehearsal)[-1]
        assert total.startswith("  total: "), total
        figures = re.match(r"^  total: (\d+) rows in (\d+) base tables", total)
        assert figures is not None, total
        assert int(figures.group(1)) == base_rows, total
        assert int(figures.group(2)) == len(base), total

        # And the case has teeth: the old statement's answer is a DIFFERENT number here,
        # so a total that summed the views could not pass by coincidence.
        assert view_rows >= PROBE_ROWS, view_rows
        assert base_rows + view_rows != base_rows

    def test_the_total_says_which_tables_it_counted(self, rehearsal: Connection) -> None:
        """An operator reads this before destroying real client documents. `17 tables`
        over sixteen of them was true of nothing; `16 base tables` names its own scope,
        and the views it did not add are named rather than silently dropped."""
        total = _lines(rehearsal)[-1]
        views = len([1 for kind in _kinds(rehearsal).values() if kind != "BASE TABLE"])
        assert "base tables" in total, total
        assert f"(and {views} views listed above" in total, total

    def test_the_total_line_is_still_what_the_rehearsal_counted_guard_reads(
        self, rehearsal: Connection
    ) -> None:
        """`D-24`'s guard greps `^  total: ` as the evidence the count ran to the end. A
        repair that reworded the total out from under it would have removed a guard by
        accident, and the rehearsal would exit 0 again on a database it could not read."""
        assert "'^  total: '" in RESET.read_text(encoding="utf-8")
        assert [line for line in _lines(rehearsal) if line.startswith("  total: ")]

    def test_every_table_and_every_view_still_has_its_own_exact_line(
        self, rehearsal: Connection
    ) -> None:
        """`D-24`, which must not regress while `D-39` is repaired: the per-table figures
        are exact `count(*)`s, for the views too. The view is LISTED because the wipe
        drops it with the schema -- leaving it off would be the same untruth pointing the
        other way -- and its line says what it is."""
        lines = _lines(rehearsal)[:-1]
        printed = {line.split("  (")[0]: line for line in lines}
        kinds = _kinds(rehearsal)
        assert set(printed) == set(kinds), set(printed) ^ set(kinds)
        for name, kind in kinds.items():
            assert f"({_counted(rehearsal, name)} rows" in printed[name], printed[name]
            if kind != "BASE TABLE":
                assert "these rows are counted above" in printed[name], printed[name]
            else:
                assert printed[name].endswith(" rows)"), printed[name]

    def test_there_is_no_materialized_view_this_listing_cannot_see(
        self, rehearsal: Connection
    ) -> None:
        """The named limit of the repair, pinned rather than written down and forgotten.

        A MATERIALIZED view is not in `information_schema.tables` at all, so it would have
        no line on this screen and no place in the total -- an UNDER-report, which is the
        direction `D-24` exists to prevent. There is none in this schema; if one is ever
        added, this reddens before an operator is shown a screen that omits it.
        """
        matviews = rehearsal.exec_driver_sql(
            "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'"
        ).fetchall()
        assert matviews == [], (
            f"{[row[0] for row in matviews]} is a materialized view in public, and the "
            "rehearsal's listing reads information_schema.tables, which does not contain "
            "it. The screen would under-report what a wipe destroys."
        )
