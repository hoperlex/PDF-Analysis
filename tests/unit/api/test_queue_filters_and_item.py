"""`UI-PARITY-QUEUE-A`: the queue's filters, the scope of its cursor and the wire body of an item.

No database. The SQL (fields per job, each filter, the period, a cursor across a filter) is asserted on real PostgreSQL in
``tests/integration/execution/test_queue_readable.py``, and the edge in ``tests/integration/api/test_queue_wire.py``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError

from auditmanager.api.app import create_documentation_app
from auditmanager.api.routers.declarations import QueueCreatedFromParam, QueueCreatedToParam
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import decode_cursor, encode_cursor
from auditmanager.bootstrap.adapters import _queue_cursor, _queue_item_model, _queue_scope
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CREATED = datetime(2026, 11, 4, 9, 30, tzinfo=timezone.utc)
COORDINATES = ("0", "5", CREATED.isoformat(), JOB)


def _refused(cursor: str, scope: tuple[str, str, str] | None, constraint: str) -> None:
    with pytest.raises(DomainError) as error:
        _queue_cursor(cursor, scope)
    assert error.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(error.value.detail_fields) == {"field": "cursor", "constraint": constraint}


# ---------------------------------------------------------------------------- the scope a cursor carries


def test_no_filter_is_no_scope_and_a_filter_is_three_words() -> None:
    assert _queue_scope(None, None, None) is None
    assert _queue_scope("failed", None, None) == ("failed", "", "")
    assert _queue_scope(None, CREATED, None) == ("", "2026-11-04T09:30:00+00:00", "")
    assert _queue_scope("queued", CREATED, CREATED + timedelta(days=1)) == (
        "queued", "2026-11-04T09:30:00+00:00", "2026-11-05T09:30:00+00:00",
    )


def test_a_group_is_the_first_word_of_the_scope_and_a_state_never_looks_like_one() -> None:
    """`D-370`: a group rides the state's slot as `group:<name>`, so the cursor format is the one it always was."""
    assert _queue_scope(None, None, None, "errors") == ("group:errors", "", "")
    assert _queue_scope(None, CREATED, None, "active") == ("group:active", "2026-11-04T09:30:00+00:00", "")
    # Another group, a state of that group, and no group are each another list.
    assert len({_queue_scope(None, None, None, name) for name in ("active", "completed", "errors")}) == 3
    assert _queue_scope(None, None, None, "errors") != _queue_scope("failed", None, None)
    assert _queue_scope(None, None, None, "errors") != _queue_scope(None, None, None)
    assert all(not state.startswith("group:") for state in ("queued", "leased", "running", "retry_wait", "succeeded", "failed", "cancelled", "dead_letter"))


def test_a_group_cursor_is_read_only_under_its_own_group() -> None:
    scope = _queue_scope(None, None, None, "errors")
    assert scope is not None
    cursor = encode_cursor(("q2", *scope, *COORDINATES))
    position = _queue_cursor(cursor, scope)
    assert position is not None and position.job_id == JOB
    for other in (_queue_scope(None, None, None, "active"), _queue_scope("failed", None, None), _queue_scope(None, CREATED, None, "errors"), None):
        _refused(cursor, other, "scope")


def test_one_instant_sent_with_two_offsets_is_one_scope() -> None:
    plus_five = datetime(2026, 11, 4, 14, 30, tzinfo=timezone(timedelta(hours=5)))
    assert plus_five == CREATED
    assert _queue_scope(None, plus_five, None) == _queue_scope(None, CREATED, None)


# ---------------------------------------------------------------------------- the cursor under its filters


def test_an_unfiltered_cursor_keeps_the_format_it_always_had() -> None:
    cursor = encode_cursor(("q1", *COORDINATES))
    position = _queue_cursor(cursor, None)
    assert position is not None and (position.rank, position.priority, position.job_id) == (0, 5, JOB)
    assert position.created_at == CREATED


