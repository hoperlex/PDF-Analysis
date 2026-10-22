"""How a run gets its model adapter when the provider source is the database (`EXEC-HTTP-01`).

Two moments, each a small callable the composition root supplies and ``runs`` only calls:

* **freeze** (:data:`RouteFreezer`) -- at run start, in the transaction that creates the run:
  resolve the ``text_analysis`` route to a connection revision and return it as a
  :class:`FrozenRoute`. The revision is written to the run row, which freezes it; the input budget
  follows that revision's pinned model; a standby chosen instead of the primary is journaled.
  A refusal is raised here, before any row exists.
* **bind** (:data:`ProviderResolver`) -- at each Attempt, just before the model stage: build the
  adapter of the run's frozen revision with the connection's *current* key, and say how the call
  must be recorded and held to its model (:class:`ProviderBinding`).

The ``environment`` source needs neither: its adapter is built once at start-up and passed to
``execute_run`` as before. ``runs`` imports nothing from ``executors``; the composition root
(``bootstrap/providers.py``) is where the two meet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.jobs.public import AttemptContext

__all__ = ["FrozenRoute", "ProviderBinding", "ProviderResolver", "RouteFreezer"]


@dataclass(frozen=True, slots=True)
class FrozenRoute:
    """The connection revision a run starts on, and the budget that follows its model."""

    revision_id: str
    input_budget_characters: int
    #: Set when the standby served instead of the primary: the two connections and why.
    primary_connection_id: str | None = None
    standby_connection_id: str | None = None
    standby_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    """What one Attempt calls: the adapter, the configuration it runs under (``model_id`` is the
    pin id) and the :class:`~auditmanager.analysis.text.binding.CallBinding` the stage reads."""

    adapter: Any
    config: Any
    call: Any = None


RouteFreezer = Callable[[Session], FrozenRoute]
ProviderResolver = Callable[[Session, Any, AttemptContext], ProviderBinding]
