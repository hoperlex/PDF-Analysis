"""The composed C3 pair API serves its DB lane only with stages enabled."""

from __future__ import annotations

import os
import hashlib
import io
import zipfile
from pathlib import Path

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from auditmanager.shared.identity import new_ulid
from tests.support.accounts import provisioned_credential, provisioned_record

SECRET = "stage-pair-http-suite-token"
PDF = Path("tests/e2e/pc01/journey/fixtures/w28-live/w28_own_document.pdf").read_bytes()


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def client(modules: str) -> TestClient:
    environ = dict(os.environ) | {
        API_TOKEN_VARIABLE: SECRET,
        COMPARISON_MODULES_ENV: modules,
    }
    app = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=app),
                      raise_server_exceptions=False)


def test_pair_catalog_suggestion_and_keyed_expert_confirmation_over_http() -> None:
    assert os.environ.get("DATABASE_URL"), "run on the isolated C3 stack at 0041"
    account = provisioned_record("stage-pair-http")
    actor = str(account.user_uid)
    token = provisioned_credential(SECRET, "stage-pair-http")
    headers = {"Authorization": f"Bearer {token}"}
    project, left, right = uid("prj"), uid("doc"), uid("doc")
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage HTTP')"),
                {"project": project},
            )
            for document, stage in ((left, "P"), (right, "R")):
                version = uid("ver")
                connection.execute(
                    text(
                        "INSERT INTO document (document_uid, project_uid, display_title) "
                        "VALUES (:document, :project, 'Site 01')"
                    ),
                    {"document": document, "project": project},
                )
                connection.execute(
                    text(
                        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                        "media_type, byte_size, sha256, page_count) "
                        "VALUES (:version, :document, 1, 'application/pdf', 4096, :sha, 1)"
                    ),
                    {"version": version, "document": document, "sha": "d" * 64},
                )
                connection.execute(
                    text(
                        "INSERT INTO document_version_classification "
                        "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
                        "VALUES (:version, :stage, 'AR', :actor)"
                    ),
                    {"version": version, "stage": stage, "actor": actor},
                )

        off = client("versions")
        refusal = off.get(f"/projects/{project}/stage-pairs", headers=headers)
        assert refusal.status_code == 503
        assert refusal.json()["details"] == {"dependency": "comparison_modules"}

        served = client("versions,stages")
        suggestions = served.get(
            f"/projects/{project}/stage-pair-suggestions", headers=headers,
        )
        assert suggestions.status_code == 200, suggestions.text
        assert [(item["left_document_uid"], item["right_document_uid"])
                for item in suggestions.json()["items"]] == [(left, right)]
        keyed = headers | {"Idempotency-Key": f"stage-pair-http-{new_ulid()}"}
        body = {"left_document_uid": left, "right_document_uid": right}
        first = served.post(f"/projects/{project}/stage-pairs", headers=keyed, json=body)
        replay = served.post(f"/projects/{project}/stage-pairs", headers=keyed, json=body)
        assert first.status_code == replay.status_code == 201, (first.text, replay.text)
        pair_id = first.json()["pair_id"]
        assert replay.json()["pair_id"] == pair_id
        assert served.get(f"/stage-pairs/{pair_id}", headers=headers).json()["state"] == "confirmed"
        listed = served.get(f"/projects/{project}/stage-pairs", headers=headers)
        assert listed.status_code == 200
        assert [item["pair_id"] for item in listed.json()["items"]] == [pair_id]
        assert served.get(
            f"/projects/{project}/stage-pair-suggestions", headers=headers,
        ).json()["items"] == []
        completion = served.post(
            f"/stage-pairs/{pair_id}/completeness",
            headers=headers | {"Idempotency-Key": f"stage-complete-http-{new_ulid()}"},
            json={"completeness": "full"},
        )
        assert completion.status_code == 200, completion.text
        assert completion.json()["completeness"] == "full"
    finally:
        engine.dispose()


