"""`PROD-11B-V3-STAGE-ID-MIGRATION-01`: ``0033_ar_v3_cite_stage_id`` on a populated ``0032`` database.

`D-225`: the CITE ``StageResult`` of every AR v3 Run was refused by the database, because
``ck_stage_result_stage_id`` (``0002``) admitted nine stage ids and not ``ar_v3_citation_review``.
``0033`` replaces that one CHECK and touches nothing else. Five claims, each against a real
PostgreSQL server:

* **the constraint says exactly the nine ids plus the one** -- read back from
  ``pg_get_constraintdef`` and compared with a list written out here, so a missing or an extra
  id fails; a lookalike id is refused;
* **the same insert is refused at ``0032`` and accepted after the step** -- so the migration, and
  nothing else, is what admits the CITE row;
* **a populated ``0032`` database upgrades without a row changing** and the new constraint is
  validated;
* **the two other CHECKs over the same nine ids are not widened** (``ck_model_call_stage_id``,
  ``ck_finding_observation_stage_id``): the v3 code writes the CITE id into neither, and a
  vocabulary nobody writes is not admitted;
* **the downgrade is refused while a ``stage_result`` row carries the new id, and only then** --
  the refusal changes nothing, deleting the row lifts it, and with no such row the downgrade
  restores ``0002``'s constraint and the upgrade runs again.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from auditmanager.api.schemas.models import ArV3BetaStageId, StageId
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from tests.support.expected_facts import FACTS

HEAD = FACTS.migration_head  # the tree's head: this revision or a later one
THIS = "0033_ar_v3_cite_stage_id"
PREVIOUS = "0032_ar_v3_run_group"
CITE = "ar_v3_citation_review"
#: The nine stages ``0002`` admitted, written out here and not imported from the migration.
NINE = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
    "block_analysis",
    "finding_merge",
    "finding_review",
    "finding_correction",
    "norm_verification",
)
STAGE_CHECK = "ck_stage_result_stage_id"
MODEL_CALL_CHECK = "ck_model_call_stage_id"
OBSERVATION_CHECK = "ck_finding_observation_stage_id"


ROOT = Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "db" / "migrations" / "versions"
CITE_CONTRACT = ROOT / "contracts" / "analysis" / "ar_v3_beta" / "v1" / "stage.json"


def _load_migration(file_name: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, VERSIONS / file_name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _definition(engine: Engine, name: str) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        ).scalar_one()


def _vocabulary(engine: Engine, name: str = STAGE_CHECK) -> list[str]:
    """The quoted literals of the CHECK, in the order the catalogue prints them."""
    return re.findall(r"'([a-z_0-9]+)'::text", _definition(engine, name))


def _validated(engine: Engine, name: str = STAGE_CHECK) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(
            text("SELECT convalidated FROM pg_constraint WHERE conname = :name"), {"name": name},
        ).scalar_one())


def _seed_run(connection: Connection) -> str:
    ids = {
        "project_uid": str(ProjectUid.new()),
        "document_uid": str(DocumentUid.new()),
        "version_uid": str(VersionUid.new()),
        "run_id": str(RunId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project_uid, 'cite stage')"), ids)
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
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest) VALUES (:run_id, :project_uid, :version_uid, :ap, :pb, "
            "'recorded', :digest)"
        ),
        {**ids, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()), "digest": "b" * 64},
    )
    return ids["run_id"]


def _stage(connection: Connection, run_id: str, stage_id: str, *, status: str = "succeeded") -> None:
    error = (
        None if status == "succeeded"
        else '{"code": "internal_error", "message": "the stage failed", "retryable": false}'
    )
    connection.execute(
        text(
            "INSERT INTO stage_result (run_id, stage_id, stage_version, status, error, started_at, finished_at) "
            "VALUES (:run, :stage, '1.0.0', :status, CAST(:error AS jsonb), now(), now())"
        ),
        {"run": run_id, "stage": stage_id, "status": status, "error": error},
    )


def _rows(engine: Engine) -> list[tuple[Any, ...]]:
    with engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(
            "SELECT run_id, stage_id, stage_version, status, artifacts, metrics, error, "
            "started_at, finished_at, created_at FROM stage_result ORDER BY run_id, stage_id"
        )).all()]


def _count(engine: Engine, stage_id: str = CITE) -> int:
    with engine.connect() as connection:
        return int(connection.execute(
            text("SELECT count(*) FROM stage_result WHERE stage_id = :stage"), {"stage": stage_id},
        ).scalar_one())


def _upgrade(foundation_command: Any, database: DatabaseSettings, revision: str) -> None:
    result = foundation_command(_alembic("upgrade", revision), database.url.render_as_string(hide_password=False))
    assert result.returncode == 0, result.describe()


def test_the_migrations_vocabulary_is_0002s_nine_ids_plus_the_profile_stage_of_the_api_and_the_contract() -> None:
    """The migration restates its ids (history must not move), so something else must tie them.

    No database: the nine are ``0002``'s ``STAGE_IDS`` and the API's legacy ``StageId``; the one is
    the API's ``ArV3BetaStageId`` and the stage id of the AR v3 stage extension contract. An eleventh
    id added to either side, or a typo in the migration, fails here before any server is asked.
    """
    this = _load_migration("20261026_0033_ar_v3_cite_stage_id.py", "ar_v3_cite_stage_id_under_test")
    first = _load_migration("20260910_0002_pc01_schema.py", "pc01_schema_under_test")
    contract = json.loads(CITE_CONTRACT.read_text(encoding="utf-8"))["stage"]["stage_id"]
    assert this._REGISTRY_STAGE_IDS == NINE == first.STAGE_IDS == tuple(item.value for item in StageId)
    assert (this._ADDED_STAGE_ID,) == (CITE,) == (contract,) == tuple(item.value for item in ArV3BetaStageId)
    assert this._NEW_STAGE_IDS == (*first.STAGE_IDS, contract)
    assert this.revision == THIS and this.down_revision == PREVIOUS


def test_the_check_reads_back_as_the_nine_ids_plus_the_cite_id(empty_database, foundation_command) -> None:
    _upgrade(foundation_command, empty_database, THIS)
    engine = create_database_engine(empty_database)
    try:
        assert _version(engine) == THIS
        assert _vocabulary(engine) == [*NINE, CITE]  # the order is the migration's, so a reorder shows too
        assert len(set(_vocabulary(engine))) == 10
        assert _validated(engine)
        for lookalike in (CITE + "x", "ar_v3_citation", "AR_V3_CITATION_REVIEW", "ar_v3_citation_review ", "norm_verification2"):
            with pytest.raises(IntegrityError, match=STAGE_CHECK), engine.begin() as connection:
                _stage(connection, _seed_run(connection), lookalike)
    finally:
        engine.dispose()


def test_the_cite_row_is_refused_at_0032_and_accepted_after_the_step(empty_database, foundation_command) -> None:
    _upgrade(foundation_command, empty_database, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        assert _vocabulary(engine) == list(NINE)
        with engine.begin() as connection:  # the control: a registry id is stored at 0032
            _stage(connection, _seed_run(connection), "source_preparation")
        with pytest.raises(IntegrityError, match=STAGE_CHECK), engine.begin() as connection:
            _stage(connection, _seed_run(connection), CITE)
        assert _count(engine) == 0

        _upgrade(foundation_command, empty_database, THIS)
        with engine.begin() as connection:
            run = _seed_run(connection)
            _stage(connection, run, "source_preparation")
            _stage(connection, run, CITE)
            _stage(connection, _seed_run(connection), CITE, status="failed")
        assert _count(engine) == 2
        # the key is still (run, stage): one CITE row per run
        with pytest.raises(IntegrityError, match="pk_stage_result"), engine.begin() as connection:
            _stage(connection, run, CITE)
    finally:
        engine.dispose()


def test_the_cite_row_is_accepted_at_the_head(migrated_engine: Engine) -> None:
    assert _version(migrated_engine) == HEAD
    assert CITE in _vocabulary(migrated_engine)
    with migrated_engine.begin() as connection:
        _stage(connection, _seed_run(connection), CITE)
    assert _count(migrated_engine) == 1


def test_a_populated_0032_database_upgrades_without_a_row_changing(empty_database, foundation_command) -> None:
    _upgrade(foundation_command, empty_database, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            for position in range(3):
                run = _seed_run(connection)
                for stage in NINE[: 3 + position]:
                    _stage(connection, run, stage)
                _stage(connection, run, NINE[8], status="failed")
        before = _rows(engine)
        assert len(before) == 4 + 5 + 6  # populated, not vacuous
        assert _count(engine) == 0

        _upgrade(foundation_command, empty_database, THIS)
        assert _version(engine) == THIS
        assert _rows(engine) == before
        assert _validated(engine)
        assert _vocabulary(engine) == [*NINE, CITE]
    finally:
        engine.dispose()


def test_the_two_other_checks_over_the_nine_ids_are_not_widened(empty_database, foundation_command) -> None:
    _upgrade(foundation_command, empty_database, THIS)
    engine = create_database_engine(empty_database)
    try:
        for name in (MODEL_CALL_CHECK, OBSERVATION_CHECK):
            assert _vocabulary(engine, name) == list(NINE), name
        with pytest.raises(IntegrityError, match=MODEL_CALL_CHECK), engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, "
                    "provider_mode, request_sha256, status, error_code) VALUES (:m, :run, :stage, "
                    "'anthropic', 'a-model', 'recorded', :h, 'failed', 'internal_error')"
                ),
                {"m": str(ModelCallId.new()), "run": _seed_run(connection), "stage": CITE, "h": "d" * 64},
            )
        with engine.begin() as connection:  # the control: the stage the v3 call is journalled under
            connection.execute(
                text(
                    "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, "
                    "provider_mode, request_sha256, status, error_code) VALUES (:m, :run, 'text_analysis', "
                    "'anthropic', 'a-model', 'recorded', :h, 'failed', 'internal_error')"
                ),
                {"m": str(ModelCallId.new()), "run": _seed_run(connection), "h": "d" * 64},
            )
    finally:
        engine.dispose()


def test_the_downgrade_is_refused_while_a_row_carries_the_new_id_and_only_then(
    empty_database, foundation_command
) -> None:
    _upgrade(foundation_command, empty_database, THIS)
    url = empty_database.url.render_as_string(hide_password=False)
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            run = _seed_run(connection)
            _stage(connection, run, "source_preparation")
            _stage(connection, run, CITE)
        rows, definition = _rows(engine), _definition(engine, STAGE_CHECK)

        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0, refused.describe()
        assert "0033 downgrade refused" in refused.stderr, refused.stderr
        assert _version(engine) == THIS  # a refusal changes nothing
        assert _definition(engine, STAGE_CHECK) == definition
        assert _rows(engine) == rows and _count(engine) == 1

        with engine.begin() as connection:  # the row was the only reason
            connection.execute(text("DELETE FROM stage_result WHERE stage_id = :s"), {"s": CITE})
        allowed = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert allowed.returncode == 0, allowed.describe()
        assert _version(engine) == PREVIOUS
        assert _vocabulary(engine) == list(NINE)
        assert [row[1] for row in _rows(engine)] == ["source_preparation"]
    finally:
        engine.dispose()


def test_without_such_a_row_the_downgrade_restores_the_nine_id_check_and_the_upgrade_runs_again(
    empty_database, foundation_command
) -> None:
    _upgrade(foundation_command, empty_database, HEAD)
    url = empty_database.url.render_as_string(hide_password=False)
    engine = create_database_engine(empty_database)
    try:
        before = _definition(engine, STAGE_CHECK)
        with engine.begin() as connection:
            run = _seed_run(connection)
            for stage in NINE:
                _stage(connection, run, stage)
        rows = _rows(engine)
        down = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        assert _version(engine) == PREVIOUS
        assert _vocabulary(engine) == list(NINE)
        assert _validated(engine)
        assert _rows(engine) == rows
        with pytest.raises(IntegrityError, match=STAGE_CHECK), engine.begin() as connection:
            _stage(connection, _seed_run(connection), CITE)
        _upgrade(foundation_command, empty_database, HEAD)
        assert _definition(engine, STAGE_CHECK) == before
        assert _rows(engine) == rows
    finally:
        engine.dispose()
