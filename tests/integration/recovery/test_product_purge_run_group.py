"""`DEV-PURGE-INVENTORY-01`: the product purge handles a six-run AR v3 group (migration `0032`).

Migration `0032_ar_v3_run_group` added ``ar_v3_run_group`` and ``ar_v3_run_group_member`` and
the command type ``start_ar_v3_beta_group``, and nobody classified them: the tool refused every
database at head with "table(s) classified as neither PRODUCT, KEEP nor MIXED". The rest of
``test_product_purge.py`` proves that on the stand in miniature; this module proves it on a real
group, written the way the product writes one (``start_ar_v3_group``), in a database of its own:

* a dry run names both tables with their exact counts and changes nothing;
* the real run empties the group, its members, the six runs and the group's command receipt, and
  leaves every KEEP table (the snapshot and the retrieval sets the group pins) byte for byte;
* the ONLY way out is the one multi-table TRUNCATE: a row DELETE is refused by the immutable-row
  trigger and TRUNCATE of the parent alone is refused by the foreign key. So the order of tables
  never mattered; what matters is that the group, its members and every table that references
  them are classified PRODUCT together;
* the foreign keys of the two tables are pinned, so a later reference from a KEEP table, or from
  the group into a table the purge cannot leave consistent, fails here and not on a stand.

The database is a private clone of the migrated template, the bucket is private and empty (the
group writes no object), and ``DATABASE_URL``/``S3_*`` are pointed at them for the code under test.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage import S3StorageSettings
from auditmanager.runs.v3_group import start_ar_v3_group
from scripts.recovery import product_purge as tool
from tests.integration.db.test_ar_v3_run_group import _seed
from tests.integration.recovery.purge_seed import digest_of, s3
from tests.integration.recovery.purge_stand import (  # noqa: F401  (a fixture module imported by name)
    Stand, _empty_and_delete, full_purge, invoke, state_of,
)

GROUP_TABLES = ("ar_v3_run_group", "ar_v3_run_group_member")


@pytest.fixture
def grouped(migrated_database, monkeypatch) -> Iterator[Stand]:
    """A migrated clone holding ONE started group of six runs, and an empty private bucket."""
    base = S3StorageSettings.from_env()
    bucket = f"{base.bucket[:36]}-grp-{secrets.token_hex(5)}"
    values = {
        "DATABASE_URL": migrated_database.url.render_as_string(hide_password=False),
        "S3_ENDPOINT_URL": base.endpoint_url, "S3_REGION": base.region,
        "S3_ACCESS_KEY_ID": base.access_key_id, "S3_SECRET_ACCESS_KEY": base.secret_access_key,
        "S3_BUCKET": bucket,
    }
    client = s3(values)
    client.create_bucket(Bucket=bucket)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    engine = create_database_engine(migrated_database)
    try:
        with Session(engine) as session, session.begin():
            version, pack = _seed(session)
        with Session(engine) as session, session.begin():
            started = start_ar_v3_group(
                session, version_uid=version, idempotency_key="purge-inventory-group",
                provider_mode="recorded", pack=pack, input_budget_characters=1000,
            )
        assert len(started.group.members) == 6 and not started.replayed
        yield Stand(str(migrated_database.url.database), bucket, migrated_database, engine, values,
                    client, {"group_id": started.group.group_id})
    finally:
        engine.dispose()
        _empty_and_delete(client, bucket)


def _count(stand: Stand, table: str) -> int:
    with stand.engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM public.{table}")).scalar_one())


def test_the_fixture_is_a_real_group_with_its_receipt(grouped: Stand) -> None:
    """The premise of every other test here, measured: one group, six members, six runs, one receipt."""
    assert (_count(grouped, "ar_v3_run_group"), _count(grouped, "ar_v3_run_group_member")) == (1, 6)
    assert _count(grouped, "audit_run") == 6
    with grouped.engine.connect() as connection:
        types_ = connection.execute(text("SELECT command_type, count(*) FROM command_record GROUP BY 1")).all()
    assert [tuple(row) for row in types_] == [("start_ar_v3_beta_group", 1)]


def test_a_dry_run_names_both_group_tables_with_exact_counts_and_changes_nothing(grouped: Stand) -> None:
    before = state_of(grouped)
    code, out, err = invoke(tool, grouped, "plan", "--dry-run")
    assert code == 0, err
    assert "  ar_v3_run_group  (1 rows)" in out
    assert "  ar_v3_run_group_member  (6 rows)" in out
    assert "  audit_run  (6 rows)" in out
    assert "  command_record  (delete 1 rows, keep 0 rows)" in out
    assert "--dry-run: NOTHING ABOVE WAS CHANGED." in out and "nothing-to-purge: no" in out
    assert state_of(grouped) == before


def test_the_purge_empties_the_group_and_its_receipt_and_keeps_what_the_group_pins(
    grouped: Stand, tmp_path: Path
) -> None:
    keep_before = {table: digest_of(grouped.engine, table) for table in sorted(tool.KEEP_TABLES)}
    # the corpus the group pins is really there to be kept
    assert keep_before["norms_snapshot"][0] == 1 and keep_before["norm_retrieval_set"][0] == 6

    steps = full_purge(tool, grouped, tmp_path / "dump")
    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps

    for table in (*GROUP_TABLES, "audit_run", "project", "document_version", "input_manifest_entry"):
        assert _count(grouped, table) == 0, table
    assert _count(grouped, "command_record") == 0
    for table, digest in keep_before.items():
        assert digest_of(grouped.engine, table) == digest, table
    # every table that references the two tables is empty (a constraint violation would have
    # rolled the transaction back; this is the same fact read from the catalog)
    with grouped.engine.connect() as connection:
        referrers = connection.execute(text(
            "SELECT DISTINCT conrelid::regclass::text FROM pg_constraint WHERE contype = 'f' "
            "AND confrelid = ANY(ARRAY['public.ar_v3_run_group'::regclass, "
            "'public.ar_v3_run_group_member'::regclass])")).scalars().all()
    assert referrers == ["ar_v3_run_group_member"]

    code, out, err = invoke(tool, grouped, "plan")
    assert code == 0, err
    assert "nothing-to-purge: yes" in out


def test_only_the_one_multi_table_truncate_can_remove_a_group(grouped: Stand) -> None:
    """The brief's "children first" is not the mechanism: the rows are immutable and the tool truncates."""
    def refused(statement: str) -> DBAPIError:
        with pytest.raises(DBAPIError) as caught, grouped.engine.begin() as connection:
            connection.execute(text(statement))
        return caught.value

    deleted = refused("DELETE FROM public.ar_v3_run_group_member")
    assert "ar_v3_run_group_member is immutable once written; DELETE is refused" in str(deleted), deleted
    truncated = refused("TRUNCATE TABLE public.ar_v3_run_group")
    assert "cannot truncate a table referenced in a foreign key constraint" in str(truncated), truncated
    # the statement the tool issues (a set closed under "is referenced by") passes
    every_product_table = ", ".join(f'public."{name}"' for name in sorted(tool.PRODUCT_TABLES))
    with grouped.engine.connect() as connection:
        connection.execute(text("TRUNCATE TABLE " + every_product_table))
        assert connection.execute(text("SELECT count(*) FROM public.ar_v3_run_group_member")).scalar_one() == 0
        connection.rollback()
    assert _count(grouped, "ar_v3_run_group_member") == 6  # that probe changed nothing


