"""Real PostgreSQL acceptance of the gated six-run AR beta group."""

from __future__ import annotations

from dataclasses import asdict, replace

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.api.schemas import models
from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.jobs.public import JobRepository
from auditmanager.norms.public import SetIdentity
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import (
    ReviewedScope, TrustedPack, TrustedPackRegistry, get_ar_v3_group, start_ar_v3_group,
)
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AuditEventId, DocumentUid, NormCustodyAdmissionId,
    NormCustodyBindingId, NormDocumentId, NormParagraphId, NormRetrievalSetId,
    NormsSnapshotId, ProjectUid, RunId, VersionUid,
)
from auditmanager.shared.identity.ids import UserUid
from auditmanager.storage.models import derive_blob_id
from auditmanager.shared.db.engine import create_database_engine

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
CHUNKING = "characters-v2:1200"
QUOTE = "Test normative paragraph."


def _blob(session: Session, sha: str, size: int, media_type: str) -> str:
    blob_id = str(derive_blob_id(sha256=sha, size=size))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:id)"), {"id": blob_id})
    session.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :id"), {"id": blob_id})
    session.execute(text("""
        UPDATE blob SET state = 'available', sha256 = :sha,
            size_bytes = :size, media_type = :media WHERE blob_id = :id
    """), {"id": blob_id, "sha": sha, "size": size, "media": media_type})
    return blob_id


def _binding(
    session: Session, *, role: str, target_kind: str, target_id: str,
    anchor_kind: str, anchor: str, blob_id: str, size: int,
    sha: str, media_type: str,
) -> None:
    admission = str(NormCustodyAdmissionId.new())
    session.execute(text("""
        INSERT INTO norm_custody_admission
            (norm_custody_admission_id, role, target_kind, target_id, anchor_kind,
             anchor, blob_id, declared_size_bytes, declared_sha256, media_type)
        VALUES (:id, :role, :kind, :target, :anchor_kind, :anchor, :blob,
                :size, :sha, :media)
    """), {
        "id": admission, "role": role, "kind": target_kind, "target": target_id,
        "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id,
        "size": size, "sha": sha, "media": media_type,
    })
    session.execute(text("""
        UPDATE norm_custody_admission SET state = 'confirmed',
            confirmed_at = clock_timestamp(), attempt_count = 1
        WHERE norm_custody_admission_id = :id
    """), {"id": admission})
    session.execute(text("""
        INSERT INTO norm_custody_binding
            (norm_custody_binding_id, norm_custody_admission_id, role, target_kind,
             target_id, anchor_kind, anchor, blob_id)
        VALUES (:id, :admission, :role, :kind, :target, :anchor_kind, :anchor, :blob)
    """), {
        "id": str(NormCustodyBindingId.new()), "admission": admission,
        "role": role, "kind": target_kind, "target": target_id,
        "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id,
    })


