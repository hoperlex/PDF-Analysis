"""`RUN-STAGES-01` (contract 1.46.0): the SQL of ``runs/stage_facts.py`` against a real migrated database (head ``0062``).

HEAVY: PostgreSQL. The assembly is pure and is held by ``tests/unit/runs/test_stage_facts.py``; what only a database can say is that the five
statements -- the run, the stage results, the call journal (effects joined to the ``model_call`` row they ended in, plus the rows no effect names),
the cell bindings and the connection revision of a legacy run -- name real columns, join as the journal is written and give the rows the assembly
expects. Run once by the integrator on a throwaway database (`HOSTS-PLAN.md` section 6); it is written with the suite's ``migrated_engine``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import sessionmaker

from auditmanager.runs.stage_facts import read_run_stage_facts
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    DocumentUid,
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    JobId,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

ACTOR = f"usr_{'0' * 26}"
PLAN = {"cells": [
    {"cell_key": "text:main", "model_id": "claude-sonnet-5-5", "effort": "medium", "access": "subscription"},
    {"cell_key": "norms:main", "model_id": "claude-sonnet-5-5", "effort": "medium", "access": "subscription"},
]}


def _run(connection: Connection, *, plan: dict[str, Any] | None = None, revision_id: str | None = None) -> str:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'stage-facts')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'stage-facts')"), ids)
    connection.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "frozen_input_digest, connection_revision_id, binding_state, stage_plan) "
        "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, :revision, :binding, CAST(:plan AS jsonb))"),
        {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64,
         "revision": revision_id, "binding": "pending" if plan is not None else "frozen_at_start",
         "plan": None if plan is None else json.dumps(plan)})
    return ids["run"]


def _no_review(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests read the facts of a planned run inserted without the command and consent v2 a real start carries
    (`HOSTS-LAYOUT-01`: a planned run never starts without them, and `read_run_cost_policy` refuses one that has none). The extended
    review's own reader is tested on its own; here it stands absent, so the facts are read from the stage rows and the journal."""
    import auditmanager.runs.extended_review as extended_review

    monkeypatch.setattr(extended_review, "read_extended_review", lambda *args, **kwargs: None)


def _connection_revision(connection: Connection) -> str:
    connection_id, revision_id = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:id, 'http_api', 'kzSonnet', :actor)"),
        {"id": connection_id, "actor": ACTOR})
    connection.execute(text(
        "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, billing, "
        "allow_client_documents, timeout_seconds, api_flavour, base_url, transport) VALUES (:id, :c, 1, :actor, 'claude-opus-5', "
        "'anthropic/claude-opus-5', 'not_metered', false, 60, 'openai_chat', 'https://proxy.test', 'direct')"),
        {"id": revision_id, "c": connection_id, "actor": ACTOR})
    return revision_id


def _stage(connection: Connection, run_id: str, stage_id: str, status: str = "succeeded") -> None:
    connection.execute(text(
        "INSERT INTO stage_result (run_id, stage_id, stage_version, status, started_at, finished_at) "
        "VALUES (:run, :stage, '1.0.0', :status, now() - interval '5 minutes', now() - interval '4 minutes')"),
        {"run": run_id, "stage": stage_id, "status": status})


def _call(connection: Connection, run_id: str, *, phase: str | None, stage_key: str | None = None, access: str | None = None,
          basis: str = "estimated", cost: int = 0, tokens: tuple[int, int] = (100, 10), request: str = "c") -> str:
    call_id = str(ModelCallId.new())
    parameters = {} if phase is None else {"extended_phase": phase}
    connection.execute(text(
        "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, provider_mode, parameters, request_sha256, "
        "response_sha256, input_tokens, output_tokens, latency_ms, cost_micros, cost_basis, status, stage_key, access) "
        "VALUES (:id, :run, 'text_analysis', 'anthropic', 'claude-sonnet-5-5', 'recorded', CAST(:parameters AS jsonb), :request, :response, "
        ":tin, :tout, 1500, :cost, :basis, 'succeeded', :stage_key, :access)"),
        {"id": call_id, "run": run_id, "parameters": json.dumps(parameters), "request": request * 64, "response": "d" * 64,
         "tin": tokens[0], "tout": tokens[1], "cost": cost, "basis": basis, "stage_key": stage_key, "access": access})
    return call_id


def _job(connection: Connection, run_id: str) -> tuple[str, str]:
    """The run's one job (``uq_job_run_id``) and its one attempt, which every effect of the run names."""
    job_id, attempt_id = str(JobId.new()), str(AttemptId.new())
    connection.execute(text("INSERT INTO job (job_id, run_id) VALUES (:job, :run)"), {"job": job_id, "run": run_id})
    connection.execute(text("INSERT INTO attempt (attempt_id, job_id, execution_token) VALUES (:attempt, :job, 'test-token')"),
                       {"attempt": attempt_id, "job": job_id})
    return job_id, attempt_id


def _effect(connection: Connection, run_id: str, authority: tuple[str, str], *, call_id: str | None = None, stage_key: str | None,
            access: str | None, complete: bool, request: str = "e") -> str:
    job_id, attempt_id = authority
    call_id = call_id or str(ModelCallId.new())
    connection.execute(text(
        "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, attempt_id, stage_id, provider, model_identity, provider_mode, "
        "parameters, request_sha256, stage_key, access) VALUES (:id, :run, :job, :attempt, 'text_analysis', 'anthropic', "
        "'claude-sonnet-5-5', 'recorded', '{}'::jsonb, :request, :stage_key, :access)"),
        {"id": call_id, "run": run_id, "job": job_id, "attempt": attempt_id, "request": request * 64, "stage_key": stage_key, "access": access})
    if complete:
        connection.execute(text(
            "UPDATE provider_call_effect SET state = 'response_received', response_sha256 = :r, input_tokens = 100, output_tokens = 10, "
            "latency_ms = 1500 WHERE model_call_id = :id"), {"id": call_id, "r": "d" * 64})
        connection.execute(text("UPDATE provider_call_effect SET state = 'completed', final_model_call_id = :id WHERE model_call_id = :id"),
                           {"id": call_id})
    return call_id


