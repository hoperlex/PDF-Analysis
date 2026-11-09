"""`UI-PARITY-AUDIT-STATE` (contract 1.40.0): the wire bodies of the three additive properties, and the frozen shapes.

`DocumentAudit.active_run` (`UI-A-47`), `RunStatus.estimated_finish_at` (`UI-A-65` / `UI-B-45`) and
`OptimisationProposal.saving_percent` (`UI-B-07`). Pure functions and the frozen document -- no database. What the SQL
reads is asserted on real PostgreSQL in ``tests/integration/dashboard/test_document_active_run.py`` and
``tests/integration/api/test_run_estimated_finish.py``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.schemas.documents import DocumentActiveRunView, DocumentAuditView, document_audit_body
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.optimisation.proposals.generator import saving_percent_for

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "api" / "v1" / "openapi.json"
_AT = datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)
_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _schemas() -> dict[str, dict]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"]


def _audit(**overrides: object) -> DocumentAuditView:
    fields: dict[str, object] = dict(
        state="not_run", partial=False, result_run_id=None, finding_count=0, undecided_finding_count=0,
    )
    fields.update(overrides)
    return DocumentAuditView(**fields)  # type: ignore[arg-type]


def _status(**overrides: object) -> RunStatusView:
    fields: dict[str, object] = dict(
        run_id=f"run_{_ULID}", project_uid=f"prj_{_ULID}", version_uid=f"ver_{_ULID}", state="running",
        provider_mode="live", created_at=_AT,
    )
    fields.update(overrides)
    return RunStatusView(**fields)  # type: ignore[arg-type]


# --- DocumentAudit.active_run -------------------------------------------------------------------------------------


def test_an_active_run_is_rendered_only_when_there_is_one_and_leaves_the_four_words_alone() -> None:
    quiet = document_audit_body(_audit())
    assert "active_run" not in quiet, "an absent property is omitted, never sent as null"
    running = document_audit_body(
        _audit(active_run=DocumentActiveRunView(run_id=f"run_{_ULID}", state="running"))
    )
    assert running["active_run"] == {"run_id": f"run_{_ULID}", "state": "running"}
    assert {key: running[key] for key in quiet} == quiet, "the state, the flag and the counts are what they were"
    rerun = document_audit_body(_audit(
        state="checked", result_run_id=f"run_{_ULID}", finding_count=2,
        active_run=DocumentActiveRunView(run_id=f"run_{_ULID[:-1]}B", state="queued"),
    ))
    assert rerun["state"] == "checked" and rerun["active_run"]["state"] == "queued"


def test_the_frozen_shape_of_the_active_run_is_closed_optional_and_three_words() -> None:
    schemas = _schemas()
    shape = schemas["DocumentActiveRun"]
    assert shape["required"] == ["run_id", "state"] and shape["additionalProperties"] is False
    assert shape["properties"]["state"]["enum"] == ["queued", "running", "validating"]
    audit = schemas["DocumentAudit"]
    assert audit["properties"]["active_run"] == {"$ref": "#/components/schemas/DocumentActiveRun"}
    assert "active_run" not in audit["required"], "optional: absent when no run is in flight"
    assert audit["properties"]["state"]["enum"] == ["not_run", "clean", "awaiting_decision", "checked"], (
        "the four words are not widened"
    )
    generated = models.DocumentAudit.model_json_schema()
    assert "active_run" in generated["properties"] and "active_run" not in generated.get("required", [])


# --- RunStatus.estimated_finish_at ---------------------------------------------------------------------------------


def test_the_estimate_is_rendered_as_a_utc_instant_and_omitted_without_one() -> None:
    assert "estimated_finish_at" not in run_status_body(_status())
    assert run_status_body(_status(estimated_finish_at=_AT))["estimated_finish_at"] == "2026-11-08T09:30:00Z"


def test_the_frozen_shape_of_the_estimate_is_the_queues_own() -> None:
    schemas = _schemas()
    status = schemas["RunStatus"]
    queue = schemas["ExecutionQueueItem"]
    assert "estimated_finish_at" not in status["required"]
    assert {key: value for key, value in status["properties"]["estimated_finish_at"].items() if key != "description"} == {
        key: value for key, value in queue["properties"]["estimated_finish_at"].items() if key != "description"
    }, "one estimate, one type, on the queue item and on the run status"
    assert "estimated_finish_at" in models.RunStatus.model_json_schema()["properties"]


# --- OptimisationProposal.saving_percent ---------------------------------------------------------------------------


def _pattern() -> re.Pattern[str]:
    return re.compile(_schemas()["OptimisationProposal"]["properties"]["saving_percent"]["pattern"])


@pytest.mark.parametrize("text", ["0", "0.5", "0.05", "1", "9.9", "10", "12.34", "99.99", "100"])
def test_the_percent_pattern_admits_a_plain_percent_up_to_one_hundred(text: str) -> None:
    assert _pattern().fullmatch(text), text


@pytest.mark.parametrize("text", ["", "00", "01", "1.0", "12.30", "12.345", "100.5", "101", "-1", "1e1", " 1", "1.", ".5", "NaN"])
def test_the_percent_pattern_refuses_everything_else(text: str) -> None:
    assert not _pattern().fullmatch(text), text


def test_everything_the_server_computes_matches_the_frozen_pattern() -> None:
    pattern = _pattern()
    seen: set[str] = set()
    for current in ("1", "3", "7", "8", "25000", "0.00001", "99999999999999"):
        for proposed in ("0", "0.00001", "1", "2", "7.99", "24999.999999", "99999999999998"):
            if Decimal(proposed) > Decimal(current):
                continue
            value = saving_percent_for(current_unit_price=Decimal(current), proposed_unit_price=Decimal(proposed))
            assert value is not None
            text = format(value.normalize(), "f")  # the adapter's own rendering (`_plain_decimal`)
            assert pattern.fullmatch(text), (current, proposed, text)
            seen.add(text)
    assert {"0", "100", "33.33", "66.67"} <= seen, "the table reaches both ends and the repeating fractions"


def test_the_frozen_shape_of_the_percent_is_optional_beside_the_required_nullable_saving() -> None:
    proposal = _schemas()["OptimisationProposal"]
    assert "saving_percent" not in proposal["required"] and "saving" in proposal["required"]
    assert "saving_percent" in models.OptimisationProposal.model_json_schema()["properties"]


# --- DocumentAudit.optimisation_* (`D-361`, contract 1.43.0) -------------------------------------------------------


def test_the_optimisation_counts_are_rendered_together_or_not_at_all_and_leave_the_four_words_alone() -> None:
    quiet = document_audit_body(_audit())
    assert "optimisation_proposal_count" not in quiet and "optimisation_undecided_count" not in quiet, (
        "no pass is no figure: omitted, never sent as null and never a zero"
    )
    read = document_audit_body(_audit(optimisation_proposal_count=7, optimisation_undecided_count=3))
    assert (read["optimisation_proposal_count"], read["optimisation_undecided_count"]) == (7, 3)
    assert {key: read[key] for key in quiet} == quiet, "the state, the flag and the counts are what they were"
    # A pass with no proposal is a figure: zero is said, because a pass was read.
    empty = document_audit_body(_audit(optimisation_proposal_count=0, optimisation_undecided_count=0))
    assert (empty["optimisation_proposal_count"], empty["optimisation_undecided_count"]) == (0, 0)


def test_the_frozen_shape_of_the_optimisation_counts_is_two_optional_counts() -> None:
    audit = _schemas()["DocumentAudit"]
    for name in ("optimisation_proposal_count", "optimisation_undecided_count"):
        assert audit["properties"][name]["type"] == "integer" and audit["properties"][name]["minimum"] == 0
        assert name not in audit["required"], "optional: absent when no pass was started over the version"
    generated = models.DocumentAudit.model_json_schema()
    assert {"optimisation_proposal_count", "optimisation_undecided_count"} <= set(generated["properties"])
    assert not {"optimisation_proposal_count", "optimisation_undecided_count"} & set(generated.get("required", []))
    assert audit["properties"]["state"]["enum"] == ["not_run", "clean", "awaiting_decision", "checked"]
