"""Offline projection of AR v2 publication plans into seeded evidence scoring.

Bundle identity is supplied by the harness with source digests; it cannot be
inferred from an observation, a file name, or a finding UID. Published rows
carry no quotes, so their ordinals are checked against the grounded plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from evaluation.matcher import EvidenceQuote, FindingMember, MatchReport, PredictedGroup, score


@dataclass(frozen=True, slots=True)
class SeededPlan:
    bundle_id: str
    pdf_sha256: str
    portal_bundle_sha256: str
    run_id: str
    plan: object
    publication: object | None = None


@dataclass(frozen=True, slots=True)
class RejectedDiagnostic:
    proposal_ordinal: int
    failures: tuple[tuple[int, int, str, str], ...]


@dataclass(frozen=True, slots=True)
class BundleDiagnostics:
    bundle_id: str
    run_id: str
    rejected: tuple[RejectedDiagnostic, ...]
    malformed_count: int
    salvaged: bool


@dataclass(frozen=True, slots=True)
class SeededScore:
    match: MatchReport
    diagnostics: tuple[BundleDiagnostics, ...]


def _required(value: object, name: str) -> object:
    try:
        return getattr(value, name)
    except AttributeError:
        raise ValueError(f"missing_{name}") from None


def _manifest_bundles(manifest: Mapping[str, object]) -> dict[str, tuple[str, str]]:
    if manifest.get("schema") != "ar-v2-seeded/1" or manifest.get("profile") != "ar_v2":
        raise ValueError("seeded_manifest_version_mismatch")
    raw = manifest.get("bundles")
    if not isinstance(raw, list) or not raw:
        raise ValueError("seeded_manifest_bundles_required")
    bundles: dict[str, tuple[str, str]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("seeded_manifest_bundle_invalid")
        identifier = item.get("id")
        pdf_digest = item.get("pdf_sha256")
        portal_digest = item.get("portal_bundle_sha256")
        if (not isinstance(identifier, str) or not identifier or identifier in bundles
                or not isinstance(pdf_digest, str) or len(pdf_digest) != 64
                or not isinstance(portal_digest, str) or len(portal_digest) != 64):
            raise ValueError("seeded_manifest_bundle_invalid")
        bundles[identifier] = (pdf_digest, portal_digest)
    return bundles


def _diagnostics(plan: object, *, bundle_id: str, run_id: str) -> BundleDiagnostics:
    rejected = _required(plan, "rejected")
    malformed = _required(plan, "malformed_count")
    salvaged = _required(plan, "salvaged")
    if (not isinstance(rejected, tuple) or type(malformed) is not int or malformed < 0
            or type(salvaged) is not bool):
        raise ValueError("plan_diagnostics_invalid")
    output: list[RejectedDiagnostic] = []
    for item in rejected:
        ordinal = _required(item, "proposal_ordinal")
        failures = _required(item, "failures")
        if type(ordinal) is not int or ordinal < 0 or not isinstance(failures, tuple) or not failures:
            raise ValueError("rejected_diagnostic_invalid")
        details = []
        for failure in failures:
            detail = tuple(_required(failure, field) for field in (
                "evidence_ordinal", "page_number", "quote", "reason"
            ))
            if (type(detail[0]) is not int or detail[0] < 0
                    or type(detail[1]) is not int or detail[1] < 1
                    or not isinstance(detail[2], str) or not detail[2]
                    or not isinstance(detail[3], str) or not detail[3]):
                raise ValueError("rejected_diagnostic_invalid")
            details.append(detail)
        output.append(RejectedDiagnostic(ordinal, tuple(details)))
    if len({item.proposal_ordinal for item in output}) != len(output):
        raise ValueError("rejected_diagnostic_duplicate")
    return BundleDiagnostics(bundle_id, run_id, tuple(output), malformed, salvaged)


def _project_plan(plan: object, bundle_id: str) -> tuple[PredictedGroup, ...]:
    groups = _required(plan, "groups")
    if not isinstance(groups, tuple):
        raise ValueError("plan_groups_invalid")
    output: list[PredictedGroup] = []
    ordinals: set[int] = set()
    source_ordinals: set[int] = set()
    for group in groups:
        category = _required(group, "category")
        members = _required(group, "members")
        canonical = _required(group, "canonical")
        if not isinstance(category, str) or not category or not isinstance(members, tuple) or not members or canonical not in members:
            raise ValueError("plan_group_invalid")
        projected_members: list[FindingMember] = []
        for member in members:
            ordinal = _required(member, "observation_ordinal")
            source = _required(member, "source_proposal_ordinal")
            proposal = _required(member, "proposal")
            evidence = _required(member, "evidence")
            if (type(ordinal) is not int or ordinal < 0 or ordinal in ordinals
                    or type(source) is not int or source < 0 or source in source_ordinals
                    or _required(proposal, "category") != category
                    or not isinstance(evidence, tuple) or not evidence):
                raise ValueError("plan_member_invalid")
            ordinals.add(ordinal)
            source_ordinals.add(source)
            quotes = []
            for anchor in evidence:
                page = _required(anchor, "page_number")
                quote = _required(anchor, "quote")
                start = _required(anchor, "char_start")
                end = _required(anchor, "char_end")
                if (type(page) is not int or page < 1 or not isinstance(quote, str) or not quote
                        or type(start) is not int or start < 0 or type(end) is not int
                        or end - start != len(quote)):
                    raise ValueError("plan_evidence_invalid")
                quotes.append(EvidenceQuote(page, quote))
            projected_members.append(FindingMember(tuple(quotes)))
        output.append(PredictedGroup(bundle_id, category, tuple(projected_members)))
    if ordinals != set(range(len(ordinals))):
        raise ValueError("plan_members_not_dense")
    return tuple(output)


def _check_source_partition(plan: object, diagnostics: BundleDiagnostics) -> None:
    accepted = [
        _required(member, "source_proposal_ordinal")
        for group in _required(plan, "groups")
        for member in _required(group, "members")
    ]
    rejected = [item.proposal_ordinal for item in diagnostics.rejected]
    if sorted((*accepted, *rejected)) != list(range(len(accepted) + len(rejected))):
        raise ValueError("plan_sources_not_partitioned")


def _check_publication(plan: object, publication: object, run_id: str) -> None:
    if _required(publication, "run_id") != run_id:
        raise ValueError("publication_run_mismatch")
    groups = _required(plan, "groups")
    findings = _required(publication, "findings")
    if not isinstance(findings, tuple) or len(findings) != len(groups):
        raise ValueError("publication_groups_mismatch")
    if (_required(publication, "rejected") != _required(plan, "rejected")
            or _required(publication, "malformed_count") != _required(plan, "malformed_count")
            or _required(publication, "salvaged") != _required(plan, "salvaged")):
        raise ValueError("publication_diagnostics_mismatch")
    finding_ids: set[str] = set()
    observation_ids: set[str] = set()
    for planned, published in zip(groups, findings, strict=True):
        finding_id = _required(published, "finding_uid")
        if not isinstance(finding_id, str) or not finding_id or finding_id in finding_ids:
            raise ValueError("publication_identity_invalid")
        finding_ids.add(finding_id)
        if _required(published, "category") != _required(planned, "category"):
            raise ValueError("publication_category_mismatch")
        members = _required(published, "members")
        if not isinstance(members, tuple) or len(members) != len(_required(planned, "members")):
            raise ValueError("publication_members_mismatch")
        canonical_id: str | None = None
        for expected, actual in zip(_required(planned, "members"), members, strict=True):
            observation_id = _required(actual, "finding_observation_id")
            if (not isinstance(observation_id, str) or not observation_id
                    or observation_id in observation_ids):
                raise ValueError("publication_identity_invalid")
            observation_ids.add(observation_id)
            if (_required(actual, "observation_ordinal") != _required(expected, "observation_ordinal")
                    or _required(actual, "source_proposal_ordinal") != _required(expected, "source_proposal_ordinal")
                    or _required(actual, "evidence_count") != len(_required(expected, "evidence"))):
                raise ValueError("publication_members_mismatch")
            if expected == _required(planned, "canonical"):
                canonical_id = observation_id
        if _required(published, "canonical_observation_id") != canonical_id:
            raise ValueError("publication_canonical_mismatch")


def score_seeded_plans(
    manifest: Mapping[str, object], runs: Sequence[SeededPlan]
) -> SeededScore:
    """Score grounded plans; optionally prove published groups map to the same plan.

    The harness must independently verify input bytes and digests. This pure
    bridge checks the supplied provenance against the committed manifest.
    """
    bundles = _manifest_bundles(manifest)
    seen_bundles: set[str] = set()
    seen_runs: set[str] = set()
    groups: list[PredictedGroup] = []
    diagnostics: list[BundleDiagnostics] = []
    for run in runs:
        if (not isinstance(run, SeededPlan) or not isinstance(run.bundle_id, str)
                or run.bundle_id not in bundles or run.bundle_id in seen_bundles
                or not isinstance(run.run_id, str) or not run.run_id or run.run_id in seen_runs):
            raise ValueError("seeded_bundle_provenance_required")
        if (run.pdf_sha256, run.portal_bundle_sha256) != bundles[run.bundle_id]:
            raise ValueError("seeded_bundle_digest_mismatch")
        seen_bundles.add(run.bundle_id)
        seen_runs.add(run.run_id)
        groups.extend(_project_plan(run.plan, run.bundle_id))
        bundle_diagnostics = _diagnostics(run.plan, bundle_id=run.bundle_id, run_id=run.run_id)
        _check_source_partition(run.plan, bundle_diagnostics)
        diagnostics.append(bundle_diagnostics)
        if run.publication is not None:
            _check_publication(run.plan, run.publication, run.run_id)
    # A partial harness run cannot masquerade as a full seeded evaluation.
    if seen_bundles != set(bundles):
        raise ValueError("seeded_bundle_coverage_incomplete")
    return SeededScore(score(manifest, tuple(groups)), tuple(diagnostics))
