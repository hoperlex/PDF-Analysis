"""Everything the application reads from its environment, resolved once at startup.

The composition root's contract is that a missing or malformed dependency fails **at
construction**, not at first use. A settings object that lazily reads an environment
variable the first time somebody needs it defeats that: the process starts, answers a
health check, and dies on the first upload. So every value is read and validated here,
and :func:`load` raises before anything is wired.

Provider configuration is deliberately **not** in ``.env``. ``P02_LOCK.json`` records why:
the Makefile enforces a strict allowlist of exactly the fifteen names FF-01 section 3
freezes, and its comment states the intent - ``.env`` does not carry credentials for other
systems "or anything that selects what code runs". ``AUDITMANAGER_PROVIDER_MODE`` is
precisely something that selects what code runs. These names are read from the process
environment instead, and the credential is an injected secret that is never written to a
file in this repository.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

#: The application-layer names, distinct from the fifteen FF-01 freezes for the services.
PROVIDER_MODE_ENV: Final[str] = "AUDITMANAGER_PROVIDER_MODE"
MODEL_ID_ENV: Final[str] = "AUDITMANAGER_MODEL_ID"
COST_CEILING_ENV: Final[str] = "AUDITMANAGER_RUN_COST_CEILING_USD"
API_KEY_ENV: Final[str] = "ANTHROPIC_API_KEY"

_DECLARED_MODES: Final[frozenset[str]] = frozenset({"live", "recorded"})


class ConfigurationError(DomainError):
    """A dependency is missing or malformed. Raised while wiring, never while serving."""

    def __init__(self, detail: str) -> None:
        super().__init__(ErrorCode.INTERNAL_ERROR, message=detail)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Resolved configuration. Every field is present and checked."""

    database_url: str
    s3_endpoint_url: str
    s3_region: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket: str
    provider_mode: str
    model_id: str
    run_cost_ceiling_usd: float
    api_key: str | None

    @property
    def requires_credential(self) -> bool:
        return self.provider_mode == "live"


def _require(name: str, environ: dict[str, str]) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"the environment variable {name} is unset or empty; the application "
            "refuses to start rather than fail on the first request that needs it"
        )
    return value


def load(environ: dict[str, str] | None = None) -> AppSettings:
    """Read and validate. Raises :class:`ConfigurationError` on anything missing."""
    env = dict(os.environ if environ is None else environ)

    mode = env.get(PROVIDER_MODE_ENV, "recorded").strip() or "recorded"
    if mode not in _DECLARED_MODES:
        raise ConfigurationError(
            f"{PROVIDER_MODE_ENV} is {mode!r}; the declared modes are "
            f"{sorted(_DECLARED_MODES)}. A run is live or replayed and never a third thing"
        )

    raw_ceiling = env.get(COST_CEILING_ENV, "1.00").strip() or "1.00"
    try:
        ceiling = float(raw_ceiling)
    except ValueError:
        raise ConfigurationError(
            f"{COST_CEILING_ENV} is not a number. A ceiling that cannot be parsed is a "
            "ceiling that does not hold"
        ) from None
    if ceiling <= 0:
        raise ConfigurationError(f"{COST_CEILING_ENV} must be positive, got {ceiling}")

    api_key = env.get(API_KEY_ENV, "").strip() or None
    if mode == "live" and api_key is None:
        # Refusing here is the point. A live-mode process with no credential would start,
        # pass a health check, and fail on the first run - after a document had been
        # uploaded and a run row written.
        raise ConfigurationError(
            f"{PROVIDER_MODE_ENV} is live but {API_KEY_ENV} is unset; a live run cannot "
            "be served and the process refuses to start rather than discover it later"
        )

    return AppSettings(
        database_url=_require("DATABASE_URL", env),
        s3_endpoint_url=_require("S3_ENDPOINT_URL", env),
        s3_region=_require("S3_REGION", env),
        s3_access_key_id=_require("S3_ACCESS_KEY_ID", env),
        s3_secret_access_key=_require("S3_SECRET_ACCESS_KEY", env),
        s3_bucket=_require("S3_BUCKET", env),
        provider_mode=mode,
        model_id=env.get(MODEL_ID_ENV, "").strip() or "claude-opus-5",
        run_cost_ceiling_usd=ceiling,
        api_key=api_key,
    )
