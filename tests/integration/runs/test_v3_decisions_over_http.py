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

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
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
    finding_of: dict[str, str] = field(default_factory=dict)
    observation_of: dict[str, str] = field(default_factory=dict)


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
        for scope in SCOPES:
            x[f"findings_{scope}"] = wire.call("GET", f"/runs/{out.run_of[scope]}/findings", token=tokens["expert"])
            x[f"status_{scope}"] = wire.call("GET", f"/runs/{out.run_of[scope]}", token=tokens["expert"])
        x["review_after"] = wire.call("GET", f"{accept.GROUPS}/{out.group_id}/review", token=tokens["expert"])
        out.db["frozen_before"] = accept._rows(factory, """
            SELECT o.finding_observation_id, o.finding_text, o.proposed_severity, o.required_value, o.stated_value,
                   (SELECT count(*) FROM finding_evidence e WHERE e.finding_observation_id = o.finding_observation_id),
                   (SELECT count(*) FROM finding_observation_norm_citation c WHERE c.finding_observation_id = o.finding_observation_id)
              FROM finding_observation o ORDER BY 1""")
        # -- piece 3: the verdict path, on the findings the terminals published ------------------
        found = {scope: x[f"findings_{scope}"].data["items"][0] for scope in PROVISIONAL_SCOPES}
        out.finding_of = {scope: item["finding_uid"] for scope, item in found.items()}
        out.observation_of = {scope: item["observation"]["finding_observation_id"] for scope, item in found.items()}
        f1, f2, a1 = (out.finding_of[k] for k in PROVISIONAL_SCOPES)
        o1, o2, oa = (out.observation_of[k] for k in PROVISIONAL_SCOPES)
        decisions = lambda uid: f"/findings/{uid}/decisions"  # noqa: E731
        x["before_report_F1"] = x["report_F1"]
        x["before_review"] = x["review_after"]
        x["accept"] = wire.call("POST", decisions(f1), token=tokens["expert"], key="verdict-accept",
                                body={"event_type": "accept", "finding_observation_id": o1, "severity": "economic"})
        x["accept_again"] = wire.call("POST", decisions(f1), token=tokens["expert"], key="verdict-accept",
                                      body={"event_type": "accept", "finding_observation_id": o1, "severity": "economic"})
        x["accept_other_body"] = wire.call("POST", decisions(f1), token=tokens["expert"], key="verdict-accept",
                                           body={"event_type": "reject", "finding_observation_id": o1})
        x["reject"] = wire.call("POST", decisions(f2), token=tokens["expert"], key="verdict-reject",
                                body={"event_type": "reject", "finding_observation_id": o2, "comment": "Норма не применима."})
        x["comment"] = wire.call("POST", decisions(a1), token=tokens["expert"], key="verdict-comment",
                                 body={"event_type": "comment", "finding_observation_id": oa, "comment": "Нужна проверка редакции."})
        x["admin_verdict"] = wire.call("POST", decisions(a1), token=tokens["admin"], key="verdict-admin",
                                       body={"event_type": "accept", "finding_observation_id": oa})
        x["suspended_verdict"] = wire.call("POST", decisions(a1), token=tokens["suspended"], key="verdict-susp",
                                           body={"event_type": "accept", "finding_observation_id": oa})
        x["anonymous_verdict"] = wire.call("POST", decisions(a1), key="verdict-anon",
                                           body={"event_type": "accept", "finding_observation_id": oa})
        x["keyless_verdict"] = wire.call("POST", decisions(a1), token=tokens["expert"],
                                         body={"event_type": "accept", "finding_observation_id": oa})
        x["foreign_observation"] = wire.call("POST", decisions(a1), token=tokens["expert"], key="verdict-foreign",
                                             body={"event_type": "accept", "finding_observation_id": o1})
        x["absent_finding"] = wire.call("POST", decisions("fnd_" + "0" * 26), token=tokens["expert"], key="verdict-absent",
                                        body={"event_type": "accept", "finding_observation_id": o1})
        x["severity_on_reject"] = wire.call("POST", decisions(a1), token=tokens["expert"], key="verdict-sev",
                                            body={"event_type": "reject", "finding_observation_id": oa, "severity": "critical"})
        for scope in PROVISIONAL_SCOPES:
            uid = out.finding_of[scope]
            x[f"finding_{scope}_decided"] = wire.call("GET", f"/findings/{uid}", token=tokens["expert"])
            x[f"history_{scope}"] = wire.call("GET", decisions(uid), token=tokens["expert"])
        for scope in SCOPES:
            x[f"findings_{scope}_decided"] = wire.call("GET", f"/runs/{out.run_of[scope]}/findings", token=tokens["expert"])
        x["csv_F1"] = wire.call("GET", f"/runs/{out.run_of['F1']}/export.csv", token=tokens["expert"])
        x["journal"] = wire.call("GET", "/decisions", token=tokens["expert"])
        x["report_F1_decided"] = wire.call("GET", report_path(out.run_of["F1"]), token=tokens["expert"])
        x["review_decided"] = wire.call("GET", f"{accept.GROUPS}/{out.group_id}/review", token=tokens["expert"])
        out.db["events"] = accept._rows(factory, """
            SELECT finding_uid, event_type, verdict, severity, author_label, author_user_uid IS NOT NULL
              FROM expert_decision_event ORDER BY sequence_no""")
        out.db["frozen_after"] = accept._rows(factory, """
            SELECT o.finding_observation_id, o.finding_text, o.proposed_severity, o.required_value, o.stated_value,
                   (SELECT count(*) FROM finding_evidence e WHERE e.finding_observation_id = o.finding_observation_id),
                   (SELECT count(*) FROM finding_observation_norm_citation c WHERE c.finding_observation_id = o.finding_observation_id)
              FROM finding_observation o ORDER BY 1""")
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
        out.db["observations"] = accept._rows(factory, """
            SELECT o.run_id, o.finding_uid, o.finding_observation_id, o.stage_id, o.category, o.grounded,
                   o.ungrounded_reason, o.analysis_profile_id, o.provider_mode, o.proposed_severity,
                   o.norm_citation_count, o.required_value, o.stated_value, o.model_call_id,
                   f.canonical_observation_id
              FROM finding_observation o LEFT JOIN finding f ON f.finding_uid = o.finding_uid
              JOIN ar_v3_run_group_member m ON m.run_id = o.run_id
             WHERE m.group_id = :g ORDER BY o.run_id""", g=out.group_id)
        out.db["evidence"] = accept._rows(factory, """
            SELECT o.run_id, e.evidence_ordinal, e.page_number, e.quote, e.char_start, e.char_end
              FROM finding_evidence e JOIN finding_observation o USING (finding_observation_id)
              JOIN ar_v3_run_group_member m ON m.run_id = o.run_id WHERE m.group_id = :g ORDER BY 1, 2""",
            g=out.group_id)
        out.db["citations"] = accept._rows(factory, """
            SELECT c.run_id, c.citation_ordinal, c.norm_document_id, c.norm_paragraph_id, c.quote, c.state
              FROM finding_observation_norm_citation c
              JOIN ar_v3_run_group_member m ON m.run_id = c.run_id WHERE m.group_id = :g ORDER BY 1, 2""",
            g=out.group_id)
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


