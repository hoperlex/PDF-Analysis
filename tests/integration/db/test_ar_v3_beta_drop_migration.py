"""`AR-V3-BE-RM-01`: ``0063_drop_ar_v3_beta`` drops the six-scope АР beta from a database that served it (rulings `R-154a`, `R-154c`).

The beta lived in three revisions: ``0032`` (two tables, three triggers, one function), ``0033`` (its stage id in
``ck_stage_result_stage_id``) and ``0036`` (its CITE stage in ``am_verify_norm_citation_partition()``). ``0063`` takes all three back. Claims, each
against a real PostgreSQL server:

* **the upgrade removes exactly the beta** -- the tables, the triggers and ``am_ar_v3_group_complete()`` are gone, the stage CHECK reads the nine ids of
  ``0002`` again, and the partition function is ``0036``'s body with its stage test narrowed to ``0023``'s (read back from the database, not from the
  migration's own constant);
* **it refuses while any row of the beta exists**, naming the counts, and a refusal changes nothing (the version, the tables and the CHECK stay);
* **the downgrade recreates the previous head exactly** -- a digest of every column, constraint, trigger and function definition of the beta and of the two
  restored objects, taken at ``0062``, equals the one taken after ``0063`` up and down, and the upgrade then runs again;
* **the vocabulary is tied** -- the profile and bundle ids the refusal counts are the ones the beta pinned, written out here.
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine

THIS = "0063_drop_ar_v3_beta"
PREVIOUS = "0062_hosts_stage_models"
CITE = "ar_v3_citation_review"
#: The nine stages ``0002`` admitted, written out here and not imported from the migration.
NINE = (
    "source_preparation", "page_geometry_extraction", "document_context_build", "text_analysis", "block_analysis",
    "finding_merge", "finding_review", "finding_correction", "norm_verification",
)
PROFILE = "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
BUNDLE = "pb_01M5M28ZCDVCR37BX1884JGSPM"
TABLES = ("ar_v3_run_group", "ar_v3_run_group_member")
FUNCTION = "am_ar_v3_group_complete"
PARTITION_FUNCTION = "am_verify_norm_citation_partition"
OLD_TEST = "st.stage_id = 'norm_verification'"
WIDE_TEST = "st.stage_id IN ('norm_verification', 'ar_v3_citation_review')"
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _upgrade(foundation_command: Any, database: DatabaseSettings, revision: str) -> Any:
    return foundation_command(_alembic("upgrade", revision), database.url.render_as_string(hide_password=False))


def _downgrade(foundation_command: Any, database: DatabaseSettings, revision: str) -> Any:
    return foundation_command(_alembic("downgrade", revision), database.url.render_as_string(hide_password=False))


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _uid(prefix: str) -> str:
    return prefix + "_" + "".join(random.choices(ALPHABET, k=26))


def _tables(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return [row[0] for row in connection.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'ar\\_v3\\_%' ORDER BY 1"))]


def _function_exists(engine: Engine, name: str = FUNCTION) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = :n)"), {"n": name}).scalar_one())


def _partition_source(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT prosrc FROM pg_proc WHERE proname = :n"), {"n": PARTITION_FUNCTION}).scalar_one()


def _stage_vocabulary(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        definition = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_stage_result_stage_id'")).scalar_one()
    return re.findall(r"'([a-z_0-9]+)'::text", definition)


def _digest(engine: Engine) -> str:
    """One digest of every definition the beta touched: the columns, constraints, indexes and triggers of its two tables, its function, the stage
    CHECK and the partition function. A table or a function that does not exist contributes nothing."""
    parts: list[str] = []
    with engine.connect() as connection:
        for table in TABLES:
            parts += [f"column {table} {row[0]} {row[1]} {row[2]} {row[3]} {row[4]}" for row in connection.execute(text(
                "SELECT ordinal_position, column_name, data_type, is_nullable, coalesce(column_default, '') "
                "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :t ORDER BY 1"), {"t": table})]
            parts += [f"constraint {table} {row[0]} {row[1]}" for row in connection.execute(text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = to_regclass(:t) ORDER BY 1"), {"t": table})]
            parts += [f"index {row[0]} {row[1]}" for row in connection.execute(text(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :t ORDER BY 1"), {"t": table})]
            parts += [f"trigger {row[0]} {row[1]}" for row in connection.execute(text(
                "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid = to_regclass(:t) AND NOT tgisinternal ORDER BY 1"), {"t": table})]
        parts += [f"function {row[0]} {row[1]}" for row in connection.execute(text(
            "SELECT proname, pg_get_functiondef(oid) FROM pg_proc WHERE proname IN (:a, :b) ORDER BY 1"),
            {"a": FUNCTION, "b": PARTITION_FUNCTION})]
        parts.append("check " + connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_stage_result_stage_id'")).scalar_one())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _project_and_version(connection: Connection) -> tuple[str, str, str]:
    project, document, version = _uid("prj"), _uid("doc"), _uid("ver")
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'beta drop')"), {"p": project})
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'doc')"), {"d": document, "p": project})
    connection.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:v, :d, 1, 'application/pdf', 1, :h, 1)"), {"v": version, "d": document, "h": "a" * 64})
    return project, document, version


def _run(connection: Connection, *, profile: str, bundle: str) -> str:
    project, _, version = _project_and_version(connection)
    run = _uid("run")
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "frozen_input_digest) VALUES (:r, :p, :v, :ap, :pb, 'recorded', :h)"),
        {"r": run, "p": project, "v": version, "ap": profile, "pb": bundle, "h": "b" * 64})
    return run


def _seed_stage(connection: Connection) -> None:
    run = _run(connection, profile=_uid("ap"), bundle=_uid("pb"))
    connection.execute(text(
        "INSERT INTO stage_result (run_id, stage_id, stage_version, status, started_at, finished_at) "
        "VALUES (:r, :s, '1.0.0', 'succeeded', now(), now())"), {"r": run, "s": CITE})


def _seed_command(connection: Connection) -> None:
    connection.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
        "VALUES (:c, 'start_ar_v3_beta_group', :k, :f)"),
        {"c": _uid("cmd"), "k": "key-" + _uid("k"), "f": "c" * 64})


def _seed_pinned_run(connection: Connection) -> None:
    _run(connection, profile=PROFILE, bundle=BUNDLE)


def _seed_group(connection: Connection) -> None:
    """One group row, written with the triggers off: the deferred check of six members is not what this test is about."""
    project, _, version = _project_and_version(connection)
    connection.execute(text("SET LOCAL session_replication_role = replica"))
    connection.execute(text(
        "INSERT INTO ar_v3_run_group (group_id, project_uid, version_uid, command_id, norms_snapshot_id, analysis_profile_id, prompt_bundle_id, "
        "pack_sha256, composition_sha256, policy_sha256, provider_mode) VALUES (:g, :p, :v, :c, :n, :ap, :pb, :h, :h, :h, 'recorded')"),
        {"g": _uid("arg"), "p": project, "v": version, "c": _uid("cmd"), "n": _uid("ns"), "ap": PROFILE, "pb": BUNDLE, "h": "d" * 64})


def test_the_migration_is_chained_after_0062_and_names_the_beta_it_counts() -> None:
    from pathlib import Path
    import importlib.util

    path = Path(__file__).resolve().parents[3] / "db" / "migrations" / "versions" / "20261110_0063_drop_ar_v3_beta.py"
    spec = importlib.util.spec_from_file_location("drop_ar_v3_beta_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (module.revision, module.down_revision) == (THIS, PREVIOUS)
    assert (module._PROFILE_ID, module._BUNDLE_ID, module._CITE_STAGE_ID) == (PROFILE, BUNDLE, CITE)
    assert module._REGISTRY_STAGE_IDS == NINE and module._WITH_CITE_STAGE_IDS == (*NINE, CITE)
    assert module._STAGE_TEST_0023 == OLD_TEST and module._STAGE_TEST_0036 == WIDE_TEST


def test_the_upgrade_removes_exactly_the_beta_and_restores_the_two_older_objects(
    empty_database: DatabaseSettings, foundation_command: Any,
) -> None:
    assert _upgrade(foundation_command, empty_database, PREVIOUS).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        assert _tables(engine) == list(TABLES) and _function_exists(engine)
        assert _stage_vocabulary(engine) == [*NINE, CITE]
        wide = _partition_source(engine)
        assert wide.count(WIDE_TEST) == 1 and OLD_TEST not in wide
        result = _upgrade(foundation_command, empty_database, THIS)
        assert result.returncode == 0, result.describe()
        assert _version(engine) == THIS
        assert _tables(engine) == [] and not _function_exists(engine)
        assert _stage_vocabulary(engine) == list(NINE)
        assert _partition_source(engine) == wide.replace(WIDE_TEST, OLD_TEST), "0023's body: only the stage test moved back"
        with engine.connect() as connection:
            assert connection.execute(text(
                "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'trg\\_ar\\_v3\\_%'")).scalar_one() == 0
            assert connection.execute(text(
                "SELECT count(*) FROM pg_trigger WHERE tgname IN ('trg_finding_observation_partition', 'trg_norm_citation_partition')")
            ).scalar_one() == 2, "the two partition triggers keep their names"
    finally:
        engine.dispose()


@pytest.mark.parametrize("seed,expected", [
    (_seed_stage, "1 stage_result named ar_v3_citation_review"),
    (_seed_command, "1 command_record of type start_ar_v3_beta_group"),
    (_seed_pinned_run, "1 audit_run of the beta's profile and bundle"),
    (_seed_group, "1 ar_v3_run_group row"),
])
def test_the_upgrade_is_refused_while_a_row_of_the_beta_exists_and_a_refusal_changes_nothing(
    empty_database: DatabaseSettings, foundation_command: Any, seed: Any, expected: str,
) -> None:
    assert _upgrade(foundation_command, empty_database, PREVIOUS).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            seed(connection)
        before = _digest(engine)
        refused = _upgrade(foundation_command, empty_database, THIS)
        assert refused.returncode != 0, refused.describe()
        assert "0063 upgrade refused" in refused.stderr and expected in refused.stderr, refused.stderr
        assert _version(engine) == PREVIOUS and _tables(engine) == list(TABLES) and _digest(engine) == before
    finally:
        engine.dispose()


def test_a_model_call_or_effect_that_carries_an_ar_v3_parameter_blocks_the_upgrade_too(
    empty_database: DatabaseSettings, foundation_command: Any,
) -> None:
    """The refusal reads the ``parameters`` of the journal, not only the run: a key that starts with ``ar_v3_`` is a row of the beta."""
    assert _upgrade(foundation_command, empty_database, PREVIOUS).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            statements = [row[0] for row in connection.execute(text(
                "SELECT 'SELECT count(*) FROM ' || table_name || ' WHERE EXISTS (SELECT 1 FROM jsonb_object_keys(parameters) AS key "
                "WHERE key LIKE ''ar\\_v3\\_%'')' FROM information_schema.columns WHERE table_schema = 'public' AND column_name = 'parameters' "
                "AND table_name IN ('model_call', 'provider_call_effect') ORDER BY 1"))]
            assert len(statements) == 2, "both journals carry a parameters column the refusal reads"
            assert [connection.execute(text(statement)).scalar_one() for statement in statements] == [0, 0]
    finally:
        engine.dispose()


def test_the_downgrade_recreates_the_previous_head_exactly_and_the_upgrade_runs_again(
    empty_database: DatabaseSettings, foundation_command: Any,
) -> None:
    assert _upgrade(foundation_command, empty_database, PREVIOUS).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        at_0062 = _digest(engine)
        assert _upgrade(foundation_command, empty_database, THIS).returncode == 0
        at_0063 = _digest(engine)
        assert at_0063 != at_0062, "the digest does see the beta"
        down = _downgrade(foundation_command, empty_database, PREVIOUS)
        assert down.returncode == 0, down.describe()
        assert _version(engine) == PREVIOUS
        assert _digest(engine) == at_0062, "digest-equal to the head the migration took the beta from"
        assert _upgrade(foundation_command, empty_database, THIS).returncode == 0
        assert _digest(engine) == at_0063
    finally:
        engine.dispose()
