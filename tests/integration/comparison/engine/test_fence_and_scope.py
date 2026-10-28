"""The row is written inside the transaction the queue's fence holds (ADR-0025 decision 7), and only for pages of the
project (`CMP-ENGINE-01`)."""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine import compare_sheet_pair
from auditmanager.shared.errors import DomainError, ErrorCode


def test_an_attempt_the_fence_refuses_writes_no_row(lane) -> None:
    project = lane.project()
    v1, v2 = lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)
    seen: list[str] = []

    def fence(session) -> None:
        seen.append("called")
        raise DomainError(ErrorCode.STALE_ATTEMPT)

    with pytest.raises(DomainError) as refusal:
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[2],
                           page_b_profile_id=v2.pages[2], fence=fence)
    assert refusal.value.code is ErrorCode.STALE_ATTEMPT and seen == ["called"]
    assert lane.results(project) == []
    # The pair is still comparable by the next attempt, which finds no row and writes one.
    assert compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[2],
                              page_b_profile_id=v2.pages[2]).created is True


def test_a_stop_before_the_blob_is_published_publishes_nothing(lane) -> None:
    project = lane.project()
    v1, v2 = lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)

    class Stop(Exception):
        pass

    def stop() -> None:
        raise Stop

    with pytest.raises(Stop):
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[2],
                           page_b_profile_id=v2.pages[2], before_publish=stop)
    assert lane.results(project) == []


def test_pages_that_are_not_the_projects_are_refused_before_any_work(lane) -> None:
    project, other = lane.project(), lane.project()
    v1 = lane.seed("vs1/v1.pdf", 6, project_uid=project)
    w2 = lane.seed("vs1/v2.pdf", 6, project_uid=other)
    with pytest.raises(DomainError) as refusal:
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[2],
                           page_b_profile_id=w2.pages[2])
    assert refusal.value.code is ErrorCode.NOT_FOUND and lane.results(project) == [] and lane.results(other) == []
