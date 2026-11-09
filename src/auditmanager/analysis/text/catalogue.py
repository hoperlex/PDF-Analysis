"""The model catalogue the stage layout may name (`HOSTS-LAYOUT-01`, ADR-0028 decisions 6, 13).

``contracts/analysis/v1/model-catalogue.json`` lists, for every lock pin the layout offers and every provider that can serve
it, the accesses, the reasoning efforts that may be asked for and the **exact** strings an answer may report as its model. It is
read-only here and decides nothing about a price or an identity: rates stay in ``docs/program/P02_LOCK.json``.

Two questions are answered from it and nowhere else:

* may a layout cell name this (model, effort) pair? (:meth:`ModelCatalogue.require_pair`) -- a model that is not an entry
  (any Haiku, an unpinned alias), an effort that the entry does not list (``xhigh``, ``max``, ``low`` for Opus) and a value
  outside the vocabulary are all one typed refusal, ``validation_failed``;
* may an answer that reports ``reported`` stand for the model ``expected_model``? (:func:`accepted_reported`, `R-133`) -- by
  **exact** string membership. No prefix, no date suffix, no case folding, no trimming. A model the catalogue does not list is
  held to plain equality, which is what the identity check has always been for a gateway name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Iterable

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CATALOGUE_RELPATH", "CatalogueEntry", "FORBIDDEN_EFFORTS", "ModelCatalogue", "accepted_reported", "load_model_catalogue",
    "model_catalogue",
]

#: ``src/auditmanager/analysis/text/catalogue.py`` -> repository root (the same location rule as ``lock.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
CATALOGUE_RELPATH: Final[str] = "contracts/analysis/v1/model-catalogue.json"

#: Never offered, whatever a catalogue file says (the original's owner forbids them, ADR-0028 decision 13). A second line behind the
#: file: a catalogue edited to list one is still refused here.
FORBIDDEN_EFFORTS: Final[frozenset[str]] = frozenset({"xhigh", "max"})


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    provider: str
    model_id: str
    access: tuple[str, ...]
    efforts: tuple[str, ...]
    accepted_reported: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelCatalogue:
    contract_version: str
    efforts_vocabulary: tuple[str, ...]
    entries: tuple[CatalogueEntry, ...]

    def model_ids(self) -> tuple[str, ...]:
        """The offered models once each, in the file's order."""
        seen: dict[str, None] = {}
        for entry in self.entries:
            seen.setdefault(entry.model_id)
        return tuple(seen)

    def entries_of(self, model_id: str) -> tuple[CatalogueEntry, ...]:
        return tuple(entry for entry in self.entries if entry.model_id == model_id)

    def efforts_of(self, model_id: str) -> tuple[str, ...]:
        """The efforts a layout cell may ask of ``model_id``: those every provider entry of the model lists."""
        entries = self.entries_of(model_id)
        if not entries:
            return ()
        allowed = set(entries[0].efforts)
        for entry in entries[1:]:
            allowed &= set(entry.efforts)
        return tuple(effort for effort in self.efforts_vocabulary if effort in allowed and effort not in FORBIDDEN_EFFORTS)

    def require_pair(self, model_id: object, effort: object, *, field: str = "cells") -> None:
        """Refuse (``validation_failed``) a pair the catalogue does not offer."""
        if not isinstance(model_id, str) or not self.entries_of(model_id) or "haiku" in model_id.lower():
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="model_not_in_catalogue")
        if not isinstance(effort, str) or effort in FORBIDDEN_EFFORTS or effort not in self.efforts_of(model_id):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="effort_not_offered_for_model")

    def accepted_reported(self, expected_model: str, *, provider: str | None = None) -> frozenset[str]:
        """Every string an answer may report for ``expected_model`` (the union over the providers, or one provider's)."""
        names: set[str] = set()
        for entry in self.entries_of(expected_model):
            if provider is None or entry.provider == provider:
                names.update(entry.accepted_reported)
        return frozenset(names)


def _unreadable() -> DomainError:
    # The message names no path (the envelope screen forbids one); the location is this module's constant.
    return DomainError(ErrorCode.INTERNAL_ERROR, message="the model catalogue document could not be read")


def _tuple_of_str(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise _unreadable()
    return tuple(value)


def load_model_catalogue(path: Path | None = None) -> ModelCatalogue:
    """Read the catalogue. ``path`` exists so a test can point at a variant."""
    try:
        document = json.loads((path or _REPO_ROOT / CATALOGUE_RELPATH).read_text(encoding="utf-8"))
        entries = tuple(
            CatalogueEntry(
                provider=str(item["provider"]), model_id=str(item["model_id"]), access=_tuple_of_str(item["access"]),
                efforts=_tuple_of_str(item["efforts"]), accepted_reported=_tuple_of_str(item["accepted_reported"]),
            )
            for item in document["entries"]
        )
        return ModelCatalogue(
            contract_version=str(document["contract_version"]),
            efforts_vocabulary=_tuple_of_str(document["efforts_vocabulary"]), entries=entries,
        )
    except (OSError, ValueError, KeyError, TypeError):
        raise _unreadable() from None


@lru_cache(maxsize=1)
def model_catalogue() -> ModelCatalogue:
    """The repository's catalogue, read once per process."""
    return load_model_catalogue()


def accepted_reported(expected_model: str | None, reported: object, *, provider: str | None = None,
                      catalogue: ModelCatalogue | None = None) -> bool:
    """``R-133``: may ``reported`` stand for ``expected_model``? Exact membership, nothing looser.

    ``reported`` is accepted when it is **the same string** as ``expected_model`` or when the catalogue lists it among the strings
    ``expected_model`` may be reported as (``provider`` narrows the list to one provider's entry). A string that only starts with an
    accepted one, differs from it in case or carries whitespace is not accepted; an absent or non-string report never is.
    """
    if not isinstance(expected_model, str) or not expected_model or not isinstance(reported, str):
        return False
    if reported == expected_model:
        return True
    return reported in (catalogue or model_catalogue()).accepted_reported(expected_model, provider=provider)
