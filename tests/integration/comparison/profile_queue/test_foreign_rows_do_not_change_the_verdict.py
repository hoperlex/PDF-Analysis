"""The suite does not depend on what other integration directories leave in the database (`CMP-PQ-ISOLATION-01`).

The comparison queue is written for a worker: it yields to *any* claimable Run, leases the strongest queued item of *any*
project and reclaims *every* expired lease. A test that asks about its own items must not inherit those answers. The
other tests of this directory read the queue through the lane's own projects (``Lane.gates``, ``Lane.claim``,
``Lane.reclaim``); here the rows another directory would leave are planted on purpose -- a claimable Run, a queued item
that is stronger than the lane's, a lease that ran out -- so that the isolation is shown on any database, fresh or not,
and not only on one that happens to be dirty. Each plant is a row the unscoped runner would act on; each is shown acted
on by the real, unscoped read and ignored by the lane's.
"""

from __future__ import annotations

from sqlalchemy import text

from auditmanager.comparison.public import default_gates


def test_the_lanes_run_gate_reads_its_own_projects_the_real_gate_reads_every_run(lane, small_pdf) -> None:
    lane.foreign_run()
    seeded = lane.seed(small_pdf(1), 1)
    with lane.sessions() as session:
        # A Run of another project is claimable: the real gate yields to it, the lane's does not.
        assert default_gates().run_claimable(session) is True, "premise: the real gate yields to the foreign Run"
        assert lane.gates().run_claimable(session) is False
        session.rollback()
        # A Run of the lane's own project (written here, never committed) shuts the lane's gate: it is a read, not a constant.
        own_run = lane.queue_run(session, project_uid=seeded.project_uid, version_uid=seeded.version_uid)
        assert lane.gates().run_claimable(session) is True, f"the lane's gate did not see its own Run {own_run}"
        session.rollback()
        # ... and not the Run once it is no longer due or no longer queued.
        lane.queue_run(session, project_uid=seeded.project_uid, version_uid=seeded.version_uid)
        session.execute(text(
            "UPDATE job SET available_at = statement_timestamp() + interval '1 hour' "
            "WHERE run_id IN (SELECT run_id FROM audit_run WHERE project_uid = :p)"
        ), {"p": seeded.project_uid})
        assert lane.gates().run_claimable(session) is False, "a Job that is not due yet is not claimable"
        session.rollback()


def test_a_foreign_run_a_stronger_foreign_item_and_a_foreign_expired_lease_change_nothing_the_suite_asks(
    lane, small_pdf
) -> None:
    lane.foreign_run()
    expired_work, expired_attempt = lane.foreign_expired_lease()
    queued_work = lane.foreign_item()
    seeded = lane.seed(small_pdf(1), 1)
    enqueued = lane.enqueue(seeded)
    runner = lane.runner()

    # The claim: not silenced by the foreign Run, and not taken by the stronger foreign item.
    item = lane.claim(runner)
    assert item.work_id == enqueued.work_id and item.project_uid == seeded.project_uid
    assert lane.work(queued_work)["state"] == "queued" and lane.work(queued_work)["attempt_count"] == 0

    # The reclaim: the worker's reclaim also fences the foreign lease; the lane counts only its own attempt.
    lane.expire_lease(item.attempt_id)
    assert lane.reclaim(runner) == 1
    assert [(a["attempt_id"], a["state"]) for a in lane.attempts(expired_work)] == [(expired_attempt, "lost")], (
        "premise: the reclaim did fence the foreign lease"
    )
    assert lane.work(expired_work)["state"] == "queued", "so the foreign item is queued again, stronger than the lane's"
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "lost")]

    # The next claim, with two stronger foreign items queued, is the lane's own item again, and it is built.
    lane.make_due(enqueued.work_id)
    again = lane.claim(runner)
    assert again.work_id == enqueued.work_id and again.attempt_no == 2
    assert runner.execute(again) == "succeeded"
    assert [row.page_number for row in lane.rows(seeded.version_uid)] == [1]

    # Nothing foreign was leased, run or changed by the lane: the foreign items are as the reclaim left them.
    assert [a["state"] for a in lane.attempts(queued_work)] == []
    assert [a["state"] for a in lane.attempts(expired_work)] == ["lost"]
    assert lane.work(queued_work)["state"] == "queued" and lane.work(expired_work)["state"] == "queued"
