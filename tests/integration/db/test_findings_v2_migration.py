"""W56a 0022: current schema, populated forward upgrade and refused downgrade.

All databases are private throwaways supplied by the DB suite. Historical
migrations remain unchanged; only the new 0022 step owns these assertions.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

HEAD = "0022_findings_v2"
PREVIOUS = "0021_portal_bundles"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _seed_legacy_finding(engine: Engine, *, with_observation: bool) -> tuple[str, str | None]:
    project, document, version, run, finding = (
        str(cls.new())
        for cls in (ProjectUid, DocumentUid, VersionUid, RunId, FindingUid)
    )
    observation = str(FindingObservationId.new()) if with_observation else None
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'legacy AR')"), {"p": project}
        )
        connection.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) "
                 "VALUES (:d, :p, 'source')"),
            {"d": document, "p": project},
        )
        connection.execute(
            text("INSERT INTO document_version "
                 "(version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                 "VALUES (:v, :d, 1, 'application/pdf', 1024, :h, 1)"),
            {"v": version, "d": document, "h": "a" * 64},
        )
        connection.execute(
            text("INSERT INTO audit_run "
                 "(run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
                 "provider_mode, frozen_input_digest) "
                 "VALUES (:r, :p, :v, :ap, :pb, 'recorded', :h)"),
            {
                "r": run, "p": project, "v": version,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()), "h": "b" * 64,
            },
        )
        connection.execute(
            text("INSERT INTO finding "
                 "(finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
                 "VALUES (:f, :p, :v, :r, 'internal_contradiction')"),
            {"f": finding, "p": project, "v": version, "r": run},
        )
        if observation is not None:
            connection.execute(
                text("INSERT INTO finding_observation "
                     "(finding_observation_id, run_id, finding_uid, stage_id, category, "
                     "finding_text, recommendation_text, grounded, analysis_profile_id, "
                     "prompt_bundle_id, provider_mode) "
                     "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', "
                     "'A conflict', 'Resolve the conflict', true, :ap, :pb, 'recorded')"),
                {
                    "o": observation, "r": run, "f": finding,
                    "ap": str(AnalysisProfileId.new()),
                    "pb": str(PromptBundleId.new()),
                },
            )
    return finding, observation


def test_clean_upgrade_has_the_v2_columns_and_guards(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        columns = {
            row[0]
            for row in connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE (table_name = 'finding' AND column_name = 'canonical_observation_id') "
                "OR (table_name = 'finding_observation' AND column_name = 'proposed_severity') "
                "OR (table_name = 'expert_decision_event' AND column_name = 'severity') "
                "OR (table_name = 'finding_current_verdict' AND column_name = 'decided_severity')"
            ))
        }
        assert columns == {
            "canonical_observation_id", "proposed_severity", "severity", "decided_severity"
        }
        constraints = {
            row[0]: row[1]
            for row in connection.execute(text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname IN ('ck_finding_category', 'ck_finding_observation_category', "
                "'ck_finding_observation_ungrounded_reason', "
                "'ck_expert_decision_event_severity_accept_only', "
                "'fk_finding_canonical_observation', 'ck_model_call_error_code')"
            ))
        }
        assert len(constraints) == 6
        assert "documentation" in constraints["ck_finding_category"]
        assert "quote_in_recognised_text" in constraints["ck_finding_observation_ungrounded_reason"]
        assert "event_type" in constraints["ck_expert_decision_event_severity_accept_only"]
        assert "model_identity_mismatch" in constraints["ck_model_call_error_code"]


def test_populated_0021_backfills_the_sole_observation_and_refuses_downgrade(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_previous = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_previous.returncode == 0, at_previous.describe()
    engine = create_database_engine(empty_database)
    try:
        finding, observation = _seed_legacy_finding(engine, with_observation=True)
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert connection.execute(text(
                "SELECT canonical_observation_id FROM finding WHERE finding_uid = :f"
            ), {"f": finding}).scalar_one() == observation
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert "0022 downgrade refused: retained finding" in refused.stderr
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    finally:
        engine.dispose()


def test_corrupt_0021_finding_without_observation_stops_backfill(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_previous = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_previous.returncode == 0, at_previous.describe()
    engine = create_database_engine(empty_database)
    try:
        _seed_legacy_finding(engine, with_observation=False)
        refused = foundation_command(_alembic("upgrade", "head"), url)
        assert refused.returncode != 0
        assert "without exactly one grounded observation" in refused.stderr
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
            assert connection.execute(text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'finding' AND column_name = 'canonical_observation_id'"
            )).scalar_one() == 0
    finally:
        engine.dispose()
