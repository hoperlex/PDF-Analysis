"""Password hashing for the ``access`` boundary: PBKDF2-HMAC-SHA256, and nothing else.

Why PBKDF2 and why no new dependency
------------------------------------
The legacy portal hashed with ``pbkdf2_sha256`` and that choice is kept: it is a
standards-named KDF (RFC 8018), it is what any operator migrating an old hash would
expect, and :func:`hashlib.pbkdf2_hmac` ships in the standard library. ``passlib`` would
add a dependency to the runtime closure to supply an algorithm CPython already has, and
a parser for an encoded string this module does not need -- the parameters live in their
own columns, so there is nothing to parse and nothing to mis-parse.

What this module guarantees
---------------------------
* **A salt per user, from :mod:`secrets`.** Two users with the same password have
  different digests, so a digest is never evidence that two accounts share a password
  and a precomputed table is worthless against the whole table at once.
* **Comparison through :func:`hmac.compare_digest`.** ``==`` on bytes returns at the
  first differing byte, which leaks a prefix length to anyone who can time the call.
  This module contains no ``==`` between a stored digest and a computed one.
* **The cost is a recorded parameter, not a constant read at verification time.**
  :data:`ITERATIONS` is what *new* hashes are written with. Verification uses the
  iteration count stored beside the digest, so raising the constant later leaves every
  existing row verifiable instead of locking its owner out.
* **The digest never reaches a log by accident.** :class:`StoredPassword` redacts its
  own ``repr``; a dataclass-generated one would print the salt and the digest into any
  traceback, f-string or debug log that touched it.

What it deliberately does not do
--------------------------------
No password *policy* -- no minimum length, no complexity rule, no history, no expiry.
Registration and password change are the next piece of work; a policy invented here
would have to be renegotiated there. The two bounds that are enforced are mechanical:
a password must be non-empty, and it is capped at :data:`MAX_PASSWORD_LENGTH` so an
unbounded body cannot be fed to the KDF.

No pepper and no encryption of the digest. Either would put a key somewhere, and there
is no key-management story in this system yet; claiming one by storing the key next to
the data would be worse than not claiming it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ALGORITHM",
    "DERIVED_KEY_BYTES",
    "ITERATIONS",
    "MAX_PASSWORD_LENGTH",
    "SALT_BYTES",
    "StoredPassword",
    "hash_password",
    "is_the_same_password",
    "spend_a_verification",
    "verify_password",
]

#: The only algorithm this module writes or accepts. A row naming anything else is
#: refused rather than guessed at: a hash whose algorithm is unknown cannot be verified,
#: and treating it as a mismatch would silently turn an upgrade bug into "wrong password".
ALGORITHM: Final[str] = "pbkdf2_sha256"

#: Iterations for a hash written today. OWASP's 2023 password-storage guidance for
#: PBKDF2-HMAC-SHA256 is 600_000. Measured on this lane's interpreter at
#: 0.113 s per derivation (`.venv/bin/python`, single call, 2026-09-22), which is the
#: intended cost: it is charged once per login attempt and multiplied by every guess an
#: attacker makes offline.
ITERATIONS: Final[int] = 600_000

#: 128 bits of salt from the OS CSPRNG. A salt is not secret; it must only be unique.
SALT_BYTES: Final[int] = 16

#: The derived key is 32 bytes -- the natural output width of the underlying SHA-256.
DERIVED_KEY_BYTES: Final[int] = 32

#: An upper bound on what is fed to the KDF. PBKDF2's cost is dominated by the iteration
#: count rather than by the input length, so this is not a cost control; it stops a
#: multi-megabyte body from being carried through the boundary and into a database column
#: that has its own CHECK.
MAX_PASSWORD_LENGTH: Final[int] = 1024


@dataclass(frozen=True, slots=True)
class StoredPassword:
    """Everything needed to verify one password, and nothing that identifies its owner.

    The four fields are exactly the four columns of ``app_user`` that describe the
    credential. They travel together because verifying with parameters other than the
    ones a digest was written with does not produce "wrong password", it produces a
    meaningless answer.
    """

    algorithm: str
    iterations: int
    salt: str
    digest: str

    def __repr__(self) -> str:
        """Redacted on purpose; see the module docstring.

        The algorithm and the iteration count are kept because they are operational
        facts an operator needs when reading a log, and neither helps an attacker who
        does not already have the digest.
        """
        return (
            f"StoredPassword(algorithm={self.algorithm!r}, "
            f"iterations={self.iterations}, salt=<redacted>, digest=<redacted>)"
        )


def _derive(password: str, *, salt: bytes, iterations: int) -> bytes:
    if not isinstance(password, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the password must be text",
        )
    if not password:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the password must not be empty",
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"the password must be at most {MAX_PASSWORD_LENGTH} characters",
        )
    if iterations < 1:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the iteration count must be positive",
        )
    # UTF-8, with no Unicode normalisation. Normalising would silently accept a password
    # that is not the one that was typed; refusing to normalise means a user who types
    # the same characters gets the same bytes, which is the property that matters.
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=DERIVED_KEY_BYTES,
    )


def hash_password(password: str, *, iterations: int = ITERATIONS) -> StoredPassword:
    """Hash ``password`` with a fresh random salt.

    ``iterations`` is an argument so a test can run at a cost it can afford, and so a
    future rehash-on-login can write a higher count without this module changing. The
    value used is stored in the returned record, never assumed at verification time.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt=salt, iterations=iterations)
    return StoredPassword(
        algorithm=ALGORITHM,
        iterations=iterations,
        salt=salt.hex(),
        digest=digest.hex(),
    )


