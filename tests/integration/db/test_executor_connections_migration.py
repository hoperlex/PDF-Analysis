"""`EXEC-SEAL-01`: migration ``0030_executor_connections`` -- connections, sealed secrets, probes,
routes and the frozen revision of a run.

Required: a fresh upgrade, an upgrade from a populated ``0029``, a refused downgrade with
retained data, and the downgrade of an empty ``0030`` that restores ``0029``'s guard and
``ck_model_call_cost_basis``. The behavioural tests show each guard failing, not only existing.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ExecutorProbeId,
    ExecutorRouteEventId,
    ExecutorSecretId,
    ProjectUid,
    PromptBundleId,
    RunId,
    UserUid,
    VersionUid,
)
from tests.support.expected_facts import FACTS

ACTOR = f"usr_{'0' * 26}"
THIS = "0030_executor_connections"
PREVIOUS = "0029_routing_refusal_codes"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _connection(connection, *, kind: str = "http_api") -> str:
    connection_id = str(ExecutorConnectionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
        "VALUES (:id, :kind, 'test', :actor)"
    ), {"id": connection_id, "kind": kind, "actor": ACTOR})
    return connection_id


def _revision(connection, connection_id: str, *, number: int = 1) -> str:
    revision_id = str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
        "created_by, pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, "
        "api_flavour, base_url, transport) VALUES (:id, :c, :n, :actor, 'claude-opus-5', "
        "'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', 'https://proxy.test', "
        "'direct')"
    ), {"id": revision_id, "c": connection_id, "n": number, "actor": ACTOR})
    return revision_id


def _secret(connection, connection_id: str, *, purpose: str = "api_key") -> str:
    secret_id = str(ExecutorSecretId.new())
    connection.execute(text(
        "INSERT INTO executor_secret (secret_id, connection_id, purpose, kid, destination, "
        "ciphertext, last4, set_by) VALUES (:id, :c, :p, 'k1', 'direct||https://proxy.test:443', "
        "'\\x0102'::bytea, 'abcd', :actor)"
    ), {"id": secret_id, "c": connection_id, "p": purpose, "actor": ACTOR})
    return secret_id


def _run(connection, *, label: str, revision_id: str | None = None) -> dict[str, str]:
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, :name)"),
                       {**ids, "name": f"executors-{label}"})
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, :title)"), {**ids, "title": label})
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, "
                            "version_ordinal, media_type, byte_size, sha256, page_count) "
                            "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                       {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
        "prompt_bundle_id, provider_mode, frozen_input_digest, connection_revision_id) "
        "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, :revision)"
    ), {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
        "digest": "b" * 64, "revision": revision_id})
    return ids


def test_a_fresh_upgrade_creates_the_tables_the_view_and_the_widened_check(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        assert _head(connection) == FACTS.migration_head
        for table in ("executor_connection", "executor_connection_revision", "executor_secret",
                      "executor_probe", "executor_route_event", "executor_route_current"):
            assert connection.execute(text("SELECT to_regclass(:name)"),
                                      {"name": f"public.{table}"}).scalar_one(), table
        frozen = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger "
            "WHERE tgname = 'trg_audit_run_frozen_guard'"
        )).scalar_one()
        assert "'connection_revision_id'" in frozen and "'norm_retrieval_set_id'" in frozen, frozen
        definition = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_model_call_cost_basis'"
        )).scalar_one()
        assert "unmetered" in definition, definition


def test_a_populated_0029_upgrades_and_its_rows_name_no_revision(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_previous = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_previous.returncode == 0, at_previous.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = {
                "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
                "version": str(VersionUid.new()), "run": str(RunId.new()),
            }
            connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'x')"), ids)
            connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                                    "VALUES (:document, :project, 'x')"), ids)
            connection.execute(text("INSERT INTO document_version (version_uid, document_uid, "
                                    "version_ordinal, media_type, byte_size, sha256, page_count) "
                                    "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                               {**ids, "sha": "a" * 64})
            connection.execute(text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
                "prompt_bundle_id, provider_mode, frozen_input_digest) VALUES (:run, :project, "
                ":version, :profile, :bundle, 'recorded', :digest)"
            ), {**ids, "profile": str(AnalysisProfileId.new()),
                "bundle": str(PromptBundleId.new()), "digest": "b" * 64})
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert _head(connection) == FACTS.migration_head
            assert connection.execute(text(
                "SELECT connection_revision_id FROM audit_run WHERE run_id = :run"
            ), ids).scalar_one() is None
            assert connection.execute(text("SELECT count(*) FROM executor_connection")).scalar_one() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("retained", ["executor_connection", "audit_run.connection_revision_id"])
def test_retained_executor_data_refuses_the_downgrade(
    empty_database, foundation_command, retained: str,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", THIS), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            connection_id = _connection(connection)
            if retained == "audit_run.connection_revision_id":
                _run(connection, label="held", revision_id=_revision(connection, connection_id))
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert f"refusing to downgrade {THIS}" in refused.stderr
        assert retained in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == THIS
    finally:
        engine.dispose()


def test_an_empty_0030_downgrades_and_restores_the_run_guard_and_the_cost_basis_check(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            assert _head(connection) == PREVIOUS
            assert connection.execute(text("SELECT to_regclass('public.executor_connection')")).scalar_one() is None
            frozen = connection.execute(text(
                "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'"
            )).scalar_one()
            assert "connection_revision_id" not in frozen and "norm_retrieval_set_id" in frozen, frozen
            definition = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_model_call_cost_basis'"
            )).scalar_one()
            assert "unmetered" not in definition, definition
    finally:
        engine.dispose()


def test_a_run_never_changes_its_frozen_revision(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id = _connection(connection)
        first = _revision(connection, connection_id, number=1)
        second = _revision(connection, connection_id, number=2)
        ids = _run(connection, label="frozen", revision_id=first)
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                connection.execute(text(
                    "UPDATE audit_run SET connection_revision_id = :revision WHERE run_id = :run"
                ), {**ids, "revision": second})
        assert _sqlstate(refused) == "AM003"
        # The control: a column the guard does not freeze still moves.
        connection.execute(text("UPDATE audit_run SET state = state WHERE run_id = :run"), ids)


def test_a_revision_is_immutable_and_numbered_once(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id = _connection(connection)
        revision_id = _revision(connection, connection_id)
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                connection.execute(text(
                    "UPDATE executor_connection_revision SET base_url = 'https://other.test' "
                    "WHERE revision_id = :id"), {"id": revision_id})
        assert _sqlstate(refused) == "AM003"
        with pytest.raises(DBAPIError) as repeated:
            with connection.begin_nested():
                _revision(connection, connection_id, number=1)
        assert _sqlstate(repeated) == "23505"
        with pytest.raises(DBAPIError) as query:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO executor_connection_revision (revision_id, connection_id, "
                    "revision_no, created_by, pin_id, gateway_model, billing, "
                    "allow_client_documents, timeout_seconds, base_url) VALUES (:id, :c, 9, "
                    ":actor, 'p', 'm', 'metered', false, 60, 'https://x.test/?k=1')"
                ), {"id": str(ExecutorConnectionRevisionId.new()), "c": connection_id, "actor": ACTOR})
        assert _sqlstate(query) == "23514"


def test_a_secret_moves_only_by_being_replaced_once(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id = _connection(connection)
        old = _secret(connection, connection_id)
        for change in ("ciphertext = '\\x03'::bytea", "kid = 'k2'", "destination = 'x'", "last4 = 'zzzz'"):
            with pytest.raises(DBAPIError) as refused:
                with connection.begin_nested():
                    connection.execute(text(f"UPDATE executor_secret SET {change} WHERE secret_id = :id"),
                                       {"id": old})
            assert _sqlstate(refused) == "AM003", change
        with pytest.raises(DBAPIError) as second_current:
            with connection.begin_nested():
                _secret(connection, connection_id)
        assert _sqlstate(second_current) == "23505"
        connection.execute(text("UPDATE executor_secret SET replaced_at = clock_timestamp() "
                                "WHERE secret_id = :id"), {"id": old})
        with pytest.raises(DBAPIError) as again:
            with connection.begin_nested():
                connection.execute(text("UPDATE executor_secret SET replaced_at = NULL WHERE secret_id = :id"),
                                   {"id": old})
        assert _sqlstate(again) == "AM003"
        _secret(connection, connection_id)  # the rotation: a new current row


def test_a_probe_has_a_state_shape_and_a_revision_of_its_own_connection(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        mine, other = _connection(connection), _connection(connection)
        revision_id = _revision(connection, mine)
        probe_id = str(ExecutorProbeId.new())
        connection.execute(text(
            "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, requested_by) "
            "VALUES (:id, :c, :r, 'requested', :actor)"
        ), {"id": probe_id, "c": mine, "r": revision_id, "actor": ACTOR})
        with pytest.raises(DBAPIError) as foreign:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, "
                    "requested_by) VALUES (:id, :c, :r, 'requested', :actor)"
                ), {"id": str(ExecutorProbeId.new()), "c": other, "r": revision_id, "actor": ACTOR})
        assert _sqlstate(foreign) == "23503"
        with pytest.raises(DBAPIError) as unfinished:
            with connection.begin_nested():
                connection.execute(text("UPDATE executor_probe SET state = 'finished' WHERE probe_id = :id"),
                                   {"id": probe_id})
        assert _sqlstate(unfinished) == "23514"
        connection.execute(text(
            "UPDATE executor_probe SET state = 'finished', outcome = 'no_worker', "
            "finished_at = clock_timestamp() WHERE probe_id = :id"), {"id": probe_id})
        with pytest.raises(DBAPIError) as moved:
            with connection.begin_nested():
                connection.execute(text("UPDATE executor_probe SET revision_id = revision_id, "
                                        "requested_by = :other WHERE probe_id = :id"),
                                   {"id": probe_id, "other": str(UserUid.new())})
        assert _sqlstate(moved) == "AM003"


def test_the_route_is_append_only_and_the_view_is_its_latest_event(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        primary, standby = _connection(connection), _connection(connection)

        def route(number: int, p: str, s: str | None) -> str:
            event_id = str(ExecutorRouteEventId.new())
            connection.execute(text(
                "INSERT INTO executor_route_event (route_event_id, work_kind, route_no, "
                "primary_connection_id, standby_connection_id, set_by) "
                "VALUES (:id, 'text_analysis', :n, :p, :s, :actor)"
            ), {"id": event_id, "n": number, "p": p, "s": s, "actor": ACTOR})
            return event_id

        first = route(1, primary, None)
        last = route(2, standby, primary)
        current = connection.execute(text(
            "SELECT route_event_id, primary_connection_id, standby_connection_id "
            "FROM executor_route_current WHERE work_kind = 'text_analysis'")).one()
        assert current == (last, standby, primary)
        for statement in ("UPDATE executor_route_event SET set_by = set_by",
                          "DELETE FROM executor_route_event"):
            with pytest.raises(DBAPIError) as refused:
                with connection.begin_nested():
                    connection.execute(text(statement + " WHERE route_event_id = :id"), {"id": first})
            assert _sqlstate(refused) == "AM002", statement  # am_append_only
        with pytest.raises(DBAPIError) as same:
            with connection.begin_nested():
                route(3, primary, primary)
        assert _sqlstate(same) == "23514"


def test_an_unmetered_call_and_a_revision_travel_together_or_not_at_all(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        revision_id = _revision(connection, _connection(connection))
        ids = _run(connection, label="calls", revision_id=revision_id)

        def call(**columns: str | None) -> None:
            connection.execute(text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, "
                "provider_mode, request_sha256, response_sha256, status, cost_micros, cost_basis, "
                "connection_revision_id, identity_basis) VALUES (:call, :run, 'text_analysis', "
                "'anthropic', 'claude-opus-5', 'live', :sha, :sha, 'succeeded', NULL, :basis, "
                ":revision, :identity)"
            ), {"call": f"mc_{str(RunId.new())[4:]}", "run": ids["run"], "sha": "c" * 64,
                "basis": columns.get("basis", "unmetered"), "revision": columns.get("revision"),
                "identity": columns.get("identity")})

        call(revision=revision_id, identity="declared")
        with pytest.raises(DBAPIError) as half:
            with connection.begin_nested():
                call(revision=revision_id, identity=None)
        assert _sqlstate(half) == "23514"
        with pytest.raises(DBAPIError) as bad_basis:
            with connection.begin_nested():
                call(revision=revision_id, identity="claimed")
        assert _sqlstate(bad_basis) == "23514"
        with pytest.raises(DBAPIError) as bad_cost:
            with connection.begin_nested():
                call(basis="free", revision=None, identity=None)
        assert _sqlstate(bad_cost) == "23514"
