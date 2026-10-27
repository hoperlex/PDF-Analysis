"""SECTION-PROMPT-SENTENCE-GUARD-01: the specimens of the three widen lanes, replayed through the real stage.

``SECTION-WIDEN-G1-01``, ``-G2-`` and ``-G3-`` each wrote, for the checks they added to the section
prompts, a text with a hand-authored reply: a **positive** (a written total disagrees with its rows,
a capacity with a count, one load written in two units) and a **negative** (consistent figures and
a trap the prompt says to leave alone), and said they were "not committed as fixtures". They are
filed here, one JSON per specimen, under ``fixtures/recorded/sections_widen/<code>/``: 30 files,
15 positive and 15 negative, in the 12 widened sections (``PB`` has none, ``AI`` was not widened).

Every specimen is replayed through ``run_text_analysis`` with the section's own registered
profile, over a text layer built from its ``pages`` the way the extractor builds one (pages
concatenated with no separator, document-global offsets), and a recording written to a temporary
directory **under the key of the request the current prompt sends**. Nothing is stored keyed to a
prompt, so editing a prompt orphans nothing here; what these tests hold is the other half of the
widening, the part no prompt test reads:

* a positive reply is grounded: its observations all come out of the stage, every quote is found
  at the offsets the stage reports and on the page the reply names, none is unresolved;
* a negative specimen's empty reply is accepted and publishes no observation;
* one altered character in any one quote leaves exactly one unresolved evidence item (and a
  finding whose only quote is altered is refused), so the grounding gate is what keeps a
  misquote out;
* the directory is **not** a recordings directory: the recorded adapter's default search never
  reads it and no file in it is named like a recording key, so it cannot answer a section run.

What this does **not** show: that a model gives these replies, or that it leaves the traps alone.
The replies are hand-authored; the negatives prove only that an empty reply is accepted.

Container-free.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text import STATUS_SUCCEEDED, run_text_analysis
from auditmanager.analysis.text import recorded as recorded_module
from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import RunId

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPECIMENS = REPOSITORY_ROOT / "fixtures" / "recorded" / "sections_widen"
BASE_LAYER = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis" / "inputs" / "ar_baseline_text_layer.json"
MODEL_ID = "claude-opus-5"
REGISTRY = load_text_profile_registry()

#: The one sub-directory that is not a widen section: the omission specimens of `SECTION-CATEGORY-OCR-01`
#: (`R-146ao`), a different format held by `test_section_omission_specimens.py`. The glob below is one level
#: deep and never reaches it.
OMISSION_DIRECTORY = "omission"
#: The filed set, by section: the case names are the keys of the reports' specimen blocks.
EXPECTED = {
    "ps": ("negative", "positive"),
    "pos": ("negative", "positive"),
    "tx": ("negative", "positive"),
    "kj": ("negative", "positive"),
    "km": ("negative", "positive"),
    "ov": ("negative", "positive"),
    "vk": ("negative", "positive"),
    "pt": ("negative", "positive"),
    "eom": ("negative", "positive"),
    "ss": ("capacity_negative", "capacity_positive", "journal_negative", "journal_positive"),
    "itp": ("total_negative", "total_positive", "units_negative", "units_positive"),
    "gp": ("areas_positive", "boundary_negative", "nototal_negative", "shares_positive"),
}
TASK_OF = {
    **dict.fromkeys(("ps", "pos", "tx", "kj"), "SECTION-WIDEN-G1-01"),
    **dict.fromkeys(("km", "ov", "vk", "pt"), "SECTION-WIDEN-G2-01"),
    **dict.fromkeys(("eom", "ss", "itp", "gp"), "SECTION-WIDEN-G3-01"),
}
FILES = sorted(SPECIMENS.glob("*/*.json"))
POSITIVES = [path for path in FILES if json.loads(path.read_text("utf-8"))["expect"] == "finding"]
NEGATIVES = [path for path in FILES if json.loads(path.read_text("utf-8"))["expect"] == "none"]


def _ident(path: Path) -> str:
    return f"{path.parent.name}/{path.stem}"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def _layer(pages: list[str]) -> dict[str, Any]:
    """A text-layer document the way the extractor makes one: no separator between pages."""
    base = json.loads(BASE_LAYER.read_text("utf-8"))
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"char_start": start, "char_end": start + len(text), "page_number": number, "text": text})
        start += len(text)
    return {**{key: value for key, value in base.items() if key != "pages"}, "pages": out, "total_char_count": start}


def replay(code: str, pages: list[str], observations: list[dict[str, Any]], directory: Path) -> Any:
    """The stage's outcome for ``observations`` as the model's one reply over ``pages``."""
    profile = REGISTRY.entries[code.upper()].profile
    document = _layer(pages)
    request = build_request(model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=load_text_layer(document))
    recording = recording_document(
        request=request,
        output_text=json.dumps({"observations": observations}, ensure_ascii=False),
        stop_reason="end_turn",
        input_tokens=3000,
        output_tokens=300,
        latency_ms=9000,
        note="specimen",
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{request.request_sha256}.json").write_text(json.dumps(recording, ensure_ascii=False), "utf-8")
    config = ProviderConfig(
        mode=ProviderMode.RECORDED,
        model_id=MODEL_ID,
        run_cost_ceiling_usd=1.00,
        api_key=None,
        ceiling_is_explicit=True,
    )
    return run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=document,
        adapter=RecordedAdapter(directory),
        profile=profile,
        config=config,
    )


def _evidence(observations: list[dict[str, Any]]) -> int:
    return sum(len(item["evidence"]) for item in observations)


# --- the filed set -------------------------------------------------------------------------


def test_the_filed_set_is_exactly_the_reports_specimens() -> None:
    found: dict[str, tuple[str, ...]] = {}
    for path in sorted(SPECIMENS.iterdir()):
        if path.name == OMISSION_DIRECTORY:
            continue  # `SECTION-CATEGORY-OCR-01`: its own format and its own test, test_section_omission_specimens.py
        assert path.is_dir(), f"{path.name}: only section directories live here"
        found[path.name] = tuple(sorted(item.stem for item in path.iterdir()))
        assert all(item.suffix == ".json" for item in path.iterdir()), path.name
    assert found == EXPECTED
    assert len(FILES) == 30 and len(POSITIVES) == 15 and len(NEGATIVES) == 15
    assert sorted(path.parent.name for path in POSITIVES) == sorted(
        code for code, cases in EXPECTED.items() for case in cases if case.endswith("positive")
    )


@pytest.mark.parametrize("path", FILES, ids=[_ident(path) for path in FILES])
def test_each_specimen_is_labelled_synthetic_and_shaped_as_declared(path: Path) -> None:
    document = _load(path)
    code = path.parent.name
    assert set(document) == {"format", "section_code", "case", "expect", "origin", "pages", "observations"}
    assert document["format"] == "section-widen-specimen/1"
    assert document["section_code"] == code.upper() and document["case"] == path.stem
    assert document["expect"] == ("finding" if path.stem.endswith("positive") else "none")
    origin = document["origin"]
    assert origin["kind"] == "synthetic" and origin["task_id"] == TASK_OF[code]
    assert origin["source_report"] == f"docs/program/{TASK_OF[code]}.md"
    assert "No model produced this reply" in origin["statement"] and "Not field evidence" in origin["statement"]
    assert not {"provider_mode", "mode", "request_sha256"} & (set(document) | set(origin))
    assert not re.fullmatch(r"[0-9a-f]{64}", path.stem), "named like a recording key"
    pages = document["pages"]
    assert pages and all(isinstance(page, str) and page for page in pages)
    for observation in document["observations"]:
        assert set(observation) == {"category", "finding_text", "recommendation_text", "evidence"}
        assert observation["category"] == "internal_contradiction"
        assert observation["finding_text"].startswith("Синтетический ответ (")
        assert "не результат вызова модели" in observation["finding_text"]
        assert len(observation["evidence"]) >= 1
        for item in observation["evidence"]:
            assert set(item) == {"page_number", "quote"}
            assert 1 <= item["page_number"] <= len(pages)
    if document["expect"] == "finding":
        assert document["observations"], "a positive specimen holds a reply with a finding"
    else:
        assert document["observations"] == [], "a negative specimen's reply is empty"


# --- replay through the real stage ---------------------------------------------------------


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
def test_a_positive_specimen_replays_to_grounded_findings_with_every_quote_resolved(
    path: Path, tmp_path: Path
) -> None:
    document = _load(path)
    reply = document["observations"]
    outcome = replay(path.parent.name, document["pages"], reply, tmp_path)
    assert outcome.status == STATUS_SUCCEEDED and outcome.error is None
    metrics = outcome.metrics
    assert metrics["observations_proposed"] == len(reply)
    assert metrics["observations_emitted"] == len(reply)
    assert metrics["observations_dropped_unresolved"] == 0
    assert metrics["evidence_unresolved"] == 0
    assert metrics["evidence_emitted"] == _evidence(reply)
    assert metrics["proposals_malformed"] == 0

    layer_text = "".join(document["pages"])  # the document-global sequence the offsets index
    published = outcome.artifact["observations"]
    # The two places that disagree, at least: the total and a row, a capacity and a count, two units.
    assert max(len(item["evidence"]) for item in reply) >= 2
    assert [item["finding_text"] for item in published] == [item["finding_text"] for item in reply]
    for emitted, wanted in zip(published, reply, strict=True):
        assert emitted["category"] == "internal_contradiction"
        assert len(emitted["evidence"]) == len(wanted["evidence"])
        for found, said in zip(emitted["evidence"], wanted["evidence"], strict=True):
            assert found["quote"] == said["quote"] and found["page_number"] == said["page_number"]
            assert layer_text[found["char_start"] : found["char_end"]] == found["quote"]
            page = document["pages"][found["page_number"] - 1]
            assert found["quote"] in page, "the quote lies on the page the reply names"


@pytest.mark.parametrize("path", NEGATIVES, ids=[_ident(path) for path in NEGATIVES])
def test_a_negative_specimen_replays_to_no_observation(path: Path, tmp_path: Path) -> None:
    document = _load(path)
    outcome = replay(path.parent.name, document["pages"], document["observations"], tmp_path)
    assert outcome.status == STATUS_SUCCEEDED and outcome.error is None
    assert outcome.metrics["observations_proposed"] == 0
    assert outcome.metrics["observations_emitted"] == 0
    assert outcome.metrics["evidence_emitted"] == 0 and outcome.metrics["evidence_unresolved"] == 0
    assert outcome.artifact["observations"] == []


def _misquoted(observations: list[dict[str, Any]], which: int, item: int, layer_text: str) -> list[dict[str, Any]]:
    changed = json.loads(json.dumps(observations))
    quote = changed[which]["evidence"][item]["quote"]
    middle = len(quote) // 2
    altered = quote[:middle] + ("#" if quote[middle] != "#" else "%") + quote[middle + 1 :]
    assert altered not in layer_text, "the altered quote must not occur in the text by chance"
    changed[which]["evidence"][item]["quote"] = altered
    return changed


@pytest.mark.parametrize("path", POSITIVES, ids=[_ident(path) for path in POSITIVES])
def test_one_changed_character_in_any_quote_leaves_one_unresolved_evidence_item(
    path: Path, tmp_path: Path
) -> None:
    document = _load(path)
    reply = document["observations"]
    layer_text = "".join(document["pages"])
    cases = 0
    for which, observation in enumerate(reply):
        for item in range(len(observation["evidence"])):
            outcome = replay(
                path.parent.name,
                document["pages"],
                _misquoted(reply, which, item, layer_text),
                tmp_path / f"{which}-{item}",
            )
            metrics = outcome.metrics
            assert outcome.status == STATUS_SUCCEEDED
            assert metrics["evidence_unresolved"] == 1, (which, item)
            assert metrics["evidence_emitted"] == _evidence(reply) - 1, (which, item)
            alone = len(observation["evidence"]) == 1
            # A finding with other quotes left stays, one evidence short; a finding whose only
            # quote was altered has nothing to stand on and is refused by the grounding gate.
            assert metrics["observations_emitted"] == len(reply) - (1 if alone else 0), (which, item)
            assert metrics["observations_dropped_unresolved"] == (1 if alone else 0), (which, item)
            cases += 1
    assert cases == _evidence(reply)


# --- the directory is not a recordings directory --------------------------------------------


def test_the_recorded_adapters_default_search_never_reads_the_specimens() -> None:
    searched = recorded_module.default_recording_dirs()
    assert SPECIMENS not in searched and not any(SPECIMENS in directory.parents for directory in searched)
    assert {directory.name for directory in searched} >= {"text_analysis", "ps", "itp", "pb"}
    assert SPECIMENS.parent == recorded_module.default_section_recordings_root().parent
    assert SPECIMENS.name not in {path.name for path in recorded_module.default_section_recordings_root().iterdir()}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_a_specimen_text_is_not_answered_by_the_default_recordings(code: str) -> None:
    """Over a specimen's text the default adapter finds no recording: the specimen is no answer to a run."""
    path = next(path for path in POSITIVES if path.parent.name == code)
    document = _load(path)
    profile = REGISTRY.entries[code.upper()].profile
    request = build_request(
        model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=load_text_layer(_layer(document["pages"]))
    )
    with pytest.raises(DomainError):
        RecordedAdapter().complete(request)