# --- publication (piece 2) ---------------------------------------------------------------------


def _observations(world: World, scope: str) -> list[tuple[Any, ...]]:
    return [row for row in world.db["observations"] if row[0] == world.run_of[scope]]


@pytest.mark.parametrize("scope", PROVISIONAL_SCOPES)
def test_each_provisional_proposal_is_one_grounded_normative_finding_with_its_evidence_and_citation(
    world: World, scope: str
) -> None:
    (row,) = _observations(world, scope)
    (run_id, finding_uid, observation, stage, category, grounded, reason, profile, mode, severity,
     citations, required, stated, model_call, canonical) = row
    assert (stage, category, grounded, reason) == ("text_analysis", "evacuation", True, None)
    assert profile == str(AR_V3_BETA_PROFILE_ID) and mode == "recorded"
    assert severity == "operational" and citations == 1 and canonical == observation
    assert (required, stated) == (accept.REQUIRED_VALUE, accept.STATED_VALUE)  # stored, never served
    assert world.db["finding_rows"][run_id] == 1
    (evidence,) = [e for e in world.db["evidence"] if e[0] == run_id]
    assert evidence[2:4] == (accept.EVIDENCE_PAGE, accept.EVIDENCE_QUOTE)
    assert evidence[5] - evidence[4] == len(accept.EVIDENCE_QUOTE)
    (citation,) = [c for c in world.db["citations"] if c[0] == run_id]
    assert citation[1] == 1 and citation[4] == accept.NORM_QUOTE and citation[5] == "verified"


@pytest.mark.parametrize("scope", WITHHELD_SCOPES)
def test_a_proposal_withheld_by_the_beta_policy_leaves_no_row_of_any_kind(world: World, scope: str) -> None:
    assert _observations(world, scope) == []
    assert world.db["finding_rows"][world.run_of[scope]] == 0
    assert not [c for c in world.db["citations"] if c[0] == world.run_of[scope]]


def test_a_rejected_proposal_is_in_no_table_at_all(world: World) -> None:
    """Six rejected proposals (one per Run) and no diagnostic row: the review keeps their count only."""
    assert all(row[5] is True and row[6] is None for row in world.db["observations"])
    assert len(world.db["observations"]) == len(PROVISIONAL_SCOPES)


