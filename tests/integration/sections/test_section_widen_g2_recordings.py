"""`SECTION-WIDEN-G2-01`: the widened КМ, ОВ, ВК and ПТ prompts and their synthetic positive and
negative recordings.

Container-free. What is held here:

* each of the four section prompts carries the fragments the lane added (the exception paragraph,
  the hint bullet and its conditions), compared with whitespace normalised, so a later edit that
  drops or rewords one fails here even if its recording is rebuilt consistently (`D-224` residual;
  `SECTION-PROMPT-SENTENCE-GUARD-01` may absorb this table);
* ``fixtures/recorded/sections_widen_g2/`` holds exactly two recordings per section, one positive
  and one negative, keyed to the request the section's **current** prompt sends over the lane's
  own invented text, labelled synthetic, with no provider mode; the builder reports no drift;
* the invented texts are what the file name says: in every positive case each seeded defect is a real
  arithmetic disagreement beyond the tolerance the prompt states in words, in every negative case
  the same figures are consistent, and every *trap* (a place where the prompt says not to compare)
  would be flagged by a naive sum or product, so the trap is a trap;
* every positive recording replays through the real stage with the section's own profile, publishes
  exactly one grounded observation per seeded defect (every quote found verbatim on its page) and
  every negative one publishes none; a recording whose quote is altered loses its observation.

Nothing here says what a model answers on this text. The replies are authored.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import pytest

from auditmanager.analysis.text import STATUS_SUCCEEDED, run_text_analysis
from auditmanager.analysis.text.adapter import ModelRequest, build_request
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recorded import RecordedAdapter
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.identity import RunId

ROOT = Path(__file__).resolve().parents[3]
WIDEN = ROOT / "fixtures" / "recorded" / "sections_widen_g2"
SECTIONS = ROOT / "fixtures" / "recorded" / "sections"
PROFILES = ROOT / "src" / "auditmanager" / "analysis" / "text" / "profiles"
MODEL_ID = "claude-opus-5"
CODES = ("KM", "OV", "VK", "PT")
CASES = ("positive", "negative")
REGISTRY = load_text_profile_registry()
CASE_IDS = [(code, case) for code in CODES for case in CASES]


def _normal(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


# --- the fragments the lane added to each prompt (verbatim, whitespace normalised) --------------

#: Section -> the exact sentences the lane added. The report table repeats them.
FRAGMENTS: dict[str, tuple[str, ...]] = {
    "KM": (
        "- итог столбца масс и сумма масс строк этого столбца в спецификации металлопроката и в "
        "ведомости элементов — только на условиях абзаца об исключении из запрета на расчёты ниже;",
        "Единственное исключение из запрета на расчёты — сверка записанного итога с суммой "
        "записанных слагаемых. Для КМ это строка «Итого» («Всего», «Сумма») столбца масс в "
        "спецификации металлопроката или в ведомости элементов и сумма масс строк этого же столбца.",
        "- итог и каждое слагаемое прямо записаны в тексте числами в одних и тех же единицах, а "
        "текст показывает, что эти строки составляют именно этот итог; все строки видны в "
        "переданном тексте — без пропусков, без «и т. д.» и без обрыва таблицы;",
        "- ни одно число не прочитано с чертежа, рисунка или распознанного изображения и не "
        "восстановлено по другим значениям;",
        "- у самой таблицы или в её примечании текст называет основу массы: включены ли в неё "
        "наплавленный металл, метизы, огнезащита, запас; основа одна и та же у итога и у всех "
        "строк, а между строками и итогом нет подытогов и строк-добавок;",
        "- разницу считай расхождением, только если она больше погрешности округления — суммы "
        "половин единицы последнего записанного разряда итога и каждого слагаемого; меньшая "
        "разница — это округление.",
        "Если хотя бы одно условие не выполнено, итог с суммой не сопоставляй. Находка — только "
        "internal_contradiction: в evidence приведи цитату строки с итогом и цитату каждой "
        "строки-слагаемого. Других вычислений (например, массу одного элемента, умноженную на "
        "количество) не выполняй.",
    ),
    "OV": (
        "- итог таблицы воздухообмена по системе и сумма расходов её помещений; итог таблицы "
        "тепловых нагрузок и сумма её строк — только на условиях абзаца об исключении из запрета "
        "на расчёты ниже;",
        "Единственное исключение из запрета на расчёты — сверка записанного итога с суммой "
        "записанных слагаемых. Для ОВ это строка «Итого» («Всего») таблицы воздухообмена по "
        "системе и сумма расходов помещений этой системы того же вида (приток с притоком, вытяжка "
        "с вытяжкой), а также строка «Итого» таблицы тепловых нагрузок и сумма её строк того же "
        "вида нагрузки.",
        "Расход системы из таблицы характеристик систем или из спецификации с суммой расходов "
        "помещений сопоставляй, только если текст прямо называет его суммой расходов этих "
        "помещений: разница на подсосы и потери допустима. Приток с вытяжкой и нагрузки разных "
        "видов друг с другом не сопоставляй.",
        "- ни одно число не прочитано с чертежа, рисунка или распознанного изображения и не "
        "восстановлено по другим значениям;",
        "- между строками и итогом нет подытогов и строк-добавок, а текст не говорит, что итог "
        "включает или не включает какую-то часть либо получен иначе (с учётом потерь, "
        "коэффициента, резерва); если такое сказано, сверяй, только если эта же часть входит или "
        "не входит и в строки;",
        "- разницу считай расхождением, только если она больше погрешности округления — суммы "
        "половин единицы последнего записанного разряда итога и каждого слагаемого; меньшая "
        "разница — это округление.",
        "Если хотя бы одно условие не выполнено, итог с суммой не сопоставляй. Находка — только "
        "internal_contradiction: в evidence приведи цитату строки с итогом и цитату каждой "
        "строки-слагаемого. Других вычислений не выполняй.",
    ),
    "VK": (
        "- суточное водопотребление здания и сумма его частей, которые текст сам называет частями "
        "этого итога, — только на условиях абзаца об исключении из запрета на расчёты ниже;",
        "Единственное исключение из запрета на расчёты — сверка записанного итога с суммой "
        "записанных слагаемых. Для ВК это только суточное водопотребление: итог по зданию "
        "(«Итого», «Всего») и строки по системам или потребителям, которые текст сам называет "
        "частями этого итога («в том числе», «из них»).",
        "Часовые и секундные расходы здания не суммируй: расходы отдельных систем в сумме не "
        "обязаны давать расход здания. Строку, которая сама является итогом или повторяет другую "
        "строку (например, расход канализации, равный общему расходу воды), в сумму не включай.",
        "- ни одно число не прочитано с чертежа, рисунка или распознанного изображения и не "
        "восстановлено по другим значениям;",
        "- между частями и итогом нет подытогов и строк-добавок, а текст не говорит, что итог "
        "включает или не включает какую-то часть (полив, потери, резерв); если такое сказано, "
        "сверяй, только если эта же часть входит или не входит и в строки;",
        "- разницу считай расхождением, только если она больше погрешности округления — суммы "
        "половин единицы последнего записанного разряда итога и каждого слагаемого; меньшая "
        "разница — это округление.",
        "Если хотя бы одно условие не выполнено, итог с суммой не сопоставляй. Находка — только "
        "internal_contradiction: в evidence приведи цитату строки с итогом и цитату каждой "
        "строки-слагаемого. Других вычислений не выполняй.",
    ),
    "PT": (
        "- один и тот же расход в разных единицах, расчётный расход ВПВ и произведение числа "
        "струй на расход одной струи, итоговый расход и сумма расходов ВПВ и АУПТ — только на "
        "условиях абзаца об исключении из запрета на расчёты ниже;",
        "Единственное исключение из запрета на расчёты — три сверки записанных значений одной и "
        "той же системы или одного и того же насоса:",
        "- один и тот же расход (подача одного и того же насоса, расход одной и той же системы), "
        "записанный в одном месте в л/с, а в другом в м³/ч: приведи к одним единицам по равенству "
        "1 л/с = 3,6 м³/ч. Других коэффициентов и других пар единиц не применяй, а напор, "
        "записанный в метрах, и давление, записанное в МПа, между собой не сопоставляй;",
        "- расчётный расход ВПВ и произведение числа струй на расход одной струи — только если "
        "число струй, расход одной струи и расчётный расход записаны в тексте для одной и той же "
        "системы, а текст не говорит, что расчётный расход определён иначе (например, по "
        "гидравлическому расчёту при другом числе или расходе струй);",
        "- итоговый расход и сумма расходов ВПВ и АУПТ — только если расход ВПВ, расход АУПТ и "
        "итог записаны в тексте и текст прямо называет итог суммой этих расходов; если сказано о "
        "большем из двух расходов или об отдельной работе систем, итог с суммой не сопоставляй.",
        "- ни одно число не прочитано с чертежа, рисунка или распознанного изображения и не "
        "восстановлено по другим значениям;",
        "- разницу считай расхождением, только если она больше погрешности округления — суммы "
        "половин единицы последнего записанного разряда всех сравниваемых величин, каждой с "
        "учётом множителя, на который она умножается или в который пересчитана; меньшая разница "
        "— это округление.",
        "Если хотя бы одно условие не выполнено, величины не сопоставляй. Находка — только "
        "internal_contradiction: в evidence приведи цитату каждого места, где записана "
        "сравниваемая величина, и цитату итога. Других вычислений не выполняй.",
    ),
}


def _prompt(code: str) -> str:
    return (PROFILES / code.lower() / "system_prompt.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("code", CODES)
def test_the_prompt_carries_every_fragment_the_lane_added_exactly_once(code: str) -> None:
    body = _normal(_prompt(code))
    counts = {fragment: body.count(_normal(fragment)) for fragment in FRAGMENTS[code]}
    lost = [fragment[:70] for fragment, count in counts.items() if count == 0]
    repeated = [fragment[:70] for fragment, count in counts.items() if count > 1]
    assert lost == [], f"{code}: the prompt lost {len(lost)} fragment(s): {lost}"
    assert repeated == [], f"{code}: fragment(s) occur more than once: {repeated}"


# --- the recordings -----------------------------------------------------------------------------


def _layer(code: str, case: str) -> dict[str, Any]:
    return json.loads((WIDEN / "inputs" / f"{code.lower()}_{case}.json").read_text(encoding="utf-8"))


def _request(code: str, case: str) -> ModelRequest:
    return build_request(
        model_id=MODEL_ID,
        bundle=REGISTRY.entries[code].profile.prompt_bundle,
        text_layer=load_text_layer(_layer(code, case)),
    )


def _recording_path(code: str, case: str) -> Path:
    return WIDEN / code.lower() / f"{_request(code, case).request_sha256}.json"


def _recording(code: str, case: str) -> dict[str, Any]:
    return json.loads(_recording_path(code, case).read_text(encoding="utf-8"))


def _observations(code: str, case: str) -> list[dict[str, Any]]:
    return json.loads(_recording(code, case)["output_text"])["observations"]


def _page_text(code: str, case: str, number: int) -> str:
    return next(page["text"] for page in _layer(code, case)["pages"] if page["page_number"] == number)


def test_the_builder_reports_no_drift() -> None:
    completed = subprocess.run(
        [sys.executable, str(WIDEN / "build_fixtures.py"), "--check"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "fixtures match"


@pytest.mark.parametrize("code", CODES)
def test_each_section_directory_holds_exactly_its_positive_and_negative_recording(code: str) -> None:
    keys = {_request(code, case).request_sha256 for case in CASES}
    assert len(keys) == 2, "positive and negative must be two different questions"
    assert sorted(item.name for item in (WIDEN / code.lower()).iterdir()) == sorted(
        f"{key}.json" for key in keys
    )
    # Neither key is the section's routing recording over the AR corpus, so nothing here can
    # answer (or be answered by) the 14 recordings under fixtures/recorded/sections/.
    main = {item.stem for item in (SECTIONS / code.lower()).iterdir()}
    assert not keys & main
    assert sorted(item.name for item in (WIDEN / "inputs").iterdir() if item.name.startswith(code.lower())) == [
        f"{code.lower()}_negative.json", f"{code.lower()}_positive.json",
    ]


@pytest.mark.parametrize(("code", "case"), CASE_IDS)
def test_each_recording_is_synthetic_keyed_to_the_current_prompt_and_carries_no_mode(
    code: str, case: str
) -> None:
    request = _request(code, case)
    document = _recording(code, case)
    entry = REGISTRY.entries[code]
    assert document["request_sha256"] == request.request_sha256
    assert document["model_id"] == MODEL_ID
    origin = document["origin"]
    assert origin["kind"] == "synthetic"
    assert "No model produced this reply" in origin["statement"]
    assert "Not field evidence" in origin["statement"]
    assert origin["task_id"] == "SECTION-WIDEN-G2-01" and origin["case"] == case
    assert origin["section_code"] == code
    assert origin["analysis_profile_id"] == entry.analysis_profile_id
    assert origin["prompt_bundle_id"] == entry.prompt_bundle_id
    assert origin["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
    assert origin["profile_version"] == "1.2.0" and origin["profile_status"] == "reviewed"
    for mapping in (document, origin):
        assert not {"provider_mode", "mode"} & set(mapping)
    observations = _observations(code, case)
    if case == "negative":
        assert observations == []
    else:
        assert observations
        assert all(item["category"] == "internal_contradiction" for item in observations)
        assert all(item["finding_text"].startswith("Синтетический ответ (") for item in observations)


# --- the arithmetic of the invented texts ---------------------------------------------------------

_NUMBER = re.compile(r"\d+(?:,\d+)?")


def _last_number(line: str) -> Decimal:
    return Decimal(_NUMBER.findall(line)[-1].replace(",", "."))


def _half_unit(line: str) -> Decimal:
    """Half a unit of the last written digit of the last number of ``line``."""
    text = _NUMBER.findall(line)[-1]
    decimals = len(text.split(",")[1]) if "," in text else 0
    return Decimal(5) / (Decimal(10) ** (decimals + 1))


def _line(code: str, case: str, page: int, prefix: str, *, not_prefix: str | None = None) -> str:
    """The one line of a page that starts with ``prefix`` (and not with ``not_prefix``)."""
    found = [
        line for line in _page_text(code, case, page).splitlines()
        if line.startswith(prefix) and not (not_prefix and line.startswith(not_prefix))
    ]
    assert len(found) == 1, (code, case, page, prefix, found)
    return found[0]


def _sum_fact(
    code: str, case: str, page: int, total: str, parts: tuple[str, ...], *, not_prefix: str | None = None
) -> tuple[bool, str]:
    """(consistent, the total line): the prompt's rule for a total against its rows, in numbers."""
    total_line = _line(code, case, page, total, not_prefix=not_prefix)
    part_lines = [_line(code, case, page, prefix) for prefix in parts]
    difference = abs(_last_number(total_line) - sum(_last_number(line) for line in part_lines))
    tolerance = _half_unit(total_line) + sum(_half_unit(line) for line in part_lines)
    return difference <= tolerance, total_line


