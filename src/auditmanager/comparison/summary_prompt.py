"""The request of the comparison summary: one prompt over one bounded input (`COMPARE-PERSISTED-SUMMARY-01`, B2).

The model sees **only** the changed lines of the approved pairs, as ``summary_input`` projected them
after rechecking the raw evidence seal, each changed span under its identity
(``<sheet_link_id>:<n>``, defined once in :func:`~auditmanager.comparison.approved_evidence.hunk_id`).
It answers in one closed shape -- statements, each citing the spans it is about -- and the
validator (:mod:`~auditmanager.comparison.summary_validation`) holds every cited span to the input.
The summary therefore *refers to* the raw differences and can neither add one nor change one.

Nothing time-varying, random or identity-bearing of a request enters the body: two requests for the
same input have byte-identical bodies and so the same ``request_sha256``, which is what keys a
recording. A prompt edit changes the key (and ``PROMPT_VERSION`` must move with it), a different
input changes the key, so a stale recording is reported missing and never replayed against a
question it does not answer.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.comparison.approved_evidence import hunk_id
from auditmanager.comparison.summary_input import VersionSummaryInput

PROMPT_VERSION: Final[str] = "comparison-summary-v1"
MAX_STATEMENTS: Final[int] = 20
MAX_STATEMENT_CHARACTERS: Final[int] = 1_000
MAX_HUNKS_PER_STATEMENT: Final[int] = 50

SYSTEM_PROMPT: Final[str] = (
    "Ты помогаешь эксперту сверить две версии одного комплекта чертежей. Тебе даны только "
    "изменившиеся строки текста подтверждённых экспертом пар листов. Каждое изменение имеет "
    "идентификатор hunk_id; в строках «до» указан текст более ранней версии, в строках «после» "
    "текст более поздней.\n"
    "Коротко опиши, что изменилось. Правила:\n"
    "1. Пиши только то, что прямо видно в строках «до» и «после». Не делай выводов о причинах, "
    "последствиях, нормах и допустимости изменений, не оценивай их.\n"
    "2. Каждое утверждение должно называть в hunk_ids те изменения, на которые оно опирается. "
    "Используй только идентификаторы из входных данных; не придумывай идентификаторы.\n"
    "3. Не повторяй строки целиком, если достаточно назвать, что изменилось.\n"
    "4. Ответь одним JSON-объектом по схеме. Кроме него в ответе ничего не должно быть."
)

RESPONSE_SCHEMA: Final[Mapping[str, Any]] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["statements"],
    "properties": {
        "statements": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_STATEMENTS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "hunk_ids"],
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": MAX_STATEMENT_CHARACTERS},
                    "hunk_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_HUNKS_PER_STATEMENT,
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}


def canonical_json(payload: Any) -> str:
    """One canonical serialization for every checksum here (sorted keys, no whitespace, Unicode kept)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class SummaryRequest:
    """Exactly the body that goes to the model, plus its checksum and the identities it may cite."""

    body: Mapping[str, Any]
    input_sha256: str
    #: Every span identity of the input, in order. The validator's whole world.
    hunk_ids: tuple[str, ...]

    @property
    def request_sha256(self) -> str:
        return hashlib.sha256(canonical_json(self.body).encode("utf-8")).hexdigest()


def input_hunk_ids(summary_input: VersionSummaryInput) -> tuple[str, ...]:
    return tuple(
        hunk_id(sheet.sheet_link_id, ordinal)
        for sheet in summary_input.sheets
        for ordinal in range(len(sheet.changes))
    )


def build_request(summary_input: VersionSummaryInput) -> SummaryRequest:
    """The one request this command makes for a bounded input."""
    sheets = [
        {
            "sheet_link_id": sheet.sheet_link_id,
            "source_page_number": sheet.source_page_number,
            "target_page_number": sheet.target_page_number,
            "changes": [
                {
                    "hunk_id": hunk_id(sheet.sheet_link_id, ordinal),
                    "tag": change.tag,
                    "before": list(change.source_lines),
                    "after": list(change.target_lines),
                }
                for ordinal, change in enumerate(sheet.changes)
            ],
        }
        for sheet in summary_input.sheets
    ]
    body: dict[str, Any] = {
        "prompt_version": PROMPT_VERSION,
        "instructions": SYSTEM_PROMPT,
        "response_schema": RESPONSE_SCHEMA,
        "input_sha256": summary_input.input_sha256,
        "raw_seal_sha256": summary_input.raw_seal_sha256,
        "sheets": sheets,
    }
    return SummaryRequest(body, summary_input.input_sha256, input_hunk_ids(summary_input))


__all__ = [
    "MAX_HUNKS_PER_STATEMENT", "MAX_STATEMENTS", "MAX_STATEMENT_CHARACTERS", "PROMPT_VERSION",
    "RESPONSE_SCHEMA", "SYSTEM_PROMPT", "SummaryRequest", "build_request", "canonical_json",
    "input_hunk_ids",
]
