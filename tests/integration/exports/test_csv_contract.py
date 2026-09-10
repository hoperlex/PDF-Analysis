"""The frozen seventeen-column CSV, asserted against a real run's real rows.

Every assertion here is about bytes or about resolution:

* the **bytes** — BOM, CRLF, delimiter, quoting, empty cells — because ``OD-11`` makes
  them the contract, and because the reader opens this in Excel;
* the **resolution** — every row's identifiers must name the exact project, version,
  run, finding and observation the chain wrote, not merely well-formed strings.

The rows come from executing the chain, never from hand-built fixtures. A CSV checked
against invented rows would prove the serializer correct and prove nothing about whether
the seventeen columns are wired to the right sources — which is the half of this contract
that can actually be got wrong.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports import BOM, COLUMNS, CONTENT_TYPE, export_run_csv
from auditmanager.exports.policy import exportable_states, publishes_result
from auditmanager.findings import published_finding_count
from auditmanager.runs import RunRepository, execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode


def _start(session: Session, seeded, key):
    return start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )


def _run_and_export(session, seeded, blob_store, adapter, provider_config, key):
    started = _start(session, seeded, key)
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
    )
    return started, result, export_run_csv(session, started.run_id)


def _parse(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Decode and parse exactly as a conforming RFC 4180 reader would."""
    assert content.startswith(BOM)
    body = content[len(BOM) :].decode("utf-8")
    reader = csv.reader(io.StringIO(body, newline=""), delimiter=",", quotechar='"')
    rows = list(reader)
    header, data = rows[0], rows[1:]
    return header, [dict(zip(header, row)) for row in data]


# --- bytes -------------------------------------------------------------------


def test_the_header_is_the_frozen_column_list_in_order(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    _, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("header")
    )
    header, _ = _parse(export.content)
    assert header == list(COLUMNS)
    assert len(header) == 17


def test_the_bytes_are_utf8_with_a_bom_and_crlf_endings(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """The three encoding decisions ``OD-11`` fixes, checked on the bytes themselves."""
    _, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("bytes")
    )
    content = export.content

    assert content.startswith(BOM), "no byte-order mark: Excel will mis-decode Cyrillic"
    body = content[len(BOM) :]
    body.decode("utf-8")  # raises if the payload is not UTF-8

    assert body.endswith(b"\r\n"), "the final record is not CRLF-terminated"
    # Every LF in the payload is part of a CRLF pair: no bare LF line ending survives.
    assert body.count(b"\n") == body.count(b"\r\n")
    assert export.content_type == CONTENT_TYPE

    # The corpus is Russian; the point of the BOM is that this round-trips.
    assert "Степень огнестойкости" in body.decode("utf-8")


def test_two_exports_of_an_unchanged_run_are_byte_identical(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Proved by comparing bytes, not by assuming determinism."""
    started, _, first = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("identical")
    )
    second = export_run_csv(session, started.run_id)
    third = export_run_csv(session, started.run_id)

    assert first.content == second.content
    assert second.content == third.content
    assert len(first.content) == len(second.content) == len(third.content)


def test_an_export_creates_nothing(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """No export row, no ``export_id``, no ``exported_at`` — and no table to hold one."""
    started, _, _ = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("creates-nothing")
    )

    def snapshot() -> tuple[int, ...]:
        return tuple(
            int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
            for table in (
                "audit_run",
                "stage_result",
                "finding",
                "finding_observation",
                "finding_evidence",
                "command_record",
                "expert_decision_event",
                "model_call",
            )
        )

    before = snapshot()
    for _ in range(3):
        export_run_csv(session, started.run_id)
    assert snapshot() == before

    assert (
        session.execute(text("SELECT to_regclass('public.export')")).scalar_one_or_none()
        is None
    ), "PC-01 instantiates no export aggregate"


def test_a_null_projection_column_is_the_empty_string(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Never the literal ``null``, never ``NULL``.

    A run with no expert decisions has a projection row whose verdict fields are all
    null, so the four decision columns exercise this on every row.
    """
    _, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("nulls")
    )
    _, rows = _parse(export.content)
    assert rows

    for row in rows:
        # No decisions were recorded, so the projection is pending with null details.
        assert row["current_verdict"] == "pending"
        assert row["latest_comment"] == ""
        assert row["latest_decision_id"] == ""
        assert row["decision_recorded_at"] == ""

    text_body = export.content.decode("utf-8-sig")
    for forbidden in (",null,", ",NULL,", ",None,"):
        assert forbidden not in text_body


