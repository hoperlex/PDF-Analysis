"""Account management, an administrator's surface (`R-55`, `R-61`).

`W49-SEAL-01`. Every operation here is ``{admin}`` in
:data:`~auditmanager.api.security.OPERATION_ROLES`, so the seam has refused everyone else
before a handler runs. The account addressed is the path's ``user_uid``; the administrator
acting is the verified subject, passed as ``actor_uid`` and never read from a body.

The invariants -- an account cannot archive, purge, demote or reset itself
(``permission_denied``, no detail), the last active administrator stays one (``conflict``,
``conflict_reason: last_admin``), a purge refuses a non-archived account
(``state_transition_not_allowed`` against ``app_user``) and a referenced one (``conflict``,
``account_referenced``), a restore refuses a login an active account now holds
(``login_taken``) -- are enforced in ``auditmanager.access`` and proven there without a
router. This module parses, calls one port method and renders.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    CursorParam,
    IncludeArchivedParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import AccountPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.accounts import PersonNamesView, account_body
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.security import CurrentSubject

__all__ = ["build_user_routes"]

UserUidPath = Annotated[models.UserUid, Path()]

_CONFLICT = {409: STATE_CONFLICT_DESCRIPTION}


def build_user_routes(router: APIRouter, accounts: AccountPort) -> None:
    @router.get(
        "/users",
        operation_id="listUsers",
        tags=["users"],
        status_code=200,
        response_model=models.AccountPage,
        responses={
            **success(200, "One page of accounts, ordered by login."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="List accounts.",
    )
    def list_users(
        include_archived: IncludeArchivedParam = False,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        rows = accounts.list_accounts(include_archived=include_archived)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_account_sort_key)
        body = page_body([account_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))

    @router.get(
        "/users/{user_uid}",
        operation_id="getUser",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "One account, archived or not."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
        summary="Read one account.",
    )
    def get_user(user_uid: UserUidPath) -> WireResponse:
        view = accounts.get_account(user_uid=user_uid)
        return json_response(200, encode_json(account_body(view)))

    @router.patch(
        "/users/{user_uid}",
        operation_id="updateUser",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "The account after the change."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions=_CONFLICT),
        },
        summary="Change an account's names, its role set, or both.",
    )
    def update_user(
        subject: CurrentSubject, user_uid: UserUidPath, body: models.UpdateUserRequest
    ) -> WireResponse:
        names = (
            None
            if body.names is None
            else PersonNamesView(
                last_name=body.names.last_name,
                first_name=body.names.first_name,
                middle_name=body.names.middle_name,
            )
        )
        roles = None if body.roles is None else frozenset(role.value for role in body.roles)
        view = accounts.update_account(
            actor_uid=subject.user_uid, user_uid=user_uid, names=names, roles=roles
        )
        return json_response(200, encode_json(account_body(view)))

    @router.post(
        "/users/{user_uid}/archive",
        operation_id="archiveUser",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "The account is archived; every credential it held is refused."),
            **envelope_responses(401, 403, 404, 409, 500, 503, descriptions=_CONFLICT),
        },
        summary="Archive an account.",
    )
    def archive_user(subject: CurrentSubject, user_uid: UserUidPath) -> WireResponse:
        view = accounts.archive_account(actor_uid=subject.user_uid, user_uid=user_uid)
        return json_response(200, encode_json(account_body(view)))

    @router.post(
        "/users/{user_uid}/restore",
        operation_id="restoreUser",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(200, "The account is active again."),
            **envelope_responses(401, 403, 404, 409, 500, 503, descriptions=_CONFLICT),
        },
        summary="Restore an archived account.",
    )
    def restore_user(subject: CurrentSubject, user_uid: UserUidPath) -> WireResponse:
        view = accounts.restore_account(actor_uid=subject.user_uid, user_uid=user_uid)
        return json_response(200, encode_json(account_body(view)))

    @router.delete(
        "/users/{user_uid}",
        operation_id="purgeUser",
        tags=["users"],
        status_code=204,
        response_model=None,
        responses={
            **success(204, "The archived account was deleted irreversibly."),
            **envelope_responses(401, 403, 404, 409, 500, 503, descriptions=_CONFLICT),
        },
        summary="Purge an archived, unreferenced account.",
    )
    def purge_user(subject: CurrentSubject, user_uid: UserUidPath) -> WireResponse:
        accounts.purge_account(actor_uid=subject.user_uid, user_uid=user_uid)
        return WireResponse(204, ())

    @router.post(
        "/users/{user_uid}/sessions/end",
        operation_id="endUserSessions",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(
                200,
                "Every credential the account held is refused from its next request; the account is "
                "unchanged otherwise.",
            ),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions=_CONFLICT),
        },
        summary="End every session of an account.",
        description=(
            "Requires `admin` and an `Idempotency-Key`. Raises the account's credential epoch, so every "
            "credential it holds -- in every browser and on every device -- is refused from its next "
            "request and it signs in again; its password, roles and sign-in brake are untouched. The "
            "event `sessions_ended` is journalled in the same transaction (`listAuthEvents`). Not "
            "oneself (`permission_denied`): an administrator ends their own sessions by changing their "
            "password. An archived or missing account is `not_found`. An exact repeat of the key answers "
            "the account unchanged and ends nothing more; the key under another account or another "
            "administrator is `idempotency_key_reuse`."
        ),
    )
    def end_user_sessions(
        subject: CurrentSubject, user_uid: UserUidPath, idempotency_key: RequiredIdempotencyKey
    ) -> WireResponse:
        view = accounts.end_account_sessions(
            actor_uid=subject.user_uid, user_uid=user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, encode_json(account_body(view)))

    @router.get(
        "/auth-events",
        operation_id="listAuthEvents",
        tags=["users"],
        status_code=200,
        response_model=models.AuthEventPage,
        responses={
            **success(200, "One page of the access journal, newest first."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="List the access journal.",
        description=(
            "Requires `admin`. The append-only journal of sign-ins and what changes an account's access, newest "
            "first: `sign_in_succeeded`, `sign_in_blocked` (a refused attempt that started a cooling-off period, "
            "at most one per account per period -- refusals that start none and attempts on an unknown login are "
            "not journalled), `password_changed`, `password_reset`, `role_granted`, `role_revoked` and "
            "`sessions_ended`. An account is named by identity and by its label now; the journal never holds a "
            "password, a token, an address or a login as typed. The cursor is the last event's identity."
        ),
    )
    def list_auth_events(
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = accounts.list_auth_events(cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.post(
        "/users/{user_uid}/password",
        operation_id="resetUserPassword",
        tags=["users"],
        status_code=200,
        response_model=models.Account,
        responses={
            **success(
                200,
                "The account's password is the temporary one, which it must change at its "
                "next sign-in; every credential it held is refused.",
            ),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
        summary="Set a temporary password for an account.",
    )
    def reset_user_password(
        subject: CurrentSubject,
        user_uid: UserUidPath,
        body: models.ResetUserPasswordRequest,
    ) -> WireResponse:
        view = accounts.reset_password(
            actor_uid=subject.user_uid,
            user_uid=user_uid,
            temporary_password=body.temporary_password,
        )
        return json_response(200, encode_json(account_body(view)))


def _account_sort_key(view: object) -> tuple[str, ...]:
    """``(login, user_uid)`` -- the listing's declared total order."""
    return (getattr(view, "login"), getattr(view, "user_uid"))
