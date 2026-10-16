"""The offline bridge scores grounded plans without a live provider or database."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from auditmanager.analysis.public import (
    ProposalGroundingResult, ProposedObservation, ResolvedAnchor, prepare_merge,
)
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    GroundedProposal, RejectedProposal, UnresolvedEvidence,
)
from auditmanager.analysis.profiles.ar_v2.response import ProposedEvidence
from auditmanager.findings.merge_publication_plan import plan_v2_merge_publication
from auditmanager.findings.v2_publication import (
    PublishedV2Finding, PublishedV2Observation, V2PublicationResult,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from evaluation.bridge import SeededPlan, score_seeded_plans  # noqa: E402

MANIFEST = json.loads(
    (ROOT / "fixtures/evaluation/ar_v2/expected_issues.json").read_text(encoding="utf-8")
)


def _proposal(case: dict, ordinal: int, start: int) -> GroundedProposal:
    page = case["evidence"][0]["page"]
    quote = case["evidence"][0]["quote"]
    proposal = ProposedObservation(
        case["category"], f"Finding {ordinal}", "Check drawing", "operational",
        (ProposedEvidence(page, quote),),
    )
    return GroundedProposal(ordinal, proposal, (ResolvedAnchor(page, quote, start, start + len(quote)),))


def _runs(*, omit: str | None = None, any_member: bool = False) -> tuple[SeededPlan, ...]:
    runs = []
    for bundle in MANIFEST["bundles"]:
        cases = [item for item in MANIFEST["issues"] if item["bundle_id"] == bundle["id"] and item["id"] != omit]
        accepted = []
        for case in cases:
            if any_member and case["id"] == "ic_area":
                # Same source span makes the rule merge the two observations;
                # only the second member cites the seeded issue.
                wrong = dict(case, evidence=[{"page": 1, "quote": "Совсем другая цитата на том же листе"}])
                accepted.append(_proposal(wrong, len(accepted), 100))
                accepted.append(_proposal(case, len(accepted), 100))
            else:
                accepted.append(_proposal(case, len(accepted), 1000 * (len(accepted) + 1)))
        rejected = ()
        if bundle["id"] == "ar_v2_01":
            rejected = (RejectedProposal(
                len(accepted), (UnresolvedEvidence(0, 1, "не найдена", "quotation_absent"),)
            ),)
        grounding = ProposalGroundingResult(tuple(accepted), rejected, 1 if rejected else 0, False)
        plan = plan_v2_merge_publication(grounding, prepare_merge(grounding))
        runs.append(SeededPlan(
            bundle["id"], bundle["pdf_sha256"], bundle["portal_bundle_sha256"],
            f"run-{bundle['id']}", plan,
        ))
    return tuple(runs)


def _published(run: SeededPlan) -> V2PublicationResult:
    findings = []
    for group_index, group in enumerate(run.plan.groups):
        members = tuple(
            PublishedV2Observation(
                f"observation-{run.bundle_id}-{group_index}-{index}", member.observation_ordinal,
                member.source_proposal_ordinal, len(member.evidence),
            )
            for index, member in enumerate(group.members)
        )
        canonical_index = group.members.index(group.canonical)
        findings.append(PublishedV2Finding(
            f"finding-{run.bundle_id}-{group_index}", group.category,
            members[canonical_index].finding_observation_id, members,
        ))
    return V2PublicationResult(
        run.run_id, tuple(findings), run.plan.rejected,
        run.plan.malformed_count, run.plan.salvaged,
    )


def test_all_seeded_plans_score_and_keep_rejected_diagnostics() -> None:
    scored = score_seeded_plans(MANIFEST, _runs())
    assert scored.match.recall == 1.0
    assert scored.match.missed_issue_ids == ()
    assert scored.match.control_false_positive_rate == 0.0
    assert scored.match.finding_group_count == 21
    assert scored.diagnostics[0].rejected[0].failures == (
        (0, 1, "не найдена", "quotation_absent"),
    )
    assert scored.diagnostics[0].malformed_count == 1
    assert scored.match.overmerged_groups == ()


def test_one_removed_seeded_issue_lowers_recall() -> None:
    complete = score_seeded_plans(MANIFEST, _runs())
    doctored = score_seeded_plans(MANIFEST, _runs(omit="ic_area"))
    assert complete.match.recall == 1.0
    assert doctored.match.recall == 20 / 21
    assert doctored.match.missed_issue_ids == ("ic_area",)


def test_any_group_member_can_match_and_published_ordinals_are_checked() -> None:
    runs = _runs(any_member=True)
    first = runs[0]
    publication = _published(first)
    scored = score_seeded_plans(MANIFEST, (replace(first, publication=publication), *runs[1:]))
    assert scored.match.recall == 1.0
    assert scored.match.finding_group_count == 21
    assert first.plan.groups[0].members[0].evidence[0].quote != MANIFEST["issues"][0]["evidence"][0]["quote"]
    broken = replace(publication, findings=(
        replace(publication.findings[0], canonical_observation_id="wrong"),
        *publication.findings[1:],
    ))
    with pytest.raises(ValueError, match="publication_canonical_mismatch"):
        score_seeded_plans(MANIFEST, (replace(first, publication=broken), *runs[1:]))


def test_missing_or_false_bundle_provenance_is_refused() -> None:
    runs = _runs()
    with pytest.raises(ValueError, match="seeded_bundle_coverage_incomplete"):
        score_seeded_plans(MANIFEST, runs[:-1])
    with pytest.raises(ValueError, match="seeded_bundle_digest_mismatch"):
        score_seeded_plans(MANIFEST, (replace(runs[0], pdf_sha256="0" * 64), *runs[1:]))
    with pytest.raises(ValueError, match="seeded_bundle_provenance_required"):
        score_seeded_plans(MANIFEST, (replace(runs[0], bundle_id=""), *runs[1:]))
    with pytest.raises(ValueError, match="seeded_bundle_provenance_required"):
        score_seeded_plans(MANIFEST, (*runs, runs[0]))


def test_published_group_member_loss_cannot_score_its_plan() -> None:
    runs = _runs(any_member=True)
    first = runs[0]
    publication = _published(first)
    first_finding = publication.findings[0]
    broken_finding = replace(first_finding, members=first_finding.members[:1])
    broken = replace(publication, findings=(broken_finding, *publication.findings[1:]))
    with pytest.raises(ValueError, match="publication_members_mismatch"):
        score_seeded_plans(MANIFEST, (replace(first, publication=broken), *runs[1:]))


def test_all_published_runs_with_distinct_ids_keep_the_same_score() -> None:
    runs = tuple(replace(run, publication=_published(run)) for run in _runs())
    scored = score_seeded_plans(MANIFEST, runs)
    assert scored.match.recall == 1.0
    assert scored.match.finding_group_count == 21
    assert scored.match.control_false_positive_rate == 0.0


def test_published_finding_id_cannot_repeat_across_runs() -> None:
    runs = tuple(replace(run, publication=_published(run)) for run in _runs())
    first_id = runs[0].publication.findings[0].finding_uid
    second = runs[1]
    second_finding = second.publication.findings[0]
    duplicate = replace(second_finding, finding_uid=first_id)
    changed_publication = replace(
        second.publication, findings=(duplicate, *second.publication.findings[1:]),
    )
    with pytest.raises(ValueError, match="publication_identity_invalid"):
        score_seeded_plans(MANIFEST, (
            runs[0], replace(second, publication=changed_publication), *runs[2:],
        ))


def test_published_observation_id_cannot_repeat_across_runs() -> None:
    runs = tuple(replace(run, publication=_published(run)) for run in _runs())
    first_id = runs[0].publication.findings[0].members[0].finding_observation_id
    second = runs[1]
    second_finding = second.publication.findings[0]
    old_id = second_finding.members[0].finding_observation_id
    duplicate = replace(second_finding.members[0], finding_observation_id=first_id)
    changed_finding = replace(
        second_finding,
        members=(duplicate, *second_finding.members[1:]),
        canonical_observation_id=(
            first_id if second_finding.canonical_observation_id == old_id
            else second_finding.canonical_observation_id
        ),
    )
    changed_publication = replace(
        second.publication, findings=(changed_finding, *second.publication.findings[1:]),
    )
    with pytest.raises(ValueError, match="publication_identity_invalid"):
        score_seeded_plans(MANIFEST, (
            runs[0], replace(second, publication=changed_publication), *runs[2:],
        ))


def test_rejected_proposal_cannot_reenter_predicted_members() -> None:
    runs = _runs()
    first = runs[0]
    leaked = replace(first.plan, rejected=(replace(first.plan.rejected[0], proposal_ordinal=0),))
    with pytest.raises(ValueError, match="plan_sources_not_partitioned"):
        score_seeded_plans(MANIFEST, (replace(first, plan=leaked), *runs[1:]))
