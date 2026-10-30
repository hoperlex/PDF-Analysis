"""The vocabulary of the AI description of sheet changes (`CMP-VC-AISHEET-01`).

Nothing here reads a database or calls a model. The numbers that come from the original (`23f379fd`) carry their file and line;
the others are this lane's and say so.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "AI_STATES",
    "CHANGE_STATES",
    "DISCLAIMER",
    "DESCRIPTION_STATES",
    "ELIGIBLE_STATUSES",
    "IMAGE_MAX_PX",
    "ITEM_STATES",
    "KIND_PAIR",
    "KIND_SINGLE",
    "LABEL_ADDED",
    "LABEL_REMOVED",
    "MAX_CONTEXT_REQUESTS",
    "MAX_EXTRA_IMAGES",
    "MAX_LAUNCHES",
    "MAX_OUTPUT_TOKENS",
    "METHOD",
    "RECORDED_NOTICE",
    "SINGLE_DISCLAIMER",
    "SINGLE_STATUSES",
    "SINGLE_TEXT_LIMIT",
    "STATE_LABELS",
    "TIERS",
    "TIER_IMAGE",
    "TIER_TEXT",
    "TIER_UNVERIFIED",
    "WORK_KIND",
]

METHOD: Final[str] = "sheet_changes"
#: The executor work kind (``ExecutorWorkKind``) the job's calls are routed under, and the kind of its work items.
WORK_KIND: Final[str] = "comparison_sheet_changes"

#: The statuses of a sheet pair that are described as a pair: the engine found a difference of content or could not decide
#: (``jobs.py:119`` ``SC_SKIP_STATUSES`` = ``same``, ``same_zones_changed`` are not sent; ``needs_review`` is).
ELIGIBLE_STATUSES: Final[tuple[str, ...]] = ("different", "needs_review")
#: A sheet that exists in one version only is described on its own (``single.py:1-8``).
SINGLE_STATUSES: Final[tuple[str, ...]] = ("added", "removed")
KIND_PAIR: Final[str] = "pair"
KIND_SINGLE: Final[str] = "single"
LABEL_ADDED: Final[str] = "Лист добавлен"  # single.py:28
LABEL_REMOVED: Final[str] = "Лист удалён"

#: Launches of the model for one sheet, the free waits aside (``run.py:33``): the main call, one technical retry, one context
#: request and one pass over the unreviewed candidates, at most three in all.
MAX_LAUNCHES: Final[int] = 3
MAX_CONTEXT_REQUESTS: Final[int] = 6  # run.py:34
MAX_EXTRA_IMAGES: Final[int] = 6  # run.py:35
#: The long side of a crop or an overview, in pixels (``pack.py:37``).
IMAGE_MAX_PX: Final[int] = 1950
#: ``max_tokens`` of a request, and so the output the estimate prices per call. `[own design]`: the original runs through a
#: subscription and has no ceiling; a ceiling is what an estimate in USD needs.
MAX_OUTPUT_TOKENS: Final[int] = 8192
#: The text layer of a single sheet that the model reads (``single.py:26``).
SINGLE_TEXT_LIMIT: Final[int] = 6000

#: The states of a stored description (the CHECK of ``comparison_sheet_description``) -- ``validate.py:244-254`` ``state_of``.
DESCRIPTION_STATES: Final[tuple[str, ...]] = ("done", "needs_clarification", "partial", "no_construction_changes")
#: The states of ``comparison_ai_sheet_item``.
ITEM_STATES: Final[tuple[str, ...]] = ("queued", "running", "done", "failed", "cancelled", "skipped")
#: The eleven states of «Изменения в листе» (the contract's ``ComparisonAiSheetState``): the four of a stored description, and
#: the ones that are derived when it is read.
AI_STATES: Final[tuple[str, ...]] = (
    "not_processed", "queued", "running", "done", "needs_clarification", "partial", "no_construction_changes", "stale",
    "failed", "cancelled", "engine_same",
)
#: ``validate.py:257-263`` ``STATE_LABELS``.
STATE_LABELS: Final[dict[str, str]] = {
    "not_processed": "Не обработано", "queued": "В очереди", "running": "В обработке", "done": "Готово",
    "needs_clarification": "Требуется уточнение", "partial": "Частично",
    "no_construction_changes": "Строительных изменений не выявлено", "stale": "Описание устарело", "failed": "Ошибка",
    "cancelled": "Отменено", "engine_same": "По данным сравнения изменений нет",
}
#: The states that count a sheet as having changes to read (the «Изм.» column): a description with at least one change.
CHANGE_STATES: Final[tuple[str, ...]] = ("done", "needs_clarification", "partial")

#: How a value of a change was checked by the program (the contract's ``ComparisonAiTier``; ``validate.py:6-9``).
TIER_TEXT: Final[str] = "from_text"
TIER_IMAGE: Final[str] = "from_image"
TIER_UNVERIFIED: Final[str] = "unverified"
TIERS: Final[tuple[str, ...]] = (TIER_TEXT, TIER_IMAGE, TIER_UNVERIFIED)

#: ``report.py:306``; the label every AI text carries («не подтверждено инженером», ADR-0025 decision 16).
DISCLAIMER: Final[str] = "Описание составлено ИИ по исходным листам двух версий и инженером не подтверждено."
#: ``single.py:192``.
SINGLE_DISCLAIMER: Final[str] = "Описание составлено ИИ по исходному листу и инженером не подтверждено."
#: Our counterpart of «ТЕСТОВЫЙ ОТВЕТ подменного исполнителя» (plan section 1.1): a recorded answer is labelled as such.
RECORDED_NOTICE: Final[str] = "Записанный (тестовый) ответ: описание составлено не моделью."
