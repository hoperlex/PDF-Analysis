"""The 0014 authority/effect schema is closed, guarded and reversibly installable."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.migrations import head_revision
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    DocumentUid,
    JobId,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    clear_the_role_backfill,
)


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


def _seed_run(connection, *, label: str) -> dict[str, str]:
    identities = {
        "project_uid": str(ProjectUid.new()),
        "document_uid": str(DocumentUid.new()),
        "version_uid": str(VersionUid.new()),
        "run_id": str(RunId.new()),
    }
    connection.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project_uid, :name)"),
        {**identities, "name": f"durable-{label}"},
    )
    connection.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:document_uid, :project_uid, :title)"
        ),
        {**identities, "title": f"durable-{label}"},
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:version_uid, :document_uid, 1, 'application/pdf', 1, :sha256, 1)"
        ),
        {**identities, "sha256": "a" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, "
            "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:run_id, :project_uid, :version_uid, :profile_id, :bundle_id, "
            "'recorded', :digest)"
        ),
        {
            **identities,
            "profile_id": str(AnalysisProfileId.new()),
            "bundle_id": str(PromptBundleId.new()),
            "digest": "b" * 64,
        },
    )
    return identities


def _assert_database_refusal(error: pytest.ExceptionInfo[DBAPIError], *, sqlstate: str) -> None:
    assert getattr(error.value.orig, "sqlstate", None) == sqlstate


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


def test_cross_run_final_model_call_insert_is_refused_by_the_composite_fk(
    migrated_engine,
) -> None:
    with migrated_engine.begin() as connection:
        owner = _seed_run(connection, label="owner")
        foreign = _seed_run(connection, label="foreign")
        job_id = str(JobId.new())
        attempt_id = str(AttemptId.new())
        connection.execute(
            text("INSERT INTO job (job_id, run_id) VALUES (:job_id, :run_id)"),
            {"job_id": job_id, "run_id": owner["run_id"]},
        )
        connection.execute(
            text(
                "INSERT INTO attempt (attempt_id, job_id, execution_token) "
                "VALUES (:attempt_id, :job_id, 'test-token')"
            ),
            {"attempt_id": attempt_id, "job_id": job_id},
        )
        foreign_call_id = str(ModelCallId.new())
        connection.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, request_sha256, response_sha256, "
                "input_tokens, output_tokens, latency_ms, cost_micros, status) "
                "VALUES (:call_id, :run_id, 'text_analysis', 'anthropic', 'a-model', "
                "'recorded', :request_sha, :response_sha, 1, 1, 1, 0, 'succeeded')"
            ),
            {
                "call_id": foreign_call_id,
                "run_id": foreign["run_id"],
                "request_sha": "c" * 64,
                "response_sha": "d" * 64,
            },
        )

        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, "
                        "attempt_id, stage_id, provider, model_identity, provider_mode, "
                        "parameters, request_sha256, state, response_sha256, input_tokens, "
                        "output_tokens, latency_ms, final_model_call_id) "
                        "VALUES (:effect_id, :run_id, :job_id, :attempt_id, "
                        "'text_analysis', 'anthropic', 'a-model', 'recorded', '{}'::jsonb, "
                        ":request_sha, 'completed', :response_sha, 1, 1, 1, :foreign_call_id)"
                    ),
                    {
                        "effect_id": foreign_call_id,
                        "run_id": owner["run_id"],
                        "job_id": job_id,
                        "attempt_id": attempt_id,
                        "request_sha": "e" * 64,
                        "response_sha": "f" * 64,
                        "foreign_call_id": foreign_call_id,
                    },
                )
        _assert_database_refusal(refused, sqlstate="23503")
        assert (
            getattr(getattr(refused.value.orig, "diag", None), "constraint_name", None)
            == "fk_provider_effect_final_call_belongs_to_run"
        )


def test_invalid_initial_job_and_attempt_states_are_refused_by_the_trigger(
    migrated_engine,
) -> None:
    with migrated_engine.begin() as connection:
        seeded = _seed_run(connection, label="initial-state")
        with pytest.raises(DBAPIError) as job_refused:
            with connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO job (job_id, run_id, state) "
                        "VALUES (:job_id, :run_id, 'running')"
                    ),
                    {"job_id": str(JobId.new()), "run_id": seeded["run_id"]},
                )
        _assert_database_refusal(job_refused, sqlstate="AM001")

        job_id = str(JobId.new())
        connection.execute(
            text("INSERT INTO job (job_id, run_id) VALUES (:job_id, :run_id)"),
            {"job_id": job_id, "run_id": seeded["run_id"]},
        )
        with pytest.raises(DBAPIError) as attempt_refused:
            with connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO attempt (attempt_id, job_id, state, execution_token) "
                        "VALUES (:attempt_id, :job_id, 'running', 'invalid-initial-state')"
                    ),
                    {"attempt_id": str(AttemptId.new()), "job_id": job_id},
                )
        _assert_database_refusal(attempt_refused, sqlstate="AM001")


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


#: Catalog codes the application never stores, so no CHECK admits them. `rate_limited`
#: (`W49-SEAL-01`, the integrator's decision on the seal's stop report) is answered only by
#: the edge in front of ``/api/v1``; no provider call can end with it, and widening this
#: CHECK would need a migration for a value nothing writes. The same named exception as
#: ``tests/contract/domain_p02/test_contract_vocabulary.py::EDGE_ONLY_CODES``.
EDGE_ONLY_CODES: frozenset[str] = frozenset({"rate_limited"})


def test_provider_effect_error_code_is_the_closed_catalog(migrated_engine) -> None:
    """The CHECK admits every stored catalog code, and the edge-only ones it must not.

    Both halves are asserted: an edge-only code that the CHECK admitted would be a widened
    schema, and a stored code put into ``EDGE_ONLY_CODES`` would make the loop skip a code
    the database must admit -- which the exact count below then reports.
    """
    with migrated_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'provider_call_effect' "
                "AND c.conname = 'ck_provider_effect_error_code'"
            )
        ).scalar_one()
    assert EDGE_ONLY_CODES <= {code.value for code in ErrorCode}, sorted(EDGE_ONLY_CODES)
    stored = [code for code in ErrorCode if code.value not in EDGE_ONLY_CODES]
    for code in stored:
        assert f"'{code.value}'" in definition
    for value in sorted(EDGE_ONLY_CODES):
        assert f"'{value}'" not in definition, (value, definition)
    assert definition.count("::text") == len(stored), definition


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
    # `0015` refuses its own downgrade while its role backfill is there; this test is about an
    # earlier revision, so that backfill is removed first (conftest.clear_the_role_backfill).
    clear_the_role_backfill(url)
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


def test_occupied_0014_downgrade_refuses_without_moving_the_head(
    migrated_database, migrated_engine, foundation_command
) -> None:
    url = migrated_database.url.render_as_string(hide_password=False)
    # Reach the revision under test while the later W53 schema is empty. A Job
    # inserted before this step would correctly stop at 0017's own refusal.
    clear_the_role_backfill(url)
    to_0014 = foundation_command(
        [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini",
         "downgrade", "0014_durable_analysis_effects"], url
    )
    assert to_0014.returncode == 0, to_0014.describe()
    with migrated_engine.begin() as connection:
        seeded = _seed_run(connection, label="occupied-downgrade")
        connection.execute(
            text("INSERT INTO job (job_id, run_id) VALUES (:job_id, :run_id)"),
            {"job_id": str(JobId.new()), "run_id": seeded["run_id"]},
        )

    result = foundation_command(
        [
            ".venv/bin/python",
            "-m",
            "alembic",
            "--config",
            "db/migrations/alembic.ini",
            "downgrade",
            "0013_norm_embeddings",
        ],
        url,
    )
    assert result.returncode != 0
    assert "downgrade refused: durable execution evidence would be discarded" in (
        result.stdout + result.stderr
    )
    assert "job=1" in (result.stdout + result.stderr)
    with migrated_engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0014_durable_analysis_effects"
        assert connection.execute(text("SELECT count(*) FROM job")).scalar_one() == 1
