"""What ``enqueue_version_page_profiles`` hands to the queue (`CMP-PROFILE-QUEUE-01`). Container-free.

The two collaborators (the document repository that proves the version, the queue that stores the item) are
replaced by recorders, so each rule is shown at the call that carries it: the module, the kind, the payload, the
dedupe key per version and per retry, and the refusals that happen before anything is written. The rows themselves
are read back from PostgreSQL in ``tests/integration/comparison/profile_queue``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.profile_queue import enqueue as enqueue_module
from auditmanager.comparison.profile_queue.enqueue import enqueue_version_page_profiles, page_profile_dedupe_key
from auditmanager.comparison.public import PAGE_PROFILE_WORK_KIND, Enqueued
from auditmanager.shared.errors import DomainError, ErrorCode

PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PROJECT = "prj_01BX5ZZKBKACTAV9WEVGEMMVRZ"
VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_VERSION = "ver_01BX5ZZKBKACTAV9WEVGEMMVRZ"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class Recorder:
    def __init__(self) -> None:
        self.lookups: list[str] = []
        self.enqueued: list[dict[str, Any]] = []
        self.owner = PROJECT
        self.created = True


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    seen = Recorder()

    class Documents:
        def get_version(self, session: Any, version: Any) -> Any:
            seen.lookups.append(str(version))
            if str(version) == "ver_01ZZZZZZZZZZZZZZZZZZZZZZZZ":
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")
            return SimpleNamespace(project_uid=seen.owner)

    class Queue:
        def enqueue(self, session: Any, **options: Any) -> Enqueued:
            seen.enqueued.append(options)
            return Enqueued(work_id="cq_01ARZ3NDEKTSV4RRFFQ69G5FAV", created=seen.created)

    monkeypatch.setattr(enqueue_module, "DocumentRepository", Documents)
    monkeypatch.setattr(enqueue_module, "ComparisonWorkRepository", Queue)
    return seen


def call(**override: Any) -> Enqueued:
    options: dict[str, Any] = {
        "project_uid": PROJECT, "version_uid": VERSION, "created_by_user_uid": USER,
    }
    options.update(override)
    return enqueue_version_page_profiles(object(), **options)  # type: ignore[arg-type]


def test_an_item_is_a_versions_module_page_profile_item_with_the_version_as_its_whole_payload(recorder: Recorder) -> None:
    assert call() == Enqueued(work_id="cq_01ARZ3NDEKTSV4RRFFQ69G5FAV", created=True)
    (options,) = recorder.enqueued
    assert options["module"] == "versions"
    assert options["kind"] == PAGE_PROFILE_WORK_KIND == "page_profile"
    assert options["project_uid"] == PROJECT and options["created_by_user_uid"] == USER
    assert options["payload"] == {"version_uid": VERSION}
    assert options["dedupe_key"] == f"page_profile:{VERSION}"
    assert recorder.lookups == [VERSION], "the version is proved before anything is written"


def test_a_retry_item_says_so_in_its_payload_and_has_a_key_of_its_own(recorder: Recorder) -> None:
    call(retry_failed=True)
    (options,) = recorder.enqueued
    assert options["payload"] == {"version_uid": VERSION, "retry_failed": True}
    assert options["dedupe_key"] == f"page_profile:{VERSION}:retry_failed"
    assert options["dedupe_key"] != page_profile_dedupe_key(VERSION)


def test_the_dedupe_key_is_one_per_version_and_one_per_retry_and_fits_the_column() -> None:
    plain, retry = page_profile_dedupe_key(VERSION), page_profile_dedupe_key(VERSION, retry_failed=True)
    other = page_profile_dedupe_key(OTHER_VERSION)
    assert len({plain, retry, other, page_profile_dedupe_key(OTHER_VERSION, retry_failed=True)}) == 4
    assert page_profile_dedupe_key(VERSION) == plain, "the same version always has the same key"
    assert max(len(plain), len(retry)) <= 256


def test_a_live_item_that_is_returned_is_not_a_second_one(recorder: Recorder) -> None:
    recorder.created = False
    assert call().created is False


def test_a_version_of_another_project_is_not_found_and_nothing_is_written(recorder: Recorder) -> None:
    recorder.owner = OTHER_PROJECT
    with pytest.raises(DomainError) as raised:
        call()
    assert raised.value.code is ErrorCode.NOT_FOUND and recorder.enqueued == []


def test_an_unknown_version_is_not_found_and_nothing_is_written(recorder: Recorder) -> None:
    with pytest.raises(DomainError) as raised:
        call(version_uid="ver_01ZZZZZZZZZZZZZZZZZZZZZZZZ")
    assert raised.value.code is ErrorCode.NOT_FOUND and recorder.enqueued == []


@pytest.mark.parametrize("bad", ["", "ver_", "version", "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV", VERSION + " ", "../etc/passwd"])
def test_a_malformed_version_identity_is_a_validation_failure_before_any_lookup(recorder: Recorder, bad: str) -> None:
    with pytest.raises(DomainError) as raised:
        call(version_uid=bad)
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert recorder.lookups == [] and recorder.enqueued == []
