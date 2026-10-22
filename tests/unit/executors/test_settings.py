"""`EXEC-SEAL-01`: the key-ring variables of `settings.load`. The `api` holds public keys only."""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from auditmanager.bootstrap import settings as settings_module
from auditmanager.bootstrap.settings import ConfigurationError, load

BASE = {
    "DATABASE_URL": "postgresql://user:pw@localhost/db", "S3_ENDPOINT_URL": "http://s3.test",
    "S3_REGION": "r", "S3_ACCESS_KEY_ID": "a", "S3_SECRET_ACCESS_KEY": "b", "S3_BUCKET": "c",
    "AUDITMANAGER_API_TOKEN": "token-for-the-signer",
}
_KEY = X25519PrivateKey.generate()
PRIVATE = base64.b64encode(_KEY.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode()
PUBLIC = base64.b64encode(_KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def test_the_variable_names_are_the_documented_three() -> None:
    assert settings_module.SECRETS_PUBLIC_KEYS_ENV == "AUDITMANAGER_SECRETS_PUBLIC_KEYS"
    assert settings_module.SECRETS_ACTIVE_KID_ENV == "AUDITMANAGER_SECRETS_ACTIVE_KID"
    assert settings_module.SECRETS_KEYS_ENV == "AUDITMANAGER_SECRETS_KEYS"


def test_no_variable_means_no_ring() -> None:
    loaded = load(BASE)
    assert loaded.secrets_public_ring is None and loaded.secrets_private_ring is None


def test_the_api_loads_the_public_ring_and_prints_no_key() -> None:
    loaded = load({**BASE, "EXECUTION_ROLE": "api",
                   "AUDITMANAGER_SECRETS_PUBLIC_KEYS": f"k1:{PUBLIC}",
                   "AUDITMANAGER_SECRETS_ACTIVE_KID": "k1"})
    assert loaded.secrets_public_ring is not None and loaded.secrets_private_ring is None
    assert PUBLIC not in repr(loaded)


def test_the_api_refuses_to_start_with_the_private_ring() -> None:
    with pytest.raises(ConfigurationError) as refused:
        load({**BASE, "EXECUTION_ROLE": "api", "AUDITMANAGER_SECRETS_KEYS": f"k1:{PRIVATE}"})
    assert PRIVATE not in str(refused.value)


def test_the_worker_loads_the_private_ring_and_prints_no_key() -> None:
    env = {k: v for k, v in BASE.items() if k != "AUDITMANAGER_API_TOKEN"}
    loaded = load({**env, "EXECUTION_ROLE": "worker", "AUDITMANAGER_SECRETS_KEYS": f"k1:{PRIVATE}",
                   "AUDITMANAGER_SECRETS_PUBLIC_KEYS": f"k1:{PUBLIC}",
                   "AUDITMANAGER_SECRETS_ACTIVE_KID": "k1"})
    assert loaded.secrets_private_ring is not None and loaded.secrets_public_ring is not None
    assert PRIVATE not in repr(loaded)


def test_a_malformed_variable_refuses_the_start_and_names_no_key() -> None:
    with pytest.raises(ConfigurationError) as refused:
        load({**BASE, "AUDITMANAGER_SECRETS_PUBLIC_KEYS": f"k1:{PUBLIC}",
              "AUDITMANAGER_SECRETS_ACTIVE_KID": "not-in-the-ring"})
    assert PUBLIC not in str(refused.value)
    with pytest.raises(ConfigurationError):
        load({**BASE, "AUDITMANAGER_SECRETS_PUBLIC_KEYS": "k1:%%%", "AUDITMANAGER_SECRETS_ACTIVE_KID": "k1"})
