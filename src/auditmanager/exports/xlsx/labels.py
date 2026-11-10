"""The Russian words the Excel workbook shows for contract enum values.

`XLSX-RU-LABELS-01`. The screens print severity, finding category and decision verdict in
Russian and keep the contract value in a data attribute. The workbook is read by the same
people, so it prints the same words; the contract value stays where it is an identity.

**One source for the workbook.** The writer takes every label from the tables here
and from nowhere else. Each table is the Python image of one web table and is held equal to
it by ``tests/unit/exports/test_xlsx_labels_lockstep.py``, which reads the ``.ts`` and
``.tsx`` sources as text:

=====================  ===================================================================
table                  web source (exported name)
=====================  ===================================================================
``SEVERITY_LABELS``    ``web/src/entities/finding/model/severity-labels.ts``
                       (``SEVERITY_LABELS``)
``CATEGORY_LABELS``    ``web/src/entities/expert-decision/model/category-labels.ts``
                       (``CATEGORY_LABELS``)
``VERDICT_LABELS``     ``web/src/entities/expert-decision/ui/verdict-badge.tsx``
                       (``VERDICT_LABELS``)
=====================  ===================================================================

A relabel on a screen without the same change here fails that test; a value the contract
adds without a label here fails it too. The key order of each table is the contract's value
order, which is the order the writer's summary lists severities in.

``SOURCE_LABELS`` is the fourth table and has no web twin yet: it is the three words of the column
«Источник» that only a workbook of a ``one_list`` run has (`F8-COUNT-XLSX`), and ``source_of`` is the one
place that says which of them a finding gets. The screens' chip «Источник» (`F8-WEB`) must print the same words.

**No fallback.** :func:`label` raises for a value the table does not hold. A workbook that
printed the raw value, or a blank, for a value nobody labelled would be exactly the English
cell this module exists to remove, only quieter.

Identifiers (project, version, run, profile, snapshot) are not labelled and never pass
through here; free text (finding text, recommendation, comment, citations, page labels) is
written verbatim.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

#: ``Severity``: the closed AR v2/v3 vocabulary, in the contract's order.
SEVERITY_LABELS: Final[Mapping[str, str]] = MappingProxyType({
    "critical": "Критическое",
    "economic": "Экономическое",
    "operational": "Эксплуатационное",
    "recommendation": "Рекомендация",
    "check_adjacent": "Проверить смежный раздел",
})

#: ``FindingCategory``: the fourteen sealed categories, in the contract's order (contract 1.51.0 added the last two, which only a
#: ``one_list`` run publishes: a candidate of the drawing, and a candidate that stands on more than one source).
CATEGORY_LABELS: Final[Mapping[str, str]] = MappingProxyType({
    "internal_contradiction": "Внутреннее противоречие",
    "explicit_placeholder": "Явный пропуск",
    "dimensions": "Размеры помещений",
    "layout": "Планировочные решения",
    "facade": "Фасадные решения",
    "roof": "Кровля",
    "documentation": "Документация",
    "evacuation": "Эвакуация",
    "fire_safety": "Пожарная безопасность",
    "accessibility": "Доступность",
    "insulation": "Теплоизоляция",
    "sound": "Звукоизоляция",
    "drawing_discrepancy": "Расхождение на чертеже",
    "cross_source": "Расхождение источников",
})

#: ``Verdict``: the expert's current decision on a finding, in the contract's order.
VERDICT_LABELS: Final[Mapping[str, str]] = MappingProxyType({
    "pending": "не решено",
    "accepted": "принято",
    "rejected": "отклонено",
    "needs_manual_review": "нужен ручной разбор",
})


#: ``SourceKey``: where a finding of a ``one_list`` run stands, as the column «Источник» says it: the text of the document, a block of
#: the drawing, or a cross-check of more than one source. Not a contract enum: it is derived (:func:`source_of`).
SOURCE_LABELS: Final[Mapping[str, str]] = MappingProxyType({
    "text": "Текст",
    "drawing": "Чертёж",
    "cross_check": "Сверка",
})

#: ``finding_observation.grounding_kind`` (``ck_finding_observation_grounding_kind``): how an observation is grounded.
GROUNDING_TEXT_SPAN: Final[str] = "text_span"
GROUNDING_PORTAL_BLOCK: Final[str] = "portal_block"


def source_of(category: str, grounding_kind: str) -> str:
    """The key of :data:`SOURCE_LABELS` for a finding: its category and the grounding of its canonical observation.

    * ``cross_source`` (a group that stands on a block and on another source) is a **cross-check**, whatever grounds its observations;
    * otherwise a block-grounded observation, or the category ``drawing_discrepancy``, is the **drawing**;
    * otherwise a text-grounded observation is the **text**.

    A ``grounding_kind`` outside the two the database allows is refused, never read as text: a source nobody named would be a quiet
    claim that the finding stands on the document's text.
    """
    if grounding_kind not in (GROUNDING_TEXT_SPAN, GROUNDING_PORTAL_BLOCK):
        raise ValueError("xlsx_grounding_kind_invalid")
    if category == "cross_source":
        return "cross_check"
    if category == "drawing_discrepancy" or grounding_kind == GROUNDING_PORTAL_BLOCK:
        return "drawing"
    return "text"


def label(table: Mapping[str, str], value: str, *, refusal: str) -> str:
    """The table's Russian label for ``value``, or ``ValueError(refusal)`` for any other.

    ``value`` must be an exact member: no case folding, no trimming.
    """
    if not isinstance(value, str) or value not in table:
        raise ValueError(refusal)
    return table[value]


__all__ = [
    "CATEGORY_LABELS",
    "GROUNDING_PORTAL_BLOCK",
    "GROUNDING_TEXT_SPAN",
    "SEVERITY_LABELS",
    "SOURCE_LABELS",
    "VERDICT_LABELS",
    "label",
    "source_of",
]
