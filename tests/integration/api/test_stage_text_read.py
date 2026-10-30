"""The frozen Stage Text GETs serve stored evidence and retain typed refusals."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from auditmanager.comparison.stage_text.store import StageTextEvidenceStore
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_text.test_store import _batch, _completed_run, _seed
from tests.support.accounts import provisioned_credential, provisioned_record

SECRET = "stage-text-read-http-token"


def _client(modules: str) -> TestClient:
    environment = dict(os.environ) | {
        API_TOKEN_VARIABLE: SECRET, COMPARISON_MODULES_ENV: modules,
    }
    app = create_app(environ=environment)
    return TestClient(create_asgi_app(environ=environment, application=app),
                      raise_server_exceptions=False)


def test_stage_text_gets_over_real_http() -> None:
    assert os.environ.get("DATABASE_URL"), "run on the isolated C3 stack at 0041"
    provisioned_record("stage-text-read")
    credential = provisioned_credential(SECRET, "stage-text-read")
    headers = {"Authorization": f"Bearer {credential}"}
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.begin() as connection:
            session = Session(bind=connection)
            _store, pair, revision, actor, left, right = _seed(session)
        off = _client("versions")
        off_result = off.get(f"/stage-pairs/{pair}/text-fragments", headers=headers)
        assert off_result.status_code == 503
        assert off_result.json()["details"] == {"dependency": "comparison_modules"}

        app = _client("versions,stages")
        before = app.get(f"/stage-link-revisions/{revision}/raw-differences", headers=headers)
        assert before.status_code == 503
        assert before.json()["details"] == {"dependency": "comparison_stage_text_evidence"}

        fragments, manifest, raw = _batch(left, right)
        StageTextEvidenceStore(sessionmaker(bind=engine, expire_on_commit=False)).write(
            pair_id=pair, revision_id=revision, fragments=fragments,
            expected_keys=manifest, raw=raw, hints=(),
        )
        with engine.begin() as connection:
            _completed_run(Session(bind=connection), pair, revision, actor, left, right)
        first = app.get(f"/stage-pairs/{pair}/text-fragments?limit=2", headers=headers)
        assert first.status_code == 200, first.text
        assert len(first.json()["items"]) == 2
        cursor = first.json()["page"]["next_cursor"]
        assert cursor
        second = app.get(f"/stage-pairs/{pair}/text-fragments",
                         params={"limit": 2, "cursor": cursor}, headers=headers)
        assert second.status_code == 200, second.text
        assert len(second.json()["items"]) == 2
        assert second.json()["page"]["next_cursor"] is None
        assert len({item["fragment_id"] for item in first.json()["items"]
                    + second.json()["items"]}) == 4

        exclusions = app.get(f"/stage-link-revisions/{revision}/text-exclusions", headers=headers)
        differences = app.get(f"/stage-link-revisions/{revision}/raw-differences", headers=headers)
        hints = app.get(f"/stage-link-revisions/{revision}/text-hints", headers=headers)
        assert (exclusions.status_code, differences.status_code, hints.status_code) == (200, 200, 200)
        assert len(exclusions.json()["items"]) == len(differences.json()["items"]) == 1
        assert hints.json()["items"] == []
        assert differences.json()["items"][0]["status"] == "changed"

        bad = app.get(f"/stage-pairs/{pair}/text-fragments",
                      params={"cursor": "not-a-cursor"}, headers=headers)
        assert bad.status_code == 422
        recompute_key = f"stage-text-read-{new_ulid()}"
        recompute = app.post(
            f"/stage-link-revisions/{revision}/text-evidence/recomputation",
            headers=headers | {"Idempotency-Key": recompute_key},
        )
        assert recompute.status_code == 202, recompute.text
        assert recompute.json()["state"] == "queued"
        assert [step["step_no"] for step in recompute.json()["steps"]] == [2, 3]
        replay = app.post(
            f"/stage-link-revisions/{revision}/text-evidence/recomputation",
            headers=headers | {"Idempotency-Key": recompute_key},
        )
        assert replay.status_code == 202 and replay.json() == recompute.json()
    finally:
        engine.dispose()
