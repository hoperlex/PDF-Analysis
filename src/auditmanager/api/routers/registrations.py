"""The five registration operations -- applying for an account, and deciding an application.

`W49-SEAL-01`, owner rulings `R-55` and `R-56` with its addendum of 2026-10-06.

Two of them are reached **without a credential**, and they are the second and third
entries of :data:`~auditmanager.api.security.UNAUTHENTICATED_OPERATIONS` after the
exchange:

* ``submitRegistration`` records an application. Its refusals are ``validation_failed``
  (the e-mail, the names or the password policy) and ``conflict`` with
  ``details.conflict_reason`` -- ``login_taken``, ``request_pending`` or ``queue_full``. It
  declares neither ``401`` nor ``403``: it has no credential to refuse and no subject to
  deny.
* ``readRegistrationStatus`` answers ``{"status": "pending"}`` for a pair that proves a
  pending request, and **the same ``401`` a refused exchange gets for every other pair** --
  an unknown login, a wrong password, a decided request. A rejected applicant learns nothing
  here (`R-56` addendum); the reason is for administrators.

The edge in front of ``/api/v1`` throttles both per client and answers ``rate_limited``
(``429``) itself, before an operation is reached; this application never raises it, and --
like the edge's own body-size refusal -- it is not declared on the operations. Both carry
``security: []`` through :data:`~auditmanager.api.routers.auth.OPEN_REQUIREMENT`, the
exchange's own mechanism.

The other three are an administrator's (``OPERATION_ROLES``: ``{admin}``): list, approve,
reject. ``approveRegistration`` takes an ``Idempotency-Key`` as every create on this surface
does -- it creates an account. Every rule -- one decision per request, at least one role, the
reason's bounds, the queue cap -- is ``auditmanager.access``'s; this module parses, calls one
port method and renders.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.auth import OPEN_REQUIREMENT, IssueTokenRequest
from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    CursorParam,
    LimitParam,
    RegistrationStatusFilterParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import RegistrationPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate, timestamp
from auditmanager.api.schemas.registrations import registration_body
from auditmanager.api.security import CurrentSubject
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["build_registration_routes"]

#: The approval's ``409`` covers three things: an idempotency-key conflict, a request that
#: is no longer pending, and a login an active account took meanwhile.
_APPROVAL_CONFLICT = (
    "The idempotency key was already used with a different payload, the request is no "
    "longer pending (`state_transition_not_allowed`), or an active account now holds the "
    "login (`conflict`, `conflict_reason: login_taken`)."
)


def build_registration_routes(router: APIRouter, registrations: RegistrationPort) -> None:
    @router.post(
        "/registrations",
        operation_id="submitRegistration",
        tags=["registrations"],
        status_code=201,
        response_model=models.RegistrationStatusResponse,
        openapi_extra=dict(OPEN_REQUIREMENT),
        responses={
            **success(201, "The application was recorded and is pending a decision."),
            **envelope_responses(
                409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION}
            ),
        },
        summary="Apply for an account.",
    )
    def submit_registration(body: models.SubmitRegistrationRequest) -> WireResponse:
        status = registrations.submit(
            login=body.login,
            password=body.password,
            last_name=body.last_name,
            first_name=body.first_name,
            middle_name=body.middle_name,
        )
        return json_response(201, encode_json({"status": status}))

    @router.post(
        "/registrations/status",
        operation_id="readRegistrationStatus",
        tags=["registrations"],
        status_code=200,
        response_model=models.RegistrationStatusResponse,
        openapi_extra=dict(OPEN_REQUIREMENT),
        responses={
            **success(200, "The pair proves a pending application."),
            # 401 and not 403, as on the exchange: there is no authenticated subject here
            # to deny. It is the one refusal every other pair gets.
            **envelope_responses(401, 422, 500, 503),
        },
        summary="Read whether a login and password pair proves a pending application.",
    )
    def read_registration_status(body: IssueTokenRequest) -> WireResponse:
        status = registrations.read_status(login=body.login, password=body.password)
        if status is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        return json_response(200, encode_json({"status": status}))

    @router.get(
        "/registrations",
        operation_id="listRegistrations",
        tags=["registrations"],
        status_code=200,
        response_model=models.RegistrationRequestPage,
        responses={
            **success(200, "One page of registration requests, oldest first."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="List registration requests.",
    )
    def list_registrations(
        status: RegistrationStatusFilterParam = None,  # type: ignore[assignment]
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        listing = registrations.list_requests(
            status=None if status is None else status.value
        )
        page = paginate(listing.items, limit=limit, cursor=cursor, sort_key=_request_sort_key)
        body = page_body([registration_body(view) for view in page.items], page.next_cursor)
        body["pending_total"] = listing.pending_total
        return json_response(200, encode_json(body))

    @router.post(
        "/registrations/{request_id}/approve",
        operation_id="approveRegistration",
        tags=["registrations"],
        status_code=200,
        response_model=models.RegistrationRequest,
        responses={
            **success(
                200,
                "The account was created and the request decided, or the recorded outcome "
                "of an identical earlier request was replayed.",
            ),
            **envelope_responses(
                401,
                403,
                404,
                409,
                422,
                500,
                503,
                descriptions={409: _APPROVAL_CONFLICT},
            ),
        },
        summary="Approve a registration request and create the account.",
    )
    def approve_registration(
        subject: CurrentSubject,
        request_id: Annotated[models.RegistrationRequestId, Path()],
        body: models.ApproveRegistrationRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = registrations.approve(
            actor_uid=subject.user_uid,
            request_id=request_id,
            roles=frozenset(role.value for role in body.roles),
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(registration_body(view)))

    @router.post(
        "/registrations/{request_id}/reject",
        operation_id="rejectRegistration",
        tags=["registrations"],
        status_code=200,
        response_model=models.RegistrationRequest,
        responses={
            **success(200, "The request was decided as rejected."),
            **envelope_responses(
                401,
                403,
                404,
                409,
                422,
                500,
                503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        summary="Reject a registration request with a reason.",
    )
    def reject_registration(
        subject: CurrentSubject,
        request_id: Annotated[models.RegistrationRequestId, Path()],
        body: models.RejectRegistrationRequest,
    ) -> WireResponse:
        view = registrations.reject(
            actor_uid=subject.user_uid, request_id=request_id, reason=body.reason
        )
        return json_response(200, encode_json(registration_body(view)))


def _request_sort_key(view: object) -> tuple[str, ...]:
    """``(submitted_at, request_id)`` -- the listing's declared total order, oldest first."""
    return (timestamp(getattr(view, "submitted_at")), getattr(view, "request_id"))
