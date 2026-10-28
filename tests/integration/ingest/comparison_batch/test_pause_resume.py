"""`CMP-INGEST-02`: pause the batch after the set in hand, and resume it (contract: «Пауза после текущего проекта»).

A pause stops the *release* of the next confirmed set: the set in hand (every item of it, the one in flight and the ones
still waiting) finishes, and nothing of the next set is put on the queue until the resume. The drive is what looks at the
queue, so these tests run the real runner over the real drive handler.
"""

from __future__ import annotations

import pytest

from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.ingest.comparison_batch.support import ADMIN, Harness, Queue


def _reason(refusal: DomainError) -> str:
    return str(refusal.detail_fields["conflict_reason"])


def _versions_of(h: Harness, set_id: str) -> list[str]:
    [(proposal,)] = h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=set_id)
    return [f["version_uid"] for f in sorted(proposal["confirmed"]["files"], key=lambda f: f["position"])]


def _two_sets_processing(h: Harness) -> tuple[str, list[str], list[str]]:
    """Alpha (two versions) confirmed and released, Beta (one) confirmed and waiting behind it."""
    upload_id = h.proposed({"Alpha": 2, "Beta": 1})
    alpha, beta = h.sets(upload_id)
    h.confirm(upload_id, alpha)
    h.confirm(upload_id, beta)
    assert h.state(upload_id) == "processing"
    return upload_id, _versions_of(h, alpha.set_id), _versions_of(h, beta.set_id)


