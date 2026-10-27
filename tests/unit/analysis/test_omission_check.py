"""SECTION-CATEGORY-OCR-01 (`R-146ao`): the absence check, the claim parser and the per-profile schema.

The check (:func:`auditmanager.analysis.text.omission.decide`) is pure: it takes the saved text layer, a
parsed proposal, the resolutions of its quotes and the pages the model was shown, and answers published or
one reason of a closed vocabulary. These cases cover each reason with a text that triggers it and a
neighbouring text that does not, so a check that stopped checking would turn one of them red. The same
guards are shown failing against the real stage in
``tests/integration/sections/test_section_omission_specimens.py``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor, resolve_anchor
from auditmanager.analysis.text.omission import (
    OMISSION_REASONS,
    TERM_MAX_CHARACTERS,
    USABLE_PAGE_CHARACTERS,
    OmissionTally,
    decide,
    fold,
    note_for,
    occurs,
    quotes_of,
)
from auditmanager.analysis.text.profile_registry import (
    PACKAGE_FORMAT_CATEGORIES,
    TextProfileLoadError,
    load_text_profile_registry,
)
from auditmanager.analysis.text.prompt import (
    CATEGORIES,
    OMISSION_CATEGORY,
    RESPONSE_SCHEMA,
    response_schema_for,
)
from auditmanager.analysis.text.response import parse_response
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.ingest.envelope import TEXTLESS_PAGE_CHARACTERS

PLAN = "План. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000."
SCHEDULE = "Ведомость дверных заполнений\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д-2 Дверь межкомнатная, 6 шт."
CATEGORIES3 = (*CATEGORIES, OMISSION_CATEGORY)


def layer(*pages: str) -> Any:
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    return load_text_layer(
        {
            "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_x",
            "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out,
        }
    )


def reply(**claim: Any) -> str:
    omission = {
        "term": "Д-5", "first_page": 2, "last_page": 2,
        "heading": {"page_number": 2, "quote": "Ведомость дверных заполнений"},
    }
    omission.update(claim)
    return json.dumps(
        {
            "observations": [
                {
                    "category": "documentation", "finding_text": "Марка Д-5 названа на плане и не найдена в ведомости.",
                    "recommendation_text": "Сверить.", "evidence": [{"page_number": 1, "quote": "Дверь Д-5 в санузел"}],
                    "omission": omission,
                }
            ]
        },
        ensure_ascii=False,
    )


def check(text_layer: Any, body: str, *, visible: tuple[int, int] | None = None) -> Any:
    (proposal,) = parse_response(body, truncated=False, categories=CATEGORIES3).observations
    anchors = [
        resolve_anchor(text_layer, page_number=item.page_number, quote=item.quote) for item in quotes_of(proposal)
    ]
    return decide(text_layer, proposal, anchors, visible)


# --- the check: published, and each reason with its neighbour ------------------------------------


def test_a_term_named_once_and_absent_from_the_range_is_published_with_both_places() -> None:
    outcome = check(layer(PLAN, SCHEDULE), reply())
    assert outcome.published and outcome.reason is None
    assert [(a.page_number, a.quote) for a in outcome.evidence] == [
        (1, "Дверь Д-5 в санузел"), (2, "Ведомость дверных заполнений"),
    ]
    assert outcome.finding_text.endswith(note_for("Д-5", 2, 2))
    assert outcome.finding_text.startswith("Марка Д-5 названа на плане")


def test_the_sentence_says_what_was_verified_and_what_was_not() -> None:
    assert note_for("Д-5", 2, 2) == (
        "Проверка программой: запись «Д-5» не найдена в текстовом слое на странице 2; "
        "сравнение без учёта регистра, тире, пробелов и сходных по начертанию букв; "
        "другие написания не проверялись."
    )
    assert "на страницах 2–4" in note_for("Д-5", 2, 4)


@pytest.mark.parametrize(
    ("variant", "why"),
    [
        ("Марка Д-5 Дверь в санузел, 1 шт.", "the same spelling"),
        ("Марка д-5 Дверь в санузел, 1 шт.", "another case"),
        ("Марка Д–5 Дверь в санузел, 1 шт.", "an en dash"),
        ("Марка Д—5 Дверь в санузел, 1 шт.", "an em dash"),
        ("Марка Д‑‑5 Дверь в санузел, 1 шт.", "non-breaking hyphens"),
        ("Марка Д­-5 Дверь в санузел, 1 шт.", "a soft hyphen"),
        ("Марка Д-\n5 Дверь в санузел, 1 шт.", "a line break after the hyphen"),
        ("Марка Д 5 Дверь в санузел, 1 шт.", "spaces instead of the hyphen"),
        ("Марка Д5 Дверь в санузел, 1 шт.", "no hyphen"),
        ("Марка Д-5 Дверь в санузел, 1 шт.".replace("Д-5", "Д - 5"), "non-breaking spaces"),
    ],
)
def test_every_way_a_record_can_hide_is_a_presence(variant: str, why: str) -> None:
    text_layer = layer(PLAN, SCHEDULE + "\n" + variant)
    outcome = check(text_layer, reply())
    assert outcome.reason == "term_present_in_range", why


def test_yo_reads_as_ye_and_compatibility_forms_fold() -> None:
    assert fold("Подъёмник") == fold("подъемник") == "подъемник"
    assert fold("ﬁlter") == fold("filter") != "ﬁlter"  # a ligature (the fold also reads Latin look-alikes)
    assert occurs("Подъёмник", ["Список: подъемник, 1 шт."])


def test_a_term_split_by_a_page_break_is_a_presence() -> None:
    outcome = check(layer(PLAN, SCHEDULE + "\nМарка Д-", "5 Дверь в санузел, 1 шт., и ещё достаточно текста на странице."), reply(last_page=3))
    assert outcome.reason == "term_present_in_range"


def test_the_term_outside_the_range_is_no_presence_in_the_range_but_is_on_a_page_the_model_saw() -> None:
    """Before `SECTION-JUDGE-FIXES-01` this case was «published, page 3 is not in the range 2-2»: the judge's defect."""
    outcome = check(layer(PLAN, SCHEDULE, "Марка Д-5 Дверь в санузел, 1 шт. Достаточно длинная страница после ведомости."), reply())
    assert outcome.reason == "term_on_other_visible_page", "page 3 is not in the range 2-2, but the model saw it"
    outcome = check(
        layer(PLAN, SCHEDULE, "Марка Д-5 Дверь в санузел, 1 шт. Достаточно длинная страница после ведомости."),
        reply(last_page=3),
    )
    assert outcome.reason == "term_present_in_range"


