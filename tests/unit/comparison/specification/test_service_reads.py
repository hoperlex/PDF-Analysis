"""The reads of a series do not plan its transitions; a version without a page count is one transition's diagnostic (`REVIEW-FIX-CMP-SPEC-1102`).

Code review 2026-11-02, S2-blocks-4-9-08. Planning a transition opens the page-profile archives of both of its versions and renders every
prompt; the list of a series (up to ``PAGE_MAX`` transitions) must not do that once per row, and a version whose source cannot be
established must not make the read of the transition (or of the list around it) fail. Store, reader and session are fakes that count.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.specification.repository import TransitionScope
from auditmanager.comparison.specification.service import SpecificationService
from auditmanager.comparison.specification.transition import REASON_PAGE_COUNT
from auditmanager.shared.errors import DomainError, ErrorCode

PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991D"
SERIES = "cser_unit"
VERSIONS = [f"ver_unit{n}" for n in range(1, 5)]


def factory() -> Any:
    return SimpleNamespace(commit=lambda: None, rollback=lambda: None, close=lambda: None)


class Repository:
    def __init__(self) -> None:
        self.scopes = [TransitionScope(f"ctn_unit{n}", SERIES, n, VERSIONS[n - 1], VERSIONS[n], PROJECT, DOCUMENT) for n in (1, 2, 3)]

    def series_exists(self, session: Any, series_id: str) -> bool:
        return series_id == SERIES

    def transitions_after(self, session: Any, series_id: str, *, after_no: int) -> list[TransitionScope]:
        return [scope for scope in self.scopes if scope.transition_no > after_no]

    def wholes_of_series(self, session: Any, series_id: str) -> dict[str, Any]:
        return {}

    def transition(self, session: Any, transition_id: str) -> TransitionScope | None:
        return next((scope for scope in self.scopes if scope.transition_id == transition_id), None)

    def whole(self, session: Any, transition_id: str) -> None:
        return None


class Reader:
    """Every version has one specification page by its title block; planning it is what ``version_stream`` is."""

    def __init__(self, *, source_unreadable: bool = False) -> None:
        self.streams = 0
        self.source_unreadable = source_unreadable

    def version_rows(self, version_uid: str) -> list[Any]:
        stamp = {"designation": "", "sheet_name": "Спецификация"}
        return [SimpleNamespace(is_ready=True, summary={"text_layer": True, "scan": False, "stamp": stamp}, page_number=1)]

    def version_stream(self, version_uid: str, **_: Any) -> Any:
        self.streams += 1
        if self.source_unreadable:
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message="the version binds more than one source document")
        raise AssertionError("not reached by these tests")


def service_over(reader: Reader) -> SpecificationService:
    return SpecificationService(factory, None, repository=Repository(), reader=reader)  # type: ignore[arg-type]


def test_the_list_of_a_series_plans_no_transition_without_a_row() -> None:
    reader = Reader()
    page = service_over(reader).list_specifications(series_id=SERIES, after_no=0, limit=10)
    assert reader.streams == 0, "listing opened the page profiles of the versions"
    assert [item["state"] for item in page.items] == ["not_started"] * 3
    assert all(item["method"] == "whole" and (item["sheets_a"], item["sheets_b"]) == (1, 1) for item in page.items)


def test_one_transition_is_still_read_through_the_store() -> None:
    """The single read plans (it can be ``completed`` from stored readings); the list does not. The mutation: planning in the list."""
    reader = Reader(source_unreadable=True)
    service_over(reader).get_specification(transition_id="ctn_unit1")
    assert reader.streams >= 1


def test_a_version_whose_source_cannot_be_established_is_that_transitions_incomplete_diagnostic() -> None:
    reader = Reader(source_unreadable=True)
    view = service_over(reader).get_specification(transition_id="ctn_unit2")
    assert view["state"] == "incomplete" and view["method"] == "sheet_ai" and view["reason"] == REASON_PAGE_COUNT
    assert "totals" not in view and "coverage_a" not in view
    assert re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", REASON_PAGE_COUNT)  # the contract's reason pattern and the table's CHECK
    assert service_over(Reader(source_unreadable=True)).list_changes(transition_id="ctn_unit2", kind=None, offset=0, limit=10) == ([], None)


def test_any_other_failure_of_the_read_is_not_turned_into_a_diagnostic() -> None:
    class Broken(Reader):
        def version_stream(self, version_uid: str, **_: Any) -> Any:
            raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison.page_profile")

    with pytest.raises(DomainError) as failure:
        service_over(Broken()).get_specification(transition_id="ctn_unit1")
    assert failure.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