def _seed(session: Session) -> tuple[str, TrustedPack]:
    profile = resolve_beta_v3_profile(
        "ap_01M5M28ZCDD8VPSP1BTAEW92YE", "pb_01M5M28ZCDVCR37BX1884JGSPM",
    )
    actor = str(UserUid.new())
    session.execute(text("""
        INSERT INTO app_user (user_uid, login, password_algorithm,
            password_iterations, password_salt, password_hash)
        VALUES (:id, :login, 'pbkdf2_sha256', 100000, :salt, :hash)
    """), {"id": actor, "login": actor.lower(), "salt": "0" * 32, "hash": "0" * 64})
    project, document, version = str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
    pdf_blob = _blob(session, "a" * 64, 1024, "application/pdf")
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:id, 'AR beta')"), {"id": project})
    session.execute(text("""
        INSERT INTO document (document_uid, project_uid, display_title)
        VALUES (:id, :project, 'AR')
    """), {"id": document, "project": project})
    session.execute(text("""
        INSERT INTO document_version
            (version_uid, document_uid, version_ordinal, media_type,
             byte_size, sha256, page_count)
        VALUES (:id, :document, 1, 'application/pdf', 1024, :sha, 1)
    """), {"id": version, "document": document, "sha": "a" * 64})
    session.execute(text("""
        INSERT INTO input_manifest_entry
            (version_uid, role, blob_id, sha256, size_bytes, media_type)
        VALUES (:version, 'source.document', :blob, :sha, 1024, 'application/pdf')
    """), {"version": version, "blob": pdf_blob, "sha": "a" * 64})
    session.execute(text("UPDATE document SET current_version_uid = :version WHERE document_uid = :document"),
                    {"version": version, "document": document})
    session.execute(text("""
        INSERT INTO document_version_classification
            (version_uid, project_stage, section_code, confirmed_by_user_uid)
        VALUES (:version, 'R', 'AR', :actor)
    """), {"version": version, "actor": actor})

    content_key = "ar-v3-beta-synthetic"
    session.execute(text("""
        INSERT INTO norms_snapshot
            (norms_snapshot_id, content_key, base_content_key, content_digest,
             undated_documents, document_count, segmentation_profile)
        VALUES (:id, :key, :key, :sha, 0, 1, 'markdown-v1')
    """), {"id": SNAPSHOT, "key": content_key, "sha": "b" * 64})
    norm_document = str(NormDocumentId.new())
    norm_pk = session.execute(text("""
        INSERT INTO norm_document
            (norm_document_id, norms_snapshot_id, source_document_ref, slug, title,
             doc_type, source_attribution, pdf_page_count, block_count,
             page_heading_count, recognised_characters, paragraph_count)
        VALUES (:id, :snapshot, 'synthetic-source', 'synthetic-slug', 'Synthetic standard',
                'СП', 'unattributed', 1, 1, 0, :length, 1)
        RETURNING norm_document_pk
    """), {"id": norm_document, "snapshot": SNAPSHOT, "length": len(QUOTE)}).scalar_one()
    _binding(session, role="norm_source", target_kind="norm_document",
             target_id=norm_document, anchor_kind="pdf", anchor="synthetic-source",
             blob_id=pdf_blob, size=1024, sha="a" * 64, media_type="application/pdf")
    session.execute(text("""
        INSERT INTO norm_paragraph
            (norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
             page_label, block_ref, char_offset, char_length, kind, text)
        VALUES (:id, :snapshot, :document, 0, 1, 'synthetic-block',
                0, :length, 'body', :quote)
    """), {"id": str(NormParagraphId.new()), "snapshot": SNAPSHOT,
           "document": norm_pk, "length": len(QUOTE), "quote": QUOTE})
    session.execute(text("""
        INSERT INTO norm_chunk_build
            (norms_snapshot_id, chunking_profile, target_characters, chunk_count)
        VALUES (:snapshot, :chunking, 1200, 1)
    """), {"snapshot": SNAPSHOT, "chunking": CHUNKING})
    chunk_pk = session.execute(text("""
        INSERT INTO norm_chunk
            (norms_snapshot_id, norm_document_pk, chunking_profile, ordinal,
             page_first, page_last, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count,
             contains_clause, text, content_sha256)
        VALUES (:snapshot, :document, :chunking, 0, 1, 1, 0, :length,
                0, 0, 1, false, :quote, :sha)
        RETURNING norm_chunk_pk
    """), {"snapshot": SNAPSHOT, "document": norm_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "quote": QUOTE, "sha": "c" * 64}).scalar_one()
    session.execute(text("""
        INSERT INTO norm_embedding_build
            (norms_snapshot_id, chunking_profile, embedding_profile,
             chunk_count, window_count, embedding_set_sha256)
        VALUES (:snapshot, :chunking, 'bge-m3-dense-v1', 1, 1, :sha)
    """), {"snapshot": SNAPSHOT, "chunking": CHUNKING, "sha": "d" * 64})
    session.execute(text("""
        INSERT INTO norm_embedding
            (norms_snapshot_id, norm_chunk_pk, chunking_profile, embedding_profile,
             window_ordinal, token_count, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, input_sha256,
             embedding_sha256, embedding)
        VALUES (:snapshot, :chunk, :chunking, 'bge-m3-dense-v1', 0, 10, 0,
                :length, 0, 0, :input, :embedding_sha,
                ('[1,' || repeat('0,', 1022) || '0]')::vector)
    """), {"snapshot": SNAPSHOT, "chunk": chunk_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "input": "e" * 64, "embedding_sha": "f" * 64})
    event = str(AuditEventId.new())
    session.execute(text("""
        INSERT INTO norm_current_snapshot_event
            (event_id, from_snapshot_id, to_snapshot_id, actor_user_uid)
        VALUES (:event, NULL, :snapshot, :actor)
    """), {"event": event, "snapshot": SNAPSHOT, "actor": actor})
    session.execute(text("""
        INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id)
        VALUES (:snapshot, :event)
    """), {"snapshot": SNAPSHOT, "event": event})

    set_blob = _blob(session, "1" * 64, 10, "application/json")
    catalogue_blob = _blob(session, "2" * 64, 11, "application/json")
    scopes = []
    for index, scope_id in enumerate(profile.scopes, 1):
        set_id = str(NormRetrievalSetId.new())
        map_sha = f"{index:x}" * 64
        session.execute(text("""
            INSERT INTO norm_retrieval_set
                (norm_retrieval_set_id, norms_snapshot_id, map_sha256,
                 reviewed_content_key, chunking_profile, embedding_profile,
                 builder_version, state, expected_set_sha256, observed_set_sha256,
                 expected_catalogue_sha256, observed_catalogue_sha256,
                 set_blob_id, set_size_bytes, catalogue_blob_id,
                 catalogue_size_bytes, prompt_part_characters)
            VALUES (:id, :snapshot, :map, :key, :chunking, 'bge-m3-dense-v1',
                    'norm-retrieval-set-prep-v1', 'verified', :set_sha, :set_sha,
                    :catalogue_sha, :catalogue_sha, :set_blob, 10,
                    :catalogue_blob, 11, 100)
        """), {"id": set_id, "snapshot": SNAPSHOT, "map": map_sha,
               "key": content_key, "chunking": CHUNKING,
               "set_sha": "1" * 64, "catalogue_sha": "2" * 64,
               "set_blob": set_blob, "catalogue_blob": catalogue_blob})
        for role, blob, sha, size in (
            ("norm_retrieval_set", set_blob, "1" * 64, 10),
            ("norm_catalogue", catalogue_blob, "2" * 64, 11),
        ):
            _binding(session, role=role, target_kind="norm_retrieval_set",
                     target_id=set_id, anchor_kind="artifact", anchor=role,
                     blob_id=blob, size=size, sha=sha, media_type="application/json")
        scopes.append(ReviewedScope(
            scope_id=scope_id,
            identity=SetIdentity(
                map_sha256=map_sha, snapshot_id=SNAPSHOT,
                reviewed_content_key=content_key,
                embedding_build=f"bge-m3-dense-v1:{CHUNKING}",
            ),
            chunking_profile=CHUNKING, set_id=set_id, set_sha256="1" * 64,
        ))
    return version, TrustedPack(str(profile.analysis_profile_id), str(profile.prompt_bundle_id), tuple(scopes))


