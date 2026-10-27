"""SECTION-JUDGE-FIXES-01 finding 2: the presence test sees the spellings the judge listed.

``occurs`` answers «may the term be in these texts?» and the omission check publishes only when the answer is
no, so every spelling it misses is a false «не найдена» that an expert would read as fact. The judge's list of
spellings a Russian drawing set really contains, where the term (as the model copies it from the naming quote)
and the schedule's text (as the extractor reads it) differ only in how the same designation is written:

* Latin letters that look like Cyrillic ones (``ВК-1`` and ``BK-1``, ``ВРУ-1`` and ``BPY-1``, ``х`` and ``x``);
* the decimal comma and the decimal point (``3х2,5`` and ``3х2.5``), the multiplication sign;
* the separators of a mark: hyphen, dots, spaces, line breaks, table-cell bars (``Г-3`` and ``Г.3``);
* the diameter sign (``Ø20``, ``⌀20``, ``∅20`` and ``Ф20``);
* combining marks and zero-width characters inside a mark;
* the Roman numeral and its look-alikes in a mark (``ЩО-I``, ``ЩО-l``, ``ЩО-І``, ``ЩО-Ⅰ`` and ``ЩО-1``);
* a mark broken across two table cells with only whitespace or a bar between them.

The rule is the check's own: **presence wins**. Folding only ever makes two strings more alike, so it can only
turn a would-be absence into a presence. The negative controls below keep the fold from collapsing everything:
different digits, different letters and different marks stay different.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.text.anchors import resolve_anchor
from auditmanager.analysis.text.omission import decide, fold, occurs, quotes_of
from auditmanager.analysis.text.prompt import CATEGORIES, OMISSION_CATEGORY
from auditmanager.analysis.text.response import parse_response
from auditmanager.analysis.text.textlayer import load_text_layer

LOOKALIKES = [
    ("А", "A"), ("В", "B"), ("Е", "E"), ("К", "K"), ("М", "M"), ("Н", "H"),
    ("О", "O"), ("Р", "P"), ("С", "C"), ("Т", "T"), ("Х", "X"), ("У", "Y"),
    ("а", "a"), ("в", "b"), ("е", "e"), ("к", "k"), ("м", "m"), ("н", "h"),
    ("о", "o"), ("р", "p"), ("с", "c"), ("т", "t"), ("х", "x"), ("у", "y"),
]

#: ``(usual spelling, another spelling of the same designation, what differs)``. Each row is tried in both
#: directions: the term may be the odd spelling and the schedule the usual one, or the other way round.
SPELLINGS = [
    ("ВК-1", "BK-1", "Latin B and K for Cyrillic В and К"),
    ("ВРУ-1", "BPY-1", "Latin B, P, Y for Cyrillic В, Р, У"),
    ("3х2,5", "3x2,5", "Latin x for Cyrillic х"),
    ("3х2,5", "3х2.5", "decimal point for decimal comma"),
    ("3х2,5", "3×2,5", "multiplication sign for х"),
    ("3х2,5", "3*2,5", "asterisk for х"),
    ("3х2,5", "3X2.5", "capital Latin X and a point"),
    ("Г-3", "Г.3", "a point for the hyphen"),
    ("Г-3", "Г–3", "an en dash for the hyphen"),
    ("Г-3", "Г 3", "a space for the hyphen"),
    ("Г-3", "Г,3", "a comma for the hyphen"),
    ("Г-3", "Г_3", "an underscore for the hyphen"),
    ("Г-3", "Г/3", "a slash for the hyphen"),
    ("Ø20", "Ф20", "Cyrillic Ф for the diameter sign"),
    ("Ø20", "⌀20", "the diameter sign U+2300"),
    ("Ø20", "∅20", "the empty-set sign for the diameter sign"),
    ("Ø20", "Φ20", "Greek Φ for the diameter sign"),
    ("Ф20", "ø20", "lower-case ø for Ф"),
    ("ЩО-1", "Щ\u0301О-1", "a combining accent on Щ"),
    ("ЩО-1", "ЩО\u0301-1", "a combining accent on О"),
    ("ЩО-1", "ЩО-1\u0301", "a combining accent on the digit"),
    ("ЩО-1", "ЩО-I", "Latin capital I for 1"),
    ("ЩО-1", "ЩО-l", "Latin small l for 1"),
    ("ЩО-1", "ЩО-І", "Cyrillic Ukrainian І for 1"),
    ("ЩО-1", "ЩО-Ⅰ", "Roman numeral one U+2160 for 1"),
    ("ЩО-1", "ЩО\u200b-1", "a zero-width space inside"),
    ("ЩО-1", "Щ\ufeffО-1", "a zero-width no-break space inside"),
    ("ВК-1", "ＢＫ－１", "full-width forms"),
    ("ВК-1", "ВК\u00a0-\u00a01", "non-breaking spaces round the hyphen"),
    ("ВК-1", "вк-1", "lower case"),
    ("ВК-1", "В\u0301К-1", "a combining accent on В"),
    ("Подъёмник", "Подъемник", "ё read as е"),
    ("ВК-1", "ВК\n1", "a line break in place of the hyphen (the two cells of a column)"),
    ("ВК-1", "ВК | -1", "a table-cell bar between the two cells"),
    ("ВК-1", "ВК\t-1", "a tab between the two cells"),
    ("ВК-1", "ВК-\n1", "a hyphenated line break"),
    ("ВК-1", "ВК-\n\n\n 1", "several blank lines between the two cells"),
]

#: Different designations stay different: the fold must not turn everything into a presence.
DIFFERENT = [
    ("ВК-1", "ВК-2"),
    ("ВК-1", "ВР-1"),
    ("ВК-1", "КВ-1"),
    ("ВРУ-1", "ВРУ-2"),
    ("3х2,5", "3х4"),
    ("3х2,5", "3х1,5"),
    ("3х2,5", "5х2,5"),
    ("Г-3", "Г-4"),
    ("Г-3", "Д-3"),
    ("Ø20", "Ф25"),
    ("Ø20", "Ø32"),
    ("ЩО-1", "ЩО-2"),
    ("ЩО-1", "ЩР-1"),
    ("ЩО-1", "ЩО-3"),
    ("Подъёмник", "Подъездник"),
]


def sentence(designation: str) -> str:
    return f"Позиция {designation} Кран шаровой, 1 шт."


@pytest.mark.parametrize(("usual", "odd", "why"), SPELLINGS, ids=[row[2] for row in SPELLINGS])
def test_every_listed_spelling_is_a_presence_in_both_directions(usual: str, odd: str, why: str) -> None:
    assert occurs(usual, [sentence(odd)]), f"{why}: the term in its usual spelling, the schedule in the odd one"
    assert occurs(odd, [sentence(usual)]), f"{why}: the term in the odd spelling, the schedule in the usual one"


@pytest.mark.parametrize(("cyrillic", "latin"), LOOKALIKES, ids=[f"{c}/{l}" for c, l in LOOKALIKES])
def test_each_latin_lookalike_of_a_cyrillic_letter_reads_as_the_cyrillic_one(cyrillic: str, latin: str) -> None:
    assert fold(cyrillic) == fold(latin)
    assert occurs(f"{cyrillic}Ж-12", [f"марка {latin}Ж-12 позиция"])
    assert occurs(f"{latin}Ж-12", [f"марка {cyrillic}Ж-12 позиция"])


@pytest.mark.parametrize(("term", "other"), DIFFERENT, ids=[f"{t} vs {o}" for t, o in DIFFERENT])
def test_different_designations_stay_different(term: str, other: str) -> None:
    assert not occurs(term, [sentence(other)])
    assert not occurs(other, [sentence(term)])


def test_decimal_comma_and_point_are_one_number_only_between_digits() -> None:
    assert fold("2,5") == fold("2.5")
    assert fold("а,б") != fold("а.б"), "outside digits a comma is a comma"


def test_a_spelling_the_fold_reaches_publishes_nothing_through_decide() -> None:
    """The stage-level consequence: the schedule writes the mark with Latin letters, so no «не найдена» is said."""
    plan = "Схема. Кран ВК-1 на вводе, ВК-2 на выпуске. Давление 0,6 МПа."
    schedule = "Спецификация\nПоз. 1 Кран BK-1 шаровой, 2 шт.\nПоз. 2 Кран ВК-3 шаровой, 1 шт."
    body = json.dumps(
        {
            "observations": [
                {
                    "category": "documentation", "finding_text": "ВК-1 названа на схеме и не найдена в спецификации.",
                    "recommendation_text": "Сверить.", "evidence": [{"page_number": 1, "quote": "Кран ВК-1 на вводе"}],
                    "omission": {
                        "term": "ВК-1", "first_page": 2, "last_page": 2,
                        "heading": {"page_number": 2, "quote": "Спецификация"},
                    },
                }
            ]
        },
        ensure_ascii=False,
    )
    pages = [plan, schedule]
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    layer: Any = load_text_layer(
        {
            "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_x",
            "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out,
        }
    )
    (proposal,) = parse_response(body, truncated=False, categories=(*CATEGORIES, OMISSION_CATEGORY)).observations
    anchors = [resolve_anchor(layer, page_number=item.page_number, quote=item.quote) for item in quotes_of(proposal)]
    assert decide(layer, proposal, anchors, None).reason == "term_present_in_range"
    clean = schedule.replace("BK-1", "ВК-4")
    layer2 = load_text_layer(
        {
            "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_x",
            "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": len(plan) + len(clean),
            "pages": [
                {"page_number": 1, "char_start": 0, "char_end": len(plan), "text": plan},
                {"page_number": 2, "char_start": len(plan), "char_end": len(plan) + len(clean), "text": clean},
            ],
        }
    )
    anchors2 = [resolve_anchor(layer2, page_number=item.page_number, quote=item.quote) for item in quotes_of(proposal)]
    assert decide(layer2, proposal, anchors2, None).published
