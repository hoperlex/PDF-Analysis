"""The shipped read adapter presents a v2 merge group as one Finding."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from auditmanager.api.schemas.findings import finding_body, finding_detail_body
from auditmanager.bootstrap.adapters import FindingAdapter
from auditmanager.findings import published_finding_count, published_findings
from auditmanager.shared.errors import DomainError


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> FindingAdapter:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def install_c_collation(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        dbapi_connection.create_collation("C", lambda a, b: (a > b) - (a < b))

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE finding (
                finding_uid text PRIMARY KEY, project_uid text, version_uid text,
                allocated_by_run_id text, category text, canonical_observation_id text
            )
        """))
        conn.execute(text("""
            CREATE TABLE finding_observation (
                finding_observation_id text PRIMARY KEY, run_id text, finding_uid text,
                category text, finding_text text, recommendation_text text, stage_id text,
                analysis_profile_id text, prompt_bundle_id text, model_call_id text,
                provider_mode text, proposed_severity text, grounded boolean, created_at text
            )
        """))
        conn.execute(text("""
            CREATE TABLE finding_evidence (
                finding_observation_id text, evidence_ordinal integer, page_number integer,
                quote text, char_start integer, char_end integer, block_id text
            )
        """))
        conn.execute(text("""
            INSERT INTO finding VALUES ('fnd_one', 'prj_one', 'ver_one', 'run_one',
                                        'dimensions', 'fobs_a')
        """))
        conn.execute(text("""
            INSERT INTO finding_observation VALUES
            ('fobs_a', 'run_one', 'fnd_one', 'dimensions', 'Канонический вывод',
             'Проверить размер', 'text_analysis', 'ap_v2', 'pb_v2', 'mc_one',
             'recorded', 'critical', 1, '2026-10-23'),
            ('fobs_b', 'run_one', 'fnd_one', 'dimensions', 'Повторное наблюдение',
             'Проверить размер', 'text_analysis', 'ap_v2', 'pb_v2', 'mc_one',
             'recorded', 'operational', 1, '2026-10-23')
        """))
        conn.execute(text("""
            INSERT INTO finding_evidence VALUES
            ('fobs_a', 0, 1, 'Размер 20', 0, 9, NULL),
            ('fobs_b', 0, 2, 'Размер 20', 10, 19, NULL)
        """))

    monkeypatch.setattr(
        "auditmanager.decisions.current_verdict",
        lambda _session, _finding_uid: SimpleNamespace(current_verdict="pending"),
    )
    monkeypatch.setattr(
        "auditmanager.decisions.decision_history", lambda _session, _finding_uid: (),
    )
    yield FindingAdapter(sessionmaker(engine))
    engine.dispose()


def test_list_and_detail_return_one_canonical_finding_with_merged_member(
    adapter: FindingAdapter,
) -> None:
    with adapter._sessions() as session:
        assert published_finding_count(session, "run_one") == 1
        assert len(published_findings(session, "run_one")) == 2
    listed = adapter.list_run_findings(run_id="run_one")
    assert len(listed) == 1
    body = finding_body(listed[0])
    assert body["finding_uid"] == "fnd_one"
    assert body["observation"]["finding_observation_id"] == "fobs_a"
    assert body["observation"]["proposed_severity"] == "critical"
    assert body["merged_observations"][0]["finding_observation_id"] == "fobs_b"
    assert body["merged_observations"][0]["proposed_severity"] == "operational"
    assert body["merged_observations"][0]["evidence"][0]["page_number"] == 2

    detail = finding_detail_body(adapter.get_finding(finding_uid="fnd_one"))
    assert detail["observation"] == body["observation"]
    assert detail["merged_observations"] == body["merged_observations"]
    assert detail["decision_event_count"] == 0


@pytest.mark.parametrize("canonical", ["fobs_missing", None])
def test_missing_canonical_is_refused_instead_of_showing_duplicate_findings(
    adapter: FindingAdapter, canonical: str | None,
) -> None:
    with adapter._sessions() as session:  # this corruption is isolated to the test DB
        session.execute(
            text("UPDATE finding SET canonical_observation_id = :canonical"),
            {"canonical": canonical},
        )
        session.commit()
    with pytest.raises(DomainError):
        adapter.list_run_findings(run_id="run_one")


def test_exact_legacy_single_member_without_canonical_remains_readable(
    adapter: FindingAdapter,
) -> None:
    with adapter._sessions() as session:
        session.execute(text("""
            INSERT INTO finding VALUES ('fnd_legacy', 'prj_one', 'ver_one', 'run_one',
                                        'layout', NULL)
        """))
        session.execute(text("""
            INSERT INTO finding_observation VALUES
            ('fobs_legacy', 'run_one', 'fnd_legacy', 'layout', 'Проверить план',
             'Согласовать план', 'text_analysis', 'ap_v1', 'pb_v1', 'mc_one',
             'recorded', NULL, 1, '2026-10-23')
        """))
        session.commit()
    listed = adapter.list_run_findings(run_id="run_one")
    assert {view.finding_uid for view in listed} == {"fnd_one", "fnd_legacy"}
    legacy = finding_body(adapter.get_finding(finding_uid="fnd_legacy").finding)
    assert legacy["observation"]["finding_observation_id"] == "fobs_legacy"
    assert "merged_observations" not in legacy
    assert "proposed_severity" not in legacy["observation"]