def test_a_page_of_the_range_without_usable_text_proves_nothing() -> None:
    short = "Лист 3"
    assert len(short) < USABLE_PAGE_CHARACTERS
    outcome = check(layer(PLAN, SCHEDULE, short), reply(last_page=3))
    assert outcome.reason == "range_page_without_text"
    just_enough = "Продолжение ведомости: марка Д-1, марка Д-2, марка Д-3, марка Д-4."
    assert len(just_enough.strip()) >= USABLE_PAGE_CHARACTERS
    assert check(layer(PLAN, SCHEDULE, just_enough), reply(last_page=3)).published


def test_the_usable_page_threshold_is_the_products_text_less_threshold() -> None:
    assert USABLE_PAGE_CHARACTERS == TEXTLESS_PAGE_CHARACTERS


def test_the_term_must_be_in_a_naming_quote() -> None:
    outcome = check(layer(PLAN, SCHEDULE), reply(term="Д-9"))
    assert outcome.reason == "term_not_in_naming_quote"


def test_the_heading_must_lie_inside_the_range() -> None:
    body = reply(
        first_page=2, last_page=3, heading={"page_number": 1, "quote": "План. Помещение 4"},
    )
    outcome = check(layer(PLAN, SCHEDULE, "Продолжение ведомости: марка Д-1, марка Д-2, марка Д-3, марка Д-4."), body)
    assert outcome.reason == "heading_outside_range"


def test_a_quote_that_does_not_resolve_drops_the_pair() -> None:
    assert check(layer(PLAN, SCHEDULE), reply(heading={"page_number": 2, "quote": "Ведомость дверных ЗАПОЛНЕНИЙ"})).reason == "evidence_unresolved"
    body = json.loads(reply())
    body["observations"][0]["evidence"][0]["quote"] = "Дверь Д-5 в кухне"
    assert check(layer(PLAN, SCHEDULE), json.dumps(body, ensure_ascii=False)).reason == "evidence_unresolved"
    # on the wrong page
    assert check(layer(PLAN, SCHEDULE), reply(heading={"page_number": 1, "quote": "Ведомость дверных заполнений"})).reason in {
        "heading_outside_range", "evidence_unresolved",
    }


@pytest.mark.parametrize(
    "claim",
    [
        {"term": "Д"}, {"term": "--"}, {"term": "ab"}, {"term": "Д-" + "5" * TERM_MAX_CHARACTERS},
        {"term": "Д-5 Д-5 Д-5 Д-5 Д-5 Д-5"},
        {"first_page": 3, "last_page": 2}, {"first_page": 0}, {"last_page": 9},
    ],
)
def test_a_claim_that_is_not_well_formed_is_dropped(claim: dict[str, Any]) -> None:
    assert check(layer(PLAN, SCHEDULE), reply(**claim)).reason == "claim_invalid"


