"""Terminal selection, and the run states the database will actually accept.

``select_terminal`` is a pure function, but a terminal it chose that the schema refuses
would be a decision nobody could record. So every selection here is also *applied* to a
real ``audit_run`` row, through the declared topology and past the state-guard trigger
and the degradation-set constraints. A test that only checked the function's return
value would pass just as happily with a terminal the run can never reach.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from auditmanager.findings import (
    TerminalSelection,
    publish_gate_result,
    published_finding_count,
    run_grounding_gate,
    select_terminal,
)
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode

REQUIRED = ("source_preparation", "page_geometry_extraction", "text_analysis")


def _observation(anchors, *, category="internal_contradiction"):
    return {
        "category": category,
        "finding_text": "Расхождение между разделами.",
        "recommendation_text": "Согласовать значения.",
        "evidence": anchors,
    }


class TestSelection:
    def test_all_required_stages_succeeded_gives_published_with_no_degradation(self) -> None:
        selection = select_terminal(
            {stage: "succeeded" for stage in REQUIRED}, required_stages=REQUIRED
        )
        assert selection.state == "published"
        assert selection.degradation_set == ()
        assert selection.terminal_reason is None
        assert selection.is_publishable

    def test_a_partial_text_analysis_gives_partial_and_records_the_missing_set(self) -> None:
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "partial"
        selection = select_terminal(statuses, required_stages=REQUIRED)
        assert selection.state == "partial"
        assert selection.degradation_set == ("text_analysis",)
        assert selection.is_publishable, (
            "partial is a terminal state and stays exportable under OD-11; no PC-01 "
            "operation refuses because a run is partial"
        )

    def test_a_partial_text_analysis_is_never_published(self) -> None:
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "partial"
        assert select_terminal(statuses, required_stages=REQUIRED).state != "published"

    def test_a_failed_required_stage_gives_failed_with_a_reason(self) -> None:
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "failed"
        selection = select_terminal(statuses, required_stages=REQUIRED)
        assert selection.state == "failed"
        assert selection.terminal_reason == "analysis_failed"
        assert not selection.is_publishable

    def test_failed_dominates_partial(self) -> None:
        """A run that lost a whole stage is not on the exportable side of the line."""
        statuses = {
            "source_preparation": "succeeded",
            "page_geometry_extraction": "failed",
            "text_analysis": "partial",
        }
        assert select_terminal(statuses, required_stages=REQUIRED).state == "failed"

    def test_a_skipped_required_stage_fails_the_run(self) -> None:
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["page_geometry_extraction"] = "skipped"
        assert select_terminal(statuses, required_stages=REQUIRED).state == "failed"

    def test_a_gate_that_did_not_run_cannot_publish(self) -> None:
        """The gate is unconditional and no flag lets an ungrounded item publish."""
        selection = select_terminal(
            {stage: "succeeded" for stage in REQUIRED},
            required_stages=REQUIRED,
            gate_ran=False,
        )
        assert selection.state == "failed"

    def test_an_unreported_required_stage_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            select_terminal({"source_preparation": "succeeded"}, required_stages=REQUIRED)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_a_status_outside_the_declared_set_is_refused(self) -> None:
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "mostly_fine"
        with pytest.raises(DomainError) as caught:
            select_terminal(statuses, required_stages=REQUIRED)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_an_incoherent_selection_cannot_be_constructed(self) -> None:
        """The same coupling the schema enforces, refused at the point of decision."""
        with pytest.raises(ValueError):
            TerminalSelection(state="published", degradation_set=("text_analysis",))
        with pytest.raises(ValueError):
            TerminalSelection(state="partial", degradation_set=())
        with pytest.raises(ValueError):
            TerminalSelection(state="failed")

    def test_zero_findings_is_still_published(self) -> None:
        """A clean document publishes nothing and is not a failure. Making the terminal
        depend on the finding count would give the run a reason to want findings."""
        assert (
            select_terminal(
                {stage: "succeeded" for stage in REQUIRED}, required_stages=REQUIRED
            ).state
            == "published"
        )


class TestTheRunCanActuallyReachTheChosenTerminal:
    def test_a_partial_run_terminates_partial_and_still_carries_its_findings(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """A partial text analysis: usable observations over a strict subset of pages.

        The run publishes what grounded and terminates ``partial`` with the degraded
        stage recorded. ``partial`` is terminal and exportable, so the findings are
        readable afterwards exactly as a published run's are.
        """
        anchors = [a for a in corpus.seeded_anchors() if a["page_number"] in {2, 3}]
        assert anchors
        observations = make_observations(
            [_observation([a], category=a["category"]) for a in anchors],
            pages_analysed=(1, 2, 3, 4),
        )
        assert set(observations.pages_analysed) < set(range(1, 9)), (
            "partial is reported only over a strict subset of pages"
        )

        seeded.advance_to("validating")
        result = run_grounding_gate(observations, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )

        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "partial"
        selection = select_terminal(statuses, required_stages=REQUIRED)
        seeded.terminate(selection)

        assert seeded.state() == "partial"
        degradation = session.execute(
            text("SELECT degradation_set FROM audit_run WHERE run_id = :run"),
            {"run": seeded.run_id},
        ).scalar_one()
        assert degradation == ["text_analysis"]
        assert published_finding_count(session, seeded.run_id) == len(anchors)

    def test_a_published_run_terminates_published(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchors = corpus.seeded_anchors()
        observations = make_observations(
            [_observation([a], category=a["category"]) for a in anchors]
        )
        seeded.advance_to("validating")
        result = run_grounding_gate(observations, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        selection = select_terminal(
            {stage: "succeeded" for stage in REQUIRED}, required_stages=REQUIRED
        )
        seeded.terminate(selection)
        assert seeded.state() == "published"

    def test_a_failed_run_publishes_nothing(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """A required stage failed, so the gate's verdict never becomes rows."""
        statuses = {stage: "succeeded" for stage in REQUIRED}
        statuses["text_analysis"] = "failed"
        selection = select_terminal(statuses, required_stages=REQUIRED)
        assert not selection.is_publishable

        seeded.advance_to("validating")
        seeded.terminate(selection)
        assert seeded.state() == "failed"
        assert published_finding_count(session, seeded.run_id) == 0
        assert (
            session.execute(
                text("SELECT count(*) FROM finding_observation WHERE run_id = :run"),
                {"run": seeded.run_id},
            ).scalar_one()
            == 0
        )

    def test_the_database_refuses_a_published_run_that_records_a_degradation(
        self, session: Session, seeded
    ) -> None:
        """A silent degradation cannot reach the success terminal, whatever the
        selection function says."""
        seeded.advance_to("validating")
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "UPDATE audit_run SET state = 'published', terminal_at = now(), "
                        "degradation_set = '[\"text_analysis\"]'::jsonb WHERE run_id = :run"
                    ),
                    {"run": seeded.run_id},
                )

    def test_the_database_refuses_a_partial_run_with_an_empty_degradation_set(
        self, session: Session, seeded
    ) -> None:
        seeded.advance_to("validating")
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "UPDATE audit_run SET state = 'partial', terminal_at = now() "
                        "WHERE run_id = :run"
                    ),
                    {"run": seeded.run_id},
                )

    def test_a_terminal_run_is_never_reopened(self, session: Session, seeded) -> None:
        seeded.advance_to("validating")
        seeded.terminate(
            select_terminal(
                {stage: "succeeded" for stage in REQUIRED}, required_stages=REQUIRED
            )
        )
        assert seeded.state() == "published"
        with pytest.raises(DBAPIError) as caught:
            with nested_transaction(session):
                proxy = session.execute(
                    text(
                        "UPDATE audit_run SET state = 'validating', terminal_at = NULL "
                        "WHERE run_id = :run"
                    ),
                    {"run": seeded.run_id},
                )
                assert proxy.rowcount == 1
        assert caught.value.orig.sqlstate == "AM001"