def test_a_filtered_cursor_is_read_only_under_the_filters_it_was_issued_under() -> None:
    scope = _queue_scope("failed", CREATED, None)
    assert scope is not None
    cursor = encode_cursor(("q2", *scope, *COORDINATES))
    position = _queue_cursor(cursor, scope)
    assert position is not None and position.job_id == JOB
    # Another state, another period, a period dropped, the filter dropped altogether: each is another list.
    for other in (
        _queue_scope("running", CREATED, None),
        _queue_scope("failed", CREATED + timedelta(seconds=1), None),
        _queue_scope("failed", CREATED, CREATED + timedelta(days=1)),
        _queue_scope("failed", None, None),
        None,
    ):
        _refused(cursor, other, "scope")


def test_a_cursor_of_the_unfiltered_list_is_refused_under_a_filter() -> None:
    _refused(encode_cursor(("q1", *COORDINATES)), _queue_scope("queued", None, None), "scope")


def test_a_malformed_cursor_is_a_format_refusal_not_a_scope_one() -> None:
    scope = _queue_scope("failed", None, None)
    assert scope is not None
    for cursor in (
        encode_cursor(("q1", *COORDINATES[:3])),                       # a coordinate short
        encode_cursor(("q2", *scope, *COORDINATES[:3])),               # a coordinate short, filtered
        encode_cursor(("q3", *scope, *COORDINATES)),                   # a tag nobody issues
        encode_cursor((JOB,)),                                         # an event cursor
        encode_cursor(("q2", *scope, "9", "5", CREATED.isoformat(), JOB)),   # rank outside the five
        encode_cursor(("q2", *scope, "0", "5", "not-a-time", JOB)),
        encode_cursor(("q2", *scope, "0", "5", CREATED.isoformat(), "not-a-job")),
    ):
        _refused(cursor, scope, "format")


def test_the_cursor_the_adapter_issues_is_the_one_it_reads() -> None:
    """The adapter builds ``("q2", *scope, rank, priority, created_at, job_id)``; the reader takes it back."""
    scope = _queue_scope("running", None, CREATED)
    assert scope is not None
    issued = encode_cursor(("q2", *scope, "2", "0", CREATED.astimezone(timezone.utc).isoformat(), JOB))
    assert decode_cursor(issued)[:4] == ("q2", "running", "", CREATED.isoformat())
    assert _queue_cursor(issued, scope) is not None


# ---------------------------------------------------------------------------- the item on the wire


def _row(**overrides: object) -> SimpleNamespace:
    fields: dict[str, object] = dict(
        job_id=JOB, run_id=RUN, state="queued", priority=3, created_at=CREATED, available_at=CREATED,
        project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", project_name="Школа",
        document_uid="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV", document_name="АР-1",
        version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_ordinal=2,
        started_at=None, finished_at=None, error_code=None, interrupted_reason=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _wire(row: SimpleNamespace, facts: dict | None = None) -> dict:
    return json.loads(json.dumps(_queue_item_model(row, facts or {}).model_dump(mode="json", exclude_unset=True)))


def test_a_job_without_a_start_an_end_or_an_error_omits_them_and_the_binding_members_too() -> None:
    body = _wire(_row())
    assert body["project_name"] == "Школа" and body["document_name"] == "АР-1" and body["version_ordinal"] == 2
    assert body["project_uid"].startswith("prj_") and body["document_uid"].startswith("doc_")
    assert body["version_uid"].startswith("ver_")
    for absent in ("started_at", "finished_at", "error_code", "interrupted_reason", "binding_state", "wait_reason"):
        assert absent not in body, f"{absent} is absent, never sent as null"
    assert None not in body.values()


def test_a_failed_job_carries_its_start_its_end_and_the_runs_reason() -> None:
    started, finished = CREATED + timedelta(minutes=1), CREATED + timedelta(minutes=9)
    body = _wire(_row(
        state="failed", started_at=started, finished_at=finished, error_code="analysis_failed",
        interrupted_reason="executor_process_ended_before_terminal",
    ))
    assert body["started_at"] == "2026-11-04T09:31:00Z" and body["finished_at"] == "2026-11-04T09:39:00Z"
    assert body["error_code"] == "analysis_failed"
    assert body["interrupted_reason"] == "executor_process_ended_before_terminal"


def test_the_binding_facts_of_a_group_run_still_ride_the_item() -> None:
    body = _wire(_row(), {RUN: {"binding_state": "pending", "wait_reason": "runner_offline"}})
    assert (body["binding_state"], body["wait_reason"]) == ("pending", "runner_offline")


def test_a_reason_outside_the_catalogue_is_refused_rather_than_shown() -> None:
    with pytest.raises(ValueError):
        _queue_item_model(_row(error_code="not_a_catalogue_code"), {})


# ---------------------------------------------------------------------------- the period parameters


@pytest.mark.parametrize("annotation", [QueueCreatedFromParam, QueueCreatedToParam])
def test_a_period_bound_is_an_rfc_3339_instant_with_an_offset_and_nothing_else(annotation) -> None:
    adapter = TypeAdapter(annotation)
    for good, expected in (
        ("2026-11-04T10:00:00Z", datetime(2026, 11, 4, 10, tzinfo=timezone.utc)),
        ("2026-11-04T10:00:00.250000Z", datetime(2026, 11, 4, 10, 0, 0, 250000, tzinfo=timezone.utc)),
        ("2026-11-04T15:00:00+05:00", datetime(2026, 11, 4, 10, tzinfo=timezone.utc)),
    ):
        assert adapter.validate_python(good) == expected, good
    assert adapter.validate_python("") is None and adapter.validate_python(None) is None, "the absent parameter"
    # A number is a Unix time to pydantic, which would turn a typo into a filter that selects another era.
    for bad in ("1", "20261104", "1730714400", "2026-11-04", "2026-11-04T10:00:00", "2026-11-04T10:00:00 05:00",
                "2026-11-04 10:00:00Z", "yesterday", "2026-13-40T10:00:00Z"):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)


