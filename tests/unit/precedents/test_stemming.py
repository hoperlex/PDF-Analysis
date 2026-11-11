"""`plan-v5` 2.4: stop words match by word stem, with a small deterministic stemmer and no dependency."""

from __future__ import annotations

import pytest

from auditmanager.precedents.stemming import compile_stop_words, stem, stems, tokens

FAMILIES = [
    ("стена", "стены", "стене", "стену", "стеной", "стенами", "стен"),
    ("арматура", "арматуры", "арматуре", "арматуру", "арматурой", "арматурами"),
    ("бетон", "бетона", "бетону", "бетоном", "бетоне", "бетонов"),
    ("нормативный", "нормативного", "нормативному", "нормативным", "нормативные", "нормативных"),
    ("требование", "требования", "требованию", "требованием", "требованиям", "требованиями"),
    ("конструкция", "конструкции", "конструкцию", "конструкцией", "конструкций"),
    ("пожарный", "пожарного", "пожарным", "пожарные", "пожарных"),
]


@pytest.mark.parametrize("family", FAMILIES)
def test_the_inflected_forms_of_a_word_meet_in_one_stem(family):
    assert len({stem(form) for form in family}) == 1


def test_different_words_do_not_meet():
    assert len({stem("стена"), stem("стойка"), stem("арматура"), stem("бетон")}) == 4


def test_case_and_the_letter_yo_do_not_matter_and_the_stem_is_stable():
    assert stem("ЕЛКА") == stem("ёлка") == stem("елка") == "елк"
    assert [stem("Железобетонные"), stem("железобетонных")] == ["железобетон", "железобетон"]
    assert stem("требования") == "требован"


def test_a_word_that_is_not_cyrillic_is_left_alone_casefolded():
    assert stem("СП") == "сп" and stem("A500") == "a500" and stem("13130") == "13130" and stem("смесь2") == "смесь2"


def test_a_word_with_no_vowel_or_nothing_after_the_first_vowel_is_not_cut():
    assert stem("в") == "в" and stem("шва") == "шва" and stem("") == ""


def test_tokens_split_on_anything_but_letters_and_digits():
    assert tokens("СП 4.13130.2013, п. 5.2—«Стены»") == ("сп", "4", "13130", "2013", "п", "5", "2", "стены")
    assert stems("стенами и арматурой") == ("стен", "и", "арматур")


def test_a_stop_word_matches_another_case_of_the_word():
    matcher = compile_stop_words(["стена"])
    for text in ("Стены не соответствуют", "в стене", "со стенами", "стен"):
        assert matcher.matches(text) == ("стена",), text
    assert matcher.matches("стойка и ригель") == ()


def test_a_stop_phrase_matches_consecutive_stems_only_inside_one_text():
    matcher = compile_stop_words(["пожарный отсек"])
    assert matcher.matches("Границы пожарных отсеков не указаны") == ("пожарный отсек",)
    assert matcher.matches("отсек пожарный") == ()  # order matters
    assert matcher.matches("пожарный шкаф и отсек") == ()  # not consecutive
    assert matcher.matches("Нет пожарный", "отсек") == ()  # a phrase never spans two texts


def test_a_designation_with_digits_matches_as_words():
    matcher = compile_stop_words(["СП 4.13130"])
    assert matcher.matches("Согласно СП 4.13130.2013 требуется") == ("СП 4.13130",)
    assert matcher.matches("СП 5.13130") == ()


def test_matches_come_back_as_the_owner_wrote_them_in_list_order_without_duplicates():
    matcher = compile_stop_words(["  арматура ", "Бетон", "арматуры"])
    assert matcher.matches("бетоном и арматурой") == ("арматура", "Бетон")


def test_a_blank_stop_word_is_refused_not_dropped():
    for bad in ("", "   ", "—,.", "«»"):
        with pytest.raises(ValueError):
            compile_stop_words(["арматура", bad])
