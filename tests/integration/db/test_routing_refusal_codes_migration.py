"""`BETA-CONTRACT-SEAL-01` phase A: ``0029_routing_refusal_codes`` on a populated ``0028`` database.

``0029`` widens the four stored-error ``CHECK`` constraints with the two run-routing codes
(``version_classification_required``, ``section_profile_unavailable``; `D-179`) and touches
nothing else. Four claims, each against a real PostgreSQL server:

* **the constraints say exactly the catalogue's stored vocabulary.** Each of the four reads
  back, from ``pg_get_constraintdef``, as the catalogue's codes minus the two that nothing
  stores -- not a superset, so the vocabulary is still closed;
* **before the step the codes are refused, after it they are storable** -- the same insert
  fails at ``0028`` and succeeds at the head, so the widening is what admits them;
* **a row that carries one survives the upgrade and stops the downgrade**, once per table, so
  each of the downgrade guard's four reads is shown to matter; the refused downgrade changes
  nothing;
* **with no such row the downgrade restores ``0022``'s constraints and the upgrade runs again.**
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    CommandId,
    DocumentUid,
    JobId,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from tests.support.expected_facts import FACTS

HEAD = FACTS.migration_head  # the tree's head: this revision or a later one
THIS = "0029_routing_refusal_codes"
PREVIOUS = "0028_classification_corrections"
NEW_CODES = ("version_classification_required", "section_profile_unavailable")
#: Catalogue codes that nothing stores (see ``test_contract_vocabulary.EDGE_ONLY_CODES``).
NOT_STORED = frozenset({"rate_limited", "analysis_input_budget_exceeded"})
CHECKS = {
    "command_record": "ck_command_record_error_code",
    "audit_run": "ck_audit_run_terminal_reason",
    "model_call": "ck_model_call_error_code",
    "provider_call_effect": "ck_provider_effect_error_code",
}
CATALOGUE = json.loads(
    (Path(__file__).resolve().parents[3] / "contracts/domain/v1/error-codes.json").read_text("utf-8")
)["codes"]


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _vocabulary(engine: Engine, table: str) -> set[str]:
    with engine.connect() as connection:
        definition = connection.execute(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"),
            {"name": CHECKS[table]},
        ).scalar_one()
    return set(re.findall(r"'([a-z_]+)'", definition))


def _seed_run(connection: Connection) -> dict[str, str]:
    ids = {
        "project_uid": str(ProjectUid.new()),
        "document_uid": str(DocumentUid.new()),
        "version_uid": str(VersionUid.new()),
        "run_id": str(RunId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project_uid, 'routing codes')"), ids)
    connection.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document_uid, :project_uid, 'doc')"),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:version_uid, :document_uid, 1, 'application/pdf', 1, :h, 1)"
        ),
        {**ids, "h": "a" * 64},
    )
    return ids


def _insert_run(connection: Connection, ids: dict[str, str]) -> None:
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest) VALUES (:run_id, :project_uid, :version_uid, :ap, :pb, "
            "'recorded', :digest)"
        ),
        {**ids, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()), "digest": "b" * 64},
    )


def _store_in_command_record(connection: Connection, code: str) -> None:
    command = str(CommandId.new())
    connection.execute(
        text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "VALUES (:c, 'start_run', :k, :d)"
        ),
        {"c": command, "k": f"k-{command}", "d": "c" * 64},
    )
    connection.execute(
        text("UPDATE command_record SET state = 'failed', error_code = :code WHERE command_id = :c"),
        {"c": command, "code": code},
    )


def _store_in_audit_run(connection: Connection, code: str) -> None:
    ids = _seed_run(connection)
    _insert_run(connection, ids)
    # The state machine's own path to a failure: created, queued, running, failed.
    for state in ("queued", "running"):
        connection.execute(text(f"UPDATE audit_run SET state = '{state}' WHERE run_id = :run_id"), ids)
    connection.execute(
        text("UPDATE audit_run SET state = 'failed', terminal_reason = :code, terminal_at = now() WHERE run_id = :run_id"),
        {**ids, "code": code},
    )


def _store_in_model_call(connection: Connection, code: str) -> None:
    ids = _seed_run(connection)
    _insert_run(connection, ids)
    connection.execute(
        text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, "
            "provider_mode, request_sha256, status, error_code) VALUES (:m, :run_id, 'text_analysis', "
            "'anthropic', 'a-model', 'recorded', :h, 'failed', :code)"
        ),
        {**ids, "m": str(ModelCallId.new()), "h": "d" * 64, "code": code},
    )


def _store_in_provider_call_effect(connection: Connection, code: str) -> None:
    ids = _seed_run(connection)
    _insert_run(connection, ids)
    job, attempt = str(JobId.new()), str(AttemptId.new())
    connection.execute(text("INSERT INTO job (job_id, run_id) VALUES (:j, :run_id)"), {**ids, "j": job})
    connection.execute(
        text("INSERT INTO attempt (attempt_id, job_id, execution_token) VALUES (:a, :j, :t)"),
        {"a": attempt, "j": job, "t": f"token-{attempt}"},
    )
    effect = str(ModelCallId.new())
    connection.execute(
        text(
            "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, attempt_id, stage_id, provider, "
            "model_identity, provider_mode, parameters, request_sha256) VALUES "
            "(:m, :run_id, :j, :a, 'text_analysis', 'anthropic', 'a-model', 'recorded', '{}'::jsonb, :h)"
        ),
        {**ids, "m": effect, "j": job, "a": attempt, "h": "e" * 64},
    )
    connection.execute(
        text("UPDATE provider_call_effect SET state = 'outcome_unknown', error_code = :code WHERE model_call_id = :m"),
        {"m": effect, "code": code},
    )


STORE: dict[str, Callable[[Connection, str], None]] = {
    "command_record": _store_in_command_record,
    "audit_run": _store_in_audit_run,
    "model_call": _store_in_model_call,
    "provider_call_effect": _store_in_provider_call_effect,
}


def test_the_four_checks_read_back_as_the_catalogues_stored_vocabulary(migrated_engine: Engine) -> None:
    stored = set(CATALOGUE) - NOT_STORED
    assert len(stored) == FACTS.stored_error_codes
    for table in CHECKS:
        assert _vocabulary(migrated_engine, table) == stored, table


@pytest.mark.parametrize("table", sorted(CHECKS))
def test_the_widening_is_what_admits_the_codes(
    table: str, empty_database, foundation_command
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    assert foundation_command(_alembic("upgrade", PREVIOUS), url).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        assert set(NEW_CODES).isdisjoint(_vocabulary(engine, table))
        for code in NEW_CODES:
            with pytest.raises(IntegrityError, match=CHECKS[table]), engine.begin() as connection:
                STORE[table](connection, code)
        upgraded = foundation_command(_alembic("upgrade", THIS), url)
        assert upgraded.returncode == 0, upgraded.describe()
        assert set(NEW_CODES) <= _vocabulary(engine, table)
        for code in NEW_CODES:
            with engine.begin() as connection:
                STORE[table](connection, code)
    finally:
        engine.dispose()


@pytest.mark.parametrize("table", sorted(CHECKS))
def test_a_row_carrying_a_new_code_survives_the_upgrade_and_stops_the_downgrade(
    table: str, empty_database, foundation_command
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            STORE[table](connection, NEW_CODES[0])
        before = _vocabulary(engine, table)
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0, refused.describe()
        assert "0029 downgrade refused" in refused.stderr, refused.stderr
        assert _version(engine) == HEAD
        assert _vocabulary(engine, table) == before and set(NEW_CODES) <= before
        with engine.connect() as connection:
            assert connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE {'terminal_reason' if table == 'audit_run' else 'error_code'} = :c"),
                {"c": NEW_CODES[0]},
            ).scalar_one() == 1
    finally:
        engine.dispose()


def test_without_such_a_row_the_downgrade_restores_the_previous_vocabulary(
    empty_database, foundation_command
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    assert foundation_command(_alembic("upgrade", HEAD), url).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        stored = set(CATALOGUE) - NOT_STORED
        down = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        assert _version(engine) == PREVIOUS
        for table in CHECKS:
            assert _vocabulary(engine, table) == stored - set(NEW_CODES), table
        up = foundation_command(_alembic("upgrade", HEAD), url)
        assert up.returncode == 0, up.describe()
        for table in CHECKS:
            assert _vocabulary(engine, table) == stored, table
    finally:
        engine.dispose()
