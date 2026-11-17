"""`RUN-RESTART-01`: the provenance of a restart carry (mode ``restart``) and the wire view of a carried decision's origin."""

from __future__ import annotations

import pytest

from auditmanager.api.schemas.decisions import (
    DecisionCarriedFromView,
    decision_carried_from_body,
    decision_carried_from_view,
)
from auditmanager.decisions.public import (
    CARRYOVER_MODES,
    RESTART_MODE,
    CarriedOrigin,
    CarryoverProvenance,
    carryover_comment,
    known_carry_mode,
)
from auditmanager.decisions.carryover import _check_provenance
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, FindingUid, RunId, VersionUid

VERSION = VersionUid.new().value
SOURCE_RUN, TARGET_RUN = RunId.new().value, RunId.new().value


def provenance(**changes) -> CarryoverProvenance:  # noqa: ANN003
    values = {
        "source_finding_uid": FindingUid.new().value, "source_decision_id": DecisionId.new().value, "source_version_uid": VERSION,
        "source_version_ordinal": 1, "target_version_uid": VERSION, "mode": "restart",
        "source_run_id": SOURCE_RUN, "target_run_id": TARGET_RUN,
    } | changes
    return CarryoverProvenance(**values)


class TestTheRestartMode:
    def test_it_is_one_of_the_modes_the_provenance_names(self) -> None:
        assert RESTART_MODE == "restart" and "restart" in CARRYOVER_MODES

    def test_one_version_on_both_sides_is_a_pair_for_a_restart_and_for_nothing_else(self) -> None:
        _check_provenance(provenance())                                    # the same version: admitted
        for mode in ("version", "stage"):
            with pytest.raises(DomainError) as refused:
                _check_provenance(provenance(mode=mode))
            assert refused.value.code is ErrorCode.CONFLICT
            assert refused.value.detail_fields["conflict_reason"] == "carryover_pair_not_proposed"

    def test_a_restart_needs_two_runs_and_two_different_ones(self) -> None:
        for field in ("source_run_id", "target_run_id"):
            for bad in (None, "run_x", 7):
                with pytest.raises(DomainError) as refused:
                    _check_provenance(provenance(**{field: bad}))
                assert refused.value.code is ErrorCode.VALIDATION_FAILED
                assert refused.value.detail_fields["field"] == field
        with pytest.raises(DomainError) as same:
            _check_provenance(provenance(target_run_id=SOURCE_RUN))
        assert same.value.detail_fields["conflict_reason"] == "carryover_pair_not_proposed"

    def test_the_other_modes_read_no_run(self) -> None:
        other = VersionUid.new().value
        _check_provenance(provenance(mode="version", target_version_uid=other, source_run_id=None, target_run_id=None))

    def test_the_sentence_names_the_restart_and_both_runs_and_claims_no_confirmation(self) -> None:
        sentence = carryover_comment(provenance())
        assert sentence.startswith(f"Перенесено при перезапуске из прогона {SOURCE_RUN}. ")
        assert TARGET_RUN in sentence
        assert "подтвержден" not in sentence and "экспертом" not in sentence

    def test_the_sentence_is_a_byte_stable_function_of_the_provenance(self) -> None:
        one = provenance()
        assert carryover_comment(one) == carryover_comment(one)
        assert carryover_comment(one) != carryover_comment(provenance(source_decision_id=DecisionId.new().value))
        assert carryover_comment(one) != carryover_comment(provenance(target_run_id=RunId.new().value))


class TestTheModeReadFromACommand:
    @pytest.mark.parametrize("mode", ["version", "stage", "restart"])
    def test_a_known_mode_is_kept(self, mode: str) -> None:
        assert known_carry_mode(mode) == mode

    @pytest.mark.parametrize("value", [None, "", "object", "RESTART", 3, {"mode": "restart"}])
    def test_anything_else_is_not_a_mode(self, value: object) -> None:
        assert known_carry_mode(value) is None


class TestTheWireViewOfAnOrigin:
    def origin(self, **changes) -> CarriedOrigin:  # noqa: ANN003
        values = {
            "decision_id": DecisionId.new().value, "finding_uid": FindingUid.new().value, "version_uid": VERSION, "version_ordinal": 2,
            "run_id": SOURCE_RUN, "mode": "restart",
        } | changes
        return CarriedOrigin(**values)

    def test_the_run_and_the_mode_reach_the_view_and_the_body(self) -> None:
        origin = self.origin()
        view = decision_carried_from_view(origin)
        assert view == DecisionCarriedFromView(
            decision_id=origin.decision_id, finding_uid=origin.finding_uid, version_uid=VERSION, version_ordinal=2,
            run_id=SOURCE_RUN, mode="restart",
        )
        body = decision_carried_from_body(view)
        assert body["run_id"] == SOURCE_RUN and body["mode"] == "restart"

    def test_an_origin_that_read_neither_is_a_view_without_them(self) -> None:
        view = decision_carried_from_view(self.origin(run_id=None, mode=None))
        assert (view.run_id, view.mode) == (None, None)
        assert "run_id" not in decision_carried_from_body(view) and "mode" not in decision_carried_from_body(view)

    def test_a_decision_made_directly_has_no_view(self) -> None:
        assert decision_carried_from_view(None) is None

    def test_an_origin_of_the_old_shape_still_reads(self) -> None:
        assert CarriedOrigin("dec_x", "fnd_x", "ver_x", 1).run_id is None
