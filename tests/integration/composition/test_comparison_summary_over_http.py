"""`COMPARE-PERSISTED-SUMMARY-01` (B2), end to end: the summary of the approved pairs over HTTP.

The composed ASGI application (``create_asgi_app``) with the recorded provider, against the lane's
PostgreSQL (migrated to ``0035`` with its summary table) and MinIO. Two versions of one document are
uploaded and both analysed by recorded runs, so the comparison has real versions, real runs and real
receipts; the **text** the comparison reads is replaced by a synthetic pair (the recorded analysis
corpus holds one document, which has no differences with itself), and the summary model is the
recorded one reading a directory of this test's own: no live model is reachable.

In order: an expert is refused a summary while nothing is approved, an administrator who is not an
expert is refused; after an approval the command stores a ``ready`` summary from the recording and
the read serves it with its label beside the raw differences, which are byte for byte what they were;
the same key and another key answer the stored summary and call nothing; a second approval makes the
summary a superseded one and a second command without a recording is an explicit refusal that stores
nothing; a recording whose reply cites a change that does not exist is stored as ``rejected`` and
shown as an answer; the audit trail holds one event per stored summary; a missing key or body is
``422``.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.comparison.approved_evidence import raw_artifact
from auditmanager.comparison.summary_input import prepare_version_summary_input
from auditmanager.comparison.summary_model import recording_document
from auditmanager.comparison.summary_prompt import build_request
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

DEPLOYMENT_SECRET = "comparison-summary-over-http-token"
EXPERT, ADMIN = "comparison-summary", "comparison-summary-admin"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BUNDLE = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles" / "ar_baseline.zip"
LABEL = "Сводка подготовлена моделью, проверка человеком не проводилась"


def _page(number: int, revision: str) -> str:
    frame = "\n".join(f"Штамп строка {k}" for k in range(12))
    body = "\n".join(f"Лист {number} позиция {k} размер {k * 10}" for k in range(40))
    return f"{frame}\nЛист {number} изм. {revision}\n{body}\n"


def _synthetic_pages(is_source: bool, page_count: int) -> dict[int, str]:
    pages = {n: _page(n, "1" if is_source else "2") for n in range(1, page_count + 1)}
    if not is_source:
        pages[2] = pages[2].replace("позиция 3 размер 30", "позиция 3 размер 35")
    return pages


def _expert() -> dict[str, str]:
    from am_test_accounts import provisioned_credential

    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, EXPERT)}"}


def _admin() -> dict[str, str]:
    from am_test_accounts import provisioned_credential, provisioned_record

    from auditmanager.access.public import AccountRepository

    record = provisioned_record(ADMIN)
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with Session(engine) as session:
            accounts = AccountRepository()
            if accounts.roles_of(session, str(record.user_uid)) != frozenset({"admin"}):
                seed = session.execute(
                    text("SELECT user_uid FROM app_user WHERE login = 'admin'")
                ).scalar_one()
                accounts.set_roles(
                    session, actor_uid=str(seed), user_uid=str(record.user_uid), roles=frozenset({"admin"}),
                )
            session.commit()
    finally:
        engine.dispose()
    return {"Authorization": f"Bearer {provisioned_credential(DEPLOYMENT_SECRET, ADMIN)}"}


def _upload(client: TestClient, auth: dict[str, str], project_uid: str, tag: str) -> dict[str, Any]:
    boundary = "comparisonsummaryboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.zip"\r\nContent-Type: application/zip\r\n\r\n'
    ).encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth | {
            IDEMPOTENCY_HEADER: f"cmpsum-{tag}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_BUNDLE.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _second_version(document_uid: str, version_uid: str) -> str:
    from auditmanager.documents.public import DocumentRepository
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.identity import DocumentUid, VersionUid

    engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
    try:
        with engine.begin() as connection:
            session = Session(bind=connection)
            documents = DocumentRepository()
            base = documents.get_version(session, VersionUid.parse(version_uid))
            published = documents.publish_version(
                session, document_uid=DocumentUid.parse(document_uid), media_type=base.media_type,
                byte_size=base.byte_size, sha256=base.sha256, page_count=base.page_count,
                source_filename="ar_baseline_v2.zip", entries=base.manifest,
                text_character_count=base.text_character_count, textless_pages=base.textless_pages,
                recognised_character_count=base.recognised_character_count,
            )
            session.flush()
            return str(published)
    finally:
        engine.dispose()


def _json(world: dict[str, Any], who: str = "expert", key: str | None = None) -> dict[str, str]:
    headers = world[who] | {"Content-Type": "application/json"}
    return headers if key is None else headers | {IDEMPOTENCY_HEADER: key}


def _key(world: dict[str, Any], label: str) -> str:
    return f"cmpsum-{world['tag']}-{label}"


@pytest.fixture(scope="module")
def world():
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.bootstrap import adapters
    from auditmanager.api.app import create_asgi_app
    from auditmanager.comparison.public import SavedPageText

    recordings = Path(tempfile.mkdtemp(prefix="cmpsum-recordings-"))
    holder: dict[str, str] = {}

    def synthetic_text(self, session, *, run_id, version):  # noqa: ANN001
        return SavedPageText(
            run_id, "e" * 64, _synthetic_pages(version.version_uid == holder["v1"], version.page_count),
        )

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("auditmanager.comparison.summary_model.default_recording_dir", lambda: recordings)
        patch.setattr(adapters._AnalysisReader, "saved_page_text", synthetic_text)
        app = create_asgi_app(environ=dict(os.environ) | {
            "AUDITMANAGER_PROVIDER_MODE": "recorded", API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
        })
        client = TestClient(app, raise_server_exceptions=False)
        tag = uuid.uuid4().hex[:12]
        world: dict[str, Any] = {
            "app": app, "client": client, "expert": _expert(), "admin": _admin(), "tag": tag,
            "recordings": recordings,
        }
        answer = client.post(
            "/projects", headers=_json(world, key=_key(world, "prj")),
            content=json.dumps({"name": f"Сводка сравнения {tag}"}).encode("utf-8"),
        )
        assert answer.status_code == 201, answer.content
        project_uid = answer.json()["project_uid"]
        first = _upload(client, world["expert"], project_uid, f"{tag}-v1")
        v2 = _second_version(first["document_uid"], first["version_uid"])
        holder |= {"v1": first["version_uid"], "v2": v2}
        world |= {"project_uid": project_uid, "document_uid": first["document_uid"], "v1": holder["v1"], "v2": v2}
        for version_uid in (holder["v1"], v2):
            classified = client.put(
                f"/projects/{project_uid}/documents/{world['document_uid']}/versions/{version_uid}/classification",
                headers=_json(world),
                content=json.dumps({"project_stage": "P", "section_code": "PB"}).encode("utf-8"),
            )
            assert classified.status_code == 200, classified.content
            started = client.post(
                "/runs", headers=_json(world, key=_key(world, version_uid[-6:])),
                content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
            )
            assert started.status_code == 202, started.content
        assert app.state.run_carrier.drain(timeout=300), "the runs never finished"
        yield world


def _base(world: dict[str, Any]) -> str:
    return (
        f"/projects/{world['project_uid']}/documents/{world['document_uid']}"
        f"/versions/{world['v1']}/comparison"
    )


def _compare(world: dict[str, Any]) -> dict[str, Any]:
    answer = world["client"].get(
        _base(world), params={"target_version_uid": world["v2"]}, headers=world["expert"],
    )
    assert answer.status_code == 200, answer.content
    assert answer.json()["outcome"] == "compared", answer.json()["refusal"]
    return answer.json()


def _approve(world: dict[str, Any], page: int, label: str) -> dict[str, Any]:
    row = next(
        r for r in _compare(world)["sheets"]
        if r["source_page_number"] == page and r["target_page_number"] == page
    )
    answer = world["client"].post(
        f"{_base(world)}/sheet-pairings", headers=_json(world, key=_key(world, label)),
        content=json.dumps({
            "target_version_uid": world["v2"], "mode": "version", "source_page_number": page,
            "target_page_number": page, "suggestion_sha256": row["suggestion_sha256"],
        }).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    return answer.json()


def _generate(world: dict[str, Any], key: str | None, who: str = "expert", body: dict | None = None) -> Any:
    return world["client"].post(
        f"{_base(world)}/summaries", headers=_json(world, who, key),
        content=json.dumps({"target_version_uid": world["v2"], "mode": "version"} if body is None else body).encode(
            "utf-8"),
    )


def _expected_request(world: dict[str, Any], comparison_id: str):
    """The request the command will make, rebuilt here from the read, with this test's own pages."""
    read = _compare(world)
    approved = read["approved_pairs"]
    source, target = read["source"], read["target"]

    def facts(side: dict[str, Any]) -> VersionFacts:
        return VersionFacts(
            side["version_uid"], read["document_uid"], read["project_uid"], side["version_ordinal"],
            side["sha256"], 1, side["page_count"], "application/pdf",
        )

    pair = OrderedVersionPair(read["project_uid"], read["document_uid"], facts(source), facts(target))
    diffs, seal = raw_artifact(
        pair=pair, comparison_id=comparison_id, link_revision=approved["link_revision"],
        links=[(i["sheet_link_id"], i["source_page_number"], i["target_page_number"]) for i in approved["items"]],
        source_pages=_synthetic_pages(True, source["page_count"]),
        target_pages=_synthetic_pages(False, target["page_count"]),
    )
    assert seal.seal_sha256 == approved["raw_evidence_seal_sha256"]
    return build_request(prepare_version_summary_input(version_pair=pair, raw_diffs=diffs, raw_seal=seal))


