"""The one way a comparison lane calls a model (`CMP-SPEND-01`, ADR-0025 decisions 5, 6 and 19).

:meth:`ComparisonModelCaller.call` is the whole protocol of a comparison model call, in this order,
with no way to enter it half-way:

1. **Refuse what needs no database** -- a live call with no consent, a consent given for another
   revision or model, a reply that cannot be held to a model (`R-133`).
2. **Prepare** (one transaction, committed): the attempt still holds the item; no earlier attempt of the
   item left a call open; the connection has no other user (a Run, another call) -- under the advisory
   lock the Run path's claim takes; the USD ceilings and the overrun rule hold -- under an
   installation-wide lock; then the ``prepared`` row of ``comparison_model_call`` is inserted and
   **committed before anything is sent**. This is the pre-call breadcrumb.
3. **Mark sent** (one transaction, committed): ``prepared -> sent``, again under the attempt's
   authority. The adapter is called only after this commit.
4. **Call the adapter**, outside any transaction, exactly once. Nothing here retries.
5. **Settle** (one transaction, committed): ``completed`` with the reply's cost; ``failed`` when the
   transport proved nothing was processed, or when the provider answered something unusable (with the
   cost it may have charged); ``unknown`` when nothing proves whether the provider did billable work.
   A reply that names another model than the pinned one is a typed refusal and nothing is returned
   (`R-133`), but its cost is recorded.

A worker that dies anywhere after step 2 leaves a ``prepared`` or ``sent`` row; the queue's reclaim
settles it ``unknown`` in its own transaction (:mod:`.settler`) and ends the item ``spend_unknown``, so
the call is never sent a second time by itself.

Money. A live metered call is priced from the pinned rates (``CallEstimate`` is a size in tokens, never a
USD figure the caller chose). A ``not_metered`` connection, and every recorded reply, is journalled as
``unmetered``, has an estimate of zero, and is limited by nothing in money (decision 19).
"""

from __future__ import annotations

import logging
import math
import re
import time
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.spend.ceilings import check_after_call, check_before_call
from auditmanager.comparison.spend.errors import (
    REASON_CONNECTION_BUSY,
    REASON_CONSENT_REQUIRED,
    REASON_CONSENT_STALE,
    REASON_IMAGES_UNSUPPORTED,
    REASON_LEASE_LOST,
    REASON_MODEL_IDENTITY,
    REASON_MODEL_NOT_SELECTED,
    REASON_UNSETTLED_CALL,
    CallFailed,
    CallLost,
    CallRefused,
    OutcomeUnknown,
)
from auditmanager.comparison.spend.model import (
    COST_ESTIMATED,
    COST_MEASURED,
    COST_UNMETERED,
    JOB_KEY,
    CallEstimate,
    CallResult,
    CallRoute,
    Consent,
    estimate_micros_of,
    measured_micros_of,
)
from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.comparison.work.model import WorkItem
from auditmanager.shared.errors import DomainError, ErrorCode

if TYPE_CHECKING:
    from auditmanager.analysis.public import ModelRequest, ModelResponse

__all__ = ["ComparisonModelCaller", "MODEL_STUBS", "PROVIDER_LIVE", "PROVIDER_RECORDED"]

_log = logging.getLogger(__name__)

PROVIDER_LIVE: Final[str] = "live"
PROVIDER_RECORDED: Final[str] = "recorded"
#: What the journal's ``model_identity`` holds for a recorded reply (the CHECK of migration ``0038``).
_RECORDED_IDENTITY: Final[str] = "recorded"
#: The values the gateway reads as "I am not choosing a model" (``analysis.text.proxy.MODEL_STUBS``;
#: a test pins the two equal). A live call whose reply must be held to a model, with one of these or
#: nothing selected, fails closed before it is made.
MODEL_STUBS: Final[frozenset[str]] = frozenset({"proxy", "default", "auto"})
#: The transport's own proof that nothing was processed (``ProxyDispatchError.dispatch_class``): the
#: journal says ``failed`` and no money is counted. Everything else on a live call is not proof.
_NOT_PROCESSED: Final[frozenset[str]] = frozenset(
    {"not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"}
)
#: The ``dependency`` detail a pull call carries when the runner refused the images (``pull.py``).
_IMAGE_DEPENDENCY: Final[str] = "executor_image_input_unsupported"
_CODE = re.compile(r"^[a-z][a-z_]{2,63}$")
_FAULT: Final[str] = "adapter_fault"
_STALE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})


