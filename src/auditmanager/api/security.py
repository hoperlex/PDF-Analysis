"""`T-6` -- the authorization seam, and what `W34-API` put inside it.

The contract declares one scheme at its root since `W13-SEAL`'s reseal (`a5f4001`)::

    "bearerAuth": {"type": "http", "scheme": "bearer"}

and ``security: [{"bearerAuth": []}]`` over every operation but one. **That declares the
seam, not its implementation.** No issuer, no discovery URL, no flow, no token format, and
no role, subject or capability vocabulary appears in the document, and none may be added
here: the deployment decides all of them and the same operations must keep working when it
does. The alpha's implementation was one static token; this is the replacement, and it
touches neither the operations nor the contract.

**What replaced the static token.** A credential is now *minted* by this module, for a
subject this deployment authenticated, and *verified* by this module on every other
operation. The credential is a string carrying a payload and an HMAC-SHA256 tag over it,
produced with :mod:`hmac` and :mod:`hashlib` from the standard library. A JWT library would
have bought the same three properties -- a tamper-evident payload, an expiry, a
deployment-held key -- at the price of a root dependency pin, which is a protected hotspot
and a wave-level ratification; the seam needs "did this deployment sign this, and has it
expired", and that is forty lines of stdlib rather than an amendment to the lock.

**The format is this module's business and nobody else's.** ``am1.<payload>.<tag>`` appears
in no contract, no test outside this session's own, and no client. A caller that reads
anything out of a credential has taken a dependency this surface does not offer, and the
document says so in ``IssueTokenResponse.token``. A deployment that later replaces this
body with OIDC changes no operation -- which was the whole point of the seam.

Four things this module does **not** do, each because the contract or `T-6` says so:

* **it does not emit ``bearerFormat``.** ``HTTPBearer`` will not unless asked, which is why
  `W13-SEAL` chose the scheme it did: an opaque deployment token and an OIDC-issued JWT are
  both bearer credentials, and naming the format would pin the document to whichever one is
  current. It is now doubly true: the format below is not the deployment's to depend on;
* **it does not raise FastAPI's own 401.** ``auto_error=True`` raises an ``HTTPException``
  whose body is ``{"detail": "Not authenticated"}`` -- not an ``ErrorEnvelope``, and with no
  ``X-Correlation-Id`` beyond what the middleware appends. `W13-SEAL` section 8.1 names this
  trap by name: **401 is ``authentication_required`` in an ``ErrorEnvelope``, and nothing
  else is acceptable.** So ``auto_error=False``, and the refusal is a ``DomainError``;
* **it does not decide what a subject may do.** It decides *who* the subject is and refuses
  everyone else. ``permission_denied`` stays in the catalog, reachable and unraised by this
  application, because the day there are roles it is already the right code. A verified
  subject is published on ``request.state.subject`` and read by nothing in this tree: it is
  what the next session needs and this one must not invent a use for;
* **it does not choose which operations it guards, except by a written register.**
  :data:`UNAUTHENTICATED_OPERATIONS` is the exception list, by ``operationId``, and it holds
  exactly the operation that hands a credential out. A route whose ``operationId`` the seam
  cannot read is guarded, not exempted, so a new operation is closed by default and an
  operation opens only by being written into a set a test compares.

**Where the key comes from, and why there is no new variable.** The seam derives its
signing key from ``AUDITMANAGER_API_TOKEN`` -- the one deployment secret this surface
already has, required at construction by :mod:`auditmanager.bootstrap.settings` since
`W14-PKG` -- through one HMAC with a fixed context string. Three reasons, in order:
a second required secret would have to be added to the deploy script, the runbook, the
image and every driver in the suite, none of which this session owns; a *derived* key is
domain-separated, so the deployment secret and the signing key are not the same bytes even
though there is one thing to configure; and, crucially, **the old static token stops
working the moment this lands**. Its literal value is no longer a credential -- it fails
the signature check like any other string -- so an upgraded deployment does not quietly
keep a shared password that everyone who read the runbook already has.
``test_the_deployment_secret_is_not_itself_a_credential`` is that sentence as an assertion.

**Unconfigured means refused, not open.** An application built with no deployment secret
answers ``authentication_required`` to every request on the authorized surface and refuses
to issue a credential at all. The alternative -- "no secret configured, so let everyone
in" -- is a switch that turns the seam off by omission, which is exactly the failure mode a
deployment discovers in production. The health plane of `T-3` is on its own port and
outside this surface, so an unconfigured application is still pollable by the proxy and the
deploy script.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated, Any, Final, Mapping

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "API_TOKEN_VARIABLE",
    "SCHEME_NAME",
    "TOKEN_LIFETIME_SECONDS",
    "UNAUTHENTICATED_OPERATIONS",
    "AuthorizationDependency",
    "IssuedCredential",
    "Subject",
    "TokenSigner",
    "bearer_scheme",
    "build_authorization_dependency",
    "build_signer",
    "derive_signing_key",
]

#: The document's ``components.securitySchemes`` key. Not the class name FastAPI would
#: otherwise use (``HTTPBearer``): the contract names the scheme and the contract wins.
SCHEME_NAME: Final[str] = "bearerAuth"

#: The deployment secret this seam derives its signing key from. Spelled again in
#: ``bootstrap/settings.py`` as ``API_TOKEN_ENV`` -- ``bootstrap`` is below ``api`` and must
#: not depend upward -- and ``tests/integration/composition/test_api_token_channel.py`` pins
#: the two spellings equal so the duplication cannot drift.
API_TOKEN_VARIABLE: Final[str] = "AUDITMANAGER_API_TOKEN"

#: The operations that answer without a credential, by ``operationId``.
#:
#: A register and not a rule, for the same reason the contract's own guards use one
#: (`W34-CONTRACT`, ``UNAUTHENTICATED_OPERATIONS`` in
#: ``tests/contract/domain_p02/test_openapi_document.py``): "the exchange is open" is a
#: fact about one named operation, and a *rule* -- "anything under ``/auth``", "anything
#: whose path contains token" -- would open the next operation somebody put there without
#: anybody deciding to. ``test_the_open_surface_is_exactly_the_register`` sweeps the served
#: application and asserts the set of operations that answer without a credential **equals**
#: this one, so a second open operation is reported rather than tolerated.
UNAUTHENTICATED_OPERATIONS: Final[frozenset[str]] = frozenset({"issueToken"})

#: How long a minted credential stays valid, in seconds. One hour.
#:
#: A constant rather than a configured value: it is a property of this implementation, and
#: the contract already tells every caller the lifetime in the response it just received
#: (``IssueTokenResponse.expires_in``), so a deployment that wants another one changes this
#: line and the answer changes with it. A configuration name would have to be added to the
#: deploy script and the runbook, which this session does not own, to express something no
#: caller has asked to vary.
TOKEN_LIFETIME_SECONDS: Final[int] = 3600

#: The credential format's version tag, and the first field of every credential this seam
#: mints. Present so that a future body -- a different payload, a different algorithm, OIDC
#: -- is *distinguishable* rather than merely different: a credential of an unknown version
#: is refused by the same path that refuses a forged one.
_FORMAT: Final[str] = "am1"

#: Domain separation. The signing key is ``HMAC-SHA256(deployment secret, this string)``, so
#: the bytes that sign credentials are not the bytes the deployment configured, and a second
#: use of the same secret for a different purpose would derive a different key by using a
#: different context rather than by needing a second secret.
_SIGNING_CONTEXT: Final[bytes] = b"auditmanager/api/token-signing/v1"

#: ``auto_error=False``: see the module note. The description is the seam's, and the
#: conformance gate drops it under `N4` -- it is here for the served documentation page.
bearer_scheme = HTTPBearer(
    scheme_name=SCHEME_NAME,
    auto_error=False,
    description="The authorization seam. A bearer credential presented as "
    "`Authorization: Bearer <token>`, obtained from the credential exchange.",
)

AuthorizationDependency = Annotated[
    HTTPAuthorizationCredentials | None, Security(bearer_scheme)
]


@dataclass(frozen=True, slots=True)
class Subject:
    """Who the deployment decided the caller is. Not what they may do.

    Two fields, both already known to the caller: their own identity and their own login.
    Nothing else is carried, because everything else -- a role, a group, a permission, an
    expiry the client could act on -- would be this module inventing the identity model
    `T-6` says it must not have.
    """

    user_uid: str
    login: str


@dataclass(frozen=True, slots=True)
class IssuedCredential:
    """What the exchange hands back: the opaque credential and its lifetime in seconds."""

    token: str
    expires_in: int


def derive_signing_key(secret: str) -> bytes:
    """The signing key for a deployment secret, or a refusal for an empty one.

    ``HMAC-SHA256(secret, context)`` rather than the secret itself -- see
    :data:`_SIGNING_CONTEXT`. An empty or blank secret has no key: the caller is expected to
    treat that as "this deployment cannot verify or issue anything" and refuse, which is
    what :func:`build_signer` does.
    """
    material = secret.strip().encode("utf-8")
    if not material:
        raise ValueError("an empty deployment secret derives no signing key")
    return hmac.new(material, _SIGNING_CONTEXT, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    """URL-safe base64 without padding. Unpadded because a credential travels in a header."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    """The inverse. Raises on anything that is not what :func:`_b64` produces."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class TokenSigner:
    """Mints credentials for subjects this deployment authenticated, and verifies them.

    One object holds the key, so the key is read from the environment once, by the thing
    that builds this, and never reached for again. Both directions are here rather than in
    two modules because they are one decision: a change to the payload, the tag or the
    expiry rule that reached only one side would produce a deployment that issues
    credentials it will not accept.
    """

    __slots__ = ("_key", "_lifetime")

    def __init__(self, key: bytes, *, lifetime_seconds: int = TOKEN_LIFETIME_SECONDS) -> None:
        if not key:
            raise ValueError("a signer needs a key")
        if lifetime_seconds < 1:
            raise ValueError("a credential that is already expired is not a credential")
        self._key = key
        self._lifetime = lifetime_seconds

    @property
    def lifetime_seconds(self) -> int:
        return self._lifetime

    def issue(self, subject: Subject, *, now: float | None = None) -> IssuedCredential:
        """Mint a credential for ``subject``.

        ``now`` is a parameter so a test can state the clock instead of sleeping. The
        payload carries the issue and expiry instants as whole seconds of Unix time; the
        *response* carries a lifetime and never a clock reading, because two clocks that
        must agree are two ways to be wrong.
        """
        issued_at = int(time.time() if now is None else now)
        expires_at = issued_at + self._lifetime
        payload = {
            "sub": subject.user_uid,
            "login": subject.login,
            "iat": issued_at,
            "exp": expires_at,
        }
        body = _b64(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signed = f"{_FORMAT}.{body}"
        return IssuedCredential(
            token=f"{signed}.{_b64(self._tag(signed))}",
            expires_in=self._lifetime,
        )

    def verify(self, presented: str, *, now: float | None = None) -> Subject | None:
        """The subject this credential names, or ``None``.

        ``None`` for every way a credential can fail to be one: a wrong shape, an unknown
        format version, a tag this key did not produce, a payload that is not the object
        this module writes, an expiry that has passed. **One answer for all of them**, and
        one answer for the caller to act on -- the seam's ``authentication_required`` --
        because telling a caller *which* of those it was is an oracle they have not earned,
        and because a credential that fails any of these checks is not a credential.

        The tag is compared with :func:`hmac.compare_digest`: the comparison is over a
        secret, and a short-circuiting one leaks its length and its prefix to a caller who
        can time it.
        """
        parts = presented.split(".")
        if len(parts) != 3:
            return None
        version, body, tag = parts
        if version != _FORMAT:
            return None
        signed = f"{version}.{body}"
        try:
            presented_tag = _unb64(tag)
        except (binascii.Error, ValueError):
            return None
        if not hmac.compare_digest(presented_tag, self._tag(signed)):
            return None
        # Only now is the payload read. Decoding before the tag is checked would run this
        # module's parser over bytes an unauthenticated caller chose.
        try:
            payload: Any = json.loads(_unb64(body))
        except (binascii.Error, ValueError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        subject_uid = payload.get("sub")
        login = payload.get("login")
        expires_at = payload.get("exp")
        if not isinstance(subject_uid, str) or not subject_uid:
            return None
        if not isinstance(login, str) or not login:
            return None
        # ``isinstance(True, int)`` is true, so booleans are excluded explicitly: a
        # credential whose expiry is ``true`` would otherwise compare as 1 and be expired,
        # which is the right answer for the wrong reason and would stop being the right
        # answer if the comparison ever flipped.
        if not isinstance(expires_at, int) or isinstance(expires_at, bool):
            return None
        if expires_at <= (time.time() if now is None else now):
            return None
        return Subject(user_uid=subject_uid, login=login)

    def _tag(self, signed: str) -> bytes:
        # ``utf-8`` and not ``ascii``: a non-printable byte in the credential raised
        # ``UnicodeEncodeError`` out of here, and the seam answered ``500 internal_error``
        # instead of ``401``. That made the 500 an oracle -- it appeared only behind the
        # ``am1`` prefix, so a caller could learn the credential format from the status
        # code alone. Found by ``JUDGE-SEC`` driving raw bytes at the built application.
        return hmac.new(self._key, signed.encode("utf-8"), hashlib.sha256).digest()


def build_signer(environ: Mapping[str, str]) -> TokenSigner | None:
    """The signer this environment configures, or ``None`` when it configures none.

    ``None`` is not "open": every caller here treats it as a refusal. It is separate from
    raising because an application is *built* with an environment and must be able to
    report an unconfigured seam as a refused request rather than as a failed import --
    ``bootstrap.settings`` is what refuses to start a process with no deployment secret,
    and this is the second, independent line of the same rule.
    """
    secret = environ.get(API_TOKEN_VARIABLE) or ""
    try:
        return TokenSigner(derive_signing_key(secret))
    except ValueError:
        return None


def _operation_of(request: Request) -> str | None:
    """The ``operationId`` of the route serving ``request``, when there is one.

    ``scope["route"]`` is set by ``fastapi.routing.APIRoute.matches`` before any dependency
    is solved. When it is absent, or carries no ``operationId``, the answer is ``None`` --
    which no register contains, so the request is guarded. An unreadable route is a closed
    route.
    """
    route = request.scope.get("route")
    operation_id = getattr(route, "operation_id", None)
    return operation_id if isinstance(operation_id, str) else None


def build_authorization_dependency(environ: Mapping[str, str]) -> object:
    """The dependency that guards the surface, closed over this environment's signer.

    A factory rather than a module-level dependency reading ``os.environ``, because
    ``create_app(environ=...)`` exists precisely so that a second application can be built
    with a different configuration in the same process -- `W13-BASE` builds one that way for
    the `D-7` case, and `W5CERT-DEF-2` is the defect that happened the last time a component
    reached for the process environment instead of the injected mapping.
    """
    signer = build_signer(environ)

    def require_authorization(
        request: Request, credentials: AuthorizationDependency
    ) -> None:
        """Refuse anything this deployment did not mint, or minted too long ago.

        The exchange is let through by name, because requiring a credential to obtain one
        is a door with a handle on the inside. Everything else -- including a request whose
        route the seam could not identify -- must present a credential this deployment's key
        produced and whose expiry has not passed.
        """
        if _operation_of(request) in UNAUTHENTICATED_OPERATIONS:
            return
        if signer is None or credentials is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        subject = signer.verify(credentials.credentials)
        if subject is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        # Published, and read by nothing in this tree. `T-6`: the seam says who the caller
        # is; what they may do is the next session's question and this one must not answer
        # it by accident.
        request.state.subject = subject

    return Depends(require_authorization)
