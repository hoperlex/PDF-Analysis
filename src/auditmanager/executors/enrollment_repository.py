"""The only writer and reader of ``executor_enrollment``, and of the health columns of
``executor_runner_token`` (migration ``0046``, `EXEC2-ENROLL-01`).

Statements only: the rules live in ``enrollment.py``. Every comparison with time uses the database clock
(``clock_timestamp()``), as ``runner_repository.py`` does, and a row is read together with the clock it was
read by (``read_at``) so a state derived from it in Python agrees with the database that holds the row.

**Only the SHA-256 of a grant's secret is stored.** The hash is returned to exactly one caller,
:meth:`EnrollmentRepository.by_prefix`, which hands it to the comparison in ``enrollment.authenticate``; no
other method returns it, and no record has a hash field. The health columns hold closed enumerations and
bounded strings (``ck_executor_runner_token_*``), never a credential, a path or a document's text.

A grant's **state** is derived, never stored (``ExecutorEnrollmentState``): ``redeemed`` once redeemed;
``revoked`` when revoked before it expired; ``expired`` once past ``expires_at`` (a grant that a newer one
revoked after its own expiry was already expired, and stays so); otherwise ``pending``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.repository import RUNNER_ONLINE_SECONDS
from auditmanager.shared.identity import ExecutorEnrollmentId

__all__ = [
    "EnrollmentRecord",
    "EnrollmentRepository",
    "TokenHealth",
    "enrollment_state",
]

_COLUMNS: Final = (
    "enrollment_id, connection_id, host_id, secret_prefix, created_at, created_by, expires_at, "
    "redeemed_at, runner_token_id, revoked_at, revoked_by, clock_timestamp() AS read_at"
)


def enrollment_state(
    *, redeemed_at: datetime | None, revoked_at: datetime | None, expires_at: datetime, now: datetime
) -> str:
    """``redeemed``, ``revoked``, ``expired`` or ``pending``: derived, in this order."""
    if redeemed_at is not None:
        return "redeemed"
    if revoked_at is not None and revoked_at <= expires_at:
        return "revoked"
    if expires_at <= now:
        return "expired"
    return "pending"


@dataclass(frozen=True, slots=True)
class EnrollmentRecord:
    """A grant's metadata. Neither the secret nor its hash is a field."""

    enrollment_id: str
    #: Exactly one of ``connection_id`` and ``host_id`` is set (`HOSTS-SEAL-1`, ``ck_executor_enrollment_target``).
    connection_id: str | None
    secret_prefix: str
    created_at: datetime
    created_by: str
    expires_at: datetime
    redeemed_at: datetime | None
    runner_token_id: str | None
    revoked_at: datetime | None
    revoked_by: str | None
    #: The database clock when the row was read.
    read_at: datetime
    host_id: str | None = None

    @property
    def state(self) -> str:
        return enrollment_state(
            redeemed_at=self.redeemed_at, revoked_at=self.revoked_at,
            expires_at=self.expires_at, now=self.read_at)

    @property
    def usable(self) -> bool:
        """Still to be redeemed: not redeemed, not revoked, not expired."""
        return self.state == "pending"


@dataclass(frozen=True, slots=True)
class TokenHealth:
    """What an agent last reported on its token, and whether it is online now (by the database clock)."""

    token_id: str
    agent_version: str
    clis: tuple[Mapping[str, Any], ...]
    concurrency: int
    execution_profile: str
    features: tuple[str, ...]
    reported_at: datetime
    online: bool


def _record(row: Mapping[str, Any]) -> EnrollmentRecord:
    return EnrollmentRecord(**{name: row[name] for name in (
        "enrollment_id", "connection_id", "host_id", "secret_prefix", "created_at", "created_by",
        "expires_at", "redeemed_at", "runner_token_id", "revoked_at", "revoked_by", "read_at")})


def _json(raw: Any) -> Any:
    return raw if isinstance(raw, (list, dict)) else json.loads(raw)


