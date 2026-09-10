"""The frozen domain error catalog, loaded once from the contract.

``contracts/domain/v1/error-codes.json`` is the authority. This module reads it at
import and exposes it as immutable data; it never restates a value the contract owns,
because a restatement is a second place to be wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, Mapping

_CONTRACT = (
    Path(__file__).resolve().parents[4] / "contracts" / "domain" / "v1" / "error-codes.json"
)


def _load() -> tuple[str, Mapping[str, Mapping[str, Any]], Mapping[str, Any]]:
    raw = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    codes = {
        code: MappingProxyType(dict(entry)) for code, entry in raw["codes"].items()
    }
    return raw["contract_version"], MappingProxyType(codes), MappingProxyType(dict(raw["safety"]))


CONTRACT_VERSION: Final[str]
CODES: Final[Mapping[str, Mapping[str, Any]]]
SAFETY: Final[Mapping[str, Any]]
CONTRACT_VERSION, CODES, SAFETY = _load()

#: The code an unmapped internal failure becomes. The catalog's own rule, not a choice
#: made here: "A code that is not in this catalog is never emitted and never invented
#: at the edge."
UNKNOWN_INTERNAL_CODE: Final[str] = json.loads(_CONTRACT.read_text(encoding="utf-8"))[
    "internal_mapping"
]["unknown_internal_code"]
