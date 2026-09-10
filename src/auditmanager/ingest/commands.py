"""The command record: what makes an upload safe to retry and impossible to duplicate.

``command_record`` carries ``UNIQUE (command_type, idempotency_key)`` and the
``command_idempotency`` machine ``in_progress -> succeeded|failed|abandoned``. This
module is the only writer of that table in the ingest slice.

Why a record at all, rather than a retry
----------------------------------------
``docs/program/P02_SEAMS.md`` section 3.5: "there is no automatic retry -- a retry that
does not consult the command record writes duplicates." The record is the thing a retry
consults. A repeat of the same key with the same payload replays the recorded outcome
and creates nothing; the same key with a *different* payload is
``idempotency_key_reuse`` and creates nothing either.

The key is never an identity
----------------------------
``IdempotencyKey`` is a non-identity value type, and the frozen catalog lists
``idempotency_key`` among its *forbidden* envelope detail keys. Nothing here puts the
key in an error: every refusal below carries ``command_type`` and nothing else, which
is the only safe detail those codes declare.

The fingerprint
---------------
sha256 over the RFC 8785 (JCS) serialization of the normalized payload, which for this
command is the target project, the content digest, the byte size, the media type and
the source file name. Two requests that differ in any of those are different payloads,
so a client that reuses a key after changing the file learns about it instead of
silently getting the first upload back.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final, Mapping

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditmanager.documents import UNIQUE_VIOLATION, sqlstate_of
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, IdempotencyKey, PayloadFingerprint
from auditmanager.shared.statemachine import Topology, assert_initial, assert_transition
from auditmanager.shared.statemachine import load as load_topology

__all__ = [
    "COMMAND_MACHINE",
    "COMMAND_TYPE_UPLOAD",
    "CommandRecord",
    "CommandRepository",
    "CommandStarted",
    "CommandReplay",
    "payload_fingerprint",
]

#: The machine name as ``contract_state_transition`` spells it. Note that it is not the
#: table name: the contract calls the machine ``command_idempotency``.
COMMAND_MACHINE: Final[str] = "command_idempotency"

#: Matches ``ck_command_record_command_type``: lowercase snake_case, 3-64 characters.
COMMAND_TYPE_UPLOAD: Final[str] = "upload_source_document"

_COLUMNS = (
    "command_id, command_type, idempotency_key, payload_fingerprint, state, outcome, "
    "error_code"
)
_SELECT_BY_KEY = text(
    f"SELECT {_COLUMNS} FROM command_record "
    "WHERE command_type = :command_type AND idempotency_key = :idempotency_key"
)
_SELECT_BY_ID = text(f"SELECT {_COLUMNS} FROM command_record WHERE command_id = :command_id")
_INSERT = text(
    "INSERT INTO command_record "
    "(command_id, command_type, idempotency_key, payload_fingerprint, state) "
    "VALUES (:command_id, :command_type, :idempotency_key, :payload_fingerprint, :state)"
)
_SUCCEED = text(
    "UPDATE command_record SET state = :to_state, outcome = CAST(:outcome AS jsonb), "
    "updated_at = now() WHERE command_id = :command_id AND state = :from_state"
)
_TERMINATE = text(
    "UPDATE command_record SET state = :to_state, error_code = :error_code, "
    "updated_at = now() WHERE command_id = :command_id AND state = :from_state"
)
_STALE = text(
    f"SELECT {_COLUMNS} FROM command_record "
    "WHERE state = 'in_progress' AND updated_at < now() - CAST(:age AS interval) "
    "ORDER BY updated_at"
)


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    """RFC 8785-shaped serialization: sorted keys, no insignificant whitespace, UTF-8."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_fingerprint(payload: Mapping[str, Any]) -> PayloadFingerprint:
    """The comparison value that distinguishes a repeat from a same-key conflict."""
    return PayloadFingerprint(hashlib.sha256(_canonical_json(payload)).hexdigest())


@dataclass(frozen=True, slots=True)
class CommandRecord:
    """One row of ``command_record``. The key is held inside the trust boundary only."""

    command_id: CommandId
    command_type: str
    idempotency_key: IdempotencyKey
    payload_fingerprint: PayloadFingerprint
    state: str
    outcome: Mapping[str, Any] | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class CommandStarted:
    """The command is this caller's to execute. Nothing has been done yet."""

    command_id: CommandId


@dataclass(frozen=True, slots=True)
class CommandReplay:
    """The command already succeeded with this exact payload. Nothing was created."""

    command_id: CommandId
    outcome: Mapping[str, Any]


def _record(row: Any) -> CommandRecord:
    (
        command_id,
        command_type,
        idempotency_key,
        fingerprint,
        state,
        outcome,
        error_code,
    ) = tuple(row)
    return CommandRecord(
        command_id=CommandId(command_id),
        command_type=command_type,
        idempotency_key=IdempotencyKey(idempotency_key),
        payload_fingerprint=PayloadFingerprint(fingerprint),
        state=state,
        outcome=outcome,
        error_code=error_code,
    )