def test_rows_are_sorted_by_the_frozen_sort_key(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """``(finding_uid, finding_observation_id, evidence_ordinal)`` ascending."""
    started, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("sorted")
    )
    _, rows = _parse(export.content)

    ordinals = {
        (row["finding_observation_id"], row["evidence_page"], row["evidence_quote"])
        for row in rows
    }
    assert len(ordinals) == len(rows), "a row is duplicated"

    keys = [(row["finding_uid"], row["finding_observation_id"]) for row in rows]
    assert keys == sorted(keys), "rows are not in ascending identifier order"

    # And the evidence of one observation is contiguous and in stored ordinal order.
    stored = (
        session.execute(
            text(
                "SELECT o.finding_observation_id, e.evidence_ordinal, e.quote "
                "FROM finding_evidence e "
                "JOIN finding_observation o "
                "  ON o.finding_observation_id = e.finding_observation_id "
                "JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :run_id "
                'ORDER BY o.finding_observation_id COLLATE "C", e.evidence_ordinal'
            ),
            {"run_id": started.run_id},
        )
        .mappings()
        .all()
    )
    assert [row["quote"] for row in stored] == [row["evidence_quote"] for row in rows]


def test_a_finding_with_several_quotations_produces_one_row_per_quotation(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """§6 granularity: columns 1-11 and 14-17 repeat; 12 and 13 vary."""
    started, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("granularity")
    )
    _, rows = _parse(export.content)

    by_observation: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_observation.setdefault(row["finding_observation_id"], []).append(row)

    multi = [group for group in by_observation.values() if len(group) > 1]
    assert multi, (
        "no observation in this run carries more than one quotation, so the shared-column "
        "claim would be untested"
    )
    shared = [column for column in COLUMNS if column not in ("evidence_page", "evidence_quote")]
    for group in multi:
        for column in shared:
            values = {row[column] for row in group}
            assert len(values) == 1, f"{column} differs across rows of one observation"
        assert len({row["evidence_quote"] for row in group}) == len(group)


# --- resolution --------------------------------------------------------------


def test_every_row_resolves_to_the_exact_project_version_run_and_finding(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    started, result, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("resolution")
    )
    _, rows = _parse(export.content)
    assert rows

    canonical = {
        row["finding_observation_id"]: row
        for row in session.execute(
            text(
                "SELECT o.finding_observation_id, o.finding_text, o.recommendation_text, "
                "       f.finding_uid, f.project_uid, f.version_uid, f.category, "
                "       f.allocated_by_run_id "
                "FROM finding_observation o JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :run_id"
            ),
            {"run_id": started.run_id},
        )
        .mappings()
        .all()
    }

    for row in rows:
        source = canonical[row["finding_observation_id"]]
        assert row["project_uid"] == seeded.project_uid == source["project_uid"]
        assert row["document_uid"] == seeded.document_uid
        assert row["version_uid"] == seeded.version_uid == source["version_uid"]
        assert row["run_id"] == started.run_id == source["allocated_by_run_id"]
        assert row["finding_uid"] == source["finding_uid"]
        assert row["category"] == source["category"]
        assert row["finding_text"] == source["finding_text"]
        assert row["recommendation_text"] == (source["recommendation_text"] or "")
        assert row["run_state"] == result.terminal_state
        assert row["provider_mode"] == "recorded"


def test_the_export_agrees_with_the_findings_read_surface(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """Cross-check against ``B4``'s own query, so the join cannot quietly widen.

    The export contains SQL of its own because seven frozen columns are projected by no
    public query. This is the guard that keeps that SQL honest: if it ever stopped
    dropping ungrounded observations, the distinct finding count here would exceed
    ``published_finding_count`` and this reddens.
    """
    started, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("cross-check")
    )
    _, rows = _parse(export.content)

    assert len({row["finding_uid"] for row in rows}) == published_finding_count(
        session, started.run_id
    )


