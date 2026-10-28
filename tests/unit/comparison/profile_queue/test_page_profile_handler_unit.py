"""The handler of the ``page_profile`` kind without a database or a child (`CMP-PROFILE-QUEUE-01`). Container-free.

A fake builder stands where ``build_version_page_profiles`` stands: it stores "pages" one at a time and calls
``on_page`` after each, as the real one does, so what is shown here is the handler's decision at each point -- what
ends the item, what retries it, what stops the build between pages and where. The same behaviours run against
PostgreSQL, the real children and the real runner in ``tests/integration/comparison/profile_queue``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.profile.builder import PageBuildReport, VersionBuildReport
from auditmanager.comparison.profile.runner import ChildStartError
from auditmanager.comparison.public import (
    HANDLER_FACTORIES,
    PAGE_PROFILE_WORK_KIND,
    Completed,
    Failed,
    HandlerRegistry,
    HandlerRegistryError,
    PageProfileHandler,
    Yielded,
    page_profile_handler,
)
from auditmanager.comparison.profile_queue.handler import (
    PAGE_PROFILE_KIND,
    REASON_CHILD_START_FAILED,
    REASON_INCOMPLETE,
    REASON_PAYLOAD_INVALID,
    REASON_SOURCE_UNREADABLE,
    REASON_VERSION_NOT_FOUND,
    page_profile_payload,
    read_payload,
)
from auditmanager.comparison.work.model import ItemAuthority, WorkItem
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class FakeSession:
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def commit(self) -> None:
        self.log.append("commit")


class FakeWork:
    """What the handler asks of the queue between pages: extend the lease, ask for a cancel."""

    def __init__(self) -> None:
        self.heartbeats = 0
        self.cancel_reads = 0
        #: the n-th heartbeat (1-based) and later answer "the lease is gone"
        self.lease_gone_from: int | None = None
        #: the n-th read (1-based) and later answer "a cancel was requested"
        self.cancel_from: int | None = None

    def heartbeat(self, session: Any, authority: Any) -> bool:
        self.heartbeats += 1
        return self.lease_gone_from is None or self.heartbeats < self.lease_gone_from

    def cancel_requested(self, session: Any, work_id: str) -> bool:
        self.cancel_reads += 1
        return self.cancel_from is not None and self.cancel_reads >= self.cancel_from


class FakeRepository:
    """What ``WorkItem.check_current`` calls."""

    def __init__(self) -> None:
        self.checks = 0
        self.error_from: int | None = None
        self.error: Exception = DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")

    def check_current(self, session: Any, authority: Any) -> None:
        self.checks += 1
        if self.error_from is not None and self.checks >= self.error_from:
            raise self.error


def make_item(repository: FakeRepository, payload: dict[str, Any] | None = None) -> WorkItem:
    return WorkItem(
        work_id="cq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        attempt_id="cqa_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        attempt_no=1,
        project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        module="versions",
        kind=PAGE_PROFILE_KIND,
        payload=page_profile_payload(VERSION) if payload is None else payload,
        comparison_upload_id=None,
        created_by_user_uid=None,
        max_attempts=3,
        authority=ItemAuthority("cq_01ARZ3NDEKTSV4RRFFQ69G5FAV", "cqa_01ARZ3NDEKTSV4RRFFQ69G5FAV", "token"),
        _repository=repository,  # type: ignore[arg-type]
    )


class Harness:
    """A handler over fakes, and a builder that stores ``page_count`` pages one at a time."""

    def __init__(self, *, page_count: int = 6, skipped: int = 0) -> None:
        self.log: list[str] = []
        self.work = FakeWork()
        self.repository = FakeRepository()
        self.page_count = page_count
        self.skipped = skipped
        self.stored: list[int] = []
        self.calls: list[dict[str, Any]] = []
        self.raises: BaseException | None = None
        self.raises_after: int | None = None
        self.report_pages: int | None = None  # how many of the wanted pages the report claims
        dependencies = SimpleNamespace(
            session_factory=lambda: FakeSession(self.log), blob_store=object(), work=self.work,
        )
        self.runner = object()
        self.handler = PageProfileHandler(dependencies, runner=self.runner, build=self.build)  # type: ignore[arg-type]

    def build(
        self, session_factory: Any, blob_store: Any, version_uid: str, *, runner: Any = None,
        retry_failed: bool = False, on_page: Callable[[PageBuildReport], None] | None = None, **rest: Any,
    ) -> VersionBuildReport:
        self.calls.append({"version_uid": version_uid, "runner": runner, "retry_failed": retry_failed,
                           "on_page": on_page, "rest": rest})
        if self.raises is not None and self.raises_after is None:
            raise self.raises
        reports: list[PageBuildReport] = []
        for number in range(self.skipped + 1, self.page_count + 1):
            if self.report_pages is not None and len(reports) >= self.report_pages:
                break
            self.stored.append(number)
            report = PageBuildReport(number, f"cpr_{number}", "ready", None, True)
            reports.append(report)
            if self.raises is not None and self.raises_after == len(reports):
                raise self.raises
            if on_page is not None:
                on_page(report)
        return VersionBuildReport(version_uid, "cmp-profile/1", self.page_count, tuple(reports), self.skipped)

    def run(self, item: WorkItem | None = None) -> Any:
        return self.handler.run(item or make_item(self.repository))


# -- the kind, the factory, the registry ---------------------------------------------------------------


def test_the_handler_has_the_kind_the_profile_lane_named_and_is_the_one_factory_of_it() -> None:
    assert PAGE_PROFILE_KIND == PAGE_PROFILE_WORK_KIND == "page_profile"
    assert page_profile_handler in HANDLER_FACTORIES
    handler = page_profile_handler(SimpleNamespace())  # a factory costs nothing and touches nothing
    assert handler.kind == PAGE_PROFILE_WORK_KIND


def test_the_shipped_tuple_holds_one_handler_for_the_kind_and_a_second_is_refused() -> None:
    dependencies: Any = SimpleNamespace()
    registry = HandlerRegistry.build(HANDLER_FACTORIES, dependencies)
    assert PAGE_PROFILE_WORK_KIND in registry.kinds
    assert [factory(dependencies).kind for factory in HANDLER_FACTORIES].count(PAGE_PROFILE_WORK_KIND) == 1
    assert isinstance(registry.handler(PAGE_PROFILE_WORK_KIND), PageProfileHandler)
    with pytest.raises(HandlerRegistryError, match=PAGE_PROFILE_WORK_KIND):
        HandlerRegistry.build((*HANDLER_FACTORIES, page_profile_handler), dependencies)


# -- the payload -----------------------------------------------------------------------------------------


def test_the_payload_is_the_version_and_only_a_retry_that_is_asked_for() -> None:
    assert page_profile_payload(VERSION) == {"version_uid": VERSION}
    assert page_profile_payload(VERSION, retry_failed=True) == {"version_uid": VERSION, "retry_failed": True}
    assert read_payload({"version_uid": VERSION}) == (VERSION, False)
    assert read_payload({"version_uid": VERSION, "retry_failed": True}) == (VERSION, True)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"version_uid": None},
        {"version_uid": 7},
        {"version_uid": "not-an-identity"},
        {"version_uid": "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"},  # an identity of another entity
        {"version_uid": VERSION + "\n"},
        {"version_uid": VERSION, "retry_failed": "yes"},
        {"version_uid": VERSION, "retry_failed": 1},
        {"version_uid": VERSION, "pages": [1, 2]},
        {"version_uid": VERSION, "path": "/tmp/x.pdf"},
    ],
)
def test_a_payload_of_another_shape_fails_without_a_retry_and_starts_no_build(payload: dict[str, Any]) -> None:
    harness = Harness()
    outcome = harness.run(make_item(harness.repository, payload))
    assert outcome == Failed(REASON_PAYLOAD_INVALID, retry=False)
    assert harness.calls == [] and harness.work.heartbeats == 0


# -- how a build ends ---------------------------------------------------------------------------------------


def test_a_build_that_leaves_every_page_with_a_row_completes_the_item() -> None:
    harness = Harness(page_count=6)
    assert harness.run() == Completed()
    assert harness.stored == [1, 2, 3, 4, 5, 6]
    (call,) = harness.calls
    assert call["version_uid"] == VERSION and call["retry_failed"] is False and call["runner"] is harness.runner
    assert call["rest"] == {}, "the handler passes the builder no page subset and no private limit"


def test_pages_that_were_stored_before_count_and_a_version_with_nothing_to_build_completes() -> None:
    assert Harness(page_count=6, skipped=4).run() == Completed()
    done = Harness(page_count=6, skipped=6)
    assert done.run() == Completed() and done.stored == []


def test_a_build_that_leaves_a_page_without_a_row_is_not_complete_and_is_retried() -> None:
    harness = Harness(page_count=6)
    harness.report_pages = 5
    assert harness.run() == Failed(REASON_INCOMPLETE, retry=True)


def test_a_retry_item_passes_retry_failed_to_the_builder_and_an_ordinary_one_does_not() -> None:
    harness = Harness()
    harness.run(make_item(harness.repository, page_profile_payload(VERSION, retry_failed=True)))
    assert harness.calls[0]["retry_failed"] is True
    other = Harness()
    other.run()
    assert other.calls[0]["retry_failed"] is False


def test_a_child_that_never_started_is_the_servers_fault_and_the_attempt_is_retried() -> None:
    harness = Harness()
    harness.raises = ChildStartError("the child died before it set its limits")
    assert harness.run() == Failed(REASON_CHILD_START_FAILED, retry=True)


def test_the_same_fault_after_some_pages_were_stored_is_the_same_answer() -> None:
    harness = Harness()
    harness.raises, harness.raises_after = ChildStartError("no start"), 2
    assert harness.run() == Failed(REASON_CHILD_START_FAILED, retry=True)
    assert harness.stored == [1, 2]


def test_a_version_the_database_does_not_know_fails_without_a_retry() -> None:
    harness = Harness()
    harness.raises = DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
    assert harness.run() == Failed(REASON_VERSION_NOT_FOUND, retry=False)


@pytest.mark.parametrize("code", [ErrorCode.ANALYSIS_INPUT_INVALID, ErrorCode.STORAGE_INTEGRITY_ERROR])
def test_a_source_that_cannot_be_read_or_is_not_the_recorded_bytes_fails_with_a_retry_and_the_budget_decides(
    code: ErrorCode,
) -> None:
    harness = Harness()
    harness.raises = DomainError(code, reason="source_unreadable")
    assert harness.run() == Failed(REASON_SOURCE_UNREADABLE, retry=True)


def test_any_other_refusal_or_fault_is_not_hidden_it_reaches_the_runner() -> None:
    harness = Harness()
    harness.raises = DomainError(ErrorCode.CONFLICT, aggregate_type="X")
    with pytest.raises(DomainError):
        harness.run()
    surprise = Harness()
    surprise.raises = RuntimeError("the database went away")
    with pytest.raises(RuntimeError):
        surprise.run()


# -- between pages: the lease, the heartbeat, the cancel ----------------------------------------------------------


def test_every_page_extends_the_lease_and_proves_it_before_the_next() -> None:
    harness = Harness(page_count=6)
    harness.run()
    assert harness.work.heartbeats == 7 and harness.repository.checks == 7, "once before the build and once after each page"
    assert harness.log.count("commit") == 7


def test_a_cancel_the_heartbeat_thread_already_saw_stops_the_item_before_any_page() -> None:
    harness = Harness()
    item = make_item(harness.repository)
    item.cancelled.set()
    assert harness.run(item) == Yielded()
    assert harness.calls == [] and harness.stored == []


def test_a_lease_the_heartbeat_thread_already_saw_gone_stops_the_item_before_any_page() -> None:
    harness = Harness()
    item = make_item(harness.repository)
    item.lease_lost.set()
    assert harness.run(item) == Yielded()
    assert harness.calls == [] and harness.work.heartbeats == 0


def test_a_cancel_requested_while_a_page_was_built_stops_the_build_after_that_page_and_before_the_next() -> None:
    harness = Harness(page_count=6)
    harness.work.cancel_from = 3  # read before the build (1), after page 1 (2), after page 2 (3)
    item = make_item(harness.repository)
    assert harness.run(item) == Yielded()
    assert harness.stored == [1, 2], "the page in flight finished; nothing after it was started"
    assert item.cancelled.is_set() and not item.lease_lost.is_set()


def test_a_cancel_noticed_after_the_last_page_leaves_every_page_stored_and_the_queue_ends_the_item() -> None:
    """The check follows every page, the last included; the stored pages are the ones a later run would write."""
    harness = Harness(page_count=3)
    harness.work.cancel_from = 4  # read before the build (1) and after each of the three pages
    assert harness.run() == Yielded() and harness.stored == [1, 2, 3]
    earlier = Harness(page_count=3)
    earlier.work.cancel_from = 3
    assert earlier.run() == Yielded() and earlier.stored == [1, 2]
    never = Harness(page_count=3)
    assert never.run() == Completed(), "no cancel, no stop"


def test_a_lease_that_is_gone_when_a_page_ends_stops_the_build_and_says_so_on_the_item() -> None:
    harness = Harness(page_count=6)
    harness.repository.error_from = 3  # proved before the build (1) and after page 1 (2); gone after page 2
    item = make_item(harness.repository)
    assert harness.run(item) == Yielded()
    assert harness.stored == [1, 2]
    assert item.lease_lost.is_set() and not item.cancelled.is_set()


def test_a_token_that_is_not_the_attempts_is_a_lost_lease_too() -> None:
    harness = Harness(page_count=6)
    harness.repository.error_from = 2
    harness.repository.error = DomainError(ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="ComparisonWorkAttempt")
    assert harness.run() == Yielded() and harness.stored == [1]


def test_a_heartbeat_that_finds_no_live_lease_stops_the_build_there() -> None:
    harness = Harness(page_count=6)
    harness.work.lease_gone_from = 3
    item = make_item(harness.repository)
    assert harness.run(item) == Yielded()
    assert harness.stored == [1, 2] and item.lease_lost.is_set()
    assert harness.work.cancel_reads == 2, "no cancel is read from an attempt that no longer holds the item"


def test_a_fault_of_the_check_itself_is_not_taken_for_a_stop() -> None:
    harness = Harness()
    harness.repository.error_from = 2
    harness.repository.error = DomainError(ErrorCode.CONFLICT, aggregate_type="X")
    with pytest.raises(DomainError):
        harness.run()


def test_the_flags_the_heartbeat_thread_sets_are_the_items_own_events() -> None:
    item = make_item(FakeRepository())
    assert isinstance(item.cancelled, threading.Event) and isinstance(item.lease_lost, threading.Event)
    assert not item.cancelled.is_set() and not item.lease_lost.is_set()


# -- the two kinds of source (`CMP-C1-FIX-C` item 1) -------------------------------------------------------


def test_a_source_that_cannot_be_read_retries_but_a_manifest_that_holds_two_sources_does_not() -> None:
    """An unreadable source may be a storage outage, so the attempt budget is spent on it; a manifest that binds both source
    roles does not become one by waiting, so the item ends at once with a reason of its own."""
    from auditmanager.comparison.profile.source import REASON_AMBIGUOUS, REASON_UNREADABLE
    from auditmanager.comparison.profile_queue.handler import REASON_SOURCE_AMBIGUOUS

    unreadable = Harness()
    unreadable.raises = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason=REASON_UNREADABLE)
    assert unreadable.run() == Failed(REASON_SOURCE_UNREADABLE, retry=True)

    ambiguous = Harness()
    ambiguous.raises = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason=REASON_AMBIGUOUS)
    assert ambiguous.run() == Failed(REASON_SOURCE_AMBIGUOUS)
    assert Failed(REASON_SOURCE_AMBIGUOUS).retry is False
