"""Identity for the ``access`` boundary: users, their passwords, and the port over them.

What is here is one aggregate -- a user with a login and a password -- and the three
operations the rest of the system needs from it: find one, prove a password, create one.

What is deliberately **not** here: sessions, tokens, cookies, roles, permissions and
object-level authorization. The README calls this boundary "identity/session/object
authorization policies and ports"; this is the identity half of the first word. The rest
arrives with the work on users and rights that follows the alpha, and inventing its shape
now would mean negotiating it twice.

**Wave 39 added a password change and revocation, and neither brings a token in here.**
``token_epoch`` is one integer per account: the generation of credentials that account
accepts. This boundary raises it; :mod:`auditmanager.api.security` stamps it into what it
mints and compares it on what it is shown. That is the whole of the coupling, and it is why
revocation could be added without this package learning what a credential looks like.

Changing a password raises the epoch **in the same statement** that writes the new digest,
because a password change that leaves the old password's credentials working is a password
change in name only. ``python -m auditmanager.access.revoke`` is the operator's half, for
the case that has no password behind it -- the pilot ended, and the credentials handed out
during it must stop working.

One account is seeded by migration ``0006_app_user``: ``admin``, with the password
``password``. It is an owner decision for a short window, and it is recorded rather than
hidden -- the row carries ``is_default_credential``, every sign-in with it logs a
warning, and ``python -m auditmanager.access.check`` names it without anybody logging in.
"""

from __future__ import annotations

from auditmanager.access.models import (
    LOGIN_PATTERN,
    MAX_LOGIN_LENGTH,
    USER_UID_PATTERN,
    USER_UID_PREFIX,
    UserRecord,
    UserUid,
    is_user_uid,
    normalize_login,
)
from auditmanager.access.passwords import (
    ALGORITHM,
    ITERATIONS,
    MAX_PASSWORD_LENGTH,
    StoredPassword,
    hash_password,
    is_the_same_password,
    verify_password,
)
from auditmanager.access.ports import UserRepository as UserRepositoryPort
from auditmanager.access.repository import (
    CREDENTIALS_REVOKED,
    DEFAULT_CREDENTIAL_WARNING,
    UserRepository,
)

__all__ = [
    "ALGORITHM",
    "CREDENTIALS_REVOKED",
    "DEFAULT_CREDENTIAL_WARNING",
    "ITERATIONS",
    "LOGIN_PATTERN",
    "MAX_LOGIN_LENGTH",
    "MAX_PASSWORD_LENGTH",
    "USER_UID_PATTERN",
    "USER_UID_PREFIX",
    "StoredPassword",
    "UserRecord",
    "UserRepository",
    "UserRepositoryPort",
    "UserUid",
    "hash_password",
    "is_the_same_password",
    "is_user_uid",
    "normalize_login",
    "verify_password",
]
