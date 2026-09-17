"""An unusable store is an explicit typed failure, never a degradation.

Three distinct ways for the store to be unusable, three distinct types. They
are separated because a caller's correct response differs: an unreachable
endpoint may be retried, a refused credential and an absent bucket may not.
Collapsing them into one error would hide that.

The last test is the one the whole task turns on: when storage is unavailable
there is no filesystem fallback. Nothing is written anywhere.
"""

from __future__ import annotations

import os
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    S3BlobStore,
    S3StorageSettings,
    StorageBucketMissingError,
    StorageConfigurationError,
    StorageCredentialRefusedError,
    StorageUnavailableError,
    derive_blob_id,
    sha256_of,
)
from auditmanager.storage.errors import BLOB_STORAGE_DEPENDENCY

PAYLOAD = b"bytes that must never reach anywhere but the object store"


def test_an_unreachable_endpoint_is_typed_unavailable(
    unreachable_store: S3BlobStore,
) -> None:
    with pytest.raises(StorageUnavailableError) as raised:
        unreachable_store.check_access()
    assert raised.value.details["dependency"] == BLOB_STORAGE_DEPENDENCY
    assert raised.value.code == "dependency_unavailable"


def test_publishing_to_an_unreachable_store_raises_rather_than_degrading(
    unreachable_store: S3BlobStore,
) -> None:
    with pytest.raises(StorageUnavailableError):
        unreachable_store.put_blob(
            PAYLOAD,
            declared_sha256=sha256_of(PAYLOAD),
            declared_size=len(PAYLOAD),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )


def test_reading_from_an_unreachable_store_raises(
    unreachable_store: S3BlobStore,
) -> None:
    blob_id = derive_blob_id(sha256=sha256_of(PAYLOAD), size=len(PAYLOAD))
    with pytest.raises(StorageUnavailableError):
        unreachable_store.read(blob_id)
    with pytest.raises(StorageUnavailableError):
        unreachable_store.inspect(blob_id)


def test_there_is_no_filesystem_fallback(
    unreachable_store: S3BlobStore, tmp_path: Path
) -> None:
    """The invariant, made observable.

    A publication against a dead store, run from an empty directory, must
    leave that directory empty. If any fallback ever appeared -- a spool file,
    a local cache, a "degraded mode" directory -- this is the test that fails.
    """
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(StorageUnavailableError):
            unreachable_store.put_blob(
                PAYLOAD,
                declared_sha256=sha256_of(PAYLOAD),
                declared_size=len(PAYLOAD),
                role=ROLE_SOURCE_DOCUMENT,
                media_type="application/pdf",
            )
    finally:
        os.chdir(previous)
    assert list(tmp_path.iterdir()) == []


def test_the_package_ships_no_filesystem_adapter() -> None:
    """FF-01 section 4 lists filesystem canonical storage as not approved."""
    import auditmanager.storage as package

    module_dir = Path(package.__file__).parent
    modules = sorted(path.stem for path in module_dir.glob("*.py"))
    banned = ("filesystem", "local_disk", "localfs", "fs_adapter", "disk")
    assert not [name for name in modules if any(word in name for word in banned)], (
        "a filesystem canonical adapter appeared in the storage package"
    )
    exported = set(package.__all__)
    assert not [
        name
        for name in exported
        if any(word in name.lower() for word in ("filesystem", "localblob", "diskblob"))
    ]
    # The only adapter the package exports is the S3 one.
    adapters = {name for name in exported if name.endswith("BlobStore")}
    assert adapters == {"BlobStore", "S3BlobStore"}


def test_refused_credentials_are_typed_dependency_credential_refused(
    settings: S3StorageSettings,
) -> None:
    wrong = S3BlobStore(
        replace(
            settings,
            access_key_id="a3-wrong-access-key",
            secret_access_key="a3-wrong-secret-key",
        )
    )
    with pytest.raises(StorageCredentialRefusedError) as raised:
        wrong.check_access()
    assert raised.value.code == "dependency_credential_refused"
    # The keys that made the two 403s indistinguishable are gone with the code.
    assert dict(raised.value.details) == {"dependency": "blob_storage"}


def test_publishing_with_refused_credentials_publishes_nothing(
    settings: S3StorageSettings, bucket_keys: Any
) -> None:
    before = bucket_keys()
    wrong = S3BlobStore(
        replace(
            settings,
            access_key_id="a3-wrong-access-key",
            secret_access_key="a3-wrong-secret-key",
        )
    )
    with pytest.raises(StorageCredentialRefusedError):
        wrong.put_blob(
            PAYLOAD,
            declared_sha256=sha256_of(PAYLOAD),
            declared_size=len(PAYLOAD),
            role=ROLE_SOURCE_DOCUMENT,
            media_type="application/pdf",
        )
    assert bucket_keys() == before


def test_a_missing_bucket_is_a_typed_configuration_failure(
    settings: S3StorageSettings,
) -> None:
    """Not "unavailable": retrying never creates a bucket, and this adapter
    never creates one either. It names the setting to fix, never its value."""
    absent = S3BlobStore(replace(settings, bucket=f"{settings.bucket}-absent-a3"))
    with pytest.raises(StorageBucketMissingError) as raised:
        absent.check_access()
    assert isinstance(raised.value, StorageConfigurationError)
    assert raised.value.details["field"] == "S3_BUCKET"
    assert settings.bucket not in str(raised.value)


def test_missing_configuration_is_explicit_and_names_the_variable() -> None:
    with pytest.raises(StorageConfigurationError) as raised:
        S3StorageSettings.from_env({})
    assert raised.value.details["field"] in {
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_BUCKET",
    }


def test_an_empty_value_is_as_missing_as_an_absent_one() -> None:
    env = {
        "S3_ENDPOINT_URL": "http://127.0.0.1:1",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "k",
        "S3_SECRET_ACCESS_KEY": "s",
        "S3_BUCKET": "   ",
    }
    with pytest.raises(StorageConfigurationError) as raised:
        S3StorageSettings.from_env(env)
    assert raised.value.details["field"] == "S3_BUCKET"


def test_failure_text_never_names_the_bucket_or_a_credential(
    settings: S3StorageSettings,
) -> None:
    wrong = S3BlobStore(
        replace(
            settings,
            access_key_id="a3-wrong-access-key",
            secret_access_key="a3-wrong-secret-key",
        )
    )
    with pytest.raises(StorageCredentialRefusedError) as raised:
        wrong.check_access()
    error = raised.value
    rendered = "\n".join(
        [
            str(error),
            repr(error),
            "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        ]
    )
    assert settings.bucket not in rendered
    assert settings.secret_access_key not in rendered
    assert "a3-wrong-secret-key" not in rendered


def test_settings_repr_redacts_the_secret_and_the_bucket(
    settings: S3StorageSettings,
) -> None:
    rendered = repr(settings)
    assert settings.secret_access_key not in rendered
    assert settings.access_key_id not in rendered
    assert settings.bucket not in rendered
    assert "<redacted>" in rendered
