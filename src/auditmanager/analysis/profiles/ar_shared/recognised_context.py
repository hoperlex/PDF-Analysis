"""Select W55b recognised text for AR v2's uncitable prompt context.

The source of truth for page selection is the version row's ``textless_pages``.
Portal IMAGE descriptions and recognised text on textful PDF pages never
become prompt input. None of these words can ground an evidence quote.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final, Mapping

from auditmanager.analysis.recognised.artifact import (
    KIND_PORTAL_DESCRIPTION,
    KIND_RECOGNISED_TEXT,
    QUOTE_SOURCE_RECOGNISED,
)
from auditmanager.analysis.recognised.flags import FLAG_ORDER


class RecognisedContextError(ValueError):
    """The W55b source or its version-page binding is inconsistent."""


@dataclass(frozen=True, slots=True)
class RecognisedContext:
    page_number: int
    text: str
    flags: tuple[str, ...]


_ROLE: Final[str] = "prepared.recognised_text"
_VERSION: Final[str] = "1.0.0"
_SHA256: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
_TEXT_KEYS: Final[frozenset[str]] = frozenset({
    "portal_block_id", "page_number", "kind", "quote_source", "text", "flags"
})
_DESCRIPTION_KEYS: Final[frozenset[str]] = frozenset({
    "portal_block_id", "page_number", "kind", "text"
})


def select_context(
    artifact: Mapping[str, Any] | None,
    *,
    version_uid: str,
    textless_pages: tuple[int, ...] | None,
) -> tuple[RecognisedContext, ...]:
    """Return recognised TEXT entries on the stored textless pages only."""
    if not isinstance(version_uid, str) or not version_uid:
        raise RecognisedContextError("invalid_version_identity")
    if textless_pages is None:
        if artifact is not None:
            raise RecognisedContextError("unbound_legacy_recognition")
        return ()
    if (not isinstance(textless_pages, tuple) or
            any(type(page) is not int or page < 1 for page in textless_pages) or
            tuple(sorted(set(textless_pages))) != textless_pages):
        raise RecognisedContextError("invalid_textless_pages")
    if artifact is None:
        if textless_pages:
            raise RecognisedContextError("missing_recognised_artifact")
        return ()
    if (not isinstance(artifact, Mapping) or artifact.get("artifact_role") != _ROLE or
            artifact.get("artifact_version") != _VERSION or
            artifact.get("version_uid") != version_uid):
        raise RecognisedContextError("recognised_artifact_mismatch")
    checksum = artifact.get("results_sha256")
    entries = artifact.get("entries")
    if (not isinstance(checksum, str) or _SHA256.fullmatch(checksum) is None or
            not isinstance(entries, list)):
        raise RecognisedContextError("invalid_recognised_artifact")

    allowed = set(textless_pages)
    result: list[RecognisedContext] = []
    previous_page = 0
    seen_blocks: set[str] = set()
    for raw in entries:
        if not isinstance(raw, Mapping):
            raise RecognisedContextError("invalid_recognised_entry")
        kind = raw.get("kind")
        required = (_TEXT_KEYS if kind == KIND_RECOGNISED_TEXT else
                    _DESCRIPTION_KEYS if kind == KIND_PORTAL_DESCRIPTION else None)
        if required is None or set(raw) != required:
            raise RecognisedContextError("invalid_recognised_entry")
        block_id, page, body = raw["portal_block_id"], raw["page_number"], raw["text"]
        if (not isinstance(block_id, str) or not block_id or block_id in seen_blocks or
                type(page) is not int or page < 1 or page < previous_page or
                not isinstance(body, str)):
            raise RecognisedContextError("invalid_recognised_entry")
        seen_blocks.add(block_id)
        previous_page = page
        if kind == KIND_PORTAL_DESCRIPTION:
            continue
        flags = raw["flags"]
        if (raw["quote_source"] != QUOTE_SOURCE_RECOGNISED or
                not isinstance(flags, list) or
                tuple(flags) != tuple(flag for flag in FLAG_ORDER if flag in flags)):
            raise RecognisedContextError("invalid_recognised_entry")
        if page in allowed:
            result.append(RecognisedContext(page_number=page, text=body, flags=tuple(flags)))
    return tuple(result)


def render_context(context: tuple[RecognisedContext, ...]) -> str:
    """Render untrusted OCR as JSON-quoted, explicitly uncitable data."""
    if not context:
        return ""
    rows = [
        {"page_number": item.page_number, "text": item.text, "quality_flags": list(item.flags)}
        for item in context
    ]
    return (
        "=== Распознанный текст — только контекст, не цитировать ===\n"
        "Данные OCR могут содержать ошибки. Цитаты бери только из текстового слоя PDF.\n"
        + json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
        + "\n=== Конец распознанного контекста ==="
    )