def verify_password(stored: StoredPassword, password: str) -> bool:
    """True when ``password`` reproduces ``stored``'s digest under ``stored``'s parameters.

    A stored record naming an algorithm this module does not implement raises rather than
    returning ``False``. Returning ``False`` would report an unverifiable credential as a
    wrong password -- a silent fallback, and the one that costs an operator the most time.
    """
    if stored.algorithm != ALGORITHM:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message=f"stored password uses an unsupported algorithm: {stored.algorithm!r}",
        )
    try:
        salt = bytes.fromhex(stored.salt)
    except ValueError as exc:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message="stored password salt is not hexadecimal",
        ) from exc
    computed = _derive(password, salt=salt, iterations=stored.iterations)
    try:
        expected = bytes.fromhex(stored.digest)
    except ValueError as exc:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message="stored password digest is not hexadecimal",
        ) from exc
    return hmac.compare_digest(computed, expected)


def is_the_same_password(one: str, other: str) -> bool:
    """True when two typed passwords are the same string.

    Used by password change to refuse a "new" password that is the old one. That refusal
    is **mechanical, not a policy**: this module still has no minimum length, no complexity
    rule, no history and no expiry, and inventing one here would have to be renegotiated
    when a policy is really specified. What it enforces is that a password change changes
    the password -- otherwise the operation is a credential revocation wearing a password
    change's name, and a reviewer who typed the same string twice would be told their
    password had changed when it had not.

    Compared with :func:`hmac.compare_digest` over UTF-8 bytes, for the same reason
    everything else in this module is: one of the two operands is a live password. ``==``
    on ``str`` returns at the first differing character, so an attacker who can present one
    side and time the call learns a prefix of the other. ``compare_digest`` refuses a
    non-ASCII ``str`` outright, which is why both sides are encoded first rather than
    handed over as text -- a password with a Cyrillic character in it is an ordinary
    password here and must not raise.

    Neither side is hashed. Both are already in this process, in the clear, because the
    caller has just been handed both by the request that wants to change one into the
    other; deriving a key from each to compare them would cost a quarter of a second and
    protect nothing that is not already in memory.
    """
    return hmac.compare_digest(one.encode("utf-8"), other.encode("utf-8"))


def spend_a_verification(password: str, *, iterations: int = ITERATIONS) -> None:
    """Do the work of one verification and discard the answer.

    Called when no user matched the login. Without it, an unknown login returns in
    microseconds and a known one in ~0.1 s, which is a user-enumeration oracle that needs
    no response body at all -- a stopwatch is enough. The work is real: a throwaway salt
    and the same iteration count, so the two paths cost the same.

    A password that fails the mechanical bounds above is not spent on: it could not have
    matched any stored digest either, so both paths still agree.
    """
    try:
        _derive(password, salt=secrets.token_bytes(SALT_BYTES), iterations=iterations)
    except DomainError:
        return