def test_in_a_windowed_run_the_range_must_lie_inside_the_window() -> None:
    text_layer = layer(PLAN, SCHEDULE, "Продолжение ведомости: марка Д-1, марка Д-2, марка Д-3, марка Д-4.")
    assert check(text_layer, reply(last_page=3), visible=(1, 3)).published
    assert check(text_layer, reply(last_page=3), visible=(1, 2)).reason == "range_outside_window"
    assert check(text_layer, reply(), visible=(3, 3)).reason == "range_outside_window"


def test_a_claim_may_end_before_the_window_end_but_not_on_it_unless_it_is_the_last_window() -> None:
    """Before `SECTION-JUDGE-FIXES-01`: `reply()` (pages 2-2) with `visible=(1, 2)` of three pages was published."""
    text_layer = layer(PLAN, SCHEDULE, "Продолжение ведомости: марка Д-1, марка Д-2, марка Д-3, марка Д-4.")
    assert check(text_layer, reply(), visible=(1, 2)).reason == "range_reaches_window_end"
    assert check(text_layer, reply(), visible=(1, 3)).published, "page 2 ends before the window's last page"
    assert check(text_layer, reply(last_page=3), visible=(1, 3)).published, "the last window may end on the last page"


def test_the_reasons_are_the_closed_vocabulary_the_stage_counts() -> None:
    assert OMISSION_REASONS == (
        "claim_invalid", "range_outside_window", "range_reaches_window_end", "heading_outside_range",
        "evidence_unresolved", "term_not_in_naming_quote", "finding_text_overclaims", "range_page_textless",
        "range_page_without_text", "term_present_in_range", "term_on_other_visible_page",
        "term_in_recognised_text",
    )
    assert all(len(f"omissions_dropped_{reason}") <= 64 for reason in OMISSION_REASONS)
    tally = OmissionTally(enabled=True)
    assert tally.metrics()["omissions_proposed"] == 0
    assert set(tally.metrics()) == {
        "omissions_proposed", "omissions_published", "omissions_dropped",
        *(f"omissions_dropped_{reason}" for reason in OMISSION_REASONS),
    }
    assert OmissionTally(enabled=False).metrics() == {}


def test_unresolved_anchors_never_publish() -> None:
    text_layer = layer(PLAN, SCHEDULE)
    (proposal,) = parse_response(reply(), truncated=False, categories=CATEGORIES3).observations
    resolved = [resolve_anchor(text_layer, page_number=i.page_number, quote=i.quote) for i in quotes_of(proposal)]
    assert all(isinstance(a, ResolvedAnchor) for a in resolved)
    broken = [resolved[0], UnresolvedAnchor(2, "x", "quotation_absent")]
    assert decide(text_layer, proposal, broken, None).reason == "evidence_unresolved"
    with pytest.raises(ValueError):
        decide(text_layer, proposal, resolved[:1], None)


# --- the parser: the claim is part of the proposal -------------------------------------------------


def test_documentation_needs_a_well_formed_claim_and_nothing_else_may_carry_one() -> None:
    good = parse_response(reply(), truncated=False, categories=CATEGORIES3)
    assert good.malformed_count == 0 and good.observations[0].omission is not None
    for bad in (
        reply(term=""), reply(first_page="2"), reply(first_page=True),
        reply(heading={"page_number": 2}), reply(heading={"page_number": 2, "quote": ""}),
        reply(extra=1),
    ):
        parsed = parse_response(bad, truncated=False, categories=CATEGORIES3)
        assert parsed.observations == () and parsed.malformed_count == 1, bad
    body = json.loads(reply())
    del body["observations"][0]["omission"]
    missing = parse_response(json.dumps(body, ensure_ascii=False), truncated=False, categories=CATEGORIES3)
    assert missing.observations == () and missing.malformed_count == 1
    body = json.loads(reply())
    body["observations"][0]["category"] = "internal_contradiction"
    carried = parse_response(json.dumps(body, ensure_ascii=False), truncated=False, categories=CATEGORIES3)
    assert carried.observations == () and carried.malformed_count == 1


def test_a_two_category_profile_refuses_documentation_and_the_default_is_the_v1_pair() -> None:
    assert parse_response(reply(), truncated=False, categories=CATEGORIES).malformed_count == 1
    assert parse_response(reply(), truncated=False).malformed_count == 1  # no `categories`: the v1 pair


# --- the per-profile schema ------------------------------------------------------------------------


