"""``getMe`` and ``updateMyProfile`` -- the signed-in account reading and naming itself.

`W49-SEAL-01`, owner rulings `R-55` and `R-59`. Both operations address the account the
authorization seam verified, read from :data:`~auditmanager.api.security.CurrentSubject` and
never from a path or a body: there is no ``user_uid`` to aim at somebody else.

Both are in the seam's registers as reachable by an **incomplete** profile, because they
are the way out of one, and ``getMe`` also by an account still on a **default** credential,
because a client has to learn that state before it can send the person anywhere. What an
update may do -- complete a legacy profile in one UPDATE, or change the names of a complete
one whose login is fixed -- is ``auditmanager.access``'s rule, behind the port; this module
parses, calls one method and renders.
"""

from __future__ import annotations

from fastapi import APIRouter

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import AccountPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.accounts import account_body
from auditmanager.api.security import CurrentSubject

__all__ = ["build_me_routes"]


def build_me_routes(router: APIRouter, accounts: AccountPort) -> None:
    @router.get(
        "/me",
        operation_id="getMe",
        tags=["account"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "The signed-in account: its login, names, roles and state."),
            **envelope_responses(401, 403, 500, 503),
        },
        summary="Read the signed-in account.",
    )
    def get_me(subject: CurrentSubject) -> WireResponse:
        view = accounts.get_account(user_uid=subject.user_uid)
        return json_response(200, encode_json(account_body(view)))

    @router.patch(
        "/me",
        operation_id="updateMyProfile",
        tags=["account"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "The account after the change."),
            **envelope_responses(
                401,
                403,
                409,
                422,
                500,
                503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
        summary="Set the signed-in account's names, and complete its profile.",
    )
    def update_my_profile(
        subject: CurrentSubject, body: models.UpdateMyProfileRequest
    ) -> WireResponse:
        view = accounts.update_my_profile(
            user_uid=subject.user_uid,
            last_name=body.last_name,
            first_name=body.first_name,
            middle_name=body.middle_name,
            email=body.email,
        )
        return json_response(200, encode_json(account_body(view)))