@pytest.fixture
def sessions(migrated_engine: Engine) -> sessionmaker:
    return sessionmaker(bind=migrated_engine, expire_on_commit=False)


def test_a_planned_run_reads_its_stage_results_and_a_journal_of_new_and_old_rows(
    migrated_engine: Engine, sessions: sessionmaker, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_review(monkeypatch)
    with migrated_engine.begin() as connection:
        run_id = _run(connection, plan=PLAN)
        _stage(connection, run_id, "source_preparation")
        # a new row: effect and model_call, both carrying the key and the access (0062)
        done = _call(connection, run_id, phase=None, stage_key="text", access="subscription", request="1")
        authority = _job(connection, run_id)
        _effect(connection, run_id, authority, call_id=done, stage_key="text", access="subscription", complete=True, request="1")
        # an old row: no effect, no key, an unmetered cost basis, the chip derived from its extended phase
        _call(connection, run_id, phase="v3:w001:blocks:b001", basis="unmetered", request="2")
        # a call in flight: an effect only, with its key
        _effect(connection, run_id, authority, stage_key="norms", access="subscription", complete=False, request="3")

    answer = read_run_stage_facts(sessions, None, run_id=run_id, include_server=True)

    assert (answer["run_id"], answer["plan_source"], answer["state"]) == (run_id, "stage_plan", "created")
    chips = {entry["chip"]: entry for entry in answer["items"]}
    assert list(chips) == ["preparation", "text", "blocks", "norms"]  # the plan's two rows, the stage result's chip and the old row's chip
    assert chips["preparation"]["facts"]["state"] == "running" and chips["preparation"]["plan"] == []  # one of three, the run is open
    text_facts = chips["text"]["facts"]
    assert (text_facts["calls_succeeded"], text_facts["calls_failed"], text_facts["input_tokens"]) == (1, 0, 100)
    assert text_facts["subscription_input_tokens"] == 100  # by the access the new row carries
    assert chips["text"]["plan"][0]["model_id"] == "claude-sonnet-5-5" and "server" not in chips["text"]["plan"][0]  # not bound yet
    blocks = chips["blocks"]["facts"]
    assert (blocks["calls_succeeded"], blocks["subscription_output_tokens"]) == (1, 10)  # an unmetered old row is a subscription call
    assert chips["blocks"]["plan"] == []  # the plan froze no cell for the row, and the answer does not invent one
    norms = chips["norms"]["facts"]
    assert (norms["state"], norms["calls_succeeded"], norms["calls_failed"]) == ("running", 0, 0)  # in flight: neither
    assert "finished_at" not in norms and "started_at" in norms


def test_the_viewers_read_leaves_out_the_access_of_every_cell(
    migrated_engine: Engine, sessions: sessionmaker, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_review(monkeypatch)
    with migrated_engine.begin() as connection:
        run_id = _run(connection, plan=PLAN)
    answer = read_run_stage_facts(sessions, None, run_id=run_id, include_server=False)
    assert {entry["chip"] for entry in answer["items"]} == {"text", "norms"}
    assert all("access" not in cell and "server" not in cell for entry in answer["items"] for cell in entry["plan"])


def test_a_run_without_a_plan_takes_the_model_server_and_access_of_its_connection_revision(
    migrated_engine: Engine, sessions: sessionmaker,
) -> None:
    with migrated_engine.begin() as connection:
        run_id = _run(connection, revision_id=_connection_revision(connection))
        _stage(connection, run_id, "text_analysis")
        _call(connection, run_id, phase=None, basis="unmetered")
    answer = read_run_stage_facts(sessions, None, run_id=run_id, include_server=True)
    assert answer["plan_source"] == "run_binding"
    text_chip = next(entry for entry in answer["items"] if entry["chip"] == "text")
    assert text_chip["plan"] == [{"role": "main", "model_id": "claude-opus-5", "server": "kzSonnet", "access": "subscription"}]
    assert text_chip["facts"]["state"] == "done" and text_chip["facts"]["calls_succeeded"] == 1
    viewer = read_run_stage_facts(sessions, None, run_id=run_id, include_server=False)
    assert next(entry for entry in viewer["items"] if entry["chip"] == "text")["plan"] == [{"role": "main", "model_id": "claude-opus-5"}]


def test_an_unknown_run_is_not_found(sessions: sessionmaker) -> None:
    with pytest.raises(DomainError) as refusal:
        read_run_stage_facts(sessions, None, run_id=str(RunId.new()), include_server=True)
    assert refusal.value.code is ErrorCode.NOT_FOUND


def test_a_journal_row_with_a_phase_the_map_does_not_know_is_refused_by_the_reader(
    migrated_engine: Engine, sessions: sessionmaker,
) -> None:
    with migrated_engine.begin() as connection:
        run_id = _run(connection)
        _call(connection, run_id, phase="v3:w001:something_new:b001")
    with pytest.raises(DomainError) as refusal:
        read_run_stage_facts(sessions, None, run_id=run_id, include_server=True)
    assert refusal.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
