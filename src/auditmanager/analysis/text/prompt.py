"""The AR text-consistency prompt bundle. Immutable, content-hashed, narrow.

This is a **new** prompt written for exactly one product question. It is not a port of
the legacy AR prompt tree, and it must not grow into one: every sentence below either
states the question, closes off a way of answering a different question, or fixes the
shape of the reply.

``PROTOTYPE_PROFILE.md`` section 7.1 states the only question PC-01 answers:

    Does the text state conflicting values or claims about the same project attribute
    in different places, or leave an explicit placeholder that requires expert
    attention?

Two categories, no third. The stage does not decide compliance with external norms,
does not infer facts from drawings, and does not claim that a missing statement was
legally required. **The model never writes a verdict** - it proposes observations that
a human accepts or rejects, and nothing in this package sets an expert decision.

``OD-05`` fixes the language split, and the schema below enforces it structurally:
``finding_text`` and ``recommendation_text`` are Russian prose for a Russian reviewer;
``category`` is a closed ASCII enum, and every other machine field is ASCII.

The bundle is immutable and content-hashed. Editing any string in this module changes
``content_sha256`` and therefore changes every request checksum, which invalidates
every committed recording. That is the intended coupling: a prompt change is a new
recording, not a silently different run under the same evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final, Mapping

from auditmanager.analysis.text.textlayer import TextLayer
from auditmanager.shared.identity import PromptBundleId

#: The two categories, exactly as ``P02_SEAMS.md`` section 4.7 and the analysis
#: contract spell them. ASCII, closed, and the same tuple the schema is built from.
CATEGORIES: Final[tuple[str, ...]] = ("internal_contradiction", "explicit_placeholder")

#: Pinned identity of this bundle. An immutable bundle has a fixed identity resolved
#: at run time, not a fresh ULID per run - a new ULID each run would make the artifact
#: unreproducible and would make "resolved by identity" meaningless.
PROMPT_BUNDLE_ID: Final[PromptBundleId] = PromptBundleId.parse("pb_01M25P3TH0PDQYVKTRQFEM0CYS")

SYSTEM_PROMPT: Final[str] = """\
Ты — инструмент проверки внутренней согласованности текста одного раздела проектной
документации «Архитектурные решения» (АР) на русском языке.

Тебе передан ТОЛЬКО текстовый слой документа, постранично. Чертежей, внешних норм и
других разделов у тебя нет, и обращаться к ним нельзя.

ЕДИНСТВЕННЫЙ вопрос, на который ты отвечаешь:
указывает ли текст противоречащие друг другу значения или утверждения об ОДНОМ И ТОМ ЖЕ
признаке ОДНОГО И ТОГО ЖЕ объекта в разных местах документа, либо оставлен ли в нём явный
незаполненный заполнитель, требующий решения эксперта?

Ровно две категории, третьей нет:
- internal_contradiction — два или более места документа приписывают одному и тому же
  признаку одного и того же объекта несовместимые значения;
- explicit_placeholder — на месте проектного решения буквально оставлена отметка о
  незаполненности: «уточнить», «уточняется», «TBD», «XX», «___», «(?)» и подобное.

Прежде чем сообщить находку, проверь каждое из пяти условий. Если выполняется хотя бы
одно — находки нет:
1. Разные объекты. Значения относятся к разным зданиям, сооружениям, этажам, частям
   здания, помещениям или конструкциям. Это не противоречие, даже если признак называется
   одинаково. Ищи в тексте прямое указание на то, к чему относится значение.
2. Разные признаки. Похожие названия — не один признак. Прежде чем сравнивать значения,
   убедись, что это буквально одна и та же характеристика.
3. Совпадающие значения. Повторение одного и того же значения в разных разделах — это
   согласованность, а не расхождение.
4. Решение приведено в другом месте. Ссылка на таблицу, ведомость, раздел или том, где
   значение приведено, — это принятое решение, а не заполнитель, даже если формулировка
   содержит корень «уточн».
5. Утверждения просто нет. Если документ ничего не говорит о чём-то — это не находка.
   Ты не решаешь, что должно было быть указано.

Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, техническим регламентам),
НЕ делаешь выводов из чертежей и НЕ утверждаешь, что отсутствующее указание требовалось.
Ты не выносишь вердикт: принять или отклонить наблюдение решает эксперт.