def _facts(code: str, case: str) -> list[tuple[bool, str]]:
    """Every seeded relation of the section's text: (consistent, a line that carries the total)."""
    if code == "KM":
        return [_sum_fact("KM", case, 2, "Итого", ("Б1 ", "Б2 ", "К1 ", "К2 ", "Св1 "))]
    if code == "OV":
        return [
            _sum_fact("OV", case, 2, "Итого по системе П1", ("101 ", "102 ", "103 ", "104 ")),
            _sum_fact(
                "OV", case, 2, "Итого", ("Отопление ", "Вентиляция ", "Горячее "),
                not_prefix="Итого по системе",
            ),
        ]
    if code == "VK":
        return [
            _sum_fact("VK", case, 2, "Суточное водопотребление", ("жилая часть", "встроенные", "полив"))
        ]
    # PT: the same flow in two units, the jets x single-jet flow product, the ВПВ + АУПТ sum.
    factor = Decimal("3.6")
    litres = _line("PT", case, 1, "Подача основного")
    cubic = _line("PT", case, 2, "Насос пожарный основной")
    unit_tolerance = _half_unit(litres) * factor + Decimal("0.5")
    cubic_value = Decimal(_NUMBER.findall(cubic.split("подача")[1])[0])
    unit_ok = abs(_last_number(litres) * factor - cubic_value) <= unit_tolerance
    jets_line = _line("PT", case, 1, "Внутренний противопожарный водопровод:")
    jets, single, design = (Decimal(x.replace(",", ".")) for x in _NUMBER.findall(jets_line)[:3])
    product_ok = abs(jets * single - design) <= jets * Decimal("0.05") + Decimal("0.05")
    aupt = _line("PT", case, 2, "Расчётный расход АУПТ")
    total = _line("PT", case, 2, "Суммарный расход ВПВ и АУПТ")
    sum_ok = abs(design + _last_number(aupt) - _last_number(total)) <= Decimal("0.15")
    return [(unit_ok, litres), (product_ok, jets_line), (sum_ok, total)]


