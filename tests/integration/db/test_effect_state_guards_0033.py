"""`DEBT-EFFECT-GUARDS-0033`: the effect-table state guards, before and after ``0018``.

The register still listed `D-148` (the guards fire on UPDATE only) and `D-142` (an interrupted
artifact intent has no settlement state) as open, but ``0018_norm_custody`` already closed both.
``test_norm_custody_migration.py`` asserts the head schema. This module adds the two
things it does not:

* the boundary itself, on one populated database: ``0017`` accepts a terminal row inserted
  directly (the control that gives the later refusal its meaning), ``0018`` keeps those rows
  and refuses every new one;
* the ``0018`` downgrade and re-upgrade on a database that holds ordinary effect rows
  (``prepared`` and ``bound``), which the sibling's empty-database downgrade does not exercise.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    DocumentUid,
    JobId,
    LeaseId,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.storage.models import derive_blob_id
from tests.support.expected_facts import FACTS

_STAGE = "text_analysis"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _upgrade(foundation_command, url: str, target: str) -> None:
    result = foundation_command(_alembic("upgrade", target), url)
    assert result.returncode == 0, result.describe()


def _seed_attempt(connection: Connection, label: str) -> dict[str, str]:
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()), "job": str(JobId.new()),
        "attempt": str(AttemptId.new()), "lease": str(LeaseId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, :name)"),
                       {**ids, "name": label})
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, :name)"), {**ids, "name": label})
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, "
                            "version_ordinal, media_type, byte_size, sha256, page_count) "
                            "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                       {**ids, "sha": "a" * 64})
    connection.execute(text("INSERT INTO audit_run (run_id, project_uid, version_uid, "
                            "analysis_profile_id, prompt_bundle_id, provider_mode, "
                            "frozen_input_digest) VALUES (:run, :project, :version, :profile, "
                            ":bundle, 'recorded', :digest)"),
                       {**ids, "profile": str(AnalysisProfileId.new()),
                        "bundle": str(PromptBundleId.new()), "digest": "b" * 64})
    connection.execute(text("INSERT INTO job (job_id, run_id, state) VALUES (:job, :run, 'queued')"), ids)
    connection.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) "
                            "VALUES (:attempt, :job, :token)"), {**ids, "token": f"tok-{label}"})
    connection.execute(text("INSERT INTO lease (lease_id, job_id, attempt_id) "
                            "VALUES (:lease, :job, :attempt)"), ids)
    return ids


def _blob(connection: Connection, digit: str) -> str:
    sha, size = digit * 64, 30 + int(digit)
    blob_id = str(derive_blob_id(sha256=sha, size=size))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob_id})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob_id})
    connection.execute(text("UPDATE blob SET state = 'available', sha256 = :d, size_bytes = :s, "
                            "media_type = 'application/pdf' WHERE blob_id = :b"),
                       {"b": blob_id, "d": sha, "s": size})
    return blob_id


def _effect(connection: Connection, ids: dict[str, str], *, state: str | None = None,
            error_code: str | None = None) -> str:
    call = str(ModelCallId.new())
    columns = ", state, error_code" if state else ""
    values = ", :state, :error_code" if state else ""
    connection.execute(text(
        "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, attempt_id, stage_id, "
        f"provider, model_identity, provider_mode, request_sha256{columns}) VALUES (:call, :run, "
        f":job, :attempt, '{_STAGE}', 'anthropic', 'a-model', 'recorded', :sha{values})"
    ), {**ids, "call": call, "sha": "1" * 64, "state": state, "error_code": error_code})
    return call


def _publication(connection: Connection, ids: dict[str, str], blob: str, *,
                 state: str | None = None) -> None:
    extra = {
        None: ("", ""),
        "bound": (", state, artifact_role, bound_at",
                  ", 'bound', 'analysis.text', clock_timestamp()"),
        "abandoned": (", state, abandoned_at", ", 'abandoned', clock_timestamp()"),
    }[state]
    connection.execute(text(
        "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
        f"blob_id, blob_role{extra[0]}) VALUES (:run, :job, :attempt, '{_STAGE}', :blob, "
        f"'stage_output'{extra[1]})"
    ), {**ids, "blob": blob})


def _refused_on_insert(connection: Connection, insert) -> None:
    with pytest.raises(DBAPIError) as refused:
        with connection.begin_nested():
            insert()
    assert getattr(refused.value.orig, "sqlstate", None) == "AM001", refused.value
    assert "may not be created in state" in str(refused.value.orig)


def _guard_events(connection: Connection) -> dict[str, str]:
    """The trigger definitions of the two effect-table state guards, keyed by table."""
    return dict(connection.execute(text(
        "SELECT t.tgrelid::regclass::text, pg_get_triggerdef(t.oid) FROM pg_trigger t "
        "WHERE t.tgname IN ('trg_provider_call_effect_state_guard', "
        "'trg_analysis_artifact_state_guard') AND NOT t.tgisinternal"
    )).all())


def _states(connection: Connection) -> dict[str, list[str]]:
    return {
        "provider_call_effect": sorted(connection.execute(
            text("SELECT state FROM provider_call_effect")).scalars()),
        "analysis_artifact_publication": sorted(connection.execute(
            text("SELECT state FROM analysis_artifact_publication")).scalars()),
    }


def test_0018_keeps_the_terminal_rows_0017_accepted_and_refuses_new_ones(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, "0017_execution_queue")
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_attempt(connection, "d148")
            # The control: at 0017 the guards fire on UPDATE only, so a direct INSERT creates
            # a terminal row. Without this the refusal below could be a malformed statement.
            _effect(connection, ids, state="outcome_unknown", error_code="dependency_unavailable")
            _effect(connection, ids, state="abandoned", error_code="analysis_failed")
            _publication(connection, ids, _blob(connection, "1"), state="bound")
            assert all("BEFORE UPDATE ON" in d for d in _guard_events(connection).values())
        _upgrade(foundation_command, url, "head")
        with engine.begin() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() \
                == FACTS.migration_head
            assert _states(connection) == {
                "provider_call_effect": ["abandoned", "outcome_unknown"],
                "analysis_artifact_publication": ["bound"],
            }
            guards = _guard_events(connection)
            assert set(guards) == {"provider_call_effect", "analysis_artifact_publication"}
            assert all("BEFORE INSERT OR UPDATE ON" in d for d in guards.values()), guards

            for state, code in (("outcome_unknown", "dependency_unavailable"),
                                ("abandoned", "analysis_failed")):
                _refused_on_insert(connection, lambda s=state, c=code: _effect(
                    connection, ids, state=s, error_code=c))
            refused_blob = _blob(connection, "2")
            for state in ("bound", "abandoned"):
                _refused_on_insert(connection, lambda s=state: _publication(
                    connection, ids, refused_blob, state=s))

            # The controls: the initial state is accepted, and the legal edges still work.
            call = _effect(connection, ids)
            _publication(connection, ids, _blob(connection, "3"))
            _publication(connection, ids, _blob(connection, "4"))
            connection.execute(text(
                "UPDATE provider_call_effect SET state = 'response_received', "
                "response_sha256 = :r, input_tokens = 1, output_tokens = 1, latency_ms = 1 "
                "WHERE model_call_id = :call"), {"call": call, "r": "f" * 64})
            connection.execute(text(
                "UPDATE analysis_artifact_publication SET state = 'abandoned', "
                "abandoned_at = clock_timestamp() WHERE blob_id = :b"),
                {"b": str(derive_blob_id(sha256="3" * 64, size=33))})
            connection.execute(text(
                "UPDATE analysis_artifact_publication SET state = 'bound', "
                "artifact_role = 'analysis.text', bound_at = clock_timestamp() WHERE blob_id = :b"),
                {"b": str(derive_blob_id(sha256="4" * 64, size=34))})
            assert _states(connection) == {
                "provider_call_effect": ["abandoned", "outcome_unknown", "response_received"],
                "analysis_artifact_publication": ["abandoned", "bound", "bound"],
            }
    finally:
        engine.dispose()


def test_0018_round_trips_with_prepared_and_bound_effect_rows(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, "0018_norm_custody")
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_attempt(connection, "round-trip")
            _effect(connection, ids)
            _publication(connection, ids, _blob(connection, "5"))
            bound = _blob(connection, "6")
            _publication(connection, ids, bound)
            connection.execute(text(
                "UPDATE analysis_artifact_publication SET state = 'bound', "
                "artifact_role = 'analysis.text', bound_at = clock_timestamp() WHERE blob_id = :b"),
                {"b": bound})
            before = _states(connection)
        assert before == {"provider_call_effect": ["prepared"],
                          "analysis_artifact_publication": ["bound", "prepared"]}

        down = foundation_command(_alembic("downgrade", "0017_execution_queue"), url)
        assert down.returncode == 0, down.describe()
        with engine.connect() as connection:
            assert all("BEFORE UPDATE ON" in d for d in _guard_events(connection).values())
            assert _states(connection) == before

        _upgrade(foundation_command, url, "0018_norm_custody")
        with engine.connect() as connection:
            assert all("BEFORE INSERT OR UPDATE ON" in d for d in _guard_events(connection).values())
            assert _states(connection) == before
    finally:
        engine.dispose()