@pytest.mark.parametrize("scope", SCOPES)
def test_the_run_status_counts_the_published_findings(world: World, scope: str) -> None:
    status = world.x[f"status_{scope}"].data
    assert status["state"] == "published"
    assert status["published_finding_count"] == (1 if scope in PROVISIONAL_SCOPES else 0)


@pytest.mark.parametrize("scope", PROVISIONAL_SCOPES)
def test_a_new_finding_is_pending_with_no_decided_severity_and_no_number_on_the_wire(world: World, scope: str) -> None:
    answer = world.x[f"findings_{scope}"]
    assert answer.status == 200, answer.text
    (item,) = answer.data["items"]
    assert item["current_verdict"] == "pending" and item["latest_decision_id"] is None
    assert "decided_severity" not in item
    assert item["observation"]["proposed_severity"] == "operational"
    assert not {"required_value", "stated_value"} & _keys(answer.data)
    assert item["run_id"] == world.run_of[scope] and item["category"] == "evacuation"


@pytest.mark.parametrize("scope", WITHHELD_SCOPES)
def test_a_run_with_nothing_provisional_lists_no_finding(world: World, scope: str) -> None:
    assert world.x[f"findings_{scope}"].data["items"] == []


@pytest.mark.parametrize("scope", PROVISIONAL_SCOPES)
def test_the_report_lists_exactly_the_finding_the_run_listed(world: World, scope: str) -> None:
    (item,) = world.x[f"findings_{scope}"].data["items"]
    (entry,) = world.x[f"report_{scope}"].data["findings"]
    assert entry["finding_uid"] == item["finding_uid"]
    assert entry["canonical"]["finding_observation_id"] == item["observation"]["finding_observation_id"]
    (citation,) = entry["canonical"]["norm_citations"]
    assert citation["quote"] == accept.NORM_QUOTE and citation["state"] == "verified"
    assert entry["merged_observations"] == []


def test_the_group_review_still_verifies_all_six_runs_with_the_findings_in_place(world: World) -> None:
    review = world.x["review_after"].data
    assert [m["review_state"] for m in review["members"]] == ["available"] * 6
    for member in review["members"]:
        proposals = member["review"]["provisional_citations"]
        assert len(proposals) == (1 if member["scope_id"] in PROVISIONAL_SCOPES else 0)


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
        # The claimed numbers may appear only inside a verbatim quote field (the norm's own words).
        for key, value in accept._leaves(world.x[f"report_{scope}"].data):
            if isinstance(value, str) and any(c in value for c in (accept.REQUIRED_VALUE, accept.STATED_VALUE)):
                assert key == "quote", (key, value)
        assert accept.UNGROUNDED_VALUE not in text_
        for prose in accept.MODEL_PROSE:
            assert prose not in text_


def test_the_report_refuses_a_suspended_account_an_anonymous_caller_and_an_absent_run(world: World) -> None:
    accept.check_typed_refusal(
        world.x["report_suspended"], "permission_denied", {"required_capability": "role:admin|expert"})
    accept.check_typed_refusal(world.x["report_anonymous"], "authentication_required", None)
    accept.check_typed_refusal(world.x["report_absent"], "not_found", {"aggregate_type": "AuditRun"})


# --- the verdict path (piece 3) -----------------------------------------------------------------


def test_an_expert_records_accept_reject_and_comment_on_published_findings(world: World) -> None:
    for name, event_type, verdict in (("accept", "accept", "accepted"), ("reject", "reject", "rejected"),
                                      ("comment", "comment", None)):
        answer = world.x[name]
        assert answer.status == 201, answer.text
        assert answer.data["event"]["event_type"] == event_type
        assert answer.data["event"].get("verdict") == verdict
    assert world.x["accept"].data["current_verdict"] == "accepted"
    assert world.x["accept"].data["event"]["severity"] == "economic"
    assert world.x["comment"].data["current_verdict"] == "pending"  # a comment is not a judgement


def test_the_author_is_the_verified_subject_never_a_field_of_the_request(world: World) -> None:
    labels = {row[4] for row in world.db["events"]}
    assert labels == {"Сьютова Е."} and all(row[5] for row in world.db["events"])  # an account is recorded
    assert len(world.db["events"]) == 3  # replays, refusals and the keyless call appended nothing


def test_the_same_key_and_body_replays_the_first_event_and_appends_nothing(world: World) -> None:
    assert world.x["accept_again"].status == 201
    assert world.x["accept_again"].data["event"]["decision_id"] == world.x["accept"].data["event"]["decision_id"]


def test_the_same_key_with_another_body_is_a_reused_key_and_appends_nothing(world: World) -> None:
    accept.check_typed_refusal(world.x["accept_other_body"], "idempotency_key_reuse",
                               world.x["accept_other_body"].data.get("details"))