@pytest.mark.parametrize("code", CODES)
def test_the_positive_text_seeds_exactly_the_defects_the_reply_cites(code: str) -> None:
    facts = _facts(code, "positive")
    assert facts and all(not consistent for consistent, _ in facts), (
        f"{code}: every seeded relation of the positive text must be a disagreement beyond the tolerance"
    )
    observations = _observations(code, "positive")
    assert len(observations) == len(facts)
    for (_, carrier), observation in zip(facts, observations, strict=True):
        cited = [item["quote"] for item in observation["evidence"]]
        assert any(quote in carrier for quote in cited), (code, carrier, cited)


@pytest.mark.parametrize("code", CODES)
def test_the_negative_text_is_consistent_in_every_relation_the_prompt_checks(code: str) -> None:
    facts = _facts(code, "negative")
    assert facts and all(consistent for consistent, _ in facts), (code, facts)


#: Trap lines in both texts: the prompt says not to compare them, yet a naive sum or product
#: would flag them. (text, a Python expression over the figures that must NOT hold)
TRAPS: dict[str, tuple[tuple[int, str, Callable[[], bool]], ...]] = {
    "KM": ((3, "с учётом наплавленного металла — 6071,7 кг", lambda: Decimal("6071.7") not in {Decimal("5982.5"), Decimal("5892.5")}),),
    "OV": ((3, "1250 м³/ч (с учётом подсосов и потерь)", lambda: 1250 not in (300 + 450 + 200 + 150, 1200)),),
    "VK": (
        (2, "общий 4,20, в том числе холодной воды 3,10 и горячей воды 2,00",
         lambda: Decimal("3.10") + Decimal("2.00") != Decimal("4.20")),
    ),
    "PT": (
        (3, "расчётный расход — 6,1 л/с по результатам гидравлического расчёта",
         lambda: Decimal("2") * Decimal("2.6") != Decimal("6.1")),
        (3, "давление у пожарного крана по таблице гидравлического расчёта — 0,43 МПа",
         lambda: Decimal("45") != Decimal("0.43")),
    ),
}


