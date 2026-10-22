"""Fixtures for the executors suite: real PostgreSQL, one rolled-back transaction per test.

The run-suite harness (``tests/integration/runs/harness.py``) supplies ``engine`` and
``session`` exactly as ``tests/integration/execution`` binds them, and the API driver
(``tests/integration/api/driver.py``) supplies the served application, so the HTTP-level tests
drive the real edge: the seam, the role register, the envelope and the middlewares.

Nothing here can spend or call a model: the executors context makes no network call at all
in this slice. The rings are generated per test and exist only in memory.
"""

from __future__ import annotations

import base64
import importlib.util
import sys
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

engine = harness.engine
session = harness.session

_DRIVER_NAME = "w13_api_driver"
_DRIVER_PATH = Path(__file__).resolve().parents[1] / "api" / "driver.py"
if _DRIVER_NAME in sys.modules:
    driver: ModuleType = sys.modules[_DRIVER_NAME]
else:
    _driver_spec = importlib.util.spec_from_file_location(_DRIVER_NAME, _DRIVER_PATH)
    assert _driver_spec is not None and _driver_spec.loader is not None
    driver = importlib.util.module_from_spec(_driver_spec)
    sys.modules[_DRIVER_NAME] = driver
    _driver_spec.loader.exec_module(driver)

ADMIN = driver.TEST_SUBJECT.user_uid


@dataclass(frozen=True)
class Rings:
    """A generated key pair as the two rings the two processes load."""

    public_text: str
    private_text: str
    kid: str

    @property
    def public(self):
        from auditmanager.executors.public import load_public_ring

        return load_public_ring(f"{self.kid}:{self.public_text}", self.kid)

    @property
    def private(self):
        from auditmanager.executors.public import load_private_ring

        return load_private_ring(f"{self.kid}:{self.private_text}")


def make_rings(kid: str = "k1") -> Rings:
    key = X25519PrivateKey.generate()
    return Rings(
        public_text=base64.b64encode(
            key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode(),
        private_text=base64.b64encode(
            key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode(),
        kid=kid,
    )


@pytest.fixture
def rings() -> Rings:
    return make_rings()


@pytest.fixture
def admin_account(session: Session) -> str:
    """The row behind the suite's credential, an administrator, rolled back with the test."""
    from auditmanager.access.passwords import hash_password

    stored = hash_password(driver.SUITE_PASSWORD)
    last, first, middle = driver.SUITE_NAMES
    session.execute(text(
        "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
        "password_salt, password_hash, is_default_credential, token_epoch, last_name, "
        "first_name, middle_name, profile_completed_at) VALUES (:uid, :login, :algorithm, "
        ":iterations, :salt, :digest, false, :epoch, :last, :first, :middle, now())"
    ), {"uid": ADMIN, "login": driver.SUITE_LOGIN, "algorithm": stored.algorithm,
        "iterations": stored.iterations, "salt": stored.salt, "digest": stored.digest,
        "epoch": driver.TEST_EPOCH, "last": last, "first": first, "middle": middle})
    session.execute(text("INSERT INTO app_user_role (user_uid, role) VALUES (:uid, 'admin')"),
                    {"uid": ADMIN})
    return ADMIN


def build_surface(session: Session, ring, *, roles: frozenset[str]):
    from auditmanager.api.routers import build_router
    from auditmanager.bootstrap.adapters import ExecutorAdapter

    return driver.Surface(build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=driver.SuiteCredentialAdapter(roles=roles),
        accounts=driver.SuiteAccountAdapter(),
        registrations=driver.SuiteRegistrationAdapter(),
        executors=ExecutorAdapter(lambda: nullcontext(session), ring=ring),  # type: ignore[arg-type]
    ))


@pytest.fixture
def surface(session: Session, admin_account: str, rings: Rings):
    return build_surface(session, rings.public, roles=frozenset({"admin"}))