def test_the_v1_pair_gets_the_v1_schema_object_and_the_three_get_the_claim() -> None:
    assert response_schema_for(CATEGORIES) is RESPONSE_SCHEMA
    schema = response_schema_for(CATEGORIES3)
    item = schema["properties"]["observations"]["items"]
    assert item["properties"]["category"]["enum"] == list(CATEGORIES3)
    assert set(item["properties"]["omission"]["required"]) == {"term", "first_page", "last_page", "heading"}
    assert item["required"] == ["category", "finding_text", "recommendation_text", "evidence"], "the claim is optional"
    assert item["additionalProperties"] is False and item["properties"]["omission"]["additionalProperties"] is False
    assert "omission" not in RESPONSE_SCHEMA["properties"]["observations"]["items"]["properties"]
    assert RESPONSE_SCHEMA["properties"]["observations"]["items"]["properties"]["category"]["enum"] == list(CATEGORIES)
    for other in (("documentation",), (*CATEGORIES, "layout"), (OMISSION_CATEGORY, *CATEGORIES)):
        with pytest.raises(ValueError):
            response_schema_for(other)


def test_the_registry_serves_three_categories_to_exactly_the_five_and_two_to_the_rest() -> None:
    registry = load_text_profile_registry()
    five = {"AI", "TX", "EOM", "SS", "ITP"}
    for code, entry in registry.entries.items():
        profile = entry.profile
        if code in five:
            assert profile.categories == CATEGORIES3, code
            assert profile.prompt_bundle.response_schema == response_schema_for(CATEGORIES3), code
            assert profile.profile_version == "1.3.1", code
        else:
            assert profile.categories == CATEGORIES, code
            assert profile.prompt_bundle.response_schema is RESPONSE_SCHEMA, code
    assert len(registry.entries) == 14


def test_the_category_set_is_part_of_the_profile_and_the_bundle_identity() -> None:
    registry = load_text_profile_registry()
    ai = registry.entries["AI"].profile
    assert ai.content_sha256 != registry.entries["PS"].profile.content_sha256
    assert ai.prompt_bundle.content_sha256 != registry.entries["PS"].prompt_bundle_id


# --- the package format -----------------------------------------------------------------------------


def _package(root: Any, **overrides: Any) -> None:
    profile: dict[str, Any] = {
        "format": PACKAGE_FORMAT_CATEGORIES, "section_code": "KJ",
        "analysis_profile_id": "ap_01M5AXG1K82P9BCJ1NRYSTC2NA", "prompt_bundle_id": "pb_01M5AXG1K8EDTH597XY32Z696A",
        "profile_version": "1.0.0", "status": "draft", "categories": list(CATEGORIES3),
        "title_ru": "Синтетический раздел",
        "source": {"repository": "s", "commit": "0" * 40, "files": [{"path": "p.md", "sha256": "a" * 64}]},
    }
    profile.update(overrides)
    directory = root / "kj"
    directory.mkdir()
    (directory / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    (directory / "system_prompt.md").write_text("Ты — инструмент.\n", encoding="utf-8")


def test_a_format_2_package_declares_its_categories(tmp_path: Any) -> None:
    _package(tmp_path)
    entry = load_text_profile_registry(tmp_path).entries["KJ"]
    assert entry.profile.categories == CATEGORIES3


@pytest.mark.parametrize(
    "categories",
    [list(CATEGORIES), [OMISSION_CATEGORY], [*CATEGORIES, "layout"], [*CATEGORIES, OMISSION_CATEGORY, OMISSION_CATEGORY],
     [OMISSION_CATEGORY, *CATEGORIES], "documentation", None],
)
def test_a_format_2_package_may_declare_only_the_v1_pair_plus_the_omission_category(
    tmp_path: Any, categories: Any
) -> None:
    _package(tmp_path, categories=categories)
    with pytest.raises(TextProfileLoadError, match="categories_invalid"):
        load_text_profile_registry(tmp_path)


def test_the_key_set_follows_the_format(tmp_path: Any) -> None:
    (tmp_path / "x").mkdir()
    _package(tmp_path)
    profile = json.loads((tmp_path / "kj" / "profile.json").read_text("utf-8"))
    del profile["categories"]
    (tmp_path / "kj" / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "x").rmdir()
    with pytest.raises(TextProfileLoadError, match="profile_keys_invalid"):
        load_text_profile_registry(tmp_path)
    profile["format"] = "text-profile/1"
    profile["categories"] = list(CATEGORIES3)
    (tmp_path / "kj" / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(TextProfileLoadError, match="profile_keys_invalid"):
        load_text_profile_registry(tmp_path)
