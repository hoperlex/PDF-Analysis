"""The 15-section catalogue suggests but never confirms a discipline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.sections import suggest_sections


CATALOGUE = Path(__file__).resolve().parents[3] / "src/auditmanager/sections/suggestion_patterns.json"
EXPECTED_CODES = {
    "AI", "AR", "EOM", "GP", "ITP", "KJ", "KM", "OV", "PB", "POS",
    "PS", "PT", "SS", "TX", "VK",
}


def test_all_fifteen_sections_have_distinct_codes_and_names() -> None:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = data["sections"]
    assert data["legacy_registry_sha256"] == (
        "0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970"
    )
    assert {item["code"] for item in entries} == EXPECTED_CODES
    assert len({item["name"] for item in entries}) == 15
    assert {item["code"]: item["name"] for item in entries}["PS"] == "Пояснительная записка"
    assert {item["code"]: item["name"] for item in entries}["PB"] == "Пожарная безопасность"
    assert sum(item["source"] == "legacy" for item in entries) == 14


@pytest.mark.parametrize(
    ("filename", "code"),
    [
        ("01-АР-Планы.pdf", "AR"), ("Интерьер_АИ_том.zip", "AI"),
        ("Том_ПС_общие_данные.pdf", "PS"), ("Раздел-ПБ.pdf", "PB"),
        ("Раздел_ПОС.zip", "POS"), ("02-ЭОМ.zip", "EOM"),
        ("КЖ-армирование.pdf", "KJ"), ("ИТП.pdf", "ITP"),
    ],
)
def test_filename_patterns_cover_sections_without_auto_confirmation(
    filename: str, code: str
) -> None:
    result = suggest_sections(filename, "")
    assert result[0].code == code
    assert result[0].filename_patterns
    assert not hasattr(result[0], "confirmed")


def test_text_keywords_and_exact_name_can_rank_a_section() -> None:
    result = suggest_sections(
        "комплект.zip", "Однолинейная схема; ВРУ; ГРЩ; кабель ВВГ; заземление"
    )
    assert result[0].code == "EOM"
    assert result[0].score == 4
    assert len(result[0].text_keywords) >= 4
    assert suggest_sections("комплект.zip", "Пояснительная записка")[0].code == "PS"
    assert suggest_sections("комплект.zip", "Пожарная безопасность")[0].code == "PB"


def test_ambiguous_and_neutral_inputs_do_not_choose_a_section() -> None:
    assert suggest_sections("комплект.zip", "нейтральный текст") == ()
    tied = suggest_sections("АР-КЖ.zip", "")
    assert [item.code for item in tied] == ["AR", "KJ"]
    assert tied[0].score == tied[1].score


def test_short_codes_do_not_match_inside_longer_words() -> None:
    assert suggest_sections("ПАРКИНГ.zip", "") == ()
    assert suggest_sections("SUPERPOSITIVE.pdf", "") == ()
    assert suggest_sections("Раздел_ПБ.pdf", "") != suggest_sections("Раздел_ПС.pdf", "")


def test_invalid_input_is_refused_and_repetition_is_stable() -> None:
    with pytest.raises(TypeError):
        suggest_sections(None, "")  # type: ignore[arg-type]
    first = suggest_sections("АР.zip", "фасад и разрез")
    assert first == suggest_sections("АР.zip", "фасад и разрез")
