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

**The format is this module's business and nobody else's.** ``am2.<payload>.<tag>`` appears
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
  subject is published on ``request.state.subject``, and since wave 39 exactly one operation
  reads it -- ``changePassword``, which needs to know whose password it is changing and must
  not be told by the body;
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

**What wave 39 added: a credential can now be taken back.** Until `W39-REVOKE` a credential
was a signed statement and nothing else, which made it *irrevocable*: between issuing one
and its ``exp``, the only lever was rotating the deployment secret -- which signs everybody
out, including the operator, and needs a redeploy. `R-26` rules revocation into the alpha,
and it is the one guard of the four that cannot be added later, because no later work
reaches a credential already sitting in somebody's browser.

**What is revoked is an account's credentials, all of them, and never one token.** The
payload carries ``ver``: the value of ``app_user.token_epoch`` at the moment of minting. On
every guarded request the seam reads that account's *current* epoch and refuses a credential
that disagrees. Raising the column by one therefore invalidates every credential ever minted
for that account, immediately, everywhere, with no list of tokens kept anywhere.

**Three properties of that choice, stated because each was the reason an alternative lost.**

* *Nothing is stored per credential.* A denylist keyed by a token identity needs a table
  that grows with traffic, needs sweeping, and -- the part that decides it -- cannot revoke
  a credential minted before the denylist existed, because such a credential carries no
  identity to list. The counter revokes credentials it has never seen.
* *It survives a restart, and it must.* ``web/src/app/bff/session/store.ts`` is process
  memory, so restarting the web container already signs everyone out; **that is not
  revocation** and nothing here may lean on it. The API is a second process, the deployment
  runs more than one thing, and an operator who ends the pilot must not have to guess which
  processes have been restarted since. The epoch is a column: it is the same answer after a
  restart, after a redeploy, and to every replica at once.
* *A credential with no epoch is refused.* Everything minted before this landed carries no
  ``ver`` at all, and an unreadable epoch is treated exactly as an unknown format version
  is. So deploying this change is itself a global revocation -- everyone signs in again
  once -- which is the correct direction for a change whose point is that credentials can be
  taken away, and is written down here rather than discovered in an incident.

**What it costs, and why that is the right trade.** One primary-key ``SELECT`` of one
integer, on every request the seam guards. The seam was previously free -- one HMAC and no
I/O -- and it is not free any more. That is the *whole* price of revocation and it is not
avoidable by cleverness: a statement that can be taken back cannot be verified by reading
only the statement. What was refused instead is a cached epoch with a short TTL, which would
buy back the read and reintroduce exactly the property being removed: a revocation that
takes effect in a little while. The request that follows a revocation is refused, not the
one after that.

