"""Helpers for the durable repair suite; the fixtures are in ``conftest.py``.

Shared as a module (not through ``conftest``) so that the test modules and the fixtures see
one ``Killed`` and one ``MemoryStore`` class.

The no-network guard and the store selection are described in ``conftest.py``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from auditmanager.norms.repair_journal import (
    CallFailure,
    CallIntent,
    CallRow,
    CallState,
    DurableRepairRunner,
    LocalJournal,
    PreparedRequest,
    Settlement,
    StoreConflict,
    money,
)
from auditmanager.norms.rerecognition import PageToRecognise

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MODEL = "claude-opus-5"
BASE = "2026-07-23..2026-08-20+17d.4b74348debf7"
#: The SHA-256 of the operator's ``SHA256SUMS`` a journal header records (`W54-JUDGE-Y` F3).
SUMS = "5" * 64
PIXELS = 1241 * 1754

CLEAN_PAGE = (
    "##### 7.2 РАСЧЁТ ПО ПРЕДЕЛЬНЫМ СОСТОЯНИЯМ\n\n"
    "7.2.4 Расчёт элементов железобетонных конструкций по прочности производят "
    "для сечений, нормальных к их продольной оси."
)
DEGENERATE_PAGE = (
    "The user wants me to act as a strict transcription engine for Russian construction "
    "documents. I must adhere to the following rules: 1. Extract only visible text."
)


# --- the no-network guard ------------------------------------------------------------------


class LiveCallAttempted(AssertionError):
    pass


# --- answers ------------------------------------------------------------------------------


def openai_body(
    text: str,
    *,
    model: str = MODEL,
    cost: float | None = 0.03,
    finish_reason: str = "stop",
) -> bytes:
    """A chat-completions answer in the proxy's documented shape."""
    usage: dict[str, Any] = {"prompt_tokens": 1800, "completion_tokens": 900}
    if cost is not None:
        usage["cost"] = cost
    return json.dumps(
        {
            "id": "chatcmpl-test",
            "model": model,
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": text},
                 "finish_reason": finish_reason}
            ],
            "usage": usage,
        },
        ensure_ascii=False,
    ).encode("utf-8")


def page(slug: str = "СП_63_13330_2018", block: str = "a", *, crop: bytes | None = None) -> PageToRecognise:
    return PageToRecognise(
        document_slug=slug,
        block_id="blk_" + block * 32,
        page_label=70,
        original_text=DEGENERATE_PAGE,
        crop=crop if crop is not None else f"%PDF-1.4 crop {slug} {block}".encode(),
    )


# --- the scripted transport -----------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    raw: bytes


@dataclass(frozen=True)
class Fail:
    failure: str
    retry_safe: bool = False
    retry_after: float = 0.0


@dataclass(frozen=True)
class AnswerThenFail:
    """A body arrived (and was checkpointed), then the adapter refused to parse it."""

    raw: bytes


@dataclass
class ScriptedTransport:
    """A :class:`RepairTransport` that answers from a script and counts every dispatch.

    ``dispatches`` is the number of tries that left the process: in the real transport each
    one may be a paid call, so every no-re-pay assertion is made against it.
    """

    script: list[Any] = field(default_factory=list)
    model: str = MODEL
    dispatches: list[str] = field(default_factory=list)
    prepared: int = 0

    def prepare(self, page: PageToRecognise) -> PreparedRequest:
        self.prepared += 1
        return PreparedRequest(
            request_sha256=hashlib.sha256(b"request\0" + page.crop).hexdigest(),
            pixels=PIXELS,
            max_output_tokens=8000,
            payload={"block": page.block_id},
        )

    def dispatch(
        self, prepared: PreparedRequest, *, call_id: str, checkpoint: Callable[[bytes], None]
    ) -> None:
        self.dispatches.append(call_id)
        if not self.script:
            raise AssertionError("the transport was dispatched beyond its script")
        action = self.script.pop(0)
        if isinstance(action, Answer):
            checkpoint(action.raw)
            return
        if isinstance(action, AnswerThenFail):
            checkpoint(action.raw)
            raise CallFailure("proxy_outcome_unknown", retry_safe=False)
        if isinstance(action, Fail):
            raise CallFailure(action.failure, retry_safe=action.retry_safe,
                              retry_after_seconds=action.retry_after)
        raise AssertionError(f"unknown script action {action!r}")

    def read_answer(self, raw: bytes):
        from auditmanager.norms.__main__ import read_proxy_answer

        return read_proxy_answer(raw)


# --- the in-memory store ------------------------------------------------------------------


