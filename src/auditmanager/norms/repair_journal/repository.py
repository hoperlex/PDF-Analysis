"""The database half of the paid repair journal: the only writer of ``norm_repair_call``.

Every method is its own short transaction, committed before it returns: `R-106`'s write
order needs the row committed *before* a call is dispatched and each effect committed
*before* the file records it. ``trg_norm_repair_call_guard`` (`0018`) re-checks every move —
created ``prepared`` only; ``prepared -> response_received | not_processed |
outcome_unknown``; ``response_received -> completed``; immutable within a state; never
deleted — so a statement here that disagreed with the machine is refused there.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .model import CallIntent, CallRow, CallState, Settlement, money


class CallStore(Protocol):
    """What the runner needs from the database. :class:`SqlCallStore` is the real one."""

    def insert_prepared(self, intent: CallIntent) -> None: ...

    def checkpoint(self, call_id: str, response_sha256: str) -> None: ...

    def settle(self, call_id: str, settlement: Settlement) -> None: ...

    def get(self, call_id: str) -> CallRow | None: ...

    def all_calls(self) -> list[CallRow]: ...

    def charged_total(self) -> Decimal: ...


_COLUMNS = (
    "norm_repair_call_id, block_anchor, crop_sha256, request_sha256, model, attempt_number, "
    "state, response_sha256, response_model, cost_usd, charged_usd, failure"
)

_INSERT = text(
    """
    INSERT INTO norm_repair_call (
        norm_repair_call_id, idempotency_scope, block_anchor, crop_sha256, request_sha256,
        model, attempt_number
    ) VALUES (:id, :id, :block_anchor, :crop_sha256, :request_sha256, :model, :attempt_number)
    """
)
_CHECKPOINT = text(
    """
    UPDATE norm_repair_call
       SET state = 'response_received', response_sha256 = :sha, updated_at = clock_timestamp()
     WHERE norm_repair_call_id = :id AND state = 'prepared'
    """
)
_COMPLETE = text(
    """
    UPDATE norm_repair_call
       SET state = 'completed', response_model = :response_model, cost_usd = :cost_usd,
           charged_usd = :charged_usd, failure = :failure, updated_at = clock_timestamp(),
           terminal_at = clock_timestamp()
     WHERE norm_repair_call_id = :id AND state = 'response_received'
    """
)
_SETTLE_UNANSWERED = text(
    """
    UPDATE norm_repair_call
       SET state = :state, charged_usd = :charged_usd, failure = :failure,
           updated_at = clock_timestamp(), terminal_at = clock_timestamp()
     WHERE norm_repair_call_id = :id AND state = 'prepared'
    """
)
_GET = text(f"SELECT {_COLUMNS} FROM norm_repair_call WHERE norm_repair_call_id = :id")
_ALL = text(f"SELECT {_COLUMNS} FROM norm_repair_call ORDER BY prepared_at, norm_repair_call_id")
_CHARGED = text(
    "SELECT coalesce(sum(charged_usd), 0) FROM norm_repair_call "
    "WHERE state IN ('completed', 'not_processed', 'outcome_unknown')"
)


class StoreConflict(RuntimeError):
    """A guarded update matched no row: the row is not in the state the runner believed."""


def _row(mapping: Any) -> CallRow:
    state = CallState(mapping["state"])
    settlement = None
    if state.terminal:
        settlement = Settlement(
            state=state,
            charged_usd=money(mapping["charged_usd"]),
            cost_usd=None if mapping["cost_usd"] is None else money(mapping["cost_usd"]),
            response_model=mapping["response_model"],
            failure=mapping["failure"],
        )
    return CallRow(
        call_id=mapping["norm_repair_call_id"],
        block_anchor=mapping["block_anchor"],
        crop_sha256=mapping["crop_sha256"],
        request_sha256=mapping["request_sha256"],
        model=mapping["model"],
        attempt_number=int(mapping["attempt_number"]),
        state=state,
        response_sha256=mapping["response_sha256"],
        settlement=settlement,
    )


class SqlCallStore:
    """:class:`CallStore` over the promotion database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def insert_prepared(self, intent: CallIntent) -> None:
        with self._sessions.begin() as session:
            session.execute(
                _INSERT,
                {
                    "id": intent.call_id,
                    "block_anchor": intent.block_anchor,
                    "crop_sha256": intent.crop_sha256,
                    "request_sha256": intent.request_sha256,
                    "model": intent.model,
                    "attempt_number": intent.attempt_number,
                },
            )

    def checkpoint(self, call_id: str, response_sha256: str) -> None:
        with self._sessions.begin() as session:
            moved = session.execute(_CHECKPOINT, {"id": call_id, "sha": response_sha256}).rowcount
            if moved != 1:
                raise StoreConflict(f"{call_id}: not prepared, so no response can be checkpointed")

    def settle(self, call_id: str, settlement: Settlement) -> None:
        with self._sessions.begin() as session:
            if settlement.state is CallState.COMPLETED:
                moved = session.execute(
                    _COMPLETE,
                    {
                        "id": call_id,
                        "response_model": settlement.response_model,
                        "cost_usd": settlement.cost_usd,
                        "charged_usd": settlement.charged_usd,
                        "failure": settlement.failure,
                    },
                ).rowcount
            else:
                moved = session.execute(
                    _SETTLE_UNANSWERED,
                    {
                        "id": call_id,
                        "state": settlement.state.value,
                        "charged_usd": settlement.charged_usd,
                        "failure": settlement.failure,
                    },
                ).rowcount
            if moved != 1:
                raise StoreConflict(
                    f"{call_id}: cannot settle as {settlement.state.value} from its current state"
                )

    def get(self, call_id: str) -> CallRow | None:
        with self._sessions() as session:
            found = session.execute(_GET, {"id": call_id}).mappings().first()
        return None if found is None else _row(found)

    def all_calls(self) -> list[CallRow]:
        with self._sessions() as session:
            return [_row(found) for found in session.execute(_ALL).mappings()]

    def charged_total(self) -> Decimal:
        with self._sessions() as session:
            return money(session.execute(_CHARGED).scalar_one())
