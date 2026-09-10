"""Adapter configuration, read from the frozen environment names.

``FF-01`` section 3 fixes the names; this module reads exactly those and invents
none. A missing or empty value is a typed
:class:`~auditmanager.storage.errors.StorageConfigurationError` naming the
variable -- never a default, never an anonymous client, never a fallback to a
local directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Final, Mapping

from .errors import StorageConfigurationError

#: The frozen FF-01 section 3 names this adapter consumes.
ENDPOINT_URL_VAR: Final[str] = "S3_ENDPOINT_URL"
REGION_VAR: Final[str] = "S3_REGION"
ACCESS_KEY_ID_VAR: Final[str] = "S3_ACCESS_KEY_ID"
SECRET_ACCESS_KEY_VAR: Final[str] = "S3_SECRET_ACCESS_KEY"
BUCKET_VAR: Final[str] = "S3_BUCKET"

REQUIRED_VARS: Final[tuple[str, ...]] = (
    ENDPOINT_URL_VAR,
    REGION_VAR,
    ACCESS_KEY_ID_VAR,
    SECRET_ACCESS_KEY_VAR,
    BUCKET_VAR,
)


@dataclass(frozen=True, slots=True)
class S3StorageSettings:
    """Everything the S3 adapter needs, and nothing a consumer may see.

    This is adapter configuration, not a public return model: it is never
    handed to business code. Its ``repr`` still redacts the secret, the access
    key and the bucket, because configuration objects end up in tracebacks and
    log lines and a redacted repr costs nothing.
    """

    endpoint_url: str
    region: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    bucket: str = field(repr=False)

    #: Kept short so an unreachable endpoint is an immediate typed failure
    #: rather than a minutes-long hang. Retrying a dead store is a caller's
    #: decision; this adapter never retries silently.
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 30.0
    max_attempts: int = 1

    def __repr__(self) -> str:
        return (
            f"S3StorageSettings(endpoint_url={self.endpoint_url!r}, "
            f"region={self.region!r}, access_key_id=<redacted>, "
            "secret_access_key=<redacted>, bucket=<redacted>)"
        )

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, **overrides: object
    ) -> "S3StorageSettings":
        """Build settings from the frozen environment names.

        Raises :class:`StorageConfigurationError` naming the first missing or
        empty variable. Missing configuration is an explicit failure: there is
        no anonymous client and no local-directory mode to fall back to.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        values: dict[str, str] = {}
        for name in REQUIRED_VARS:
            raw = source.get(name, "")
            if not raw or not raw.strip():
                raise StorageConfigurationError(field=name, constraint="required")
            values[name] = raw.strip()

        settings = cls(
            endpoint_url=values[ENDPOINT_URL_VAR],
            region=values[REGION_VAR],
            access_key_id=values[ACCESS_KEY_ID_VAR],
            secret_access_key=values[SECRET_ACCESS_KEY_VAR],
            bucket=values[BUCKET_VAR],
        )
        if overrides:
            from dataclasses import replace

            settings = replace(settings, **overrides)  # type: ignore[arg-type]
        return settings


__all__ = [
    "ACCESS_KEY_ID_VAR",
    "BUCKET_VAR",
    "ENDPOINT_URL_VAR",
    "REGION_VAR",
    "REQUIRED_VARS",
    "SECRET_ACCESS_KEY_VAR",
    "S3StorageSettings",
]
