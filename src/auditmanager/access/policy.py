"""The password policy: `R-48`, exactly as ruled, and nothing it does not say.

`OWNER_RULINGS_2026-09-17.md` §3.16, `R-48` -- the owner took the general shape first and
then said the specifics were the integrator's to ask, not to assume. Asked, and answered:

* **minimum length 8** -- NIST SP 800-63B's floor; the lockout (`W40-LIMIT`) already makes
  guessing impractical, so length defends a leaked hash, not a guesser;
* **a *contextual* blocklist and nothing else** -- the account's own login, the product's
  name, the account's own current password. **Nothing stored, nothing to license, nothing
  to go stale**: every entry is a fact this call already has in hand, never a corpus read
  from a file or a dependency;
* **no expiry** -- not this module's concern and there is no field here for one;
* **confirmation** -- a second entry of the new password, ruled into the *UI*
  (`web/src/features/change-password`), not this boundary. There is nothing to confirm
  against here: this function sees one candidate, not two.

**Why this is a policy and not a transport bound.** `api/routers/auth.py`'s
``ChangePasswordRequest`` bounds ``new_password`` to ``1..1024`` characters and says so
itself: *"these are not a password policy... a policy invented here would have to be
renegotiated when a policy is really specified."* It is specified now, and it is specified
**here**, in the access context, because a password policy is a statement about accounts
and credentials -- exactly this boundary's subject -- and not about the shape of an HTTP
body. `api/routers/auth.py` still bounds the body; this module decides whether a
mechanically-valid body is a password this deployment will accept.

**Why the current-password entry is not re-checked here.**
:func:`auditmanager.access.repository.UserRepository.change_password` already refuses a
new password that equals the current one -- :func:`~auditmanager.access.passwords.
is_the_same_password`, compared with :func:`hmac.compare_digest` because one side is a live
password. That refusal **is** the blocklist's third entry: "the current password" and "the
password you are changing away from" name the same string. A second comparison here would
be the same check twice, with two messages that could disagree -- the kind of duplication
this tree avoids everywhere else. This module therefore enforces the first two entries --
the login and the product name -- and the length floor; the caller is expected to have
already run (or to run) the current-password check, and
:mod:`auditmanager.access.repository` does.

**`D-101`, named and not closed here.** With a contextual-only list and an 8-character
floor, the literal string ``password`` is itself a legal password everywhere this module
is *not* the current-password check -- it is exactly 8 characters, it is not a login (no
login folds to it: `LOGIN_PATTERN` would accept it, but nobody's login is required to be
it) and it is not the product's name. It is refused only when it is also the *current*
password, which is `change_password`'s job and not this module's. **The one-line repair
recorded against `D-101`** -- adding the shipped default credential value to the
contextual list -- **is not taken here**: the owner has been asked and the ruling record
says so explicitly, and this module must not make that call by adding a fourth blocklist
entry the ruling did not name. `test_the_d101_gap_is_still_open` in
``tests/integration/access/test_password_policy.py`` states the gap as a passing
assertion, so a future reader finds it recorded rather than rediscovers it as a defect.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MIN_PASSWORD_LENGTH",
    "PRODUCT_NAME",
    "enforce_password_policy",
]

#: NIST SP 800-63B's floor. See the module docstring for why length and not complexity.
MIN_PASSWORD_LENGTH: Final[int] = 8

#: The product's name, as it is titled everywhere a reviewer reads it --
#: ``web/src/app/layout.tsx``'s ``<title>`` is ``"AuditManager — PC-01"`` and
#: ``pyproject.toml`` names the distribution ``auditmanager-foundation``. Spelled once here
#: because the blocklist compares against it, not against a document that could drift from
#: it; there is no second copy for this constant to disagree with.
PRODUCT_NAME: Final[str] = "AuditManager"


def enforce_password_policy(new_password: str, *, login: str) -> None:
    """Refuse ``new_password`` when `R-48` says a deployment must not accept it.

    Raises :class:`~auditmanager.shared.errors.DomainError` with
    :data:`~auditmanager.shared.errors.ErrorCode.VALIDATION_FAILED` -- the catalog's
    existing code for "this is a statement about the request", the same code
    ``api/routers/auth.py`` already documents for a refused new password. **No error code
    is added**: `D-18`, and the catalog stays frozen at 22.

    Two checks, run in the order that costs the least to explain:

    1. **length.** Fewer than :data:`MIN_PASSWORD_LENGTH` characters is refused before the
       blocklist is even consulted -- a short password is wrong regardless of what it says.
    2. **the contextual blocklist's first two entries.** Case-folded, because a blocklist
       that only caught ``AuditManager`` and let ``auditmanager`` or ``AUDITMANAGER``
       through would be a blocklist a reviewer could defeat by holding the Shift key
       differently, and `login` is already folded to lower case by
       :func:`~auditmanager.access.models.normalize_login` before it ever reaches a row --
       comparing case-sensitively here would make the rule depend on typing the login back
       in exactly the casing it happened to be typed in at sign-up, which is not a security
       property, just an accident of the keyboard.

    The blocklist's **third** entry -- the current password -- is not checked here; see
    the module docstring for where it is and why it stays there.
    """
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"a password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    folded = new_password.casefold()
    if folded == login.casefold():
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a password may not be the account's own login",
        )
    if folded == PRODUCT_NAME.casefold():
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a password may not be the product's name",
        )
