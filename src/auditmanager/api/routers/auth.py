"""``issueToken`` and ``changePassword`` -- the credential exchange, and taking one back.

Three things here are not the shape the other six router modules have, and each is the
contract's doing rather than a liberty:

* **the operation declares ``security: []``.** Every other operation inherits the router's
  ``T-6`` dependency and FastAPI emits ``[{"bearerAuth": []}]`` for it. An *omitted*
  ``security`` would mean "inherit the document's", which is not what the contract says
  here: it says the empty requirement, explicitly, overriding the root. It is stated
  through ``openapi_extra`` -- the same mechanism ``uploadDocument`` uses to restore
  ``encoding.file.contentType`` -- and :data:`_OPEN_REQUIREMENT` is where the exact
  spelling and the reason for it are written down. The runtime half of the same fact is
  :data:`auditmanager.api.security.UNAUTHENTICATED_OPERATIONS`, which is what actually lets
  an uncredentialed request through. Two halves, both named, neither inferred from the
  other;
* **there is no ``Idempotency-Key``.** Nothing is created and nothing is changed, so a
  repeat of the same exchange is a second exchange and not a replay of the first. The four
  idempotent writes are unchanged;
* **a refused login and a refused password are one answer.** The port returns ``None`` for
  "no such user", "wrong password" and "not a login this deployment would have stored", and
  this module turns all three into the catalog's ``authentication_required`` -- the *same*
  refusal a request with no credential gets, because "the deployment does not accept this"
  is one fact. Anything more specific is an account-enumeration oracle with extra steps.

**Where the models should live.** ``IssueTokenRequest``, ``IssueTokenResponse`` and
``ChangePasswordRequest`` are ``components.schemas`` entries and belong beside the others in
``api/schemas/models.py``. `W34-API` did not own that file, so the first two were declared
here instead of edited into another session's module, and the third is declared beside them
for the same reason plus one more: the three are one subject. Moving them changes no byte of
the served document -- FastAPI names a schema after the class, not after its module. The
declarations are the contract's, spelling for spelling.

``changePassword``, and why it looks the way it does
----------------------------------------------------
**It is not an open operation.** It requires a credential like every operation but the
exchange, and the account whose password changes is the one that credential names -- read
from :data:`~auditmanager.api.security.CurrentSubject`, never from the body. A login in the
body would be an operation one reviewer could aim at another, which is an authorization
model this system has not got and `T-6` forbids inventing here.

**It answers with a credential, and that is the revocation being visible rather than a
convenience.** Changing a password raises the account's credential epoch in the same
statement that writes the new digest, so every credential minted under the old password
stops being accepted -- *including the one this very request presented*. Answering `204`
would leave the caller holding something already dead and unable to tell that from a
failure. So the answer is the replacement: minted after the change, under the new epoch, and
the only credential in the world this account now accepts.

**The response reuses ``IssueTokenResponse`` and adds no schema.** A credential and its
lifetime is one shape; the contract already has a name for it. A second name for the same
two properties would be two spellings of one thing in a document whose size is itself a
guarded number, and `D-18`'s lesson is that the surface grows by as little as it can.

**One refusal for the credential, as everywhere on this path.** A wrong current password is
``authentication_required`` -- the same answer a missing credential gets -- because "this
deployment does not accept this" is one fact. A *new* password that is the current one, or
that fails the mechanical bounds, is ``validation_failed``: that is a statement about the
request and not about whether the caller is who they say, and it is only ever reported to a
caller who has already proved the current password. No error code is added to the catalog:
`D-18`, and neither refusal needs one that is not already there.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import CredentialPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.security import CurrentSubject
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ChangePasswordRequest",
    "IssueTokenRequest",
    "IssueTokenResponse",
    "build_auth_routes",
]

#: The operation's own ``security``: **the empty requirement**, which overrides the
#: document root for this operation and for no other.
#:
#: The value is an empty ``tuple`` and not an empty ``list``, and that is the whole
#: mechanism rather than a typo. ``fastapi.utils.deep_dict_update`` -- what applies
#: ``openapi_extra`` to a generated operation, at ``fastapi/openapi/utils.py:537`` --
#: *concatenates* when both sides are lists and *replaces* otherwise
#: (``fastapi/utils.py:103-118``, measured on FastAPI 0.141.1). The seam's
#: ``Security(bearer_scheme)`` reaches every operation of the included router, so this
#: operation is generated carrying ``[{"bearerAuth": []}]`` and an empty *list* here would
#: concatenate onto it and change nothing. An empty tuple replaces it, and JSON has one
#: spelling for both: the served ``/openapi.json`` carries ``"security": []``, which is
#: what the frozen contract declares and what a conformance check reads.
#:
#: Two alternatives were rejected. Removing the requirement from the route's dependency
#: tree is not reachable from here: FastAPI 0.141 keeps the router's dependencies in an
#: include context and merges them into an *effective* route at document time, so the
#: object this module constructs never sees them. Editing the generated document is what
#: ``api/app.py`` does for FastAPI's injected 422 -- and that file belongs to another
#: session, which is the constraint this line is written under.
#:
#: ``test_the_exchange_declares_the_empty_requirement`` asserts both halves: the normalized
#: in-memory document and the bytes of the served ``/openapi.json``.
_OPEN_REQUIREMENT: Final[dict[str, Any]] = {"security": ()}


class _Object(BaseModel):
    """Every object schema in this contract is closed. Same rule as ``schemas/models.py``."""

    model_config = ConfigDict(extra="forbid")


class IssueTokenRequest(_Object):
    """The exchanged pair. Both properties are required and neither may be empty."""

    login: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class IssueTokenResponse(_Object):
    """The credential, and how long it stays valid counted from this response.

    Answered by ``issueToken`` and by ``changePassword``. One shape, one name: both
    operations hand back a credential this deployment has just minted and the number of
    seconds it stays good for, and a second schema saying the same two things would grow the
    document without telling a caller anything new.
    """

    token: Annotated[str, Field(min_length=1)]
    expires_in: Annotated[int, Field(ge=1)]


class ChangePasswordRequest(_Object):
    """The current password and its replacement. Both required, neither may be empty.

    **There is no login here and there will not be one.** Whose password this changes is
    decided by the credential the request carries, which the seam has already verified. A
    login in this body would let a caller name an account other than their own, and the only
    thing standing between that and a working impersonation would be a check nobody has
    specified yet.

    The bounds are :mod:`auditmanager.access.passwords`' mechanical ones, restated here
    because a transport schema is where a body is bounded. They are not a password policy:
    there is still no minimum length, no complexity rule, no history and no expiry, and
    inventing one at this seam would have to be renegotiated when a policy is really
    specified.
    """

    current_password: Annotated[str, Field(min_length=1, max_length=1024)]
    new_password: Annotated[str, Field(min_length=1, max_length=1024)]


def build_auth_routes(router: APIRouter, credentials: CredentialPort) -> None:

    @router.post(
        "/auth/token",
        operation_id="issueToken",
        tags=["auth"],
        status_code=200,
        response_model=IssueTokenResponse,
        openapi_extra=dict(_OPEN_REQUIREMENT),
        responses={
            **success(
                200,
                "The credentials were accepted. The body carries the credential to "
                "present on every other operation and how long it stays valid.",
            ),
            # 401 and not 403: ``permission_denied`` is an *authenticated* subject being
            # refused, and this is the operation that produces one. 409 is absent because
            # nothing here is idempotent, and 404 because this path addresses no aggregate.
            **envelope_responses(401, 422, 500, 503),
        },
        summary="Exchange a login and a password for a bearer credential.",
    )
    def issue_token(body: IssueTokenRequest) -> WireResponse:
        issued = credentials.issue(login=body.login, password=body.password)
        if issued is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        return json_response(
            200,
            encode_json({"token": issued.token, "expires_in": issued.expires_in}),
        )

    @router.post(
        "/auth/password",
        operation_id="changePassword",
        tags=["auth"],
        status_code=200,
        response_model=IssueTokenResponse,
        responses={
            **success(
                200,
                "The password was changed. Every credential minted for this account "
                "before this response -- including the one this request presented -- is "
                "refused from now on. The body carries the replacement.",
            ),
            # 401 covers both "no credential" and "that is not the current password": one
            # refusal, as on the exchange.
            #
            # 403 is declared, and this is the difference from ``issueToken``. That
            # operation omits it because it has no authenticated subject -- it is the one
            # that produces one -- and every *other* operation on this surface declares it,
            # which `tests/contract/domain_p02/test_openapi_document.py`'s
            # ``test_every_operation_can_report_401_and_403`` enforces for exactly the
            # reason that makes it right here: a generated client needs a typed shape for
            # `permission_denied` on every authorized operation, and an operation that
            # omitted it would be asserting something about a role model this surface does
            # not have. Nothing raises it, here or anywhere else.
            #
            # 409 is absent because nothing here is idempotent: a second identical change
            # is refused by its own current password, not replayed. 404 is absent because
            # this path addresses no aggregate; an account that has gone is a refused
            # credential.
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="Change the signed-in account's password and revoke its old credentials.",
    )
    def change_password(subject: CurrentSubject, body: ChangePasswordRequest) -> WireResponse:
        # `subject.user_uid` and never `body`: the account is the one the seam verified.
        issued = credentials.change_password(
            user_uid=subject.user_uid,
            current_password=body.current_password,
            new_password=body.new_password,
        )
        if issued is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        return json_response(
            200,
            encode_json({"token": issued.token, "expires_in": issued.expires_in}),
        )
