"""The upload declaration is durable, keyed and bounded before byte transfer."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage.uploads import StageDeclaredFile, StageUploadService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def test_stage_declaration_replays_and_lists_opaque_file_identities(
    comparison_session: Session,
) -> None:
    project, actor = uid("prj"), uid("usr")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage intake')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    service = StageUploadService(sessions)
    request = {
        "project_uid": project,
        "files": (
            StageDeclaredFile("Проект\u202e.zip", "zip", 10, "a" * 64),
            StageDeclaredFile("Том.pdf", "pdf", 20, "b" * 64),
        ),
        "user_uid": actor, "idempotency_key": f"stage-upload-{new_ulid()}",
    }
    created = service.create(**request)
    assert service.create(**request) == created
    assert created.state == "uploading"
    assert created.upload_id.startswith("stu_")
    assert [f.declaration.display_name for f in created.files] == ["Проект_.zip", "Том.pdf"]
    assert {f.file_id[:4] for f in created.files} == {"suf_"}
    assert created.candidates == ()
    assert service.get(created.upload_id) == created
    page, next_upload = service.page(
        project_uid=project, after_upload_id=None, limit=1,
    )
    assert page == (created,) and next_upload is None
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_upload_file WHERE stage_upload_id = :upload"),
        {"upload": created.upload_id},
    ).scalar_one() == 2

    with pytest.raises(DomainError) as reused:
        service.create(**(request | {
            "files": (StageDeclaredFile("Other.zip", "zip", 10, "a" * 64),),
        }))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    with pytest.raises(DomainError) as active:
        service.create(**(request | {"idempotency_key": f"stage-upload-second-{new_ulid()}"}))
    assert active.value.code is ErrorCode.CONFLICT


def test_stage_declaration_refuses_raw_total_before_any_row(
    comparison_session: Session,
) -> None:
    project = uid("prj")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage budget')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    with pytest.raises(DomainError) as refused:
        StageUploadService(sessions).create(
            project_uid=project,
            files=(
                StageDeclaredFile("a.zip", "zip", 2 * 1024**3, "a" * 64),
                StageDeclaredFile("b.pdf", "pdf", 1, "b" * 64),
            ),
            user_uid=uid("usr"), idempotency_key=f"stage-over-{new_ulid()}",
        )
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_upload WHERE project_uid = :project"),
        {"project": project},
    ).scalar_one() == 0
