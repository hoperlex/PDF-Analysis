"""Where a run's model adapter comes from: the two provider sources (`EXEC-HTTP-01`, plan section 6).

The composition root is the one place that knows both ``runs`` and ``executors``, so the seam
between them is assembled here and nowhere else:

* :class:`EnvironmentProviders` -- ``AUDITMANAGER_PROVIDER_SOURCE=environment`` (the default). The
  adapter is built once at start-up from ``PROXY_LLM_*`` or ``ANTHROPIC_API_KEY``, exactly as
  before, and every run uses it. Two things are new: ``R-133`` is enforced (the stage holds the
  reply to the configured model, so the stand needs an explicit ``PROXY_LLM_MODEL``), and a run
  that froze a connection revision is refused rather than served by the wrong source;
* :class:`DatabaseProviders` -- ``database``. ``freeze`` resolves the ``text_analysis`` route at
  run start; ``resolve`` builds, per Attempt, the adapter of the revision the run froze, opening
  that connection's current key with the worker's private ring.

Nothing here falls back: a source that cannot serve a run says so with a typed error.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

from sqlalchemy import Connection
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import input_budget_characters
from auditmanager.analysis.text import CallBinding, ModelRequest, ModelResponse, ProviderMode
from auditmanager.executors.public import SecretUnreadableError
from auditmanager.executors.runtime import (
    DestinationPolicy,
    KindRuntime,
    bind_connection,
    freeze_connection,
    route_missing,
)
from auditmanager.runs import FrozenRoute, ProviderBinding, RouteFreezer
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "WORK_KIND",
    "DatabaseProviders",
    "EnvironmentProviders",
    "ProviderSource",
    "UnboundAdapter",
]

#: Today exactly one run stage calls a model (plan section 2.2).
WORK_KIND: Final[str] = "text_analysis"


class UnboundAdapter:
    """The adapter of a process that makes no model call of its own: it is ``live`` (a run
    started here declares ``live``) and refuses to complete. Serves the ``database`` source, where
    every run is bound to its connection, and ``EXECUTION_ROLE=api``, which claims nothing."""

    __slots__ = ("_detail",)

    def __init__(self, detail: str = "this process holds no provider credential") -> None:
        self._detail = detail

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message=self._detail,
            dependency="executor_route_missing",
        )


class ProviderSource:
    """What the composition root hands the run path: ``resolve`` always, ``freeze`` for the
    ``database`` source only."""

    freeze: RouteFreezer | None = None

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:  # pragma: no cover
        raise NotImplementedError


class EnvironmentProviders(ProviderSource):
    def __init__(self, adapter: Any, config: Any, call: CallBinding | None = None) -> None:
        self._binding = ProviderBinding(adapter=adapter, config=config, call=call)
        self.freeze = None

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:
        if getattr(run, "connection_revision_id", None) is not None:
            # The run froze a connection under the `database` source; this process serves the
            # `environment` one. Using its adapter would record a call against a revision that
            # did not serve it, and a silent switch is what the plan forbids.
            raise route_missing()
        return self._binding


class DatabaseProviders(ProviderSource):
    def __init__(
        self, *, ring: Any, policy: DestinationPolicy, base_config: Any, ceiling_usd: float,
        runtime: KindRuntime | None = None,
    ) -> None:
        self._ring = ring
        self._policy = policy
        self._base = base_config
        self._ceiling = ceiling_usd
        #: What a ``pull`` connection's adapter needs (`EXEC-PULL-01`): short transactions to write
        #: and read its task. Handed by the composition root; when absent it is taken from the
        #: engine the Attempt's own session is bound to.
        self._runtime = runtime
        self.freeze = self._freeze

    def _runtime_for(self, session: Session) -> KindRuntime:
        if self._runtime is not None:
            return self._runtime
        # The Attempt's own session is bound to the engine in service. A session bound to one
        # connection (a test's transaction) shares it; it has no engine to LISTEN on and polls.
        bind = session.get_bind()
        return KindRuntime(
            session_factory=sessionmaker(bind=bind), engine=None if isinstance(bind, Connection) else bind,
        )

    def _freeze(self, session: Session, *, connection_id: str | None = None) -> FrozenRoute:
        """The route's revision, or -- when the caller named a connection (`EXEC-PAR-START-01`) --
        that connection's current revision. No ``connection_id`` is the call it always was."""
        frozen = (
            freeze_connection(session, WORK_KIND) if connection_id is None
            else freeze_connection(session, WORK_KIND, connection_id=connection_id)
        )
        return FrozenRoute(
            revision_id=frozen.revision_id,
            # The budget follows the revision's pinned model, not the model the process
            # started with.
            input_budget_characters=input_budget_characters(frozen.pin_id, self._ceiling),
            primary_connection_id=frozen.primary_connection_id if frozen.used_standby else None,
            standby_connection_id=frozen.standby_connection_id if frozen.used_standby else None,
            standby_reason=frozen.reason,
            chosen_connection_id=frozen.connection_id if frozen.explicit else None,
        )

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:
        revision_id = getattr(run, "connection_revision_id", None)
        if revision_id is None:
            # A run frozen under the `environment` source, served after the switch: no fallback.
            raise route_missing()
        try:
            bound = bind_connection(
                session, revision_id, ring=self._ring, policy=self._policy, context=context,
                runtime=self._runtime_for(session),
            )
        except SecretUnreadableError:
            raise DomainError(
                ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED,
                message=(
                    "the connection's key cannot be opened here for its address "
                    "(secret_unreadable); an administrator enters the key again"
                ),
                dependency="model_provider",
            ) from None
        settings = bound.revision.settings
        config = dataclasses.replace(
            self._base, mode=ProviderMode.LIVE, model_id=settings.pin_id, api_key=None,
        )
        call = CallBinding(
            provider_label=bound.provider_label, expected_model=settings.gateway_model,
            check_identity=True, unmetered=settings.billing == "not_metered",
            identity_basis=bound.identity_basis, connection_revision_id=bound.revision.revision_id,
        )
        return ProviderBinding(adapter=bound.adapter, config=config, call=call)