class TestPauseStopsAfterTheSetInHand:
    def test_the_set_in_hand_finishes_and_the_next_set_is_not_released_until_the_resume(
        self, h: Harness, queue: Queue
    ) -> None:
        upload_id, alpha, beta = _two_sets_processing(h)
        assert [(w["state"], w["payload"]["version_uid"]) for w in h.work(upload_id, kind="page_profile")] == [
            ("queued", alpha[0]), ("queued", alpha[1])], "only the set in hand is on the queue; Beta waits"

        first = queue.claim()
        assert first is not None and first.payload["version_uid"] == alpha[0]  # in flight
        paused = h.pause(upload_id)
        assert paused.state == "paused"
        assert h.rows("SELECT pause_requested FROM comparison_upload WHERE comparison_upload_id = :i", i=upload_id) == [(True,)]
        assert queue.runner.execute(first) == "succeeded"

        # The rest of the set in hand is not paused: it runs although the batch is paused.
        assert queue.run_all() == [("page_profile", "succeeded")]
        assert [v for v, _u in queue.profiles.seen] == alpha

        # The drive looks at the batch: paused, nothing in flight, a confirmed set waiting -- and it releases nothing.
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "queued")]
        assert [w["payload"]["version_uid"] for w in h.work(upload_id, kind="page_profile")] == alpha
        assert h.state(upload_id) == "paused"

        resumed = h.resume(upload_id)
        assert resumed.state == "processing"
        assert h.rows("SELECT pause_requested FROM comparison_upload WHERE comparison_upload_id = :i", i=upload_id) == [(False,)]
        assert [w["payload"]["version_uid"] for w in h.work(upload_id, kind="page_profile")] == alpha + beta, (
            "the resume releases the next set at once: nothing is in flight")
        assert queue.run_all() == [("page_profile", "succeeded")]
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "succeeded")]
        assert h.state(upload_id) == "completed"

    def test_pausing_while_an_item_is_in_flight_does_not_stop_it(self, h: Harness, queue: Queue) -> None:
        upload_id, alpha, _beta = _two_sets_processing(h)
        in_flight = queue.claim()
        assert in_flight is not None
        h.pause(upload_id)
        row = {w["id"]: w for w in h.work(upload_id, kind="page_profile")}[in_flight.work_id]
        assert row["state"] in ("leased", "running") and not row["cancel_requested"]
        assert queue.runner.execute(in_flight) == "succeeded"

    def test_a_set_confirmed_while_paused_waits_for_the_resume(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        queue.run_all()
        h.pause(upload_id)
        h.confirm(upload_id, beta)  # a person may still decide while the processing is paused
        assert h.set_states(upload_id)[beta.set_id] == "done"
        assert [w["payload"]["version_uid"] for w in h.work(upload_id, kind="page_profile")] == _versions_of(h, alpha.set_id)
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert len(h.work(upload_id, kind="page_profile")) == 1
        h.resume(upload_id)
        assert len(h.work(upload_id, kind="page_profile")) == 2 and h.state(upload_id) == "processing"


class TestPauseAndResumeNeedTheRightState:
    @pytest.mark.parametrize("reach", ["uploading", "proposed", "paused", "completed", "cancelled"])
    def test_pause_is_a_conflict_unless_the_batch_is_being_processed(self, h: Harness, reach: str) -> None:
        if reach == "uploading":
            upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        elif reach == "proposed":
            upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        elif reach == "paused":
            upload_id, _a, _b = _two_sets_processing(h)
            h.pause(upload_id)
        elif reach == "completed":
            upload_id = h.proposed({"Alpha": 1})
            h.confirm(upload_id, h.sets(upload_id)[0])
        else:
            upload_id = h.proposed({"Alpha": 1})
            h.cancel(upload_id)
        assert h.state(upload_id) == reach
        with pytest.raises(DomainError) as refused:
            h.pause(upload_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_state"
        assert h.state(upload_id) == reach

    @pytest.mark.parametrize("reach", ["uploading", "proposed", "processing", "completed", "cancelled"])
    def test_resume_is_a_conflict_unless_the_batch_is_paused(self, h: Harness, reach: str) -> None:
        if reach == "uploading":
            upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        elif reach == "proposed":
            upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        elif reach == "processing":
            upload_id, _a, _b = _two_sets_processing(h)
        elif reach == "completed":
            upload_id = h.proposed({"Alpha": 1})
            h.confirm(upload_id, h.sets(upload_id)[0])
        else:
            upload_id = h.proposed({"Alpha": 1})
            h.cancel(upload_id)
        with pytest.raises(DomainError) as refused:
            h.resume(upload_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_state"
        assert h.state(upload_id) == reach

    def test_a_paused_batch_can_still_be_cancelled(self, h: Harness) -> None:
        upload_id, _a, _b = _two_sets_processing(h)
        h.pause(upload_id)
        assert h.cancel(upload_id).state == "cancelled"


class TestTheActsAreKeyedAndAnExperts:
    def test_a_repeated_pause_answers_the_recorded_outcome_although_the_batch_is_no_longer_processing(
        self, h: Harness
    ) -> None:
        upload_id, _a, _b = _two_sets_processing(h)
        first = h.pause(upload_id, key="pause-1")
        again = h.pause(upload_id, key="pause-1")
        assert (first.state, again.state) == ("paused", "paused")
        with pytest.raises(DomainError) as other_key:
            h.pause(upload_id, key="pause-2")  # a new request on a batch that is already paused is a conflict
        assert other_key.value.code is ErrorCode.CONFLICT

    def test_a_repeated_resume_does_not_release_a_second_time(self, h: Harness) -> None:
        upload_id, _alpha, _beta = _two_sets_processing(h)
        h.pause(upload_id)
        h.resume(upload_id, key="resume-1")
        work = h.work(upload_id)
        h.resume(upload_id, key="resume-1")
        assert h.work(upload_id) == work

    def test_the_same_key_for_another_batch_is_a_key_reuse_and_changes_nothing(self, h: Harness, other_user: str) -> None:
        upload_id, _a, _b = _two_sets_processing(h)
        second = h.proposed({"Gamma": 1, "Delta": 1}, owner=other_user)
        h.confirm(second, h.sets(second)[0])
        assert h.state(second) == "processing"
        h.pause(upload_id, key="shared")
        with pytest.raises(DomainError) as refused:
            h.pause(second, key="shared")
        assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert h.state(second) == "processing"

    @pytest.mark.parametrize("act", ["pause", "resume"])
    def test_an_administrator_without_the_expert_role_is_refused_and_nothing_changes(self, h: Harness, act: str) -> None:
        upload_id, _a, _b = _two_sets_processing(h)
        if act == "resume":
            h.pause(upload_id)
        before = h.state(upload_id)
        with pytest.raises(DomainError) as refused:
            getattr(h, act)(upload_id, roles=ADMIN, key=f"admin-{act}")
        assert refused.value.code is ErrorCode.PERMISSION_DENIED
        assert h.state(upload_id) == before
        assert h.rows("SELECT count(*) FROM command_record WHERE idempotency_key = :k", k=f"admin-{act}") == [(0,)]

    @pytest.mark.parametrize("act", ["pause", "resume"])
    def test_an_unknown_batch_is_not_found(self, h: Harness, act: str) -> None:
        with pytest.raises(DomainError) as refused:
            getattr(h, act)("cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert refused.value.code is ErrorCode.NOT_FOUND
