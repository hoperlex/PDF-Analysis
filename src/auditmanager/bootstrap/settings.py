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
from typing import Any, Final

from auditmanager.analysis.public import REFERENCE_DOCUMENT_CHARACTERS, input_budget_characters
from auditmanager.executors.public import (
    SealingConfigurationError,
    load_private_ring,
    load_public_ring,
)
from auditmanager.shared.errors import DomainError, ErrorCode

#: The application-layer names, distinct from the fifteen FF-01 freezes for the services.
PROVIDER_MODE_ENV: Final[str] = "AUDITMANAGER_PROVIDER_MODE"
MODEL_ID_ENV: Final[str] = "AUDITMANAGER_MODEL_ID"
COST_CEILING_ENV: Final[str] = "AUDITMANAGER_RUN_COST_CEILING_USD"
API_KEY_ENV: Final[str] = "ANTHROPIC_API_KEY"

#: The deployment secret of `T-6`'s seam, given a configuration channel by `W14-PKG`.
#:
#: **What it means changed in wave 34 and its name did not.** Until `W34-API` this value
#: *was* the credential: a caller presented it and the seam compared. It is now the secret
#: the seam derives its signing key from (``api/security.py``,
#: :func:`~auditmanager.api.security.derive_signing_key`), and its literal value is no
#: longer accepted as a bearer credential by anything. A deployment therefore keeps one
#: configured name and gains no second secret -- and stops honouring the string its
#: runbook published, which is the point rather than a side effect.
#:
#: ``api/security.py`` reads this same name out of the mapping ``create_app(environ=...)``
#: carries, and spells it there as ``API_TOKEN_VARIABLE``. It is spelled again here rather
#: than imported, because ``bootstrap`` is below ``api`` and must not depend upward;
#: ``tests/integration/composition/test_api_token_channel.py`` pins the two spellings
#: equal so the duplication cannot drift.
#:
#: **Why it is required rather than optional.** ``W13_CLOSURE.md`` section 7: the seam is
#: fail-closed, so a deployment that forgets the token gets a surface that refuses every
#: one of the sealed operations while liveness and readiness stay green. From outside,
#: that reads as a broken product rather than an unconfigured one. Refusing at
#: construction is the same Gate C contract ``ANTHROPIC_API_KEY`` is already held to, and
#: for the same reason: the cheap place to discover a missing credential is before the
#: process binds a socket.
API_TOKEN_ENV: Final[str] = "AUDITMANAGER_API_TOKEN"

#: How the application reaches a model. `proxy` is a **transport**, not a provenance mode:
#: a proxied call is recorded in the run as `live`, because a model really answered it.
#: `OD-02` was revised to the proxy on 2026-09-14.
_DECLARED_MODES: Final[frozenset[str]] = frozenset({"live", "recorded", "proxy"})

#: `W54-WORKER-01`, owner ruling R-105. Which process claims runs. ``all`` is W53's
#: in-process execution and the value when the name is unset -- every test and every
#: developer stack builds an application without it. On the stand ``compose.server.yml``
#: sets it literally per service (``api`` on the API, ``worker`` on the worker service),
#: never through the ``.env`` and its fifteen frozen names, and ``deploy.sh`` refuses a
#: compose file in which either service lacks it.
EXECUTION_ROLE_ENV: Final[str] = "EXECUTION_ROLE"
EXECUTION_ROLES: Final[frozenset[str]] = frozenset({"all", "api", "worker"})

#: Where the worker writes its identity and heartbeat file (a tmpfs on the stand). Unset,
#: it writes nothing and the container health check has nothing to read.
WORKER_STATE_DIR_ENV: Final[str] = "AUDITMANAGER_WORKER_STATE_DIR"