def test_no_cell_contains_a_bucket_object_key_path_or_credential(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """None of those is an identity (P02 §2.2), and none may reach a reviewer's file."""
    import os

    _, _, export = _run_and_export(
        session, seeded, blob_store, recorded_adapter, provider_config, new_key("no-secrets")
    )
    body = export.content.decode("utf-8-sig")

    forbidden = [
        os.environ.get("S3_BUCKET", ""),
        os.environ.get("S3_ACCESS_KEY_ID", ""),
        os.environ.get("S3_SECRET_ACCESS_KEY", ""),
        os.environ.get("S3_ENDPOINT_URL", ""),
        os.environ.get("POSTGRES_PASSWORD", ""),
        seeded.source_blob_id,
    ]
    for value in forbidden:
        if value:
            assert value not in body, f"the export leaked {value!r}"

    for marker in ("s3://", "http://", "https://", "/root/", "AKIA", "postgresql://"):
        assert marker not in body, f"the export contains {marker!r}"


# --- the OD-11 export policy -------------------------------------------------


def test_the_discriminator_is_the_contract_flag_not_a_state_list():
    """``publishes_result`` is read from the contract, and yields exactly two states."""
    assert exportable_states() == {"published", "partial"}
    assert publishes_result("published") is True
    assert publishes_result("partial") is True
    assert publishes_result("failed") is False
    assert publishes_result("cancelled") is False
    # A non-terminal state has no terminal_semantics entry at all.
    for state in ("created", "queued", "running", "validating"):
        assert publishes_result(state) is False


def test_a_partial_run_exports_with_its_degraded_state_visible(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """A degraded run is exported, not refused and not silently emptied."""
    started, result, export = _run_and_export(
        session,
        seeded,
        blob_store,
        variant_adapter("truncated"),
        provider_config,
        new_key("partial-export"),
    )
    assert result.terminal_state == "partial"

    _, rows = _parse(export.content)
    assert rows, "a partial run exported an empty file instead of its findings"
    assert {row["run_state"] for row in rows} == {"partial"}


@pytest.mark.parametrize("state", ["created", "queued", "running", "validating"])
def test_a_non_terminal_run_is_refused(
    session: Session, seeded, new_key, state, helpers
):
    """Refused with the typed code, never exported empty."""
    started = _start(session, seeded, new_key(f"non-terminal-{state}"))
    runs = RunRepository()
    path = {
        "created": (),
        "queued": ("queued",),
        "running": ("queued", "running"),
        "validating": ("queued", "running", "validating"),
    }[state]
    current = "created"
    for target in path:
        runs.advance(session, run_id=started.run_id, from_state=current, to_state=target)
        current = target
    assert helpers.run_state_of(session, started.run_id) == state

    with pytest.raises(DomainError) as raised:
        export_run_csv(session, started.run_id)
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_a_failed_run_is_refused(session: Session, seeded, new_key, helpers):
    """``failed`` declares ``publishes_result: false``, so there is nothing to export."""
    started = _start(session, seeded, new_key("failed-export"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    runs.terminate(
        session,
        run_id=started.run_id,
        from_state="running",
        to_state="failed",
        terminal_reason="analysis_failed",
    )
    assert helpers.run_state_of(session, started.run_id) == "failed"

    with pytest.raises(DomainError) as raised:
        export_run_csv(session, started.run_id)
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_pc01_never_emits_partial_result_not_publishable_from_the_export(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """P02 §6 says so explicitly; asserted because it is easy to reach for that code.

    A ``partial`` run is the case where the wrong code is tempting, so the refusal
    vocabulary is checked on exactly that run — and on a refused one — rather than in
    the abstract.
    """
    _, result, export = _run_and_export(
        session,
        seeded,
        blob_store,
        variant_adapter("truncated"),
        provider_config,
        new_key("no-prnp"),
    )
    assert result.terminal_state == "partial"
    assert export.content  # exported, not refused

    started = _start(session, seeded, new_key("no-prnp-refused"))
    with pytest.raises(DomainError) as raised:
        export_run_csv(session, started.run_id)
    assert raised.value.code is not ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_an_unknown_run_is_not_found(session: Session):
    with pytest.raises(DomainError) as raised:
        export_run_csv(session, "run_01M2545JSD15ETSNNV904X991J")
    assert raised.value.code is ErrorCode.NOT_FOUND
