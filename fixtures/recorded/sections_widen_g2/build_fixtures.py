#!/usr/bin/env python3
"""Rebuild the SYNTHETIC positive and negative recordings of `SECTION-WIDEN-G2-01` (КМ, ОВ, ВК, ПТ).

    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections_widen_g2/build_fixtures.py
    PYTHONPATH=src .venv/bin/python fixtures/recorded/sections_widen_g2/build_fixtures.py --check

``--check`` rebuilds into memory and reports any file that would change or that no longer belongs,
so a prompt edit that orphans a recording fails loudly (the same idiom as
``fixtures/recorded/sections/build_fixtures.py``).

What these files are, and what they are not
-------------------------------------------
Lane `SECTION-WIDEN-G2-01` widened four section prompts (КМ, ОВ, ВК, ПТ) with the same-document
checks that ``ROADMAP-GAP-2026-10-27.md`` section 2.3 marks reinstatable: a total against the sum of
its rows, and for ПТ the same flow in two units, the jets x single-jet flow product and the
ВПВ + АУПТ sum. For each of the four sections this directory holds

* one **positive** case: a short invented text in which a total differs from its rows (or a flow
  differs from itself in another unit), and a recorded reply with one observation per defect,
  each citing the places that disagree; and
* one **negative** case: the same text with consistent figures, and an empty reply. Both texts also
  carry *traps*, places where the prompt says not to compare (a total with a stated different
  basis, an air flow of a unit with leaks, secondly flows, a head in metres against a pressure in
  МПа, a flow the text says came from the hydraulic calculation).

Every file is **synthetic**: the text and the reply were authored by hand. No model produced them
and no provider call was made. They prove that a reply of this shape binds to the text it quotes
(every quote is found verbatim on its page) and that the section's own prompt keys the request; they
say nothing about what a model would answer on this text or on a real document. They are not field
evidence and never count towards a profile's review (`R-146ag`, `A-7`).

They live outside ``fixtures/recorded/sections/`` on purpose: ``tests/integration/sections/
test_section_recordings.py`` pins exactly one recording per directory there and exactly fourteen
planned entries, and the default ``RecordedAdapter()`` searches every directory there, so adding
these files there would turn that suite red and change what a served stack can answer. Here they are
read only by an adapter built with a directory (``RecordedAdapter(<code>/)``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
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
from auditmanager.shared.identity import VersionUid  # noqa: E402

HERE = Path(__file__).resolve().parent
MODEL_ID = "claude-opus-5"
TASK_ID = "SECTION-WIDEN-G2-01"
SECTION_CODES = ("KM", "OV", "VK", "PT")
CASES = ("positive", "negative")
_KEY_FILE = re.compile(r"[0-9a-f]{64}\.json")
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _statement() -> str:
    return (
        f"Synthetic: authored by hand for {TASK_ID} to show how a total that differs from its rows "
        "(or a flow in two units) is cited, and that a consistent text yields no observation. No "
        "model produced this reply and no provider call was made. Not field evidence for the "
        "profile's review."
    )


def _head(title: str) -> str:
    return (
        f"{title}\n"
        "Объект: многоквартирный жилой дом (вымышленный, для проверки)\n"
        "Стадия: П\n"
        "Общие данные\n"
    )


# --- the invented texts, one list of pages per (section, case) -------------------------------


def _km(consistent: bool) -> list[str]:
    total = "5982,5" if consistent else "5892,5"
    return [
        _head("Раздел 4. Конструкции металлические (КМ)")
        + "Конструктивная схема каркаса — рамно-связевая.\n"
        + f"Общая масса металлоконструкций, прямо указанная в общих данных: {total} кг.\n",
        "Спецификация металлопроката. Масса марок, кг\n"
        "Марка Профиль Количество, шт. Масса марки, кг\n"
        "Б1 Двутавр 30Б1 6 1240,5\n"
        "Б2 Двутавр 25Б1 4 868,0\n"
        "К1 Двутавр 30К1 8 2315,5\n"
        "К2 Двутавр 25К1 4 1102,0\n"
        "Св1 Уголок 100х8 20 456,5\n"
        f"Итого {total}\n"
        "Примечание. Масса в таблице дана без учёта наплавленного металла и метизов.\n",
        "Пояснительная записка. Масса металлоконструкций с учётом наплавленного металла — "
        "6071,7 кг.\n",
    ]


def _ov(consistent: bool) -> list[str]:
    air = "1100" if consistent else "1200"
    heat = "415,5" if consistent else "405,5"
    return [
        _head("Раздел 5. Отопление, вентиляция и кондиционирование (ОВ)")
        + "Теплоноситель систем отопления — вода.\n",
        "Таблица воздухообмена. Система П1 (приток), расход воздуха, м³/ч\n"
        "101 Тамбур 300\n"
        "102 Лифтовой холл 450\n"
        "103 Помещение охраны 200\n"
        "104 Электрощитовая 150\n"
        f"Итого по системе П1 {air}\n"
        "Таблица тепловых нагрузок, кВт\n"
        "Отопление 180,0\n"
        "Вентиляция 95,5\n"
        "Горячее водоснабжение 140,0\n"
        f"Итого {heat}\n",
        "Таблица характеристик систем\n"
        "Система П1: расход воздуха установки 1250 м³/ч (с учётом подсосов и потерь).\n",
    ]


def _vk(consistent: bool) -> list[str]:
    total = "118,4" if consistent else "121,4"
    return [
        _head("Раздел 6. Водоснабжение и канализация (ВК)")
        + "Источник водоснабжения — городской водопровод.\n",
        "Таблица расчётных расходов воды\n"
        f"Суточное водопотребление здания, м³/сут: всего {total}, в том числе:\n"
        "жилая часть 96,2\n"
        "встроенные помещения 14,6\n"
        "полив территории 7,6\n"
        "Максимальный секундный расход, л/с: общий 4,20, в том числе холодной воды 3,10 "
        "и горячей воды 2,00.\n",
    ]


def _pt(consistent: bool) -> list[str]:
    pump = "36" if consistent else "40"
    vpv = "5,2" if consistent else "4,8"
    total = "33,2" if consistent else "34,0"
    return [
        _head("Раздел 7. Противопожарный водопровод (ПТ)")
        + "Подача основного пожарного насоса — 10 л/с.\n"
        + "Внутренний противопожарный водопровод: число струй — 2, расход одной струи — 2,6 л/с, "
        + f"расчётный расход ВПВ — {vpv} л/с.\n",
        "Спецификация оборудования\n"
        f"Насос пожарный основной: подача {pump} м³/ч, напор 55 м\n"
        "Расчётный расход АУПТ — 28,0 л/с.\n"
        f"Суммарный расход ВПВ и АУПТ — {total} л/с.\n",
        "Внутренний противопожарный водопровод паркинга: число струй — 2, расход одной струи — "
        "2,6 л/с, расчётный расход — 6,1 л/с по результатам гидравлического расчёта.\n"
        "Напор у диктующего пожарного крана — 45 м; давление у пожарного крана по таблице "
        "гидравлического расчёта — 0,43 МПа.\n",
    ]


PAGES = {
    "KM": _km,
    "OV": _ov,
    "VK": _vk,
    "PT": _pt,
}

# --- the authored replies ----------------------------------------------------------------------


def _observation(label: str, finding: str, recommendation: str,
                 evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "category": "internal_contradiction",
        "finding_text": f"Синтетический ответ ({label}), не результат вызова модели: {finding}",
        "recommendation_text": recommendation,
        "evidence": evidence,
    }


#: The positive replies. The quotes are copied from the positive texts above, one per place that
#: disagrees: the line that carries the total (or the second writing of the flow) and each row.
POSITIVE_REPLIES: dict[str, list[dict[str, Any]]] = {
    "KM": [
        _observation(
            "КМ",
            "итог столбца масс в спецификации металлопроката записан как 5892,5 кг, а сумма масс "
            "пяти марок того же столбца — 5982,5 кг; разность больше погрешности округления, "
            "основа массы в таблице названа одна (без наплавленного металла и метизов).",
            "Проверить массы марок и итог спецификации и привести их в соответствие.",
            [
                {"page_number": 2, "quote": "Итого 5892,5"},
                {"page_number": 2, "quote": "Б1 Двутавр 30Б1 6 1240,5"},
                {"page_number": 2, "quote": "Б2 Двутавр 25Б1 4 868,0"},
                {"page_number": 2, "quote": "К1 Двутавр 30К1 8 2315,5"},
                {"page_number": 2, "quote": "К2 Двутавр 25К1 4 1102,0"},
                {"page_number": 2, "quote": "Св1 Уголок 100х8 20 456,5"},
            ],
        ),
    ],
    "OV": [
        _observation(
            "ОВ",
            "итог таблицы воздухообмена по системе П1 записан как 1200 м³/ч, а сумма расходов "
            "четырёх помещений этой системы — 1100 м³/ч.",
            "Сверить расходы помещений системы П1 с итогом таблицы воздухообмена.",
            [
                {"page_number": 2, "quote": "Итого по системе П1 1200"},
                {"page_number": 2, "quote": "101 Тамбур 300"},
                {"page_number": 2, "quote": "102 Лифтовой холл 450"},
                {"page_number": 2, "quote": "103 Помещение охраны 200"},
                {"page_number": 2, "quote": "104 Электрощитовая 150"},
            ],
        ),
        _observation(
            "ОВ",
            "итог таблицы тепловых нагрузок записан как 405,5 кВт, а сумма трёх её строк — "
            "415,5 кВт.",
            "Сверить строки таблицы тепловых нагрузок с её итогом.",
            [
                {"page_number": 2, "quote": "Итого 405,5"},
                {"page_number": 2, "quote": "Отопление 180,0"},
                {"page_number": 2, "quote": "Вентиляция 95,5"},
                {"page_number": 2, "quote": "Горячее водоснабжение 140,0"},
            ],
        ),
    ],
    "VK": [
        _observation(
            "ВК",
            "суточное водопотребление здания записано как 121,4 м³/сут, а сумма трёх частей, "
            "названных в тексте частями этого итога, — 118,4 м³/сут.",
            "Сверить части суточного водопотребления с итогом по зданию.",
            [
                {"page_number": 2, "quote": "всего 121,4"},
                {"page_number": 2, "quote": "жилая часть 96,2"},
                {"page_number": 2, "quote": "встроенные помещения 14,6"},
                {"page_number": 2, "quote": "полив территории 7,6"},
            ],
        ),
    ],
    "PT": [
        _observation(
            "ПТ",
            "подача основного пожарного насоса записана как 10 л/с, что при равенстве "
            "1 л/с = 3,6 м³/ч составляет 36 м³/ч, и как 40 м³/ч в спецификации; разность "
            "больше погрешности округления.",
            "Привести подачу основного пожарного насоса к одному значению.",
            [
                {"page_number": 1, "quote": "Подача основного пожарного насоса — 10 л/с."},
                {"page_number": 2, "quote": "Насос пожарный основной: подача 40 м³/ч, напор 55 м"},
            ],
        ),
        _observation(
            "ПТ",
            "расчётный расход ВПВ записан как 4,8 л/с, а число струй 2, умноженное на расход "
            "одной струи 2,6 л/с, даёт 5,2 л/с; текст не говорит, что расчётный расход "
            "определён иначе.",
            "Согласовать расчётный расход ВПВ с числом струй и расходом одной струи.",
            [
                {
                    "page_number": 1,
                    "quote": "число струй — 2, расход одной струи — 2,6 л/с, "
                    "расчётный расход ВПВ — 4,8 л/с",
                },
            ],
        ),
        _observation(
            "ПТ",
            "суммарный расход ВПВ и АУПТ записан как 34,0 л/с, а сумма записанных расходов "
            "ВПВ (4,8 л/с) и АУПТ (28,0 л/с) — 32,8 л/с.",
            "Сверить суммарный расход с расходами ВПВ и АУПТ.",
            [
                {"page_number": 2, "quote": "Суммарный расход ВПВ и АУПТ — 34,0 л/с."},
                {"page_number": 1, "quote": "расчётный расход ВПВ — 4,8 л/с"},
                {"page_number": 2, "quote": "Расчётный расход АУПТ — 28,0 л/с."},
            ],
        ),
    ],
}

#: Authored, not measured: (input tokens, output tokens, latency in ms) per (section, case).
USAGE: dict[tuple[str, str], tuple[int, int, int]] = {
    ("KM", "positive"): (2850, 520, 11800),
    ("KM", "negative"): (2840, 90, 6200),
    ("OV", "positive"): (2890, 760, 13100),
    ("OV", "negative"): (2880, 90, 6400),
    ("VK", "positive"): (2860, 500, 11500),
    ("VK", "negative"): (2850, 90, 6100),
    ("PT", "positive"): (2910, 940, 14800),
    ("PT", "negative"): (2900, 90, 6600),
}


def reply(code: str, case: str) -> list[dict[str, Any]]:
    return POSITIVE_REPLIES[code] if case == "positive" else []


def _version_uid(code: str, case: str) -> str:
    """A well-formed, deterministic ``ver_`` identity for the invented text layer."""
    digest = hashlib.sha256(f"{TASK_ID}:{code}:{case}".encode()).digest()
    body = "".join(_CROCKFORD[byte % 32] for byte in digest[:26])
    uid = f"ver_{body}"
    VersionUid.parse(uid)
    return uid


def layer_document(code: str, case: str) -> dict[str, Any]:
    """The ``prepared.text_layer`` artifact of one invented text (NFC, gapless offsets)."""
    pages = [unicodedata.normalize("NFC", text) for text in PAGES[code](case == "negative")]
    entries: list[dict[str, Any]] = []
    start = 0
    for number, text in enumerate(pages, start=1):
        entries.append(
            {"char_end": start + len(text), "char_start": start, "page_number": number, "text": text}
        )
        start += len(text)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "extractor": {"name": "hand-authored", "options_sha256": "", "version": "synthetic"},
        "normalization": {
            "description": "Unicode NFC. Authored by hand; no extractor ran.",
            "id": "nfc_v1",
        },
        "pages": entries,
        "total_char_count": start,
        "version_uid": _version_uid(code, case),
    }


def input_path(code: str, case: str) -> Path:
    return HERE / "inputs" / f"{code.lower()}_{case}.json"


def plan() -> list[tuple[Path, dict[str, Any], Path, dict[str, Any]]]:
    """``(recording path, recording, input path, input document)`` for every (section, case)."""
    registry = load_text_profile_registry()
    entries: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []
    for code in SECTION_CODES:
        registered = registry.entries[code]
        profile = registered.profile
        for case in CASES:
            document = layer_document(code, case)
            request = build_request(
                model_id=MODEL_ID, bundle=profile.prompt_bundle, text_layer=load_text_layer(document)
            )
            input_tokens, output_tokens, latency_ms = USAGE[(code, case)]
            recording = recording_document(
                request=request,
                output_text=json.dumps({"observations": reply(code, case)}, ensure_ascii=False),
                stop_reason="end_turn",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                note=(
                    f"Synthetic {case} case for {code}: invented text, reply authored by hand. "
                    "Token counts and latency are authored, not measured."
                ),
                origin={
                    "kind": "synthetic",
                    "statement": _statement(),
                    "task_id": TASK_ID,
                    "case": case,
                    "section_code": code,
                    "analysis_profile_id": str(profile.analysis_profile_id),
                    "prompt_bundle_id": str(profile.prompt_bundle.prompt_bundle_id),
                    "prompt_bundle_sha256": profile.prompt_bundle.content_sha256,
                    "profile_version": profile.profile_version,
                    "profile_status": registered.status,
                    "text_layer": input_path(code, case).relative_to(_REPO_ROOT).as_posix(),
                },
            )
            entries.append(
                (HERE / code.lower() / f"{request.request_sha256}.json", recording,
                 input_path(code, case), document)
            )
    return entries


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stale(planned: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]]) -> list[Path]:
    """Files in the planned directories that the plan does not write."""
    wanted = {entry[0] for entry in planned} | {entry[2] for entry in planned}
    found: list[Path] = []
    directories = {entry[0].parent for entry in planned} | {entry[2].parent for entry in planned}
    for directory in sorted(directories):
        if directory.is_dir():
            found.extend(
                item for item in sorted(directory.iterdir())
                if item.suffix == ".json"
                and (_KEY_FILE.fullmatch(item.name) or item.parent.name == "inputs")
                and item not in wanted
            )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    planned = plan()
    leftovers = stale(planned)
    drift: list[str] = []
    for recording_path, recording, layer_path, layer in planned:
        for path, document in ((recording_path, recording), (layer_path, layer)):
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
