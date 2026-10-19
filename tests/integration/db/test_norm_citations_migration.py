"""W57A 0023: certified empty partitions and populated 0022 forward upgrade.

These assertions use real PostgreSQL constraint triggers. An empty SELECT by
itself is deliberately not accepted as a v3 citation certificate.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId, DocumentUid, FindingObservationId, FindingUid,
    NormCustodyAdmissionId, NormCustodyBindingId, NormRetrievalSetId,
    NormDocumentId, NormParagraphId, NormsSnapshotId, ProjectUid, PromptBundleId,
    RunId, VersionUid,
)
from auditmanager.storage.models import derive_blob_id

HEAD = "0023_norm_citations"
#: The tree's head, which `W59-SECTION-SEAL-01` moved past this revision.
TREE_HEAD = "0024_version_classification"
PREVIOUS = "0022_findings_v2"
QUOTE = "Требуемая ширина пути эвакуации составляет 1,2 м."


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _available_blob(connection, *, sha: str, size: int) -> str:
    blob = str(derive_blob_id(sha256=sha, size=size))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:blob)"), {"blob": blob})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :blob"), {"blob": blob})
    connection.execute(text(
        "UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = :size, "
        "media_type = 'application/json' WHERE blob_id = :blob"
    ), {"blob": blob, "sha": sha, "size": size})
    return blob


def _verified_set(
    connection, *, include_catalogue_binding: bool = True, declared_windows: int = 1,
) -> tuple[str, str]:
    snapshot, set_id = str(NormsSnapshotId.new()), str(NormRetrievalSetId.new())
    content_key = f"synthetic-{snapshot}"
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, segmentation_profile) "
        "VALUES (:s, :key, :key, :digest, 0, 1, 'markdown-v1')"
    ), {"s": snapshot, "key": content_key, "digest": "a" * 64})
    document, paragraph = str(NormDocumentId.new()), str(NormParagraphId.new())
    document_pk = connection.execute(text(
        "INSERT INTO norm_document "
        "(norm_document_id, norms_snapshot_id, source_document_ref, slug, title, "
        "doc_type, source_attribution, pdf_page_count, block_count, "
        "page_heading_count, recognised_characters, paragraph_count) "
        "VALUES (:d, :s, 'synthetic-source', 'synthetic-slug', 'Synthetic standard', "
        "'СП', 'unattributed', 1, 1, 0, :length, 1) RETURNING norm_document_pk"
    ), {"d": document, "s": snapshot, "length": len(QUOTE)}).scalar_one()
    connection.execute(text(
        "INSERT INTO norm_paragraph "
        "(norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal, "
        "page_label, block_ref, char_offset, char_length, kind, text) "
        "VALUES (:p, :s, :pk, 0, 1, 'synthetic-block', 0, :length, 'body', :quote)"
    ), {"p": paragraph, "s": snapshot, "pk": document_pk,
        "length": len(QUOTE), "quote": QUOTE})
    connection.execute(text(
        "INSERT INTO norm_chunk_build "
        "(norms_snapshot_id, chunking_profile, target_characters, chunk_count) "
        "VALUES (:s, 'reliable-v1-1200', 1200, 1)"
    ), {"s": snapshot})
    chunk_pk = connection.execute(text(
        "INSERT INTO norm_chunk "
        "(norms_snapshot_id, norm_document_pk, chunking_profile, ordinal, page_first, "
        "page_last, char_offset, char_length, paragraph_ordinal_first, "
        "paragraph_ordinal_last, paragraph_count, contains_clause, text, content_sha256) "
        "VALUES (:s, :pk, 'reliable-v1-1200', 0, 1, 1, 0, :length, 0, 0, 1, false, "
        ":quote, :sha) RETURNING norm_chunk_pk"
    ), {"s": snapshot, "pk": document_pk, "length": len(QUOTE), "quote": QUOTE,
        "sha": "b" * 64}).scalar_one()
    connection.execute(text(
        "INSERT INTO norm_embedding_build "
        "(norms_snapshot_id, chunking_profile, embedding_profile, chunk_count, "
        "window_count, embedding_set_sha256) "
        "VALUES (:s, 'reliable-v1-1200', 'bge-m3-dense-v1', 1, :windows, :sha)"
    ), {"s": snapshot, "windows": declared_windows, "sha": "b" * 64})
    connection.execute(text(
        "INSERT INTO norm_embedding "
        "(norms_snapshot_id, norm_chunk_pk, chunking_profile, embedding_profile, "
        "window_ordinal, token_count, char_offset, char_length, "
        "paragraph_ordinal_first, paragraph_ordinal_last, input_sha256, "
        "embedding_sha256, embedding) "
        "VALUES (:s, :chunk, 'reliable-v1-1200', 'bge-m3-dense-v1', "
        "0, 10, 0, :length, 0, 0, :input_sha, :embedding_sha, "
        "('[1,' || repeat('0,', 1022) || '0]')::vector)"
    ), {"s": snapshot, "chunk": chunk_pk, "length": len(QUOTE),
        "input_sha": "c" * 64, "embedding_sha": "d" * 64})
    set_sha, catalogue_sha = "c" * 64, "d" * 64
    set_blob = _available_blob(connection, sha=set_sha, size=10)
    catalogue_blob = _available_blob(connection, sha=catalogue_sha, size=11)
    connection.execute(text(
        "INSERT INTO norm_retrieval_set "
        "(norm_retrieval_set_id, norms_snapshot_id, map_sha256, reviewed_content_key, "
        "chunking_profile, embedding_profile, builder_version, state, "
        "expected_set_sha256, observed_set_sha256, expected_catalogue_sha256, "
        "observed_catalogue_sha256, set_blob_id, set_size_bytes, catalogue_blob_id, "
        "catalogue_size_bytes, prompt_part_characters) "
        "VALUES (:id, :snapshot, :map, :key, 'reliable-v1-1200', 'bge-m3-dense-v1', "
        "'set-v1', 'verified', :set_sha, :set_sha, :catalogue_sha, :catalogue_sha, "
        ":set_blob, 10, :catalogue_blob, 11, 100)"
    ), {"id": set_id, "snapshot": snapshot, "map": "e" * 64, "key": content_key,
        "set_sha": set_sha, "catalogue_sha": catalogue_sha,
        "set_blob": set_blob, "catalogue_blob": catalogue_blob})
    for role, blob, sha, size in (
        ("norm_retrieval_set", set_blob, set_sha, 10),
        ("norm_catalogue", catalogue_blob, catalogue_sha, 11),
    ):
        if role == "norm_catalogue" and not include_catalogue_binding:
            continue
        admission = str(NormCustodyAdmissionId.new())
        connection.execute(text(
            "INSERT INTO norm_custody_admission "
            "(norm_custody_admission_id, role, target_kind, target_id, anchor_kind, "
            "anchor, blob_id, declared_size_bytes, declared_sha256, media_type) "
            "VALUES (:a, :role, 'norm_retrieval_set', :set, 'artifact', :role, :blob, "
            ":size, :sha, 'application/json')"
        ), {"a": admission, "role": role, "set": set_id, "blob": blob,
            "size": size, "sha": sha})
        connection.execute(text(
            "UPDATE norm_custody_admission SET state = 'confirmed', "
            "confirmed_at = clock_timestamp(), attempt_count = 1 "
            "WHERE norm_custody_admission_id = :a"
        ), {"a": admission})
        connection.execute(text(
            "INSERT INTO norm_custody_binding "
            "(norm_custody_binding_id, norm_custody_admission_id, role, target_kind, "
            "target_id, anchor_kind, anchor, blob_id) "
            "VALUES (:binding, :admission, :role, 'norm_retrieval_set', :set, "
            "'artifact', :role, :blob)"
        ), {"binding": str(NormCustodyBindingId.new()), "admission": admission,
            "role": role, "set": set_id, "blob": blob})
    return snapshot, set_id


def _seed_finding(
    connection, *, citation_count: int | None, with_0023: bool, cite_stage: bool = True,
    category: str = "internal_contradiction",
) -> tuple[str, str]:
    project, document, version, run, finding, observation = (
        str(cls.new()) for cls in (
            ProjectUid, DocumentUid, VersionUid, RunId, FindingUid, FindingObservationId,
        )
    )
    profile, prompt = str(AnalysisProfileId.new()), str(PromptBundleId.new())
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'legacy AR')"), {"p": project})
    connection.execute(text(
        "INSERT INTO document (document_uid, project_uid, display_title) "
        "VALUES (:d, :p, 'source')"
    ), {"d": document, "p": project})
    connection.execute(text(
        "INSERT INTO document_version "
        "(version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:v, :d, 1, 'application/pdf', 1024, :h, 1)"
    ), {"v": version, "d": document, "h": "a" * 64})
    verified = _verified_set(connection) if citation_count is not None else None
    pin_columns = ", norms_snapshot_id, norm_retrieval_set_id" if verified else ""
    pin_values = ", :snapshot, :set_id" if verified else ""
    connection.execute(text(
        "INSERT INTO audit_run "
        "(run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
        f"provider_mode, frozen_input_digest{pin_columns}) "
        f"VALUES (:r, :p, :v, :ap, :pb, 'recorded', :h{pin_values})"
    ), {"r": run, "p": project, "v": version, "ap": profile, "pb": prompt,
        "h": "b" * 64, "snapshot": verified[0] if verified else None,
        "set_id": verified[1] if verified else None})
    if verified and cite_stage:
        connection.execute(text(
            "INSERT INTO stage_result (run_id, stage_id, stage_version, status) "
            "VALUES (:r, 'norm_verification', '1.0.0', 'succeeded')"
        ), {"r": run})
    connection.execute(text(
        "INSERT INTO finding "
        "(finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
        "VALUES (:f, :p, :v, :r, :category)"
    ), {"f": finding, "p": project, "v": version, "r": run, "category": category})
    new_column = ", norm_citation_count, required_value, stated_value" if with_0023 else ""
    new_value = ", :count, :required, :stated" if with_0023 else ""
    connection.execute(text(
        "INSERT INTO finding_observation "
        "(finding_observation_id, run_id, finding_uid, stage_id, category, "
        "finding_text, recommendation_text, grounded, analysis_profile_id, "
        f"prompt_bundle_id, provider_mode{new_column}) "
        "VALUES (:o, :r, :f, 'text_analysis', :category, "
        f"'A conflict', 'Resolve the conflict', true, :ap, :pb, 'recorded'{new_value})"
    ), {"o": observation, "r": run, "f": finding, "ap": profile, "pb": prompt,
        "count": citation_count, "category": category,
        "required": "1,2 м" if category == "evacuation" else None,
        "stated": "1,0 м" if category == "evacuation" else None})
    connection.execute(text(
        "UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"
    ), {"o": observation, "f": finding})
    return finding, observation


def test_zero_is_a_committed_certificate_but_null_is_legacy(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        _, legacy = _seed_finding(connection, citation_count=None, with_0023=True)
        _, certified = _seed_finding(connection, citation_count=0, with_0023=True)
    with migrated_engine.connect() as connection:
        rows = dict(connection.execute(text(
            "SELECT finding_observation_id, norm_citation_count FROM finding_observation "
            "WHERE finding_observation_id IN (:legacy, :certified)"
        ), {"legacy": legacy, "certified": certified}).all())
        assert rows == {legacy: None, certified: 0}
        assert connection.execute(text(
            "SELECT count(*) FROM finding_observation_norm_citation"
        )).scalar_one() == 0


def test_nonzero_certificate_without_rows_refuses_at_commit(migrated_engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="citation partition count mismatch"):
        with migrated_engine.begin() as connection:
            _seed_finding(
                connection, citation_count=1, with_0023=True, category="evacuation",
            )


def test_verified_citation_is_raw_substring_of_the_pinned_snapshot(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        _, observation = _seed_finding(
            connection, citation_count=1, with_0023=True, category="evacuation",
        )
        citation = connection.execute(text(
            "SELECT o.run_id, r.norms_snapshot_id, r.norm_retrieval_set_id, "
            "d.norm_document_id, p.norm_paragraph_id "
            "FROM finding_observation o JOIN audit_run r ON r.run_id = o.run_id "
            "JOIN norm_paragraph p ON p.norms_snapshot_id = r.norms_snapshot_id "
            "JOIN norm_document d ON d.norm_document_pk = p.norm_document_pk "
            "WHERE o.finding_observation_id = :o"
        ), {"o": observation}).mappings().one()
        values = {**citation, "observation": observation, "quote": QUOTE,
                  "length": len(QUOTE)}
        statement = text(
            "INSERT INTO finding_observation_norm_citation "
            "(finding_observation_id, citation_ordinal, run_id, norms_snapshot_id, "
            "norm_retrieval_set_id, norm_document_id, norm_paragraph_id, quote, "
            "char_start, char_length, state) "
            "VALUES (:observation, :ordinal, :run_id, :norms_snapshot_id, "
            ":norm_retrieval_set_id, :norm_document_id, :norm_paragraph_id, :quote, "
            "0, :length, 'verified')"
        )
        connection.execute(statement, {**values, "ordinal": 1})
        with pytest.raises(DBAPIError, match="citation is outside"):
            with connection.begin_nested():
                connection.execute(statement, {
                    **values, "ordinal": 2, "quote": QUOTE.replace("1,2", "9,9"),
                })
    with migrated_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM finding_observation_norm_citation "
            "WHERE finding_observation_id = :o"
        ), {"o": observation}).scalar_one() == 1


def test_zero_without_succeeded_cite_stage_refuses_at_commit(migrated_engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="needs succeeded CITE stage"):
        with migrated_engine.begin() as connection:
            _seed_finding(connection, citation_count=0, with_0023=True, cite_stage=False)


def test_verified_set_needs_both_custody_bindings(migrated_engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="needs both exact confirmed custody bindings"):
        with migrated_engine.begin() as connection:
            _verified_set(connection, include_catalogue_binding=False)


def test_verified_set_refuses_incomplete_vector_build(migrated_engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="needs a complete vector build"):
        with migrated_engine.begin() as connection:
            _verified_set(connection, declared_windows=2)


def test_rejected_set_cannot_pin_and_existing_run_pin_is_frozen(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        _, observation = _seed_finding(connection, citation_count=0, with_0023=True)
        run = connection.execute(text(
            "SELECT r.run_id, r.project_uid, r.version_uid, r.norms_snapshot_id "
            "FROM finding_observation o JOIN audit_run r ON r.run_id = o.run_id "
            "WHERE o.finding_observation_id = :o"
        ), {"o": observation}).mappings().one()
        rejected = str(NormRetrievalSetId.new())
        connection.execute(text(
            "INSERT INTO norm_retrieval_set "
            "(norm_retrieval_set_id, norms_snapshot_id, map_sha256, reviewed_content_key, "
            "chunking_profile, embedding_profile, builder_version, state, "
            "expected_set_sha256, observed_set_sha256, expected_catalogue_sha256, "
            "observed_catalogue_sha256) "
            "SELECT :id, :snapshot, :map, content_key, 'reliable-v1-1200', "
            "'bge-m3-dense-v1', 'rejected-v1', 'rejected', :expected, :observed, "
            ":catalogue, :catalogue FROM norms_snapshot WHERE norms_snapshot_id = :snapshot"
        ), {"id": rejected, "snapshot": run["norms_snapshot_id"], "map": "e" * 64,
            "expected": "a" * 64, "observed": "b" * 64, "catalogue": "d" * 64})
        with pytest.raises(DBAPIError, match="run needs a verified set"):
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO audit_run "
                    "(run_id, project_uid, version_uid, analysis_profile_id, "
                    "prompt_bundle_id, provider_mode, frozen_input_digest, "
                    "norms_snapshot_id, norm_retrieval_set_id) "
                    "VALUES (:run, :project, :version, :profile, :prompt, "
                    "'recorded', :digest, :snapshot, :set_id)"
                ), {"run": str(RunId.new()), "project": run["project_uid"],
                    "version": run["version_uid"], "profile": str(AnalysisProfileId.new()),
                    "prompt": str(PromptBundleId.new()), "digest": "b" * 64,
                    "snapshot": run["norms_snapshot_id"], "set_id": rejected})
        with pytest.raises(DBAPIError, match="frozen at creation"):
            with connection.begin_nested():
                connection.execute(text(
                    "UPDATE audit_run SET norm_retrieval_set_id = NULL WHERE run_id = :run"
                ), {"run": run["run_id"]})


def test_populated_0022_upgrades_without_inventing_citations_and_refuses_downgrade(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_previous = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert at_previous.returncode == 0, at_previous.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            finding, observation = _seed_finding(connection, citation_count=None, with_0023=False)
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == TREE_HEAD
            assert connection.execute(text(
                "SELECT norm_citation_count FROM finding_observation "
                "WHERE finding_observation_id = :o"
            ), {"o": observation}).scalar_one() is None
            assert connection.execute(text(
                "SELECT canonical_observation_id FROM finding WHERE finding_uid = :f"
            ), {"f": finding}).scalar_one() == observation
        with engine.begin() as connection:
            _, certified = _seed_finding(connection, citation_count=0, with_0023=True)
        refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
        assert refused.returncode != 0
        assert "0023 downgrade refused" in refused.stderr
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == TREE_HEAD
            assert connection.execute(text(
                "SELECT norm_citation_count FROM finding_observation "
                "WHERE finding_observation_id = :o"
            ), {"o": certified}).scalar_one() == 0
    finally:
        engine.dispose()