# ---------------------------------------------------------------------------- the declared surface


def _operation() -> dict:
    document = create_documentation_app().openapi()
    return document["paths"]["/execution/queue"]["get"]


def _declared(operation: dict) -> dict[str, dict]:
    return {p["name"]: p for p in operation["parameters"] if p.get("in") == "query"}


def test_the_operation_declares_the_optional_filters() -> None:
    declared = _declared(_operation())
    # `D-370` (contract 1.43.0) adds `state_group` beside `state` and the period.
    assert set(declared) == {"cursor", "limit", "state", "state_group", "created_from", "created_to"}
    for name in ("state", "state_group", "created_from", "created_to"):
        assert declared[name].get("required", False) is False, name
    assert declared["state_group"]["schema"]["enum"] == ["active", "completed", "errors"]
    for name in ("created_from", "created_to"):
        schema = declared[name]["schema"]
        assert (schema["type"], schema["format"]) == ("string", "date-time"), name


def test_the_state_filter_is_the_job_state_machine_of_the_frozen_catalogue() -> None:
    machine = json.loads((ROOT / "contracts/domain/v1/state-machines.json").read_text())["machines"]["job"]
    states = set(machine["transitions"]) | {s for targets in machine["transitions"].values() for s in targets}
    assert states == set(_declared(_operation())["state"]["schema"]["enum"])


def test_the_item_schema_requires_the_work_it_names_and_leaves_the_rest_optional() -> None:
    schema = create_documentation_app().openapi()["components"]["schemas"]["ExecutionQueueItem"]
    assert set(schema["required"]) == {
        "job_id", "run_id", "state", "priority", "created_at", "available_at",
        "project_uid", "project_name", "document_uid", "document_name", "version_uid", "version_ordinal",
    }
    optional = set(schema["properties"]) - set(schema["required"])
    # Contract 1.21.0 adds who started the run (`started_by_label`, `R-151v`), 1.26.0 a running job's
    # `estimated_finish_at` (`R-151u`); both absent when unknown, never invented. 1.28.0 adds a queued job's
    # `queue_position` and the `attempt_count` (`UI-PARITY-P0M`), the latter always sent.
    assert optional == {
        "started_at", "finished_at", "error_code", "interrupted_reason", "binding_state", "wait_reason",
        "started_by_label", "estimated_finish_at", "queue_position", "attempt_count",
    }
    assert schema["properties"]["error_code"] == {"$ref": "#/components/schemas/ErrorCode"}, "no nullable form"
    assert models.ExecutionQueueItem.model_fields["version_ordinal"].is_required()