**The port is narrow on purpose.** :class:`CredentialEpochs` has one method, takes a
``user_uid`` and returns an integer or ``None``. It cannot read a password, cannot list
accounts and cannot write. ``None`` -- no such account -- is a refusal and never a
permissive default, which is how deleting a row revokes that account's credentials for free.

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
from typing import Annotated, Any, Final, Mapping, Protocol, runtime_checkable

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "API_TOKEN_VARIABLE",
    "SCHEME_NAME",
    "TOKEN_LIFETIME_SECONDS",
    "UNAUTHENTICATED_OPERATIONS",
    "AuthorizationDependency",
    "CredentialEpochs",
    "CurrentSubject",
    "IssuedCredential",
    "Subject",
    "TokenSigner",
    "bearer_scheme",
    "build_authorization_dependency",
    "build_signer",
    "current_subject",
    "derive_signing_key",
    "is_authorization_seam",
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
#:
#: **`R-37` is the first time that promise was called in.** The payload gained a required
#: ``name``, so an ``am1`` credential -- everything minted before this wave -- carries a
#: payload this seam no longer accepts. There were two things that could be done with one
#: and only one of them was allowed: refuse it, or fall back to ``login`` for the label
#: *inside the seam*, which is a silent fallback (``AGENTS.md`` section 4) on the
#: authorization path, in the module that may least have one. So it is refused -- and
#: refused **at the version check**, because a required field added to an ``am1`` body
#: would have made that body *different* without making it *distinguishable*, which is the
#: one thing this constant exists to prevent.
#:
#: **So deploying this signs everybody out once**, exactly as ``0007_credential_epoch``
#: does and for a comparable reason. Written down here rather than discovered in an
#: incident.
_FORMAT: Final[str] = "am2"

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

    Four fields, all already known to the caller: their own identity, their own login, the
    generation of credentials their account accepts, and the name other reviewers read on
    their decisions. Nothing else is carried, because everything else -- a role, a group, a
    permission, an expiry the client could act on -- would be this module inventing the
    identity model `T-6` says it must not have. The fourth arrived with `R-37` and the
    paragraph on it says why it is not one of those.

    ``token_epoch`` has **no default**, and that is the point of it being a field rather than
    an argument with one. A caller that could omit it would mint a credential under an epoch
    it assumed instead of one it read, and the two differ exactly when it matters: in the
    moment just after a revocation. Every construction of this class therefore has to have
    got the number from somewhere, and the only place it comes from is the account's row.
    """

    user_uid: str
    login: str
    token_epoch: int
    #: `R-37`. **The name other reviewers read**, already resolved, never empty.
    #:
    #: It is :attr:`~auditmanager.access.models.UserRecord.display_label` -- the account's
    #: chosen display name when it has one and its **login** when it has not -- and the
    #: fallback happens *there*, at the moment the row is read, not here. This field is a
    #: fact that has already been decided; nothing on the request path may decide it again.
    #:
    #: **It has no default, for `token_epoch`'s reason.** A caller that could omit it would
    #: attribute a decision to whatever the default said, and a ledger row attributed to a
    #: constant is exactly `D-66`'s shape and exactly what `D-78` was raised to remove.
    #: Every construction of this class has therefore had to get the name from somewhere,
    #: and the only place it comes from is the account's row.
    #:
    #: **Is this `T-6`'s forbidden identity model?** No, and the line is worth drawing.
    #: `T-6` forbids this module inventing a *role, group, permission or capability*
    #: vocabulary -- statements about what a subject may **do**. A display name says
    #: nothing about that; it is the same kind of fact as ``login``, which has travelled
    #: here since wave 34, and the seam still decides *who* the caller is and never *what
    #: they may do*.
    display_label: str


@dataclass(frozen=True, slots=True)
class IssuedCredential:
    """What the exchange hands back: the opaque credential and its lifetime in seconds."""

    token: str
    expires_in: int


@runtime_checkable
class CredentialEpochs(Protocol):
    """The one thing the seam needs from a database, and nothing more.

    One method. It cannot read a password, cannot list accounts, cannot write and cannot be
    handed a login -- only the opaque identity the credential itself carries. A wider port
    here would be a wider thing for the seam to be tempted by: this module is on the path of
    every request, and the narrower its reach the fewer decisions it can make by accident.
    """

    def epoch_of(self, user_uid: str) -> int | None:
        """This account's current credential generation, or ``None`` when there is none.

        ``None`` is a **refusal**, never a permissive default. An account that no longer
        exists must not keep authorising requests until its last credential expires, and a
        deployment whose epoch lookup cannot answer must fail closed.
        """


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
            # The account's credential generation at the moment of minting. A whole
            # integer and not a clock reading: an instant would have to be compared against
            # another instant, and two clocks that must agree are two ways to be wrong --
            # the same reason the response carries a lifetime and never an expiry. A counter
            # has no granularity to get wrong, so a credential minted in the same second as
            # a revocation is unambiguously on one side of it.
            "ver": subject.token_epoch,
            "sub": subject.user_uid,
            "login": subject.login,
            # `R-37`. The name other reviewers read, already resolved by the account's own
            # record before this method was reached. It travels here rather than being
            # looked up per request for three reasons, in order: it is the mechanism
            # `D-78` already established for `login`, and `R-37` changes only the *source*
            # of the label; reading it per request would mean widening `CredentialEpochs`,
            # which the module note argues at length must stay one integer on the path of
            # every request; and a decisions router reaching the `access` boundary for a
            # name would be the deep import `AGENTS.md` section 4 forbids.
            #
            # The price, stated rather than left to be found: a rename is visible on the
            # next credential, so a reviewer holding one goes on recording decisions under
            # the old name for at most `TOKEN_LIFETIME_SECONDS`. For an append-only ledger
            # that is arguably the better reading -- the row records who decided, under the
            # name they had then -- but it is a consequence and not the goal.
            "name": subject.display_label,
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
        display_label = payload.get("name")
        expires_at = payload.get("exp")
        token_epoch = payload.get("ver")
        if not isinstance(subject_uid, str) or not subject_uid:
            return None
        if not isinstance(login, str) or not login:
            return None
        # `R-37`. Required, and required to be non-empty: a credential naming no author is
        # not one this seam will admit, because the one operation that reads the name
        # writes it into an append-only ledger whose contract bounds it at 1..128. There is
        # no fallback here on purpose -- the fallback is the account's, decided once at
        # `UserRecord.display_label`, and a second one in the seam would be a silent one.
        if not isinstance(display_label, str) or not display_label:
            return None
        # A credential with no epoch, or with one that is not a positive integer, is not a
        # credential. `bool` is excluded for the same reason it is below -- `True` would
        # otherwise compare equal to epoch 1 and authorise against an account that had never
        # been revoked. Every credential minted before wave 39 lands here, which is why
        # deploying that change signs everybody out once; see the module note.
        if not isinstance(token_epoch, int) or isinstance(token_epoch, bool):
            return None
        if token_epoch < 1:
            return None
        # ``isinstance(True, int)`` is true, so booleans are excluded explicitly: a
        # credential whose expiry is ``true`` would otherwise compare as 1 and be expired,
        # which is the right answer for the wrong reason and would stop being the right
        # answer if the comparison ever flipped.
        if not isinstance(expires_at, int) or isinstance(expires_at, bool):
            return None
        if expires_at <= (time.time() if now is None else now):
            return None
        # What this returns is what the CREDENTIAL claims, including the epoch it was minted
        # under. It is not yet known to be current: this method holds the key and no
        # database, so it can prove the deployment signed this and cannot prove the account
        # still accepts it. `require_authorization` is where the claim meets the row.
        return Subject(
            user_uid=subject_uid,
            login=login,
            token_epoch=token_epoch,
            display_label=display_label,
        )

    def _tag(self, signed: str) -> bytes:
        # ``utf-8`` and not ``ascii``: a non-printable byte in the credential raised
        # ``UnicodeEncodeError`` out of here, and the seam answered ``500 internal_error``
        # instead of ``401``. That made the 500 an oracle -- it appeared only behind the
        # ``am2`` prefix, so a caller could learn the credential format from the status
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


def build_authorization_dependency(
    environ: Mapping[str, str], *, epochs: CredentialEpochs | None = None
) -> object:
    """The dependency that guards the surface, closed over this environment's signer.

    A factory rather than a module-level dependency reading ``os.environ``, because
    ``create_app(environ=...)`` exists precisely so that a second application can be built
    with a different configuration in the same process -- `W13-BASE` builds one that way for
    the `D-7` case, and `W5CERT-DEF-2` is the defect that happened the last time a component
    reached for the process environment instead of the injected mapping.

    ``epochs`` is how revocation reaches this seam, and it is a **keyword argument with a
    ``None`` default that refuses**, not an optional feature. ``None`` means this
    application was assembled without a way to read credential generations, and a deployment
    that cannot tell a live credential from a revoked one must answer
    ``authentication_required`` rather than guess -- the same bargain the module note already
    strikes for a missing deployment secret. ``create_documentation_app`` is the caller that
    passes none, and it can serve no request anyway.
    """
    signer = build_signer(environ)

    def require_authorization(
        request: Request, credentials: AuthorizationDependency
    ) -> None:
        """Refuse anything this deployment did not mint, minted too long ago, or has revoked.

        The exchange is let through by name, because requiring a credential to obtain one
        is a door with a handle on the inside. Everything else -- including a request whose
        route the seam could not identify -- must present a credential this deployment's key
        produced, whose expiry has not passed, **and whose epoch is the one its account
        accepts right now**.

        One refusal for all of them, as before. A caller learning that their credential was
        *revoked* rather than *forged* learns that the account exists, which is the
        enumeration oracle the exchange already refuses to be.
        """
        if _operation_of(request) in UNAUTHENTICATED_OPERATIONS:
            return
        if signer is None or credentials is None or epochs is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        subject = signer.verify(credentials.credentials)
        if subject is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        # The credential is genuine and unexpired. Only now is the row read, and only now
        # can this request be refused for having been revoked. The order is deliberate: a
        # forged credential must not cost a database round trip, or an unauthenticated
        # caller can make this deployment query on demand.
        current = epochs.epoch_of(subject.user_uid)
        if current is None or current != subject.token_epoch:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        # Published. `T-6`: the seam says who the caller is; what they may do is still not
        # its question. `changePassword` is the one operation that reads this, and it reads
        # the identity rather than being handed one in a body -- a body could name somebody
        # else.
        request.state.subject = subject

    # `R-31`. The stamp that lets a guard find this seam inside an assembled application's
    # dependant trees without matching on a function name. `D-73` is closed by attaching
    # the seam where it reaches *every* route the application serves, and a guard that only
    # drove the four documentation paths would pass the day somebody added a fifth -- so the
    # guard walks `app.routes` and asks each route whether it carries this. A name match
    # would be a guard a rename silently disables.
    setattr(require_authorization, _SEAM_MARKER, True)
    return Depends(require_authorization)


#: The attribute :func:`build_authorization_dependency` stamps on the callable it returns.
#: Private because nothing outside this module may set it; :func:`is_authorization_seam` is
#: the reader.
_SEAM_MARKER: Final[str] = "__auditmanager_authorization_seam__"


def is_authorization_seam(candidate: object) -> bool:
    """True when ``candidate`` is a callable this module produced as the seam.

    Accepts the ``dependency`` attribute of a solved dependant, a ``Depends`` object, or the
    raw function -- all three, because a caller walking FastAPI's dependant tree meets the
    first, a caller reading ``app.router.dependencies`` meets the second, and a guard that
    had to know which it was holding would be a guard coupled to a FastAPI version.
    """
    dependency = getattr(candidate, "dependency", candidate)
    return bool(getattr(dependency, _SEAM_MARKER, False))


def current_subject(request: Request) -> Subject:
    """The subject the seam verified for this request.

    Only an operation the seam guards may depend on this, and every such operation is
    guaranteed one: ``require_authorization`` either published a subject or refused the
    request before any handler ran. The refusal below is therefore unreachable through the
    assembled application and is still not an ``assert``: an operation added to
    :data:`UNAUTHENTICATED_OPERATIONS` that also asked for a subject would reach it, and
    answering ``authentication_required`` is the correct thing to do about that, where an
    ``AttributeError`` would be a 500 telling the caller about this module's internals.
    """
    subject = getattr(request.state, "subject", None)
    if not isinstance(subject, Subject):
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    return subject


#: What an operation writes to receive the verified caller. The seam is the only producer.
CurrentSubject = Annotated[Subject, Depends(current_subject)]
