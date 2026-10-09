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

from pathlib import Path

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
    ReleasesAdapter,
)
from auditmanager.releases.public import ReleaseRepository
from w13_api_driver import DEPLOYMENT_SECRET, Surface

__all__ = ["ADMIN_ROLES", "credential_for", "identity_surface", "make_account"]

SIGNER = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
assert SIGNER is not None

ADMIN_ROLES = ("expert", "admin")


_PRODUCT_VERSION = (Path(__file__).resolve().parents[3] / "VERSION").read_text(encoding="utf-8").strip()


class _CheckedReleasePort:
    """Keep the injected test port visible to the whole-port wiring guard."""

    def __init__(
        self, delegate: ReleasesPort | None, session_factory: sessionmaker[Session]
    ) -> None:
        selected = delegate if delegate is not None else ReleasesAdapter(
            ReleaseRepository(session_factory, product_version=_PRODUCT_VERSION),
            product_version=_PRODUCT_VERSION,
            build_id="b0123456789abcdef",
        )
        if not isinstance(selected, ReleasesPort):
            raise TypeError("release test stand-in does not implement ReleasesPort")
        self._delegate = selected

    def get_product_version(self):
        return self._delegate.get_product_version()

    def list_releases(self, *, user_uid: str):
        return self._delegate.list_releases(user_uid=user_uid)

    def mark_read(self, *, user_uid: str, read_through: str):
        return self._delegate.mark_read(user_uid=user_uid, read_through=read_through)


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
            releases=_CheckedReleasePort(releases, session_factory),
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
