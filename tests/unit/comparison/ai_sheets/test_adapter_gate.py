"""The module-flag refusal of ``ComparisonAiSheetAdapter`` (`CMP-VC-AISHEET-01`; ADR-0025 decision 23, ``A-12``).

While the versions module is off, every one of the fifteen methods refuses with ``503 comparison_modules`` as its **first statement**:
the service behind it is never reached, so nothing is read, nothing is written and no model is called. With the module on, each one
reaches the service. The adapter is built with a service that fails on any touch, so a method that reads before it checks is caught.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.bootstrap.adapters import ComparisonAiSheetAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

JOB = "cai_" + "0" * 25 + "1"
PAIR = "ctp_" + "0" * 25 + "1"
SERIES = "cser_" + "0" * 24 + "1"
TRANSITION = "ctn_" + "0" * 25 + "1"


class Touched(Exception):
    pass


class TrippingService:
    """Fails with :class:`Touched` on any attribute access: a refusal must come before the service is looked at."""

    def __getattr__(self, name: str) -> Any:
        raise Touched(name)


class Sessions:
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise Touched("a session was opened")


def calls(adapter: ComparisonAiSheetAdapter) -> dict[str, Any]:
    from auditmanager.api.schemas import models

    consent = models.ComparisonAiConsent(estimate_digest="a" * 64, confirmed=True)
    key = {"user_uid": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV", "idempotency_key": "k"}
    return {
        "estimate_series_changes": lambda: adapter.estimate_series_changes(series_id=SERIES, only_failed=False),
        "get_series_changes": lambda: adapter.get_series_changes(series_id=SERIES),
        "start_series_changes": lambda: adapter.start_series_changes(series_id=SERIES, consent=consent, restart=False, **key),
        "pause_changes_job": lambda: adapter.pause_changes_job(job_id=JOB, **key),
        "resume_changes_job": lambda: adapter.resume_changes_job(job_id=JOB, consent=None, **key),
        "cancel_changes_job": lambda: adapter.cancel_changes_job(job_id=JOB, **key),
        "finish_changes_job": lambda: adapter.finish_changes_job(job_id=JOB, **key),
        "dequeue_changes_job": lambda: adapter.dequeue_changes_job(job_id=JOB, **key),
        "retry_changes_job": lambda: adapter.retry_changes_job(job_id=JOB, consent=consent, **key),
        "get_sheet_description": lambda: adapter.get_sheet_description(sheet_pair_id=PAIR),
        "estimate_sheet_description": lambda: adapter.estimate_sheet_description(sheet_pair_id=PAIR),
        "start_sheet_description": lambda: adapter.start_sheet_description(sheet_pair_id=PAIR, consent=consent, **key),
        "list_sheet_description_history": lambda: adapter.list_sheet_description_history(sheet_pair_id=PAIR, cursor=None, limit=5),
        "read_sheet_description_md": lambda: adapter.read_sheet_description_md(sheet_pair_id=PAIR),
        "list_review_sheets": lambda: adapter.list_review_sheets(transition_id=TRANSITION, cursor=None, limit=5),
    }


def test_the_adapter_has_exactly_the_fifteen_methods_of_the_port() -> None:
    from auditmanager.api.routers.ports import ComparisonAiSheetPort

    port = {n for n in vars(ComparisonAiSheetPort) if not n.startswith("_")}
    adapter = ComparisonAiSheetAdapter(Sessions(), service=TrippingService(), comparison_modules="none")  # type: ignore[arg-type]
    assert port == set(calls(adapter)) and len(port) == 15


def test_every_method_refuses_naming_the_module_before_it_touches_anything_while_the_versions_module_is_off() -> None:
    adapter = ComparisonAiSheetAdapter(Sessions(), service=TrippingService(), comparison_modules="none")  # type: ignore[arg-type]
    for name, call in calls(adapter).items():
        with pytest.raises(DomainError) as refused:
            call()
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE, name
        assert refused.value.detail_fields["dependency"] == "comparison_modules", name


def test_the_stages_module_alone_does_not_turn_the_versions_module_on() -> None:
    adapter = ComparisonAiSheetAdapter(Sessions(), service=TrippingService(), comparison_modules="none")  # type: ignore[arg-type]
    assert all(isinstance(self_check(call), DomainError) for call in calls(adapter).values())


def self_check(call: Any) -> Exception:
    try:
        call()
    except Exception as error:  # noqa: BLE001
        return error
    raise AssertionError("no refusal")


def test_with_the_module_on_each_method_goes_on_to_the_service() -> None:
    adapter = ComparisonAiSheetAdapter(Sessions(), service=TrippingService(), comparison_modules="versions")  # type: ignore[arg-type]
    for name, call in calls(adapter).items():
        with pytest.raises(Touched):
            call()
