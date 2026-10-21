#!/usr/bin/env python3
"""Rebuild the SYNTHETIC recorded model response for the AR specification set (`SPEC-TABLE-RECORDING-01`).

    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/ar_specification/build_fixtures.py
    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/ar_specification/build_fixtures.py --check

``--check`` rebuilds into memory and reports a file that would change or that no longer
belongs, so an edit of the AR prompt bundle, of the PDF or of the extractor that orphans the
recording fails loudly instead of as a run that cannot find its answer.

What this file is, and what it is not
-------------------------------------
It answers one request: the canonical AR profile's prompt bundle over the text layer that
``analysis.stages.extraction`` (pdfplumber) produces from the committed
``fixtures/synthetic/ar_specification/ar_specification.pdf`` -- the document a project holds
when the expert uploads ``ar_specification.zip``. The key is ``request_sha256`` of that exact
body, computed here, never chosen.

The reply is **authored by hand**. No model produced it and no provider call was made; the
file says so in its ``origin`` block and the finding text opens with «Синтетический ответ».
It exists so that a version of this set, classified AR, runs end to end in recorded mode and
publishes, which is what reaches the specification table and an optimisation pass with
proposals. It is not field evidence for any profile. ``usage`` and ``latency_ms`` are authored,
not measured, and nothing prices them for real.

The file sits in a directory of its own under ``fixtures/recorded/sections/`` because that is
where ``RecordedAdapter()`` -- what the composition root serves in recorded mode -- searches
besides the canonical directory. It is **not** a section recording: the profile is AR's, the
canonical one.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from auditmanager.analysis.stages.extraction import extract_document  # noqa: E402
from auditmanager.analysis.text.adapter import build_request  # noqa: E402
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE  # noqa: E402
from auditmanager.analysis.text.recorded import recording_document  # noqa: E402
from auditmanager.analysis.text.textlayer import load_text_layer  # noqa: E402

HERE = Path(__file__).resolve().parent
PDF_PATH = _REPO_ROOT / "fixtures/synthetic/ar_specification/ar_specification.pdf"
MODEL_ID = "claude-opus-5"
TASK_ID = "SPEC-TABLE-RECORDING-01"
#: A stand-in version identity for the text layer built here; nothing keys on it.
FIXTURE_VERSION_UID = "ver_01M25P3TH0X4C5ZR8G4M2Q7WJH"
_KEY_FILE = re.compile(r"[0-9a-f]{64}\.json")

_STATEMENT = (
    "Synthetic: authored by hand for SPEC-TABLE-RECORDING-01 so that the AR specification set "
    "runs end to end in recorded mode. No model produced this reply and no provider call was "
    "made. Not field evidence for any profile."
)

OBSERVATIONS: list[dict[str, Any]] = [
    {
        "category": "explicit_placeholder",
        "finding_text": (
            "Синтетический ответ (АР, спецификация), не результат вызова модели: тип "
            "светопрозрачного заполнения не определён, в общих данных оставлено указание "
            "«уточнить»."
        ),
        "recommendation_text": (
            "Определить тип светопрозрачного заполнения и согласовать его с позицией 2 "
            "спецификации (окно ПВХ двухкамерное)."
        ),
        "evidence": [
            {"page_number": 2, "quote": "1.3. Тип светопрозрачного заполнения — уточнить."},
        ],
    },
]


def text_layer_document() -> dict[str, Any]:
    """The ``prepared.text_layer`` the pinned extractor produces from the committed PDF."""
    extracted = extract_document(PDF_PATH.read_bytes())
    pages: list[dict[str, Any]] = []
    cursor = 0
    for page in extracted.pages:
        pages.append({
            "page_number": page.page_number,
            "char_start": cursor,
            "char_end": cursor + len(page.text),
            "text": page.text,
        })
        cursor += len(page.text)
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


def plan() -> list[tuple[Path, dict[str, Any]]]:
    layer = load_text_layer(text_layer_document())
    request = build_request(
        model_id=MODEL_ID, bundle=AR_TEXT_PROFILE.prompt_bundle, text_layer=layer
    )
    document = recording_document(
        request=request,
        output_text=json.dumps({"observations": OBSERVATIONS}, ensure_ascii=False),
        stop_reason="end_turn",
        input_tokens=2640,
        output_tokens=310,
        latency_ms=7800,
        note=(
            "Synthetic AR reply over the AR specification set's text layer, authored by hand: "
            "the one seeded placeholder, nothing else. Token counts and latency are authored, "
            "not measured."
        ),
        origin={
            "kind": "synthetic",
            "statement": _STATEMENT,
            "task_id": TASK_ID,
            "section_code": "AR",
            "analysis_profile_id": str(AR_TEXT_PROFILE.analysis_profile_id),
            "prompt_bundle_id": str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id),
            "prompt_bundle_sha256": AR_TEXT_PROFILE.prompt_bundle.content_sha256,
            "source_pdf": PDF_PATH.relative_to(_REPO_ROOT).as_posix(),
        },
    )
    return [(HERE / f"{request.request_sha256}.json", document)]


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stale(planned: list[tuple[Path, dict[str, Any]]]) -> list[Path]:
    wanted = {path for path, _ in planned}
    return [
        entry for entry in sorted(HERE.iterdir())
        if _KEY_FILE.fullmatch(entry.name) and entry not in wanted
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    planned = plan()
    leftovers = stale(planned)
    drift: list[str] = []
    for path, document in planned:
        rendered = render(document)
        relative = path.relative_to(_REPO_ROOT)
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != rendered:
                drift.append(str(relative))
            continue
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {relative}")
    for path in leftovers:
        relative = path.relative_to(_REPO_ROOT)
        if args.check:
            drift.append(f"{relative} (stale)")
        else:
            path.unlink()
            print(f"removed {relative}")

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
