"""The question to the model and the check of its answer (the original's ``_prompt``, ``ANSWER_SCHEMA`` and ``ask``).

``build_prompt`` is a port of ``sheet_match.py:171-202`` (the Russian text is the original's, its pilot-tested wording, with one
paragraph changed: this port prints no caption band on the pictures -- a labelled copy would be a blob that no table owns and
nothing can delete, ADR-0025 decision 9 -- so the paragraph that sent the model to «the caption printed above each picture»
now names the pictures by their order; see the report). ``validate_answer`` is the strict validator of ADR-0025 decision 3: the
reply must be exactly the schema, a candidate number is a number of the list shown, the reason is cut to the contract's 300
characters, anything else is *no answer* and is never stored.

A request is built **only** here, so the digest that the recorded-mode tests and the content key of an answer rest on has one
author: ``build_request``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.analysis.public import ModelRequest
from auditmanager.comparison.ai_pairs.model import (
    ANSWER_CONFIDENCES,
    ANSWER_REASON_MAX,
    MAX_OUTPUT_TOKENS,
    Answer,
    PageFacts,
)

__all__ = [
    "ANSWER_SCHEMA",
    "EFFORT",
    "SYSTEM_PROMPT",
    "THINKING",
    "build_prompt",
    "build_request",
    "crop_ids",
    "validate_answer",
]

#: ``sheet_match.py:46-49``: ``choice`` (a candidate number, 0 for none), ``page`` (that candidate's page, 0 for none),
#: ``confidence`` and ``reason``.
ANSWER_SCHEMA: Final[Mapping[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["choice", "page", "confidence", "reason"],
    "properties": {
        "choice": {"type": "integer"},
        "page": {"type": "integer"},
        "confidence": {"type": "string", "enum": list(ANSWER_CONFIDENCES)},
        "reason": {"type": "string"},
    },
}
#: The pull and the HTTP transports need a system text; the original puts everything into one message
#: (``describer.run(DescribeTask(prompt=...))``), so the system text only names the format of the reply.
SYSTEM_PROMPT: Final[str] = "Отвечай только JSON-объектом по заданной схеме, без пояснений вне его."
#: ``settings.py:261`` effort ``high``; adaptive thinking as every text stage of this product (``analysis/text/prompt.py``).
EFFORT: Final[str] = "high"
THINKING: Final[Mapping[str, Any]] = {"type": "adaptive"}


def _line(version_label: str, facts: PageFacts, page_count: int) -> str:
    """``line`` of ``sheet_match.py:173-179``: where the page stands in its version and what its stamp says."""
    text = f"версия «{version_label}», стр. {facts.page_number} из {page_count}"
    if facts.sheet_number:
        text += f", номер листа в штампе «{facts.sheet_number}»"
    if facts.title:
        text += f", название в штампе «{facts.title}»"
    return text


def build_prompt(
    *, code: str, a_label: str, a_facts: PageFacts, a_page_count: int, b_label: str,
    candidates: Sequence[PageFacts], b_page_count: int, back: bool,
) -> str:
    """The text of one question: sheet A against the candidates of the other version (``sheet_match.py:171-202``).
    ``back`` is the reverse question («the candidates of the PREVIOUS version»)."""
    lines = [f"Изображение 1 — лист A: {_line(a_label, a_facts, a_page_count)}."]
    for number, candidate in enumerate(candidates, 1):
        lines.append(f"Изображение {number + 1} — кандидат {number}: {_line(b_label, candidate, b_page_count)}.")
    goal = (
        "Нужно найти, какой из кандидатов ПРЕДЫДУЩЕЙ версии — ЭТО ЖЕ лист, что лист A (его прежняя редакция).\n" if back
        else "Нужно найти, какой из кандидатов следующей версии — ЭТО ЖЕ лист, что лист A (его новая редакция).\n"
    )
    head = "Ты сверяешь две версии одного комплекта рабочей документации" + (f" (шифр {code})" if code else "") + ".\n"
    return (
        head + goal +
        "Новая редакция может отличаться содержанием — изменения нормальны, но это тот же лист: тот же план/фасад/разрез/"
        "схема/таблица того же объекта (этаж, оси, корпус, щит, система, раздел).\n"
        "Одинаковое оформление и похожая сетка — ещё не тот же лист: соседние этажи, другие щиты, другие разделы спецификации "
        "— разные листы. Для таблиц, где строки сдвинулись между листами, выбери кандидата, на котором продолжаются те же "
        "строки/позиции, что на листе A. Учитывай номер листа и название в штампе, надписи и заголовки на чертеже "
        "(если текста в PDF нет — читай с картинки), положение страницы в документе.\n"
        "Шифр комплекта и наименование объекта в штампе могут смениться между версиями (комплект переобозначили, в штамп "
        "попал чужой шаблон) — это не довод против: сравнивай сам чертёж/таблицу и номер листа. Название листа тоже может "
        "уточниться (например, план переименовали), если сам план/схема — тот же (контур, оси, расстановка). Если надпись внутри "
        "листа противоречит штампу, назови противоречие в reason.\n"
        # The original's paragraph («над каждой картинкой крупно впечатано …») refers to a caption band this port does not print.
        "Картинки идут строго в порядке списка ниже: изображение 1 — лист A, изображение n+1 — кандидат n. Номер кандидата "
        "бери ТОЛЬКО из этого порядка и из строки «кандидат n» списка, а не из надписей на самих чертежах.\n"
        "Если ни один кандидат не является тем же листом — ответ 0.\n\n" + "\n".join(lines) +
        "\n\nОтветь JSON: choice — номер кандидата (1…" + str(len(candidates)) + ") или 0; "
        "page — номер страницы выбранного кандидата («стр. N» из его строки выше) или 0; "
        "confidence — high/medium/low; reason — коротко по-русски, по каким признакам (не длиннее 300 знаков)."
    )


def crop_ids(candidate_count: int) -> tuple[str, ...]:
    """The opaque crop references of a request, in the order the model sees the pictures: ``sheet-a``, ``cand-1`` … (echoed by
    the transports, never parsed -- ADR-0025 decision 18)."""
    return ("sheet-a", *(f"cand-{number}" for number in range(1, candidate_count + 1)))


def build_request(*, model_id: str, prompt: str) -> ModelRequest:
    """The request without its pictures (``executors.public.attach_images`` adds them): the same Anthropic-shaped body every
    text stage of the product builds, so every channel reads it the way it reads the others."""
    body: dict[str, Any] = {
        "model": model_id,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": dict(THINKING),
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": dict(ANSWER_SCHEMA)}},
    }
    return ModelRequest(model_id=model_id, body=body)


def validate_answer(output_text: str, cands: Sequence[int]) -> Answer:
    """The model's reply as an :class:`~auditmanager.comparison.ai_pairs.model.Answer`, or an unusable one (``ok`` false).

    Exactly the four members of :data:`ANSWER_SCHEMA` with their types; ``confidence`` one of the three words; a ``choice``
    that is a candidate number or 0 (anything else is not a reading of the list that was shown); the reason is trimmed and cut
    to 300 characters. A ``choice`` and a ``page`` that disagree are *kept* -- the rule drops them as ``answer_mismatch``
    (``sheet_match.py:313-314``) -- because that is an answer, a wrong one, which must not be asked for again."""
    try:
        document = json.loads(output_text)
    except (TypeError, ValueError):
        return Answer(ok=False)
    if not isinstance(document, dict) or set(document) != {"choice", "page", "confidence", "reason"}:
        return Answer(ok=False)
    choice, page, confidence, reason = (document[k] for k in ("choice", "page", "confidence", "reason"))
    if type(choice) is not int or type(page) is not int or not isinstance(reason, str):
        return Answer(ok=False)
    if confidence not in ANSWER_CONFIDENCES or not 0 <= choice <= len(cands) or page < 0:
        return Answer(ok=False)
    return Answer(
        ok=True, choice=choice, page=page, confidence=confidence, reason=" ".join(reason.split())[:ANSWER_REASON_MAX],
        cands=tuple(int(n) for n in cands),
    )
