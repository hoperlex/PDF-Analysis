"""`SMALL-HARDENING-02` / `R-146ax`, end to end: ``export_run_csv`` of a real run.

``tests/unit/exports/test_csv_formula_neutralisation.py`` holds the rule on hand-built rows.
This file holds the one thing that suite cannot: that the use case the router calls
(``export_run_csv`` -> ``export_rows`` -> ``render_csv``) is the path the rule sits on, over
the rows a real recorded run wrote. The stored rows cannot be edited (``finding_evidence`` and
``finding_observation`` refuse UPDATE and DELETE), so the read the service performs is
replaced by the real read with some cells replaced -- the bytes are still produced by the real
service and the real serializer.
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace

import pytest
from sqlalchemy.orm import Session

from auditmanager.exports import export_run_csv
from auditmanager.exports import service as export_service
from auditmanager.exports.query import export_rows
from auditmanager.runs import execute_run, start_audit_run
from tests.support.v1_reference_profile import resolve_reference_profile

BOM_BYTES = b"\xef\xbb\xbf"

#: One per class of `R-146ax`: (row index, column, value). A recorded run of the reference
#: profile has five evidence rows, so two classes share the first row.
HOSTILE = (
    (0, "evidence_quote", '=HYPERLINK("http://example.invalid","x")'),
    (0, "finding_text", "+1 выход"),
    (1, "recommendation_text", "-5 м"),
    (2, "latest_comment", "@SUM(A1)"),
    (3, "evidence_quote", "\tтабуляция"),
    (4, "recommendation_text", "\rперевод"),
)


def _parse(content: bytes) -> tuple[list[str], list[list[str]]]:
    assert content[:3] == BOM_BYTES
    rows = list(csv.reader(io.StringIO(content[3:].decode("utf-8"), newline="")))
    return rows[0], rows[1:]


def _export(session, seeded, blob_store, adapter, provider_config, key):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        text_profiles=resolve_reference_profile,
    )
    return started, export_run_csv(session, started.run_id)


def test_a_runs_export_carries_the_apostrophe_on_exactly_the_cells_that_start_like_a_formula(
    session: Session,
    seeded,
    blob_store,
    recorded_adapter,
    provider_config,
    new_key,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started, clean = _export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("neutralise")
    )
    header, clean_rows = _parse(clean.content)
    stored = export_rows(session, started.run_id)
    assert len(stored) == len(clean_rows) >= 1 + max(index for index, _, _ in HOSTILE)

    # Nothing a recorded run wrote starts with a trigger, so the clean file is untouched.
    for row in clean_rows:
        for cell in row:
            assert not cell or cell[0] not in "=+-@\t\r", cell

    hostile = list(stored)
    for index, column, value in HOSTILE:
        hostile[index] = replace(hostile[index], **{column: value})
    monkeypatch.setattr(export_service, "export_rows", lambda _session, _run_id: tuple(hostile))

    changed = export_run_csv(session, started.run_id)
    _, changed_rows = _parse(changed.content)
    assert len(changed_rows) == len(clean_rows)

    expected_changes = {
        (index, header.index(column)): "'" + value for index, column, value in HOSTILE
    }
    for row_index, (before, after) in enumerate(zip(clean_rows, changed_rows)):
        for column_index, (old, new) in enumerate(zip(before, after)):
            if (row_index, column_index) in expected_changes:
                assert new == expected_changes[(row_index, column_index)]
            else:
                assert new == old, (row_index, header[column_index])