def _record(world: dict[str, Any], request, statements: list[dict[str, Any]]) -> None:
    document = recording_document(
        request=request, output_text=json.dumps({"statements": statements}, ensure_ascii=False),
        input_tokens=200, output_tokens=60, note="test", origin={"kind": "synthetic"},
    )
    (world["recordings"] / f"{request.request_sha256}.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _raw_bytes(world: dict[str, Any]) -> str:
    return json.dumps(_compare(world)["approved_pairs"]["items"], ensure_ascii=False, sort_keys=True)


def _events(comparison_id: str) -> list[str]:
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            return list(connection.execute(
                text("SELECT event_type FROM audit_event WHERE aggregate_id = :c ORDER BY sequence_no"),
                {"c": comparison_id},
            ).scalars())
    finally:
        engine.dispose()


def test_the_summary_is_a_command_that_stores_beside_unchanged_raw_differences(world) -> None:
    assert _compare(world)["approved_pairs"]["summary"] is None
    nothing = _generate(world, _key(world, "none"))
    assert nothing.status_code == 409, nothing.content
    assert nothing.json()["details"]["conflict_reason"] == "summary_evidence_not_sealed"
    refused = _generate(world, _key(world, "admin"), who="admin")
    assert refused.status_code == 403, refused.content
    assert refused.json()["details"]["required_capability"] == "role:expert"

    approved = _approve(world, 2, "approve-2")
    comparison_id = approved["comparison_id"]
    request = _expected_request(world, comparison_id)
    assert len(request.hunk_ids) == 2
    _record(world, request, [
        {"text": "На листе 2 размер изменён с 30 на 35.", "hunk_ids": [request.hunk_ids[1]]},
        {"text": "На листе 2 изменена отметка изменения.", "hunk_ids": [request.hunk_ids[0]]},
    ])
    before = _raw_bytes(world)

    stored = _generate(world, _key(world, "gen-1"))
    assert stored.status_code == 201, stored.content
    body = stored.json()
    assert body["replayed"] is False
    summary = body["summary"]
    assert summary["state"] == "ready" and summary["rejection_reason"] is None
    assert summary["label"] == LABEL
    assert (summary["provider_mode"], summary["model_identity"], summary["cost_basis"]) == (
        "recorded", "recorded", "unmetered",
    )
    assert summary["is_current"] is True and summary["link_revision"] == 1
    assert [s["hunk_ids"] for s in summary["statements"]] == [[request.hunk_ids[1]], [request.hunk_ids[0]]]
    assert summary["input_sha256"] == request.input_sha256
    assert summary["raw_evidence_seal_sha256"] == approved["raw_evidence_seal_sha256"]

    for label in ("gen-1", "gen-2"):  # the same key, and another key for the same input
        again = _generate(world, _key(world, label))
        assert again.status_code == 201 and again.json() == {"summary": summary, "replayed": True}

    read = _compare(world)["approved_pairs"]
    assert read["summary"] == summary
    assert _raw_bytes(world) == before  # beside the raw differences, never in them

    # a second approval supersedes the set the summary describes
    _approve(world, 3, "approve-3")
    assert _compare(world)["approved_pairs"]["summary"]["is_current"] is False
    # the second set has no recording: an explicit refusal that stores nothing
    missing = _generate(world, _key(world, "gen-3"))
    assert missing.status_code == 422, missing.content
    assert missing.json()["error_code"] == "analysis_input_invalid"
    assert missing.json()["details"]["reason"] == "recording_missing"
    assert _compare(world)["approved_pairs"]["summary"]["summary_id"] == summary["summary_id"]

    # a reply that cites a change which does not exist is stored as rejected and shown as an answer
    second = _expected_request(world, comparison_id)
    link = second.hunk_ids[0].split(":")[0]
    _record(world, second, [{"text": "Выдумано.", "hunk_ids": [f"{link}:99"]}])
    rejected = _generate(world, _key(world, "gen-4"))
    assert rejected.status_code == 201, rejected.content
    answer = rejected.json()["summary"]
    assert answer["state"] == "rejected" and answer["rejection_reason"] == "unknown_hunk_reference"
    assert answer["statements"] == [] and answer["label"] == LABEL and answer["link_revision"] == 2
    latest = _compare(world)["approved_pairs"]["summary"]
    assert latest["summary_id"] == answer["summary_id"] and latest["is_current"] is True

    assert _events(comparison_id).count("comparison.summary_generated") == 2
    assert _events(comparison_id)[:3] == [
        "comparison.sheet_link_approved", "comparison.summary_generated", "comparison.sheet_link_approved",
    ]


def test_a_summary_request_without_its_key_or_its_body_is_refused(world) -> None:
    assert _generate(world, None).status_code == 422
    empty = _generate(world, _key(world, "empty"), body={})
    assert empty.status_code == 422, empty.content
    extra = _generate(world, _key(world, "extra"), body={
        "target_version_uid": world["v2"], "mode": "version", "model": "another"})
    assert extra.status_code == 422, extra.content  # the model is never chosen by the caller


def test_only_a_process_in_recorded_mode_holds_a_summary_model() -> None:
    from auditmanager.bootstrap.composition import summary_model_for
    from auditmanager.comparison.public import RecordedSummaryModel

    assert isinstance(summary_model_for("recorded"), RecordedSummaryModel)
    for mode in ("live", "proxy", "anything else"):
        assert summary_model_for(mode) is None
