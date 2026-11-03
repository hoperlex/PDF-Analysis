"""Where a run's model adapter comes from: the two provider sources (`EXEC-HTTP-01`, plan section 6).

The composition root is the one place that knows both ``runs`` and ``executors``, so the seam
between them is assembled here and nowhere else:

* :class:`EnvironmentProviders` -- ``AUDITMANAGER_PROVIDER_SOURCE=environment`` (the default). The
  adapter is built once at start-up from ``PROXY_LLM_*`` or ``ANTHROPIC_API_KEY``, exactly as
  before, and every run uses it. Two things are new: ``R-133`` is enforced (the stage holds the
  reply to the configured model, so the stand needs an explicit ``PROXY_LLM_MODEL``), and a run
  that froze a connection revision is refused rather than served by the wrong source. One more
  (`PROD-11C`, `D-225` piece 2): a *recorded* adapter may carry a second binding, handed to the
  AR v3 beta Runs only, that says the replayed call charges nothing (see the class);
* :class:`DatabaseProviders` -- ``database``. ``freeze`` resolves the ``text_analysis`` route at
  run start; ``resolve`` builds, per Attempt, the adapter of the revision the run froze, opening
  that connection's current key with the worker's private ring. `EXEC2-GROUP-RUN-01`: ``admit_group``
  admits a start on a group or by the routing rules (:class:`GroupAdmission`); the connection of such a run
  is chosen at dispatch, so ``resolve`` serves it only once it is ``bound`` and refuses a ``pending`` one.
  The ``environment`` source has neither: it refuses a group start, and ``resolve`` refuses a ``pending`` run
  as it refuses a ``bound`` one (a connection it cannot serve).

Nothing here falls back: a source that cannot serve a run says so with a typed error.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

from sqlalchemy import Connection
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID,
    AR_V3_BETA_PROFILE_ID,
    input_budget_characters,
)
from auditmanager.analysis.text import CallBinding, ModelRequest, ModelResponse, ProviderMode
from auditmanager.executors.public import ExecutorRepository, SecretUnreadableError
from auditmanager.executors.resolver import admit_group, group_of_revision
from auditmanager.executors.runtime import (
    DestinationPolicy,
    KindRuntime,
    bind_connection,
    freeze_connection,
    route_missing,
)
from auditmanager.runs import AdmittedGroup, FrozenRoute, GroupAdmitter, ProviderBinding, RouteFreezer
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "WORK_KIND",
    "DatabaseProviders",
    "EnvironmentProviders",
    "GroupAdmission",
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
    """What the composition root hands the run path: ``resolve`` always, ``freeze`` and ``admit_group`` for the
    ``database`` source only."""

    freeze: RouteFreezer | None = None
    #: `EXEC2-GROUP-RUN-01`. ``None`` for the ``environment`` source: a start that names a group is then refused
    #: (``environment_source``), and a start that names nothing is what it always was.
    admit_group: GroupAdmitter | None = None

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:  # pragma: no cover
        raise NotImplementedError


def _awaits_dispatch(run: Any) -> bool:
    """A run admitted by a rule or a group whose connection no member has been bound to yet. ``None`` for the
    connection revision does **not** say this: with ``frozen_at_start`` it is the ``environment`` source. The row says
    it (``binding_state``); a run object without the attribute is a run written before the column existed."""
    return getattr(run, "binding_state", None) == "pending"


def _is_ar_v3_beta_run(run: Any) -> bool:
    """The exact sealed pair the executor routes to the v3 review chain (`v3_exact`), nothing looser."""
    return (
        getattr(run, "analysis_profile_id", None) == str(AR_V3_BETA_PROFILE_ID)
        and getattr(run, "prompt_bundle_id", None) == str(AR_V3_BETA_BUNDLE_ID)
    )


class EnvironmentProviders(ProviderSource):
    """Every run uses the one adapter built at start-up.

    ``ar_v3_replay_call`` (`PROD-11C`, `D-225` piece 2) is the call binding of a **recorded replay**
    that costs nothing. The AR v3 worker refuses, after the provider call, a call whose cost is not
    a measured or estimated amount or an explicit ``unmetered`` (`AR-V3-BETA-COST-REFUSAL-01`), and
    a replayed reply carries no cost; without the mark no recorded v3 Run could publish. It is
    handed to the AR v3 beta Runs **only**, never to a v1 Run (whose recorded calls keep the pin
    estimate they have always had), and it is accepted only together with a recorded adapter: a live
    or proxied adapter with it is refused here, at construction, so no live call can reach the cost
    check marked as costing nothing through this source. The `database` source's ``not_metered``
    connections are a different, declared route and are untouched.
    """

    def __init__(
        self, adapter: Any, config: Any, call: CallBinding | None = None, *,
        ar_v3_replay_call: CallBinding | None = None,
    ) -> None:
        if ar_v3_replay_call is not None:
            if getattr(adapter, "provider_mode", None) is not ProviderMode.RECORDED:
                raise ValueError(
                    "a call binding that charges nothing is for a recorded adapter only; "
                    "a live or proxied call must report its own cost"
                )
            if not ar_v3_replay_call.unmetered:
                raise ValueError("the AR v3 replay call binding must be explicitly unmetered")
        self._binding = ProviderBinding(adapter=adapter, config=config, call=call)
        self._ar_v3_replay = (
            None if ar_v3_replay_call is None
            else ProviderBinding(adapter=adapter, config=config, call=ar_v3_replay_call)
        )
        self.freeze = None
        self.admit_group = None

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:
        if _awaits_dispatch(run):
            # `EXEC2-GROUP-RUN-01`: a run admitted by a rule or a group has **no connection yet**, and no
            # connection is what an environment run has too. Serving it here would run group work on this
            # process's own adapter -- the silent switch the plan forbids. The environment source refuses a
            # group start, so only a source switched under pending work reaches this line.
            raise route_missing()
        if getattr(run, "connection_revision_id", None) is not None:
            # The run froze a connection under the `database` source; this process serves the
            # `environment` one. Using its adapter would record a call against a revision that
            # did not serve it, and a silent switch is what the plan forbids.
            raise route_missing()
        if self._ar_v3_replay is not None and _is_ar_v3_beta_run(run):
            return self._ar_v3_replay
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
        self.admit_group = GroupAdmission(ceiling_usd=ceiling_usd)

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
        revision = ExecutorRepository().get_revision(session, frozen.revision_id)
        if revision is None:
            raise route_missing()
        return FrozenRoute(
            revision_id=frozen.revision_id,
            # The budget follows the revision's pinned model, not the model the process
            # started with.
            input_budget_characters=input_budget_characters(frozen.pin_id, self._ceiling),
            model_id=frozen.pin_id,
            primary_connection_id=frozen.primary_connection_id if frozen.used_standby else None,
            standby_connection_id=frozen.standby_connection_id if frozen.used_standby else None,
            standby_reason=frozen.reason,
            chosen_connection_id=frozen.connection_id if frozen.explicit else None,
            billing="unmetered" if revision.settings.billing == "not_metered" else "metered",
        )

    def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:
        revision_id = getattr(run, "connection_revision_id", None)
        if revision_id is None:
            # A run frozen under the `environment` source, served after the switch: no fallback. And a run
            # admitted by a group that no member has taken (`EXEC2-GROUP-RUN-01`): the claim binds it before
            # any stage runs, so a pending run here means the dispatch was skipped -- nothing is called.
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


class GroupAdmission:
    """The ``database`` source's admission on a group or by the routing rules (`EXEC2-GROUP-RUN-01`).

    A callable, so that the ``runs`` context takes it as a :data:`~auditmanager.runs.GroupAdmitter` and never imports
    the executors context. It adds what the executors context does not know: the input budget that follows the
    group's pin (the same ``input_budget_characters`` the route freezer applies to a revision's pin), and the
    estimate's spelling of the billing."""

    def __init__(self, *, ceiling_usd: float) -> None:
        self._ceiling = ceiling_usd

    def __call__(self, session: Session, *, group_id: str | None = None) -> AdmittedGroup | None:
        admitted = admit_group(session, WORK_KIND, group_id=group_id)
        if admitted is None:
            return None
        return AdmittedGroup(
            group_id=admitted.group_id, group_revision_id=admitted.group_revision_id, pin_id=admitted.pin_id,
            gateway_model=admitted.gateway_model,
            billing="unmetered" if admitted.billing == "not_metered" else "metered",
            input_budget_characters=input_budget_characters(admitted.pin_id, self._ceiling),
            rule_revision_id=admitted.rule_revision_id,
        )

    def group_of(self, session: Session, group_revision_id: str) -> str | None:
        return group_of_revision(session, group_revision_id)