class CommandRepository:
    """Claim, replay and terminate command records."""

    __slots__ = ("_topology",)

    def __init__(self) -> None:
        self._topology: Topology | None = None

    def topology(self, session: Session) -> Topology:
        if self._topology is None:
            self._topology = load_topology(session)
        return self._topology

    def find(
        self, session: Session, *, command_type: str, idempotency_key: IdempotencyKey
    ) -> CommandRecord | None:
        row = session.execute(
            _SELECT_BY_KEY,
            {"command_type": command_type, "idempotency_key": str(idempotency_key)},
        ).first()
        return None if row is None else _record(row)

    def get(self, session: Session, command_id: CommandId) -> CommandRecord:
        row = session.execute(_SELECT_BY_ID, {"command_id": str(command_id)}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="CommandRecord")
        return _record(row)

    def begin(
        self,
        session: Session,
        *,
        command_type: str,
        idempotency_key: IdempotencyKey,
        fingerprint: PayloadFingerprint,
    ) -> CommandStarted | CommandReplay:
        """Claim the key, or answer what already happened under it.

        Every outcome other than :class:`CommandStarted` means this caller must not
        execute the command: it either already ran, is running, or ran under a
        different payload.
        """
        existing = self.find(
            session, command_type=command_type, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._answer_existing(existing, fingerprint)

        command_id = CommandId.new()
        assert_initial(self.topology(session), COMMAND_MACHINE, "in_progress")
        try:
            # A SAVEPOINT, not the caller's whole unit of work: losing the race for the
            # key is a step that is allowed to fail, and the enclosing transaction must
            # survive it so the winner's row can be read back and answered from.
            with nested_transaction(session):
                session.execute(
                    _INSERT,
                    {
                        "command_id": str(command_id),
                        "command_type": command_type,
                        "idempotency_key": str(idempotency_key),
                        "payload_fingerprint": str(fingerprint),
                        "state": "in_progress",
                    },
                )
        except IntegrityError as exc:
            if sqlstate_of(exc) != UNIQUE_VIOLATION:
                raise
            # A concurrent caller claimed the key between the read and the insert.
            winner = self.find(
                session, command_type=command_type, idempotency_key=idempotency_key
            )
            if winner is None:
                raise DomainError(
                    ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=command_type
                ) from None
            return self._answer_existing(winner, fingerprint)
        return CommandStarted(command_id=command_id)

    def succeed(
        self, session: Session, command_id: CommandId, outcome: Mapping[str, Any]
    ) -> None:
        """``in_progress -> succeeded``, recording the outcome a repeat replays."""
        assert_transition(self.topology(session), COMMAND_MACHINE, "in_progress", "succeeded")
        result = session.execute(
            _SUCCEED,
            {
                "command_id": str(command_id),
                "from_state": "in_progress",
                "to_state": "succeeded",
                "outcome": json.dumps(dict(outcome), sort_keys=True),
            },
        )
        self._require_moved(result.rowcount, "in_progress", "succeeded")

    def fail(self, session: Session, command_id: CommandId, code: ErrorCode) -> None:
        """``in_progress -> failed``, recording the catalog code that ended it."""
        self._terminate(session, command_id, "failed", code.value)

    def abandon(self, session: Session, command_id: CommandId) -> None:
        """``in_progress -> abandoned``: nobody can establish what this command did.

        Used by reconciliation on a record whose executor is gone. Abandoned is
        terminal, so the key is never reused; a caller retries with a new one.
        """
        self._terminate(session, command_id, "abandoned", ErrorCode.IDEMPOTENCY_KEY_STALE.value)

    def stale_in_progress(
        self, session: Session, *, older_than: str = "1 hour"
    ) -> tuple[CommandRecord, ...]:
        """Records still ``in_progress`` after their executor should have finished."""
        rows = session.execute(_STALE, {"age": older_than}).all()
        return tuple(_record(row) for row in rows)

    # -- internals -----------------------------------------------------------

    def _terminate(
        self, session: Session, command_id: CommandId, to_state: str, error_code: str
    ) -> None:
        assert_transition(self.topology(session), COMMAND_MACHINE, "in_progress", to_state)
        result = session.execute(
            _TERMINATE,
            {
                "command_id": str(command_id),
                "from_state": "in_progress",
                "to_state": to_state,
                "error_code": error_code,
            },
        )
        self._require_moved(result.rowcount, "in_progress", to_state)

    @staticmethod
    def _require_moved(rowcount: int, from_state: str, to_state: str) -> None:
        if rowcount != 1:
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine=COMMAND_MACHINE,
                current_state=from_state,
                requested_state=to_state,
            )

    @staticmethod
    def _answer_existing(
        existing: CommandRecord, fingerprint: PayloadFingerprint
    ) -> CommandReplay:
        """Decide what an already-claimed key means for this request.

        The fingerprint is compared first. A different payload under the same key is a
        conflict whatever state the earlier command reached, and answering that before
        looking at the state is what keeps a client from replaying somebody else's
        outcome as if it were its own.
        """
        command_type = existing.command_type
        if existing.payload_fingerprint != fingerprint:
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_REUSE, command_type=command_type)
        if existing.state == "succeeded" and existing.outcome is not None:
            return CommandReplay(
                command_id=existing.command_id, outcome=dict(existing.outcome)
            )
        if existing.state == "in_progress":
            raise DomainError(
                ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS, command_type=command_type
            )
        if existing.state == "failed" and existing.error_code:
            # Replay the recorded failure. The command is terminal, so re-running it
            # under the same key is not available; the answer is what happened.
            raise DomainError(ErrorCode(existing.error_code))
        raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=command_type)
