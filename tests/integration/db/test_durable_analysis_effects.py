"""The 0014 authority/effect schema is closed, guarded and reversibly installable."""

from __future__ import annotations

from sqlalchemy import text

from auditmanager.shared.db.migrations import head_revision
from auditmanager.shared.errors import ErrorCode


NEW_TABLES = {
    "job",
    "attempt",
    "lease",
    "provider_call_effect",
    "analysis_artifact_publication",
}

JOB_EDGES = {
    (None, "queued"),
    ("queued", "leased"),
    ("queued", "cancelled"),
    ("leased", "running"),
    ("leased", "queued"),
    ("leased", "failed"),
    ("leased", "cancelled"),
    ("running", "succeeded"),
    ("running", "retry_wait"),
    ("running", "failed"),
    ("running", "cancelled"),
    ("retry_wait", "queued"),
    ("retry_wait", "dead_letter"),
    ("retry_wait", "cancelled"),
}

ATTEMPT_EDGES = {
    (None, "created"),
    ("created", "leased"),
    ("created", "cancelled"),
    ("leased", "running"),
    ("leased", "superseded"),
    ("leased", "lost"),
    ("leased", "failed"),
    ("leased", "cancelled"),
    ("running", "succeeded"),
    ("running", "failed"),
    ("running", "superseded"),
    ("running", "lost"),
    ("running", "cancelled"),
}


def test_0014_creates_exactly_the_owned_relations_and_topologies(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        present = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = ANY(:names)"
                ),
                {"names": sorted(NEW_TABLES)},
            )
        }
        rows = connection.execute(
            text(
                "SELECT machine, from_state, to_state FROM contract_state_transition "
                "WHERE machine IN ('job', 'attempt')"
            )
        ).all()

    assert present == NEW_TABLES
    assert {(origin, target) for machine, origin, target in rows if machine == "job"} == JOB_EDGES
    assert {
        (origin, target) for machine, origin, target in rows if machine == "attempt"
    } == ATTEMPT_EDGES


def test_every_new_mutable_state_is_trigger_guarded(migrated_engine) -> None:
    expected = {
        "job": {"trg_job_state_guard", "trg_job_frozen_guard"},
        "attempt": {"trg_attempt_state_guard", "trg_attempt_frozen_guard"},
        "lease": {"trg_lease_frozen_guard"},
        "provider_call_effect": {
            "trg_provider_call_effect_state_guard",
            "trg_provider_call_effect_frozen_guard",
        },
        "analysis_artifact_publication": {
            "trg_analysis_artifact_state_guard",
            "trg_analysis_artifact_frozen_guard",
        },
    }
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, t.tgname FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND NOT t.tgisinternal "
                "AND c.relname = ANY(:names)"
            ),
            {"names": sorted(expected)},
        ).all()
    actual = {table: set() for table in expected}
    for table, trigger in rows:
        actual[table].add(trigger)
    assert actual == expected


def test_authority_tuple_foreign_keys_cannot_be_cross_wired(migrated_engine) -> None:
    expected = {
        "fk_job_current_attempt_belongs_to_job",
        "fk_lease_attempt_belongs_to_job",
        "fk_provider_effect_job_belongs_to_run",
        "fk_provider_effect_attempt_belongs_to_job",
        "fk_provider_effect_final_call_belongs_to_run",
        "fk_analysis_artifact_job_belongs_to_run",
        "fk_analysis_artifact_attempt_belongs_to_job",
    }
    with migrated_engine.connect() as connection:
        present = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'f' AND conname = ANY(:names)"
                ),
                {"names": sorted(expected)},
            )
        }
    assert present == expected


def test_final_model_call_is_composite_bound_to_the_effect_run(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        foreign_key = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'provider_call_effect' "
                "AND c.conname = 'fk_provider_effect_final_call_belongs_to_run'"
            )
        ).scalar_one()
        unique = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'model_call' "
                "AND c.conname = 'uq_model_call_run_call'"
            )
        ).scalar_one()

    assert "FOREIGN KEY (run_id, final_model_call_id)" in foreign_key
    assert "REFERENCES model_call(run_id, model_call_id)" in foreign_key
    assert unique == "UNIQUE (run_id, model_call_id)"


def test_analysis_upload_handle_is_opaque_unique_and_frozen(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        check = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'analysis_artifact_publication' "
                "AND c.conname = 'ck_analysis_artifact_upload_token'"
            )
        ).scalar_one()
        unique = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'analysis_artifact_publication' "
                "AND c.conname = 'uq_analysis_artifact_upload_token'"
            )
        ).scalar_one()
        frozen = connection.execute(
            text(
                "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = 'analysis_artifact_publication' "
                "AND t.tgname = 'trg_analysis_artifact_frozen_guard'"
            )
        ).scalar_one()

    assert "upload_token" in check
    assert unique == "UNIQUE (upload_token)"
    assert "am_guard_frozen_columns" in frozen
    assert "upload_token" in frozen


def test_provider_effect_error_code_is_the_closed_catalog(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'provider_call_effect' "
                "AND c.conname = 'ck_provider_effect_error_code'"
            )
        ).scalar_one()
    for code in ErrorCode:
        assert f"'{code.value}'" in definition
    assert definition.count("::text") == len(ErrorCode), definition


def test_empty_0014_downgrades_to_0013_and_upgrades_back(
    migrated_database, migrated_engine, foundation_command, migrate_argv
) -> None:
    url = migrated_database.url.render_as_string(hide_password=False)
    downgrade = [
        ".venv/bin/python",
        "-m",
        "alembic",
        "--config",
        "db/migrations/alembic.ini",
        "downgrade",
        "0013_norm_embeddings",
    ]
    result = foundation_command(downgrade, url)
    assert result.returncode == 0, result.describe()

    with migrated_engine.connect() as connection:
        remaining = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = ANY(:names)"
                ),
                {"names": sorted(NEW_TABLES)},
            )
        }
        stamped = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    assert remaining == set()
    assert stamped == "0013_norm_embeddings"

    restored = foundation_command(migrate_argv, url)
    assert restored.returncode == 0, restored.describe()
    with migrated_engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == head_revision()