@pytest.mark.parametrize(("code", "case"), CASE_IDS)
def test_every_trap_is_in_the_text_and_a_naive_calculation_would_flag_it(code: str, case: str) -> None:
    for page, fragment, naive_flags in TRAPS[code]:
        assert fragment in _page_text(code, case, page), (code, case, fragment)
        assert naive_flags(), (code, fragment, "the trap would not even tempt a naive sum")


# --- replay through the real stage ---------------------------------------------------------------


def _stage(code: str, case: str, directory: Path):
    return run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=_layer(code, case),
        adapter=RecordedAdapter(directory),
        profile=REGISTRY.entries[code].profile,
        config=ProviderConfig(
            mode=ProviderMode.RECORDED, model_id=MODEL_ID, run_cost_ceiling_usd=1.00,
            api_key=None, ceiling_is_explicit=True,
        ),
    )


@pytest.mark.parametrize(("code", "case"), CASE_IDS)
def test_each_recording_replays_through_the_stage_with_every_quote_grounded(code: str, case: str) -> None:
    expected = _observations(code, case)
    outcome = _stage(code, case, WIDEN / code.lower())
    assert outcome.status == STATUS_SUCCEEDED, outcome.error
    artifact = outcome.artifact
    assert artifact["provider_mode"] == "recorded"
    assert artifact["analysis_profile_id"] == REGISTRY.entries[code].analysis_profile_id
    assert outcome.metrics["request_sha256"] == _request(code, case).request_sha256
    assert outcome.metrics["observations_proposed"] == len(expected)
    assert outcome.metrics["observations_emitted"] == len(expected)
    assert outcome.metrics["evidence_unresolved"] == 0
    assert outcome.metrics["observations_dropped_unresolved"] == 0
    assert len(artifact["observations"]) == len(expected)
    if case == "positive":
        for item in expected:
            for evidence in item["evidence"]:
                assert evidence["quote"] in _page_text(code, case, evidence["page_number"])


