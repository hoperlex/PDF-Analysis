"""The sealed stage-link HTTP surface now serves a complete expert map."""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.public import COMPARISON_MODULES_ENV, PAGE_PROFILE_ALGO_VERSION
from auditmanager.shared.identity import new_ulid
from tests.support.accounts import provisioned_credential, provisioned_record

SECRET = "stage-link-http-suite-token"


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def client(modules: str) -> TestClient:
    environment = dict(os.environ) | {
        API_TOKEN_VARIABLE: SECRET, COMPARISON_MODULES_ENV: modules,
    }
    app = create_app(environ=environment)
    return TestClient(create_asgi_app(environ=environment, application=app),
                      raise_server_exceptions=False)


def test_stage_link_passports_hint_expert_map_and_history_over_http() -> None:
    assert os.environ.get("DATABASE_URL"), "run on the isolated C3 stack at 0041"
    account = provisioned_record("stage-link-http")
    actor = str(account.user_uid)
    token = provisioned_credential(SECRET, "stage-link-http")
    headers = {"Authorization": f"Bearer {token}"}
    project = uid("prj")
    documents = (uid("doc"), uid("doc"))
    profiles = (uid("cpr"), uid("cpr"))
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO project (project_uid, name) VALUES (:project, 'Stage link HTTP')"
            ), {"project": project})
            for side, document, profile in zip(("P", "R"), documents, profiles, strict=True):
                version = uid("ver")
                connection.execute(text(
                    "INSERT INTO document (document_uid, project_uid, display_title) "
                    "VALUES (:document, :project, 'Корпус 4')"
                ), {"document": document, "project": project})
                connection.execute(text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                    "media_type, byte_size, sha256, page_count) "
                    "VALUES (:version, :document, 1, 'application/pdf', 4096, :sha, 1)"
                ), {"version": version, "document": document, "sha": "a" * 64})
                connection.execute(text(
                    "INSERT INTO document_version_classification "
                    "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
                    "VALUES (:version, :stage, 'AR', :actor)"
                ), {"version": version, "stage": side, "actor": actor})
                connection.execute(text(
                    "INSERT INTO comparison_page_profile "
                    "(comparison_page_profile_id, version_uid, page_number, content_key, "
                    "algo_version, status, profile) "
                    "VALUES (:profile, :version, 1, :key, :algo, 'ready', "
                    "CAST(:summary AS jsonb))"
                ), {"profile": profile, "version": version, "key": "1" * 64,
                    "algo": PAGE_PROFILE_ALGO_VERSION,
                    "summary": json.dumps({"stamp": {
                        "sheet_name": "План 2-го этажа корпус 4", "sheet_number": "АР-1",
                    }})})

        off = client("versions")
        refusal = off.get(f"/stage-pairs/{uid('stp')}/sheet-passports", headers=headers)
        assert refusal.status_code == 503
        assert refusal.json()["details"] == {"dependency": "comparison_modules"}

        app = client("versions,stages")
        confirmed = app.post(
            f"/projects/{project}/stage-pairs",
            headers=headers | {"Idempotency-Key": f"stage-pair-link-{new_ulid()}"},
            json={"left_document_uid": documents[0], "right_document_uid": documents[1]},
        )
        assert confirmed.status_code == 201, confirmed.text
        pair_id = confirmed.json()["pair_id"]

        passports = app.get(f"/stage-pairs/{pair_id}/sheet-passports", headers=headers)
        assert passports.status_code == 200, passports.text
        assert [(row["profile_id"], row["side"], row["building"], row["floor"])
                for row in passports.json()["items"]] == [
                    (profiles[0], "left", "4", "2"), (profiles[1], "right", "4", "2"),
                ]
        hints = app.get(f"/stage-pairs/{pair_id}/sheet-suggestions", headers=headers)
        assert hints.status_code == 200, hints.text
        assert hints.json()["items"][0]["confidence"] == "high"

        keyed = headers | {"Idempotency-Key": f"stage-map-http-{new_ulid()}"}
        body = {"items": [{
            "relation": "paired", "left_profile_id": profiles[0],
            "right_profile_id": profiles[1],
        }]}
        first = app.post(f"/stage-pairs/{pair_id}/sheet-map", headers=keyed, json=body)
        replay = app.post(f"/stage-pairs/{pair_id}/sheet-map", headers=keyed, json=body)
        assert first.status_code == replay.status_code == 201, (first.text, replay.text)
        assert first.json() == replay.json()
        revision_id = first.json()["revision_id"]
        assert first.json()["items"][0]["confidence"] == "manual"
        current = app.get(f"/stage-pairs/{pair_id}/sheet-map", headers=headers)
        history = app.get(f"/stage-pairs/{pair_id}/sheet-map/revisions", headers=headers)
        revision = app.get(f"/stage-link-revisions/{revision_id}", headers=headers)
        assert current.status_code == history.status_code == revision.status_code == 200
        assert current.json() == revision.json() == history.json()["items"][0]
    finally:
        engine.dispose()