#: `W55A-SEARCH-01` (`W55-PLAN.md` section A3.4, owner ruling R-112). The
#: ``statement_timeout`` every ``searchNorms`` query runs under, in milliseconds; a cancelled
#: search answers ``validation_failed`` (``norms_search_too_broad``). Read from the process
#: environment -- on the stand the owner sets it in the host-owned ``provider.env`` on the
#: integrator's rehearsal figure -- and never from the ``.env`` and its fifteen frozen names.
NORMS_SEARCH_TIMEOUT_ENV: Final[str] = "AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS"
#: The default `W55A-FREEZE-01` fixed provisionally; `W55A-D124-MEASURE` re-fixes it from the
#: promotion database.
DEFAULT_NORMS_SEARCH_TIMEOUT_MS: Final[int] = 3000
#: Ten minutes: anything longer is not a search a person waits for.
MAX_NORMS_SEARCH_TIMEOUT_MS: Final[int] = 600_000

#: `EXEC-SEAL-01` (`R-143b`). The key ring that seals executor secrets. The ``api`` and the
#: worker read the public keys (``kid:base64``, comma-separated) and the key id new secrets are
#: sealed to; **only the worker reads the private ring**, and the ``api`` refuses to start with
#: it. All three live in the host-owned ``provider.env``, never in PostgreSQL or S3, so a
#: database dump carries ciphertext and nothing that opens it.
SECRETS_PUBLIC_KEYS_ENV: Final[str] = "AUDITMANAGER_SECRETS_PUBLIC_KEYS"
SECRETS_ACTIVE_KID_ENV: Final[str] = "AUDITMANAGER_SECRETS_ACTIVE_KID"
SECRETS_KEYS_ENV: Final[str] = "AUDITMANAGER_SECRETS_KEYS"

PROXY_BASE_URL_ENV: Final[str] = "PROXY_LLM_BASE_URL"
PROXY_TOKEN_ENV: Final[str] = "PROXY_LLM_TOKEN"
PROXY_MODEL_ENV: Final[str] = "PROXY_LLM_MODEL"


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
    proxy_base_url: str | None
    proxy_token: str | None
    proxy_model: str
    run_cost_ceiling_usd: float
    #: `W55B-BUDGET-01` (G-11, R-118). The most pypdfium2 characters a document version may
    #: have for ``startRun`` and ``reauditRun`` to accept it, derived **once** here from
    #: :attr:`model_id` and :attr:`run_cost_ceiling_usd` by
    #: ``analysis.public.input_budget_characters``. Never a literal and never read from the
    #: environment: the two operator settings it follows are, and :func:`load` refuses a pair
    #: whose figure cannot hold the 30-page AR document set. The composition root hands it to every
    #: adapter that starts a run.
    input_budget_characters: int
    api_key: str | None
    #: The deployment secret the credential signer is derived from; see
    #: :data:`API_TOKEN_ENV`. Still required, still refused when empty, and no longer a
    #: credential anybody presents. ``None`` only for ``EXECUTION_ROLE=worker``, which
    #: serves nothing and must not hold the secret (R-105).
    api_token: str | None
    #: :data:`EXECUTION_ROLE_ENV`, validated.
    execution_role: str = "all"
    #: :data:`WORKER_STATE_DIR_ENV`; read by the worker service only.
    worker_state_dir: str | None = None
    #: :data:`NORMS_SEARCH_TIMEOUT_ENV`, validated; milliseconds.
    norms_search_timeout_ms: int = DEFAULT_NORMS_SEARCH_TIMEOUT_MS
    #: `EXEC-SEAL-01`. The ring the ``api`` seals executor secrets to (public keys only), or
    #: ``None`` when none is configured. Both rings print only their key ids.
    secrets_public_ring: Any = None
    #: The worker's private ring (:data:`SECRETS_KEYS_ENV`); ``None`` unless set, and refused
    #: for ``EXECUTION_ROLE=api``.
    secrets_private_ring: Any = None

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