class MemoryStore:
    """:class:`CallStore` mirroring ``trg_norm_repair_call_guard`` and its CHECKs."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert_prepared(self, intent: CallIntent) -> None:
        if intent.call_id in self.rows:
            raise StoreConflict("duplicate primary key")
        for row in self.rows.values():
            if (row["block_anchor"], row["crop_sha256"], row["model"], row["attempt_number"]) == (
                intent.block_anchor, intent.crop_sha256, intent.model, intent.attempt_number
            ):
                raise StoreConflict("uq_norm_repair_call_try")
        self.rows[intent.call_id] = {
            "call_id": intent.call_id,
            "block_anchor": intent.block_anchor,
            "crop_sha256": intent.crop_sha256,
            "request_sha256": intent.request_sha256,
            "model": intent.model,
            "attempt_number": intent.attempt_number,
            "state": CallState.PREPARED,
            "response_sha256": None,
            "settlement": None,
        }

    def checkpoint(self, call_id: str, response_sha256: str) -> None:
        row = self.rows[call_id]
        if row["state"] is not CallState.PREPARED:
            raise StoreConflict("not prepared")
        row["state"] = CallState.RESPONSE_RECEIVED
        row["response_sha256"] = response_sha256

    def settle(self, call_id: str, settlement: Settlement) -> None:
        row = self.rows[call_id]
        required = (
            CallState.RESPONSE_RECEIVED
            if settlement.state is CallState.COMPLETED
            else CallState.PREPARED
        )
        if row["state"] is not required:
            raise StoreConflict(f"{row['state']} -> {settlement.state}")
        if settlement.state is CallState.NOT_PROCESSED and settlement.charged_usd != 0:
            raise StoreConflict("ck_norm_repair_call_outcome_shape")
        row["state"] = settlement.state
        row["settlement"] = Settlement(
            state=settlement.state,
            charged_usd=settlement.charged_usd,
            cost_usd=settlement.cost_usd,
            response_model=settlement.response_model,
            failure=settlement.failure,
        )

    def get(self, call_id: str) -> CallRow | None:
        row = self.rows.get(call_id)
        return None if row is None else CallRow(**row)

    def all_calls(self) -> list[CallRow]:
        return [CallRow(**row) for row in self.rows.values()]

    def charged_total(self) -> Decimal:
        return money(
            sum(
                (row["settlement"].charged_usd for row in self.rows.values()
                 if row["settlement"] is not None),
                Decimal(0),
            )
        )

    # --- the lost volume ------------------------------------------------------------------

    def dump(self) -> dict[str, dict[str, Any]]:
        return copy.deepcopy(self.rows)

    def restore(self, dump: dict[str, dict[str, Any]] | None) -> None:
        self.rows = copy.deepcopy(dump) if dump is not None else {}


# --- PostgreSQL (heavy: the owner's window) ----------------------------------------------------


def _load_dotenv_if_needed() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ").strip()
        name, separator, value = line.partition("=")
        if separator and name.strip() == "DATABASE_URL":
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ["DATABASE_URL"] = value


class PostgresStore:
    """The real :class:`SqlCallStore`, plus the lost-volume helpers the cases need.

    A dump is the table's rows; a restore truncates the table and replays each row through
    the store's own statements, so the guard sees exactly the moves a restored database holds.
    """

    def __init__(self, engine: Any) -> None:
        from auditmanager.norms.repair_journal import SqlCallStore
        from auditmanager.shared.db.session import create_session_factory

        self.engine = engine
        self.sql = SqlCallStore(create_session_factory(engine))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.sql, name)

    def truncate(self) -> None:
        from sqlalchemy import text

        with self.engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE norm_repair_call"))

    def dump(self) -> list[CallRow]:
        return self.sql.all_calls()

    def restore(self, dump: list[CallRow] | None) -> None:
        self.truncate()
        for row in dump or []:
            self.sql.insert_prepared(
                CallIntent(
                    call_id=row.call_id, document_slug="-", block_anchor=row.block_anchor,
                    page_label=0, crop_sha256=row.crop_sha256, request_sha256=row.request_sha256,
                    model=row.model, attempt_number=row.attempt_number, ordinal=1,
                    try_number=1, bound_usd=money(0), prepared_at="",
                )
            )
            if row.response_sha256 is not None:
                self.sql.checkpoint(row.call_id, row.response_sha256)
            if row.settlement is not None:
                self.sql.settle(row.call_id, row.settlement)


# --- the kit ------------------------------------------------------------------------------


class Killed(BaseException):
    """A simulated process death at a named durable step."""


@dataclass
class Kit:
    directory: Path
    store: Any
    transport: ScriptedTransport
    ceiling: Decimal = Decimal(10)
    slept: list[float] = field(default_factory=list)
    ticks: int = 0
    kill_at: str | None = None
    kill_after: int = 1
    seen: dict[str, int] = field(default_factory=dict)
    journal: LocalJournal | None = None

    def clock(self) -> str:
        self.ticks += 1
        return f"2026-10-12T00:{self.ticks // 60:02d}:{self.ticks % 60:02d}+00:00"

    def fault(self, point: str) -> None:
        self.seen[point] = self.seen.get(point, 0) + 1
        if point == self.kill_at and self.seen[point] == self.kill_after:
            raise Killed(point)

    def runner(self) -> DurableRepairRunner:
        """A fresh process: a newly opened journal and a new runner over the same store."""
        if self.journal is not None:
            self.journal.close()
        self.journal = LocalJournal(self.directory).open(
            base_snapshot=BASE, model=self.transport.model, ceiling_usd=self.ceiling,
            drop_sums_sha256=SUMS, now=self.clock(),
        )
        return DurableRepairRunner(
            journal=self.journal, store=self.store, transport=self.transport,
            clock=self.clock, sleep=self.slept.append, ceiling_usd=self.ceiling,
            fault=self.fault,
        )

    def close(self) -> None:
        if self.journal is not None:
            self.journal.close()
            self.journal = None
