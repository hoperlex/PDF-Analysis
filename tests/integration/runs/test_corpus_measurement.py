"""The measured figures the gate asks for, printed with the method that produced them.

Not a pass/fail assertion about a magic number: the point is that the run state, the
finding count and the CSV row count are read off one real run against real services and
reported together, so a later reader can tell what was measured rather than what was
estimated. The assertions are relationships between the three, which is what stays true
if a recording is re-cut.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports import COLUMNS, export_run_csv
from auditmanager.findings import published_finding_count
from auditmanager.runs import execute_run, start_audit_run


def test_report_the_corpus_run_figures(
    session: Session,
    seeded,
    blob_store,
    recorded_adapter,
    provider_config,
    new_key,
    capsys,
):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("measurement"),
    )
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    findings = published_finding_count(session, started.run_id)
    diagnostics = int(
        session.execute(
            text(
                "SELECT count(*) FROM finding_observation "
                "WHERE run_id = :run_id AND finding_uid IS NULL"
            ),
            {"run_id": started.run_id},
        ).scalar_one()
    )
    export = export_run_csv(session, started.run_id)
    lines = export.content.decode("utf-8-sig").split("\r\n")
    data_rows = [line for line in lines if line][1:]

    with capsys.disabled():
        print("\n--- B5 corpus run, fixtures/synthetic/ar/ar_baseline.pdf, recorded adapter ---")
        print(f"  run state ............ {result.terminal_state}")
        print(f"  degradation set ...... {result.degradation_set or '(empty)'}")
        print(f"  stage statuses ....... {dict(result.stage_statuses)}")
        print(f"  published findings ... {findings}")
        print(f"  ungrounded diagnostics {diagnostics}")
        print(f"  CSV rows (evidence) .. {len(data_rows)}")
        print(f"  CSV bytes ............ {export.byte_size}")
        print(f"  CSV columns .......... {len(COLUMNS)}")
        print("-------------------------------------------------------------------------------")

    # The relationships, which is what a later reader can rely on.
    assert result.terminal_state in {"published", "partial"}
    assert findings > 0
    assert len(data_rows) >= findings
    assert export.byte_size > 0
