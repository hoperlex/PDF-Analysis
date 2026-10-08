"""The surface the two `W49-SEAL-01` suites drive: real rows, shipped adapters, the real seam.

``test_registration_flow.py`` and ``test_user_management.py`` assert what the account and
registration operations answer **over the database**, through the composition root's own
adapters and the shipped ``CredentialAdapter`` -- so the standing the seam decides on is the
row's, not a stand-in's. Everything runs inside the suite's per-test transaction
(``conftest.session_factory``) and is rolled back with it.

The product ports are this suite's existing stand-ins: nothing here drives a product
operation.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.passwords import hash_password
from auditmanager.access.public import (
    AccountRepository,
    RegistrationRepository,
    UserRepository,
)
from auditmanager.api.routers import build_router
from auditmanager.api.routers.ports import ReleasesPort
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.bootstrap.adapters import (
    AccountAdapter,
    CredentialAdapter,
    RegistrationAdapter,
)
from w13_api_driver import DEPLOYMENT_SECRET, Surface

__all__ = ["ADMIN_ROLES", "credential_for", "identity_surface", "make_account"]

SIGNER = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
assert SIGNER is not None

ADMIN_ROLES = ("expert", "admin")


def identity_surface(
    session_factory: sessionmaker[Session], *, releases: ReleasesPort | None = None
) -> Surface:
    """The served application over the shipped account, registration and credential ports.

    The six product ports are ``None``, as ``create_documentation_app`` passes them: their
    operations are declared and never driven here.
    """
    return Surface(
        build_router(
            projects=None,  # type: ignore[arg-type]
            documents=None,  # type: ignore[arg-type]
            runs=None,  # type: ignore[arg-type]
            findings=None,  # type: ignore[arg-type]
            decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=CredentialAdapter(
                session_factory,
                users=UserRepository(),
                accounts=AccountRepository(),
                signer=SIGNER,
            ),
            accounts=AccountAdapter(session_factory, accounts=AccountRepository()),
            registrations=RegistrationAdapter(
                session_factory, registrations=RegistrationRepository()
            ),
            releases=releases,
        )
    )


def make_account(
    session: Session,
    *,
    login: str,
    names: tuple[str, str, str | None] | None,
    roles: tuple[str, ...] = (),
    password: str = "identity-suite-password-1",
    default: bool = False,
) -> str:
    """One account row, complete (with ``names``) or a legacy one, with ``roles``."""
    from auditmanager.shared.identity.ids import UserUid

    uid = str(UserUid.new())
    stored = hash_password(password)
    last, first, middle = names if names else (None, None, None)
    session.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash, is_default_credential, last_name, first_name, "
            "middle_name, profile_completed_at) VALUES (:uid, :login, :algorithm, "
            ":iterations, :salt, :digest, :default, :last, :first, :middle, "
            "CASE WHEN :complete THEN now() ELSE NULL END)"
        ),
        {
            "uid": uid,
            "login": login,
            "algorithm": stored.algorithm,
            "iterations": stored.iterations,
            "salt": stored.salt,
            "digest": stored.digest,
            "default": default,
            "last": last,
            "first": first,
            "middle": middle,
            "complete": names is not None,
        },
    )
    for role in roles:
        session.execute(
            text("INSERT INTO app_user_role (user_uid, role) VALUES (:uid, :role)"),
            {"uid": uid, "role": role},
        )
    return uid


def credential_for(session: Session, user_uid: str) -> str:
    """A credential minted from the row, under the epoch and label it holds now."""
    login, epoch = session.execute(
        text("SELECT login, token_epoch FROM app_user WHERE user_uid = :u"), {"u": user_uid}
    ).one()
    return SIGNER.issue(
        Subject(user_uid=user_uid, login=login, token_epoch=int(epoch), display_label=login),
        is_default_credential=False,
    ).token
