#!/usr/bin/env python3
"""Rebuild the ``text_analysis`` recorded fixtures.

    PYTHONPATH=src .venv/bin/python fixtures/recorded/text_analysis/build_fixtures.py
    PYTHONPATH=src .venv/bin/python fixtures/recorded/text_analysis/build_fixtures.py --check

``--check`` rebuilds into memory and reports any file that would change, so a prompt
edit that silently invalidates every recording shows up as a failure rather than as a
test that quietly stops replaying.

Two things this script establishes, both of which matter:

* **The text layer is derived from the real corpus PDF** with the extractor
  ``docs/program/P02_LOCK.json`` pins, then NFC-normalized once. It stands in for
  ``B2``'s ``prepared.text_layer`` until ``B2`` publishes one, and it is built to the
  section 4.3 invariants so the substitution is honest: contiguous gapless pages, no
  separator between them, spans measured in code points.
* **A recording is keyed by the request checksum**, so every key below is computed
  from the bundle and the document rather than chosen. Editing the prompt changes all
  of them.

The token counts in these recordings are **authored, not measured**: no live call was
made when they were written. They are plausible for this corpus at the pinned rates
and they are what the cost meter charges in tests. The first live run should replace
them with measured usage; nothing else in the fixture depends on their exact values.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from auditmanager.analysis.text.adapter import build_request  # noqa: E402
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE  # noqa: E402
from auditmanager.analysis.text.recorded import recording_document  # noqa: E402
from auditmanager.analysis.text.textlayer import load_text_layer  # noqa: E402

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
VARIANTS = HERE / "variants"

CORPUS_PDF = _REPO_ROOT / "fixtures/synthetic/ar/ar_baseline.pdf"
TEXT_LAYER_PATH = INPUTS / "ar_baseline_text_layer.json"

MODEL_ID = "claude-opus-5"

#: A stand-in version identity for the fixture text layer. ``B2`` allocates the real
#: one; this is here so the artifact shape is complete, and nothing keys on it.
FIXTURE_VERSION_UID = "ver_01M25P3TH0X4C5ZR8G4M2Q7WJH"


def build_text_layer_document() -> dict[str, Any]:
    """Extract the corpus with the pinned extractor and lay it out per section 4.3."""
    import pdfplumber  # imported here so --check works without a PDF read at import

    pages: list[dict[str, Any]] = []
    cursor = 0
    with pdfplumber.open(CORPUS_PDF) as pdf:
        for ordinal, page in enumerate(pdf.pages, start=1):
            # The one declared normalization, applied once, here. No later stage
            # normalizes again - section 4.3 makes that a seam, not a preference.
            text = unicodedata.normalize("NFC", page.extract_text() or "")
            pages.append(
                {
                    "page_number": ordinal,
                    "char_start": cursor,
                    "char_end": cursor + len(text),
                    "text": text,
                }
            )
            cursor += len(text)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": FIXTURE_VERSION_UID,
        "extractor": {"name": "pdfplumber", "version": "0.11.10", "options_sha256": ""},
        "normalization": {
            "id": "nfc_v1",
            "description": (
                "Unicode NFC. No case folding, no whitespace collapsing, no punctuation "
                "substitution and no line-ending rewriting beyond the extractor's own output."
            ),
        },
        "total_char_count": cursor,
        "pages": pages,
    }


OBSERVATIONS_COMPLETE: list[dict[str, Any]] = [
    {
        "category": "internal_contradiction",
        "finding_text": (
            "Степень огнестойкости одного и того же здания указана по-разному: II в разделе "
            "общих данных и III в разделе противопожарных мероприятий."
        ),
        "recommendation_text": (
            "Согласовать степень огнестойкости здания между разделом общих данных и разделом "
            "противопожарных мероприятий, оставив одно значение."
        ),
        "evidence": [
            {"page_number": 2, "quote": "Степень огнестойкости здания — II."},
            {"page_number": 6, "quote": "Степень огнестойкости здания — III."},
        ],
    },
    {
        "category": "internal_contradiction",
        "finding_text": (
            "Количество эвакуационных выходов из надземной части здания указано как два в "
            "объёмно-планировочных решениях и как три в разделе эвакуационных путей и выходов."
        ),
        "recommendation_text": (
            "Привести количество эвакуационных выходов из надземной части здания к одному "
            "значению в обоих разделах."
        ),
        "evidence": [
            {
                "page_number": 3,
                "quote": "Из надземной части здания предусмотрено два эвакуационных выхода.",
            },
            {
                "page_number": 7,
                "quote": "Из надземной части здания предусмотрено три эвакуационных выхода.",
            },
        ],
    },
    {
        "category": "explicit_placeholder",
        "finding_text": (
            "Тип заполнения оконных проёмов не определён: вместо проектного решения оставлено "
            "буквальное указание «уточнить»."
        ),
        "recommendation_text": (
            "Определить тип заполнения оконных проёмов и внести его в ведомость заполнения "
            "проёмов."
        ),
        "evidence": [
            {"page_number": 8, "quote": "Тип заполнения оконных проёмов — уточнить."},
        ],
    },
]

#: One observation whose single quotation is nowhere in the document, and one whose
#: two quotations are half real and half invented. Neither is a plausible model reply
#: on this corpus; both are here because the grounding path has to be provable.
OBSERVATIONS_UNGROUNDED: list[dict[str, Any]] = [
    {
        "category": "internal_contradiction",
        "finding_text": (
            "Класс энергетической эффективности здания указан по-разному в двух разделах."
        ),
        "recommendation_text": "Согласовать класс энергетической эффективности здания.",
        "evidence": [
            {"page_number": 2, "quote": "Класс энергетической эффективности здания — A."},
        ],
    },
    {
        "category": "internal_contradiction",
        "finding_text": (
            "Степень огнестойкости одного и того же здания указана по-разному в разных разделах."
        ),
        "recommendation_text": "Согласовать степень огнестойкости здания между разделами.",
        "evidence": [
            {"page_number": 2, "quote": "Степень огнестойкости здания — II."},
            {"page_number": 6, "quote": "Степень огнестойкости здания — IV."},
        ],
    },
]


def _payload(observations: list[dict[str, Any]]) -> str:
    return json.dumps({"observations": observations}, ensure_ascii=False)


def _truncated_payload() -> str:
    """The complete reply, cut inside the third observation.

    Cutting mid-element is the point: the salvage path must keep the two elements that
    finished and discard the one that did not, rather than repair the JSON.
    """
    full = _payload(OBSERVATIONS_COMPLETE)
    third = full.index('{"category": "explicit_placeholder"')
    return full[: third + 120]


def plan() -> list[tuple[Path, dict[str, Any]]]:
    text_layer_document = build_text_layer_document()
    text_layer = load_text_layer(text_layer_document)
    request = build_request(
        model_id=MODEL_ID, bundle=AR_TEXT_PROFILE.prompt_bundle, text_layer=text_layer
    )
    key = request.request_sha256

    entries: list[tuple[Path, dict[str, Any]]] = [
        (TEXT_LAYER_PATH, text_layer_document),
        (
            HERE / f"{key}.json",
            recording_document(
                request=request,
                output_text=_payload(OBSERVATIONS_COMPLETE),
                stop_reason="end_turn",
                input_tokens=2180,
                output_tokens=940,
                latency_ms=11940,
                note=(
                    "AR baseline, complete reply. Finds both seeded cross-page "
                    "contradictions and the explicit placeholder, and flags none of the "
                    "six near-miss controls. Token counts are authored, not measured: no "
                    "live call was made when this was written."
                ),
            ),
        ),
        (
            VARIANTS / "truncated" / f"{key}.json",
            recording_document(
                request=request,
                output_text=_truncated_payload(),
                stop_reason="max_tokens",
                input_tokens=2180,
                output_tokens=16000,
                latency_ms=42310,
                note=(
                    "The same reply cut off at the output ceiling inside the third "
                    "observation. Exercises the partial mapping: usable observations over "
                    "a strict subset of pages, never succeeded."
                ),
            ),
        ),
        (
            VARIANTS / "over_budget" / f"{key}.json",
            recording_document(
                request=request,
                output_text=_payload(OBSERVATIONS_COMPLETE),
                stop_reason="end_turn",
                input_tokens=400_000,
                output_tokens=60_000,
                latency_ms=98_400,
                note=(
                    "Deliberately expensive usage - the figures of a far larger document - "
                    "so the OD-03 per-run ceiling fires on measured cost against the "
                    "default ceiling. The reply itself is the complete one."
                ),
            ),
        ),
        (
            VARIANTS / "ungrounded_quotation" / f"{key}.json",
            recording_document(
                request=request,
                output_text=_payload(OBSERVATIONS_UNGROUNDED),
                stop_reason="end_turn",
                input_tokens=2180,
                output_tokens=610,
                latency_ms=10220,
                note=(
                    "Quotations that are not in the text layer. One observation is wholly "
                    "invented; the other pairs a real quotation with an invented one. "
                    "Exercises what is emitted and what is dropped."
                ),
            ),
        ),
    ]
    return entries


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    drift: list[str] = []
    for path, document in plan():
        rendered = render(document)
        relative = path.relative_to(_REPO_ROOT)
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != rendered:
                drift.append(str(relative))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {relative}")

    if args.check:
        if drift:
            print("fixtures differ from what this script would write:", file=sys.stderr)
            for entry in drift:
                print(f"  {entry}", file=sys.stderr)
            return 1
        print("fixtures match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
