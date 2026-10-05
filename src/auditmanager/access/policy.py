"""The password policy: `R-48`, exactly as ruled, and nothing it does not say.

`OWNER_RULINGS_2026-09-17.md` §3.16, `R-48` -- the owner took the general shape first and
then said the specifics were the integrator's to ask, not to assume. Asked, and answered:

* **minimum length 8** -- NIST SP 800-63B's floor; the lockout (`W40-LIMIT`) already makes
  guessing impractical, so length defends a leaked hash, not a guesser;
* **a *contextual* blocklist and nothing else** -- the account's own login, the product's
  name, the account's own current password, and, since `D-101` was closed on 2026-09-29,
  **the password this deployment ships with**. **Nothing stored, nothing to license,
  nothing to go stale**: every entry is a fact this call already has in hand, never a
  corpus read from a file or a dependency;
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

**`D-101`, and it is closed rather than named.** With a contextual-only list and an
8-character floor, the literal string ``password`` was itself a legal password everywhere
this module is *not* the current-password check -- it is exactly 8 characters, it is not a
login (no login folds to it: `LOGIN_PATTERN` would accept it, but nobody's login is
required to be it) and it is not the product's name. It was refused only when it was also
the *current* password, which is `change_password`'s job and not this module's, so the
account forced off the shipped credential could set it straight back on the next change.
Driven by `W47-JUDGE-X` §1.3 against the built API: from the default, ``"Password"`` with
a capital ``P`` answered **200 changed**.

**The owner answered on 2026-09-29: close it now.** The repair is the one `D-101`'s own row
records -- :data:`SHIPPED_DEFAULT_PASSWORD` joins the contextual list. It is still
**context about this deployment and not a stored corpus**: the system already knows this
value, ``access/check.py`` is built on knowing it, and it costs no file, no dependency and
no licence. It is the one entry with a **second copy in the tree** -- the seed in
``db/migrations/versions/20260922_0006_app_user.py`` -- so
``tests/integration/access/test_password_policy.py`` reads that literal out of the
migration and compares it here, and a deployment that ships a different default reddens
there rather than blocking nothing.

The test that recorded the gap is the test that now proves it shut: it was
``test_the_d101_gap_is_still_open`` and it is ``test_the_d101_gap_is_closed`` in
``tests/integration/db/test_app_user_repository.py``, the same two changes with the second
one's expectation turned round. It was not deleted, because deleting it would remove the
record that anybody ever looked.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MIN_PASSWORD_LENGTH",
    "PRODUCT_NAME",
    "SHIPPED_DEFAULT_PASSWORD",
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

#: `D-101`, closed by the owner on 2026-09-29. The password ``0006_app_user`` seeds the one
#: account with, and which `R-50` exists to force every deployment off. It is **published**
#: -- in that migration, in ``DEPLOYMENT_RUNBOOK.md`` and in the deployment notes -- so
#: spelling it here leaks nothing that is not already public, and naming it in the refusal
#: message tells a reviewer nothing an attacker does not have.
#:
#: **It is a second copy and it is guarded as one.** Unlike :data:`PRODUCT_NAME`, this value
#: exists twice: here, and as ``SEED_PASSWORD`` in the migration that writes it. A
#: deployment that changed the seed and left this behind would have a blocklist entry that
#: refuses nothing, which is the quietest kind of security defect. The test beside this
#: module reads the migration's literal and compares it, so the two cannot drift silently.
SHIPPED_DEFAULT_PASSWORD: Final[str] = "password"  # noqa: S105 - the published default


def enforce_password_policy(
    new_password: str, *, login: str, context: Iterable[str | None] = ()
) -> None:
    """Refuse ``new_password`` when `R-48` says a deployment must not accept it.

    Raises :class:`~auditmanager.shared.errors.DomainError` with
    :data:`~auditmanager.shared.errors.ErrorCode.VALIDATION_FAILED` -- the catalog's
    existing code for "this is a statement about the request", the same code
    ``api/routers/auth.py`` already documents for a refused new password. **No error code
    is added**: `D-18`, and the catalog stays frozen at 22.

    Two checks, run in the order that costs the least to explain:

    1. **length.** Fewer than :data:`MIN_PASSWORD_LENGTH` characters is refused before the
       blocklist is even consulted -- a short password is wrong regardless of what it says.
    2. **the contextual blocklist's first, second and fourth entries.** Case-folded,
       because a blocklist
       that only caught ``AuditManager`` and let ``auditmanager`` or ``AUDITMANAGER``
       through would be a blocklist a reviewer could defeat by holding the Shift key
       differently, and `login` is already folded to lower case by
       :func:`~auditmanager.access.models.normalize_login` before it ever reaches a row --
       comparing case-sensitively here would make the rule depend on typing the login back
       in exactly the casing it happened to be typed in at sign-up, which is not a security
       property, just an accident of the keyboard.

    **``context``, since `W49-ACCESS-01c`** (`W49-PLAN.md` §3.3): further facts this call
    has in hand about the account -- a registration's names and its e-mail's local part --
    each refused exactly as the login is, case-folded, compared whole. Still nothing
    stored and nothing to license: every entry is the applicant's own input.

    The blocklist's **third** entry -- the current password -- is not checked here; see
    the module docstring for where it is and why it stays there. The **fourth**, the
    shipped default (`D-101`), is checked here and nowhere else: it is a fact about the
    deployment rather than about this account, so no other boundary has it in hand.
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
    for entry in context:
        if entry and folded == entry.casefold():
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="a password may not be the account's own name or e-mail",
            )
    if folded == SHIPPED_DEFAULT_PASSWORD.casefold():
        # `D-101`. Folded for the same reason the two entries above are, and here the
        # reason is not hypothetical: the change `W47-JUDGE-X` drove from the shipped
        # default was to ``"Password"``, which differs from it by one shift key and which a
        # case-sensitive entry would have accepted while appearing to close the gap.
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a password may not be the password this system ships with",
        )
