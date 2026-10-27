"""Helpers of the comparison spend journal's database tests (`CMP-SPEND-01`): the scripted model adapter, the
route, consent and request builders, the committed reads of the journal and the queue. Plain code: the fixtures
that hand it to a test are in ``conftest.py`` (a test never imports a ``conftest``)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelPin, ModelRequest, ModelResponse, ProviderMode
from auditmanager.comparison.public import (
    CallEstimate,
    CallRoute,
    ComparisonModelCaller,
    ComparisonWorkRepository,
    Consent,
    WorkItem,
)

MODEL = "claude-opus-5"
GATEWAY = "anthropic/claude-opus-5"
#: USD 1 per million input tokens, USD 5 per million output tokens.
PIN = ModelPin(model_id=MODEL, input_per_mtok_usd=1.0, output_per_mtok_usd=5.0)
DIGEST = "ab" * 32
#: USD 2.00 at the pin above.
ESTIMATE = CallEstimate(input_tokens=1_000_000, output_tokens=200_000)


class Queue:
    """Enqueue and claim items of one kind under one project, and read what the tests assert on."""

    def __init__(self, sessions: sessionmaker[Session], project_uid: str, kind: str, worker: str) -> None:
        self.sessions, self.project_uid, self.kind, self.worker = sessions, project_uid, kind, worker
        self.repository = ComparisonWorkRepository()

    def claimed(self, **payload: Any) -> WorkItem:
        with self.sessions() as session:
            self.repository.enqueue(
                session, project_uid=self.project_uid, module="versions", kind=self.kind, payload=payload,
            )
            session.commit()
        with self.sessions() as session:
            item = self.repository.claim(
                session, worker_id=self.worker, modules=frozenset({"versions"}), kinds=frozenset({self.kind}),
            )
            session.commit()
        assert item is not None, "the item was not claimed"
        return item

    def expire_and_reclaim(self, item: WorkItem, *, settlers: tuple[Any, ...]) -> int:
        """What a killed worker leaves and the queue's reclaim does about it."""
        with self.sessions() as session:
            session.execute(text(
                "UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
                "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
            session.commit()
        with self.sessions() as session:
            recovered = self.repository.reclaim_expired(session, spend_settlers=settlers)
            session.commit()
        return recovered

    def work_state(self, work_id: str) -> str:
        with self.sessions() as session:
            return str(session.execute(
                text("SELECT state FROM comparison_work WHERE comparison_work_id = :w"), {"w": work_id}).scalar_one())

    def make_due(self, work_id: str) -> None:
        with self.sessions() as session:
            session.execute(text(
                "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                "WHERE comparison_work_id = :w"), {"w": work_id})
            session.commit()

    def reclaim_item(self, *, worker: str | None = None) -> WorkItem | None:
        with self.sessions() as session:
            item = self.repository.claim(
                session, worker_id=worker or self.worker, modules=frozenset({"versions"}),
                kinds=frozenset({self.kind}),
            )
            session.commit()
        return item


class Journal:
    """Committed reads of ``comparison_model_call``, independent of the code under test."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def rows(self, work_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(row) for row in session.execute(text(
                "SELECT comparison_model_call_id AS call_id, comparison_work_attempt_id AS attempt_id, state, "
                "provider_mode, model_identity, connection_revision_id, request_sha256, estimate_micros, "
                "response_sha256, input_tokens, output_tokens, cost_basis, cost_micros, error_code, "
                "sent_at IS NOT NULL AS has_sent, terminal_at IS NOT NULL AS has_terminal "
                "FROM comparison_model_call WHERE comparison_work_id = :w ORDER BY prepared_at, comparison_model_call_id"
            ), {"w": work_id}).mappings()]

    def count(self) -> int:
        with self.sessions() as session:
            return int(session.execute(text("SELECT count(*) FROM comparison_model_call")).scalar_one())

    def insert(
        self, work_id: str, attempt_id: str, *, state: str = "completed", cost_micros: int = 0,
        estimate_micros: int = 0, connection_revision_id: str | None = None, days_ago: int = 0,
        provider_mode: str = "live", cost_basis: str | None = None,
    ) -> str:
        """A row of the journal in a given state, made the only way the database allows: inserted
        ``prepared`` (optionally on an earlier day), then moved along the edges."""
        from auditmanager.shared.identity import ComparisonModelCallId

        call_id = str(ComparisonModelCallId.new())
        with self.sessions() as session:
            session.execute(text(
                "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, "
                "comparison_work_attempt_id, work_kind, provider_mode, model_identity, connection_revision_id, "
                "request_sha256, estimate_micros, prepared_at) SELECT :id, w.comparison_work_id, :a, w.kind, :mode, "
                ":model, :rev, :sha, :est, clock_timestamp() - make_interval(days => :days) "
                "FROM comparison_work w WHERE w.comparison_work_id = :w"
            ), {"id": call_id, "w": work_id, "a": attempt_id, "mode": provider_mode, "model": MODEL,
                "rev": connection_revision_id, "sha": DIGEST, "est": estimate_micros, "days": days_ago})
            if state in ("sent", "completed"):
                session.execute(text(
                    "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
                    "WHERE comparison_model_call_id = :id"), {"id": call_id})
            if state == "completed":
                session.execute(text(
                    "UPDATE comparison_model_call SET state = 'completed', response_sha256 = :sha, input_tokens = 1, "
                    "output_tokens = 1, latency_ms = 1, cost_basis = :basis, cost_micros = :cost, "
                    "terminal_at = clock_timestamp() WHERE comparison_model_call_id = :id"
                ), {"id": call_id, "sha": DIGEST, "cost": cost_micros,
                    "basis": cost_basis or ("unmetered" if cost_micros == 0 and provider_mode == "recorded" else "measured")})
            elif state == "failed":
                session.execute(text(
                    "UPDATE comparison_model_call SET state = 'failed', error_code = 'provider_refused', "
                    "cost_basis = :basis, cost_micros = :cost, terminal_at = clock_timestamp() "
                    "WHERE comparison_model_call_id = :id"),
                    {"id": call_id, "cost": cost_micros or None, "basis": "measured" if cost_micros else None})
            elif state == "unknown":
                session.execute(text(
                    "UPDATE comparison_model_call SET state = 'unknown', error_code = 'attempt_lost', "
                    "terminal_at = clock_timestamp() WHERE comparison_model_call_id = :id"), {"id": call_id})
            session.commit()
        return call_id


@dataclass
class ScriptedAdapter:
    """The model seam: what it returns or raises is the test's; what it *saw* when called is recorded.

    ``on_call(request)`` runs inside ``complete``, after the call is counted -- where a test inspects the database
    from a connection of its own (exactly what a crash at that instant leaves) or plays the reclaim.
    """

    mode: ProviderMode = ProviderMode.LIVE
    reply: ModelResponse | None = None
    error: BaseException | None = None
    on_call: Callable[[ModelRequest], None] | None = None
    calls: int = 0
    requests: list[ModelRequest] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def provider_mode(self) -> ProviderMode:
        return self.mode

    def complete(self, request: ModelRequest) -> ModelResponse:
        with self.lock:
            self.calls += 1
            self.requests.append(request)
        if self.on_call is not None:
            self.on_call(request)
        if self.error is not None:
            raise self.error
        assert self.reply is not None
        return self.reply


def reply(*, model: str | None = GATEWAY, cost: float | None = None, tokens: tuple[int, int] = (500_000, 100_000)) -> ModelResponse:
    return ModelResponse(
        output_text="{}", stop_reason="end_turn", input_tokens=tokens[0], output_tokens=tokens[1], latency_ms=900,
        reported_cost_usd=cost, model=model,
    )


def route(adapter: ScriptedAdapter, revision_id: str | None, **over: Any) -> CallRoute:
    values: dict[str, Any] = {
        "adapter": adapter, "model_identity": MODEL, "connection_revision_id": revision_id,
        "expected_model": GATEWAY, "check_identity": True, "unmetered": False, "pin": PIN,
    }
    values.update(over)
    return CallRoute(**values)


def consent(revision_id: str | None, **over: Any) -> Consent:
    values: dict[str, Any] = {
        "estimate_digest": DIGEST, "estimate_usd": 5.0, "ceiling_usd": 10.0,
        "connection_revision_id": revision_id, "pinned_model": MODEL,
    }
    values.update(over)
    return Consent(**values)


def request(label: str = "x") -> ModelRequest:
    return ModelRequest(model_id=MODEL, body={"model": MODEL, "messages": [{"role": "user", "content": label}]})


def make_call(
    caller: ComparisonModelCaller, item: WorkItem, adapter: ScriptedAdapter, revision_id: str | None, *,
    label: str = "x", consent_over: dict[str, Any] | None = None, route_over: dict[str, Any] | None = None,
    estimate: CallEstimate = ESTIMATE, with_consent: bool = True,
) -> Any:
    return caller.call(
        item, route(adapter, revision_id, **(route_over or {})), request(label), estimate=estimate,
        consent=consent(revision_id, **(consent_over or {})) if with_consent else None,
    )