@pytest.mark.parametrize("code", CODES)
def test_a_reply_with_an_altered_quote_loses_its_observation(code: str, tmp_path: Path) -> None:
    """The grounding assertion above can fail: change one digit of the first quote of a copy."""
    path = _recording_path(code, "positive")
    document = json.loads(path.read_text(encoding="utf-8"))
    output = json.loads(document["output_text"])
    quote = output["observations"][0]["evidence"][0]["quote"]
    altered = quote.replace(next(ch for ch in quote if ch.isdigit()), "9", 1)
    assert altered != quote
    output["observations"][0]["evidence"][0]["quote"] = altered
    document["output_text"] = json.dumps(output, ensure_ascii=False)
    copy = tmp_path / code.lower()
    copy.mkdir()
    (copy / path.name).write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    outcome = _stage(code, "positive", copy)
    assert outcome.status == STATUS_SUCCEEDED
    assert (
        outcome.metrics["evidence_unresolved"] > 0
        or outcome.metrics["observations_dropped_unresolved"] > 0
        or outcome.metrics["observations_emitted"] < len(output["observations"])
    )


def test_the_served_adapter_does_not_search_this_directory() -> None:
    """The lane's files must not change what a served stack can answer or the 14-directory pin."""
    served = RecordedAdapter()
    assert served.recording_dirs
    assert all(WIDEN not in directory.parents and directory != WIDEN for directory in served.recording_dirs)
