"""A missing product input refuses during application construction."""

from __future__ import annotations

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.settings import ConfigurationError, load
from auditmanager.shared import db


def _settings():
    return load({
        "DATABASE_URL": "postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
        "S3_ENDPOINT_URL": "http://127.0.0.1:1",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "unused",
        "S3_SECRET_ACCESS_KEY": "unused",
        "S3_BUCKET": "unused",
        "AUDITMANAGER_API_TOKEN": "disposable-startup-test",
    })


@pytest.mark.parametrize("missing", ["VERSION", "build input"])
def test_missing_version_input_fails_during_construction(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    # Stop before any network dependency: the production root creates the
    # session factory, then binds version and build identity before the router.
    monkeypatch.setattr(db, "create_database_engine", lambda _: object())
    monkeypatch.setattr(db, "create_session_factory", lambda _: object())

    def absent() -> str:
        raise FileNotFoundError(missing)

    if missing == "VERSION":
        monkeypatch.setattr(composition, "read_product_version", absent)
    else:
        monkeypatch.setattr(composition, "read_product_version", lambda: "0.3.0")
        monkeypatch.setattr(composition, "compute_build_id", absent)
    with pytest.raises(ConfigurationError, match="release version or build inputs"):
        composition.build_application(settings=_settings(), environ={})