def test_the_group_tables_reference_only_what_the_purge_can_leave_consistent(grouped: Stand) -> None:
    """Pins the foreign keys of ``0032``. A new reference is a decision about the purge, taken here."""
    with grouped.engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT conrelid::regclass::text, confrelid::regclass::text FROM pg_constraint "
            "WHERE contype = 'f' AND conrelid = ANY(ARRAY['public.ar_v3_run_group'::regclass, "
            "'public.ar_v3_run_group_member'::regclass])")).all()
    references = {(a, b) for a, b in rows}
    assert references == {
        ("ar_v3_run_group", "project"), ("ar_v3_run_group", "document_version"),
        ("ar_v3_run_group", "command_record"), ("ar_v3_run_group", "norms_snapshot"),
        ("ar_v3_run_group_member", "ar_v3_run_group"), ("ar_v3_run_group_member", "audit_run"),
        ("ar_v3_run_group_member", "norm_retrieval_set"),
    }
    # the two tables are PRODUCT, so every outgoing reference is to a table that is truncated
    # with them (PRODUCT), kept as it is (KEEP), or deleted from only AFTER the truncate (MIXED).
    for table in GROUP_TABLES:
        assert table in tool.PRODUCT_TABLES and table not in tool.KEEP_TABLES | tool.MIXED_TABLES
    assert {b for _, b in references} <= tool.PRODUCT_TABLES | tool.KEEP_TABLES | tool.MIXED_TABLES
    # and nothing outside PRODUCT references them (that would need CASCADE, which is never used)
    with grouped.engine.connect() as connection:
        incoming = {r for r in connection.execute(text(
            "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'f' "
            "AND confrelid = ANY(ARRAY['public.ar_v3_run_group'::regclass, "
            "'public.ar_v3_run_group_member'::regclass])")).scalars()}
    assert incoming <= tool.PRODUCT_TABLES
