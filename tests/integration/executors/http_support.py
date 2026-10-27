"""Seeding helpers for the `EXEC-HTTP-01` integration tests (loaded by explicit path).

Everything goes through the executors context's own commands, so a change to a rule reaches the
fixture instead of being bypassed. The one thing written by hand is a finished probe: a probe is
the worker's act, and ``mark_probe`` records its result the way ``ProbeRunner`` does.
"""

from __future__ import annotations

import base64
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy.orm import Session

from auditmanager.analysis.public import pinned_models
from auditmanager.executors.public import (
    create_connection,
    load_private_ring,
    load_public_ring,
    record_probe_result,
    record_probe_started,
    request_probe,
    revise_connection,
    set_route,
    set_secret,
)
from auditmanager.executors.model import RevisionSettings

_FAKE_NAME = "am_exec_fake_gateway"
_FAKE_PATH = Path(__file__).resolve().parents[2] / "unit" / "executors" / "fake_gateway.py"
if _FAKE_NAME in sys.modules:
    fake_gateway: ModuleType = sys.modules[_FAKE_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_FAKE_NAME, _FAKE_PATH)
    assert _spec is not None and _spec.loader is not None
    fake_gateway = importlib.util.module_from_spec(_spec)
    sys.modules[_FAKE_NAME] = fake_gateway
    _spec.loader.exec_module(fake_gateway)

ADMIN_ROLES = ("admin",)
ACTOR = "usr_0000000000000000000000TEST"
GATEWAY_MODEL = "anthropic/claude-opus-5"
PIN = pinned_models()[0]
KEY = "sk-sentinel-http-0123456789abcdef"


@dataclass(frozen=True)
class Rings:
    public_text: str
    private_text: str
    kid: str

    @property
    def public(self) -> Any:
        return load_public_ring(f"{self.kid}:{self.public_text}", self.kid)

    @property
    def private(self) -> Any:
        return load_private_ring(f"{self.kid}:{self.private_text}", self.kid)


def make_rings(kid: str = "k1") -> Rings:
    key = X25519PrivateKey.generate()
    return Rings(
        public_text=base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode(),
        private_text=base64.b64encode(
            key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode(),
        kid=kid,
    )


def unique() -> str:
    return f"t-{uuid4().hex}"


def settings(base_url: str, **changes: Any) -> RevisionSettings:
    values: dict[str, Any] = dict(
        pin_id=PIN.model_id, gateway_model=GATEWAY_MODEL, billing="metered",
        allow_client_documents=False, timeout_seconds=5, api_flavour="openai_chat",
        base_url=base_url, transport="direct",
    )
    if base_url.startswith("http://"):
        values["transport"] = "vpn"  # plain http is admitted on a vpn route or to a loopback name
    values.update(changes)
    return RevisionSettings(**values)


@dataclass
class Seeded:
    connection_id: str
    revision_id: str
    secret_id: str


def revise(session: Session, connection_id: str, base_url: str, **changes: Any) -> str:
    return revise_connection(
        session, connection_id=connection_id, settings=settings(base_url, **changes),
        pinned_model_ids={pin.model_id for pin in pinned_models()}, roles=ADMIN_ROLES,
        idempotency_key=unique(), actor_uid=ACTOR,
    ).revision_id


def set_key(session: Session, rings: Rings, connection_id: str, value: str = KEY) -> str:
    return set_secret(
        session, connection_id=connection_id, purpose="api_key", value=value, ring=rings.public,
        roles=ADMIN_ROLES, idempotency_key=unique(), actor_uid=ACTOR,
    ).secret_id


def mark_probe(
    session: Session, connection_id: str, outcome: str = "ok", **result: Any,
) -> str:
    """Request a probe of the current revision and finish it as the worker would."""
    probe = request_probe(
        session, connection_id=connection_id, roles=ADMIN_ROLES, idempotency_key=unique(),
        actor_uid=ACTOR,
    )
    assert record_probe_started(session, probe.probe_id)
    assert record_probe_result(
        session, probe.probe_id, outcome=outcome,
        reported_model=result.pop("reported_model", GATEWAY_MODEL),
        identity_basis="reported", rate_check=result.pop("rate_check", "not_reported"), **result,
    )
    return probe.probe_id


def route(session: Session, primary: str, standby: str | None = None) -> None:
    set_route(
        session, work_kind="text_analysis", primary_connection_id=primary,
        standby_connection_id=standby, roles=ADMIN_ROLES, idempotency_key=unique(),
        actor_uid=ACTOR,
    )


def seed_connection(
    session: Session, rings: Rings, base_url: str, *, name: str = "gateway",
    probe: str | None = "ok", routed: bool = True, key: str = KEY, **changes: Any,
) -> Seeded:
    """A connection with a revision and a sealed key; probed ``ok`` and routed by default."""
    connection = create_connection(
        session, kind="http_api", display_name=name, roles=ADMIN_ROLES,
        idempotency_key=unique(), actor_uid=ACTOR,
    )
    revision_id = revise(session, connection.connection_id, base_url, **changes)
    secret_id = set_key(session, rings, connection.connection_id, key)
    if probe is not None:
        mark_probe(session, connection.connection_id, probe)
    if routed:
        route(session, connection.connection_id)
    return Seeded(connection.connection_id, revision_id, secret_id)
