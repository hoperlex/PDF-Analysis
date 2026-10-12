"""The repair ledger as a file: the ledger document plus the drop it was taken over.

`W54-JUDGE-Y` F3: a ledger names its base snapshot (the ``results.md`` text) but not the
crops the paid calls were made from. The run checks every crop against the operator's
``SHA256SUMS`` before it spends (step 0) and the journal header records that file's SHA-256;
the ledger file carries the same value as a top-level ``drop_sums_sha256``, so the bundle
export can require that the sums it is given are the sums the repair checked.

The field sits beside :meth:`RepairLedger.as_document`'s keys, not inside the ledger model:
:meth:`RepairLedger.from_document` reads only its own keys, so the model and its
``LEDGER_VERSION`` stay as they are.

**Backward reading is a refusal.** A ledger file without ``drop_sums_sha256`` reads back
with ``None``; the export refuses it as ``ledger_sums_unrecorded``. No paid ledger predates
this field (no live run was made before the durable journal existed), so none is lost.
"""

from __future__ import annotations

import json
import re
from typing import Any, Final

from ..repair import RepairLedger

LEDGER_SUMS_FIELD: Final[str] = "drop_sums_sha256"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def ledger_document(ledger: RepairLedger, *, drop_sums_sha256: str) -> dict[str, Any]:
    """The ledger file's document: the ledger's own keys and the sums it was taken over."""
    if _SHA256.fullmatch(drop_sums_sha256 or "") is None:
        raise ValueError("drop_sums_sha256 is not 64 lowercase hex digits")
    document = ledger.as_document()
    document[LEDGER_SUMS_FIELD] = drop_sums_sha256
    return document


def read_ledger_file(data: bytes) -> tuple[RepairLedger, str | None]:
    """``(ledger, drop_sums_sha256 or None)`` from a ledger file's bytes.

    Raises ``ValueError``, ``KeyError`` or ``TypeError`` for bytes that are not a ledger,
    and ``ValueError`` for a ``drop_sums_sha256`` that is present but not a digest.
    """
    document = json.loads(data.decode("utf-8"))
    if not isinstance(document, dict):
        raise TypeError("a repair ledger is a JSON object")
    ledger = RepairLedger.from_document(document)
    sums = document.get(LEDGER_SUMS_FIELD)
    if sums is not None and (not isinstance(sums, str) or _SHA256.fullmatch(sums) is None):
        raise ValueError(f"{LEDGER_SUMS_FIELD} is not 64 lowercase hex digits")
    return ledger, sums


__all__ = ["LEDGER_SUMS_FIELD", "ledger_document", "read_ledger_file"]
