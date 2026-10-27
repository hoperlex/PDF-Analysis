"""`AR-V3-DECISIONS-01`: ``0036_cite_partition_v3`` -- the AR v3 CITE stage certifies a citation partition.

``0023`` made the citation partition of a finding observation a certificate that the deferred
constraint triggers check at commit (``am_verify_norm_citation_partition``): the stored count must
equal the immutable citation rows, and the Run must have a *succeeded* ``norm_verification`` stage
and a pinned verified retrieval set. The AR v3 beta Run has a CITE stage of another name
(``ar_v3_citation_review``, ``0033``), so the commit of a published v3 finding was refused. ``0036``
widens that one stage test. Claims, each against a real PostgreSQL server:

* **the function is ``0035``'s body with exactly the stage test widened** -- compared with the text
  read from the database at ``0035``, not with the migration's own constant;
* **the same certified finding is refused at ``0035`` and accepted at ``0036``** when the Run's
  only succeeded CITE stage is the v3 one; the control (the v1/v2 stage) is accepted at both;
* **nothing else certifies**: a failed v3 stage, a succeeded ``text_analysis`` stage and no stage
  at all are refused at ``0036``;
* **the downgrade is refused while a certified observation rests on the v3 stage only, and only
  then**, and with no such row it restores ``0035``'s function byte for byte.

The prerequisite rows (snapshot, document, paragraph, verified retrieval set, which have their own
deferred checks) are seeded with ``session_replication_role = replica`` and the certified rows are
written afterwards with every trigger active, so the deferred partition trigger fires at COMMIT.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from tests.support.expected_facts import FACTS

HEAD = FACTS.migration_head
THIS = "0036_cite_partition_v3"
PREVIOUS = "0035_comparison_records"
V3 = "ar_v3_citation_review"
V1 = "norm_verification"
FUNCTION = "am_verify_norm_citation_partition"
REFUSAL = "certified citation partition needs succeeded CITE stage"
OLD_TEST = "st.stage_id = 'norm_verification'"
NEW_TEST = "st.stage_id IN ('norm_verification', 'ar_v3_citation_review')"
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
QUOTE = "Минимальная ширина эвакуационных путей составляет 1,4 м."
PARAGRAPH = "Текст абзаца. " + QUOTE + " Конец абзаца."
ROOT = Path(__file__).resolve().parents[3]


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _upgrade(foundation_command: Any, database: DatabaseSettings, revision: str) -> None:
    result = foundation_command(_alembic("upgrade", revision), database.url.render_as_string(hide_password=False))
    assert result.returncode == 0, result.describe()


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _source(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT prosrc FROM pg_proc WHERE proname = :name"), {"name": FUNCTION},
        ).scalar_one()


def _uid(prefix: str) -> str:
    return prefix + "_" + "".join(random.choices(ALPHABET, k=26))


def _seed_run(connection: Connection) -> dict[str, str]:
    """A Run pinned to a verified retrieval set, with one citable paragraph; no stage row yet."""
    ids = {name: _uid(prefix) for name, prefix in (
        ("project", "prj"), ("document", "doc"), ("version", "ver"), ("run", "run"),
        ("snapshot", "ns"), ("ndoc", "ndoc"), ("npar", "npar"), ("set", "nrs"),
    )}
    connection.execute(text("SET LOCAL session_replication_role = replica"))
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, content_digest, "
        "undated_documents, document_count, segmentation_profile, repair_count, unreliable_count) "
        "VALUES (:snapshot, :key, :key, :h, 0, 1, 'seg', 0, 0)"), {**ids, "h": "c" * 64, "key": "key-" + ids["snapshot"]})
    pk = connection.execute(text(
        "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, slug, title, "
        "doc_type, source_attribution, pdf_page_count, block_count, page_heading_count, "
        "recognised_characters, paragraph_count) VALUES (:ndoc, :snapshot, 'ref', 'SP_1', 'title', 'SP', "
        "'unattributed', 3, 1, 0, 100, 1) RETURNING norm_document_pk"), ids).scalar_one()
    connection.execute(text(
        "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal, "
        "page_label, block_ref, char_offset, char_length, kind, text) VALUES (:npar, :snapshot, :pk, 0, 1, "
        "'b1', 0, :length, 'body', :text)"), {**ids, "pk": pk, "text": PARAGRAPH, "length": len(PARAGRAPH)})
    connection.execute(text(
        "INSERT INTO norm_retrieval_set (norm_retrieval_set_id, norms_snapshot_id, map_sha256, "
        "reviewed_content_key, chunking_profile, embedding_profile, builder_version, state, "
        "expected_set_sha256, observed_set_sha256, expected_catalogue_sha256, observed_catalogue_sha256, "
        "set_blob_id, set_size_bytes, catalogue_blob_id, catalogue_size_bytes, prompt_part_characters) "
        "VALUES (:set, :snapshot, :h, :key, 'chunk', 'embed', 'b1', 'verified', :h, :h, :h, :h, "
        "'blob_" + "0" * 26 + "', 10, 'blob_" + "1" * 26 + "', 10, 100)"),
        {**ids, "h": "d" * 64, "key": "key-" + ids["snapshot"]})
    connection.execute(text("SET LOCAL session_replication_role = origin"))
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'partition')"), ids)
    connection.execute(text(
        "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'doc')"), ids)
    connection.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
        "sha256, page_count) VALUES (:version, :document, 1, 'application/pdf', 1, :h, 1)"), {**ids, "h": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
        "provider_mode, frozen_input_digest, norms_snapshot_id, norm_retrieval_set_id) VALUES (:run, :project, "
        ":version, :ap, :pb, 'recorded', :h, :snapshot, :set)"),
        {**ids, "ap": _uid("ap"), "pb": _uid("pb"), "h": "b" * 64})
    return ids


def _stage(connection: Connection, run: str, stage: str, status: str = "succeeded") -> None:
    error = None if status == "succeeded" else '{"code": "internal_error", "message": "x", "retryable": false}'
    connection.execute(text(
        "INSERT INTO stage_result (run_id, stage_id, stage_version, status, error, started_at, finished_at) "
        "VALUES (:run, :stage, '1.0.0', :status, CAST(:error AS jsonb), now(), now())"),
        {"run": run, "stage": stage, "status": status, "error": error})


def _certified_observation(connection: Connection, ids: dict[str, str], *, count: int = 1) -> None:
    """One grounded normative finding with one citation; its partition is checked at COMMIT."""
    finding, observation = _uid("fnd"), _uid("fobs")
    connection.execute(text(
        "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
        "VALUES (:f, :project, :version, :run, 'evacuation')"), {**ids, "f": finding})
    connection.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, "
        "finding_text, recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "proposed_severity, required_value, stated_value, norm_citation_count) SELECT :o, run_id, :f, "
        "'text_analysis', 'evacuation', 'text', 'recommendation', true, analysis_profile_id, prompt_bundle_id, "
        "provider_mode, 'operational', '1,4 м', '1,2 м', :count FROM audit_run WHERE run_id = :run"),
        {**ids, "o": observation, "f": finding, "count": count})
    connection.execute(text(
        "INSERT INTO finding_observation_norm_citation (finding_observation_id, citation_ordinal, run_id, "
        "norms_snapshot_id, norm_retrieval_set_id, norm_document_id, norm_paragraph_id, quote, char_start, "
        "char_length, state) VALUES (:o, 1, :run, :snapshot, :set, :ndoc, :npar, :quote, :start, :length, "
        "'verified')"),
        {**ids, "o": observation, "quote": QUOTE, "start": PARAGRAPH.index(QUOTE), "length": len(QUOTE)})
    connection.execute(text("UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"),
                       {"o": observation, "f": finding})


def _publish(engine: Engine, stage: str | None, status: str = "succeeded") -> None:
    """Seed a Run with the given CITE stage and write a certified finding; the COMMIT decides."""
    with engine.begin() as connection:
        ids = _seed_run(connection)
        if stage is not None:
            _stage(connection, ids["run"], stage, status)
        _certified_observation(connection, ids)


def _count(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text("SELECT count(*) FROM finding_observation")).scalar_one())


def test_the_function_at_0036_is_0035s_body_with_exactly_the_stage_test_widened(
    empty_database: DatabaseSettings, foundation_command: Any
) -> None:
    _upgrade(foundation_command, empty_database, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        before = _source(engine)
        assert before.count(OLD_TEST) == 1 and NEW_TEST not in before
        _upgrade(foundation_command, empty_database, THIS)
        assert _version(engine) == THIS
        assert _source(engine) == before.replace(OLD_TEST, NEW_TEST)
        assert _source(engine).count("'ar_v3_citation_review'") == 1
    finally:
        engine.dispose()


def test_a_certified_v3_finding_is_refused_at_0035_and_accepted_at_0036_and_the_v1_control_stays(
    empty_database: DatabaseSettings, foundation_command: Any
) -> None:
    _upgrade(foundation_command, empty_database, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        _publish(engine, V1)  # the control: the stage 0023 names certifies at 0035
        assert _count(engine) == 1
        with pytest.raises(DBAPIError, match=REFUSAL):
            _publish(engine, V3)
        assert _count(engine) == 1  # the refusal rolled the whole transaction back

        _upgrade(foundation_command, empty_database, THIS)
        _publish(engine, V3)
        _publish(engine, V1)  # still certifies
        assert _count(engine) == 3
    finally:
        engine.dispose()


@pytest.mark.parametrize("stage,status", [
    (V3, "failed"), (V1, "failed"), ("text_analysis", "succeeded"), ("source_preparation", "succeeded"), (None, "succeeded"),
])
def test_nothing_but_a_succeeded_cite_stage_certifies_a_partition(
    migrated_engine: Engine, stage: str | None, status: str
) -> None:
    assert _version(migrated_engine) == HEAD
    before = _count(migrated_engine)
    with pytest.raises(DBAPIError, match=REFUSAL):
        _publish(migrated_engine, stage, status)
    assert _count(migrated_engine) == before


def test_a_wrong_count_is_still_refused_by_the_same_function(migrated_engine: Engine) -> None:
    """The widened function keeps its first rule: the stored count equals the citation rows."""
    before = _count(migrated_engine)
    with pytest.raises(DBAPIError, match="citation partition count mismatch"):
        with migrated_engine.begin() as connection:
            ids = _seed_run(connection)
            _stage(connection, ids["run"], V3)
            _certified_observation(connection, ids, count=2)  # one citation row, two certified
    assert _count(migrated_engine) == before


def test_the_downgrade_is_refused_while_an_observation_rests_on_the_v3_stage_only_and_only_then(
    empty_database: DatabaseSettings, foundation_command: Any
) -> None:
    _upgrade(foundation_command, empty_database, THIS)
    url = empty_database.url.render_as_string(hide_password=False)
    engine = create_database_engine(empty_database)
    try:
        _publish(engine, V3)
        source = _source(engine)
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0, refused.describe()
        assert "0036 downgrade refused" in refused.stderr, refused.stderr
        assert _version(engine) == THIS and _source(engine) == source  # a refusal changes nothing
    finally:
        engine.dispose()


def test_without_such_an_observation_the_downgrade_restores_0035s_function_byte_for_byte(
    empty_database: DatabaseSettings, foundation_command: Any
) -> None:
    _upgrade(foundation_command, empty_database, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        original = _source(engine)
        _upgrade(foundation_command, empty_database, THIS)
        _publish(engine, V1)  # a v1/v2-certified observation does not block the downgrade
        url = empty_database.url.render_as_string(hide_password=False)
        down = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert down.returncode == 0, down.describe()
        assert _version(engine) == PREVIOUS
        assert _source(engine) == original
        with pytest.raises(DBAPIError, match=REFUSAL):
            _publish(engine, V3)
        _upgrade(foundation_command, empty_database, THIS)
        assert _source(engine) == original.replace(OLD_TEST, NEW_TEST)
        assert _count(engine) == 1
    finally:
        engine.dispose()
