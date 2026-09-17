"""`T-6` -- the authorization seam, and the alpha's implementation of it.

The contract declares one scheme at its root since `W13-SEAL`'s reseal (`a5f4001`)::

    "bearerAuth": {"type": "http", "scheme": "bearer"}

and `security: [{"bearerAuth": []}]` over all twelve operations. **That declares the seam,
not its implementation.** No issuer, no discovery URL, no flow, no token format, and no
role, subject or capability vocabulary appears in the document, and none may be added here:
the deployment decides all of them and the same twelve operations must keep working when it
does. The alpha's implementation is one static token; the public version replaces the body
of :func:`require_authorization` with OIDC and touches neither the operations nor the
contract.

Three things this module does **not** do, each because the contract says so:

* **it does not emit ``bearerFormat``.** ``HTTPBearer`` will not unless asked, which is why
  `W13-SEAL` chose the scheme it did: an opaque deployment token and an OIDC-issued JWT are
  both bearer credentials, and naming the format would pin the document to whichever one is
  current;
* **it does not raise FastAPI's own 401.** ``auto_error=True`` raises an ``HTTPException``
  whose body is ``{"detail": "Not authenticated"}`` -- not an ``ErrorEnvelope``, and with no
  ``X-Correlation-Id`` beyond what the middleware appends. `W13-SEAL` section 8.1 names this
  trap by name: **401 is ``authentication_required`` in an ``ErrorEnvelope``, and nothing
  else is acceptable.** So ``auto_error=False``, and the refusal is a ``DomainError``;
* **it says nothing about who the caller is.** One subject with one token is not an identity
  model. ``permission_denied`` stays in the catalog, reachable and unraised by this
  application, because the day there are subjects it is already the right code.

**Where the token comes from, and the gap that leaves.** ``create_app(environ=...)`` already
carries the whole environment through the composition root, so the seam reads
``AUDITMANAGER_API_TOKEN`` from that mapping and needs no new configuration plumbing. It is
**not** in ``.env.example`` and **not** on ``AppSettings``: both are outside this session's
scope (`W13-API` owns ``src/auditmanager/api/**``), and adding a key to either is reported in
``docs/program/reviews/W13-API.md`` rather than done here.

**Unconfigured means refused, not open.** An application built with no token answers
``authentication_required`` to every request on the authorized surface. The alternative --
"no token configured, so let everyone in" -- is a switch that turns the seam off by omission,
which is exactly the failure mode a deployment discovers in production. The health plane of
`T-3` is on its own port and outside this surface, so an unconfigured application is still
pollable by the proxy and the deploy script.
"""

from __future__ import annotations

import hmac
from typing import Annotated, Final, Mapping

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "API_TOKEN_VARIABLE",
    "SCHEME_NAME",
    "AuthorizationDependency",
    "bearer_scheme",
    "build_authorization_dependency",
]

#: The document's ``components.securitySchemes`` key. Not the class name FastAPI would
#: otherwise use (``HTTPBearer``): the contract names the scheme and the contract wins.
SCHEME_NAME: Final[str] = "bearerAuth"

#: The environment variable the alpha's static token is read from.
API_TOKEN_VARIABLE: Final[str] = "AUDITMANAGER_API_TOKEN"

#: ``auto_error=False``: see the module note. The description is the seam's, and the
#: conformance gate drops it under `N4` -- it is here for the served documentation page.
bearer_scheme = HTTPBearer(
    scheme_name=SCHEME_NAME,
    auto_error=False,
    description="The authorization seam. A bearer credential presented as "
    "`Authorization: Bearer <token>`.",
)

AuthorizationDependency = Annotated[
    HTTPAuthorizationCredentials | None, Security(bearer_scheme)
]


def build_authorization_dependency(environ: Mapping[str, str]) -> object:
    """The dependency that guards all twelve operations, closed over the configured token.

    A factory rather than a module-level dependency reading ``os.environ``, because
    ``create_app(environ=...)`` exists precisely so that a second application can be built
    with a different configuration in the same process -- `W13-BASE` builds one that way for
    the `D-7` case, and `W5CERT-DEF-2` is the defect that happened the last time a component
    reached for the process environment instead of the injected mapping.
    """
    expected = environ.get(API_TOKEN_VARIABLE) or ""

    def require_authorization(credentials: AuthorizationDependency) -> None:
        """Refuse anything that is not the configured credential.

        ``hmac.compare_digest`` rather than ``==``: the comparison is over a secret, and a
        short-circuiting one leaks its length and prefix to a caller who can time it. The
        empty expected token is refused before the comparison, so an unconfigured
        application cannot be opened by presenting an empty bearer.
        """
        if not expected or credentials is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        if not hmac.compare_digest(credentials.credentials, expected):
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)

    return Depends(require_authorization)
