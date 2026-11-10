"""The model catalogue as the hosts see it (`HOSTS-BACKEND-01`, ADR-0028 decision 13).

``contracts/analysis/v1/model-catalogue.json`` describes the lock pins the stage layout may name: for each (provider, model) the accesses
it can be served with, the efforts it may be asked for and the exact strings an answer may report as its model. The file has one reader,
``analysis.public.model_catalogue`` / ``load_model_catalogue`` (`D-669`); this module takes that reading through ``analysis.public`` and
keeps only the hosts' view of it. It answers three questions for the host machinery:

* which (provider, model) pairs a host report may be turned into system connections for (an entry of the file that is also a lock pin);
* what the stand hands an agent as its catalogue (``Catalogue.for_agent``: ``RunnerCatalogueEntry`` of the contract);
* which strings an answer's ``reported_model`` may take for a model (``accepted_reported``) -- matching is exact, no prefix, no
  case folding (`R-133`).

Rates and identity stay in ``docs/program/P02_LOCK.json``; a catalogue entry without a lock pin is not offered here (a model is a
system connection only while it is a pin). The catalogue is built once per process (``catalogue()``); ``load_catalogue`` takes a path so a
test can point at a variant.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "Catalogue",
    "CatalogueEntry",
    "catalogue",
    "load_catalogue",
]


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


def _entry(raw: Any) -> CatalogueEntry:
    """One entry of the analysis reading (``analysis.public.CatalogueEntry``) in the hosts' shape (``access`` is ``accesses`` here)."""
    return CatalogueEntry(
        provider=raw.provider, model_id=raw.model_id, accesses=tuple(raw.access), efforts=tuple(raw.efforts),
        accepted_reported=tuple(raw.accepted_reported),
    )


def load_catalogue(path: Path | None = None, *, pinned: frozenset[str] | None = None) -> Catalogue:
    """Build the hosts' catalogue from the one reader of the file, ``analysis.public`` (`D-669`). ``pinned`` is the set of model ids the
    provider lock holds; an entry whose model is not one is left out (``None`` reads the lock). ``path`` points at a variant of the file
    (a test); ``None`` takes the repository's own, read once. The file being unreadable is ``dependency_unavailable`` -- there is no
    built-in copy to fall back to."""
    from auditmanager.analysis.public import load_model_catalogue, model_catalogue, pinned_models

    try:
        document = model_catalogue() if path is None else load_model_catalogue(path)
    except DomainError:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message="the model catalogue cannot be read",
            dependency="model_catalogue",
        ) from None
    if pinned is None:
        pinned = frozenset(pin.model_id for pin in pinned_models())
    return Catalogue(entries=tuple(_entry(item) for item in document.entries if item.model_id in pinned))


@lru_cache(maxsize=1)
def catalogue() -> Catalogue:
    """The repository's catalogue, read once per process."""
    return load_catalogue()