class TestTheReasonNamesTheCause:
    """``select_terminal`` reports the stages' own code when they agree on one.

    The end-to-end behaviour is guarded in ``tests/integration/runs``; these cover the two
    branches a live run cannot easily produce — stages failing for *different* reasons, and
    a code outside the frozen catalog.
    """

    stages = ("source_preparation", "text_analysis")

    def test_one_shared_code_becomes_the_reason(self) -> None:
        selection = select_terminal(
            {"source_preparation": "succeeded", "text_analysis": "failed"},
            required_stages=self.stages,
            stage_errors={"text_analysis": "dependency_unavailable"},
        )
        assert selection.terminal_reason == "dependency_unavailable"

    def test_two_different_codes_keep_the_generic_reason(self) -> None:
        """One reason cannot represent two causes, so naming either would be a guess."""
        selection = select_terminal(
            {"source_preparation": "failed", "text_analysis": "failed"},
            required_stages=self.stages,
            stage_errors={
                "source_preparation": "dependency_unavailable",
                "text_analysis": "analysis_input_invalid",
            },
        )
        assert selection.terminal_reason == "analysis_failed"

    def test_a_code_outside_the_frozen_catalog_is_not_passed_through(self) -> None:
        """``audit_run.terminal_reason`` is CHECK-constrained to the catalog; a stage that
        invented a code must not turn a failed run into a database error."""
        selection = select_terminal(
            {"source_preparation": "succeeded", "text_analysis": "failed"},
            required_stages=self.stages,
            stage_errors={"text_analysis": "not_a_catalog_member"},
        )
        assert selection.terminal_reason == "analysis_failed"

    def test_no_codes_at_all_keeps_the_generic_reason(self) -> None:
        selection = select_terminal(
            {"source_preparation": "succeeded", "text_analysis": "failed"},
            required_stages=self.stages,
        )
        assert selection.terminal_reason == "analysis_failed"
