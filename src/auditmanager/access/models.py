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
    "MAX_LOGIN_LENGTH",
    "USER_UID_PATTERN",
    "USER_UID_PREFIX",
    "UserRecord",
    "UserUid",
    "is_user_uid",
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
    """

    user_uid: UserUid
    login: str
    is_default_credential: bool
    created_at: datetime
    password_updated_at: datetime
    token_epoch: int
    token_epoch_updated_at: datetime


def is_user_uid(value: object) -> bool:
    """True when ``value`` is a syntactically valid user identity."""
    return (
        isinstance(value, str)
        and value.startswith(f"{USER_UID_PREFIX}_")
        and is_valid_ulid(value[len(USER_UID_PREFIX) + 1 :])
    )
