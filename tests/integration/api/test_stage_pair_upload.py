"""The composed C3 pair API serves its DB lane only with stages enabled."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from auditmanager.shared.identity import new_ulid
from tests.support.accounts import provisioned_credential, provisioned_record

SECRET = "stage-pair-http-suite-token"


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
