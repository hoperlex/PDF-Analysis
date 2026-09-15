"""The API listing order and the CSV row order must agree, because a docstring says they do.

``src/auditmanager/api/routers/findings.py`` states of ``_finding_sort_key``: "The same key
family the CSV sorts on (``P02_SEAMS.md`` section 6), so a page boundary and a CSV row order
cannot disagree about what 'next' means." ``P02_SEAMS.md`` §6 makes the CSV order canonical,
so this suite holds the listing to it rather than the other way round.

**The case is constructed, not hoped for.** Both identifiers are ULIDs allocated
independently, so two findings published in the same millisecond disagree about their
relative order roughly half the time. `W2-QA` measured 31 of 416 real runs diverging — which
means a test that drove a run and compared would pass on most runs while the defect stood.
So the run is real and one extra finding is inserted into it with identities chosen to make
the two orders disagree by construction: a ``finding_uid`` that sorts first and a
``finding_observation_id`` that sorts last. Ordered by the observation id alone that row is
last; ordered by the CSV's key family it is first.

Direct inserts are the only way to control ULIDs, and controlling them is the whole point.
Everything else in the fixture is a real published run.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports import export_rows
from auditmanager.findings import published_findings
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.identity import IdempotencyKey

#: Sorts before every real ``fnd_`` ULID: ``0`` is the lowest Crockford base32 digit.
FIRST_UID = "fnd_" + "0" * 26
#: Sorts after every real ``fobs_`` ULID: ``Z`` is the highest.
LAST_OBSERVATION = "fobs_" + "Z" * 26


def _published_run(session: Session, seeded, blob_store, adapter, provider_config):
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w3-order-{uuid.uuid4()}"),
    )
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
    )
    return str(started.run_id)


def _insert_divergent_finding(session: Session, run_id: str, seeded) -> None:
    """Add one more published finding whose two identifiers sort in opposite directions."""
    existing = session.execute(
        text(
            "SELECT o.finding_observation_id, o.analysis_profile_id, o.prompt_bundle_id, "
            "       o.provider_mode, o.stage_id, o.category "
            "FROM finding_observation o WHERE o.run_id = :r AND o.grounded ORDER BY 1"
        ),
        {"r": run_id},
    ).mappings().all()
    assert existing, "the run published nothing; there is no order to disagree about"
    template = existing[-1]

    session.execute(
        text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, "
            "                     allocated_by_run_id, category) "
            "VALUES (:uid, :project, :version, :run, :category)"
        ),
        {
            "uid": FIRST_UID,
            "project": seeded.project_uid,
            "version": seeded.version_uid,
            "run": run_id,
            "category": template["category"],
        },
    )
    session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, "
            "    stage_id, category, finding_text, recommendation_text, grounded, "
            "    analysis_profile_id, prompt_bundle_id, provider_mode) "
            "VALUES (:oid, :run, :uid, :stage, :category, :ftext, :rtext, TRUE, "
            "        :profile, :bundle, :mode)"
        ),
        {
            "oid": LAST_OBSERVATION,
            "run": run_id,
            "uid": FIRST_UID,
            "stage": template["stage_id"],
            "category": template["category"],
            "ftext": "W3 order probe",
            "rtext": "W3 order probe",
            "profile": template["analysis_profile_id"],
            "bundle": template["prompt_bundle_id"],
            "mode": template["provider_mode"],
        },
    )
    session.execute(
        text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
            "    page_number, quote, char_start, char_end) "
            "VALUES (:oid, 1, 1, :quote, 0, 5)"
        ),
        {"oid": LAST_OBSERVATION, "quote": "проба"},
    )
    session.flush()


@pytest.fixture()
def divergent_run(session, seeded, blob_store, recorded_adapter, provider_config) -> str:
    run_id = _published_run(session, seeded, blob_store, recorded_adapter, provider_config)
    _insert_divergent_finding(session, run_id, seeded)
    return run_id


def _first_seen(values):
    seen, ordered = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def test_the_case_really_does_discriminate(divergent_run, session):
    """Without this, the comparison below could pass on data where no order could differ."""
    by_observation = [
        row[0]
        for row in session.execute(
            text(
                "SELECT finding_observation_id FROM finding_observation "
                "WHERE run_id = :r AND grounded ORDER BY finding_observation_id"
            ),
            {"r": divergent_run},
        )
    ]
    by_csv_key = [
        row[0]
        for row in session.execute(
            text(
                "SELECT o.finding_observation_id FROM finding_observation o "
                "JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :r AND o.grounded "
                'ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C"'
            ),
            {"r": divergent_run},
        )
    ]
    assert len(by_observation) >= 2
    assert by_observation != by_csv_key, (
        "the two key families agree on this data, so the comparison below would prove "
        "nothing about which one the listing follows"
    )


def test_the_listing_follows_the_same_order_as_the_export(divergent_run, session):
    """The property the ``_finding_sort_key`` docstring asserts."""
    listing = [str(row.finding_observation_id) for row in published_findings(session, divergent_run)]
    export = _first_seen(str(row.finding_observation_id) for row in export_rows(session, divergent_run))

    assert set(listing) == set(export), "the two surfaces disagree about which rows exist"
    assert listing == export, (
        "the API listing and the CSV disagree about row order, while "
        "api/routers/findings.py says they cannot: P02_SEAMS section 6 makes the CSV "
        f"order canonical.\n  listing: {listing}\n  export:  {export}"
    )


#: A second grounded observation under one ``finding_uid``. PC-01 allocates one finding per
#: observation, so this state is not reachable through the publish path today — and nothing
#: in the schema forbids it, there is no unique constraint, and ADR-0010 makes the finding
#: the identity that survives across runs, which is exactly how a second observation would
#: arrive. The tiebreaker in the listing's ORDER BY is what keeps that case deterministic.
SECOND_OBSERVATION = "fobs_" + "0" * 26


def test_two_observations_under_one_finding_still_order_deterministically(
    divergent_run, session
):
    """Guards the secondary key. Without it the order within one finding is unspecified.

    Added because mutation M2 — dropping ``o.finding_observation_id`` from the listing's
    ORDER BY — reddened nothing: every finding in this corpus carries exactly one grounded
    observation, so the tiebreaker never decided anything and could have been deleted
    unnoticed.
    """
    session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, "
            "    stage_id, category, finding_text, recommendation_text, grounded, "
            "    analysis_profile_id, prompt_bundle_id, provider_mode) "
            "SELECT :oid, run_id, finding_uid, stage_id, category, 'W3 second observation', "
            "       recommendation_text, TRUE, analysis_profile_id, prompt_bundle_id, "
            "       provider_mode "
            "FROM finding_observation WHERE finding_observation_id = :template"
        ),
        {"oid": SECOND_OBSERVATION, "template": LAST_OBSERVATION},
    )
    session.execute(
        text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
            "    page_number, quote, char_start, char_end) "
            "VALUES (:oid, 1, 1, :quote, 0, 5)"
        ),
        {"oid": SECOND_OBSERVATION, "quote": "проба"},
    )
    session.flush()

    sharing = [
        row[0]
        for row in session.execute(
            text(
                "SELECT finding_observation_id FROM finding_observation "
                "WHERE finding_uid = :uid AND grounded ORDER BY finding_observation_id"
            ),
            {"uid": FIRST_UID},
        )
    ]
    assert sharing == [SECOND_OBSERVATION, LAST_OBSERVATION], (
        "the two observations do not share one finding, so the tiebreaker is not exercised"
    )

    listing = [str(row.finding_observation_id) for row in published_findings(session, divergent_run)]
    export = _first_seen(str(row.finding_observation_id) for row in export_rows(session, divergent_run))
    assert listing == export, (
        "with two observations under one finding the listing and the CSV disagree: the "
        f"secondary sort key is not deciding.\n  listing: {listing}\n  export:  {export}"
    )
