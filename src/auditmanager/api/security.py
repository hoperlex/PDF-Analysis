"""`T-6` -- the authorization seam, and what `W34-API` put inside it.

The contract declares one scheme at its root since `W13-SEAL`'s reseal (`a5f4001`)::

    "bearerAuth": {"type": "http", "scheme": "bearer"}

and ``security: [{"bearerAuth": []}]`` over every operation but three -- the exchange and,
since `W49-SEAL-01`, the two registration operations an applicant with no account uses.
**That declares the seam, not its implementation.** No issuer, no discovery URL, no flow and
no token format appears in the document, and none may be added here: the deployment decides
them and the same operations must keep working when it does. The alpha's implementation was
one static token; this is the replacement, and it touches neither the operations nor the
contract. What a subject may *do* is, since `R-55`, the account's role set -- read from the
row on every request and decided against the written registers below, never carried in the
credential.

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
* **it decides what a subject may do only by written registers**, never by a rule over
  paths or names. Until `W49-SEAL-01` it decided *who* the subject was and, under `R-50`,
  one precondition; `R-55` ... `R-61` superseded `T-6`'s exclusion of a role vocabulary for
  exactly this scope, and the seam now refuses a request by four registers, evaluated in a
  fixed order on every guarded request (see :func:`build_authorization_dependency`):

  1. the credential's signature and expiry, then the account's **standing** read from its
     row -- no such account, an **archived** one, or a stale ``token_epoch`` is
     ``authentication_required``;
  2. `R-50`: an account still on a **default credential** (seeded, or reset by an
     administrator) reaches :data:`OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` and nothing
     else -- ``permission_denied``, ``required_capability: password_changed``;
  3. an **incomplete profile** -- an account that has not given its names and e-mail yet
     (`R-59`) -- reaches :data:`OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES` and nothing else
     -- ``permission_denied``, ``required_capability: profile_completed``;
  4. :data:`OPERATION_ROLES`: the subject holds **at least one** role of the operation's
     set, and the empty set means any active account with a complete profile (`R-60`) --
     ``permission_denied``, ``required_capability: role:expert`` or ``role:admin``.

  A verified subject is published on ``request.state.subject`` with the login and display
  label **its row** holds now, not the ones minted into the credential: a profile completed
  or renamed since the credential was minted is visible on the next request, and the
  decision ledger, which writes ``author_label`` from it, writes the name form a complete
  profile has (`W49-PLAN.md` section 3.1);
* **it does not choose which operations it guards, except by a written register.**
  :data:`UNAUTHENTICATED_OPERATIONS` is the exception list, by ``operationId``: the exchange,
  which hands a credential out, and the two registration operations an applicant reaches
  with no account. A route whose ``operationId`` the seam cannot read is guarded, not
  exempted; an operation that is guarded and named in no role register is refused to
  everyone, so a new operation is closed by default and opens only by being written into a
  set a test compares.

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

**The port is narrow on purpose.** :class:`AccountStandings` has one method, takes a
``user_uid`` and returns one standing or ``None``. It cannot read a password, cannot list
accounts and cannot write. ``None`` -- no such account -- is a refusal and never a
permissive default, which is how deleting a row revokes that account's credentials for free.

It answered one integer until `R-50`, and the second scalar was added to the *answer* and
not to the number of questions -- as were, under `W49-SEAL-01`, the archive state, the
profile completeness, the role set, and the login and display label the row holds now. The alternative was a second method called beside it on
every request, which is two reads of one row inside one decision -- and the two values are
the two halves of one decision, so a disagreement between them would be a request served
under a stale reading of the account. The cost of the widening is nothing measurable: the
statement was already a primary-key lookup of that row, and it now projects one more column
of it.

**Why the default-credential fact is read here and not carried in the credential.** It
would have been free to stamp into the payload at mint time, and it was refused for two
reasons. It decides whether a request is *refused*, so a copy on the caller's side of the
wire is an older second answer to a question only the row can answer now -- and an account
that acquires the flag without its epoch moving (nothing does that today; nothing has to
keep not doing it) would keep being served by every credential already minted. And a
required payload field is an ``am2`` body this seam would no longer accept, which by
:data:`_FORMAT`'s own rule means ``am3`` and signs every holder out on deploy. The
refusal is worth one column on a read the seam was already making; it is not worth
everybody signing in again.

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
from types import MappingProxyType
from typing import Annotated, Any, Final, Mapping, Protocol, runtime_checkable

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "API_TOKEN_VARIABLE",
    "SCHEME_NAME",
    "TOKEN_LIFETIME_SECONDS",
    "OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES",
    "OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES",
    "OPERATION_ROLES",
    "PASSWORD_CHANGED_CAPABILITY",
    "PROFILE_COMPLETED_CAPABILITY",
    "ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION",
    "ROLE_ADMIN",
    "ROLE_EXPERT",
    "UNAUTHENTICATED_OPERATIONS",
    "role_capability",
    "AuthorizationDependency",
    "AccountStanding",
    "AccountStandings",
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
#: this one, so a fourth open operation is reported rather than tolerated.
#:
#: `W49-SEAL-01`, `R-56`: an applicant for an account holds no credential, so submitting an
#: application and reading whether a pair proves a pending one are open too. Neither hands
#: out a credential, neither names an account by anything but the pair the caller typed, and
#: the status read answers every pair it cannot prove with the exchange's own
#: ``authentication_required``.
UNAUTHENTICATED_OPERATIONS: Final[frozenset[str]] = frozenset(
    {"issueToken", "submitRegistration", "readRegistrationStatus"}
)

#: `R-50`. The operations a credential minted for an account **still on its seeded
#: password** may reach, by ``operationId``. Everything else answers ``permission_denied``.
#:
#: A register and not a rule, for :data:`UNAUTHENTICATED_OPERATIONS`'s reason and with one
#: more of its own. "Anything under ``/auth``" would open the next operation somebody puts
#: there without anybody deciding to; and the *content* of this set is a decision about what
#: a reviewer who cannot use the application can still do, which is exactly the kind of
#: decision that must be written down where it can be read rather than derived from a path.
#:
#: Two entries, and each is here because refusing it would refuse the way out.
#: ``issueToken`` is not guarded by this seam at all (it is in
#: :data:`UNAUTHENTICATED_OPERATIONS`), and it is named here anyway so that this set reads
#: as the whole answer to "what can a default credential do" rather than as the remainder
#: after another set. ``changePassword`` is the act the refusal demands: refusing it would
#: be a deployment in which the only way to satisfy the condition is barred by the condition.
#:
#: ``test_a_default_credential_reaches_exactly_the_register`` sweeps the served application
#: and asserts the operations that answer for such a credential **equal** this set, so a
#: fourth one is reported rather than tolerated.
#:
#: `W49-SEAL-01` added ``getMe``: a client has to be able to read the state it must send the
#: person out of -- the default credential, and whether the profile is complete -- and a
#: read of one's own account is the one way to learn it without meeting a refusal.
OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES: Final[frozenset[str]] = frozenset(
    {"issueToken", "changePassword", "getMe"}
)

#: `W49-SEAL-01`, `R-59`. The operations an account whose profile is **incomplete** -- no
#: names yet, and for an account created before the identity upgrade a legacy login -- may
#: reach. Everything else answers ``permission_denied`` with ``required_capability:
#: profile_completed``.
#:
#: The three are the way out and nothing more: reading the account, completing it, and
#: changing the password (which the seeded account must do first, so a default credential
#: on an incomplete profile reaches only ``getMe`` and ``changePassword``, the intersection
#: of the two registers). It is also what makes `W49-PLAN.md` section 3.1's "a decision
#: event is written only by a complete profile" hold by construction: ``appendDecision``
#: is in neither set, so an account whose label could still be a 254-character e-mail never
#: reaches the ledger, whose ``author_label`` is bounded at 128.
OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES: Final[frozenset[str]] = frozenset(
    {"getMe", "updateMyProfile", "changePassword"}
)

#: `W49-SEAL-01`. The capability an incomplete profile is told it lacks.
PROFILE_COMPLETED_CAPABILITY: Final[str] = "profile_completed"

#: `R-55`. The seam's own role vocabulary. Spelled again in ``auditmanager.access`` --
#: this module imports nothing of that boundary -- and the composition root's adapter
#: translates between the two by an explicit table that refuses a value it does not know.
ROLE_EXPERT: Final[str] = "expert"
ROLE_ADMIN: Final[str] = "admin"

_ANY_COMPLETE_ACCOUNT: Final[frozenset[str]] = frozenset()
_EXPERT: Final[frozenset[str]] = frozenset({ROLE_EXPERT})
_ADMIN: Final[frozenset[str]] = frozenset({ROLE_ADMIN})

#: `R-60`, `W49-PLAN.md` section 3.2. What each guarded operation requires, by
#: ``operationId``: **any of** the roles in its set, and the empty set means any active
#: account with a complete profile, whatever roles it holds -- none included. Every guarded
#: operation is named and nothing has a default: an ``operationId`` absent from this map is
#: refused to everyone, so an operation added to the surface is closed until somebody
#: writes its line here. ``tests/integration/api/test_role_register.py`` sweeps the served
#: application with every role set and asserts the answers equal this map.
#:
#: The three open operations of :data:`UNAUTHENTICATED_OPERATIONS` are not here: no
#: account is read for them, so there is no role set to compare.
OPERATION_ROLES: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        # Reads of product data: any complete account (R-60).
        "listProjects": _ANY_COMPLETE_ACCOUNT,
        "listDocuments": _ANY_COMPLETE_ACCOUNT,
        "getDocumentVersion": _ANY_COMPLETE_ACCOUNT,
        "streamDocumentVersionContent": _ANY_COMPLETE_ACCOUNT,
        "getVersionBlocks": _ANY_COMPLETE_ACCOUNT,
        "listVersions": _ANY_COMPLETE_ACCOUNT,
        "listRuns": _ANY_COMPLETE_ACCOUNT,
        "getRunStatus": _ANY_COMPLETE_ACCOUNT,
        "listRunFindings": _ANY_COMPLETE_ACCOUNT,
        "getFinding": _ANY_COMPLETE_ACCOUNT,
        "listDecisionHistory": _ANY_COMPLETE_ACCOUNT,
        "listDecisions": _ANY_COMPLETE_ACCOUNT,
        "getDashboardSummary": _ANY_COMPLETE_ACCOUNT,
        # The account itself.
        "getMe": _ANY_COMPLETE_ACCOUNT,
        "updateMyProfile": _ANY_COMPLETE_ACCOUNT,
        "changePassword": _ANY_COMPLETE_ACCOUNT,
        # Product changes -- projects, uploads, runs, verdicts, comments, the export.
        "createProject": _EXPERT,
        "uploadDocument": _EXPERT,
        "startRun": _EXPERT,
        "appendDecision": _EXPERT,
        "exportRunCsv": _EXPERT,
        # Account and registration-request management.
        "listRegistrations": _ADMIN,
        "approveRegistration": _ADMIN,
        "rejectRegistration": _ADMIN,
        "listUsers": _ADMIN,
        "getUser": _ADMIN,
        "updateUser": _ADMIN,
        "archiveUser": _ADMIN,
        "restoreUser": _ADMIN,
        "purgeUser": _ADMIN,
        "resetUserPassword": _ADMIN,
    }
)

#: What a route **without** an ``operationId`` requires. Exactly four routes have none --
#: the documentation routes of ``api/app.py`` (``DOCUMENTATION_PATHS``,
#: ``test_the_four_declare_no_operation_id``) -- and they describe the surface any complete
#: account reads: the empty set. They stay behind the default-credential and
#: incomplete-profile registers like everything else that is not named in them.
ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION: Final[frozenset[str]] = _ANY_COMPLETE_ACCOUNT


def role_capability(required: frozenset[str]) -> str:
    """The ``required_capability`` a role refusal carries: ``role:`` and the set's members.

    One member today in every set (``role:expert``, ``role:admin``); a set of more would
    name them all, sorted and joined by ``|``, because the refusal is "any of these".
    """
    return "role:" + "|".join(sorted(required))

#: `R-50`. The capability a refused caller is told they are missing, in the
#: ``required_capability`` detail the catalog already declares safe for
#: ``permission_denied``. **The value names the act, not the credential**: the client can
#: already read ``is_default_credential`` off the exchange, so naming the capability after
#: the credential would give one fact two names, while naming it after the act tells a
#: caller what to do about it.
PASSWORD_CHANGED_CAPABILITY: Final[str] = "password_changed"

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
    their decisions. **No role is carried**, not even since `R-55` gave accounts one: what a
    subject may do is read from its row on every request (:class:`AccountStanding`) and
    decided by the registers before a handler runs, so a role in the subject would be a
    second, older answer to a question only the row can answer now. The fourth field arrived
    with `R-37`; since `W49-SEAL-01` the seam publishes the login and the label the row
    holds rather than the credential's copies.

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
    #: **Is this a statement about what the subject may do?** No, and the line is worth
    #: drawing. A display name says nothing about that; it is the same kind of fact as
    #: ``login``, which has travelled here since wave 34. What a subject may do is the role
    #: set `R-55` ruled in, which is read from the row by :class:`AccountStanding` and never
    #: carried on this object.
    #:
    #: **Since `W49-SEAL-01` the published value is the row's**, not the credential's: the
    #: seam replaces the minted label with :attr:`AccountStanding.display_label` before it
    #: publishes the subject, so the label a decision records is the account's current one.
    display_label: str


@dataclass(frozen=True, slots=True)
class IssuedCredential:
    """What the exchange hands back: the credential, its lifetime, and one fact about it.

    The third field is `R-50`'s and it is a fact about the **account**, not about the
    credential's bytes: whether the password this credential was minted for is still the
    one the deployment seeded. It is answered here because ``issueToken`` and
    ``changePassword`` are the two moments at which a client can be told, and being told is
    the whole point -- a screen that had to *discover* the state would discover it by
    meeting a refusal, which is the shape `R-50` was ruled against.

    **It is not in the credential's payload and must not be**, which is why it is a field
    of this record rather than of :class:`Subject`. The seam reads it from the account's
    own row on every guarded request (:class:`AccountStanding`), so the payload would be a
    second and older copy of a value that decides whether a request is refused -- and two
    sources for one refusal is one more than can be right.
    """

    token: str
    expires_in: int
    #: `R-50`. **No default**, for :attr:`Subject.token_epoch`'s reason: a caller that could
    #: omit it would answer the client a state it assumed rather than one it read, and the
    #: answer it would assume is the permissive one.
    is_default_credential: bool


@dataclass(frozen=True, slots=True)
class AccountStanding:
    """What the seam re-reads about an account on every request it guards.

    Facts about the account, none about the credential's bytes, read together in one
    statement because they are the parts of one decision -- whether this request is served,
    and as whom: the generation of credentials it accepts, whether it is still on a default
    password, whether it is archived, whether its profile is complete, the role set it
    holds, and the login and display label its row holds now (`W49-SEAL-01`).

    **No field has a default**, for :attr:`Subject.token_epoch`'s reason: a constructor that
    could omit ``roles`` or ``archived`` would serve a request under a standing it assumed
    rather than one it read, and the assumable value is the permissive one.

    It is the seam's own vocabulary and not the ``access`` boundary's. The adapter between
    them translates, exactly as it does for :class:`Subject`: this module does not import
    that boundary's models, and that boundary does not learn what a credential is.
    """

    token_epoch: int
    #: `R-50`. ``True`` while the account must change its password: still the one it was
    #: seeded with, or one an administrator reset (`W49-PLAN.md` section 3.1).
    is_default_credential: bool
    #: `R-61`. An archived account has no standing a request may be served under: it is
    #: refused as ``authentication_required``, exactly like a revoked credential.
    archived: bool
    #: `R-59`. ``False`` until the account gave its names (and, for a legacy login, its
    #: e-mail); such an account reaches :data:`OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES` only.
    profile_complete: bool
    #: `R-55`. The role set, in this module's vocabulary (:data:`ROLE_EXPERT`,
    #: :data:`ROLE_ADMIN`). Empty is a valid set.
    roles: frozenset[str]
    #: The login and the display label the row holds **now**. Published on the subject in
    #: place of the ones minted into the credential, so a completed or renamed profile is
    #: visible on the next request rather than after the credential expires.
    login: str
    display_label: str


@runtime_checkable
class AccountStandings(Protocol):
    """The one thing the seam needs from a database, and nothing more.

    One method. It cannot read a password, cannot list accounts, cannot write and cannot be
    handed a login -- only the opaque identity the credential itself carries. A wider port
    here would be a wider thing for the seam to be tempted by: this module is on the path of
    every request, and the narrower its reach the fewer decisions it can make by accident.

    It was ``CredentialEpochs`` and answered one integer until `R-50`. What widened is the
    **answer**, not the number of questions: a second method beside this one would be two
    reads of one row inside one decision, and this one already reads that row.
    """

    def standing_of(self, user_uid: str) -> AccountStanding | None:
        """This account's current standing, or ``None`` when there is no such account.

        ``None`` is a **refusal**, never a permissive default. An account that no longer
        exists must not keep authorising requests until its last credential expires, and a
        deployment whose lookup cannot answer must fail closed.
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

    def issue(
        self,
        subject: Subject,
        *,
        is_default_credential: bool,
        now: float | None = None,
    ) -> IssuedCredential:
        """Mint a credential for ``subject``.

        ``now`` is a parameter so a test can state the clock instead of sleeping. The
        payload carries the issue and expiry instants as whole seconds of Unix time; the
        *response* carries a lifetime and never a clock reading, because two clocks that
        must agree are two ways to be wrong.

        ``is_default_credential`` is `R-50`'s and it is **required**, with no default, for
        :attr:`Subject.token_epoch`'s reason: the caller has to have read it from the
        account's row rather than assumed it, and the value it would assume is the
        permissive one. It travels on the returned :class:`IssuedCredential` and **not into
        the payload below**: the seam answers "is this account still on its seeded password"
        from the row on every guarded request, and a copy in the credential would be an
        older answer to the same question, sitting on the caller's side of the wire.
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
            # record before this method was reached. Still minted and still required by
            # `verify` -- it is part of the `am2` body, and dropping a required field would
            # be a new format that signs everybody out -- but since `W49-SEAL-01` it is not
            # what a request is served under: `AccountStanding` now carries the row's label
            # on the read the seam makes anyway, and `require_authorization` publishes
            # that one. The price this comment used to state -- a rename visible only on
            # the next credential -- is gone with it, and it mattered more than a rename:
            # an account that completes its profile changes its label from a login to the
            # name form, and the decision ledger writes the label it is handed.
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
            is_default_credential=is_default_credential,
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
    environ: Mapping[str, str], *, standings: AccountStandings | None = None
) -> object:
    """The dependency that guards the surface, closed over this environment's signer.

    A factory rather than a module-level dependency reading ``os.environ``, because
    ``create_app(environ=...)`` exists precisely so that a second application can be built
    with a different configuration in the same process -- `W13-BASE` builds one that way for
    the `D-7` case, and `W5CERT-DEF-2` is the defect that happened the last time a component
    reached for the process environment instead of the injected mapping.

    ``standings`` is how revocation -- and, since `R-50`, the default-credential refusal --
    reaches this seam, and it is a **keyword argument with a ``None`` default that
    refuses**, not an optional feature. ``None`` means this application was assembled
    without a way to read an account's standing, and a deployment that cannot tell a live
    credential from a revoked one must answer ``authentication_required`` rather than guess
    -- the same bargain the module note already strikes for a missing deployment secret.
    ``create_documentation_app`` is the caller that passes none, and it can serve no request
    anyway. It was called ``epochs`` until `R-50` widened what it answers.
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

        **And, since `R-50`, one refusal that is not that one.** An account still on the
        password this deployment seeded it with reaches
        :data:`OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` and nothing else; every other
        operation answers ``permission_denied`` with
        ``required_capability: password_changed``. It is a **403 and deliberately not a
        401**: the caller is authenticated, this deployment knows exactly who they are, and
        answering "we do not accept this credential" would send them back to sign in again
        with the one password that will produce the same answer for ever. It says nothing
        an attacker could not already work out, either -- that a deployment's seeded
        password is its seeded password is in the migration's own docstring.

        **Since `W49-SEAL-01`, the four registers in their fixed order** (the module note
        lists them): the standing -- archived or stale is ``authentication_required`` --
        then the default credential, then the incomplete profile, then the role set. Each
        later refusal is a 403 for the 401's reason above: the subject is known, and the
        refusal names what it lacks. The order is the plan's (`W49-PLAN.md` section 3.2),
        and it is what makes an account that is both seeded and incomplete reach exactly
        the intersection of the two registers.
        """
        operation = _operation_of(request)
        if operation in UNAUTHENTICATED_OPERATIONS:
            return
        if signer is None or credentials is None or standings is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        subject = signer.verify(credentials.credentials)
        if subject is None:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        # The credential is genuine and unexpired. Only now is the row read, and only now
        # can this request be refused for having been revoked. The order is deliberate: a
        # forged credential must not cost a database round trip, or an unauthenticated
        # caller can make this deployment query on demand.
        standing = standings.standing_of(subject.user_uid)
        # 1. Standing. No such account, an archived one (`R-61`), or a credential minted
        #    under another generation: one refusal for all three, for the reason the
        #    exchange gives one answer -- telling a caller *which* would tell them the
        #    account exists.
        if (
            standing is None
            or standing.archived
            or standing.token_epoch != subject.token_epoch
        ):
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        # 2. `R-50`, and the order matters: a revoked credential on a default password is
        #    refused as revoked, because "this deployment does not accept this credential"
        #    is the stronger and less informative answer. An unreadable operation reached
        #    this line only by not being in the open register, and it is not in this one
        #    either: it is refused, like everything else this seam cannot identify.
        if standing.is_default_credential and (
            operation not in OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES
        ):
            raise DomainError(
                ErrorCode.PERMISSION_DENIED,
                required_capability=PASSWORD_CHANGED_CAPABILITY,
            )
        # 3. `R-59`. An account that has not given its names and e-mail reaches the way out
        #    of that state and nothing else.
        if not standing.profile_complete and (
            operation not in OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES
        ):
            raise DomainError(
                ErrorCode.PERMISSION_DENIED,
                required_capability=PROFILE_COMPLETED_CAPABILITY,
            )
        # 4. `R-60`. Any of the operation's roles; the empty set is any complete account.
        #    A named operation with no line in the register is refused to everyone -- the
        #    register has no default -- and says nothing about what would open it.
        if operation is None:
            required = ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION
        elif operation in OPERATION_ROLES:
            required = OPERATION_ROLES[operation]
        else:
            raise DomainError(ErrorCode.PERMISSION_DENIED)
        if required and required.isdisjoint(standing.roles):
            raise DomainError(
                ErrorCode.PERMISSION_DENIED,
                required_capability=role_capability(required),
            )
        # Published, with the login and display label the row holds now: the credential's
        # copies were true when it was minted, and a profile completed or renamed since is
        # what every later request must act on. The identity and the epoch are the
        # credential's own, which the checks above have just proved current.
        request.state.subject = Subject(
            user_uid=subject.user_uid,
            login=standing.login,
            token_epoch=subject.token_epoch,
            display_label=standing.display_label,
        )

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
