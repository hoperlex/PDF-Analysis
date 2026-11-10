"""The model catalogue as the hosts see it (`HOSTS-BACKEND-01`, ADR-0028 decision 13).

``contracts/analysis/v1/model-catalogue.json`` describes the lock pins the stage layout may name: for each (provider, model) the accesses
it can be served with, the efforts it may be asked for and the exact strings an answer may report as its model. This module reads that
file and nothing else. It answers three questions for the host machinery:

* which (provider, model) pairs a host report may be turned into system connections for (an entry of the file that is also a lock pin);
* what the stand hands an agent as its catalogue (``Catalogue.for_agent``: ``RunnerCatalogueEntry`` of the contract);
* which strings an answer's ``reported_model`` may take for a model (``accepted_reported``) -- matching is exact, no prefix, no
  case folding (`R-133`).

Rates and identity stay in ``docs/program/P02_LOCK.json``; a catalogue entry without a lock pin is not offered here (a model is a
system connection only while it is a pin). The file is read once per process (``catalogue()``); ``load_catalogue`` takes a path so a test
can point at a variant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CATALOGUE_RELPATH",
    "Catalogue",
    "CatalogueEntry",
    "catalogue",
    "load_catalogue",
]

CATALOGUE_RELPATH: Final[str] = "contracts/analysis/v1/model-catalogue.json"
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    provider: str
    model_id: str
    accesses: tuple[str, ...]
    efforts: tuple[str, ...]
    accepted_reported: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Catalogue:
    entries: tuple[CatalogueEntry, ...]

    def entry(self, provider: str, model_id: str) -> CatalogueEntry | None:
        for item in self.entries:
            if item.provider == provider and item.model_id == model_id:
                return item
        return None

    def serves(self, provider: str, model_id: str, access: str) -> bool:
        """Is this (provider, model) in the catalogue with this access? A model outside it is never a system connection."""
        found = self.entry(provider, model_id)
        return found is not None and access in found.accesses

    def accepted_reported(self, provider: str, model_id: str) -> tuple[str, ...]:
        """The exact strings an answer may report for the model besides ``model_id`` itself; empty for an unknown pair."""
        found = self.entry(provider, model_id)
        return () if found is None else found.accepted_reported

    def reported_is_accepted(self, provider: str, model_id: str, reported: str) -> bool:
        """``reported`` is ``model_id`` or one of its ``accepted_reported`` strings, exactly (`R-133`)."""
        found = self.entry(provider, model_id)
        return found is not None and (reported == model_id or reported in found.accepted_reported)

    def for_agent(self) -> list[dict[str, Any]]:
        """The entries as ``RunnerCatalogueEntry`` documents: one per (provider, model), the shape ``reportRunnerHealth`` answers."""
        return [
            {"provider": item.provider, "model_id": item.model_id, "efforts": list(item.efforts),
             "accepted_reported": list(item.accepted_reported)}
            for item in self.entries
        ]


def _entry(raw: dict[str, Any]) -> CatalogueEntry:
    return CatalogueEntry(
        provider=str(raw["provider"]), model_id=str(raw["model_id"]),
        accesses=tuple(str(item) for item in raw["access"]),
        efforts=tuple(str(item) for item in raw["efforts"]),
        accepted_reported=tuple(str(item) for item in raw["accepted_reported"]),
    )


def load_catalogue(path: Path | None = None, *, pinned: frozenset[str] | None = None) -> Catalogue:
    """Read the catalogue. ``pinned`` is the set of model ids the provider lock holds; an entry whose model is not one is left out
    (``None`` reads the lock). The file being unreadable is ``dependency_unavailable`` -- there is no built-in copy to fall back to."""
    source = path or (_REPO_ROOT / CATALOGUE_RELPATH)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
        entries = [_entry(item) for item in document["entries"]]
    except (OSError, ValueError, KeyError, TypeError):
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message="the model catalogue cannot be read",
            dependency="model_catalogue",
        ) from None
    if pinned is None:
        from auditmanager.analysis.public import pinned_models

        pinned = frozenset(pin.model_id for pin in pinned_models())
    return Catalogue(entries=tuple(item for item in entries if item.model_id in pinned))


@lru_cache(maxsize=1)
def catalogue() -> Catalogue:
    """The repository's catalogue, read once per process."""
    return load_catalogue()
