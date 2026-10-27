"""`CMP-INGEST-02`: leave a set out («Исключить») and queue a failed set again («Повторить»).

An exclusion is final: no edge of the database leaves ``excluded``, and nothing here asks for one. A retry is only for a
set that failed for a reason a retry can fix (the sets limit, while the batch has room); the document's own reasons would
be met again.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from tests.integration.ingest.comparison_batch.support import ADMIN, Harness, Queue


def _reason(refusal: DomainError) -> str:
    return str(refusal.detail_fields["conflict_reason"])


def _fail(h: Harness, set_id: str, reason: str) -> None:
    """The state ``CMP-INGEST-01`` leaves a set in when it refuses it (``needs_confirmation`` to ``failed``)."""
    with session_scope(h.sessions) as session:
        session.execute(text(
            "UPDATE comparison_upload_set SET state = 'failed', failure_reason = :r WHERE comparison_upload_set_id = :s"
        ), {"r": reason, "s": set_id})


def _fill_with_open_sets(h: Harness, upload_id: str, count: int) -> None:
    """``count`` more sets in a state that is neither ``failed`` nor ``excluded`` (they count toward the limit)."""
    with session_scope(h.sessions) as session:
        for _ in range(count):
            session.execute(text(
                "INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id) VALUES (:s, :u)"
            ), {"s": f"cus_{new_ulid()}", "u": upload_id})


class TestExclude:
    def test_a_set_awaiting_confirmation_is_left_out_and_its_files_stay_as_history(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        left_out = h.exclude(upload_id, alpha.set_id)
        assert left_out.state == "excluded" and [f.file_id for f in left_out.files] == [f.file_id for f in alpha.files]
        assert h.set_states(upload_id) == {alpha.set_id: "excluded", beta.set_id: "needs_confirmation"}
        assert h.rows("SELECT state, set_id FROM comparison_upload_file WHERE set_id = :s ORDER BY comparison_upload_file_id",
                      s=alpha.set_id) == [("verified", alpha.set_id)] * 2, "history: nothing is deleted and nothing is admitted"
        assert h.rows("SELECT count(*) FROM document_version") == [(0,)] and h.rows("SELECT count(*) FROM document") == [(0,)]
        assert h.rows("SELECT terminal_at IS NOT NULL FROM comparison_upload_set WHERE comparison_upload_set_id = :s",
                      s=alpha.set_id) == [(True,)]

    def test_who_left_it_out_is_kept_in_the_sets_own_record(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id)
        [(proposal,)] = h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id)
        assert proposal["exclusion"] == {"by": h.user}
        assert "files" in proposal, "what the set held is kept beside it"

    def test_a_set_that_failed_can_be_left_out(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        assert h.exclude(upload_id, alpha.set_id).state == "excluded"

    def test_a_set_that_made_versions_cannot_be_left_out(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        with pytest.raises(DomainError) as refused:
            h.exclude(upload_id, alpha.set_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_set_state"
        assert h.set_states(upload_id)[alpha.set_id] == "done"

    def test_an_excluded_set_cannot_be_left_out_again(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id)
        with pytest.raises(DomainError) as refused:
            h.exclude(upload_id, alpha.set_id)
        assert _reason(refused.value) == "comparison_set_state"

    @pytest.mark.parametrize("reach", ["completed", "cancelled"])
    def test_a_finished_batch_takes_no_exclusion(self, h: Harness, reach: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        first, second = h.sets(upload_id)
        if reach == "cancelled":
            h.cancel(upload_id)
        else:
            h.exclude(upload_id, first.set_id)
            h.exclude(upload_id, second.set_id)
        assert h.state(upload_id) == reach
        with pytest.raises(DomainError) as refused:
            h.exclude(upload_id, first.set_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_state"

    def test_a_set_of_a_batch_still_uploading_is_refused(self, h: Harness) -> None:
        names = ["Alpha (1).pdf", "Beta (1).pdf"]
        view = h.declare(names)
        by_name = {i.display_name: i.file_id for i in view.files or ()}
        h.send(view.upload_id, by_name["Alpha (1).pdf"], "Alpha (1).pdf")
        h.complete(view.upload_id, by_name["Alpha (1).pdf"])
        assert h.state(view.upload_id) == "uploading"
        [only] = h.sets(view.upload_id)
        with pytest.raises(DomainError) as refused:
            h.exclude(view.upload_id, only.set_id)
        assert _reason(refused.value) == "comparison_upload_state"
        assert h.set_states(view.upload_id)[only.set_id] == "uploading"

    def test_a_set_of_another_batch_or_an_unknown_one_is_not_found(self, h: Harness, other_user: str) -> None:
        mine = h.proposed({"Alpha": 1, "Beta": 1})
        theirs = h.proposed({"Gamma": 1, "Delta": 1}, owner=other_user)
        foreign = h.sets(theirs)[0]
        for upload_id, set_id in ((mine, foreign.set_id), (mine, "cus_01ARZ3NDEKTSV4RRFFQ69G5FAV"),
                                  ("cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV", foreign.set_id)):
            with pytest.raises(DomainError) as refused:
                h.exclude(upload_id, set_id)
            assert refused.value.code is ErrorCode.NOT_FOUND
        assert h.set_states(theirs)[foreign.set_id] == "needs_confirmation"


class TestAnExclusionIsFinal:
    def test_nothing_reopens_an_excluded_set_not_a_retry_not_a_confirmation_not_another_exclusion(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id)
        with pytest.raises(DomainError) as retried:
            h.retry(upload_id, alpha.set_id)
        assert _reason(retried.value) == "comparison_set_state"
        with pytest.raises(DomainError) as confirmed:
            h.confirm(upload_id, alpha)
        assert _reason(confirmed.value) == "comparison_set_state"
        assert h.set_states(upload_id)[alpha.set_id] == "excluded"
        assert h.rows("SELECT count(*) FROM document_version") == [(0,)]

    @pytest.mark.parametrize("to_state", ["needs_confirmation", "reading", "ready", "failed", "uploading"])
    def test_the_database_has_no_edge_out_of_excluded(self, h: Harness, to_state: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id)
        with pytest.raises(DatabaseError):
            with session_scope(h.sessions) as session:
                session.execute(text(
                    "UPDATE comparison_upload_set SET state = :t, failure_reason = CASE WHEN :t = 'failed' THEN 'x' END, "
                    "terminal_at = NULL WHERE comparison_upload_set_id = :s"), {"t": to_state, "s": alpha.set_id})


class TestExclusionCompletesTheBatch:
    def test_leaving_out_the_last_undecided_set_of_a_proposed_batch_finishes_it_and_frees_the_slot(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id)
        assert h.state(upload_id) == "proposed"
        h.exclude(upload_id, beta.set_id)
        assert h.state(upload_id) == "completed"

    def test_leaving_out_the_last_set_of_a_processing_batch_finishes_it_once_its_work_has_ended(
        self, h: Harness, queue: Queue
    ) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        h.exclude(upload_id, beta.set_id)
        assert h.state(upload_id) == "processing", "Alpha's item is still on the queue"
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert h.state(upload_id) == "completed"

    def test_leaving_out_a_set_when_nothing_is_live_finishes_a_processing_batch_at_once(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        queue.run_all()
        h.exclude(upload_id, beta.set_id)
        assert h.state(upload_id) == "completed"


class TestRetry:
    def test_a_set_that_failed_for_the_sets_limit_is_queued_again_while_the_batch_has_room(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        again = h.retry(upload_id, alpha.set_id)
        assert again.state == "needs_confirmation" and again.failure_reason is None
        assert h.rows("SELECT failure_reason FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id) == [(None,)]
        # It is a set like any other again: the user can confirm it.
        confirmed = h.confirm(upload_id, again)
        assert confirmed.state == "done" and confirmed.document_uid

    def test_a_retry_while_the_batch_has_no_room_is_refused_and_the_set_stays_failed(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        _fill_with_open_sets(h, upload_id, 99)  # beta + 99 = 100 open sets: the limit
        with pytest.raises(DomainError) as refused:
            h.retry(upload_id, alpha.set_id)
        assert _reason(refused.value) == "comparison_set_state"
        assert h.set_states(upload_id)[alpha.set_id] == "failed"
        h.exclude(upload_id, h.sets(upload_id)[1].set_id)  # leaving a set out makes room
        assert h.retry(upload_id, alpha.set_id).state == "needs_confirmation"

    @pytest.mark.parametrize("reason", [
        "content_not_encrypted", "content_declared_page_count", "comparison_file_sha256", "comparison_file_size",
        "staged_upload_lost", "batch_cancelled", "anything_else",
    ])
    def test_a_set_that_failed_for_any_other_reason_cannot_be_retried(self, h: Harness, reason: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, reason)
        with pytest.raises(DomainError) as refused:
            h.retry(upload_id, alpha.set_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_set_state"
        assert h.set_states(upload_id)[alpha.set_id] == "failed"
        assert h.rows("SELECT failure_reason FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id) == [(reason,)]

    @pytest.mark.parametrize("reach", ["needs_confirmation", "done", "excluded"])
    def test_only_a_failed_set_can_be_retried(self, h: Harness, reach: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        if reach == "done":
            h.confirm(upload_id, alpha)
        elif reach == "excluded":
            h.exclude(upload_id, alpha.set_id)
        with pytest.raises(DomainError) as refused:
            h.retry(upload_id, alpha.set_id)
        assert _reason(refused.value) == "comparison_set_state"
        assert h.set_states(upload_id)[alpha.set_id] == reach

    def test_a_finished_batch_cannot_take_a_retry(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        h.cancel(upload_id)
        with pytest.raises(DomainError) as refused:
            h.retry(upload_id, alpha.set_id)
        assert _reason(refused.value) == "comparison_upload_state"


class TestTheActsAreKeyedAndAnExperts:
    @pytest.mark.parametrize("act", ["exclude", "retry"])
    def test_an_administrator_without_the_expert_role_is_refused_and_nothing_changes(self, h: Harness, act: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        with pytest.raises(DomainError) as refused:
            getattr(h, act)(upload_id, alpha.set_id, roles=ADMIN, key=f"admin-{act}")
        assert refused.value.code is ErrorCode.PERMISSION_DENIED
        assert h.set_states(upload_id)[alpha.set_id] == "failed"
        assert h.rows("SELECT count(*) FROM command_record WHERE idempotency_key = :k", k=f"admin-{act}") == [(0,)]

    def test_a_repeated_exclusion_answers_the_recorded_outcome_and_a_new_request_is_a_conflict(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        first = h.exclude(upload_id, alpha.set_id, key="ex-1")
        again = h.exclude(upload_id, alpha.set_id, key="ex-1")
        assert (first.state, again.state) == ("excluded", "excluded")
        with pytest.raises(DomainError) as other_key:
            h.exclude(upload_id, alpha.set_id, key="ex-2")
        assert other_key.value.code is ErrorCode.CONFLICT

    def test_the_same_key_for_another_set_is_a_key_reuse_and_leaves_the_other_set_alone(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.exclude(upload_id, alpha.set_id, key="shared")
        with pytest.raises(DomainError) as refused:
            h.exclude(upload_id, beta.set_id, key="shared")
        assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert h.set_states(upload_id)[beta.set_id] == "needs_confirmation"

    def test_a_repeated_retry_answers_the_recorded_outcome(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        _fail(h, alpha.set_id, "comparison_sets_limit")
        first = h.retry(upload_id, alpha.set_id, key="retry-1")
        again = h.retry(upload_id, alpha.set_id, key="retry-1")
        assert (first.state, again.state) == ("needs_confirmation", "needs_confirmation")

    def test_a_refused_act_leaves_no_record_so_the_key_can_be_used_again(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        with pytest.raises(DomainError):
            h.retry(upload_id, alpha.set_id, key="later")  # not failed yet
        assert h.rows("SELECT count(*) FROM command_record WHERE idempotency_key = 'later'") == [(0,)]
        _fail(h, alpha.set_id, "comparison_sets_limit")
        assert h.retry(upload_id, alpha.set_id, key="later").state == "needs_confirmation"
