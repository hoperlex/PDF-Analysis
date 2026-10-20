"""The Russian words the Excel workbook shows for contract enum values.

`XLSX-RU-LABELS-01`. The screens print severity, finding category and decision verdict in
Russian and keep the contract value in a data attribute. The workbook is read by the same
people, so it prints the same words; the contract value stays where it is an identity.

**One source for the workbook.** The writer takes every label from the three tables here
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

#: ``FindingCategory``: the twelve sealed categories, in the contract's order.
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
})

#: ``Verdict``: the expert's current decision on a finding, in the contract's order.
VERDICT_LABELS: Final[Mapping[str, str]] = MappingProxyType({
    "pending": "не решено",
    "accepted": "принято",
    "rejected": "отклонено",
    "needs_manual_review": "нужен ручной разбор",
})


def label(table: Mapping[str, str], value: str, *, refusal: str) -> str:
    """The table's Russian label for ``value``, or ``ValueError(refusal)`` for any other.

    ``value`` must be an exact member: no case folding, no trimming.
    """
    if not isinstance(value, str) or value not in table:
        raise ValueError(refusal)
    return table[value]


__all__ = ["CATEGORY_LABELS", "SEVERITY_LABELS", "VERDICT_LABELS", "label"]