def _code(value: object) -> str:
    """A journal ``error_code``: a lower-case code or ``adapter_fault``; never free text."""
    return value if isinstance(value, str) and _CODE.match(value) else _FAULT


class ComparisonModelCaller:
    """Makes the model calls of comparison work. Holds no state of a call: every call is its own."""

    __slots__ = ("_sessions", "_repository")

    def __init__(
        self, session_factory: "sessionmaker[Session]", *,
        repository: ComparisonSpendRepository | None = None,
    ) -> None:
        self._sessions = session_factory
        self._repository = repository or ComparisonSpendRepository()

    @property
    def repository(self) -> ComparisonSpendRepository:
        return self._repository

    # -- the call -----------------------------------------------------------------------------
    def call(
        self, item: WorkItem, route: CallRoute, request: "ModelRequest", *, estimate: CallEstimate,
        consent: Consent | None,
    ) -> CallResult:
        """Make one model call for ``item`` over ``route``. Returns the reply and its journal row.

        Raises a :class:`~.errors.SpendError`: ``CallRefused`` (nothing was sent), ``CallFailed`` (the
        journal says ``failed``), ``OutcomeUnknown`` (it says ``unknown``; the call is **not** repeated
        here) or ``CallLost`` (the attempt lost the item). Each has ``as_outcome()`` for the handler.
        """
        mode = _mode_of(route)
        recorded = mode == PROVIDER_RECORDED
        unmetered = recorded or route.unmetered
        if not unmetered and route.pin is None:
            raise ValueError("a live metered route carries the pinned model's rates")
        self._refuse_without_database(route, mode, consent)
        estimate_micros = 0 if unmetered else estimate_micros_of(route.pin.cost_usd(  # type: ignore[union-attr]
            input_tokens=estimate.input_tokens, output_tokens=estimate.output_tokens,
        ))
        model_identity = _RECORDED_IDENTITY if recorded else route.model_identity
        job_key = _job_key_of(item)

        call_id = self._prepare(
            item, route, mode=mode, model_identity=model_identity, unmetered=unmetered,
            request_sha256=request.request_sha256, estimate_micros=estimate_micros,
            consent=consent, job_key=job_key,
        )
        if route.call_context is not None:
            route.call_context.bind(item, call_id)
        self._mark_sent(item, call_id)
        response = self._dispatch(call_id, route, request, mode=mode, unmetered=unmetered)
        cost_basis, cost_micros = self._cost(response, route, unmetered=unmetered)
        self._refuse_wrong_model(call_id, route, response, mode=mode, cost=(cost_basis, cost_micros))
        self._settle(
            call_id, lambda session: self._repository.complete(
                session, call_id, response_sha256=response.response_sha256,
                input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                latency_ms=response.latency_ms, cost_basis=cost_basis, cost_micros=cost_micros,
            ),
        )
        pause = None
        if consent is not None and not unmetered:
            with self._sessions() as session:
                job = self._repository.job_spend(
                    session, project_uid=item.project_uid, work_id=item.work_id, job_id=job_key,
                )
            pause = check_after_call(consent=consent, job=job)
        return CallResult(
            response=response, call_id=call_id, cost_basis=cost_basis, cost_micros=cost_micros, pause=pause,
        )

    # -- 1. what needs no database ---------------------------------------------------------------
    @staticmethod
    def _refuse_without_database(route: CallRoute, mode: str, consent: Consent | None) -> None:
        if mode == PROVIDER_RECORDED:
            return  # a replay spends nothing, binds no route and names no model
        if consent is None:
            raise CallRefused(REASON_CONSENT_REQUIRED, pauses_job=True)
        if (consent.connection_revision_id != route.connection_revision_id
                or consent.pinned_model != route.model_identity):
            raise CallRefused(REASON_CONSENT_STALE, pauses_job=True)
        if route.check_identity:
            expected = (route.expected_model or "").strip()
            if not expected or expected.lower() in MODEL_STUBS:
                raise CallRefused(REASON_MODEL_NOT_SELECTED, pauses_job=False)

    # -- 2. prepare: one transaction, committed before anything is sent ---------------------------
    def _prepare(
        self, item: WorkItem, route: CallRoute, *, mode: str, model_identity: str, unmetered: bool,
        request_sha256: str, estimate_micros: int, consent: Consent | None, job_key: str | None,
    ) -> str:
        repository = self._repository
        with self._sessions() as session:
            self._require_current(item, session, call_id=None)
            if repository.open_calls_of_other_attempts(
                session, work_id=item.work_id, attempt_id=item.attempt_id,
            ):
                raise CallRefused(REASON_UNSETTLED_CALL, pauses_job=False)
            if route.connection_revision_id is not None:
                connection_id = repository.connection_of(session, route.connection_revision_id)
                if connection_id is None:
                    raise ValueError("the route names a connection revision that does not exist")
                # The Run claim's own lock: this and a Run's claim cannot both pass their check.
                repository.lock_connection(session, connection_id)
                if (repository.connection_has_active_run(session, connection_id)
                        or repository.connection_has_active_call(session, connection_id)):
                    raise CallRefused(REASON_CONNECTION_BUSY, pauses_job=False)
            if not unmetered:
                assert consent is not None  # a live call without one was refused before the database
                repository.lock_day(session)
                check_before_call(
                    estimate_micros=estimate_micros, consent=consent,
                    job=repository.job_spend(
                        session, project_uid=item.project_uid, work_id=item.work_id, job_id=job_key,
                    ),
                    day=repository.day_spend(session),
                )
            repository.settle_abandoned(session)
            call_id = repository.prepare(
                session, work_id=item.work_id, attempt_id=item.attempt_id, work_kind=item.kind,
                provider_mode=mode, model_identity=model_identity,
                connection_revision_id=route.connection_revision_id, request_sha256=request_sha256,
                estimate_micros=estimate_micros,
            )
            session.commit()
        return call_id

    # -- 3. sent ------------------------------------------------------------------------------------
    def _mark_sent(self, item: WorkItem, call_id: str) -> None:
        try:
            with self._sessions() as session:
                self._require_current(item, session, call_id=call_id)
                if not self._repository.mark_sent(session, call_id):
                    raise CallLost(call_id=call_id)
                session.commit()
        except CallLost as lost:
            if lost.reason == REASON_LEASE_LOST:
                self._abandon_unsent(call_id)
            raise

    def _abandon_unsent(self, call_id: str) -> None:
        """The attempt lost the item between the two commits: nothing was sent, so the row says so."""
        try:
            with self._sessions() as session:
                self._repository.fail(session, call_id, error_code=REASON_LEASE_LOST)
                session.commit()
        except Exception:  # noqa: BLE001 - the reclaim settles an open row ``unknown`` instead
            _log.warning("comparison call %s could not be marked failed after a lost lease", call_id)

    @staticmethod
    def _require_current(item: WorkItem, session: Session, *, call_id: str | None) -> None:
        try:
            item.require_current(session)
        except DomainError as error:
            if error.code in _STALE:
                raise CallLost(call_id=call_id) from None
            raise

    # -- 4. the adapter, once -------------------------------------------------------------------------
    def _dispatch(
        self, call_id: str, route: CallRoute, request: "ModelRequest", *, mode: str, unmetered: bool,
    ) -> "ModelResponse":
        try:
            return route.adapter.complete(request)
        except DomainError as error:
            self._settle_error(call_id, route, error, mode=mode, unmetered=unmetered)
            raise  # unreachable: _settle_error always raises
        except Exception:  # noqa: BLE001 - an unexpected fault proves nothing about the provider
            self._settle(call_id, lambda s: self._repository.mark_unknown(s, call_id, error_code=_FAULT))
            raise OutcomeUnknown(call_id=call_id) from None

    def _settle_error(
        self, call_id: str, route: CallRoute, error: DomainError, *, mode: str, unmetered: bool,
    ) -> None:
        """Say in the journal what an adapter's error proves, then raise the typed error."""
        repository = self._repository
        code = _code(error.code.value)
        dispatch_class = getattr(error, "dispatch_class", None)
        dependency = getattr(error, "detail_fields", {}).get("dependency")
        if mode == PROVIDER_RECORDED:
            # A replay dispatches nothing, so it can never have spent.
            self._settle(call_id, lambda s: repository.fail(s, call_id, error_code=code))
            raise CallFailed(code, call_id=call_id)
        if dependency == _IMAGE_DEPENDENCY:
            # The runner refused the images after it claimed the task. Its tools refuse before any model
            # runs, but the contract also lets a session refuse after it has looked at them, so a metered
            # route cannot be shown not to have spent: ``unknown``. A route that costs nothing has
            # nothing unknown: ``failed``, which a new route can answer.
            if unmetered:
                self._settle(call_id, lambda s: repository.fail(s, call_id, error_code=REASON_IMAGES_UNSUPPORTED))
                raise CallFailed(REASON_IMAGES_UNSUPPORTED, call_id=call_id)
            self._settle(
                call_id, lambda s: repository.mark_unknown(s, call_id, error_code=REASON_IMAGES_UNSUPPORTED),
            )
            raise OutcomeUnknown(call_id=call_id)
        if dispatch_class in _NOT_PROCESSED:
            self._settle(call_id, lambda s: repository.fail(s, call_id, error_code=code))
            raise CallFailed(code, call_id=call_id, retry_safe=bool(getattr(error, "retry_safe", False)))
        received = getattr(error, "received", None)
        if received is not None:
            # The provider answered and the answer was unusable: it may have charged for it.
            basis, micros = self._cost_of_usage(
                route, received.input_tokens, received.output_tokens, None, unmetered=unmetered,
            )
            self._settle(call_id, lambda s: repository.fail(
                s, call_id, error_code=code, response_sha256=received.response_sha256,
                input_tokens=received.input_tokens, output_tokens=received.output_tokens,
                latency_ms=received.latency_ms, cost_basis=basis, cost_micros=micros,
            ))
            raise CallFailed(code, call_id=call_id)
        self._settle(call_id, lambda s: repository.mark_unknown(s, call_id, error_code=code))
        raise OutcomeUnknown(call_id=call_id)

    # -- 5. settle ----------------------------------------------------------------------------------
    def _settle(self, call_id: str, change: Any) -> None:
        """Run one journal change in a transaction of its own and commit it. A change that touches no
        row means the reclaim settled the call first: the attempt no longer holds the item."""
        with self._sessions() as session:
            changed = change(session)
            session.commit()
        if not changed:
            raise CallLost(call_id=call_id)

    def _refuse_wrong_model(
        self, call_id: str, route: CallRoute, response: "ModelResponse", *, mode: str,
        cost: tuple[str, int],
    ) -> None:
        """`R-133`: a live reply must report the model the call was pinned to. The answer arrived and
        may have been paid for, so the call is ``failed`` **with its cost**, and nothing is returned."""
        if mode != PROVIDER_LIVE or not route.check_identity:
            return
        reported = getattr(response, "model", None)
        if isinstance(reported, str) and reported == (route.expected_model or "").strip():
            return
        basis, micros = cost
        self._settle(call_id, lambda s: self._repository.fail(
            s, call_id, error_code=REASON_MODEL_IDENTITY, response_sha256=response.response_sha256,
            input_tokens=response.input_tokens, output_tokens=response.output_tokens,
            latency_ms=response.latency_ms, cost_basis=basis, cost_micros=micros,
        ))
        raise CallFailed(REASON_MODEL_IDENTITY, call_id=call_id)

    # -- cost ---------------------------------------------------------------------------------------
    def _cost(self, response: "ModelResponse", route: CallRoute, *, unmetered: bool) -> tuple[str, int]:
        return self._cost_of_usage(
            route, response.input_tokens, response.output_tokens,
            getattr(response, "reported_cost_usd", None), unmetered=unmetered,
        )

    @staticmethod
    def _cost_of_usage(
        route: CallRoute, input_tokens: int, output_tokens: int, reported_usd: float | None,
        *, unmetered: bool,
    ) -> tuple[str, int]:
        """``(cost_basis, cost_micros)``. Unmetered: zero, said so. Otherwise the transport's own
        figure when it gave a usable one (``measured``), else the pinned rates (``estimated``)."""
        if unmetered:
            return COST_UNMETERED, 0
        if reported_usd is not None and math.isfinite(reported_usd) and reported_usd >= 0:
            return COST_MEASURED, measured_micros_of(reported_usd)
        assert route.pin is not None
        return COST_ESTIMATED, estimate_micros_of(
            route.pin.cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
        )


def _mode_of(route: CallRoute) -> str:
    """``recorded`` or ``live``, read off the adapter that produces the reply."""
    mode = getattr(route.adapter, "provider_mode", None)
    value = getattr(mode, "value", mode)
    if value not in (PROVIDER_LIVE, PROVIDER_RECORDED):
        raise ValueError("the adapter reports neither a live nor a recorded mode")
    return str(value)


def _job_key_of(item: WorkItem) -> str | None:
    value = item.payload.get(JOB_KEY)
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise ValueError(f"the item's payload key {JOB_KEY!r} is a string of 1 to 128 characters")
    return value
