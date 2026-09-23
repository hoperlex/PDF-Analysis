"""`D-59`: the check that tells the norm's text from the recognition model talking about it.

Every degenerate fixture here is the **opening of a real block in the drop**, shortened but
not reworded, with the document and page named beside it. A guard built from invented text
would prove that the guard matches the guard's author.

The clean fixtures matter as much. The corpus is Cyrillic with real Latin in it — ISO
citations, LaTeX fragments, chemical formulae, the `КонсультантПлюс` stamps — and a check
that reddens on those would be unusable on the 706 predominantly-Latin paragraphs `W33-CORPUS`
measured across 201 documents.
"""

from __future__ import annotations

import pytest

from auditmanager.norms import DegeneracySignal, inspect, is_degenerate

#: `СП_63.13330.2018` page 15, 55 670 characters. The recognition prompt read back as content.
INSTRUCTION_ECHO_BLOCK = (
    "The user wants me to act as a strict transcription engine for Russian construction "
    "documents, specifically extracting text from a PDF page. I must adhere to the following "
    "rules: 1. Extract only visible text and table content. path 2. Return clean safe HTML "
    "only 613. Do not output any formatting 438."
)

#: `ГОСТ_33259-2015` page 27, 62 359 characters — the longest paragraph in the whole corpus.
FIRST_PERSON_BLOCK = (
    "The user wants me to transcribe a table from a technical document. The table lists "
    "flange specifications for different pipe diameters (DN) and pressure ratings (PN). "
    "I will extract the text from the image, ensuring it is accurate and follows the "
    "structure of the original document."
)

#: `СП_28.13330.2017` page 73, 50 989 characters, 1 % Cyrillic — and **no first-person
#: pronoun anywhere in it**, which is why `D-59`'s grep for `The user wants me to …` never
#: saw it. It is the second-longest block in the corpus and it is pure narration.
PAGE_NARRATION_BLOCK = (
    "The document is a technical table from a Russian engineering standard "
    "(СП 28.13330.2017) regarding the protection of reinforced concrete structures against "
    "corrosion. The table details requirements for reinforcement classes A400, A500, Bp500, "
    "and B500 under different initial stress conditions."
)

#: `СП_163.1325800.2014` page 5, 14 924 characters. Not the model at all — the pipeline's own
#: JSON envelope, written into the body where the page's text belongs.
SERIALISED_PAYLOAD_BLOCK = (
    '[{"text": "\\"СП 47.13330.2016. Свод правил. Инженерные изыскания для строительства. '
    'Основные положения\\"", "text": "Документ предоставлен КонсультантПлюс"}]'
)

#: `ГОСТ_00000-2026`-shaped: a real clause with the export's stamps around it.
CLEAN_RUSSIAN_BLOCK = (
    '"ГОСТ 33259-2015. Межгосударственный стандарт. Фланцы арматуры..."\n\n'
    "Документ предоставлен **КонсультантПлюс**\n\n"
    "##### 1. ОБЩИЕ ПОЛОЖЕНИЯ\n\n"
    "1.1. Настоящий стандарт распространяется на изделия, применяемые в строительстве, "
    "и устанавливает требования к их приёмке.\n\n"
    "Страница 27 из 93"
)

#: Legitimately Latin: an ISO citation list and a LaTeX fragment, both of which the corpus
#: really carries and neither of which is a recognition artefact.
CLEAN_LATIN_IN_A_NORM = (
    "7.2.4 Значения коэффициента \\psi при \\omega определяют по формуле "
    "\\frac{A_{f,min}}{A_{f,max}}\n\n"
    "[12] ISO 5167-2:2003, Measurement of fluid flow by means of pressure differential "
    "devices inserted in circular cross-section conduits running full — Part 2: Orifice "
    "plates\n\n"
    "[13] IEC 60947-2:2016, Low-voltage switchgear and controlgear"
)


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        pytest.param(INSTRUCTION_ECHO_BLOCK, DegeneracySignal.INSTRUCTION_ECHO, id="instruction-echo"),
        pytest.param(FIRST_PERSON_BLOCK, DegeneracySignal.FIRST_PERSON_PLAN, id="first-person-plan"),
        pytest.param(PAGE_NARRATION_BLOCK, DegeneracySignal.PAGE_NARRATION, id="page-narration"),
        pytest.param(
            SERIALISED_PAYLOAD_BLOCK, DegeneracySignal.SERIALISED_PAYLOAD, id="serialised-payload"
        ),
    ],
)
def test_every_shape_the_drop_carries_is_found(block: str, expected: DegeneracySignal) -> None:
    verdict = inspect(block)
    assert verdict.is_degenerate, verdict.describe()
    assert expected in verdict.signals


def test_the_narration_family_is_not_reachable_by_the_first_person_family() -> None:
    """The two are independent, and that independence is the whole reason `D-59` undercounts.

    `D-59` was found by grepping `The user wants me to …`. The three largest narration blocks
    in the corpus — 50 989, 38 436 and 37 199 characters — contain no first-person pronoun at
    all, so that grep could not see them and the row's population is short by them.
    """
    verdict = inspect(PAGE_NARRATION_BLOCK)
    assert DegeneracySignal.PAGE_NARRATION in verdict.signals
    assert DegeneracySignal.FIRST_PERSON_PLAN not in verdict.signals
    assert "the user wants me to" not in PAGE_NARRATION_BLOCK.casefold()


@pytest.mark.parametrize(
    "block",
    [
        pytest.param(CLEAN_RUSSIAN_BLOCK, id="a-clause-with-its-stamps"),
        pytest.param(CLEAN_LATIN_IN_A_NORM, id="latex-and-iso-citations"),
        pytest.param("", id="an-empty-block"),
    ],
)
def test_the_norms_own_text_is_left_alone(block: str) -> None:
    verdict = inspect(block)
    assert not verdict.is_degenerate, verdict.describe()
    assert verdict.describe() == "clean"


def test_the_verdict_carries_the_phrase_it_was_reached_by() -> None:
    """A bare boolean cannot be argued with, and a second degenerate result has to be read."""
    verdict = inspect(FIRST_PERSON_BLOCK)
    assert verdict.evidence
    assert all(phrase in FIRST_PERSON_BLOCK.casefold() for phrase in verdict.evidence)
    assert len(verdict.evidence) == len(verdict.signals)


def test_the_check_is_case_folded_because_the_drop_is_not_consistent() -> None:
    assert is_degenerate("THE USER WANTS ME TO TRANSCRIBE A TABLE")
    assert is_degenerate("the user wants me to transcribe a table")


def test_two_inspections_of_one_string_give_one_verdict() -> None:
    """Signals come back in family order, not in order of occurrence, so the value compares."""
    both = FIRST_PERSON_BLOCK + "\n\n" + PAGE_NARRATION_BLOCK
    reversed_order = PAGE_NARRATION_BLOCK + "\n\n" + FIRST_PERSON_BLOCK
    assert inspect(both).signals == inspect(reversed_order).signals
    assert inspect(both) == inspect(both)
