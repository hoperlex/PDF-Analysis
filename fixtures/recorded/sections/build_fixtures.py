#!/usr/bin/env python3
"""Rebuild the SYNTHETIC section recordings (`W59-ANALYSIS-SETTINGS-01`, `SECTION-RECORDINGS-01`).

    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py
    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check

``--check`` rebuilds into memory and reports any file that would change or that no longer
belongs, so a profile prompt edit that orphans a recording fails loudly.

What these files are, and what they are not
-------------------------------------------
Each file answers one request: the section profile's own prompt bundle (from the
text-profile registry) over the committed AR corpus text layer
``fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`` -- the layer the
pinned extractor produces from ``fixtures/synthetic/ar/ar_baseline.pdf``, which is the
document the run suites seed. The key is ``request_sha256`` of that exact body, computed
here, never chosen.

The replies are **authored by hand**. No model produced them and no provider call was
made; every file says so in its ``origin`` block, and every finding text opens with
«Синтетический ответ». They exist to prove that a version classified to one of these
sections runs end to end with its own profile in recorded mode. They are **not** field
evidence for any profile's expert review and never count towards a profile becoming
``reviewed``. The token counts and latencies are authored too.

Fourteen sections have a recording, every section with a registered profile but AR (whose
recording is the canonical ``fixtures/recorded/text_analysis``): АИ, ПЗ, ПОС and ТХ came with
`W59-ANALYSIS-SETTINGS-01` and are rebuilt byte for byte as they were; КЖ, КМ, ОВ, ВК, ПТ, ЭОМ,
СС, ИТП, ГП and ПБ were added by `SECTION-RECORDINGS-01`. Each file names the task that
authored it in ``origin.task_id``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from auditmanager.analysis.text.adapter import build_request  # noqa: E402
from auditmanager.analysis.text.profile_registry import (  # noqa: E402
    load_text_profile_registry,
)
from auditmanager.analysis.text.recorded import recording_document  # noqa: E402
from auditmanager.analysis.text.textlayer import load_text_layer  # noqa: E402

HERE = Path(__file__).resolve().parent
TEXT_LAYER_PATH = _REPO_ROOT / "fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json"
MODEL_ID = "claude-opus-5"
TASK_ID = "W59-ANALYSIS-SETTINGS-01"
#: The task that added every section after the first four (`SECTION-RECORDINGS-01`).
RECORDINGS_TASK_ID = "SECTION-RECORDINGS-01"
#: The four sections whose files predate `SECTION-RECORDINGS-01` keep their original task.
FIRST_FOUR: frozenset[str] = frozenset({"AI", "PS", "POS", "TX"})
_KEY_FILE = re.compile(r"[0-9a-f]{64}\.json")

def _statement(task_id: str) -> str:
    return (
        f"Synthetic: authored by hand for {task_id} to prove section routing in "
        "recorded mode. No model produced this reply and no provider call was made. Not field "
        "evidence for the profile's review."
    )


def task_of(code: str) -> str:
    return TASK_ID if code in FIRST_FOUR else RECORDINGS_TASK_ID


_FIRE_RESISTANCE = [
    {"page_number": 2, "quote": "Степень огнестойкости здания — II."},
    {"page_number": 6, "quote": "Степень огнестойкости здания — III."},
]
_EXITS = [
    {"page_number": 3, "quote": "Из надземной части здания предусмотрено два эвакуационных выхода."},
    {"page_number": 7, "quote": "Из надземной части здания предусмотрено три эвакуационных выхода."},
]
_WINDOW_PLACEHOLDER = [{"page_number": 8, "quote": "Тип заполнения оконных проёмов — уточнить."}]


def _observation(category: str, label: str, finding: str, recommendation: str,
                 evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "category": category,
        "finding_text": f"Синтетический ответ ({label}), не результат вызова модели: {finding}",
        "recommendation_text": recommendation,
        "evidence": evidence,
    }


#: Per section: (Russian code, authored observations, input tokens, output tokens, latency).
#: Different on purpose -- count and content -- so a run that consumed another section's
#: recording could not pass for this one.
SECTIONS: dict[str, tuple[str, list[dict[str, Any]], int, int, int]] = {
    "AI": (
        "АИ",
        [
            _observation(
                "explicit_placeholder", "АИ",
                "тип заполнения оконных проёмов не определён — оставлено указание «уточнить».",
                "Определить тип заполнения оконных проёмов в ведомости заполнения проёмов.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2310, 420, 9100,
    ),
    "PS": (
        "ПЗ",
        [
            _observation(
                "internal_contradiction", "ПЗ",
                "степень огнестойкости здания указана как II в общих данных и как III в "
                "противопожарных мероприятиях.",
                "Привести степень огнестойкости здания к одному значению во всех частях документа.",
                _FIRE_RESISTANCE,
            ),
        ],
        2290, 470, 9400,
    ),
    "POS": (
        "ПОС",
        [
            _observation(
                "internal_contradiction", "ПОС",
                "количество эвакуационных выходов из надземной части здания указано как два "
                "и как три в разных разделах.",
                "Согласовать количество эвакуационных выходов из надземной части здания.",
                _EXITS,
            ),
        ],
        2330, 480, 9700,
    ),
    "TX": (
        "ТХ",
        [
            _observation(
                "internal_contradiction", "ТХ",
                "степень огнестойкости здания указана по-разному: II и III.",
                "Оставить одно значение степени огнестойкости здания.",
                _FIRE_RESISTANCE,
            ),
            _observation(
                "explicit_placeholder", "ТХ",
                "вместо типа заполнения оконных проёмов оставлено «уточнить».",
                "Определить тип заполнения оконных проёмов.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2350, 760, 11200,
    ),
    # `SECTION-RECORDINGS-01`. Every figure below differs from every other section's, and so does
    # the combination of seeded defects, so no reply could pass for another section's.
    "KJ": (
        "КЖ",
        [
            _observation(
                "internal_contradiction", "КЖ",
                "степень огнестойкости здания записана как II и как III, а несущие конструкции "
                "рассчитываются по одной из них.",
                "Согласовать степень огнестойкости здания с принятыми пределами огнестойкости "
                "несущих конструкций.",
                _FIRE_RESISTANCE,
            ),
        ],
        2370, 430, 9300,
    ),
    "KM": (
        "КМ",
        [
            _observation(
                "internal_contradiction", "КМ",
                "число эвакуационных выходов из надземной части здания названо два и три.",
                "Определить число эвакуационных выходов из надземной части здания.",
                _EXITS,
            ),
        ],
        2380, 440, 9500,
    ),
    "OV": (
        "ОВ",
        [
            _observation(
                "explicit_placeholder", "ОВ",
                "заполнение оконных проёмов, от которого зависит теплотехнический расчёт, "
                "оставлено словом «уточнить».",
                "Указать тип заполнения оконных проёмов до расчёта теплопотерь.",
                _WINDOW_PLACEHOLDER,
            ),
            _observation(
                "internal_contradiction", "ОВ",
                "из надземной части здания предусмотрено два выхода в одном разделе и три в другом.",
                "Свести число выходов к одному значению для расчёта систем вентиляции.",
                _EXITS,
            ),
        ],
        2390, 720, 10800,
    ),
    "VK": (
        "ВК",
        [
            _observation(
                "explicit_placeholder", "ВК",
                "тип заполнения оконных проёмов не определён: стоит отметка «уточнить».",
                "Определить заполнение оконных проёмов в ведомости.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2400, 410, 8900,
    ),
    "PT": (
        "ПТ",
        [
            _observation(
                "internal_contradiction", "ПТ",
                "степень огнестойкости здания, по которой назначается противопожарный "
                "водопровод, дана как II и как III.",
                "Привести степень огнестойкости здания к одному значению.",
                _FIRE_RESISTANCE,
            ),
            _observation(
                "explicit_placeholder", "ПТ",
                "тип заполнения оконных проёмов не принят — оставлено «уточнить».",
                "Принять тип заполнения оконных проёмов.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2410, 740, 11000,
    ),
    "EOM": (
        "ЭОМ",
        [
            _observation(
                "internal_contradiction", "ЭОМ",
                "количество эвакуационных выходов, для которых проектируется аварийное "
                "освещение, указано как два и как три.",
                "Уточнить число эвакуационных выходов в исходных данных освещения.",
                _EXITS,
            ),
        ],
        2420, 450, 9200,
    ),
    "SS": (
        "СС",
        [
            _observation(
                "explicit_placeholder", "СС",
                "в ведомости заполнения проёмов вместо типа оконного заполнения оставлено «уточнить».",
                "Заполнить тип оконного заполнения в ведомости.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2430, 400, 8800,
    ),
    "ITP": (
        "ИТП",
        [
            _observation(
                "internal_contradiction", "ИТП",
                "степень огнестойкости здания записана двумя разными значениями: II и III.",
                "Оставить в тексте одну степень огнестойкости здания.",
                _FIRE_RESISTANCE,
            ),
        ],
        2440, 460, 9900,
    ),
    "GP": (
        "ГП",
        [
            _observation(
                "internal_contradiction", "ГП",
                "число эвакуационных выходов из надземной части здания указано как два и как три.",
                "Согласовать число выходов с решениями по подъездам и площадкам.",
                _EXITS,
            ),
            _observation(
                "internal_contradiction", "ГП",
                "степень огнестойкости здания, от которой зависят противопожарные разрывы, "
                "записана как II и как III.",
                "Установить одну степень огнестойкости здания для расчёта разрывов.",
                _FIRE_RESISTANCE,
            ),
        ],
        2450, 790, 11500,
    ),
    "PB": (
        "ПБ",
        [
            _observation(
                "internal_contradiction", "ПБ",
                "степень огнестойкости здания указана как II в общих данных и как III в "
                "противопожарных мероприятиях.",
                "Привести степень огнестойкости здания к одному значению во всех частях документа.",
                _FIRE_RESISTANCE,
            ),
            _observation(
                "internal_contradiction", "ПБ",
                "число эвакуационных выходов из надземной части здания названо два и три.",
                "Согласовать число эвакуационных выходов из надземной части здания.",
                _EXITS,
            ),
            _observation(
                "explicit_placeholder", "ПБ",
                "тип заполнения оконных проёмов не определён — оставлено указание «уточнить».",
                "Определить тип заполнения оконных проёмов в ведомости заполнения проёмов.",
                _WINDOW_PLACEHOLDER,
            ),
        ],
        2460, 980, 12600,
    ),
}


def plan() -> list[tuple[Path, dict[str, Any]]]:
    registry = load_text_profile_registry()
    text_layer = load_text_layer(json.loads(TEXT_LAYER_PATH.read_text(encoding="utf-8")))
    entries: list[tuple[Path, dict[str, Any]]] = []
    for code, (label, observations, input_tokens, output_tokens, latency_ms) in SECTIONS.items():
        registered = registry.entries[code]
        profile = registered.profile
        request = build_request(
            model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=text_layer
        )
        document = recording_document(
            request=request,
            output_text=json.dumps({"observations": observations}, ensure_ascii=False),
            stop_reason="end_turn",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            note=(
                f"Synthetic {label} ({code}) reply over the AR baseline corpus text layer, "
                "authored by hand. Token counts and latency are authored, not measured."
            ),
            origin={
                "kind": "synthetic",
                "statement": _statement(task_of(code)),
                "task_id": task_of(code),
                "section_code": code,
                "analysis_profile_id": str(profile.analysis_profile_id),
                "prompt_bundle_id": str(profile.prompt_bundle.prompt_bundle_id),
                "prompt_bundle_sha256": profile.prompt_bundle.content_sha256,
                "profile_status": registered.status,
                "text_layer": TEXT_LAYER_PATH.relative_to(_REPO_ROOT).as_posix(),
            },
        )
        entries.append((HERE / code.lower() / f"{request.request_sha256}.json", document))
    return entries


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stale(planned: list[tuple[Path, dict[str, Any]]]) -> list[Path]:
    """Recording files in the planned section directories that the plan does not write."""
    wanted = {path for path, _ in planned}
    found: list[Path] = []
    for directory in sorted({path.parent for path, _ in planned}):
        if directory.is_dir():
            found.extend(
                entry for entry in sorted(directory.iterdir())
                if _KEY_FILE.fullmatch(entry.name) and entry not in wanted
            )
    return found


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
        path.parent.mkdir(parents=True, exist_ok=True)
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
