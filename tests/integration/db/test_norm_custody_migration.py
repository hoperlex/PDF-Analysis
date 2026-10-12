"""`W54-SEAL-01`: migration ``0018_norm_custody`` on an empty and on a populated database.

Plan `W54-PLAN.md` section 4, `W54-SEAL-01`, requires for this migration: a fresh upgrade,
an upgrade from ``0017`` with rows, a refused downgrade with retained data, an insert in a
non-initial effect state refused (D-148), ``prepared -> abandoned`` (D-142), and an unknown
role or target kind refused (``ck_norm_custody_role_shape``). The custody, binding and
repair-journal guards are asserted beside them, each with a control write that succeeds,
so a refusal cannot pass because the statement was malformed.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AttemptId,
    DocumentUid,
    JobId,
    LeaseId,
    NormCustodyAdmissionId,
    NormCustodyBindingId,
    NormDocumentId,
    NormParagraphId,
    NormRepairCallId,
    NormsSnapshotId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.storage.models import derive_blob_id

PDF_SHA = "c" * 64
PDF_SIZE = 4096


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _constraint(error: pytest.ExceptionInfo[DBAPIError]) -> str | None:
    return getattr(getattr(error.value.orig, "diag", None), "constraint_name", None)


def _head(connection) -> str:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


# --- seeding -------------------------------------------------------------------------------


def _seed_attempt(connection, *, label: str) -> dict[str, str]:
    """A run with its Job, Attempt and live Lease, as the 0017 writer leaves them."""
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()), "job": str(JobId.new()),
        "attempt": str(AttemptId.new()), "lease": str(LeaseId.new()),
    }
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, :name)"),
                       {**ids, "name": f"custody-{label}"})
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, :title)"), {**ids, "title": label})
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


def _available_blob(connection, *, sha256: str = PDF_SHA, size: int = PDF_SIZE,
                    media_type: str = "application/pdf") -> str:
    blob_id = str(derive_blob_id(sha256=sha256, size=size))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob_id})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob_id})
    connection.execute(text("UPDATE blob SET state = 'available', sha256 = :d, size_bytes = :s, "
                            "media_type = :m WHERE blob_id = :b"),
                       {"b": blob_id, "d": sha256, "s": size, "m": media_type})
    return blob_id


def _seed_norms(connection, *, unreliable_count: int = 0, repaired: bool = False) -> dict[str, str]:
    snapshot, document, paragraph = (
        str(NormsSnapshotId.new()), str(NormDocumentId.new()), str(NormParagraphId.new())
    )
    key = f"2026-07-23+1d.{snapshot[-12:].lower()}"
    content_key = f"{key}+1r" if repaired else key
    connection.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, repair_count, segmentation_profile"
        + (", unreliable_count" if unreliable_count else "")
        + ") VALUES (:snapshot, :content_key, :base_key, :digest, 0, 1, :repairs, 'markdown-v1'"
        + (", :unreliable" if unreliable_count else "") + ")"
    ), {"snapshot": snapshot, "content_key": content_key if not unreliable_count else f"{key}+1u",
        "base_key": key, "digest": "d" * 64, "repairs": 1 if repaired else 0,
        "unreliable": unreliable_count})
    pk = connection.execute(text(
        "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, "
        "slug, title, doc_type, source_attribution, pdf_page_count, block_count, "
        "page_heading_count, recognised_characters, paragraph_count) VALUES (:document, "
        ":snapshot, 'source-1', 'slug-1', 'title.pdf', 'СП', 'unattributed', 1, 1, 0, 10, 1) "
        "RETURNING norm_document_pk"
    ), {"document": document, "snapshot": snapshot}).scalar_one()
    connection.execute(text(
        "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, "
        "ordinal, page_label, block_ref, char_offset, char_length, kind, text) VALUES "
        "(:paragraph, :snapshot, :pk, 0, 1, 'block-1', 0, 10, 'body', '0123456789')"
    ), {"paragraph": paragraph, "snapshot": snapshot, "pk": pk})
    return {"snapshot": snapshot, "document": document, "paragraph": paragraph}


_ADMIT = (
    "INSERT INTO norm_custody_admission (norm_custody_admission_id, role, target_kind, "
    "target_id, anchor_kind, anchor, blob_id, declared_size_bytes, declared_sha256, media_type"
    "{extra_columns}) VALUES (:id, :role, :target_kind, :target_id, :anchor_kind, :anchor, "
    ":blob, :size, :sha, :media{extra_values})"
)


def _admit(connection, *, target_id: str, blob_id: str, role: str = "norm_source",
           target_kind: str = "norm_document", anchor_kind: str = "pdf",
           anchor: str = "doc_portal-1", state: str | None = None) -> str:
    admission = str(NormCustodyAdmissionId.new())
    statement = _ADMIT.format(
        extra_columns=", state" if state else "", extra_values=", :state" if state else ""
    )
    connection.execute(text(statement), {
        "id": admission, "role": role, "target_kind": target_kind, "target_id": target_id,
        "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id, "size": PDF_SIZE,
        "sha": PDF_SHA, "media": "application/pdf", "state": state,
    })
    return admission


def _confirm(connection, admission: str) -> None:
    connection.execute(text(
        "UPDATE norm_custody_admission SET state = 'confirmed', confirmed_at = clock_timestamp(), "
        "attempt_count = 1 WHERE norm_custody_admission_id = :id"
    ), {"id": admission})


def _bind(connection, *, admission: str, target_id: str, blob_id: str,
          anchor: str = "doc_portal-1") -> str:
    binding = str(NormCustodyBindingId.new())
    connection.execute(text(
        "INSERT INTO norm_custody_binding (norm_custody_binding_id, norm_custody_admission_id, "
        "role, target_kind, target_id, anchor_kind, anchor, blob_id) VALUES (:id, :admission, "
        "'norm_source', 'norm_document', :target, 'pdf', :anchor, :blob)"
    ), {"id": binding, "admission": admission, "target": target_id, "anchor": anchor,
        "blob": blob_id})
    return binding


def _repair_call(connection, *, call_id: str | None = None, scope: str | None = None,
                 attempt: int = 1) -> str:
    call_id = call_id or str(NormRepairCallId.new())
    connection.execute(text(
        "INSERT INTO norm_repair_call (norm_repair_call_id, idempotency_scope, block_anchor, "
        "crop_sha256, request_sha256, model, attempt_number) VALUES (:id, :scope, 'blk_1', "
        ":crop, :request, 'opus-5', :attempt)"
    ), {"id": call_id, "scope": scope or call_id, "crop": "e" * 64, "request": "f" * 64,
        "attempt": attempt})
    return call_id


def _refused(connection, statement: str, parameters: dict, *, sqlstate: str,
             constraint: str | None = None) -> None:
    with pytest.raises(DBAPIError) as refused:
        with connection.begin_nested():
            connection.execute(text(statement), parameters)
    assert _sqlstate(refused) == sqlstate, refused.value
    if constraint is not None:
        assert _constraint(refused) == constraint, refused.value


# --- the migration lifecycle -----------------------------------------------------------------


def test_a_fresh_upgrade_creates_the_custody_tables_and_guards_inserts(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert _head(connection) == "0019_execution_workers"
        for table in ("norm_custody_admission", "norm_custody_binding", "norm_repair_call"):
            assert connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one()
        definitions = dict(connection.execute(text(
            "SELECT t.tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t "
            "WHERE t.tgname IN ('trg_provider_call_effect_state_guard', "
            "'trg_analysis_artifact_state_guard') AND NOT t.tgisinternal"
        )).all())
        assert len(definitions) == 2
        for name, definition in definitions.items():
            assert "BEFORE INSERT OR UPDATE" in definition, (name, definition)
        role_shape = connection.execute(text(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'ck_norm_custody_role_shape'"
        )).scalar_one()
        assert role_shape == 2, "the role-shape CHECK must guard both the admission and the binding"


def test_a_populated_0017_upgrades_and_keeps_every_row(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    at_0017 = foundation_command(_alembic("upgrade", "0017_execution_queue"), url)
    assert at_0017.returncode == 0, at_0017.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_attempt(connection, label="before-0018")
            norms = _seed_norms(connection)
            connection.execute(text(
                "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
                "blob_id, blob_role) VALUES (:run, :job, :attempt, 'text_analysis', :blob, 'stage_output')"
            ), {**ids, "blob": _available_blob(connection, sha256="9" * 64, size=7)})
        upgraded = foundation_command(_alembic("upgrade", "head"), url)
        assert upgraded.returncode == 0, upgraded.describe()
        with engine.connect() as connection:
            assert _head(connection) == "0019_execution_workers"
            assert connection.execute(text(
                "SELECT unreliable_count FROM norms_snapshot WHERE norms_snapshot_id = :s"
            ), {"s": norms["snapshot"]}).scalar_one() == 0
            assert connection.execute(text(
                "SELECT text_reliability FROM norm_paragraph WHERE norm_paragraph_id = :p"
            ), {"p": norms["paragraph"]}).scalar_one() == "reliable"
            assert connection.execute(text(
                "SELECT state, abandoned_at FROM analysis_artifact_publication WHERE run_id = :run"
            ), ids).one() == ("prepared", None)
            assert connection.execute(text(
                "SELECT worker_id FROM lease WHERE lease_id = :lease"
            ), ids).scalar_one() is None
    finally:
        engine.dispose()


def test_retained_custody_data_refuses_the_0018_downgrade(empty_database, foundation_command) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            norms = _seed_norms(connection)
            _admit(connection, target_id=norms["document"],
                   blob_id=str(derive_blob_id(sha256=PDF_SHA, size=PDF_SIZE)))
        to_0018 = foundation_command(_alembic("downgrade", "0018_norm_custody"), url)
        assert to_0018.returncode == 0, to_0018.describe()
        refused = foundation_command(_alembic("downgrade", "0017_execution_queue"), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0018_norm_custody" in refused.stderr
        assert "norm_custody_admission" in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == "0018_norm_custody"
            assert connection.execute(text("SELECT count(*) FROM norm_custody_admission")).scalar_one() == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize("retained", ["repair_call", "abandoned_publication", "unreliable_text"])
def test_every_other_retained_0018_fact_refuses_the_downgrade(
    empty_database, foundation_command, retained: str,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "0018_norm_custody"), url)
    assert up.returncode == 0, up.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            if retained == "repair_call":
                _repair_call(connection)
            elif retained == "abandoned_publication":
                ids = _seed_attempt(connection, label="abandon")
                blob = _available_blob(connection, sha256="8" * 64, size=3)
                connection.execute(text(
                    "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, "
                    "stage_id, blob_id, blob_role) VALUES (:run, :job, :attempt, "
                    "'text_analysis', :blob, 'stage_output')"
                ), {**ids, "blob": blob})
                connection.execute(text(
                    "UPDATE analysis_artifact_publication SET state = 'abandoned', "
                    "abandoned_at = clock_timestamp() WHERE run_id = :run"
                ), ids)
            else:
                _seed_norms(connection, unreliable_count=1)
        refused = foundation_command(_alembic("downgrade", "0017_execution_queue"), url)
        assert refused.returncode != 0
        assert "refusing to downgrade 0018_norm_custody" in refused.stderr
        with engine.connect() as connection:
            assert _head(connection) == "0018_norm_custody"
    finally:
        engine.dispose()


def test_an_empty_0018_downgrades_and_restores_the_update_only_guards(
    empty_database, foundation_command,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    up = foundation_command(_alembic("upgrade", "head"), url)
    assert up.returncode == 0, up.describe()
    down = foundation_command(_alembic("downgrade", "0017_execution_queue"), url)
    assert down.returncode == 0, down.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.connect() as connection:
            assert _head(connection) == "0017_execution_queue"
            for table in ("norm_custody_admission", "norm_custody_binding", "norm_repair_call", "worker"):
                assert connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one() is None
            definitions = connection.execute(text(
                "SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t "
                "WHERE t.tgname IN ('trg_provider_call_effect_state_guard', "
                "'trg_analysis_artifact_state_guard') AND NOT t.tgisinternal"
            )).scalars().all()
            assert len(definitions) == 2
            assert all("BEFORE UPDATE ON" in definition for definition in definitions), definitions
            raw_key = connection.execute(text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_norms_snapshot_raw_key'"
            )).scalar_one()
            assert "unreliable_count" not in raw_key
        again = foundation_command(_alembic("upgrade", "head"), url)
        assert again.returncode == 0, again.describe()
    finally:
        engine.dispose()


# --- D-148 and D-142 -------------------------------------------------------------------------


def test_an_effect_row_inserted_in_a_non_initial_state_is_refused(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        ids = _seed_attempt(connection, label="d148")
        blob = _available_blob(connection, sha256="7" * 64, size=5)
        _refused(connection,
                 "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, attempt_id, "
                 "stage_id, provider, model_identity, provider_mode, request_sha256, state, "
                 "error_code) VALUES ('mc_01M2545JSD15ETSNNV904X991K', :run, :job, :attempt, "
                 "'text_analysis', 'anthropic', 'a-model', 'recorded', :sha, 'outcome_unknown', "
                 "'dependency_unavailable')",
                 {**ids, "sha": "1" * 64}, sqlstate="AM001")
        _refused(connection,
                 "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
                 "blob_id, blob_role, state, artifact_role, bound_at) VALUES (:run, :job, :attempt, "
                 "'text_analysis', :blob, 'stage_output', 'bound', 'analysis.text', clock_timestamp())",
                 {**ids, "blob": blob}, sqlstate="AM001")
        # The control: the same rows inserted `prepared` are accepted.
        connection.execute(text(
            "INSERT INTO provider_call_effect (model_call_id, run_id, job_id, attempt_id, stage_id, "
            "provider, model_identity, provider_mode, request_sha256) VALUES "
            "('mc_01M2545JSD15ETSNNV904X991K', :run, :job, :attempt, 'text_analysis', "
            "'anthropic', 'a-model', 'recorded', :sha)"
        ), {**ids, "sha": "1" * 64})
        connection.execute(text(
            "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
            "blob_id, blob_role) VALUES (:run, :job, :attempt, 'text_analysis', :blob, 'stage_output')"
        ), {**ids, "blob": blob})


def test_a_prepared_publication_settles_as_abandoned_and_stays_there(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        ids = _seed_attempt(connection, label="d142")
        blob = _available_blob(connection, sha256="6" * 64, size=4)
        connection.execute(text(
            "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
            "blob_id, blob_role) VALUES (:run, :job, :attempt, 'text_analysis', :blob, 'stage_output')"
        ), {**ids, "blob": blob})
        where = "WHERE run_id = :run AND blob_id = :blob"
        params = {**ids, "blob": blob}
        _refused(connection,
                 f"UPDATE analysis_artifact_publication SET state = 'abandoned' {where}",
                 params, sqlstate="23514", constraint="ck_analysis_artifact_abandoned_shape")
        _refused(connection,
                 "UPDATE analysis_artifact_publication SET state = 'abandoned', "
                 f"abandoned_at = clock_timestamp(), blob_role = 'other_role' {where}",
                 params, sqlstate="AM003")
        connection.execute(text(
            f"UPDATE analysis_artifact_publication SET state = 'abandoned', abandoned_at = clock_timestamp() {where}"
        ), params)
        assert connection.execute(text(
            f"SELECT state FROM analysis_artifact_publication {where}"
        ), params).scalar_one() == "abandoned"
        _refused(connection,
                 "UPDATE analysis_artifact_publication SET state = 'bound', abandoned_at = NULL, "
                 f"artifact_role = 'analysis.text', bound_at = clock_timestamp() {where}",
                 params, sqlstate="AM001")


def test_a_bound_publication_is_never_abandoned(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        ids = _seed_attempt(connection, label="bound")
        blob = _available_blob(connection, sha256="5" * 64, size=4)
        params = {**ids, "blob": blob}
        connection.execute(text(
            "INSERT INTO analysis_artifact_publication (run_id, job_id, attempt_id, stage_id, "
            "blob_id, blob_role) VALUES (:run, :job, :attempt, 'text_analysis', :blob, 'stage_output')"
        ), params)
        connection.execute(text(
            "UPDATE analysis_artifact_publication SET state = 'bound', artifact_role = 'analysis.text', "
            "bound_at = clock_timestamp() WHERE run_id = :run AND blob_id = :blob"
        ), params)
        _refused(connection,
                 "UPDATE analysis_artifact_publication SET state = 'abandoned', artifact_role = NULL, "
                 "bound_at = NULL, abandoned_at = clock_timestamp() WHERE run_id = :run AND blob_id = :blob",
                 params, sqlstate="AM001")


# --- custody: roles, admissions and bindings -------------------------------------------------


@pytest.mark.parametrize(
    ("override", "value"),
    [
        ("role", "norm_retrieval_set"),
        ("role", "project_source"),
        ("target_kind", "norm_catalogue"),
        ("target_kind", "norms_snapshot"),
        ("anchor_kind", "page"),
        ("target_id", "ns_01M2545JSD15ETSNNV904X991K"),
    ],
)
def test_an_unknown_role_or_target_kind_is_refused(
    migrated_engine: Engine, override: str, value: str,
) -> None:
    with migrated_engine.begin() as connection:
        norms = _seed_norms(connection)
        blob_id = str(derive_blob_id(sha256=PDF_SHA, size=PDF_SIZE))
        fields = {"role": "norm_source", "target_kind": "norm_document",
                  "target_id": norms["document"], "anchor_kind": "pdf"}
        fields[override] = value
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                _admit(connection, blob_id=blob_id, **fields)
        assert _sqlstate(refused) == "23514"
        assert _constraint(refused) == "ck_norm_custody_role_shape"
        # The control: the declared role, target kind and anchor kinds are admitted.
        _admit(connection, blob_id=blob_id, target_id=norms["document"], anchor_kind="pdf")
        _admit(connection, blob_id=blob_id, target_id=norms["document"], anchor_kind="crop",
               anchor="doc_portal-1/blk_1/0")


def test_an_admission_is_created_pending_and_its_identity_never_moves(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        norms = _seed_norms(connection)
        blob_id = str(derive_blob_id(sha256=PDF_SHA, size=PDF_SIZE))
        with pytest.raises(DBAPIError) as refused:
            with connection.begin_nested():
                _admit(connection, blob_id=blob_id, target_id=norms["document"], state="confirmed")
        assert _sqlstate(refused) == "AM001"
        admission = _admit(connection, blob_id=blob_id, target_id=norms["document"])
        params = {"id": admission}
        # A second live admission for the same binding slot is refused.
        with pytest.raises(DBAPIError) as duplicate:
            with connection.begin_nested():
                _admit(connection, blob_id=blob_id, target_id=norms["document"])
        assert _sqlstate(duplicate) == "23505"
        _refused(connection, "UPDATE norm_custody_admission SET anchor = 'doc_other' "
                 "WHERE norm_custody_admission_id = :id", params, sqlstate="AM003")
        _refused(connection, "UPDATE norm_custody_admission SET state = 'confirmed' "
                 "WHERE norm_custody_admission_id = :id", params, sqlstate="23514",
                 constraint="ck_norm_custody_admission_confirmed_shape")
        _refused(connection, "UPDATE norm_custody_admission SET attempt_count = 6 "
                 "WHERE norm_custody_admission_id = :id", params, sqlstate="23514",
                 constraint="ck_norm_custody_admission_attempts")
        # Five tries, then poisoned; requeue returns it to pending with a fresh count.
        connection.execute(text("UPDATE norm_custody_admission SET attempt_count = 5, "
                                "state = 'poisoned', last_failure = 'staged_upload_lost' "
                                "WHERE norm_custody_admission_id = :id"), params)
        connection.execute(text("UPDATE norm_custody_admission SET attempt_count = 0, "
                                "state = 'pending' WHERE norm_custody_admission_id = :id"), params)
        _confirm(connection, admission)
        _refused(connection, "UPDATE norm_custody_admission SET state = 'pending', confirmed_at = NULL "
                 "WHERE norm_custody_admission_id = :id", params, sqlstate="AM003")
        _refused(connection, "DELETE FROM norm_custody_admission WHERE norm_custody_admission_id = :id",
                 params, sqlstate="AM003")


def test_a_binding_needs_a_confirmed_admission_its_verified_blob_and_the_target(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.begin() as connection:
        norms = _seed_norms(connection)
        blob_id = str(derive_blob_id(sha256=PDF_SHA, size=PDF_SIZE))
        admission = _admit(connection, blob_id=blob_id, target_id=norms["document"])
        bind = ("INSERT INTO norm_custody_binding (norm_custody_binding_id, "
                "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, "
                "blob_id) VALUES (:id, :admission, 'norm_source', 'norm_document', :target, "
                "'pdf', :anchor, :blob)")
        params = {"id": str(NormCustodyBindingId.new()), "admission": admission,
                  "target": norms["document"], "anchor": "doc_portal-1", "blob": blob_id}
        # Pending admission, and no blob row yet: refused by the guard, not by a foreign key.
        _refused(connection, bind, params, sqlstate="AM001")
        _available_blob(connection)
        _refused(connection, bind, params, sqlstate="AM001")
        _confirm(connection, admission)
        # A tuple that is not the admission's own is refused by the composite foreign key.
        _refused(connection, bind, {**params, "anchor": "doc_portal-2"}, sqlstate="23503",
                 constraint="fk_norm_custody_binding_admission_tuple")
        binding = _bind(connection, admission=admission, target_id=norms["document"], blob_id=blob_id)
        _refused(connection, "UPDATE norm_custody_binding SET bound_at = clock_timestamp() "
                 "WHERE norm_custody_binding_id = :id", {"id": binding}, sqlstate="AM003")
        _refused(connection, "DELETE FROM norm_custody_binding WHERE norm_custody_binding_id = :id",
                 {"id": binding}, sqlstate="AM003")


def test_a_binding_whose_bytes_disagree_with_the_admission_is_refused(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        norms = _seed_norms(connection)
        # Verified bytes under the derived id whose media type disagrees with the admission.
        blob_id = _available_blob(connection, media_type="image/png")
        admission = _admit(connection, blob_id=blob_id, target_id=norms["document"])
        _confirm(connection, admission)
        with pytest.raises(DBAPIError) as mismatched:
            with connection.begin_nested():
                _bind(connection, admission=admission, target_id=norms["document"], blob_id=blob_id)
        assert _sqlstate(mismatched) == "AM001"


def test_an_admission_whose_target_never_arrived_stays_unbound(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        norms = _seed_norms(connection)
        blob_id = _available_blob(connection)
        absent = "ndoc_01M2545JSD15ETSNNV904X991K"
        orphan = _admit(connection, blob_id=blob_id, target_id=absent, anchor="doc_portal-9")
        _confirm(connection, orphan)
        with pytest.raises(DBAPIError) as targetless:
            with connection.begin_nested():
                _bind(connection, admission=orphan, target_id=absent, blob_id=blob_id,
                      anchor="doc_portal-9")
        assert _sqlstate(targetless) == "AM001"
        # The control: the same bytes bind to a target that exists.
        present = _admit(connection, blob_id=blob_id, target_id=norms["document"])
        _confirm(connection, present)
        _bind(connection, admission=present, target_id=norms["document"], blob_id=blob_id)


# --- the repair journal ----------------------------------------------------------------------


def test_a_repair_call_is_created_prepared_and_settles_once(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        mismatched = str(NormRepairCallId.new())
        with pytest.raises(DBAPIError) as scope:
            with connection.begin_nested():
                _repair_call(connection, scope=mismatched)
        assert _sqlstate(scope) == "23514" and _constraint(scope) == "ck_norm_repair_call_scope"
        with pytest.raises(DBAPIError) as initial:
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO norm_repair_call (norm_repair_call_id, idempotency_scope, "
                    "block_anchor, crop_sha256, request_sha256, model, attempt_number, state, "
                    "charged_usd, failure, terminal_at) VALUES (:id, :id, 'blk_1', :c, :r, "
                    "'opus-5', 1, 'not_processed', 0, 'rate_limited', clock_timestamp())"
                ), {"id": str(NormRepairCallId.new()), "c": "e" * 64, "r": "f" * 64})
        assert _sqlstate(initial) == "AM001"

        call = _repair_call(connection)
        params = {"id": call}
        _refused(connection, "UPDATE norm_repair_call SET state = 'completed', response_sha256 = :s, "
                 "charged_usd = 0.1, terminal_at = clock_timestamp() WHERE norm_repair_call_id = :id",
                 {**params, "s": "0" * 64}, sqlstate="AM001")
        connection.execute(text(
            "UPDATE norm_repair_call SET state = 'response_received', response_sha256 = :s, "
            "response_model = 'opus-5', cost_usd = 0.12 WHERE norm_repair_call_id = :id"
        ), {**params, "s": "0" * 64})
        _refused(connection, "UPDATE norm_repair_call SET state = 'completed', response_sha256 = :s, "
                 "charged_usd = 0.12, terminal_at = clock_timestamp() WHERE norm_repair_call_id = :id",
                 {**params, "s": "1" * 64}, sqlstate="AM003")
        connection.execute(text(
            "UPDATE norm_repair_call SET state = 'completed', charged_usd = 0.12, "
            "terminal_at = clock_timestamp() WHERE norm_repair_call_id = :id"
        ), params)
        _refused(connection, "UPDATE norm_repair_call SET charged_usd = 0 WHERE norm_repair_call_id = :id",
                 params, sqlstate="AM003")
        _refused(connection, "DELETE FROM norm_repair_call WHERE norm_repair_call_id = :id",
                 params, sqlstate="AM003")

        unknown = _repair_call(connection, attempt=2)
        _refused(connection, "UPDATE norm_repair_call SET state = 'outcome_unknown', "
                 "failure = 'proxy_unavailable', terminal_at = clock_timestamp() "
                 "WHERE norm_repair_call_id = :id", {"id": unknown}, sqlstate="23514",
                 constraint="ck_norm_repair_call_outcome_shape")
        connection.execute(text(
            "UPDATE norm_repair_call SET state = 'outcome_unknown', failure = 'proxy_unavailable', "
            "charged_usd = 0.20, terminal_at = clock_timestamp() WHERE norm_repair_call_id = :id"
        ), {"id": unknown})
        # The same try twice is one row: a retry is a new try with the next attempt number.
        with pytest.raises(DBAPIError) as duplicate:
            with connection.begin_nested():
                _repair_call(connection, attempt=2)
        assert _sqlstate(duplicate) == "23505"


# --- unreliable text -------------------------------------------------------------------------


def test_the_raw_key_rule_counts_unreliable_blocks(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        # Unreliable blocks with the base key unchanged: the key must say `+<m>u`.
        _refused(connection,
                 "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
                 "content_digest, undated_documents, document_count, repair_count, "
                 "segmentation_profile, unreliable_count) VALUES (:id, 'k', 'k', :d, 0, 1, 0, "
                 "'markdown-v1', 2)",
                 {"id": str(NormsSnapshotId.new()), "d": "d" * 64},
                 sqlstate="23514", constraint="ck_norms_snapshot_raw_key")
        _refused(connection,
                 "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
                 "content_digest, undated_documents, document_count, repair_count, "
                 "segmentation_profile, unreliable_count) VALUES (:id, 'k2', 'k2', :d, 0, 1, 0, "
                 "'markdown-v1', -1)",
                 {"id": str(NormsSnapshotId.new()), "d": "d" * 64},
                 sqlstate="23514")
        # The controls: unreliable-only and repaired-only snapshots carry their own keys.
        _seed_norms(connection, unreliable_count=3)
        _seed_norms(connection, repaired=True)
        norms = _seed_norms(connection)
        pk = connection.execute(text(
            "SELECT norm_document_pk FROM norm_document WHERE norm_document_id = :d"
        ), {"d": norms["document"]}).scalar_one()
        _refused(connection,
                 "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, "
                 "ordinal, page_label, block_ref, char_offset, char_length, kind, text, "
                 "text_reliability) VALUES (:id, :s, :pk, 1, 1, 'block-2', 10, 3, 'body', 'abc', 'unknown')",
                 {"id": str(NormParagraphId.new()), "s": norms["snapshot"], "pk": pk},
                 sqlstate="23514", constraint="ck_norm_paragraph_text_reliability")
        connection.execute(text(
            "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, "
            "ordinal, page_label, block_ref, char_offset, char_length, kind, text, "
            "text_reliability) VALUES (:id, :s, :pk, 1, 1, 'block-2', 10, 3, 'body', 'abc', 'unreliable')"
        ), {"id": str(NormParagraphId.new()), "s": norms["snapshot"], "pk": pk})
