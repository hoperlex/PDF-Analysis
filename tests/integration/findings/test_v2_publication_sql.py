"""Characterize the additive v2 savepoint writer without claiming DB acceptance."""

from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError

from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    GroundedProposal, ProposalGroundingResult, RejectedProposal, UnresolvedEvidence,
)
from auditmanager.analysis.profiles.ar_v2.response import ProposedEvidence, ProposedObservation
from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.findings.merge_publication_plan import plan_v2_merge_publication
from auditmanager.findings.v2_publication import V2PublicationContext, publish_v2_merge_plan
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId, ModelCallId, ProjectUid, PromptBundleId, RunId, VersionUid,
)


class _Savepoint:
    def __init__(self, session: _Session) -> None:
        self.session = session

    def __enter__(self) -> _Savepoint:
        self.session.begin_count += 1
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is None:
            self.session.committed.extend(self.session.pending)
        else:
            self.session.rollback_count += 1
        self.session.pending.clear()


class _Result:
    rowcount = 1


class _Session:
    def __init__(self, *, fail_at: int | None = None, sqlstate: str = "AM003",
                 canonical_rowcount: int = 1) -> None:
        self.fail_at = fail_at
        self.sqlstate = sqlstate
        self.canonical_rowcount = canonical_rowcount
        self.pending: list[tuple[str, dict]] = []
        self.committed: list[tuple[str, dict]] = []
        self.begin_count = 0
        self.rollback_count = 0
        self.executions = 0

    def begin_nested(self) -> _Savepoint:
        return _Savepoint(self)

    def execute(self, statement: object, params: dict) -> _Result:
        self.executions += 1
        if self.executions == self.fail_at:
            class _DbRefusal(Exception):
                pass

            original = _DbRefusal("injected")
            original.sqlstate = self.sqlstate
            raise DBAPIError("statement", params, original, False)
        sql = str(statement)
        self.pending.append((sql, dict(params)))
        if sql.startswith("UPDATE finding"):
            result = _Result()
            result.rowcount = self.canonical_rowcount
            return result
        return _Result()


def _plan() -> object:
    quote = "Размеры помещения указаны"

    def item(source: int, start: int, category: str, severity: str) -> GroundedProposal:
        proposal = ProposedObservation(
            category, f"Проверить {source}", "Сверить чертёж", severity,
            (ProposedEvidence(1, quote),),
        )
        return GroundedProposal(
            source, proposal, (ResolvedAnchor(1, quote, start, start + len(quote)),)
        )

    grounding = ProposalGroundingResult(
        accepted=(
            item(0, 10, "dimensions", "operational"),
            item(2, 15, "dimensions", "critical"),
            item(3, 80, "layout", "economic"),
        ),
        rejected=(RejectedProposal(1, (UnresolvedEvidence(0, 1, "missing", "quotation_absent"),)),),
        malformed_count=2,
        salvaged=True,
    )
    return plan_v2_merge_publication(grounding, prepare_merge(grounding))


_CONTEXT = V2PublicationContext(
    run_id=RunId.new().value, project_uid=ProjectUid.new().value,
    version_uid=VersionUid.new().value,
    analysis_profile_id=AnalysisProfileId.new().value,
    prompt_bundle_id=PromptBundleId.new().value,
    provider_mode="recorded", model_call_id=ModelCallId.new().value,
)


