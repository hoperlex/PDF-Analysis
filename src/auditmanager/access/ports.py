"""The ``access`` boundary's user port: the three operations, and no fourth one.

The port is what a caller outside this boundary is allowed to depend on. It is narrow
for the same reason :mod:`auditmanager.storage.port` is: an operation the port does not
offer is an invariant the adapter can still hold.

The :class:`~sqlalchemy.orm.Session` is a parameter rather than adapter state, as in
:mod:`auditmanager.documents.repository`: the caller owns the transaction, so creating a
user and whatever else that request writes commit or roll back together.

In particular the port has **no way to read a password digest and no way to supply one**.
``create_user`` takes a plaintext password and hashes it inside the adapter;
``authenticate`` takes a plaintext password and answers yes or no. Neither returns
credential material, so no caller can grow a habit of moving digests around, comparing
them itself, or logging one. That is enforced by the return types rather than by a
convention: :class:`~auditmanager.access.models.UserRecord` has no field to put one in.

It has no ``list_users`` and no ``delete_user``. Registration is still the next piece of
work and this port still does not guess at its shape.

**Wave 39 added three, and they are one mechanism.** ``change_password``,
``revoke_credentials`` and ``token_epoch`` exist because a credential this deployment has
already minted could not be taken back: it is a signed statement with an expiry, so until
that expiry the only lever was rotating the deployment secret, which signs everybody out
and needs a redeploy. ``token_epoch`` is the lever -- the generation of credentials an
account accepts -- and the other two are the two ways it moves: a reviewer changing their
own password, and an operator ending the pilot.

The port still has no *session* concept and no token in it anywhere. It does not mint, it
does not verify, and it cannot read or write a signing key. What it publishes is one
integer that the seam stamps and compares; the seam's half stays in
:mod:`auditmanager.api.security`, and neither module imports the other.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from auditmanager.access.models import UserRecord

__all__ = ["UserRepository"]


@runtime_checkable
class UserRepository(Protocol):
    """Find a user, prove a password, create a user."""

    def find_by_login(self, session: Session, login: str) -> UserRecord | None:
        """The user with this login, or ``None`` when there is none.

        The login is normalised by the implementation, so ``" Admin "`` and ``"admin"``
        reach the same row. A malformed login is a
        :class:`~auditmanager.shared.errors.DomainError`, not a ``None``: "this cannot
        be a login" and "no such user" are different answers and the caller may need to
        tell them apart.
        """

    def authenticate(
        self, session: Session, login: str, password: str
    ) -> UserRecord | None:
        """The user, when the password is theirs; ``None`` in every other case.

        One answer covers "no such user" and "wrong password" on purpose: two answers
        would let anyone with the login form enumerate which accounts exist. The
        implementation must also spend comparable work on both paths, because a timing
        difference is the same oracle with extra steps.
        """

    def create_user(self, session: Session, login: str, password: str) -> UserRecord:
        """Create a user and return them.

        Raises :class:`~auditmanager.shared.errors.DomainError` with
        :data:`~auditmanager.shared.errors.ErrorCode.CONFLICT` when the login is taken.
        The caller never learns the digest: it is written and forgotten.
        """

    def change_password(
        self,
        session: Session,
        *,
        user_uid: str,
        current_password: str,
        new_password: str,
    ) -> UserRecord | None:
        """Replace a password and revoke every credential minted under the old one.

        ``None`` when the current password is not this account's, or when there is no such
        account -- one answer, as everywhere else on this port.

        The two halves are **required to be one write**. An implementation that changed the
        digest and raised the epoch in two statements would have a window in which the
        password is new and the old credentials still work, and that window is the whole of
        what this operation exists to close.

        The returned record carries the **new** epoch, so a caller that mints a fresh
        credential from it mints one the next request will accept. Raises
        :class:`~auditmanager.shared.errors.DomainError` with
        :data:`~auditmanager.shared.errors.ErrorCode.VALIDATION_FAILED` when the new
        password is the current one, or fails the mechanical bounds.
        """

    def revoke_credentials(
        self, session: Session, *, login: str | None = None
    ) -> tuple[UserRecord, ...]:
        """Raise the credential epoch for one account, or for every account.

        ``login=None`` means every account. It is a default rather than a separate method
        because it is one statement's difference, and the caller that meant one account and
        typed none would otherwise find the difference at the second method's name rather
        than at its own.

        Returns the records that moved, carrying their new epochs. Empty means nothing
        matched, which is a fact and not an error: whether "nothing to revoke" is a problem
        is the caller's question.
        """

    def token_epoch(self, session: Session, user_uid: str) -> int | None:
        """The generation of credentials this account accepts, or ``None`` for no account.

        This is the read the authorization seam performs on every request it guards, so it
        must stay a single indexed lookup of a single integer. ``None`` is a refusal and
        never a permissive default: an account that is gone revokes its own credentials.
        """
