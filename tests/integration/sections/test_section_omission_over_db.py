"""`SECTION-CATEGORY-OCR-01` (`R-146ao`): an omission is published as a `documentation` finding, end to end, on the lane stack.

The only test of the lane that needs PostgreSQL and MinIO, and it is skipped (with its reason) on a host
with neither a ``DATABASE_URL`` nor a ``.env``: ``tests/integration/sections`` is otherwise container-free.
It reuses the run-executor harness of ``tests/integration/runs`` by path (the way that suite's conftest
does) so that the run is the real one: a version classified АИ, a run pinned to the АИ profile, the real
executor, the real evidence gate and the real publication into the tables whose CHECKs name the categories.

What it shows, for one hand-authored reply over the committed AR baseline text:

* the omission is published, as one finding whose category is `documentation` (the value `ck_finding_category`
  has allowed since migration `0022`: no contract and no migration moved), with two evidence rows, the naming
  quote then the heading of the range, each at offsets that slice back to the quote in the saved text layer;
* the finding text is the model's sentence followed by the sentence the stage wrote about what code verified;
* the same reply with the term added to the range's page by the text (shown at stage level in the unit tests)
  is not what this test varies; here the database path is the subject: the stage metrics persisted with the
  run carry the omission counters.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import RecordedAdapter
from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.omission import note_for
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recorded import recording_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.findings import published_findings
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.sections.public import classify_document_version

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_LAYER = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis" / "inputs" / "ar_baseline_text_layer.json"
_HARNESS_PATH = REPOSITORY_ROOT / "tests" / "integration" / "runs" / "harness.py"


def _stack_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL")) or (REPOSITORY_ROOT / ".env").is_file()


pytestmark = pytest.mark.skipif(
    not _stack_configured(),
    reason="needs the lane stack (PostgreSQL and MinIO): set DATABASE_URL or provide .env; "
    "runs with tests/integration/runs",
)

if _stack_configured():
    _spec = importlib.util.spec_from_file_location("sx_run_harness", _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules["sx_run_harness"] = harness  # a dataclass resolves its annotations through sys.modules
    _spec.loader.exec_module(harness)
    # Bound at module level, as the runs conftest binds them, so pytest registers them for this module.
    _no_network = harness._no_network
    engine = harness.engine
    blob_store = harness.blob_store
    session = harness.session
    provider_config = harness.provider_config
    seeded = harness.seeded
    new_key = harness.new_key

REGISTRY = load_text_profile_registry()
AI = REGISTRY.entries["AI"]
NAMING = "Класс функциональной пожарной опасности — Ф1.3."
HEADING = "7. ВЕДОМОСТЬ ЗАПОЛНЕНИЯ ПРОЁМОВ И ОТДЕЛКИ"
TERM = "Ф1.3"


def _reply() -> dict[str, Any]:
    return {
        "category": "documentation",
        "finding_text": (
            "Синтетический ответ (АИ), не результат вызова модели: класс функциональной пожарной "
            "опасности Ф1.3 назван в общих данных на странице 2 и не найден в ведомости заполнения проёмов."
        ),
        "recommendation_text": "Сверить ведомость заполнения проёмов и отделки с общими данными.",
        "evidence": [{"page_number": 2, "quote": NAMING}],
        "omission": {
            "term": TERM, "first_page": 8, "last_page": 8,
            "heading": {"page_number": 8, "quote": HEADING},
        },
    }


def _write_recording(directory: Path, model_id: str) -> None:
    layer = load_text_layer(json.loads(BASELINE_LAYER.read_text(encoding="utf-8")))
    request = build_request(model_id=model_id, bundle=AI.profile.prompt_bundle, text_layer=layer)
    document = recording_document(
        request=request,
        output_text=json.dumps({"observations": [_reply()]}, ensure_ascii=False),
        stop_reason="end_turn", input_tokens=2310, output_tokens=420, latency_ms=9100,
        note="Synthetic omission reply over the AR baseline text layer, authored by hand (SECTION-CATEGORY-OCR-01).",
    )
    (directory / f"{request.request_sha256}.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )


def test_an_omission_is_published_as_a_documentation_finding_with_both_places(
    session: Session, seeded, blob_store, provider_config, new_key, tmp_path: Path
) -> None:
    from am_test_accounts import provisioned_record

    layer = json.loads(BASELINE_LAYER.read_text(encoding="utf-8"))
    pages = {page["page_number"]: page["text"] for page in layer["pages"]}
    assert NAMING in pages[2] and HEADING in pages[8] and TERM not in pages[8], "the premise: a pair over the baseline"

    classify_document_version(
        session, project_uid=seeded.project_uid, document_uid=seeded.document_uid,
        version_uid=seeded.version_uid, project_stage="P", section_code="AI",
        actor_uid=str(provisioned_record("section-omission-over-db").user_uid), actor_roles=frozenset({"expert"}),
    )
    run_id = start_audit_run(
        session, version_uid=seeded.version_uid, provider_mode="recorded",
        idempotency_key=new_key("section-omission-over-db"), section_profiles=REGISTRY.section_profiles(),
    ).run_id
    _write_recording(tmp_path, provider_config.model_id)

    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=RecordedAdapter(tmp_path),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    assert result.terminal_state == "published", (dict(result.stage_statuses), result.degradation_set)

    (finding,) = published_findings(session, run_id)
    assert finding.category == "documentation"
    sentence = note_for(TERM, 8, 8)
    assert finding.finding_text == f"{_reply()['finding_text']} {sentence}"
    assert (finding.analysis_profile_id, finding.prompt_bundle_id) == (AI.analysis_profile_id, AI.prompt_bundle_id)
    assert finding.provider_mode == "recorded"

    evidence = session.execute(
        text(
            "SELECT e.page_number, e.quote, e.char_start, e.char_end "
            "FROM finding_evidence e JOIN finding_observation o "
            "ON o.finding_observation_id = e.finding_observation_id "
            "WHERE o.finding_observation_id = :o ORDER BY e.evidence_ordinal"
        ),
        {"o": finding.finding_observation_id},
    ).all()
    document_text = "".join(pages[number] for number in sorted(pages))
    assert [(row.page_number, row.quote) for row in evidence] == [(2, NAMING), (8, HEADING)]
    for row in evidence:
        assert document_text[row.char_start : row.char_end] == row.quote

    metrics = session.execute(
        text("SELECT metrics FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'"),
        {"r": run_id},
    ).scalar_one()
    assert metrics["omissions_proposed"] == 1 and metrics["omissions_published"] == 1
    assert metrics["omissions_dropped"] == 0 and metrics["evidence_unresolved"] == 0
