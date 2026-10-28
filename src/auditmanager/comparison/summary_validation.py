"""The validator of a summary reply (`COMPARE-PERSISTED-SUMMARY-01`, B2).

A reply is accepted only if it is the closed shape ``{"statements": [...]}`` with between one and
twenty statements, each a text of one to a thousand characters and between one and fifty distinct
``hunk_ids``, **every one of which names a span of the input**, and no other key anywhere. One
unknown reference rejects the whole reply: nothing is repaired, dropped or guessed, because a
summary that cites a change which is not there is exactly the kind of statement a reviewer cannot
check. The statements are kept as the model wrote them and the references as the model cited them;
the validator reads, it never rewrites.

The rejection is a value (:class:`SummaryRejected` with one closed ``reason``), not a failure of the
command: the reply was paid for, so the rejection is recorded; it is shown as «ответ отклонён»
and the raw differences stay exactly as they were.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from dataclasses import dataclass
from typing import Final

from auditmanager.comparison.summary_prompt import (
    MAX_HUNKS_PER_STATEMENT,
    MAX_STATEMENT_CHARACTERS,
    MAX_STATEMENTS,
)

#: The closed vocabulary of rejection reasons; the table's CHECK and the contract restate it.
REASON_NOT_JSON: Final[str] = "reply_not_json"
REASON_SHAPE: Final[str] = "reply_shape_invalid"
REASON_UNKNOWN_HUNK: Final[str] = "unknown_hunk_reference"
REJECTION_REASONS: Final[tuple[str, ...]] = (REASON_NOT_JSON, REASON_SHAPE, REASON_UNKNOWN_HUNK)


class SummaryRejected(ValueError):
    """The reply cannot be a summary of this input. ``reason`` is one of :data:`REJECTION_REASONS`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Statement:
    text: str
    hunk_ids: tuple[str, ...]


def parse_reply(output_text: str, valid_hunk_ids: Collection[str]) -> tuple[Statement, ...]:
    """The statements of an accepted reply, or :class:`SummaryRejected`."""
    try:
        document = json.loads(output_text)
    except (TypeError, ValueError):
        raise SummaryRejected(REASON_NOT_JSON) from None
    if not isinstance(document, dict) or set(document) != {"statements"}:
        raise SummaryRejected(REASON_SHAPE)
    raw = document["statements"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_STATEMENTS:
        raise SummaryRejected(REASON_SHAPE)
    known = frozenset(valid_hunk_ids)
    statements: list[Statement] = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"text", "hunk_ids"}:
            raise SummaryRejected(REASON_SHAPE)
        text, ids = item["text"], item["hunk_ids"]
        if (
            not isinstance(text, str)
            or not 1 <= len(text) <= MAX_STATEMENT_CHARACTERS
            or text != text.strip()
            or not isinstance(ids, list)
            or not 1 <= len(ids) <= MAX_HUNKS_PER_STATEMENT
            or any(not isinstance(value, str) for value in ids)
            or len(set(ids)) != len(ids)
        ):
            raise SummaryRejected(REASON_SHAPE)
        statements.append(Statement(text, tuple(ids)))
    for statement in statements:
        if any(identity not in known for identity in statement.hunk_ids):
            raise SummaryRejected(REASON_UNKNOWN_HUNK)
    return tuple(statements)


def statements_json(statements: tuple[Statement, ...]) -> list[dict[str, object]]:
    """The stored form: a list of ``{"text", "hunk_ids"}``."""
    return [{"text": s.text, "hunk_ids": list(s.hunk_ids)} for s in statements]


__all__ = [
    "REASON_NOT_JSON", "REASON_SHAPE", "REASON_UNKNOWN_HUNK", "REJECTION_REASONS", "Statement",
    "SummaryRejected", "parse_reply", "statements_json",
]