@pytest.mark.parametrize("name", ["admin_verdict", "suspended_verdict"])
def test_only_an_expert_may_record_a_verdict(world: World, name: str) -> None:
    accept.check_typed_refusal(world.x[name], "permission_denied", {"required_capability": "role:expert"})


def test_an_anonymous_verdict_is_refused(world: World) -> None:
    accept.check_typed_refusal(world.x["anonymous_verdict"], "authentication_required", None)


def test_a_verdict_without_an_idempotency_key_is_refused(world: World) -> None:
    answer = world.x["keyless_verdict"]
    assert 400 <= answer.status < 500 and answer.data["error_code"] in {"validation_failed", "idempotency_key_required"}


def test_a_verdict_needs_the_observation_of_that_finding(world: World) -> None:
    assert world.x["foreign_observation"].status == 404
    assert world.x["foreign_observation"].data["error_code"] == "not_found"


def test_a_proposal_without_a_finding_has_nothing_to_decide(world: World) -> None:
    """Withheld, rejected and non-normative proposals are not findings, so no uid names them."""
    assert world.x["absent_finding"].status == 404 and world.x["absent_finding"].data["error_code"] == "not_found"
    for scope in WITHHELD_SCOPES:
        assert world.x[f"findings_{scope}_decided"].data["items"] == []


def test_a_severity_is_refused_on_anything_but_an_accept(world: World) -> None:
    assert world.x["severity_on_reject"].status == 422


def test_the_verdict_and_the_decided_severity_follow_from_the_ledger_not_from_the_model(world: World) -> None:
    f1 = world.x["finding_F1_decided"].data
    assert (f1["current_verdict"], f1["decided_severity"], f1["decision_event_count"]) == ("accepted", "economic", 1)
    assert f1["observation"]["proposed_severity"] == "operational"  # the model's proposal is not overwritten
    f2 = world.x["finding_F2_decided"].data
    assert (f2["current_verdict"], f2["latest_comment"]) == ("rejected", "Норма не применима.")
    assert "decided_severity" not in f2
    a1 = world.x["finding_A1_decided"].data
    assert (a1["current_verdict"], a1["decision_event_count"], a1["latest_comment"]) == (
        "pending", 1, "Нужна проверка редакции.")
    for scope in PROVISIONAL_SCOPES:
        (item,) = world.x[f"findings_{scope}_decided"].data["items"]
        assert item["current_verdict"] == world.x[f"finding_{scope}_decided"].data["current_verdict"]


def test_history_and_journal_list_the_events_in_the_order_they_were_taken(world: World) -> None:
    for scope, expected in (("F1", 1), ("F2", 1), ("A1", 1)):
        assert len(world.x[f"history_{scope}"].data["items"]) == expected
    journal = world.x["journal"].data["items"]
    assert {entry["finding_uid"] for entry in journal} == set(world.finding_of.values())


def test_a_verdict_changes_no_evidence_no_citation_and_no_sentence_of_the_model(world: World) -> None:
    """The raw grounded evidence and the model's text are byte-for-byte what was published."""
    assert world.db["frozen_after"] == world.db["frozen_before"]
    assert len(world.db["frozen_before"]) == len(PROVISIONAL_SCOPES) and all(row[5] == 1 and row[6] == 1 for row in world.db["frozen_before"])


def test_the_report_and_the_sealed_group_review_are_identical_after_the_verdicts(world: World) -> None:
    assert world.x["report_F1_decided"].body == world.x["before_report_F1"].body
    assert world.x["review_decided"].body == world.x["before_review"].body


def test_the_finding_read_carries_the_certified_citation_and_no_number(world: World) -> None:
    for scope in PROVISIONAL_SCOPES:
        answer = world.x[f"finding_{scope}_decided"]
        (citation,) = answer.data["norm_citations"]
        assert citation["quote"] == accept.NORM_QUOTE and citation["state"] == "verified"
        assert citation["designation"] and citation["title"] and citation["page_label"] >= 1
        assert answer.data["observation"]["norm_citations"] == answer.data["norm_citations"]
        assert not {"required_value", "stated_value"} & _keys(answer.data)


def test_the_run_csv_lists_the_published_finding_with_its_verdict_and_no_number_column(world: World) -> None:
    """The CSV export (not this lane's code) reads the same rows; it must not become a back door."""
    answer = world.x["csv_F1"]
    assert answer.status == 200
    header, *rows = answer.text.lstrip("\ufeff").splitlines()
    columns = header.split(",")
    assert "required_value" not in columns and "stated_value" not in columns
    assert len(rows) == 1 and world.finding_of["F1"] in rows[0] and "accepted" in rows[0]
