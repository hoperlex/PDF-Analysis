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

``connection_revision_id`` is the revision that **served this call**: ``None`` only for the ``environment`` source.
A run admitted on an executor group (`EXEC2-GROUP-RUN-01`) is *pending* until dispatch binds a member, and a pending run
has no binding at all -- the source resolver refuses it before any adapter is built -- so a call that has one names the
member the claim wrote on the run, never a revision chosen here.

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
    #: `HOSTS-LAYOUT-01` (ADR-0028 decision 6). Set only for a call of a run frozen with a stage plan: the cell the call belongs to
    #: (``row:role``), its access (``subscription`` or ``api``) and the host that serves it. ``stage_key`` is the layout row, which is
    #: what the call journal records. Never set for a connection-bound or environment run, whose calls are recorded as before.
    cell_key: str | None = None
    access: str | None = None
    host_id: str | None = None

    def __post_init__(self) -> None:
        if (self.connection_revision_id is None) != (self.identity_basis is None):
            raise ValueError("a connection revision and an identity basis go together")
        if self.cell_key is not None and (not self.check_identity or not self.expected_model or self.access is None):
            # A planned call always asks for the identity check against the cell's model (`R-133`).
            raise ValueError("a cell call is held to the cell's model and carries its access")

    @property
    def stage_key(self) -> str | None:
        """The layout row of a planned call, or ``None``: the value of ``model_call.stage_key``."""
        return None if self.cell_key is None else self.cell_key.partition(":")[0]
