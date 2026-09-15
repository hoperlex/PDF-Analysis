"""The listing's secondary sort key, shown to be load-bearing rather than defensive.

`W3_CLOSURE.md` §1 records mutation **M2** — dropping `o.finding_observation_id` from
`_PUBLISHED_FINDINGS`'s `ORDER BY` — as green and unreddenable, with this reasoning:

    M2 cannot be reddened and this is worth stating plainly: dropping the tiebreaker makes
    the order *unspecified* rather than *wrong*, and PostgreSQL happens to return the rows
    the expected way on this data. A test that passed today would be resting on the
    planner, not on a property.

That is true of the data the existing guard uses, and only of it.
`test_two_observations_under_one_finding_still_order_deterministically` ties exactly **two**
rows, and at two rows PostgreSQL's sort does not visibly reorder a tie. It is not a fact
about ties in general. Tie twenty observations under one `finding_uid` and the listing and
the CSV disagree, reproducibly, with the tiebreaker dropped:

    listing: 0019, 0016, 0017, 0018, 0000, 0001, ... 0015
    export:  0000, 0001, 0002, 0003, 0004, ...       0019

So M2 *is* reddenable, and the order under it is not merely unspecified — it is observably
different from the order the CSV produces, which is the disagreement D1 was repaired to
prevent.

Why this is a property and not planner-dependence
-------------------------------------------------
The objection in the closure record is a good one and it is worth answering rather than
brushing past. It applies to a test that pins a *literal* expected sequence: such a test
passes because of what the planner did today.

This test pins no sequence. It compares two live queries — the API listing and the CSV
export — and asserts they agree, which is the property
`api/routers/findings.py::_finding_sort_key` states in prose: "a page boundary and a CSV
row order cannot disagree about what 'next' means." If the planner changes, both sides are
free to move; what may not happen is that they move *differently*. Only a total order on
both sides guarantees that, and the tiebreaker is what makes the listing's order total.
A green result here is therefore not a bet on the planner. A red one is proof that without
the tiebreaker the two surfaces can disagree — which is all a mutation needs to show.

Twenty observations under one finding is not an extreme population. PC-01 allocates one
finding per observation so it does not arise today, but nothing in the schema forbids it —
there is no unique constraint — and `ADR-0010` makes the finding the identity that survives
across runs, which is exactly how a second, third and twentieth observation would arrive.

Shown to fail
-------------
Applied to a copy of `src/` at `/root/w5adv-mut` (`contracts/`, `docs/`, `fixtures/`
symlinked), run with `pytest -o pythonpath=/root/w5adv-mut/src`, with
`auditmanager.__file__` asserted to resolve under the copy first. No tracked file was
edited.

* **M2**, `ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C"` →
  `ORDER BY f.finding_uid COLLATE "C"` — `test_the_listing_and_the_export_agree_when_many
  _observations_share_one_finding` failed on `listing == export`, three runs out of three.
  Reverted: green, three runs out of three.
* The discriminating precondition `test_the_tie_is_real_and_the_two_orders_can_differ`
  stays green under M2, as it must: both of its queries are raw SQL, so it keeps its
  meaning while the guard beside it is red.

An earlier version of that precondition asserted the physical heap order through `ctid`
and flaked one run in four. Heap placement depends on free space left by earlier
transactions and is not a property this suite may rest on; what the guard needs is that
the two orders *can* differ, which is now asserted as the two orders.
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

#: Sorts before every real `fnd_` ULID, so the tied block lands first in both orders and a
#: disagreement inside it cannot be hidden by the surrounding rows.
TIED_UID = "fnd_" + "0" * 26

#: How many observations share `TIED_UID`. Two is below the threshold at which PostgreSQL's
#: sort visibly reorders a tie — which is why the wave-3 guard, which ties two, stays green
#: under M2. Twenty is above it. The number is a measured threshold, not a round figure:
#: it is the population at which the mutation became observable.
TIED_COUNT = 20


def _tied_id(index: int) -> str:
    """A well-formed `fobs_` identifier whose ordinal is its sort position.

    Digits only, so the value satisfies `ck_finding_observation_id_format`
    (`^fobs_[0-9A-HJKMNP-TV-Z]{26}$`) and sorts identically under `C` and under the
    database's `en_US.utf8`.
    """
    return "fobs_" + str(index).rjust(26, "0")


@pytest.fixture()
def tied_run(session: Session, seeded, blob_store, recorded_adapter, provider_config) -> str:
    """A real published run, plus `TIED_COUNT` observations under one `finding_uid`.

    They are inserted in **descending** identifier order, so that nothing about the order
    they arrived in helps a sort that has dropped the tiebreaker recover the intended
    sequence.
    """
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w5adv-tie-{uuid.uuid4()}"),
    )
    run_id = str(started.run_id)
    execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    template = session.execute(
        text(
            "SELECT analysis_profile_id, prompt_bundle_id, provider_mode, stage_id, "
            "       category, recommendation_text "
            "FROM finding_observation WHERE run_id = :r AND grounded LIMIT 1"
        ),
        {"r": run_id},
    ).mappings().one()

    session.execute(
        text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, "
            "                     allocated_by_run_id, category) "
            "VALUES (:u, :p, :v, :r, :c)"
        ),
        {
            "u": TIED_UID,
            "p": seeded.project_uid,
            "v": seeded.version_uid,
            "r": run_id,
            "c": template["category"],
        },
    )
    for index in reversed(range(TIED_COUNT)):
        oid = _tied_id(index)
        session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "    finding_uid, stage_id, category, finding_text, recommendation_text, "
                "    grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
                "VALUES (:o, :r, :u, :s, :c, :f, :rec, TRUE, :ap, :pb, :pm)"
            ),
            {
                "o": oid,
                "r": run_id,
                "u": TIED_UID,
                "s": template["stage_id"],
                "c": template["category"],
                "f": f"W5-ADV tie probe {index}",
                "rec": template["recommendation_text"],
                "ap": template["analysis_profile_id"],
                "pb": template["prompt_bundle_id"],
                "pm": template["provider_mode"],
            },
        )
        session.execute(
            text(
                "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
                "    page_number, quote, char_start, char_end) "
                "VALUES (:o, 1, 1, :q, 0, 5)"
            ),
            {"o": oid, "q": "проба"},
        )
    session.flush()
    return run_id


def _first_seen(values):
    seen, ordered = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def test_the_tie_is_real_and_the_two_orders_can_differ(tied_run, session):
    """The discriminating precondition, asserted on the rows rather than on any query.

    Without it the comparison below could pass on a population where nothing ties, or
    where the physical order already happens to be the sorted one — in either case proving
    nothing about the secondary key.
    """
    tied = [
        row[0]
        for row in session.execute(
            text(
                "SELECT finding_observation_id FROM finding_observation "
                "WHERE finding_uid = :u AND grounded ORDER BY finding_observation_id"
            ),
            {"u": TIED_UID},
        )
    ]
    assert tied == [_tied_id(i) for i in range(TIED_COUNT)], (
        f"{len(tied)} observations share the tied finding, not {TIED_COUNT}; the "
        "secondary key is not being exercised"
    )

    # The discriminator, stated as the two orders themselves rather than as a fact about
    # physical storage. My first version asserted the heap order via `ctid` and was
    # rightly flaky: heap placement depends on free space left by earlier transactions,
    # so it is not a property this suite may rest on. What matters is not *why* the two
    # orders differ but *that* they can, which these two queries establish directly.
    # Both are raw SQL, so this precondition is unaffected by any mutation of the
    # application's own query and keeps its meaning when the guard below goes red.
    by_uid_only = [
        row[0]
        for row in session.execute(
            text(
                "SELECT o.finding_observation_id FROM finding_observation o "
                "JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :r AND o.grounded "
                'ORDER BY f.finding_uid COLLATE "C"'
            ),
            {"r": tied_run},
        )
    ]
    by_key_family = [
        row[0]
        for row in session.execute(
            text(
                "SELECT o.finding_observation_id FROM finding_observation o "
                "JOIN finding f ON f.finding_uid = o.finding_uid "
                "WHERE o.run_id = :r AND o.grounded "
                'ORDER BY f.finding_uid COLLATE "C", '
                '         o.finding_observation_id COLLATE "C"'
            ),
            {"r": tied_run},
        )
    ]
    assert by_uid_only != by_key_family, (
        "ordering by the finding alone and ordering by the full key family return the "
        "same sequence on this population, so the guard below could pass without the "
        "secondary key deciding anything"
    )


def test_the_listing_and_the_export_agree_when_many_observations_share_one_finding(
    tied_run, session
):
    """The property `_finding_sort_key`'s docstring states, on a population that ties.

    Nothing here pins a sequence: both sides are live queries and either is free to
    change, so long as they change together.
    """
    listing = [str(row.finding_observation_id) for row in published_findings(session, tied_run)]
    export = _first_seen(
        str(row.finding_observation_id) for row in export_rows(session, tied_run)
    )

    assert set(listing) == set(export), "the two surfaces disagree about which rows exist"
    assert listing == export, (
        "with many observations under one finding the API listing and the CSV disagree "
        "about row order, while api/routers/findings.py says they cannot. The listing's "
        "secondary sort key is not deciding.\n"
        f"  listing: {listing}\n  export:  {export}"
    )