def _api_token(role: str, environ: dict[str, str]) -> str | None:
    """Required for a process that serves; refused for the worker (R-105).

    The token exemption: the worker answers no request, so it has no use for the secret
    credentials are derived from, and holding it would widen what a compromised worker
    could mint. Present is refused, not ignored.
    """
    if role != "worker":
        return _require(API_TOKEN_ENV, environ)
    if environ.get(API_TOKEN_ENV, "").strip():
        raise ConfigurationError(
            f"{EXECUTION_ROLE_ENV} is worker but {API_TOKEN_ENV} is set; the worker "
            "service runs with the API's environment except that secret"
        )
    return None


def _input_budget(model_id: str, ceiling_usd: float) -> int:
    """The analysis input budget for this model and ceiling, or the refusal to start.

    Two ways to refuse, both at start-up and both naming the settings to change: a model the
    P02 lock does not pin (its rates, hence its budget, are unknown -- the runtime would
    refuse it at the first run anyway), and a pair whose budget does not reach the 30-page
    AR document set, which would leave the product unable to analyse the one document it exists for.
    The figures are in the message because an operator fixing it needs both numbers.
    """
    try:
        budget = input_budget_characters(model_id, ceiling_usd)
    except DomainError:
        raise ConfigurationError(
            f"{MODEL_ID_ENV} is {model_id!r}, which the P02 lock does not pin; the analysis "
            "input budget is derived from the pinned rates and cannot be derived for an "
            "unpinned model"
        ) from None
    except ValueError:
        # `float()` parses "nan" and "inf", and neither is a ceiling anyone set on purpose.
        raise ConfigurationError(
            f"{COST_CEILING_ENV} is {ceiling_usd!r}; the run cost ceiling is a finite number "
            "of US dollars, and the analysis input budget cannot be derived from anything else"
        ) from None
    if budget < REFERENCE_DOCUMENT_CHARACTERS:
        raise ConfigurationError(
            f"{COST_CEILING_ENV} is {ceiling_usd:g} for {MODEL_ID_ENV} {model_id!r}, which "
            f"leaves an analysis input budget of {budget} characters; the 30-page AR document "
            f"set is {REFERENCE_DOCUMENT_CHARACTERS} characters, so the product could not "
            "analyse the document it exists for. Raise the ceiling or choose a cheaper "
            "pinned model"
        )
    return budget


def _norms_search_timeout_ms(environ: dict[str, str]) -> int:
    """:data:`NORMS_SEARCH_TIMEOUT_ENV`: unset or blank is the default; anything else must be
    a whole number of milliseconds in ``1 .. MAX_NORMS_SEARCH_TIMEOUT_MS``. A value that does
    not parse refuses the start: a timeout that silently fell back would be a search bound
    nobody chose."""
    raw = environ.get(NORMS_SEARCH_TIMEOUT_ENV, "").strip()
    if not raw:
        return DEFAULT_NORMS_SEARCH_TIMEOUT_MS
    if not raw.isdecimal() or raw != str(int(raw)):
        raise ConfigurationError(
            f"{NORMS_SEARCH_TIMEOUT_ENV} is {raw!r}; it is a whole number of milliseconds"
        )
    value = int(raw)
    if not 1 <= value <= MAX_NORMS_SEARCH_TIMEOUT_MS:
        raise ConfigurationError(
            f"{NORMS_SEARCH_TIMEOUT_ENV} is {value}; it must be between 1 and "
            f"{MAX_NORMS_SEARCH_TIMEOUT_MS} milliseconds"
        )
    return value


def _secret_rings(role: str, env: dict[str, str]) -> tuple[Any, Any]:
    """The public ring and the private ring, parsed at start so a malformed variable refuses
    the start instead of the first secret. The ``api`` holds public keys only: the private ring
    present on that role is refused, not ignored. A refusal names the variable, never a key."""
    private = env.get(SECRETS_KEYS_ENV, "").strip() or None
    if role == "api" and private is not None:
        raise ConfigurationError(
            f"{SECRETS_KEYS_ENV} is set but {EXECUTION_ROLE_ENV} is api; the api seals to "
            f"public keys ({SECRETS_PUBLIC_KEYS_ENV}) and holds no private key"
        )
    active = env.get(SECRETS_ACTIVE_KID_ENV, "").strip() or None
    try:
        public_ring = load_public_ring(
            env.get(SECRETS_PUBLIC_KEYS_ENV, "").strip() or None, active,
            public_variable=SECRETS_PUBLIC_KEYS_ENV, active_variable=SECRETS_ACTIVE_KID_ENV,
        )
        private_ring = load_private_ring(private, active, variable=SECRETS_KEYS_ENV)
    except SealingConfigurationError as exc:
        raise ConfigurationError(str(exc)) from None
    return public_ring, private_ring