def _counts(session: Session) -> tuple[int, int, int]:
    return tuple(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                 for table in ("command_record", "ar_v3_run_group", "audit_run"))


def _claim_member(session: Session, run_id: str):
    runs = RunRepository()
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    authority = JobRepository().start_execution(session, run_id=run_id)
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    return authority


def test_current_attempt_resolves_all_six_reviewed_member_pins(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
    with Session(migrated_engine) as session, session.begin():
        started = start_ar_v3_group(
            session, version_uid=version, idempotency_key="ar-v3-preflight",
            provider_mode="recorded", pack=pack, input_budget_characters=1000,
        )
    registry = TrustedPackRegistry("ar-v3-beta-reviewed-pack-registry/1", (pack,))
    with Session(migrated_engine) as session, session.begin():
        for member, scope in zip(started.group.members, pack.scopes, strict=True):
            authority = _claim_member(session, member.run_id)
            first = resolve_v3_execution_binding(
                session, authority=authority, registry=registry,
            )
            second = resolve_v3_execution_binding(
                session, authority=authority, registry=registry,
            )
            assert first == second
            assert first.group_id == started.group.group_id
            assert first.run_id == member.run_id
            assert first.scope_id == scope.scope_id
            assert first.map_sha256 == scope.identity.map_sha256
            assert first.norm_retrieval_set_id == scope.set_id
            assert first.set_sha256 == scope.set_sha256
            assert first.pack_sha256 == pack.sha256
        assert session.execute(text("SELECT count(*) FROM model_call")).scalar_one() == 0
        assert session.execute(text("SELECT count(*) FROM stage_result")).scalar_one() == 0


def test_preflight_refuses_missing_changed_pack_foreign_run_and_stale_attempt(
    migrated_engine: Engine,
) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
    with Session(migrated_engine) as session, session.begin():
        started = start_ar_v3_group(
            session, version_uid=version, idempotency_key="ar-v3-preflight-refusals",
            provider_mode="recorded", pack=pack, input_budget_characters=1000,
        )
    member = started.group.members[0]
    registry = TrustedPackRegistry("ar-v3-beta-reviewed-pack-registry/1", (pack,))
    with Session(migrated_engine) as session, session.begin():
        authority = _claim_member(session, member.run_id)
        with pytest.raises(DomainError) as missing:
            resolve_v3_execution_binding(
                session, authority=authority, registry=TrustedPackRegistry.empty(),
            )
        assert missing.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        changed_scope = replace(pack.scopes[0], set_sha256="f" * 64)
        changed_pack = replace(pack, scopes=(changed_scope, *pack.scopes[1:]))
        with pytest.raises(DomainError) as changed:
            resolve_v3_execution_binding(
                session, authority=authority,
                registry=TrustedPackRegistry("ar-v3-beta-reviewed-pack-registry/1", (changed_pack,)),
            )
        assert changed.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
        with pytest.raises(DomainError) as stale:
            resolve_v3_execution_binding(
                session, authority=replace(authority, execution_token="wrong"),
                registry=registry,
            )
        assert stale.value.code is ErrorCode.EXECUTION_TOKEN_INVALID

        foreign = str(RunId.new())
        session.execute(text("""
            INSERT INTO audit_run
                (run_id, project_uid, version_uid, analysis_profile_id,
                 prompt_bundle_id, provider_mode, frozen_input_digest)
            VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest)
        """), {
            "run": foreign, "project": started.group.project_uid,
            "version": version, "profile": pack.analysis_profile_id,
            "bundle": pack.prompt_bundle_id, "digest": "0" * 64,
        })
        foreign_authority = _claim_member(session, foreign)
        with pytest.raises(DomainError) as outside:
            resolve_v3_execution_binding(
                session, authority=foreign_authority, registry=registry,
            )
        assert outside.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
        assert session.execute(text("SELECT count(*) FROM model_call")).scalar_one() == 0


def test_upgrade_from_0031_preserves_old_runs(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    command = [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini"]
    assert foundation_command([*command, "upgrade", "0031_executor_pull_channel"], url).returncode == 0
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            project, document, version = str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
            connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:id, 'legacy')"),
                               {"id": project})
            connection.execute(text("""
                INSERT INTO document (document_uid, project_uid, display_title)
                VALUES (:id, :project, 'legacy')
            """), {"id": document, "project": project})
            connection.execute(text("""
                INSERT INTO document_version
                    (version_uid, document_uid, version_ordinal, media_type,
                     byte_size, sha256, page_count)
                VALUES (:id, :document, 1, 'application/pdf', 1, :sha, 1)
            """), {"id": version, "document": document, "sha": "a" * 64})
            run = "run_01M2545JSD15ETSNNV904X991K"
            connection.execute(text("""
                INSERT INTO audit_run
                    (run_id, project_uid, version_uid, analysis_profile_id,
                     prompt_bundle_id, provider_mode, frozen_input_digest)
                VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest)
            """), {"run": run, "project": project, "version": version,
                   "profile": "ap_01M2545JSD15ETSNNV904X991K",
                   "bundle": "pb_01M2545JSD15ETSNNV904X991K", "digest": "b" * 64})
        assert foundation_command([*command, "upgrade", "head"], url).returncode == 0
        with engine.connect() as connection:
            assert connection.execute(text("SELECT state FROM audit_run WHERE run_id = :run"),
                                      {"run": run}).scalar_one() == "created"
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0032_ar_v3_run_group"
            assert connection.execute(text("SELECT count(*) FROM ar_v3_run_group")).scalar_one() == 0
    finally:
        engine.dispose()


def test_no_pack_refuses_before_any_write(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session:
        before = _counts(session)
        with pytest.raises(DomainError) as raised:
            start_ar_v3_group(
                session, version_uid=str(VersionUid.new()),
                idempotency_key="ar-v3-no-pack", provider_mode="recorded",
                pack=None, input_budget_characters=1000,
            )
        assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert _counts(session) == before


def test_six_pins_replay_readback_and_refusals(migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
    with Session(migrated_engine) as session, session.begin():
        first = start_ar_v3_group(
            session, version_uid=version, idempotency_key="ar-v3-six",
            provider_mode="recorded", pack=pack, input_budget_characters=1000,
        )
        assert not first.replayed
        assert tuple(m.scope_id for m in first.group.members) == ("F1", "F2", "A1", "A2", "S1", "S2")
        assert len({m.run_id for m in first.group.members}) == 6
        assert len({m.norm_retrieval_set_id for m in first.group.members}) == 6
        assert all(m.state == "created" for m in first.group.members)
        assert models.ArV3BetaGroup.model_validate(asdict(first.group)).group_id == first.group.group_id
    with Session(migrated_engine) as session, session.begin():
        replay = start_ar_v3_group(
            session, version_uid=version, idempotency_key="ar-v3-six",
            provider_mode="recorded", pack=None, input_budget_characters=1000,
        )
        assert replay.replayed
        assert replay.group.members == first.group.members
        RunRepository().advance(session, run_id=first.group.members[0].run_id,
                                from_state="created", to_state="queued")
        assert get_ar_v3_group(session, first.group.group_id).members[0].state == "queued"
        before = _counts(session)
        with pytest.raises(DomainError) as conflict:
            start_ar_v3_group(
                session, version_uid=str(VersionUid.new()), idempotency_key="ar-v3-six",
                provider_mode="recorded", pack=None, input_budget_characters=1000,
            )
        assert conflict.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert _counts(session) == before
    with Session(migrated_engine) as session:
        before = _counts(session)
        wrong_scope = replace(pack.scopes[0], set_id=pack.scopes[1].set_id)
        duplicate = replace(pack, scopes=(wrong_scope, *pack.scopes[1:]))
        with pytest.raises(DomainError):
            start_ar_v3_group(session, version_uid=version, idempotency_key="ar-v3-duplicate",
                              provider_mode="recorded", pack=duplicate,
                              input_budget_characters=1000)
        wrong_set = replace(pack.scopes[0], set_id=str(NormRetrievalSetId.new()))
        foreign = replace(pack, scopes=(wrong_set, *pack.scopes[1:]))
        with pytest.raises(DomainError):
            start_ar_v3_group(session, version_uid=version, idempotency_key="ar-v3-foreign",
                              provider_mode="recorded", pack=foreign,
                              input_budget_characters=1000)
        assert _counts(session) == before

    # A failure after the third INSERT rolls back command, group and child Runs together.
    original_create = RunRepository.create
    inserted = 0

    def fail_third(self, session, **kwargs):
        nonlocal inserted
        inserted += 1
        if inserted == 3:
            raise RuntimeError("synthetic third-child write failure")
        return original_create(self, session, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(RunRepository, "create", fail_third)
        with pytest.raises(RuntimeError, match="third-child"):
            with Session(migrated_engine) as session, session.begin():
                start_ar_v3_group(
                    session, version_uid=version, idempotency_key="ar-v3-rollback",
                    provider_mode="recorded", pack=pack, input_budget_characters=1000,
                )
    with Session(migrated_engine) as session:
        assert _counts(session) == before

    stale_snapshot = str(NormsSnapshotId.new())
    with Session(migrated_engine) as session, session.begin():
        session.execute(text("""
            INSERT INTO norms_snapshot
                (norms_snapshot_id, content_key, base_content_key, content_digest,
                 undated_documents, document_count, segmentation_profile)
            VALUES (:id, 'stale-target', 'stale-target', :sha, 0, 1, 'markdown-v1')
        """), {"id": stale_snapshot, "sha": "3" * 64})
        event = str(AuditEventId.new())
        actor = session.execute(text("SELECT confirmed_by_user_uid FROM document_version_classification "
                                     "WHERE version_uid = :version"), {"version": version}).scalar_one()
        session.execute(text("""
            INSERT INTO norm_current_snapshot_event
                (event_id, from_snapshot_id, to_snapshot_id, actor_user_uid)
            VALUES (:event, :from_id, :to_id, :actor)
        """), {"event": event, "from_id": SNAPSHOT, "to_id": stale_snapshot, "actor": actor})
        session.execute(text("""
            UPDATE norm_current_snapshot SET norms_snapshot_id = :snapshot, event_id = :event
        """), {"snapshot": stale_snapshot, "event": event})
    with Session(migrated_engine) as session:
        with pytest.raises(DomainError) as refused:
            start_ar_v3_group(
                session, version_uid=version, idempotency_key="ar-v3-stale-snapshot",
                provider_mode="recorded", pack=pack, input_budget_characters=1000,
            )
        assert refused.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
        assert _counts(session) == before