def test_stage_upload_pdf_reaches_one_classified_version_over_http() -> None:
    assert os.environ.get("DATABASE_URL"), "run on the isolated C3 stack at 0041"
    account = provisioned_record("stage-upload-http")
    actor = str(account.user_uid)
    token = provisioned_credential(SECRET, "stage-upload-http")
    headers = {"Authorization": f"Bearer {token}"}
    project = uid("prj")
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage upload HTTP')"),
                {"project": project},
            )
        app = client("versions,stages")
        declared = app.post(
            f"/projects/{project}/stage-uploads",
            headers=headers | {"Idempotency-Key": f"stage-http-create-{new_ulid()}"},
            json={"files": [{
                "display_name": "АР-01.pdf", "media_kind": "pdf",
                "size_bytes": len(PDF), "sha256": hashlib.sha256(PDF).hexdigest(),
            }]},
        )
        assert declared.status_code == 201, declared.text
        upload_id = declared.json()["upload_id"]
        file_id = declared.json()["files"][0]["file_id"]
        assert declared.json()["candidates"] == []
        staged = app.put(
            f"/stage-uploads/{upload_id}/files/{file_id}/parts?part_number=1",
            headers=headers | {
                "Idempotency-Key": f"stage-http-part-{new_ulid()}",
                "content-type": "application/octet-stream",
            }, content=PDF,
        )
        assert staged.status_code == 200, staged.text
        assert staged.json()["received_bytes"] == len(PDF)
        completed = app.post(
            f"/stage-uploads/{upload_id}/files/{file_id}/completion",
            headers=headers | {"Idempotency-Key": f"stage-http-complete-{new_ulid()}"},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["state"] == "ready"
        listed = app.get(f"/projects/{project}/stage-uploads", headers=headers)
        assert listed.status_code == 200, listed.text
        assert [item["upload_id"] for item in listed.json()["items"]] == [upload_id]
        candidate = app.get(f"/stage-uploads/{upload_id}", headers=headers).json()["candidates"][0]
        assert candidate["state"] == "proposed"
        keyed = headers | {"Idempotency-Key": f"stage-http-confirm-{new_ulid()}"}
        body = {"stage": "P", "section_code": "AR", "designation": "АР-01"}
        first = app.post(
            f"/stage-upload-candidates/{candidate['candidate_id']}/confirmation",
            headers=keyed, json=body,
        )
        replay = app.post(
            f"/stage-upload-candidates/{candidate['candidate_id']}/confirmation",
            headers=keyed, json=body,
        )
        assert first.status_code == replay.status_code == 200, (first.text, replay.text)
        assert first.json() == replay.json()
        assert first.json()["state"] == "published"
        with engine.connect() as connection:
            actual = connection.execute(text(
                "SELECT v.upload_kind, c.project_stage, c.section_code "
                "FROM document_version v JOIN version_classification_current c "
                "ON c.version_uid = v.version_uid WHERE v.version_uid = :version"
            ), {"version": first.json()["version_uid"]}).one()
        assert actual == ("comparison_pdf", "P", "AR")
        assert actor.startswith("usr_")
    finally:
        engine.dispose()


def test_stage_zip_with_macosx_member_refuses_before_any_candidate_over_http() -> None:
    assert os.environ.get("DATABASE_URL"), "run on the isolated C3 stack at 0041"
    token = provisioned_credential(SECRET, "stage-upload-http")
    headers = {"Authorization": f"Bearer {token}"}
    project = uid("prj")
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage ZIP refusal')"),
                {"project": project},
            )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as writer:
            writer.writestr("АР-01.pdf", PDF)
            writer.writestr("__MACOSX/._АР-01.pdf", PDF)
        raw = output.getvalue()
        app = client("versions,stages")
        created = app.post(
            f"/projects/{project}/stage-uploads",
            headers=headers | {"Idempotency-Key": f"stage-bad-create-{new_ulid()}"},
            json={"files": [{
                "display_name": "Набор.zip", "media_kind": "zip",
                "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            }]},
        )
        assert created.status_code == 201, created.text
        upload_id = created.json()["upload_id"]
        file_id = created.json()["files"][0]["file_id"]
        staged = app.put(
            f"/stage-uploads/{upload_id}/files/{file_id}/parts?part_number=1",
            headers=headers | {
                "Idempotency-Key": f"stage-bad-part-{new_ulid()}",
                "content-type": "application/octet-stream",
            }, content=raw,
        )
        assert staged.status_code == 200, staged.text
        refused = app.post(
            f"/stage-uploads/{upload_id}/files/{file_id}/completion",
            headers=headers | {"Idempotency-Key": f"stage-bad-complete-{new_ulid()}"},
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["error_code"] == "validation_failed"
        state = app.get(f"/stage-uploads/{upload_id}", headers=headers)
        assert state.status_code == 200
        assert state.json()["candidates"] == []
        assert state.json()["files"][0]["state"] == "failed"
    finally:
        engine.dispose()