class EnrollmentRepository:
    """Stateless; every method takes the caller's session and never commits."""

    # -- grants ----------------------------------------------------------------------------

    def insert_enrollment(
        self, session: Session, *, connection_id: str | None = None, secret_prefix: str, secret_hash: bytes,
        lifetime_seconds: int, actor_uid: str, host_id: str | None = None,
    ) -> EnrollmentRecord:
        if (connection_id is None) == (host_id is None):
            raise ValueError("a grant names exactly one of a connection and a host")
        row = session.execute(text(
            "INSERT INTO executor_enrollment (enrollment_id, connection_id, host_id, secret_prefix, "
            "secret_hash, created_by, expires_at) VALUES (:id, :c, :h, :prefix, :hash, :actor, "
            "clock_timestamp() + make_interval(secs => :ttl)) "
            f"RETURNING {_COLUMNS}"
        ), {"id": str(ExecutorEnrollmentId.new()), "c": connection_id, "h": host_id, "prefix": secret_prefix,
            "hash": secret_hash, "actor": actor_uid, "ttl": lifetime_seconds}).mappings().one()
        return _record(row)

    def revoke_unredeemed(
        self, session: Session, connection_id: str, *, actor_uid: str
    ) -> list[tuple[str, bool]]:
        """Revoke the connection's grant that is neither redeemed nor revoked, if there is one.

        ``[(enrollment_id, was_live)]``: ``was_live`` is false for a grant that had already expired, which
        the partial unique index still counts as pending and which therefore has to be closed too."""
        rows = session.execute(text(
            "UPDATE executor_enrollment SET revoked_at = clock_timestamp(), revoked_by = :actor "
            "WHERE connection_id = :c AND redeemed_at IS NULL AND revoked_at IS NULL "
            "RETURNING enrollment_id, (expires_at > clock_timestamp()) AS was_live"
        ), {"c": connection_id, "actor": actor_uid}).all()
        return [(str(row[0]), bool(row[1])) for row in rows]

    def revoke_unredeemed_for_host(
        self, session: Session, host_id: str, *, actor_uid: str
    ) -> list[tuple[str, bool]]:
        """The same as :meth:`revoke_unredeemed` for a host's grant (at most one is pending per host)."""
        rows = session.execute(text(
            "UPDATE executor_enrollment SET revoked_at = clock_timestamp(), revoked_by = :actor "
            "WHERE host_id = :h AND redeemed_at IS NULL AND revoked_at IS NULL "
            "RETURNING enrollment_id, (expires_at > clock_timestamp()) AS was_live"
        ), {"h": host_id, "actor": actor_uid}).all()
        return [(str(row[0]), bool(row[1])) for row in rows]

    def get_enrollment(
        self, session: Session, enrollment_id: str, *, lock: bool = False
    ) -> EnrollmentRecord | None:
        row = session.execute(text(
            f"SELECT {_COLUMNS} FROM executor_enrollment WHERE enrollment_id = :id"
            + (" FOR UPDATE" if lock else "")
        ), {"id": enrollment_id}).mappings().first()
        return None if row is None else _record(row)

    def by_prefix(self, session: Session, secret_prefix: str) -> tuple[EnrollmentRecord, bytes] | None:
        """The grant a presented secret names, with its stored hash: for the one comparison in
        ``enrollment.authenticate_enrollment`` and for nothing else."""
        row = session.execute(text(
            f"SELECT {_COLUMNS}, secret_hash FROM executor_enrollment WHERE secret_prefix = :prefix"
        ), {"prefix": secret_prefix}).mappings().first()
        return None if row is None else (_record(row), bytes(row["secret_hash"]))

    def list_for_connection(
        self, session: Session, connection_id: str, *, limit: int = 10
    ) -> list[EnrollmentRecord]:
        rows = session.execute(text(
            f"SELECT {_COLUMNS} FROM executor_enrollment WHERE connection_id = :c "
            "ORDER BY created_at DESC, enrollment_id DESC LIMIT :limit"
        ), {"c": connection_id, "limit": limit}).mappings().all()
        return [_record(row) for row in rows]

    def set_current_token(self, session: Session, enrollment_id: str, token_id: str) -> bool:
        """Point a redeemed grant at the token most recently minted from it. ``runner_token_id`` is not
        write-once (migration ``0046``), which is what lets a repeat by the same instance replace it;
        ``False`` when the grant is not redeemed."""
        return bool(session.execute(text(
            "UPDATE executor_enrollment SET runner_token_id = :token "
            "WHERE enrollment_id = :id AND redeemed_at IS NOT NULL"
        ), {"id": enrollment_id, "token": token_id}).rowcount)

    def prefixes_starting(self, session: Session, start: str) -> set[str]:
        """The runner-token prefixes (``amr_`` and eight characters) that begin with ``start``, whoever
        holds them: the uniqueness of a prefix is the table's, not a connection's."""
        rows = session.execute(text(
            "SELECT token_prefix FROM executor_runner_token WHERE left(token_prefix, :n) = :start"
        ), {"n": len(start), "start": start}).all()
        return {str(row[0]) for row in rows}

    def mark_redeemed(self, session: Session, enrollment_id: str, token_id: str) -> bool:
        """Redeem once: ``False`` when the grant was not pending (redeemed, revoked or expired between the
        read and the write), in which case nothing changed.

        **One instant** decides the window and is the redemption time: the clock is read once, in a
        materialised one-row CTE (``clock_timestamp()`` is volatile, so the planner would otherwise
        evaluate it where it is written, once for the ``WHERE`` and once for the ``SET``). Two reads let a
        grant expire between them, and the row would then carry ``redeemed_at > expires_at`` --
        ``ck_executor_enrollment_redeemed_in_window`` -- which is a 500 and not the clean refusal (the
        caller's ``authentication_required``) a late redemption is."""
        return bool(session.execute(text(
            "WITH moment AS MATERIALIZED (SELECT clock_timestamp() AS t) "
            "UPDATE executor_enrollment SET redeemed_at = moment.t, runner_token_id = :token "
            "FROM moment WHERE enrollment_id = :id AND redeemed_at IS NULL "
            "AND revoked_at IS NULL AND expires_at > moment.t"
        ), {"id": enrollment_id, "token": token_id}).rowcount)

    # -- agent health, on the runner token ---------------------------------------------------

    def store_health(
        self, session: Session, token_id: str, *, agent_version: str,
        clis: Sequence[Mapping[str, Any]], concurrency: int, execution_profile: str,
        features: Sequence[str],
    ) -> datetime | None:
        """Replace the token's health with this report. ``None`` when the token is not there."""
        row = session.execute(text(
            "UPDATE executor_runner_token SET agent_version = :version, "
            "cli_health = CAST(:clis AS jsonb), concurrency = :concurrency, "
            "execution_profile = :profile, declared_features = CAST(:features AS jsonb), "
            "health_reported_at = clock_timestamp() WHERE token_id = :id "
            "RETURNING health_reported_at"
        ), {"id": token_id, "version": agent_version,
            "clis": json.dumps(list(clis), separators=(",", ":")),
            "concurrency": concurrency, "profile": execution_profile,
            "features": json.dumps(list(features), separators=(",", ":"))}).first()
        return None if row is None else row[0]

    def health_of_tokens(
        self, session: Session, token_ids: Sequence[str]
    ) -> dict[str, TokenHealth]:
        """The health of each token that has reported, with «online» read at this moment."""
        if not token_ids:
            return {}
        rows = session.execute(text(
            "SELECT token_id, agent_version, cli_health, concurrency, execution_profile, "
            "declared_features, health_reported_at, "
            "(revoked_at IS NULL AND expires_at > clock_timestamp() AND last_seen_at IS NOT NULL "
            "AND last_seen_at > clock_timestamp() - make_interval(secs => :online)) AS online "
            "FROM executor_runner_token WHERE token_id = ANY(:ids) "
            "AND health_reported_at IS NOT NULL"
        ), {"ids": list(token_ids), "online": RUNNER_ONLINE_SECONDS}).mappings().all()
        return {row["token_id"]: TokenHealth(
            token_id=row["token_id"], agent_version=row["agent_version"],
            clis=tuple(_json(row["cli_health"])), concurrency=int(row["concurrency"]),
            execution_profile=row["execution_profile"],
            features=tuple(_json(row["declared_features"])),
            reported_at=row["health_reported_at"], online=bool(row["online"]),
        ) for row in rows}

    def online_tokens(self, session: Session, connection_id: str) -> list[str]:
        """The connection's tokens that were seen within :data:`RUNNER_ONLINE_SECONDS` and are still
        usable, the most recently seen first: the agents that are there now."""
        rows = session.execute(text(
            "SELECT token_id FROM executor_runner_token WHERE connection_id = :c "
            "AND revoked_at IS NULL AND expires_at > clock_timestamp() "
            "AND last_seen_at IS NOT NULL "
            "AND last_seen_at > clock_timestamp() - make_interval(secs => :online) "
            "ORDER BY last_seen_at DESC, token_id DESC"
        ), {"c": connection_id, "online": RUNNER_ONLINE_SECONDS}).all()
        return [str(row[0]) for row in rows]
