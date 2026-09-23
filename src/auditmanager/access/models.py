"""The values the ``access`` boundary hands out, and the login rule it enforces.

Two things are deliberate.

**No credential material in a returned record.** :class:`UserRecord` carries the
identity, the login, the timestamps and the default-credential flag. It carries no
digest, no salt and no iteration count, so there is no call path that returns a
credential to a caller who only asked who the user is. Verification happens inside the
repository, against columns that never leave it.

**The login is normalised before it is stored, not when it is read.** A stored
``Admin`` that is looked up case-insensitively would let one account be addressed by
many spellings, and uniqueness would then depend on every call site remembering to fold
the case. Instead the boundary folds once, the column holds the folded value, and the
database's own UNIQUE constraint is the guarantee. The CHECK in the migration repeats
the rule, so raw SQL cannot insert a spelling the boundary would have refused.

**A third thing since `R-37`: a login and a display name are different kinds of string
and this module keeps them apart.** A login is an address -- typed, folded, unique, ASCII,
sayable down a telephone. A display name is what other reviewers *read* on a decision
somebody else took: the reviewer's own name, in their own script, not unique, because two
people really can be called the same thing. They are normalised by two functions with two
rules for that reason, and the identity is neither of them -- it is ``user_uid``, which is
why a rename of either changes nothing about who somebody is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity.ulid import is_valid_ulid, new_ulid

__all__ = [
    "LOGIN_PATTERN",
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_LOGIN_LENGTH",
    "USER_UID_PATTERN",
    "USER_UID_PREFIX",
    "UserRecord",
    "UserUid",
    "is_user_uid",
    "normalize_display_name",
    "normalize_login",
]

#: The prefix this boundary allocates its identities under.
#:
#: ``app_user`` is **not** in ``contracts/domain/v1/identifiers.json``: that catalog is
#: frozen and describes the PC-01 analysis domain, which has no user aggregate. So this
#: type deliberately does **not** subclass
#: :class:`auditmanager.shared.identity.OpaqueId` -- doing so would register ``usr`` in
#: the contract's global prefix registry and quietly add a twenty-sixth identity to a
#: catalog a contract test pins. It copies the catalog's *shape* (``<prefix>_<ULID>``,
#: opaque, no decoding of the body) so that when users are contracted, adopting the base
#: class is a renaming rather than a data migration.
USER_UID_PREFIX: Final[str] = "usr"

#: Same body alphabet and length as every other identity in this system.
USER_UID_PATTERN: Final[str] = r"^usr_[0-9A-HJKMNP-TV-Z]{26}$"

_USER_UID_RE: Final[re.Pattern[str]] = re.compile(USER_UID_PATTERN)

#: The login rule, restated in the migration as a CHECK.
#:
#: ASCII, already lower-cased, starting with a letter or a digit. Narrow on purpose: a
#: login is typed at a keyboard by someone who must be able to say it out loud to
#: support, and two logins that differ only by a Unicode confusable are an
#: impersonation, not a feature.
LOGIN_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9._-]{0,99}$"

_LOGIN_RE: Final[re.Pattern[str]] = re.compile(LOGIN_PATTERN)

MAX_LOGIN_LENGTH: Final[int] = 100

#: The longest display name this boundary stores, and the number is **not** this
#: boundary's own.
#:
#: It is ``DecisionEvent.author_label``'s ``maxLength`` in
#: ``contracts/api/v1/openapi.json``, which is the field a display name is eventually
#: written into (`R-37`). A column that allowed a longer one would let an account be given
#: a name that cannot be recorded against a decision -- discovered at the moment an expert
#: records a verdict, which is the worst moment for it. The bound therefore lives where the
#: value is *created*, and the reason it is 128 is written here rather than left to be
#: rediscovered. The migration restates it as a CHECK for the same reason the login pattern
#: is restated there: raw SQL must not be able to write what this boundary would refuse.
MAX_DISPLAY_NAME_LENGTH: Final[int] = 128

#: Anything in the C0 or C1 control range. A display name is rendered on a screen and
#: written into the CSV export, and a newline or a control byte in it is either a broken
#: row or an invisible difference between two names that look identical.
_CONTROL_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1f\x7f-\x9f]")


@dataclass(frozen=True, slots=True)
class UserUid:
    """An opaque user identity: ``usr_`` and a ULID body.

    Immutable and compared by value. The body is never decoded: it carries no creation
    time a caller may read and no order a caller may sort on, for the same reason the
    contract's identities do not.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _USER_UID_RE.match(self.value):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"a user identity must match {USER_UID_PATTERN}",
            )

    @classmethod
    def new(cls) -> "UserUid":
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{USER_UID_PREFIX}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> "UserUid":
        return cls(value)

    def __str__(self) -> str:
        return self.value


def normalize_login(raw: str) -> str:
    """Fold ``raw`` to its canonical stored form, or refuse it.

    Surrounding whitespace is stripped -- it is a copy-paste artifact, not part of a
    name -- and the result is lower-cased. Anything the pattern then refuses is a
    :class:`DomainError`, never a silently repaired value: a login the caller did not
    type is a login they cannot type again.
    """
    if not isinstance(raw, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="the login must be text")
    candidate = raw.strip().lower()
    if not _LOGIN_RE.match(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                "the login must be 1-100 characters of a-z, 0-9, dot, dash or "
                "underscore, and must start with a letter or a digit"
            ),
        )
    return candidate


