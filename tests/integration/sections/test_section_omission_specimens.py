"""SECTION-CATEGORY-OCR-01 (`R-146ao`): the omission specimens, replayed through the real stage.

``fixtures/recorded/sections_widen/omission/<code>/<case>.json`` holds, for each of the five sections that
may report a same-document omission under the existing category ``documentation`` (AI TX EOM SS ITP), a
**positive** (a term is named on a scheme, plan or explication and does not occur in the schedule or
specification: the reply is published as a pair of places) and a **negative** (a reply the model might give
that the stage's absence check must refuse: the term is in the schedule in another case, with another dash,
wrapped over a line, on the second page of the range; or a page of the range has no text). Ten files.

Every specimen is replayed through ``run_text_analysis`` with the section's own registered profile over a
text layer built from its ``pages`` the way the extractor builds one, with a recording written to a temporary
directory under the key of the request the current prompt sends. What these tests hold:

* a positive reply is published as exactly one ``documentation`` observation whose evidence is the naming
  quote followed by the heading quote, both resolved at the offsets the stage reports, and whose text ends
  with the sentence the stage writes about what code verified;
* a negative reply publishes nothing and counts one drop under the reason the specimen declares;
* the guards can fail: the term added to the range turns every positive into a drop; one altered character in
  the naming quote or in the heading quote drops the pair; the same reply to a section that does not declare
  the category is malformed and nothing is published;
* the directory is not a recordings directory.

What this does **not** show: that a model gives these replies, or how often it would. Hand-authored.
Container-free.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text import STATUS_SUCCEEDED, run_text_analysis
from auditmanager.analysis.text import recorded as recorded_module
from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.omission import OMISSION_REASONS, note_for
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.identity import RunId

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPECIMENS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections_widen" / "omission"
BASE_LAYER = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis" / "inputs" / "ar_baseline_text_layer.json"
MODEL_ID = "claude-opus-5"
REGISTRY = load_text_profile_registry()
TASK = "SECTION-CATEGORY-OCR-01"

EXPECTED = {
    "ai": ("dash_negative", "positive"),
    "tx": ("positive", "wrapped_negative"),
    "eom": ("case_negative", "positive"),
    "ss": ("positive", "second_page_negative"),
    "itp": ("positive", "scan_negative"),
}
FILES = sorted(SPECIMENS.glob("*/*.json"))
POSITIVES = [path for path in FILES if json.loads(path.read_text("utf-8"))["expect"] == "finding"]
NEGATIVES = [path for path in FILES if json.loads(path.read_text("utf-8"))["expect"] == "dropped"]


def _ident(path: Path) -> str:
    return f"{path.parent.name}/{path.stem}"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def _layer(pages: list[str]) -> dict[str, Any]:
    base = json.loads(BASE_LAYER.read_text("utf-8"))
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"char_start": start, "char_end": start + len(text), "page_number": number, "text": text})
        start += len(text)
    return {**{key: value for key, value in base.items() if key != "pages"}, "pages": out, "total_char_count": start}


def replay(code: str, pages: list[str], observations: list[dict[str, Any]], directory: Path) -> Any:
    profile = REGISTRY.entries[code.upper()].profile
    document = _layer(pages)
    request = build_request(model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=load_text_layer(document))
    recording = recording_document(
        request=request,
        output_text=json.dumps({"observations": observations}, ensure_ascii=False),
        stop_reason="end_turn", input_tokens=3000, output_tokens=300, latency_ms=9000, note="specimen",
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{request.request_sha256}.json").write_text(json.dumps(recording, ensure_ascii=False), "utf-8")
    config = ProviderConfig(
        mode=ProviderMode.RECORDED, model_id=MODEL_ID, run_cost_ceiling_usd=1.00, api_key=None,
        ceiling_is_explicit=True,
    )
    return run_text_analysis(
        run_id=RunId.new(), text_layer_document=document, adapter=RecordedAdapter(directory),
        profile=profile, config=config,
    )


# --- the filed set -------------------------------------------------------------------------


def test_the_filed_set_is_exactly_five_sections_with_one_positive_and_one_negative() -> None:
    found = {path.name: tuple(sorted(item.stem for item in path.iterdir())) for path in sorted(SPECIMENS.iterdir())}
    assert found == EXPECTED
    assert len(FILES) == 10 and len(POSITIVES) == 5 and len(NEGATIVES) == 5
    assert {path.parent.name for path in POSITIVES} == set(EXPECTED) == {path.parent.name for path in NEGATIVES}


@pytest.mark.parametrize("path", FILES, ids=[_ident(path) for path in FILES])
def test_each_specimen_is_labelled_synthetic_and_shaped_as_declared(path: Path) -> None:
    document = _load(path)
    code = path.parent.name
    assert set(document) == {
        "format", "section_code", "case", "expect", "expect_reason", "origin", "pages", "observations",
    }
    assert document["format"] == "section-omission-specimen/1"
    assert document["section_code"] == code.upper() and document["case"] == path.stem
    assert document["expect"] == ("finding" if path.stem == "positive" else "dropped")
    assert (document["expect_reason"] is None) == (document["expect"] == "finding")
    if document["expect_reason"] is not None:
        assert document["expect_reason"] in OMISSION_REASONS
    origin = document["origin"]
    assert origin["kind"] == "synthetic" and origin["task_id"] == TASK
    assert origin["source_report"] == f"docs/program/{TASK}.md"
    assert "No model produced this reply" in origin["statement"] and "Not field evidence" in origin["statement"]
    assert all(isinstance(page, str) and page for page in document["pages"])
    (observation,) = document["observations"]
    assert set(observation) == {"category", "finding_text", "recommendation_text", "evidence", "omission"}
    assert observation["category"] == "documentation"
    assert observation["finding_text"].startswith("Синтетический ответ (")
    assert "не результат вызова модели" in observation["finding_text"]
    claim = observation["omission"]
    assert set(claim) == {"term", "first_page", "last_page", "heading"}
    assert set(claim["heading"]) == {"page_number", "quote"}
    for item in [*observation["evidence"], claim["heading"]]:
        assert 1 <= item["page_number"] <= len(document["pages"])


# --- the positive: a pair of places --------------------------------------------------------


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
def test_a_positive_is_published_as_a_pair_of_places_with_the_programs_sentence(
    path: Path, tmp_path: Path
) -> None:
    document = _load(path)
    (reply,) = document["observations"]
    claim = reply["omission"]
    outcome = replay(path.parent.name, document["pages"], document["observations"], tmp_path)
    assert outcome.status == STATUS_SUCCEEDED and outcome.error is None
    metrics = outcome.metrics
    assert metrics["observations_proposed"] == 1 and metrics["observations_emitted"] == 1
    assert metrics["omissions_proposed"] == 1 and metrics["omissions_published"] == 1
    assert metrics["omissions_dropped"] == 0
    assert all(metrics[f"omissions_dropped_{reason}"] == 0 for reason in OMISSION_REASONS)
    assert metrics["evidence_unresolved"] == 0 and metrics["proposals_malformed"] == 0
    assert metrics["evidence_emitted"] == len(reply["evidence"]) + 1

    (published,) = outcome.artifact["observations"]
    assert published["category"] == "documentation"
    assert published["recommendation_text"] == reply["recommendation_text"]
    sentence = note_for(claim["term"], claim["first_page"], claim["last_page"])
    assert published["finding_text"] == f"{reply['finding_text']} {sentence}"
    assert "не найдена в текстовом слое" in sentence and "другие написания не проверялись" in sentence

    layer_text = "".join(document["pages"])
    wanted = [*reply["evidence"], claim["heading"]]
    assert [(item["page_number"], item["quote"]) for item in published["evidence"]] == [
        (item["page_number"], item["quote"]) for item in wanted
    ], "the naming place first, the heading of the range last"
    for found in published["evidence"]:
        assert layer_text[found["char_start"] : found["char_end"]] == found["quote"]
        assert found["quote"] in document["pages"][found["page_number"] - 1]


# --- the negative: the check refuses it, for the reason the specimen names ------------------


@pytest.mark.parametrize("path", NEGATIVES, ids=[_ident(path) for path in NEGATIVES])
def test_a_negative_is_dropped_with_its_reason_and_nothing_is_published(path: Path, tmp_path: Path) -> None:
    document = _load(path)
    outcome = replay(path.parent.name, document["pages"], document["observations"], tmp_path)
    assert outcome.status == STATUS_SUCCEEDED and outcome.error is None
    metrics = outcome.metrics
    assert outcome.artifact["observations"] == []
    assert metrics["observations_proposed"] == 1 and metrics["observations_emitted"] == 0
    assert metrics["omissions_proposed"] == 1 and metrics["omissions_published"] == 0
    assert metrics["omissions_dropped"] == 1
    for reason in OMISSION_REASONS:
        assert metrics[f"omissions_dropped_{reason}"] == (1 if reason == document["expect_reason"] else 0), reason
    assert metrics["evidence_emitted"] == 0 and metrics["proposals_malformed"] == 0


# --- the guards can fail --------------------------------------------------------------------


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
def test_adding_the_term_to_the_range_turns_a_positive_into_a_drop(path: Path, tmp_path: Path) -> None:
    """The absence check is what stands between the model's claim and the finding."""
    document = _load(path)
    (reply,) = document["observations"]
    claim = reply["omission"]
    pages = list(document["pages"])
    index = claim["last_page"] - 1
    pages[index] = pages[index] + f"\nЕщё одна запись: {claim['term']}, 1 шт."
    outcome = replay(path.parent.name, pages, document["observations"], tmp_path)
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_dropped_term_present_in_range"] == 1
    assert outcome.metrics["omissions_published"] == 0


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
@pytest.mark.parametrize("which", ["naming", "heading"])
def test_one_altered_character_in_either_quote_drops_the_pair(path: Path, which: str, tmp_path: Path) -> None:
    document = _load(path)
    changed = copy.deepcopy(document["observations"])
    target = changed[0]["evidence"][0] if which == "naming" else changed[0]["omission"]["heading"]
    quote = target["quote"]
    middle = len(quote) // 2
    target["quote"] = quote[:middle] + ("#" if quote[middle] != "#" else "%") + quote[middle + 1 :]
    assert target["quote"] not in "".join(document["pages"])
    outcome = replay(path.parent.name, document["pages"], changed, tmp_path)
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_dropped_evidence_unresolved"] == 1
    assert outcome.metrics["omissions_published"] == 0 and outcome.metrics["evidence_unresolved"] == 1


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
def test_a_section_that_does_not_declare_the_category_refuses_the_same_reply(path: Path, tmp_path: Path) -> None:
    """KJ declares two categories: `documentation` from it is malformed, counted, never published."""
    document = _load(path)
    outcome = replay("kj", document["pages"], document["observations"], tmp_path)
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["proposals_malformed"] == 1 and outcome.metrics["observations_proposed"] == 0
    assert not any(key.startswith("omissions_") for key in outcome.metrics), "its metrics do not move"


