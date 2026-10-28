"""Helpers of the batch-operation suites (`CMP-INGEST-02`): a harness that drives the real upload service to a state,
and a queue harness that runs the real comparison runner over the two real handlers of this lane and a stand-in for the
page-profile handler (the profile builder has its own suites; here only *that it was asked, when and for what* matters).

Nothing here decides a result: every assertion is made by the tests, against the database and against the bucket through
a plain ``boto3`` client that does not go through the code under test.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.public import (
    Completed,
    ComparisonWorkRepository,
    ComparisonWorkRunner,
    HandlerRegistry,
    WorkDependencies,
    WorkItem,
)
from auditmanager.ingest.comparison_batch.public import (
    BatchDriveHandler,
    ComparisonBatchService,
    UploadSweepHandler,
)
from auditmanager.ingest.comparison_pdf.public import (
    ComparisonUploadService,
    ConfirmedFile,
    DeclaredFileRequest,
    SetView,
    UploadView,
)
from auditmanager.shared.db import session_scope
from tests.integration.ingest.comparison_pdf.support import padded_pdf, parts_of, sha256

LABEL = "Эксперт Проверкин"
EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})
_serial = itertools.count(1)


def fresh_key(prefix: str = "k") -> str:
    return f"{prefix}-{next(_serial)}"


def distinct_pdf() -> bytes:
    """A valid one-page PDF whose bytes (and digest) differ from every other this process made."""
    return padded_pdf(3000 + next(_serial))


@dataclass
class Harness:
    """One project, one expert, the real services: the states of a batch are reached by the real operations."""

    comparison: ComparisonUploadService
    batches: ComparisonBatchService
    sessions: sessionmaker[Session]
    project_uid: str
    user: str
    contents: dict[str, bytes] = field(default_factory=dict)

    # -- reaching a state ------------------------------------------------------------------------------

    def declare(self, names: Sequence[str], *, user: str | None = None) -> UploadView:
        files = {name: distinct_pdf() for name in names}
        self.contents.update(files)
        view = self.comparison.create_upload(
            project_uid=self.project_uid,
            files=[DeclaredFileRequest(display_name=n, size_bytes=len(d), sha256=sha256(d)) for n, d in files.items()],
            user_uid=user or self.user, actor_label=LABEL, idempotency_key=fresh_key("create"),
        )
        self.batches.after_declaration(upload_id=view.upload_id)
        return view

    def send(self, upload_id: str, file_id: str, name: str, *, only_first_part: bool = False) -> None:
        data = self.contents[name]
        for number, part in enumerate(parts_of(data), start=1):
            self.comparison.put_part(
                upload_id=upload_id, file_id=file_id, part_number=number, content=part, user_uid=self.user,
                idempotency_key=fresh_key("part"),
            )

    def complete(self, upload_id: str, file_id: str) -> None:
        self.comparison.complete_file(
            upload_id=upload_id, file_id=file_id, user_uid=self.user, idempotency_key=fresh_key("done")
        )

    def proposed(self, sets: Mapping[str, int], *, owner: str | None = None) -> str:
        """Declare, send and complete ``{base name: number of files}``; the batch ends ``proposed`` with one set per
        base name (a name is a hint, and these have no stamps). ``owner`` is the account that declares it (an account
        may have one active batch, so a second batch in a test is another account's)."""
        names = [f"{base} ({i}).pdf" for base, count in sets.items() for i in range(1, count + 1)]
        view = self.declare(names, user=owner)
        by_name = {item.display_name: item.file_id for item in view.files or ()}
        for name in names:
            self.send(view.upload_id, by_name[name], name)
            self.complete(view.upload_id, by_name[name])
        assert self.comparison.get_upload(upload_id=view.upload_id).state == "proposed"
        return view.upload_id

    def sets(self, upload_id: str) -> list[SetView]:
        return list(self.comparison.get_proposal(upload_id=upload_id).sets)

    def confirm(self, upload_id: str, set_view: SetView, *, hook: bool = True, key: str | None = None) -> SetView:
        done = self.comparison.confirm_set(
            upload_id=upload_id, set_id=set_view.set_id,
            files=[ConfirmedFile(item.file_id, item.version_label) for item in set_view.files],
            designation=None, existing_document_uid=None, project_stage=None, section_code=None,
            user_uid=self.user, actor_roles=EXPERT, idempotency_key=key or fresh_key("confirm"),
        )
        if hook:
            self.batches.after_confirmation(upload_id=upload_id, set_id=set_view.set_id)
        return done

    # -- the acts, as an expert -------------------------------------------------------------------------

    def pause(self, upload_id: str, *, key: str | None = None, roles: frozenset[str] = EXPERT) -> UploadView:
        return self.batches.pause_upload(
            upload_id=upload_id, user_uid=self.user, actor_roles=roles, idempotency_key=key or fresh_key("pause")
        )

    def resume(self, upload_id: str, *, key: str | None = None, roles: frozenset[str] = EXPERT) -> UploadView:
        return self.batches.resume_upload(
            upload_id=upload_id, user_uid=self.user, actor_roles=roles, idempotency_key=key or fresh_key("resume")
        )

    def cancel(self, upload_id: str, *, key: str | None = None, roles: frozenset[str] = EXPERT) -> UploadView:
        return self.batches.cancel_upload(
            upload_id=upload_id, user_uid=self.user, actor_roles=roles, idempotency_key=key or fresh_key("cancel")
        )

    def exclude(self, upload_id: str, set_id: str, *, key: str | None = None, roles: frozenset[str] = EXPERT) -> SetView:
        return self.batches.exclude_set(
            upload_id=upload_id, set_id=set_id, user_uid=self.user, actor_roles=roles,
            idempotency_key=key or fresh_key("exclude"),
        )

    def retry(self, upload_id: str, set_id: str, *, key: str | None = None, roles: frozenset[str] = EXPERT) -> SetView:
        return self.batches.retry_set(
            upload_id=upload_id, set_id=set_id, user_uid=self.user, actor_roles=roles,
            idempotency_key=key or fresh_key("retry"),
        )

    # -- reading the database ---------------------------------------------------------------------------

    def rows(self, sql: str, **params: Any) -> list[tuple[Any, ...]]:
        with self.sessions() as session:
            return [tuple(row) for row in session.execute(text(sql), params).all()]

    def state(self, upload_id: str) -> str:
        return str(self.rows("SELECT state FROM comparison_upload WHERE comparison_upload_id = :i", i=upload_id)[0][0])

    def set_states(self, upload_id: str) -> dict[str, str]:
        return {r[0]: r[1] for r in self.rows(
            "SELECT comparison_upload_set_id, state FROM comparison_upload_set WHERE comparison_upload_id = :i", i=upload_id)}

    def work(self, upload_id: str | None = None, *, kind: str | None = None) -> list[dict[str, Any]]:
        """The queue rows of the project (or of one batch), oldest first."""
        with self.sessions() as session:
            rows = session.execute(text(
                "SELECT comparison_work_id AS id, kind, state, payload, dedupe_key, comparison_upload_id AS upload, "
                "cancel_requested_at IS NOT NULL AS cancel_requested, not_before, failure_reason "
                "FROM comparison_work WHERE project_uid = :p "
                "AND (CAST(:u AS text) IS NULL OR comparison_upload_id = :u) "
                "AND (CAST(:k AS text) IS NULL OR kind = :k) ORDER BY created_at, comparison_work_id"
            ), {"p": self.project_uid, "u": upload_id, "k": kind}).mappings().all()
            return [dict(row) for row in rows]

    def make_due(self, kind: str) -> None:
        """What the passing of time does to a delayed item: its time has come."""
        with session_scope(self.sessions) as session:
            session.execute(text(
                "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                "WHERE project_uid = :p AND kind = :k AND state = 'queued'"
            ), {"p": self.project_uid, "k": kind})

    def make_idle(self, upload_id: str, *, seconds: float) -> None:
        """Make the batch look untouched for ``seconds`` (its ``updated_at`` is moved back on the database's clock)."""
        with session_scope(self.sessions) as session:
            session.execute(text(
                "UPDATE comparison_upload SET updated_at = clock_timestamp() - make_interval(secs => :s) "
                "WHERE comparison_upload_id = :i"
            ), {"s": seconds, "i": upload_id})


class FakeProfiles:
    """A stand-in for the ``page_profile`` handler: it records what it was asked for and completes."""

    kind = "page_profile"

    def __init__(self) -> None:
        self.seen: list[tuple[str, str | None]] = []
        self.outcome: Any = Completed()

    def run(self, item: WorkItem) -> Any:
        self.seen.append((str(item.payload["version_uid"]), item.comparison_upload_id))
        return self.outcome


class Queue:
    """The real runner, real gates and the two real handlers of this lane over the throwaway database."""

    def __init__(self, sessions: sessionmaker[Session], engine: Any, store: Any, *, lifecycle: Any = None) -> None:
        from auditmanager.ingest.comparison_batch.lifecycle import BatchLifecycle

        self.sessions = sessions
        self.profiles = FakeProfiles()
        work = ComparisonWorkRepository()
        deps = WorkDependencies(engine=engine, session_factory=sessions, blob_store=store, work=work)
        self.drive = BatchDriveHandler(deps, lifecycle=lifecycle or BatchLifecycle(work=work, sweep_delay_seconds=0.0))
        self.sweep = UploadSweepHandler(deps)
        self.runner = ComparisonWorkRunner(
            sessions,
            registry=HandlerRegistry({h.kind: h for h in (self.profiles, self.drive, self.sweep)}),
            modules=frozenset({"versions"}), repository=work, heartbeat_seconds=3600.0,
        )
        self._worker: str | None = None

    def worker(self) -> str:
        from auditmanager.workers.public import WorkerRegistry

        if self._worker is None:
            with self.sessions() as session:
                self._worker = WorkerRegistry().register(session, version="cmp-ingest-02-test", slots=1)
                session.commit()
        return self._worker

    def claim(self) -> WorkItem | None:
        return self.runner.claim(self.worker())

    def run_one(self) -> tuple[str, str | None] | None:
        item = self.claim()
        if item is None:
            return None
        return item.kind, self.runner.execute(item)

    def run_all(self, *, limit: int = 60) -> list[tuple[str, str | None]]:
        """Claim and run until nothing is due (an item that yielded waits for its time and is not due)."""
        ran: list[tuple[str, str | None]] = []
        for _ in range(limit):
            step = self.run_one()
            if step is None:
                return ran
            ran.append(step)
        raise AssertionError(f"the queue was still producing work after {limit} items: {ran[-6:]}")
