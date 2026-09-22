"""``issueToken`` -- the credential exchange, and the only open operation on this surface.

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

**Where the two models should live.** ``IssueTokenRequest`` and ``IssueTokenResponse`` are
``components.schemas`` entries and belong beside the other forty-six in
``api/schemas/models.py``. `W34-API` does not own that file, so they are declared here
instead of edited into another session's module. Moving them there later changes no byte of
the served document: FastAPI names a schema after the class, not after its module. The
declarations themselves are the contract's, spelling for spelling.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import CredentialPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["IssueTokenRequest", "IssueTokenResponse", "build_auth_routes"]

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
    """The credential, and how long it stays valid counted from this response."""

    token: Annotated[str, Field(min_length=1)]
    expires_in: Annotated[int, Field(ge=1)]


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