def normalize_display_name(raw: str) -> str:
    """Fold ``raw`` to its stored form, or refuse it.

    Surrounding whitespace is stripped, as on a login: it is a copy-paste artifact and not
    part of a name. **Nothing else is changed** -- no case folding, no transliteration, no
    ASCII restriction. A login is typed at a keyboard and has to be sayable to support,
    which is why :data:`LOGIN_PATTERN` is as narrow as it is; a display name is *read* and
    is the reviewer's own name, so "Анна Петрова" is the ordinary case rather than an
    exception.

    Three refusals, each because the alternative is a defect rather than an inconvenience:

    * **empty or blank** -- ``author_label`` is ``minLength: 1`` and the ledger refuses an
      empty label, so a blank stored here is a refused write at the moment an expert
      records a verdict;
    * **longer than** :data:`MAX_DISPLAY_NAME_LENGTH` -- same reason, from the other end;
    * **a control character** -- see :data:`_CONTROL_CHARACTERS`.

    A refusal is a :class:`DomainError` and never a silently repaired value, for the reason
    :func:`normalize_login` gives: a name the caller did not type is a name they cannot
    type again.
    """
    if not isinstance(raw, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the display name must be text"
        )
    candidate = raw.strip()
    if not candidate:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the display name must not be empty",
        )
    if len(candidate) > MAX_DISPLAY_NAME_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                f"the display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters"
            ),
        )
    if _CONTROL_CHARACTERS.search(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the display name must not contain control characters",
        )
    return candidate


@dataclass(frozen=True, slots=True)
class UserRecord:
    """One user, as anything outside the repository is allowed to see them.

    ``token_epoch`` is the generation of credentials this account currently accepts. It is
    on the public record and not beside the digest, because it is not credential material:
    it is a small integer that says nothing about the password and is *meant* to travel --
    the seam stamps it into every credential it mints and compares it on every request.
    Reading it tells an attacker how many times this account has been revoked and nothing
    else, and hiding it would mean the one value the seam must check on every request could
    only be reached through the one statement that also reads the digest.

    **The last three are `W40-LIMIT`'s and they are two things, not one.**
    ``failed_sign_ins`` with ``last_failed_sign_in_at`` is the **rate limit** -- how many
    consecutive recent attempts have been refused, and when the last one was. On its own it
    refuses nothing. ``sign_in_blocked_until`` is the **lockout** -- the instant before
    which this account's password is not consulted at all, so that even the right one mints
    nothing. ``None`` means this account may be tried now, and a ``None`` here is **never**
    read as a refusal: a nullable field whose absence closed the door would be one restart
    away from shutting an installation out of itself.

    None of the three is credential material either -- they say how often somebody has been
    wrong, never what the password is -- and none of them travels: no operation returns a
    record, and the one thing this boundary hands the API is a credential. They are on the
    record because the operator's two views of the state
    (:mod:`auditmanager.access.check` and :mod:`auditmanager.access.unlock`) read them, and
    an operator who cannot see a lockout cannot answer the only question a lockout ever
    produces.
    """

    user_uid: UserUid
    login: str
    is_default_credential: bool
    created_at: datetime
    password_updated_at: datetime
    token_epoch: int
    token_epoch_updated_at: datetime
    failed_sign_ins: int
    last_failed_sign_in_at: datetime | None
    sign_in_blocked_until: datetime | None
    #: `R-37`. **The name this reviewer chose, or ``None`` because they have not chosen
    #: one.** It is not credential material and it does not travel by itself: what travels
    #: is :attr:`display_label`.
    #:
    #: **Nullable on purpose, and this is the decision `R-37` left open.** The column could
    #: have been ``NOT NULL`` and backfilled from ``login``, which would have been simpler
    #: and would have destroyed -- in data, on the first upgrade, irreversibly -- the
    #: difference between *an account that has not chosen a name* and *an account whose
    #: reviewer chose their own login*. That difference is the only thing that makes the
    #: fallback below visible, and a fallback nobody can see is the silent fallback
    #: ``AGENTS.md`` §4 forbids. Keeping the ``NULL`` makes the state a query --
    #: ``SELECT login FROM app_user WHERE display_name IS NULL`` -- which is exactly what
    #: ``is_default_credential`` does for the seeded password.
    display_name: str | None

    @property
    def display_label(self) -> str:
        """The name to show for this account. **Never empty, by construction.**

        The reviewer's chosen name when there is one, and their login when there is not.
        The fallback happens **here and nowhere else in the tree**: one expression, on the
        record, so that no call site can invent a second answer and no call site has to
        remember that there is a fallback at all.

        *Why the login and not something else.* A blank is refused by the ledger and by the
        contract (``author_label`` is ``minLength: 1``), so a blank label is a ``500`` on
        the path of an expert recording a verdict. Inventing a name -- "Reviewer 3", a
        prefix of the identity -- is worse: in an append-only ledger a fabricated name is,
        a year later, indistinguishable from one somebody chose, and `P04` exists to learn
        whose judgement was whose. The login is a real string the reviewer typed, it is
        unique, and :data:`LOGIN_PATTERN` bounds it at 1..100 characters -- inside
        ``author_label``'s 1..128 **by construction and not by luck**, which is what makes
        "this label can never be empty and can never be too long" a proof rather than a
        hope.

        *It is not silent.* The fallback is said in four places: this docstring, the
        nullable column above, ``python -m auditmanager.access.check``'s
        ``access-check NO DISPLAY NAME`` line, and the warning migration
        ``0009_reviewer_display_name`` writes into every installation's deployment log.
        """
        return self.display_name or self.login


def is_user_uid(value: object) -> bool:
    """True when ``value`` is a syntactically valid user identity."""
    return (
        isinstance(value, str)
        and value.startswith(f"{USER_UID_PREFIX}_")
        and is_valid_ulid(value[len(USER_UID_PREFIX) + 1 :])
    )
