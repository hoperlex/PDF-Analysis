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

It also has no ``list_users``, no ``delete_user``, no ``set_password`` and no session or
token concept. Password change, registration and sessions are the next piece of work and
belong to whoever specifies them; a port that guessed at their shape now would be a
contract nobody agreed to.
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
