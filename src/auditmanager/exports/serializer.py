"""The seventeen-column CSV, byte for byte — ``OD-11`` / P02 §6.

The bytes are the contract here, so each decision is written down next to the code that
makes it:

* **UTF-8 with a byte-order mark.** The intended reader opens the file in Excel, which
  without a BOM guesses a legacy code page and mis-decodes Cyrillic. The corpus is
  Russian, so this is a correctness decision and not a cosmetic one. The BOM is written
  once, at the front of the whole document — never per row.
* **CRLF line endings**, including after the header and after the final row, which is
  what RFC 4180 specifies and what Excel expects.
* **Comma delimiter, RFC 4180 quoting.** ``QUOTE_MINIMAL`` quotes a field exactly when
  it contains a comma, a double quote or a line break, and doubles an embedded quote.
* **A null projection column is the empty string** — never the literal ``null``, never
  ``NULL``. A reader opening this in a spreadsheet must see an empty cell, not the
  four-letter word a naive ``str(None)`` would produce.

One row per evidence item. A finding with three quotations produces three rows sharing
columns 1–11 and 14–17, because the reader's unit of work is a quotation.

Determinism is the property everything else hangs off: two exports of an unchanged run
are byte-identical. Nothing here reads a clock, a locale, a random source or an
environment variable, and the row order is fixed upstream by
:mod:`auditmanager.exports.query`.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Final, Sequence

from auditmanager.exports.query import ExportRow

#: The frozen column list, in the frozen order. P02 §6. `B8` downloads what this names.
COLUMNS: Final[tuple[str, ...]] = (
    "project_uid",
    "document_uid",
    "version_uid",
    "run_id",
    "run_state",
    "provider_mode",
    "finding_uid",
    "finding_observation_id",
    "category",
    "finding_text",
    "recommendation_text",
    "evidence_page",
    "evidence_quote",
    "current_verdict",
    "latest_comment",
    "latest_decision_id",
    "decision_recorded_at",
)

#: The sort key P02 §6 fixes. ``evidence_ordinal`` orders the rows of one observation
#: and is deliberately not itself a column.
SORT_KEY: Final[tuple[str, ...]] = (
    "finding_uid",
    "finding_observation_id",
    "evidence_ordinal",
)

#: UTF-8 byte-order mark. See the module docstring for why it is not optional.
BOM: Final[bytes] = b"\xef\xbb\xbf"

CONTENT_TYPE: Final[str] = "text/csv; charset=utf-8"

_DELIMITER: Final[str] = ","
_LINE_TERMINATOR: Final[str] = "\r\n"


def _cell(value: Any) -> str:
    """One cell's text. ``None`` is the empty string; a datetime is RFC 3339 with ``Z``."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        moment = (
            value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        )
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, bool):
        # Not reachable from the current column set, and defined rather than left to
        # str(): a stray "True" in a CSV a reviewer reads is worse than a refusal.
        return "true" if value else "false"
    return str(value)


def row_values(row: ExportRow) -> tuple[str, ...]:
    """The seventeen cells of one evidence item, in the frozen column order."""
    return tuple(_cell(getattr(row, column)) for column in COLUMNS)


def render_csv(rows: Sequence[ExportRow]) -> bytes:
    """Serialize rows to the exact bytes ``OD-11`` specifies.

    The rows arrive already sorted; this function does not reorder them, so the sort
    key stays defined in exactly one place. It writes the header even when there are no
    rows: a run that published nothing is a result, and an empty file with no header
    would be indistinguishable from a failure to produce one.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(
        buffer,
        delimiter=_DELIMITER,
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator=_LINE_TERMINATOR,
    )
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(row_values(row))
    return BOM + buffer.getvalue().encode("utf-8")


__all__ = [
    "BOM",
    "COLUMNS",
    "CONTENT_TYPE",
    "SORT_KEY",
    "render_csv",
    "row_values",
]
