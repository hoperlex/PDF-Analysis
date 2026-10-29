"""Helpers of the report lane's database tests (`CMP-VC-REPORT-01`): a stored series as the MD summary reads it, the recorded answers a handler is
asked for, and a driver for the worker's side. Plain code, no pytest: ``conftest.py`` hands it to a test, and it loads the shared AI-job support
(``ai_jobs/ai_jobs_support.py``) by path, as every C2 lane does.

Everything writes through the connection it is given; with the ``db`` fixture that connection is rolled back at the end of the test, so nothing of
a test stays in the lane's database (the blobs a test publishes stay in the lane's private bucket, unreferenced, as the other suites' do).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy.engine import Connection

from auditmanager.comparison.report import analytic, client, disciplines, plan as plan_module
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = _load("cmp_ai_jobs_support_for_report", Path(__file__).resolve().parents[1] / "ai_jobs" / "ai_jobs_support.py")
ACTOR = base.ACTOR
SHA = base.SHA
x = base.x
new_id = base.new_id
CODE = "133/23-ГК-ЭМ2"
_counter = [0]


def _key() -> str:
    _counter[0] += 1
    return hashlib.sha256(f"report-test-{_counter[0]}".encode()).hexdigest()


def report_world(connection: Connection, transitions: int = 3, *, described: bool = True, title: str = CODE) -> dict[str, Any]:
    """A project with a document of ``transitions + 1`` versions and a series with ``transitions`` transitions; every transition holds one sheet pair
    that differs (page 1 of both versions, sheet «1 · План») with a stored result. With ``described`` the first transition's pair has a stored AI
    description (two changes and a question), the second has none, the rest are the engine's «same»."""
    ids: dict[str, Any] = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "versions": [], "transitions": [], "pairs": []}
    x(connection, "INSERT INTO project (project_uid, name) VALUES (:project, 'Объект «Тест»')", **ids)
    x(connection, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, :title)", title=title, **ids)
    for number in range(1, transitions + 2):
        version = str(VersionUid.new())
        ids["versions"].append(version)
        x(connection, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count, "
                      "source_filename) VALUES (:v, :document, :n, 'application/pdf', 1, :sha, 5, :name)",
          v=version, document=ids["document"], n=number, sha=SHA, name=f"v{number}.pdf")
    ids["build"] = new_id("cmx")
    x(connection, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, rules_version, "
                  "algo_version, rows) VALUES (:m, :p, :d, 1, :s, 'v1.2', 'm1', '[]')", m=ids["build"], p=ids["project"], d=ids["document"], s=SHA)
    ids["series"] = new_id("cser")
    command = new_id("cmd")
    x(connection, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) VALUES (:c, "
                  "'start_comparison_series', :k, :f)", c=command, k=new_id("k")[:20], f=SHA)
    x(connection, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, comparison_matrix_id, matrix_edit_no, "
                  "input_sha256, actor_user_uid, actor_label, command_id) VALUES (:s, :p, :d, :m, 0, :sha, :a, 'A', :c)",
      s=ids["series"], p=ids["project"], d=ids["document"], m=ids["build"], sha=SHA, a=ACTOR, c=command)
    page_of: dict[str, str] = {}
    for index in range(1, transitions + 1):
        transition = new_id("ctn")
        ids["transitions"].append(transition)
        summary = {"sheets": 1, "compared": 1, "same": 0, "zones_only": 0, "different": 1, "style_only": 0, "needs_review": 0, "added": 0,
                   "removed": 0, "failed": 0, "ai_dependent": 0}
        x(connection, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, source_version_uid, "
                      "target_version_uid, state, summary, verdict) VALUES (:t, :s, :n, :a, :b, 'completed', CAST(:summary AS jsonb), "
                      "CAST(:verdict AS jsonb))", t=transition, s=ids["series"], n=index, a=ids["versions"][index - 1], b=ids["versions"][index],
          summary=json.dumps(summary), verdict=json.dumps(["different"]))
        stamp = json.dumps({"stamp": {"sheet_number": "1", "sheet_name": "План"}})
        for version in (ids["versions"][index - 1], ids["versions"][index]):
            if version not in page_of:  # one page profile per version: a middle version is the target of one transition and the source of the next
                page_of[version] = new_id("cpr")
                x(connection, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                              "algo_version, status, profile) VALUES (:i, :v, 1, :k, 'p1', 'ready', CAST(:profile AS jsonb))",
                  i=page_of[version], v=version, k=_key(), profile=stamp)
        profiles = (page_of[ids["versions"][index - 1]], page_of[ids["versions"][index]])
        result, pair = new_id("csp"), new_id("ctp")
        x(connection, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, algo_version, status, "
                      "page_a_profile_id, page_b_profile_id) VALUES (:r, :p, :k, 'vc1', 'different', :a, :b)",
          r=result, p=ids["project"], k=_key(), a=profiles[0], b=profiles[1])
        x(connection, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, state, status, "
                      "page_a_profile_id, page_b_profile_id, result_id) VALUES (:x, :t, 1, 'done', 'different', :a, :b, :r)",
          x=pair, t=transition, a=profiles[0], b=profiles[1], r=result)
        ids["pairs"].append({"pair": pair, "result": result, "transition": transition})
        if described and index == 1:
            describe(connection, ids["project"], result)
    return ids


