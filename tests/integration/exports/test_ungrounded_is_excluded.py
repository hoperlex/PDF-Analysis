"""An ungrounded observation appears in no CSV row — P02 §5.1, adversarially.

Why this needs its own module and a hand-written row
----------------------------------------------------
The composed PC-01 chain never produces an ungrounded observation: ``B3`` drops an
unresolvable anchor before writing ``analysis.text_observations``, so ``B4``'s gate never
sees one and no ``grounded = false`` row is ever written. (That is recorded as a
composition finding in ``tests/integration/runs``.) A consequence is that the export's
inner join on ``finding`` — the thing that is supposed to exclude ungrounded rows — has
**nothing to exclude** on any real run, so a test that only ran the chain would pass
whether the join were there or not.

So this module writes the adversarial row directly: an ungrounded observation *with*
evidence rows attached. ``B4``'s publication never creates that combination, which is
exactly the point — it removes the second reason the row might be absent (having no
evidence) and leaves the join as the only thing keeping it out of the file. If the query
were loosened to a ``LEFT JOIN``, these assertions would fail; against the inner join
they hold.

The database still enforces the pairing while this row is written:
``grounded = (finding_uid IS NULL) = (ungrounded_reason IS NOT NULL)`` is a CHECK
constraint, so the row below is a legal ungrounded observation and not a malformed one.
"""

from __future__ import annotations

import csv
import io

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports import BOM, export_run_csv
from auditmanager.findings import published_finding_count
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.identity import FindingObservationId

UNGROUNDED_QUOTE = "Совершенно вымышленная цитата, которой нет в тексте."
UNGROUNDED_REASON = "quotation_absent"


def _rows(content: bytes) -> list[dict[str, str]]:
    body = content[len(BOM) :].decode("utf-8")
    parsed = list(csv.reader(io.StringIO(body, newline=""), delimiter=",", quotechar='"'))
    return [dict(zip(parsed[0], row)) for row in parsed[1:]]


def _insert_ungrounded_observation_with_evidence(
    session: Session, *, run_id: str, seeded
) -> str:
    """Write the row the composed chain cannot produce, and give it evidence."""
    observation_id = FindingObservationId.new().value
    session.execute(
        text(
            "INSERT INTO finding_observation ("
            "  finding_observation_id, run_id, finding_uid, stage_id, category, "
            "  finding_text, recommendation_text, grounded, ungrounded_reason, "
            "  analysis_profile_id, prompt_bundle_id, provider_mode"
            ") VALUES ("
            "  :oid, :run_id, NULL, 'text_analysis', 'internal_contradiction', "
            "  :finding_text, :recommendation, false, :reason, :ap, :pb, 'recorded'"
            ")"
        ),
        {
            "oid": observation_id,
            "run_id": run_id,
            "finding_text": "Наблюдение, которое не прошло проверку привязки.",
            "recommendation": "Не должно попасть в выгрузку.",
            "reason": UNGROUNDED_REASON,
            "ap": seeded.analysis_profile_id,
            "pb": seeded.prompt_bundle_id,
        },
    )
    # Evidence attached deliberately: it removes "it has no evidence rows" as an
    # alternative explanation for the row's absence from the CSV.
    session.execute(
        text(
            "INSERT INTO finding_evidence ("
            "  finding_observation_id, evidence_ordinal, page_number, quote, "
            "  char_start, char_end"
            ") VALUES (:oid, 0, 1, :quote, 0, :end)"
        ),
        {"oid": observation_id, "quote": UNGROUNDED_QUOTE, "end": len(UNGROUNDED_QUOTE)},
    )
    return observation_id


def test_an_ungrounded_observation_with_evidence_reaches_no_csv_row(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("ungrounded-excluded"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    grounded_rows = _rows(export_run_csv(session, started.run_id).content)

    observation_id = _insert_ungrounded_observation_with_evidence(
        session, run_id=started.run_id, seeded=seeded
    )

    # The row really is there, and really does carry evidence: otherwise the assertions
    # below would pass by testing nothing.
    assert (
        session.execute(
            text(
                "SELECT count(*) FROM finding_observation "
                "WHERE finding_observation_id = :oid AND grounded = false "
                "AND finding_uid IS NULL AND ungrounded_reason IS NOT NULL"
            ),
            {"oid": observation_id},
        ).scalar_one()
        == 1
    )
    assert (
        session.execute(
            text(
                "SELECT count(*) FROM finding_evidence "
                "WHERE finding_observation_id = :oid"
            ),
            {"oid": observation_id},
        ).scalar_one()
        == 1
    )

    after = _rows(export_run_csv(session, started.run_id).content)

    assert observation_id not in {row["finding_observation_id"] for row in after}
    assert UNGROUNDED_QUOTE not in {row["evidence_quote"] for row in after}
    assert after == grounded_rows, (
        "an ungrounded observation changed the export; the inner join on finding is "
        "not excluding it"
    )
    # And it is counted as a finding nowhere.
    assert published_finding_count(session, started.run_id) == len(
        {row["finding_uid"] for row in after}
    )


def test_the_exported_bytes_are_unchanged_by_an_ungrounded_observation(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """The strongest form: the file is byte-identical before and after."""
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("ungrounded-bytes"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    before = export_run_csv(session, started.run_id).content

    _insert_ungrounded_observation_with_evidence(
        session, run_id=started.run_id, seeded=seeded
    )

    assert export_run_csv(session, started.run_id).content == before
