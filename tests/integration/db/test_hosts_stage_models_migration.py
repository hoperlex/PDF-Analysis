"""`HOSTS-SEAL-1`: ``0062_hosts_stage_models`` on a populated ``0061`` database (ADR-0028, plan 2026-11-09 sections 3.2 and 4.5).

Against real PostgreSQL rows, written through plain INSERTs, each rule shown failing:

* **the step changes no stored row**, and a token, a grant and an install session written before it still name their connection;
* **the host**: its identity, a name unique among live hosts, a one-way archive, no delete, and two append-only journals (the «Использовать»
  switch and the slots of a provider) numbered without a gap;
* **a credential names exactly one of a connection and a host** (token, grant, install session), and a task is claimed by a token of its
  connection or of the host that owns it, and by no other;
* **a system connection** belongs to one host and one provider of it (the capacity pool), and none of that can be changed afterwards;
* **the stage layout**: one layout, append-only revisions, a switch that needs a revision;
* **the planned run**: its plan is frozen, a wait for a model belongs to a planned run only, a planned run carries no group, connection,
  preset or rule of its own, and it is bound only when every cell of its plan has its binding row;
* **the cell binding**: written once, for a pending planned run, for a cell of its plan, for a system member that pins the cell's model;
* **the call journal**: ``stage_key``, ``host_id`` (no foreign key) and ``access``, NULL for every call written before;
* **the downgrade is refused while any of it exists, and only then**.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ExecutorEnrollmentId,
    ExecutorGroupId,
    ExecutorGroupRevisionId,
    ExecutorHostId,
    ExecutorHostSlotEventId,
    ExecutorHostUseEventId,
    ExecutorRunnerTokenId,
    ExecutorSecretId,
    ProjectUid,
    PromptBundleId,
    RunId,
    StageLayoutRevisionId,
    StageLayoutSwitchEventId,
    VersionUid,
)
from tests.support.expected_facts import FACTS

THIS = "0062_hosts_stage_models"
PREVIOUS = "0061_decision_memory_m2"
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
MODEL = "claude-opus-5-5"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = foundation_command(_alembic("upgrade", revision), url)
    assert done.returncode == 0, done.describe()


def _refused(engine: Engine, write: Any, sqlstate: str = "AM001") -> None:
    """The write is refused by the database with the given SQLSTATE (a CHECK or a key is ``23xxx``)."""
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


# -- the rows -------------------------------------------------------------------------------------


def _host(connection: Any, name: str = "adm1.hlab.kz") -> str:
    host_id = str(ExecutorHostId.new())
    connection.execute(text(
        "INSERT INTO executor_host (host_id, display_name, created_by) VALUES (:id, :name, :actor)"
    ), {"id": host_id, "name": name, "actor": ACTOR})
    return host_id


def _token(connection: Any, *, host_id: str | None = None, connection_id: str | None = None) -> str:
    token_id = str(ExecutorRunnerTokenId.new())
    prefix = "amr_" + token_id[-8:].lower()
    connection.execute(text(
        "INSERT INTO executor_runner_token (token_id, connection_id, host_id, token_prefix, token_hash, created_by, "
        "expires_at) VALUES (:id, :c, :h, :prefix, :hash, :actor, clock_timestamp() + interval '1 day')"
    ), {"id": token_id, "c": connection_id, "h": host_id, "prefix": prefix, "hash": token_id.encode()[:32].ljust(32, b"0"), "actor": ACTOR})
    return token_id


def _secret_before(connection: Any, connection_id: str) -> str:
    """A secret as ``0061`` could write it (no ``host_id`` column yet)."""
    secret_id = str(ExecutorSecretId.new())
    connection.execute(text(
        "INSERT INTO executor_secret (secret_id, connection_id, purpose, kid, destination, ciphertext, last4, set_by) "
        "VALUES (:id, :c, 'ssh_private_key', 'k1', 'adm1.hlab.kz', :cipher, 'abcd', :actor)"
    ), {"id": secret_id, "c": connection_id, "cipher": b"sealed", "actor": ACTOR})
    return secret_id


def _legacy_connection(connection: Any) -> str:
    connection_id = str(ExecutorConnectionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
        "VALUES (:id, 'pull', 'legacy', :actor)"), {"id": connection_id, "actor": ACTOR})
    return connection_id


def _secret(connection: Any, *, host_id: str | None = None, connection_id: str | None = None, purpose: str = "agent_install_key",
            replaced: bool = False) -> str:
    """One sealed secret; the install key of a host is one with ``host_id`` and no connection."""
    secret_id = str(ExecutorSecretId.new())
    connection.execute(text(
        "INSERT INTO executor_secret (secret_id, connection_id, host_id, purpose, kid, destination, ciphertext, last4, set_by, replaced_at) "
        "VALUES (:id, :c, :h, :purpose, 'k1', 'adm1.hlab.kz', :cipher, 'abcd', :actor, "
        "CASE WHEN :replaced THEN clock_timestamp() ELSE NULL END)"
    ), {"id": secret_id, "c": connection_id, "h": host_id, "purpose": purpose, "cipher": b"sealed", "actor": ACTOR, "replaced": replaced})
    return secret_id


def _system_connection(connection: Any, host_id: str, *, provider: str = "claude_code", model: str = MODEL) -> tuple[str, str]:
    """A system connection of the host and its one revision; returns (connection id, revision id)."""
    connection_id = str(ExecutorConnectionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by, system_managed, host_id, capacity_pool) "
        "VALUES (:id, 'pull', 'system', :actor, true, :host, :pool)"
    ), {"id": connection_id, "actor": ACTOR, "host": host_id, "pool": f"{host_id}:{provider}"})
    revision_id = str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, "
        "billing, allow_client_documents, timeout_seconds, pull_client, answer_deadline_seconds, max_claimed_tasks) "
        "VALUES (:rev, :c, 1, :actor, :model, :model, 'not_metered', false, 600, 'agent', 600, 1)"
    ), {"rev": revision_id, "c": connection_id, "actor": ACTOR, "model": model})
    return connection_id, revision_id


def _system_group(connection: Any, connection_id: str, revision_id: str, *, model: str = MODEL) -> str:
    """A system group with one revision holding the member; returns the group revision id."""
    group_id, group_revision_id = str(ExecutorGroupId.new()), str(ExecutorGroupRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_group (group_id, display_name, created_by, system_managed) VALUES (:g, :name, :actor, true)"
    ), {"g": group_id, "name": f"{model} {group_id[-8:]}", "actor": ACTOR})
    connection.execute(text(
        "INSERT INTO executor_group_revision (group_revision_id, group_id, revision_no, pin_id, gateway_model, billing, "
        "input_per_mtok_usd, output_per_mtok_usd, member_count, created_by) "
        "VALUES (:gr, :g, 1, :model, :model, 'not_metered', 4, 20, 1, :actor)"
    ), {"gr": group_revision_id, "g": group_id, "model": model, "actor": ACTOR})
    connection.execute(text(
        "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id) VALUES (:gr, :c, :rev)"
    ), {"gr": group_revision_id, "c": connection_id, "rev": revision_id})
    return group_revision_id


def _plan(*cell_keys: str, model: str = MODEL) -> str:
    return json.dumps({"layout_revision_id": str(StageLayoutRevisionId.new()), "cells": [
        {"cell_key": key, "model_id": model, "effort": "medium", "max_output_tokens": 16000, "timeout_seconds": 600,
         "access": "subscription"} for key in cell_keys]})


def _planned_run(connection: Any, plan: str | None, *, binding_state: str = "pending", wait_reason: str | None = None) -> str:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'hosts')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'D')"), ids)
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                            "media_type, byte_size, sha256, page_count) VALUES (:version, :document, 1, "
                            "'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "frozen_input_digest, binding_state, stage_plan, wait_reason, waiting_since) "
        "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, :state, CAST(:plan AS jsonb), :wait, "
        "CASE WHEN CAST(:wait AS text) IS NULL THEN NULL ELSE clock_timestamp() END)"),
        {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64,
         "state": binding_state, "plan": plan, "wait": wait_reason})
    return ids["run"]


def _bind_cell(connection: Any, run_id: str, cell_key: str, group_revision: str, revision: str) -> None:
    connection.execute(text(
        "INSERT INTO audit_run_cell_binding (run_id, cell_key, group_revision_id, connection_revision_id) "
        "VALUES (:run, :cell, :gr, :rev)"), {"run": run_id, "cell": cell_key, "gr": group_revision, "rev": revision})


# -- fixtures -------------------------------------------------------------------------------------


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str]]:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        yield engine, url
    finally:
        engine.dispose()


@pytest.fixture
def at_this(at_previous: tuple[Engine, str], foundation_command: Any) -> tuple[Engine, str]:
    engine, url = at_previous
    _upgrade(foundation_command, url, THIS)
    return engine, url


@pytest.fixture
def world(at_this: tuple[Engine, str]) -> Iterator[dict[str, Any]]:
    """A migrated database with a host, one system connection of it and a system group holding that connection."""
    engine, _ = at_this
    with engine.begin() as connection:
        host = _host(connection)
        connection_id, revision = _system_connection(connection, host)
        group_revision = _system_group(connection, connection_id, revision)
    yield {"engine": engine, "host": host, "connection": connection_id, "revision": revision,
           "group_revision": group_revision}


# -- the step -------------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_changes_no_stored_row_and_a_legacy_credential_still_names_its_connection(
    at_previous: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        legacy = _legacy_connection(connection)
        legacy_secret = _secret_before(connection, legacy)
        token = str(ExecutorRunnerTokenId.new())
        connection.execute(text(
            "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, created_by, expires_at) "
            "VALUES (:id, :c, :prefix, :hash, :actor, clock_timestamp() + interval '1 day')"
        ), {"id": token, "c": legacy, "prefix": "amr_abcdefgh", "hash": b"h" * 32, "actor": ACTOR})
    tables = ("executor_connection", "executor_runner_token", "executor_secret", "audit_run", "command_record")
    before = {table: _count(engine, table) for table in tables}
    _upgrade(foundation_command, url, THIS)
    assert _version(engine) == THIS
    assert {table: _count(engine, table) for table in tables} == before
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT connection_id, host_id FROM executor_runner_token WHERE token_id = :t"), {"t": token}).one()
        assert row == (legacy, None)
        pool = connection.execute(text(
            "SELECT system_managed, host_id, capacity_pool FROM executor_connection WHERE connection_id = :c"), {"c": legacy}).one()
        assert pool == (False, None, None)
        # a secret written before the step still names its connection and no host
        assert connection.execute(text(
            "SELECT connection_id, host_id, purpose FROM executor_secret WHERE secret_id = :s"), {"s": legacy_secret}).one() == (
            legacy, None, "ssh_private_key")
    for table in ("executor_host", "audit_run_cell_binding", "stage_layout_revision", "executor_host_report"):
        assert _count(engine, table) == 0
    assert _count(engine, "stage_layout") == 1  # the one layout, key `default`


def test_every_run_written_before_the_step_has_no_plan(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    with engine.begin() as connection:
        ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
               "version": str(VersionUid.new()), "run": str(RunId.new())}
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'old')"), ids)
        connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')"), ids)
        connection.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                                "sha256, page_count) VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                           {**ids, "sha": "a" * 64})
        connection.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "frozen_input_digest) VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest)"),
            {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64})
    _upgrade(foundation_command, url, THIS)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT stage_plan, binding_state FROM audit_run")).one() == (None, "frozen_at_start")


# -- the host -------------------------------------------------------------------------------------


def test_a_host_has_a_live_name_once_is_archived_once_and_is_never_deleted(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    with engine.begin() as connection:
        host = _host(connection, "Server")
    _refused(engine, lambda c: _host(c, "server"), "23505")  # unique among live hosts, case-insensitively
    _refused(engine, lambda c: c.execute(text("UPDATE executor_host SET display_name = 'x' WHERE host_id = :h"), {"h": host}), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM executor_host WHERE host_id = :h"), {"h": host}), "AM003")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_host SET archived_at = clock_timestamp() WHERE host_id = :h"),
                                        {"h": host}), "23514")  # archived_at without archived_by
    with engine.begin() as connection:
        connection.execute(text("UPDATE executor_host SET archived_at = clock_timestamp(), archived_by = :a WHERE host_id = :h"),
                           {"h": host, "a": ACTOR})
        _host(connection, "Server")  # an archived name is free again
    _refused(engine, lambda c: c.execute(text("UPDATE executor_host SET archived_by = :a WHERE host_id = :h"),
                                        {"h": host, "a": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAW"}), "AM003")  # write-once


def test_a_host_identity_must_be_well_formed(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    _refused(engine, lambda c: c.execute(text(
        "INSERT INTO executor_host (host_id, display_name, created_by) VALUES ('exh_nonsense', 'x', :a)"), {"a": ACTOR}), "23514")
    _refused(engine, lambda c: c.execute(text(
        "INSERT INTO executor_host (host_id, display_name, created_by) VALUES (:h, '', :a)"),
        {"h": str(ExecutorHostId.new()), "a": ACTOR}), "23514")


def test_the_use_journal_is_append_only_and_numbered_without_a_gap(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]

    def event(connection: Any, number: int, enabled: bool = True) -> None:
        connection.execute(text(
            "INSERT INTO executor_host_use_event (use_event_id, host_id, event_no, enabled, set_by) VALUES (:id, :h, :n, :e, :a)"
        ), {"id": str(ExecutorHostUseEventId.new()), "h": host, "n": number, "e": enabled, "a": ACTOR})

    _refused(engine, lambda c: event(c, 2))  # the first event is number 1
    with engine.begin() as connection:
        event(connection, 1)
        event(connection, 2, False)
    _refused(engine, lambda c: event(c, 2))  # a number is taken once
    _refused(engine, lambda c: event(c, 4))  # and without a gap
    _refused(engine, lambda c: c.execute(text("UPDATE executor_host_use_event SET enabled = true")), "AM002")
    _refused(engine, lambda c: c.execute(text("DELETE FROM executor_host_use_event")), "AM002")
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT enabled FROM executor_host_use_event WHERE host_id = :h ORDER BY event_no DESC LIMIT 1"), {"h": host}).scalar_one() is False


def test_the_slot_journal_takes_a_provider_and_one_to_sixteen_slots(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]

    def event(connection: Any, number: int, provider: str, slots: int) -> None:
        connection.execute(text(
            "INSERT INTO executor_host_slot_event (slot_event_id, host_id, event_no, provider, slots, set_by) "
            "VALUES (:id, :h, :n, :p, :s, :a)"
        ), {"id": str(ExecutorHostSlotEventId.new()), "h": host, "n": number, "p": provider, "s": slots, "a": ACTOR})

    with engine.begin() as connection:
        event(connection, 1, "claude_code", 1)
        event(connection, 2, "anthropic_api", 2)
    _refused(engine, lambda c: event(c, 3, "gemini_api", 1), "23514")
    _refused(engine, lambda c: event(c, 3, "codex", 0), "23514")
    _refused(engine, lambda c: event(c, 3, "codex", 17), "23514")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_host_slot_event SET slots = 3")), "AM002")


def test_the_report_is_one_snapshot_of_the_host_written_by_a_token_of_that_host(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]
    with engine.begin() as connection:
        token = _token(connection, host_id=host)
        other_token = _token(connection, host_id=_host(connection, "other"))
    insert = text(
        "INSERT INTO executor_host_report (host_id, token_id, agent_version, providers, slots, report_sha256) "
        "VALUES (:h, :t, '0.3.0', CAST(:p AS jsonb), CAST(:s AS jsonb), :d)")
    values = {"h": host, "t": token, "p": "[]", "s": "{}", "d": "c" * 64}
    _refused(engine, lambda c: c.execute(insert, {**values, "t": other_token}), "23503")  # a token of another host
    _refused(engine, lambda c: c.execute(insert, {**values, "p": "{}"}), "23514")  # providers is an array
    with engine.begin() as connection:
        connection.execute(insert, values)
    _refused(engine, lambda c: c.execute(insert, values), "23505")  # one snapshot per host, replaced by UPDATE
    with engine.begin() as connection:
        connection.execute(text("UPDATE executor_host_report SET report_sha256 = :d, reported_at = clock_timestamp() WHERE host_id = :h"),
                           {"d": "d" * 64, "h": host})


def test_a_cooldown_is_one_row_per_host_provider_and_model_with_a_closed_reason(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]
    insert = text(
        "INSERT INTO executor_model_cooldown (host_id, provider, model_id, until, reason) "
        "VALUES (:h, :p, :m, clock_timestamp() + interval '15 minutes', :r)")
    values = {"h": host, "p": "claude_code", "m": MODEL, "r": "quota_exceeded"}
    with engine.begin() as connection:
        connection.execute(insert, values)
    _refused(engine, lambda c: c.execute(insert, values), "23505")
    _refused(engine, lambda c: c.execute(insert, {**values, "m": "x", "r": "tired"}), "23514")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_model_cooldown SET model_id = 'x'")), "AM003")
    with engine.begin() as connection:
        connection.execute(text("UPDATE executor_model_cooldown SET until = until + interval '1 minute', reason = 'access_denied'"))


# -- a credential names a connection or a host, never both and never neither ----------------------


def test_a_token_names_exactly_one_of_a_connection_and_a_host(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]
    with engine.begin() as connection:
        legacy = _legacy_connection(connection)
        _token(connection, host_id=host)
        _token(connection, connection_id=legacy)
    _refused(engine, lambda c: _token(c), "23514")
    _refused(engine, lambda c: _token(c, host_id=host, connection_id=legacy), "23514")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_runner_token SET host_id = NULL WHERE host_id = :h"), {"h": host}), "AM003")


def test_a_grant_and_an_install_session_name_exactly_one_of_a_connection_and_a_host(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]
    grant = text(
        "INSERT INTO executor_enrollment (enrollment_id, connection_id, host_id, secret_prefix, secret_hash, created_by, expires_at) "
        "VALUES (:id, :c, :h, :prefix, :hash, :a, clock_timestamp() + interval '15 minutes')")

    def issue(connection: Any, *, connection_id: str | None, host_id: str | None, prefix: str) -> None:
        connection.execute(grant, {"id": str(ExecutorEnrollmentId.new()), "c": connection_id, "h": host_id, "prefix": prefix,
                                   "hash": prefix.encode().ljust(32, b"0"), "a": ACTOR})

    with engine.begin() as connection:
        legacy = _legacy_connection(connection)
        issue(connection, connection_id=None, host_id=host, prefix="ame_aaaaaaaa")
        issue(connection, connection_id=legacy, host_id=None, prefix="ame_bbbbbbbb")
    _refused(engine, lambda c: issue(c, connection_id=None, host_id=None, prefix="ame_cccccccc"), "23514")
    _refused(engine, lambda c: issue(c, connection_id=legacy, host_id=host, prefix="ame_dddddddd"), "23514")
    # at most one unredeemed grant per host, as per connection
    _refused(engine, lambda c: issue(c, connection_id=None, host_id=host, prefix="ame_eeeeeeee"), "23505")

    install = text(
        "INSERT INTO executor_agent_install (install_id, connection_id, host_id, access, ssh_host, ssh_port, ssh_user, created_by, "
        "key_removed_at) VALUES (:id, :c, :h, 'generated_key', 'adm1.hlab.kz', 22, 'root', :a, clock_timestamp())")
    with engine.begin() as connection:
        connection.execute(install, {"id": "exai_" + str(ExecutorEnrollmentId.new())[-26:], "c": None, "h": host, "a": ACTOR})
    _refused(engine, lambda c: c.execute(install, {"id": "exai_" + str(ExecutorEnrollmentId.new())[-26:], "c": None, "h": None,
                                                   "a": ACTOR}), "23514")
    _refused(engine, lambda c: c.execute(install, {"id": "exai_" + str(ExecutorEnrollmentId.new())[-26:], "c": None, "h": host,
                                                   "a": ACTOR}), "23505")  # one unfinished session per host


def test_a_task_is_claimed_by_a_token_of_its_connection_or_of_its_host_and_by_no_other(world: dict[str, Any]) -> None:
    engine, host, connection_id, revision = world["engine"], world["host"], world["connection"], world["revision"]
    with engine.begin() as connection:
        host_token = _token(connection, host_id=host)
        stranger = _token(connection, host_id=_host(connection, "stranger"))
        legacy = _legacy_connection(connection)
        legacy_token = _token(connection, connection_id=legacy)
    deadline_sql = (
        "INSERT INTO executor_task (task_id, connection_id, revision_id, origin, probe_id, expected_model, payload, deadline_at, "
        "state, claimed_by_token_id, claim_expires_at, first_claimed_at, claim_count) "
        "VALUES (:id, :c, :rev, 'probe', :probe, :model, '{}', clock_timestamp() + interval '1 hour', "
        "CASE WHEN CAST(:t AS text) IS NULL THEN 'open' ELSE 'claimed' END, :t, "
        "CASE WHEN CAST(:t AS text) IS NULL THEN NULL ELSE clock_timestamp() + interval '5 minutes' END, "
        "CASE WHEN CAST(:t AS text) IS NULL THEN NULL ELSE clock_timestamp() END, "
        "CASE WHEN CAST(:t AS text) IS NULL THEN 0 ELSE 1 END)")

    def task(connection: Any, token: str | None) -> None:
        from auditmanager.shared.identity import ExecutorProbeId, ExecutorTaskId
        probe = str(ExecutorProbeId.new())
        connection.execute(text(
            "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, requested_by) "
            "VALUES (:p, :c, :rev, 'requested', :a)"), {"p": probe, "c": connection_id, "rev": revision, "a": ACTOR})
        connection.execute(text(deadline_sql), {"id": str(ExecutorTaskId.new()), "c": connection_id, "rev": revision,
                                                "probe": probe, "model": MODEL, "t": token})

    try:
        with engine.begin() as connection:
            task(connection, None)
            task(connection, host_token)  # the host's token claims a task of the host's system connection
    except DBAPIError as error:  # pragma: no cover - the probe table's own columns are not this test's subject
        pytest.skip(f"the probe fixture is not accepted by this schema: {error.orig}")
    _refused(engine, lambda c: task(c, stranger))  # a token of another host
    _refused(engine, lambda c: task(c, legacy_token))  # a token of another connection


def test_the_sealed_key_of_a_host_install_is_a_secret_of_the_host_and_a_secret_names_exactly_one_of_a_connection_and_a_host(
    world: dict[str, Any]
) -> None:
    engine, host = world["engine"], world["host"]
    with engine.begin() as connection:
        legacy = _legacy_connection(connection)
        host_secret = _secret(connection, host_id=host)
        _secret(connection, connection_id=legacy, purpose="ssh_private_key")  # the connection form is what it was
    with engine.connect() as connection:
        assert connection.execute(text("SELECT connection_id, host_id FROM executor_secret WHERE secret_id = :s"),
                                  {"s": host_secret}).one() == (None, host)
    _refused(engine, lambda c: _secret(c, host_id=host, connection_id=legacy, purpose="api_key"), "23514")  # both
    _refused(engine, lambda c: _secret(c), "23514")  # neither
    _refused(engine, lambda c: _secret(c, host_id="exh_nonsense"), "23514")  # a malformed host identity
    _refused(engine, lambda c: _secret(c, host_id=str(ExecutorHostId.new())), "23503")  # a host that does not exist
    _refused(engine, lambda c: _secret(c, host_id=host), "23505")  # one current secret per host and purpose
    with engine.begin() as connection:
        _secret(connection, host_id=host, purpose="api_key")  # another purpose, the same host
        connection.execute(text("UPDATE executor_secret SET replaced_at = clock_timestamp() WHERE secret_id = :s"), {"s": host_secret})
        _secret(connection, host_id=host)  # replaced: the next one is current
    _refused(engine, lambda c: c.execute(text("UPDATE executor_secret SET host_id = NULL WHERE secret_id = :s"), {"s": host_secret}), "AM003")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_secret SET connection_id = :c WHERE secret_id = :s"),
                                        {"c": legacy, "s": host_secret}), "AM003")


def test_the_install_of_a_host_holds_its_sealed_key_in_a_secret_of_the_host(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]
    with engine.begin() as connection:
        secret = _secret(connection, host_id=host)
        connection.execute(text(
            "INSERT INTO executor_agent_install (install_id, connection_id, host_id, access, ssh_host, ssh_port, ssh_user, created_by, "
            "key_secret_id) VALUES (:id, NULL, :h, 'generated_key', 'adm1.hlab.kz', 22, 'root', :a, :s)"),
            {"id": "exai_" + str(ExecutorEnrollmentId.new())[-26:], "h": host, "a": ACTOR, "s": secret})
    with engine.connect() as connection:
        assert connection.execute(text("SELECT key_secret_id, key_removed_at FROM executor_agent_install WHERE host_id = :h"),
                                  {"h": host}).one() == (secret, None)


# -- system connections ---------------------------------------------------------------------------


def test_a_system_connection_is_a_pull_connection_of_a_host_with_the_pool_of_one_provider(world: dict[str, Any]) -> None:
    engine, host = world["engine"], world["host"]

    def make(connection: Any, **overrides: Any) -> None:
        values = {"id": str(ExecutorConnectionId.new()), "kind": "pull", "system": True, "host": host,
                  "pool": f"{host}:codex", "actor": ACTOR, **overrides}
        connection.execute(text(
            "INSERT INTO executor_connection (connection_id, kind, display_name, created_by, system_managed, host_id, capacity_pool) "
            "VALUES (:id, :kind, 's', :actor, :system, :host, :pool)"), values)

    with engine.begin() as connection:
        make(connection)
    _refused(engine, lambda c: make(c, kind="http_api"), "23514")  # only pull
    _refused(engine, lambda c: make(c, pool=f"{host}:gemini"), "23514")  # a closed set of providers
    _refused(engine, lambda c: make(c, pool=f"{ExecutorHostId.new()}:codex"), "23514")  # the pool of another host
    _refused(engine, lambda c: make(c, host=None, pool=None), "23514")  # system without a host
    _refused(engine, lambda c: make(c, system=False), "23514")  # a user's connection has no host and no pool


def test_a_system_connection_and_a_system_group_keep_their_flag_host_and_pool(world: dict[str, Any]) -> None:
    engine = world["engine"]
    for column, value in (("system_managed", "false"), ("host_id", "NULL"), ("capacity_pool", "'x'")):
        _refused(engine, lambda c, column=column, value=value: c.execute(text(
            f"UPDATE executor_connection SET {column} = {value} WHERE connection_id = :c"), {"c": world["connection"]}), "AM003")
    _refused(engine, lambda c: c.execute(text("UPDATE executor_group SET system_managed = false")), "AM003")


# -- the stage layout -----------------------------------------------------------------------------


def _revision(connection: Any, number: int, *, kit: str = "claude_only", cells: str = '[{"cell_key": "text:main"}]') -> None:
    connection.execute(text(
        "INSERT INTO stage_layout_revision (layout_revision_id, layout_key, revision_no, kit, cells, created_by) "
        "VALUES (:id, 'default', :n, :kit, CAST(:cells AS jsonb), :a)"),
        {"id": str(StageLayoutRevisionId.new()), "n": number, "kit": kit, "cells": cells, "a": ACTOR})


def _switch(connection: Any, number: int, enabled: bool) -> None:
    connection.execute(text(
        "INSERT INTO stage_layout_switch_event (switch_event_id, layout_key, event_no, enabled, set_by) "
        "VALUES (:id, 'default', :n, :e, :a)"),
        {"id": str(StageLayoutSwitchEventId.new()), "n": number, "e": enabled, "a": ACTOR})


def test_the_layout_is_one_row_and_its_revisions_are_append_only_and_numbered(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    _refused(engine, lambda c: c.execute(text("INSERT INTO stage_layout (layout_key) VALUES ('other')")), "23514")
    _refused(engine, lambda c: c.execute(text("DELETE FROM stage_layout")), "AM003")
    _refused(engine, lambda c: _revision(c, 2))
    with engine.begin() as connection:
        _revision(connection, 1)
        _revision(connection, 2, kit="custom")
    _refused(engine, lambda c: _revision(c, 3, kit="all_the_models"), "23514")
    _refused(engine, lambda c: _revision(c, 3, cells="{}"), "23514")
    _refused(engine, lambda c: _revision(c, 3, cells="[]"), "23514")
    _refused(engine, lambda c: c.execute(text("UPDATE stage_layout_revision SET kit = 'custom'")), "AM002")
    _refused(engine, lambda c: c.execute(text("DELETE FROM stage_layout_revision")), "AM002")


def test_the_layout_cannot_be_switched_on_without_a_revision_and_its_journal_is_append_only(at_this: tuple[Engine, str]) -> None:
    engine, _ = at_this
    _refused(engine, lambda c: _switch(c, 1, True))
    with engine.begin() as connection:
        _switch(connection, 1, False)  # switching off needs no revision
    with engine.begin() as connection:
        _revision(connection, 1)
        _switch(connection, 2, True)
    _refused(engine, lambda c: _switch(c, 2, False))  # a number is taken once
    _refused(engine, lambda c: c.execute(text("UPDATE stage_layout_switch_event SET enabled = false")), "AM002")
    _refused(engine, lambda c: c.execute(text("DELETE FROM stage_layout_switch_event")), "AM002")


# -- the planned run ------------------------------------------------------------------------------


def test_a_planned_run_is_pending_with_a_frozen_plan_and_no_executor_of_its_own(world: dict[str, Any]) -> None:
    engine, group_revision = world["engine"], world["group_revision"]
    plan = _plan("text:main")
    with engine.begin() as connection:
        run = _planned_run(connection, plan)
    _refused(engine, lambda c: c.execute(text("UPDATE audit_run SET stage_plan = CAST(:p AS jsonb) WHERE run_id = :r"),
                                        {"p": _plan("text:main", "blocks:main"), "r": run}), "AM003")  # frozen
    _refused(engine, lambda c: c.execute(text("UPDATE audit_run SET stage_plan = NULL WHERE run_id = :r"), {"r": run}), "AM003")
    _refused(engine, lambda c: _planned_run(c, "[]"), "23514")  # a plan is an object with cells
    _refused(engine, lambda c: _planned_run(c, json.dumps({"cells": []})), "23514")
    _refused(engine, lambda c: _planned_run(c, plan, binding_state="frozen_at_start"), "23514")
    # no group of its own: the cells carry them
    _refused(engine, lambda c: c.execute(text("UPDATE audit_run SET executor_group_revision_id = :g WHERE run_id = :r"),
                                        {"g": group_revision, "r": run}), "AM003")


def test_a_wait_for_a_model_belongs_to_a_planned_run_only(world: dict[str, Any]) -> None:
    engine = world["engine"]
    with engine.begin() as connection:
        run = _planned_run(connection, _plan("text:main"), wait_reason="model_unavailable")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT wait_reason, binding_state FROM audit_run WHERE run_id = :r"), {"r": run}).one() == (
            "model_unavailable", "pending")
    _refused(engine, lambda c: _planned_run(c, None, wait_reason="model_unavailable"), "23514")
    _refused(engine, lambda c: _planned_run(c, _plan("text:main"), wait_reason="tired"), "23514")
    # the older reasons are unchanged
    with engine.begin() as connection:
        _planned_run(connection, _plan("text:main"), wait_reason="needs_reconsent")


def test_a_planned_run_is_bound_only_when_every_cell_of_its_plan_has_its_binding(world: dict[str, Any]) -> None:
    engine, group_revision, revision = world["engine"], world["group_revision"], world["revision"]
    with engine.begin() as connection:
        run = _planned_run(connection, _plan("text:main", "blocks:main"))
        _bind_cell(connection, run, "text:main", group_revision, revision)
    bind = text("UPDATE audit_run SET binding_state = 'bound' WHERE run_id = :r")
    _refused(engine, lambda c: c.execute(bind, {"r": run}))  # `blocks:main` has no binding yet
    with engine.begin() as connection:
        _bind_cell(connection, run, "blocks:main", group_revision, revision)
        connection.execute(bind, {"r": run})
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT binding_state, connection_revision_id, executor_group_revision_id FROM audit_run WHERE run_id = :r"),
            {"r": run}).one() == ("bound", None, None)
    _refused(engine, lambda c: c.execute(text("UPDATE audit_run SET binding_state = 'pending' WHERE run_id = :r"), {"r": run}))
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", group_revision, revision), "AM001")  # a bound run takes no cell


# -- the cell binding -----------------------------------------------------------------------------


def test_a_cell_is_bound_once_and_the_row_is_never_changed_or_removed(world: dict[str, Any]) -> None:
    engine, group_revision, revision = world["engine"], world["group_revision"], world["revision"]
    with engine.begin() as connection:
        run = _planned_run(connection, _plan("text:main", "blocks:main"))
        _bind_cell(connection, run, "text:main", group_revision, revision)
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", group_revision, revision), "23505")  # a second write of the cell
    _refused(engine, lambda c: c.execute(text("UPDATE audit_run_cell_binding SET bound_at = clock_timestamp()")), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM audit_run_cell_binding")), "AM003")


def test_a_cell_binding_names_a_cell_of_the_plan_and_a_system_member_that_pins_its_model(world: dict[str, Any]) -> None:
    engine, host, group_revision, revision = world["engine"], world["host"], world["group_revision"], world["revision"]
    with engine.begin() as connection:
        run = _planned_run(connection, _plan("text:main"))
        other_connection, other_revision = _system_connection(connection, host, provider="codex", model="gpt-6-sol")
        other_group = _system_group(connection, other_connection, other_revision, model="gpt-6-sol")
        legacy = _legacy_connection(connection)
        legacy_revision = str(ExecutorConnectionRevisionId.new())
        connection.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, "
            "billing, allow_client_documents, timeout_seconds, pull_client, answer_deadline_seconds, max_claimed_tasks) "
            "VALUES (:rev, :c, 1, :a, :m, :m, 'not_metered', false, 600, 'agent', 600, 1)"),
            {"rev": legacy_revision, "c": legacy, "a": ACTOR, "m": MODEL})
        legacy_group = _system_group(connection, legacy, legacy_revision)
    _refused(engine, lambda c: _bind_cell(c, run, "blocks:main", group_revision, revision))  # not a cell of the plan
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", other_group, other_revision))  # a member of another model
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", group_revision, other_revision))  # not a member of that group
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", legacy_group, legacy_revision))  # not a system connection
    _refused(engine, lambda c: _bind_cell(c, run, "text:other", group_revision, revision))  # no such cell
    with engine.connect() as connection:  # and a key is `row:role` with a closed set of roles, whatever the plan says
        assert "main|leg1|leg2|judge" in connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_audit_run_cell_binding_cell_key'")).scalar_one()
    with engine.begin() as connection:
        _bind_cell(connection, run, "text:main", group_revision, revision)


def test_a_run_without_a_plan_takes_no_cell_binding(world: dict[str, Any]) -> None:
    engine, group_revision, revision = world["engine"], world["group_revision"], world["revision"]
    with engine.begin() as connection:
        run = _planned_run(connection, None, binding_state="frozen_at_start")
    _refused(engine, lambda c: _bind_cell(c, run, "text:main", group_revision, revision))


# -- the call journal -----------------------------------------------------------------------------


def test_the_call_journal_takes_a_stage_key_a_host_and_an_access_and_holds_the_host_by_identity_only(world: dict[str, Any]) -> None:
    engine = world["engine"]
    with engine.connect() as connection:
        for table in ("model_call", "provider_call_effect"):
            columns = {row[0]: row[1] for row in connection.execute(text(
                "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = :t "
                "AND column_name IN ('stage_key', 'host_id', 'access')"), {"t": table})}
            assert columns == {"stage_key": "YES", "host_id": "YES", "access": "YES"}, (table, columns)
            keys = connection.execute(text(
                "SELECT count(*) FROM information_schema.table_constraints c "
                "JOIN information_schema.key_column_usage k USING (constraint_name, table_name) "
                "WHERE c.table_name = :t AND c.constraint_type = 'FOREIGN KEY' AND k.column_name = 'host_id'"), {"t": table}).scalar_one()
            assert keys == 0, f"{table}.host_id must not be a foreign key"
            checks = {row[0] for row in connection.execute(text(
                "SELECT conname FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'c' "
                "AND conname LIKE :like"), {"t": table, "like": f"ck_{table}_%"})}
            assert {f"ck_{table}_stage_key", f"ck_{table}_host_id_format", f"ck_{table}_access"} <= checks


# -- the downgrade --------------------------------------------------------------------------------


def test_without_a_row_the_downgrade_restores_the_previous_schema_and_the_upgrade_runs_again(
    at_this: tuple[Engine, str], foundation_command: Any
) -> None:
    engine, url = at_this
    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    assert _version(engine) == PREVIOUS
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('public.executor_host')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regclass('public.audit_run_cell_binding')")).scalar_one() is None
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'audit_run' AND column_name = 'stage_plan'"
        )).scalar_one() == 0
        definition = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'")).scalar_one()
        assert "'stage_plan'" not in definition and "'started_from_run_id'" in definition, definition
        assert "stage_plan" not in connection.execute(text("SELECT pg_get_functiondef('am_guard_audit_run_frozen'::regproc)")).scalar_one()
        for table in ("executor_runner_token", "executor_enrollment", "executor_agent_install"):
            assert connection.execute(text(
                "SELECT is_nullable FROM information_schema.columns WHERE table_name = :t AND column_name = 'connection_id'"),
                {"t": table}).scalar_one() == "NO"
        assert connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'fk_executor_task_token'")).scalar_one().startswith(
            "FOREIGN KEY (claimed_by_token_id, connection_id)")
    _upgrade(foundation_command, url, THIS)
    assert _version(engine) == THIS


@pytest.mark.parametrize("retained", ["host", "revision", "plan", "switch"])
def test_the_downgrade_is_refused_while_any_of_it_exists_and_changes_nothing(
    at_this: tuple[Engine, str], foundation_command: Any, retained: str
) -> None:
    engine, url = at_this
    with engine.begin() as connection:
        if retained == "host":
            _host(connection)
        elif retained == "revision":
            _revision(connection, 1)
        elif retained == "plan":
            _planned_run(connection, _plan("text:main"))
        else:
            connection.execute(text("INSERT INTO stage_layout_switch_event (switch_event_id, layout_key, event_no, enabled, set_by) "
                                    "VALUES (:id, 'default', 1, false, :a)"), {"id": str(StageLayoutSwitchEventId.new()), "a": ACTOR})
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "refusing to downgrade 0062_hosts_stage_models" in refused.stderr, refused.stderr
    assert _version(engine) == THIS


def test_the_downgrade_refusal_names_a_secret_of_a_host(at_this: tuple[Engine, str], foundation_command: Any) -> None:
    """The host row alone refuses too; what is proved is that the secret is counted as a retained class of its own."""
    engine, url = at_this
    with engine.begin() as connection:
        _secret(connection, host_id=_host(connection))
    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "host-bound credentials" in refused.stderr and "executor_host" in refused.stderr, refused.stderr
    assert _version(engine) == THIS
