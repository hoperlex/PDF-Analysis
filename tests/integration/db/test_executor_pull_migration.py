"""`EXEC-PULL-01`: migration ``0031_executor_pull_channel`` -- runner tokens and executor tasks.

Required: a fresh upgrade, a refused downgrade with retained data, the downgrade of an empty
``0031`` that leaves ``0030`` as it was. The behavioural tests show each guard failing, not only
existing: the hash length, the one-way revoke, the frozen identity of a token and of a task, the
shapes a task's state may take, and a token that cannot claim another connection's task.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId, AttemptId, DocumentUid, ExecutorConnectionId, ExecutorConnectionRevisionId,
    ExecutorProbeId, ExecutorRunnerTokenId, ExecutorTaskId, JobId, ProjectUid, PromptBundleId,
    RunId, VersionUid,
)
from tests.support.expected_facts import FACTS

ACTOR = f"usr_{'0' * 26}"
THIS = "0031_executor_pull_channel"
PREVIOUS = "0030_executor_connections"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _connection(connection) -> tuple[str, str]:
    connection_id, revision_id = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
        "VALUES (:id, 'pull', 'test', :actor)"), {"id": connection_id, "actor": ACTOR})
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, "
        "created_by, pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, "
        "pull_client, answer_deadline_seconds, max_claimed_tasks) VALUES (:r, :c, 1, :actor, "
        "'claude-opus-5', 'claude-opus-5', 'not_metered', false, 60, 'claude_code_session', 60, 1)"
    ), {"r": revision_id, "c": connection_id, "actor": ACTOR})
    return connection_id, revision_id


def _token(connection, connection_id: str, *, prefix: str | None = None, digest: bytes | None = None,
           created: str = "now()", expires: str = "now() + interval '30 days'") -> str:
    token_id = str(ExecutorRunnerTokenId.new())
    connection.execute(text(
        "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, "
        f"created_at, created_by, expires_at) VALUES (:id, :c, :p, :h, {created}, :actor, {expires})"
    ), {"id": token_id, "c": connection_id, "p": prefix or f"amr_{token_id[-8:].lower()}",
        "h": digest or os.urandom(32), "actor": ACTOR})
    return token_id


def _probe(connection, connection_id: str, revision_id: str) -> str:
    probe_id = str(ExecutorProbeId.new())
    connection.execute(text(
        "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, requested_by) "
        "VALUES (:id, :c, :r, 'requested', :actor)"),
        {"id": probe_id, "c": connection_id, "r": revision_id, "actor": ACTOR})
    return probe_id


def _attempt(connection) -> tuple[str, str]:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new()), "job": str(JobId.new()),
           "attempt": str(AttemptId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'p')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'p')"), ids)
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                            "media_type, byte_size, sha256, page_count) VALUES (:version, :document, "
                            "1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
        "prompt_bundle_id, provider_mode, frozen_input_digest) VALUES (:run, :project, :version, "
        ":profile, :bundle, 'live', :digest)"
    ), {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
        "digest": "b" * 64})
    connection.execute(text("INSERT INTO job (job_id, run_id) VALUES (:job, :run)"), ids)
    connection.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) "
                            "VALUES (:attempt, :job, :token)"), {**ids, "token": f"t-{ids['attempt']}"})
    return ids["run"], ids["attempt"]


_PAYLOAD = "CAST('{\"system\": \"s\", \"user_text\": \"u\", \"output_schema\": {}}' AS jsonb)"


def _task(connection, connection_id: str, revision_id: str, *, probe_id: str | None = None,
          run_id: str | None = None, attempt_id: str | None = None, origin: str | None = None,
          state: str = "open", extra: str = "", values: str = "", deadline: str = "now() + interval '1 minute'",
          payload: str = _PAYLOAD) -> str:
    task_id = str(ExecutorTaskId.new())
    connection.execute(text(
        "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, run_id, attempt_id, "
        f"probe_id, state, expected_model, payload, deadline_at{extra}) VALUES (:id, :c, :r, :origin, "
        f":run, :attempt, :probe, :state, 'claude-opus-5', {payload}, {deadline}{values})"
    ), {"id": task_id, "c": connection_id, "r": revision_id,
        "origin": origin or ("probe" if probe_id else "run_call"), "run": run_id,
        "attempt": attempt_id, "probe": probe_id, "state": state})
    return task_id


def _refused(connection, statement: str, params: dict, sqlstate: str, why: str) -> None:
    with pytest.raises(DBAPIError) as raised:
        with connection.begin_nested():
            connection.execute(text(statement), params)
    assert _sqlstate(raised) == sqlstate, (why, _sqlstate(raised))


def test_a_fresh_upgrade_creates_the_two_tables(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert _head(connection) == FACTS.migration_head == THIS
        for table in ("executor_runner_token", "executor_task"):
            assert connection.execute(text("SELECT to_regclass(:n)"),
                                      {"n": f"public.{table}"}).scalar_one(), table


@pytest.mark.parametrize("retained", ["executor_runner_token", "executor_task"])
def test_retained_pull_data_refuses_the_downgrade(empty_database, foundation_command, retained) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    assert foundation_command(_alembic("upgrade", THIS), url).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            connection_id, revision_id = _connection(connection)
            if retained == "executor_runner_token":
                _token(connection, connection_id)
            else:
                _task(connection, connection_id, revision_id,
                      probe_id=_probe(connection, connection_id, revision_id))
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert f"refusing to downgrade {THIS}" in refused.stderr and retained in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == THIS
    finally:
        engine.dispose()


def test_an_empty_0031_downgrades_to_0030_and_upgrades_again(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    assert foundation_command(_alembic("upgrade", "head"), url).returncode == 0
    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            assert _head(connection) == PREVIOUS
            for table in ("executor_runner_token", "executor_task"):
                assert connection.execute(text("SELECT to_regclass(:n)"),
                                          {"n": f"public.{table}"}).scalar_one() is None
            assert connection.execute(text("SELECT to_regclass('public.executor_connection')")).scalar_one()
    finally:
        engine.dispose()
    assert foundation_command(_alembic("upgrade", "head"), url).returncode == 0


def test_a_token_stores_a_32_byte_hash_a_shown_prefix_and_a_real_lifetime(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, _ = _connection(connection)
        _token(connection, connection_id, prefix="amr_abcdefgh", digest=b"\x01" * 32)
        for why, kwargs in (
            ("a hash that is not 32 bytes", {"digest": b"\x01" * 31}),
            ("a prefix of the wrong shape", {"prefix": "amr_ABCDEFGH"}),
            ("a prefix that is too short", {"prefix": "amr_abc"}),
            ("an expiry before the creation", {"expires": "now() - interval '1 day'"}),
        ):
            with pytest.raises(DBAPIError) as raised:
                with connection.begin_nested():
                    _token(connection, connection_id, **kwargs)
            assert _sqlstate(raised) == "23514", why
        for why, kwargs in (("the same prefix", {"prefix": "amr_abcdefgh", "digest": b"\x02" * 32}),
                            ("the same hash", {"prefix": "amr_zzzzzzzz", "digest": b"\x01" * 32})):
            with pytest.raises(DBAPIError) as raised:
                with connection.begin_nested():
                    _token(connection, connection_id, **kwargs)
            assert _sqlstate(raised) == "23505", why


def test_a_token_is_frozen_and_is_revoked_once_and_for_good(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, _ = _connection(connection)
        token_id = _token(connection, connection_id)
        for change in ("token_hash = '\\x00'::bytea", "token_prefix = 'amr_aaaaaaaa'",
                       "expires_at = expires_at + interval '1 day'", "connection_id = connection_id || 'x'"):
            _refused(connection, f"UPDATE executor_runner_token SET {change} WHERE token_id = :id",
                     {"id": token_id}, "AM003", change)
        # The control: what moves still moves.
        connection.execute(text("UPDATE executor_runner_token SET last_seen_at = clock_timestamp(), "
                                "last_seen_address = '203.0.113.9' WHERE token_id = :id"), {"id": token_id})
        _refused(connection, "UPDATE executor_runner_token SET revoked_at = clock_timestamp() "
                             "WHERE token_id = :id", {"id": token_id}, "23514", "revoked_at without revoked_by")
        connection.execute(text("UPDATE executor_runner_token SET revoked_at = clock_timestamp(), "
                                "revoked_by = :a WHERE token_id = :id"), {"id": token_id, "a": ACTOR})
        _refused(connection, "UPDATE executor_runner_token SET revoked_at = NULL, revoked_by = NULL "
                             "WHERE token_id = :id", {"id": token_id}, "AM003", "un-revoking")


def test_a_task_has_the_origin_shape_its_kind_requires(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, revision_id = _connection(connection)
        run_id, attempt_id = _attempt(connection)
        probe_id = _probe(connection, connection_id, revision_id)
        _task(connection, connection_id, revision_id, run_id=run_id, attempt_id=attempt_id)
        _task(connection, connection_id, revision_id, probe_id=probe_id)
        for why, kwargs in (
            ("a run call without an attempt", {"run_id": run_id}),
            ("a run call with a probe", {"run_id": run_id, "attempt_id": attempt_id, "probe_id": probe_id,
                                          "origin": "run_call"}),
            ("a probe with a run", {"probe_id": probe_id, "run_id": run_id}),
            ("an unknown origin", {"run_id": run_id, "attempt_id": attempt_id, "origin": "other"}),
        ):
            with pytest.raises(DBAPIError) as raised:
                with connection.begin_nested():
                    _task(connection, connection_id, revision_id, **kwargs)
            assert _sqlstate(raised) == "23514", why


def test_a_task_of_one_connection_names_a_revision_and_a_token_of_that_connection_only(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        mine, my_revision = _connection(connection)
        other, other_revision = _connection(connection)
        other_token = _token(connection, other)
        probe_id = _probe(connection, mine, my_revision)
        with pytest.raises(DBAPIError) as revision:
            with connection.begin_nested():
                _task(connection, mine, other_revision, probe_id=probe_id)
        assert _sqlstate(revision) == "23503", "a revision of another connection"
        task_id = _task(connection, mine, my_revision, probe_id=probe_id)
        with pytest.raises(DBAPIError) as claimed:
            with connection.begin_nested():
                connection.execute(text(
                    "UPDATE executor_task SET state = 'claimed', claimed_by_token_id = :t, "
                    "claim_expires_at = now() + interval '1 minute', claim_count = 1, "
                    "first_claimed_at = now() WHERE task_id = :id"), {"t": other_token, "id": task_id})
        assert _sqlstate(claimed) == "23503", "a token of another connection cannot hold the claim"
        own = _token(connection, mine)
        connection.execute(text(
            "UPDATE executor_task SET state = 'claimed', claimed_by_token_id = :t, "
            "claim_expires_at = now() + interval '1 minute', claim_count = 1, "
            "first_claimed_at = now() WHERE task_id = :id"), {"t": own, "id": task_id})


def test_a_task_state_carries_exactly_the_columns_it_should(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, revision_id = _connection(connection)
        token_id = _token(connection, connection_id)
        probe_id = _probe(connection, connection_id, revision_id)

        def fresh() -> str:
            return _task(connection, connection_id, revision_id, probe_id=probe_id)

        claim = ("state = 'claimed', claimed_by_token_id = :t, claim_expires_at = now() + "
                 "interval '1 minute', claim_count = 1, first_claimed_at = now()")
        for why, change in (
            ("claimed without a token", "state = 'claimed', claim_expires_at = now(), claim_count = 1, "
                                        "first_claimed_at = now()"),
            ("claimed without a lease", "state = 'claimed', claimed_by_token_id = :t, claim_count = 1, "
                                        "first_claimed_at = now()"),
            ("claimed with no claim counted", "state = 'claimed', claimed_by_token_id = :t, "
                                              "claim_expires_at = now(), first_claimed_at = now()"),
            ("answered without a terminal time", "state = 'answered', declared_model = 'm', answer_text = 'a'"),
            ("answered without a declared model", "state = 'answered', answer_text = 'a', terminal_at = now()"),
            ("answered with no answer", "state = 'answered', declared_model = 'm', terminal_at = now()"),
            ("failed without a reason", "state = 'failed', terminal_at = now()"),
            ("a reason on an expired task", "state = 'expired', terminal_at = now(), fail_reason = 'x'"),
            ("a terminal time on an open task", "terminal_at = now()"),
            ("an answer on an open task", "answer_text = 'a'"),
            ("a payload cleared before the end", "payload = NULL, payload_cleared_at = now()"),
            ("a negative token count", "declared_input_tokens = -1"),
            ("an unknown state", "state = 'running'"),
        ):
            _refused(connection, f"UPDATE executor_task SET {change} WHERE task_id = :id",
                     {"id": fresh(), "t": token_id}, "23514", why)
        # The controls: each legal move works.
        one = fresh()
        connection.execute(text(f"UPDATE executor_task SET {claim} WHERE task_id = :id"),
                           {"id": one, "t": token_id})
        connection.execute(text(
            "UPDATE executor_task SET state = 'answered', answer_text = 'a', declared_model = 'm', "
            "declared_input_tokens = 1, declared_output_tokens = 2, terminal_at = now() "
            "WHERE task_id = :id"), {"id": one})
        connection.execute(text("UPDATE executor_task SET payload = NULL, answer_text = NULL, "
                                "payload_cleared_at = now() WHERE task_id = :id"), {"id": one})
        lapsed = fresh()
        connection.execute(text(f"UPDATE executor_task SET {claim} WHERE task_id = :id"),
                           {"id": lapsed, "t": token_id})
        connection.execute(text("UPDATE executor_task SET state = 'open', claimed_by_token_id = NULL, "
                                "claim_expires_at = NULL WHERE task_id = :id"), {"id": lapsed})


def test_a_task_is_frozen_and_its_terminal_time_is_write_once(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, revision_id = _connection(connection)
        run_id, attempt_id = _attempt(connection)
        task_id = _task(connection, connection_id, revision_id, run_id=run_id, attempt_id=attempt_id)
        for change in ("deadline_at = deadline_at + interval '1 hour'", "expected_model = 'other'",
                       "created_at = created_at - interval '1 day'", "origin = 'probe'",
                       "attempt_id = NULL", "connection_id = connection_id || 'x'"):
            _refused(connection, f"UPDATE executor_task SET {change} WHERE task_id = :id",
                     {"id": task_id}, "AM003" if "connection_id" not in change else "AM003", change)
        connection.execute(text("UPDATE executor_task SET state = 'cancelled', terminal_at = now() "
                                "WHERE task_id = :id"), {"id": task_id})
        _refused(connection, "UPDATE executor_task SET terminal_at = terminal_at + interval '1 hour' "
                             "WHERE task_id = :id", {"id": task_id}, "AM003", "moving the terminal time")
        _refused(connection, "UPDATE executor_task SET state = 'open', terminal_at = NULL "
                             "WHERE task_id = :id", {"id": task_id}, "AM003", "reopening an ended task")


def test_a_task_must_carry_a_payload_until_it_is_cleared(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection_id, revision_id = _connection(connection)
        probe_id = _probe(connection, connection_id, revision_id)
        with pytest.raises(DBAPIError) as raised:
            with connection.begin_nested():
                _task(connection, connection_id, revision_id, probe_id=probe_id, payload="NULL")
        assert _sqlstate(raised) == "23514"
        with pytest.raises(DBAPIError) as past:
            with connection.begin_nested():
                _task(connection, connection_id, revision_id, probe_id=probe_id,
                      deadline="now() - interval '1 minute'")
        assert _sqlstate(past) == "23514", "a deadline before the task existed"


@pytest.mark.parametrize("column", [
    "connection_id", "revision_id", "run_id", "attempt_id", "model_call_id", "probe_id",
])
def test_every_identity_column_of_a_task_refuses_a_malformed_value(
    migrated_engine: Engine, column: str,
) -> None:
    with migrated_engine.begin() as connection:
        connection_id, revision_id = _connection(connection)
        run_id, attempt_id = _attempt(connection)
        good = {"connection_id": connection_id, "revision_id": revision_id, "run_id": run_id,
                "attempt_id": attempt_id, "model_call_id": None, "probe_id": None}
        bad = {**good, column: "not-an-identity"}
        with pytest.raises(DBAPIError) as raised:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, "
                    "run_id, attempt_id, model_call_id, probe_id, expected_model, payload, "
                    "deadline_at) VALUES (:id, :connection_id, :revision_id, 'run_call', :run_id, "
                    ":attempt_id, :model_call_id, :probe_id, 'm', "
                    "CAST('{}' AS jsonb), now() + interval '1 minute')"
                ), {"id": str(ExecutorTaskId.new()), **bad})
        assert _sqlstate(raised) == "23514", "the format CHECK, not a foreign key, refuses it"


def test_a_token_refuses_a_malformed_connection_identity(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        with pytest.raises(DBAPIError) as raised:
            with connection.begin_nested():
                _token(connection, "exc_" + "0" * 25)
        assert _sqlstate(raised) == "23514"
