"""In-memory stand-ins for the layout store, the command ledger and the availability port (`HOSTS-LAYOUT-01`). No database."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from auditmanager.analysis.public import CellSettings
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.runs.public import LayoutRevisionRow, ModelAvailability, SwitchEventRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, StageLayoutRevisionId

ADMIN = "usr_01M2545JSD15ETSNNV904X991A"
EXPERT = "usr_01M2545JSD15ETSNNV904X991B"
VIEWER = "usr_01M2545JSD15ETSNNV904X991C"
ROLES = {ADMIN: frozenset({"admin"}), EXPERT: frozenset({"expert"}), VIEWER: frozenset({"viewer"})}

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


class FakeSession:
    """A session that proves nothing is read or written around the store: any direct SQL fails the test."""

    commits = 0

    def commit(self) -> None:
        self.commits += 1

    def execute(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - reaching it is the failure
        raise AssertionError("a direct SQL statement was issued")


class FakeSessions:
    def __init__(self) -> None:
        self.session = FakeSession()

    @contextmanager
    def _open(self):
        yield self.session

    def __call__(self):
        return self._open()


class MemoryStore:
    def __init__(self) -> None:
        self.revisions: list[LayoutRevisionRow] = []
        self.events: list[SwitchEventRow] = []
        self.locked = 0

    def lock(self, session: Any) -> None:
        self.locked += 1

    def enabled(self, session: Any) -> bool:
        return bool(self.events) and self.events[-1].enabled

    def current_revision(self, session: Any) -> LayoutRevisionRow | None:
        return self.revisions[-1] if self.revisions else None

    def history(self, session: Any, *, limit: int) -> Sequence[LayoutRevisionRow]:
        return list(reversed(self.revisions))[:limit]

    def switch_journal(self, session: Any, *, limit: int) -> Sequence[SwitchEventRow]:
        return list(reversed(self.events))[:limit]

    def append_revision(
        self, session: Any, *, kit: str, cells: Sequence[CellSettings], created_by: str,
        comparison_cells: Sequence[CellSettings] | None = None,
    ) -> LayoutRevisionRow:
        row = LayoutRevisionRow(
            StageLayoutRevisionId.new().value, len(self.revisions) + 1, kit, tuple(cells), NOW, created_by,
            tuple(comparison_cells) if comparison_cells else None)
        self.revisions.append(row)
        return row

    def append_switch(self, session: Any, *, enabled: bool, set_by: str) -> SwitchEventRow:
        event = SwitchEventRow(enabled, NOW, set_by)
        self.events.append(event)
        return event


class MemoryCommands:
    """``CommandRepository`` in memory: a new key starts, the same key with the same payload replays, another payload is a reuse."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str], tuple[str, Mapping[str, Any] | None]] = {}

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any, fingerprint: Any):
        key = (command_type, str(idempotency_key))
        known = self.records.get(key)
        if known is None:
            self.records[key] = (str(fingerprint), None)
            return CommandStarted(CommandId.new())
        if known[0] != str(fingerprint):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_REUSE, command_type=command_type)
        return CommandReplay(CommandId.new(), known[1] or {})

    def succeed(self, session: Any, command_id: Any, outcome: Mapping[str, Any]) -> None:
        for key, (fingerprint, _) in list(self.records.items()):
            if self.records[key][1] is None:
                self.records[key] = (fingerprint, dict(outcome))


class MemoryAvailability:
    """``ModelAvailabilityPort``: a model is served as the test says; a model not mentioned is not on any server."""

    def __init__(self, served: Mapping[str, ModelAvailability] | None = None) -> None:
        self.served = dict(served or {})
        self.asked: list[tuple[str, ...]] = []

    def availability(self, session: Any, model_ids: Sequence[str]) -> Mapping[str, ModelAvailability]:
        self.asked.append(tuple(model_ids))
        return {model: self.served[model] for model in model_ids if model in self.served}


SUBSCRIPTION = ModelAvailability(subscription=True, api=True)
API_ONLY = ModelAvailability(api=True)
NOWHERE = ModelAvailability(reasons=("host_offline",))
ALL_MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra", "gpt-6-luna")


def everything(availability: ModelAvailability = SUBSCRIPTION) -> MemoryAvailability:
    return MemoryAvailability({model: availability for model in ALL_MODELS})


def with_revision(store: MemoryStore, cells: Sequence[CellSettings], kit: str = "claude_only", by: str = ADMIN) -> LayoutRevisionRow:
    return store.append_revision(None, kit=kit, cells=cells, created_by=by)
