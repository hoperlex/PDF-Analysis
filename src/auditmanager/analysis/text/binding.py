"""What the stage is told about the connection that serves one run (`EXEC-HTTP-01`, `R-133`).

The adapter answers *how* to call; this says what the stage must hold the answer to, and how the
call is recorded:

* ``provider_label`` -- the call row's ``provider`` (``anthropic`` for the environment source, as
  always; the revision's API flavour for a connection);
* ``expected_model`` / ``check_identity`` -- the gateway model name the reply must report. The
  check applies only to a *live* call: a ``recorded`` response is a replayed fixture. A live call
  with no expected name (the stub ``proxy``, nothing selected) fails closed;
* ``unmetered`` -- the connection has no per-call cost, so the call is recorded with cost basis
  ``unmetered`` and charges the run's meter nothing, instead of a pin estimate;
* ``identity_basis`` and ``connection_revision_id`` -- written on the call's journal row.

Frozen and plain: it is data, not a policy object.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.text.adapter import PROVIDER

__all__ = ["CallBinding"]


@dataclass(frozen=True, slots=True)
class CallBinding:
    provider_label: str = PROVIDER
    expected_model: str | None = None
    check_identity: bool = False
    unmetered: bool = False
    identity_basis: str | None = None
    connection_revision_id: str | None = None

    def __post_init__(self) -> None:
        if (self.connection_revision_id is None) != (self.identity_basis is None):
            raise ValueError("a connection revision and an identity basis go together")