def load(environ: dict[str, str] | None = None) -> AppSettings:
    """Read and validate. Raises :class:`ConfigurationError` on anything missing."""
    env = dict(os.environ if environ is None else environ)

    role = env.get(EXECUTION_ROLE_ENV, "").strip() or "all"
    if role not in EXECUTION_ROLES:
        raise ConfigurationError(
            f"{EXECUTION_ROLE_ENV} is {role!r}; the declared roles are "
            f"{sorted(EXECUTION_ROLES)}. A process either claims runs or it does not, "
            "and which one it is must not be a guess"
        )

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

    proxy_base_url = env.get(PROXY_BASE_URL_ENV, "").strip() or None
    proxy_token = env.get(PROXY_TOKEN_ENV, "").strip() or None
    if mode == "proxy":
        # Refused at startup for the same reason a missing credential is: a process that
        # starts must be able to serve. The token is the one value the proxy cannot be
        # reached without, and the base URL is the one it cannot be found without.
        if proxy_base_url is None:
            raise ConfigurationError(
                f"{PROVIDER_MODE_ENV} is proxy but {PROXY_BASE_URL_ENV} is unset"
            )
        if proxy_token is None:
            raise ConfigurationError(
                f"{PROVIDER_MODE_ENV} is proxy but {PROXY_TOKEN_ENV} is unset; the proxy "
                "authenticates every call and refuses a blank token before reading the body"
            )

    api_key = env.get(API_KEY_ENV, "").strip() or None
    if mode == "live" and api_key is None:
        # Refusing here is the point. A live-mode process with no credential would start,
        # pass a health check, and fail on the first run - after a document had been
        # uploaded and a run row written.
        raise ConfigurationError(
            f"{PROVIDER_MODE_ENV} is live but {API_KEY_ENV} is unset; a live run cannot "
            "be served and the process refuses to start rather than discover it later"
        )

    model_id = env.get(MODEL_ID_ENV, "").strip() or "claude-opus-5"
    budget = _input_budget(model_id, ceiling)

    public_ring, private_ring = _secret_rings(role, env)
    return AppSettings(
        secrets_public_ring=public_ring,
        secrets_private_ring=private_ring,
        database_url=_require("DATABASE_URL", env),
        s3_endpoint_url=_require("S3_ENDPOINT_URL", env),
        s3_region=_require("S3_REGION", env),
        s3_access_key_id=_require("S3_ACCESS_KEY_ID", env),
        s3_secret_access_key=_require("S3_SECRET_ACCESS_KEY", env),
        s3_bucket=_require("S3_BUCKET", env),
        provider_mode=mode,
        model_id=model_id,
        run_cost_ceiling_usd=ceiling,
        input_budget_characters=budget,
        api_key=api_key,
        api_token=_api_token(role, env),
        execution_role=role,
        worker_state_dir=env.get(WORKER_STATE_DIR_ENV, "").strip() or None,
        norms_search_timeout_ms=_norms_search_timeout_ms(env),
        proxy_base_url=proxy_base_url,
        proxy_token=proxy_token,
        # The stub the proxy reads as "I am not choosing a model", so the operator's default
        # and its fallback chain apply. Any other value is a real choice that changes routing
        # and billing and switches the fallback chain off.
        proxy_model=env.get(PROXY_MODEL_ENV, "").strip() or "proxy",
    )