CHANGES = [
    {"change_id": "c1", "object_name": "Кабель ВВГнг(А)-LS", "certainty": "confirmed", "kind": "замена", "place": "щит ЩР-1", "was": "3×2,5",
     "now": "3×4", "was_tier": "from_text", "now_tier": "from_image"},
    {"change_id": "c2", "object_name": "Автомат QF1", "certainty": "confirmed", "was": "16 А", "now": "25 А", "was_tier": "from_text",
     "now_tier": "from_text"},
]


def describe(connection: Connection, project: str, result: str, *, changes: list[dict[str, Any]] | None = None, recorded: bool = False,
             state: str = "done") -> str:
    """A stored AI description of a sheet pair's result (the table's shape; this lane only reads it)."""
    identity = new_id("csd")
    body = {"changes": CHANGES if changes is None else changes, "unresolved": [{"question": "Что за щит?"}]}
    x(connection, "INSERT INTO comparison_sheet_description (comparison_sheet_description_id, project_uid, content_key, result_id, state, "
                  "prompt_version, model_identity, recorded, description) VALUES (:i, :p, :k, :r, :state, 'sc-1', 'claude-opus-5', :rec, "
                  "CAST(:d AS jsonb))", i=identity, p=project, k=_key(), r=result, state=state, rec=recorded, d=json.dumps(body))
    return identity


# -- the recorded answers a handler is asked for -----------------------------------------------------------------------------------

def client_request(doc: Any, label: str, model: str, project: str) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """The request the handler will make for the client kind's transition ``label``, built through the same functions, with the facts and groups
    the check needs: ``(request, transition, registry facts, groups/support, key)``."""
    profile = disciplines.resolve(doc.manifest.get("project_code"))
    units = plan_module.build_units("client", doc, profile, project_uid=project, model=model)
    unit = next(u for u in units if u.transition["label"] == label)
    text, groups, support = client.packet(doc.registry["facts"], label, profile)
    prompt = client.prompt_for(unit.transition, text, client.prompt_text(), f"{unit.key}:{label}", dict(profile))
    request = plan_module.request_for(model, prompt, client.schema(), plan_module.MAX_TOKENS["client"])
    return request, unit.transition, doc.registry["facts"], {"groups": groups, "support": support}, unit.key


def fact_ids(doc: Any, label: str) -> dict[str, str]:
    """The identities of the facts of a transition by a word of their text (``«ВВГнг»`` → ``Ф0002``)."""
    return {f["text"]: f["fact_id"] for f in doc.registry["facts"] if f["transition"] == label}


def good_client_answer(doc: Any, label: str = "V1→V2", **over: Any) -> dict[str, Any]:
    """A client answer the program's check accepts: one point on the cable's fact whose numbers and direction its fields hold."""
    cable = next(f for f in doc.registry["facts"] if f["transition"] == label and "ВВГнг" in f["text"])["fact_id"]
    answer = {
        "transition": label, "change_scope": "Локальные изменения", "lead": "Заменён кабель питания.", "impact": "", "impact_fact_ids": [],
        "questions": [], "not_included": [],
        "points": [{"object": "Кабель ВВГнг(А)-LS", "text": "3×2,5 → 3×4", "fact_ids": [cable], "status": "confirmed",
                    "values": [{"parameter": "сечение", "before": "3×2,5", "after": "3×4", "fact_id": cable}]}],
    }
    answer.update(over)
    return answer


def bad_point(doc: Any, label: str = "V1→V2") -> dict[str, Any]:
    """A point the check must drop: a number no fact holds."""
    breaker = next(f for f in doc.registry["facts"] if f["transition"] == label and "QF1" in f["text"])["fact_id"]
    return {"object": "Автомат QF1", "text": "16 А → 63 А", "fact_ids": [breaker], "status": "confirmed", "values": []}
