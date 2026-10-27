"""AR-V3-DECISIONS-01 (``R-146as``, ``R-146at``): the norm-verification report and the verdict path, over HTTP.

The six AR v3 beta Runs of one group are driven exactly as ``test_v3_recorded_group_over_http.py``
drives them (the stock recorded composition, a sealed synthetic pack, the recorded reply written on
first sight), by loading that module's own helpers by path and editing nothing. This module then
reads what the product now serves: ``getRunNormVerification`` for every Run (and its refusals),
and, in the later pieces of the lane, the published findings and the verdicts.

The recorded reply makes two proposals over ``N1``, the first item of each scope: ordinal 0 is
grounded and ordinal 1 is rejected (``stated_value_not_in_evidence``). In the scopes whose first
item is context-only (A2: C15, S1: C21, S2: C22) ordinal 0 is withheld by the beta policy.
So F1, F2 and A1 each have one provisional proposal; A2, S1 and S2 have none.

Everything is measured once in a module-scoped fixture; the tests read what was captured.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.runs.public import ReviewAttestation, seal_manifest
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # before execution: ``@dataclass(slots=True)`` resolves through it
    spec.loader.exec_module(module)
    return module


accept = _load("ar_v3_accept_http_helpers", "test_v3_recorded_group_over_http.py")
probe = accept.probe
#: The probe's module-scoped fixture: a fresh database migrated to head, dropped afterwards.
probe_database = probe.probe_database

REVIEW = ReviewAttestation(
    reviewer="Test Reviewer", capacity="expert", reviewed_at="2026-10-27",
    decision_ref="TEST-RULING-DECISIONS", scope_statement="six synthetic scopes, test only",
)
#: The scopes whose first topic (N1) is provisional: they hold one provisional proposal each.
PROVISIONAL_SCOPES = ("F1", "F2", "A1")
#: The scopes whose first topic is context-only: the proposal is withheld by policy.
WITHHELD_SCOPES = ("A2", "S1", "S2")
SCOPES = PROVISIONAL_SCOPES + WITHHELD_SCOPES
REJECTED = {"stated_value_not_in_evidence": 1}
#: The version's text facts as an upload leaves them (``ingest``): the report needs the textless-page
#: context, and the probe's ``_publish_source`` leaves it unset. Two pages are recorded as text-less
#: so that the report is seen to pass the list through.
TEXTLESS_PAGES = (2, 5)


def _publish_with_text_facts(session: Any, store: Any, *, title: str, actor: str) -> Any:
    """The probe's source, published with the three text counts a real upload records."""
    real = DocumentRepository.publish_version

    def publish(self: Any, session: Any, **kwargs: Any) -> Any:
        kwargs.update(text_character_count=1000, textless_pages=TEXTLESS_PAGES,
                      recognised_character_count=0)
        return real(self, session, **kwargs)

    patch = pytest.MonkeyPatch()
    patch.setattr(DocumentRepository, "publish_version", publish)
    try:
        return probe._publish_source(session, store, title=title, register_blob=True, actor=actor)
    finally:
        patch.undo()


@dataclass(slots=True)
class World:
    x: dict[str, Any] = field(default_factory=dict)
    db: dict[str, Any] = field(default_factory=dict)
    group_id: str = ""
    run_of: dict[str, str] = field(default_factory=dict)
    set_of: dict[str, str] = field(default_factory=dict)
    snapshot_id: str = ""
    version_uid: str = ""
    provider_requests: int = 0


def report_path(run_id: str) -> str:
    return f"/runs/{run_id}/norm-verification"


def _drive(url: str, blob_store: Any, recordings: Path, manifest_dir: Path) -> World:
    out = World()
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(url)))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    built: list[Any] = []
    try:
        with factory() as session, session.begin():
            probe._require_probe_database(session.execute(text("SELECT current_database()")).scalar_one())
            expert = accept._account(session, "decisions-expert", ("expert",))
            admin = accept._account(session, "decisions-admin", ("admin",))
            suspended = accept._account(session, "decisions-suspended", ())
            served = _publish_with_text_facts(session, blob_store, title="AR v3 decisions",
                                              actor=str(expert.user_uid))
            pack = probe._seed_norms(session, blob_store, served, str(expert.user_uid))
        tokens = {"expert": accept._token(expert), "admin": accept._token(admin),
                  "suspended": accept._token(suspended)}
        out.version_uid = served.version_uid
        manifest = manifest_dir / "ar-v3-pack.json"
        manifest.write_bytes(seal_manifest(pack, REVIEW))
        app = accept._build(accept._environment(url, manifest), recordings)
        built.append(app)
        wire = app.wire
        x = out.x

        x["start"] = wire.call("POST", accept.GROUPS, token=tokens["expert"], key="decisions-start",
                               body={"version_uid": served.version_uid})
        group = x["start"].data
        out.group_id = group["group_id"]
        for member in group["members"]:
            out.run_of[member["scope_id"]] = member["run_id"]
            out.set_of[member["scope_id"]] = member["norm_retrieval_set_id"]
        out.snapshot_id = group["norms_snapshot_id"]
        # Before anything runs every Run is queued: the report has nothing verified to answer.
        x["report_queued"] = wire.call("GET", report_path(out.run_of["F1"]), token=tokens["expert"])

        app.replay.release.set()
        app.held.release()
        assert app.application.carrier.drain(timeout=300), "the six Runs never finished"
        out.provider_requests = len(app.replay.requests)
        out.db["states"] = dict(accept._runs_of_group(factory, out.group_id))

        for scope in SCOPES:
            run_id = out.run_of[scope]
            x[f"report_{scope}"] = wire.call("GET", report_path(run_id), token=tokens["expert"])
            x[f"report_{scope}_again"] = wire.call("GET", report_path(run_id), token=tokens["expert"])
            x[f"report_{scope}_admin"] = wire.call("GET", report_path(run_id), token=tokens["admin"])
        run_f1 = out.run_of["F1"]
        x["report_suspended"] = wire.call("GET", report_path(run_f1), token=tokens["suspended"])
        x["report_anonymous"] = wire.call("GET", report_path(run_f1))
        x["report_absent"] = wire.call("GET", report_path("run_" + "0" * 26), token=tokens["expert"])
        out.db["textless"] = accept._rows(
            factory, "SELECT textless_pages FROM document_version WHERE version_uid = :v", v=served.version_uid)
        out.db["finding_rows"] = dict(accept._rows(factory, """
            SELECT r.run_id, (SELECT count(*) FROM finding f WHERE f.allocated_by_run_id = r.run_id)
              FROM audit_run r JOIN ar_v3_run_group_member m ON m.run_id = r.run_id
             WHERE m.group_id = :g""", g=out.group_id))
    finally:
        for item in built:
            item.replay.release.set()
            item.application.carrier.shutdown()
            item.application.session_factory.kw["bind"].dispose()
        engine.dispose()
    return out