def test_an_omission_object_on_another_category_is_malformed(tmp_path: Path) -> None:
    document = _load(SPECIMENS / "ai" / "positive.json")
    changed = copy.deepcopy(document["observations"])
    changed[0]["category"] = "internal_contradiction"
    outcome = replay("ai", document["pages"], changed, tmp_path)
    assert outcome.metrics["proposals_malformed"] == 1 and outcome.artifact["observations"] == []


def test_documentation_without_a_claim_is_malformed(tmp_path: Path) -> None:
    document = _load(SPECIMENS / "ai" / "positive.json")
    changed = copy.deepcopy(document["observations"])
    del changed[0]["omission"]
    outcome = replay("ai", document["pages"], changed, tmp_path)
    assert outcome.metrics["proposals_malformed"] == 1 and outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_proposed"] == 0


# --- the directory is not a recordings directory ---------------------------------------------


def test_the_recorded_adapters_default_search_never_reads_the_omission_specimens() -> None:
    searched = recorded_module.default_recording_dirs()
    assert not any(SPECIMENS in directory.parents or directory == SPECIMENS for directory in searched)
    assert SPECIMENS.parent.name == "sections_widen"
    for path in FILES:
        document = _load(path)
        profile = REGISTRY.entries[path.parent.name.upper()].profile
        request = build_request(
            model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=load_text_layer(_layer(document["pages"]))
        )
        with pytest.raises(Exception):
            RecordedAdapter().complete(request)