Требования к ответу:
- finding_text и recommendation_text — по-русски, кратко, одно-два предложения, без
  вердикта и без ссылок на нормы. finding_text называет признак и суть расхождения;
  recommendation_text предлагает, что согласовать или определить.
- category — строго одно из двух значений выше.
- evidence — одна или несколько цитат. Для internal_contradiction приведи по цитате для
  КАЖДОГО расходящегося значения. Для explicit_placeholder — цитату с самим заполнителем.
- quote — дословная выдержка из текста страницы, скопированная посимвольно. Не исправляй
  опечатки, не меняй пробелы, не сокращай, не добавляй кавычек и не переставляй слов.
  Цитата должна буквально встречаться на указанной странице.
- page_number — номер страницы, на которой цитата действительно напечатана.
- Если находок нет, верни пустой список observations. Пустой ответ — нормальный результат.\
"""

USER_PREAMBLE: Final[str] = (
    "Текстовый слой документа, {page_count} стр. Проанализируй его целиком и ответь "
    "по схеме."
)

#: The page banner is prompt scaffolding for the model's benefit only. Offsets are
#: never computed against this rendered string - they are computed against the text
#: layer in :mod:`auditmanager.analysis.text.anchors`, whose sequence has no
#: separator between pages at all.
PAGE_BANNER: Final[str] = "=== Страница {page_number} ==="

#: Schema-constrained output. The model returns page and quotation and nothing about
#: offsets: it cannot compute them reliably, so it is not asked to, and asking would
#: invite a plausible wrong number in place of an absent one.
RESPONSE_SCHEMA: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "finding_text": {"type": "string"},
                    "recommendation_text": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "page_number": {"type": "integer"},
                                "quote": {"type": "string"},
                            },
                            "required": ["page_number", "quote"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["category", "finding_text", "recommendation_text", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["observations"],
    "additionalProperties": False,
}

#: Generation parameters. No sampling parameter appears: ``temperature``, ``top_p``
#: and ``top_k`` are removed on the pinned model family and are rejected with a 400.
#: Adaptive thinking is on because the five exclusion conditions above are exactly the
#: kind of discrimination that a non-reasoning pass gets wrong on near-misses.
MAX_OUTPUT_TOKENS: Final[int] = 16_000
EFFORT: Final[str] = "high"
THINKING: Final[Mapping[str, Any]] = {"type": "adaptive"}


def render_document(text_layer: TextLayer) -> str:
    """The document as the model sees it: page banners plus page text.

    This rendering exists only to let the model cite a page. Nothing downstream
    measures an offset against it.
    """
    parts = [USER_PREAMBLE.format(page_count=len(text_layer.pages)), ""]
    for page in text_layer.pages:
        parts.append(PAGE_BANNER.format(page_number=page.page_number))
        parts.append(page.text)
        parts.append("")
    return "\n".join(parts)


def canonical_json(payload: Any) -> str:
    """One canonical serialization, used for every checksum in this package.

    ``sort_keys`` and a fixed separator make the encoding independent of dict order;
    ``ensure_ascii=False`` keeps Russian text as itself rather than as escapes, so the
    checksum is stable against a JSON writer that decides differently.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class PromptBundle:
    """An immutable prompt bundle, resolved by identity and verified by content."""

    prompt_bundle_id: PromptBundleId
    system_prompt: str
    response_schema: Mapping[str, Any]
    max_output_tokens: int
    effort: str
    thinking: Mapping[str, Any]

    @property
    def content_sha256(self) -> str:
        """Hash of everything that shapes a request except the document itself."""
        return hashlib.sha256(
            canonical_json(
                {
                    "system_prompt": self.system_prompt,
                    "response_schema": self.response_schema,
                    "max_output_tokens": self.max_output_tokens,
                    "effort": self.effort,
                    "thinking": self.thinking,
                    "user_preamble": USER_PREAMBLE,
                    "page_banner": PAGE_BANNER,
                }
            ).encode("utf-8")
        ).hexdigest()


AR_TEXT_PROMPT_BUNDLE: Final[PromptBundle] = PromptBundle(
    prompt_bundle_id=PROMPT_BUNDLE_ID,
    system_prompt=SYSTEM_PROMPT,
    response_schema=RESPONSE_SCHEMA,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    effort=EFFORT,
    thinking=THINKING,
)
