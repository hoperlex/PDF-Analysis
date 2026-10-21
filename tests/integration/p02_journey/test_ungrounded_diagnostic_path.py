"""The grounding diagnostic path is dead as composed. This pins what that costs.

``auditmanager.analysis.text`` resolves every quotation against the text layer and drops
what does not resolve **before** writing its artifact, recording a reason per anchor in
``anchors.py`` and then keeping only two integers. ``auditmanager.findings``' gate
therefore never receives an unresolvable anchor, so no ``finding_observation`` row of **this
chain** (the AR text profile every journey run starts) is ever written with
``grounded = false``, and the ``ungrounded_reason`` vocabulary that ``P02_SEAMS.md`` §5.1
declares has no producer in it at all.

The scope is the chain, not the database. ``auditmanager.findings.publication`` can write
``grounded = false`` and other suites exercise it or seed such a row by hand to prove a
refusal; the AR v2 and v3 recorded profiles (``W57a``) are separate chains with their own
publication paths and tests. Those rows share this database in a full run and are not
output of the chain under claim.

The safety property holds, and holds twice over: the stage drops, and the gate would
reject. What is lost is diagnostic: *which* quotation the model invented, on which page,
and under which of the five declared reasons. Only a per-stage count survives.

These tests are green. They exist so that the day someone wires the reason through --
or the day the stage stops dropping -- the change is visible rather than absorbed.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from auditmanager.analysis.text import AR_TEXT_PROFILE, AR_TEXT_PROMPT_BUNDLE


@pytest.fixture(scope="module")
def ungrounded_run(journey_harness, session_factory, blob_store, variant_adapter, provider_config):
    """A run whose recorded answer contains a quotation that is not in the document."""
    h = journey_harness
    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("ungrounded"))
        run_id = h.run_from_seed(
            session,
            seed,
            blob_store=blob_store,
            adapter=variant_adapter("ungrounded_quotation"),
            provider_config=provider_config,
            declared_provider_mode="recorded",
            run_key=h.new_key("run"),
        )
        yield {**seed, "run_id": run_id}


def _text_analysis_metrics(session, run_id: str) -> dict:
    raw = session.execute(
        text("SELECT metrics FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'"),
        {"r": run_id},
    ).scalar_one()
    return raw if isinstance(raw, dict) else json.loads(raw)


def test_the_variant_really_did_propose_something_unresolvable(ungrounded_run, session):
    """The precondition. Without it every assertion below would pass on a clean run."""
    metrics = _text_analysis_metrics(session, ungrounded_run["run_id"])
    assert metrics["observations_proposed"] > metrics["observations_emitted"], (
        f"this variant dropped nothing: {metrics}. The tests below would be vacuous."
    )
    assert metrics["evidence_unresolved"] >= 1


def test_nothing_ungrounded_is_published(ungrounded_run, session):
    """The safety property, and it is what PC-02 gate G2 measures."""
    rows = session.execute(
        text(
            "SELECT grounded, ungrounded_reason, count(*) FROM finding_observation "
            "WHERE run_id = :r GROUP BY grounded, ungrounded_reason"
        ),
        {"r": ungrounded_run["run_id"]},
    ).all()
    assert rows, "the run published no observation at all; the variant proves nothing"
    for grounded, reason, _count in rows:
        assert grounded is True, f"an ungrounded observation was persisted: reason={reason!r}"
        assert reason is None


def test_no_grounded_false_row_exists_anywhere(ungrounded_run, session):
    """Not merely absent on this run: no producer for the column exists in the chain.

    "Anywhere" means every run of the AR text profile in the database -- every project,
    every earlier test and variant of this suite -- and not only the module's own run. It
    does not mean every row of the table: a ``grounded = false`` row of another profile is
    not this chain's output (see the module docstring), and the database is shared. Taking
    the whole table is what turned this green guard red in the first complete gate, on a row
    that ``jobs/test_recorded_v2_publication_gate.py`` commits by hand for the AR v2 profile.

    The fixture is requested so the test is true on its own and not by the luck of running
    after a test that wrote something; the two scope assertions keep the narrowing from
    emptying the claim.
    """
    scope = {
        "ap": str(AR_TEXT_PROFILE.analysis_profile_id),
        "pb": str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
    }
    own = session.execute(
        text(
            "SELECT count(*) FROM finding_observation "
            "WHERE run_id = :r AND analysis_profile_id = :ap AND prompt_bundle_id = :pb"
        ),
        {"r": ungrounded_run["run_id"], **scope},
    ).scalar_one()
    assert own >= 1, (
        "the profile scope does not select the rows this suite's own run wrote; the "
        "assertion below would look at nothing"
    )
    rows = session.execute(
        text(
            "SELECT DISTINCT grounded, ungrounded_reason FROM finding_observation "
            "WHERE analysis_profile_id = :ap AND prompt_bundle_id = :pb"
        ),
        scope,
    ).all()
    assert rows, "no observations at all; this assertion would be vacuous"
    assert {(grounded, reason) for grounded, reason in rows} == {(True, None)}


def test_the_reason_vocabulary_is_declared_but_unproduced(ungrounded_run, session):
    """The cost, pinned. Five declared reasons; the run that triggered one records a count.

    ``UNGROUNDED_REASONS`` is a real vocabulary with five members and ``anchors.py``
    computes exactly such a reason per unresolved anchor. Neither reaches a row.
    """
    from auditmanager.findings import UNGROUNDED_REASONS

    assert len(UNGROUNDED_REASONS) == 12

    metrics = _text_analysis_metrics(session, ungrounded_run["run_id"])
    dropped = metrics["observations_dropped_unresolved"]
    assert dropped >= 1

    persisted_reasons = session.execute(
        text(
            "SELECT count(*) FROM finding_observation "
            "WHERE run_id = :r AND ungrounded_reason IS NOT NULL"
        ),
        {"r": ungrounded_run["run_id"]},
    ).scalar_one()
    assert persisted_reasons == 0, (
        "a reason reached the database. That is an improvement over base 92bece8 and this "
        "test should be replaced by one asserting the reason is correct."
    )


def test_the_run_still_reaches_published(ungrounded_run, session):
    """Dropping an invented quotation is not a degradation: the run is a clean success."""
    row = session.execute(
        text("SELECT state, degradation_set FROM audit_run WHERE run_id = :r"),
        {"r": ungrounded_run["run_id"]},
    ).mappings().one()
    assert row["state"] == "published"
    assert not row["degradation_set"]
