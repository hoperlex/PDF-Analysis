"""`RUN-RESTART-01`: the report a call of ``carry_restart_decisions`` hands its caller, and the marker that stores it."""

from __future__ import annotations

from auditmanager.decisions.public import RestartCarryReport
from auditmanager.shared.identity import RunId

SOURCE_RUN, TARGET_RUN = RunId.new().value, RunId.new().value


class TestTheReport:
    def report(self, **changes) -> RestartCarryReport:  # noqa: ANN003
        return RestartCarryReport(run_id=TARGET_RUN, lineage=(SOURCE_RUN,), carried_verdicts=3, carried_comments=2, appended=5, **changes)

    def test_it_is_loggable_flat_fields(self) -> None:
        fields = self.report(severities_skipped=1, unmatched_decisions=4, ties_skipped=2).as_fields()
        assert fields["run_id"] == TARGET_RUN and fields["lineage"] == [SOURCE_RUN]
        assert (fields["carried_verdicts"], fields["carried_comments"], fields["severities_skipped"]) == (3, 2, 1)
        assert (fields["unmatched_decisions"], fields["ties_skipped"], fields["failures"]) == (4, 2, 0)

    def test_the_marker_stores_the_counts_and_the_mode_and_reads_back_as_a_repeat_that_appended_nothing(self) -> None:
        stored = self.report(complete=True).marker_outcome()
        assert stored["mode"] == "restart"
        again = RestartCarryReport.from_marker(TARGET_RUN, stored)
        assert (again.carried_verdicts, again.carried_comments, again.appended) == (3, 2, 0)
        assert again.complete and again.already_complete and again.lineage == (SOURCE_RUN,)

    def test_a_marker_with_a_missing_or_foreign_count_reads_it_as_zero_never_as_a_guess(self) -> None:
        again = RestartCarryReport.from_marker(TARGET_RUN, {"carried_verdicts": True, "carried_comments": "7", "failures": 2})
        assert (again.carried_verdicts, again.carried_comments, again.failures) == (0, 0, 2)