@pytest.fixture(scope="module")
def world(probe_database: str, blob_store: Any, tmp_path_factory: pytest.TempPathFactory) -> World:
    result = _drive(probe_database, blob_store, tmp_path_factory.mktemp("decisions-recordings"),
                    tmp_path_factory.mktemp("decisions-pack"))
    print("DECISIONS-MEASUREMENT " + json.dumps(
        {"x": {k: [v.status, v.data] for k, v in result.x.items()}, "db": result.db},
        ensure_ascii=False, default=str, sort_keys=True))
    return result


# --- the report (piece 1) --------------------------------------------------------------------


def test_the_six_runs_reached_published_and_the_provider_was_asked_once_each(world: World) -> None:
    assert set(world.db["states"].values()) == {"published"}
    assert len(world.db["states"]) == 6
    assert world.provider_requests == 6


def test_a_run_that_is_not_terminal_has_no_report_and_the_refusal_is_the_declared_503(world: World) -> None:
    answer = world.x["report_queued"]
    accept.check_typed_refusal(answer, "dependency_unavailable", {"dependency": "norm_verification_reader"})


@pytest.mark.parametrize("scope", SCOPES)
def test_every_terminal_run_answers_the_canonical_report_of_its_own_set(world: World, scope: str) -> None:
    answer = world.x[f"report_{scope}"]
    assert answer.status == 200, answer.text
    report = answer.data
    assert set(report) == {
        "run_id", "norms_snapshot_id", "norm_retrieval_set_id", "status", "findings",
        "withheld_by_reason", "textless_pages",
    }
    assert report["run_id"] == world.run_of[scope]
    assert report["norms_snapshot_id"] == world.snapshot_id
    assert report["norm_retrieval_set_id"] == world.set_of[scope]
    assert report["status"] == "complete"
    assert report["textless_pages"] == list(TEXTLESS_PAGES) == list(world.db["textless"][0][0])


@pytest.mark.parametrize("scope", SCOPES)
def test_the_rejected_proposal_is_counted_by_its_grounding_reason_in_every_run(world: World, scope: str) -> None:
    assert world.x[f"report_{scope}"].data["withheld_by_reason"] == REJECTED


@pytest.mark.parametrize("scope", WITHHELD_SCOPES)
def test_a_withheld_context_only_proposal_is_not_a_reason_and_not_a_finding(world: World, scope: str) -> None:
    report = world.x[f"report_{scope}"].data
    assert report["findings"] == []
    assert set(report["withheld_by_reason"]) <= {"stated_value_not_in_evidence"}
    assert world.db["finding_rows"][world.run_of[scope]] == 0


@pytest.mark.parametrize("scope", SCOPES)
def test_the_report_is_the_same_on_a_replay_and_for_an_administrator(world: World, scope: str) -> None:
    first = world.x[f"report_{scope}"]
    assert world.x[f"report_{scope}_again"].body == first.body
    assert world.x[f"report_{scope}_admin"].body == first.body


def _keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in _keys(value)}
    if isinstance(node, list):
        return {key for value in node for key in _keys(value)}
    return set()


def test_no_report_carries_a_number_the_model_claimed(world: World) -> None:
    for scope in SCOPES:
        text_ = world.x[f"report_{scope}"].text
        assert not {"required_value", "stated_value", "proposed_severity"} & _keys(world.x[f"report_{scope}"].data)
        for claim in (accept.REQUIRED_VALUE, accept.STATED_VALUE, accept.UNGROUNDED_VALUE):
            assert claim not in text_
        for prose in accept.MODEL_PROSE:
            assert prose not in text_


def test_the_report_refuses_a_suspended_account_an_anonymous_caller_and_an_absent_run(world: World) -> None:
    accept.check_typed_refusal(
        world.x["report_suspended"], "permission_denied", {"required_capability": "role:admin|expert"})
    accept.check_typed_refusal(world.x["report_anonymous"], "authentication_required", None)
    accept.check_typed_refusal(world.x["report_absent"], "not_found", {"aggregate_type": "AuditRun"})