def test_sql_order_group_identity_canonical_and_full_member_evidence() -> None:
    session = _Session()
    plan = _plan()
    result = publish_v2_merge_plan(session, plan=plan, context=_CONTEXT)

    assert session.begin_count == 1 and session.rollback_count == 0
    assert session.pending == [] and len(session.committed) == 10
    assert [sql.split(" (")[0] if sql.startswith("INSERT") else "UPDATE finding"
            for sql, _ in session.committed] == [
        "INSERT INTO finding", "INSERT INTO finding_observation", "INSERT INTO finding_evidence",
        "INSERT INTO finding_observation", "INSERT INTO finding_evidence", "UPDATE finding",
        "INSERT INTO finding", "INSERT INTO finding_observation", "INSERT INTO finding_evidence",
        "UPDATE finding",
    ]
    first_finding = session.committed[0][1]
    first_observation = session.committed[1][1]
    second_observation = session.committed[3][1]
    first_evidence = session.committed[2][1]
    assert first_finding["finding_uid"] == first_observation["finding_uid"] == second_observation["finding_uid"]
    assert first_observation["finding_observation_id"] != second_observation["finding_observation_id"]
    assert first_observation["proposed_severity"] == "operational"
    assert second_observation["proposed_severity"] == "critical"
    assert first_observation["grounded"] is True and first_observation["ungrounded_reason"] is None
    assert first_observation["stage_id"] == "text_analysis"
    assert first_observation["model_call_id"] == _CONTEXT.model_call_id
    assert first_evidence == {
        "finding_observation_id": first_observation["finding_observation_id"],
        "evidence_ordinal": 0, "page_number": 1, "quote": "Размеры помещения указаны",
        "char_start": 10, "char_end": 35, "block_id": None,
    }
    assert session.committed[5][1] == {
        "finding_uid": first_finding["finding_uid"],
        "canonical_observation_id": first_observation["finding_observation_id"],
    }
    assert result.finding_count == 2 and result.observation_count == 3
    assert result.findings[0].canonical_observation_id == first_observation["finding_observation_id"]
    assert tuple(member.source_proposal_ordinal for finding in result.findings
                 for member in finding.members) == (0, 2, 3)
    assert result.rejected == plan.rejected and result.rejected[0].proposal_ordinal == 1
    assert (result.malformed_count, result.salvaged) == (2, True)


@pytest.mark.parametrize("sqlstate,expected", [
    ("AM003", ErrorCode.STATE_TRANSITION_NOT_ALLOWED),
    ("23503", ErrorCode.INTERNAL_ERROR),
])
def test_db_refusal_rolls_back_all_groups_and_maps_sqlstate(sqlstate: str, expected: ErrorCode) -> None:
    session = _Session(fail_at=8, sqlstate=sqlstate)
    with pytest.raises(DomainError) as caught:
        publish_v2_merge_plan(session, plan=_plan(), context=_CONTEXT)
    assert caught.value.code == expected
    assert session.begin_count == 1 and session.rollback_count == 1
    assert session.pending == [] and session.committed == []


def test_missing_canonical_update_rolls_back_savepoint() -> None:
    session = _Session(canonical_rowcount=0)
    with pytest.raises(RuntimeError, match="v2_canonical_update_refused"):
        publish_v2_merge_plan(session, plan=_plan(), context=_CONTEXT)
    assert session.rollback_count == 1 and session.committed == []


def test_typed_plan_and_complete_group_are_required_before_id_allocation() -> None:
    session = _Session()
    with pytest.raises(ValueError, match="plan_required"):
        publish_v2_merge_plan(session, plan=object(), context=_CONTEXT)
    plan = _plan()
    forged = replace(plan, groups=(replace(plan.groups[0], members=()), *plan.groups[1:]))
    with pytest.raises(ValueError, match="group_invalid"):
        publish_v2_merge_plan(session, plan=forged, context=_CONTEXT)
    assert session.begin_count == 0 and session.executions == 0


@pytest.mark.parametrize("changed", [
    {"run_id": "run_invalid"},
    {"analysis_profile_id": "pb_invalid"},
    {"model_call_id": "mc_invalid"},
    {"provider_mode": "offline"},
])
def test_invalid_provenance_is_refused_before_id_allocation(changed: dict) -> None:
    session = _Session()
    with pytest.raises(ValueError):
        publish_v2_merge_plan(session, plan=_plan(), context=replace(_CONTEXT, **changed))
    assert session.begin_count == 0 and session.executions == 0


def test_all_rejected_proposals_allocate_no_identity() -> None:
    rejected = ProposalGroundingResult(
        (), (RejectedProposal(0, (UnresolvedEvidence(0, 1, "missing", "quotation_absent"),)),),
        0, False,
    )
    session = _Session()
    result = publish_v2_merge_plan(
        session, plan=plan_v2_merge_publication(rejected, prepare_merge(rejected)),
        context=_CONTEXT,
    )
    assert result.finding_count == 0 and result.observation_count == 0
    assert result.rejected == rejected.rejected
    assert session.begin_count == 1 and session.executions == 0
