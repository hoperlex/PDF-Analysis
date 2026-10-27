"""Offline proof of the unserved W57a report context read."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.findings.citation_reader import VerifiedCitationRead
from auditmanager.findings.citation_report import (
    CitationReportRefused,
    read_verified_citation_report,
)


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, context, diagnostics, stages):
        self.rows = [context, diagnostics, stages]
        self.calls = 0

    def execute(self, statement, params):
        assert str(statement).lstrip().startswith("SELECT")
        assert params == ({
            "run_id": "run_exact", "version_uid": "ver_exact", "profile_id": "ap_v3",
        } if self.calls == 0 else {"run_id": "run_exact"})
        result = _Rows(self.rows[self.calls])
        self.calls += 1
        return result


def _facts():
    context = [{
        "run_id": "run_exact", "version_uid": "ver_exact",
        "analysis_profile_id": "ap_v3", "prompt_bundle_id": "pb_v3",
        "provider_mode": "recorded", "run_state": "published",
        "norms_snapshot_id": "ns_exact", "norm_retrieval_set_id": "nrs_exact",
        "page_count": 4, "textless_pages": [2, 4],
    }]
    diagnostics = [{
        "finding_observation_id": "fobs_rejected", "run_id": "run_exact",
        "stage_id": "text_analysis", "finding_uid": None, "grounded": False,
        "ungrounded_reason": "norm_quote_absent", "analysis_profile_id": "ap_v3",
        "prompt_bundle_id": "pb_v3", "provider_mode": "recorded",
    }]
    stages = [
        {"stage_id": "norm_verification", "status": "succeeded", "error": None},
        {"stage_id": "text_analysis", "status": "succeeded", "error": None},
    ]
    return context, diagnostics, stages


def _read(monkeypatch, facts, cite_stage_id="norm_verification"):
    expected = VerifiedCitationRead(
        run_id="run_exact", project_uid="prj_exact", version_uid="ver_exact",
        norms_snapshot_id="ns_exact", norm_retrieval_set_id="nrs_exact",
        run_state="published", findings=(),
    )
    def _certified(session, *, run_id, version_uid, profile_id, cite_stage_id):
        assert (run_id, version_uid, profile_id) == (
            "run_exact", "ver_exact", "ap_v3",
        )
        # `AR-V3-DECISIONS-01`: the certifying stage is passed through, never defaulted away.
        assert cite_stage_id == expected_stage
        return expected
    monkeypatch.setattr(
        "auditmanager.findings.citation_report.read_verified_citations", _certified,
    )
    expected_stage = cite_stage_id
    session = _Session(*facts)
    report = read_verified_citation_report(
        session, run_id="run_exact", version_uid="ver_exact", profile_id="ap_v3",
        cite_stage_id=cite_stage_id,
    )
    assert session.calls == 3
    return report


def test_persisted_diagnostics_are_counted_separately_from_verified_findings(monkeypatch):
    report = _read(monkeypatch, _facts())
    assert report.findings == ()
    assert report.withheld_by_reason == (("norm_quote_absent", 1),)
    assert report.textless_pages == (2, 4)
    assert (report.status, report.error_code) == ("complete", None)


def test_the_default_certifying_stage_is_norm_verification(monkeypatch):
    """The call that names no stage (the W57a callers) still reads ``norm_verification``."""
    expected = VerifiedCitationRead(
        run_id="run_exact", project_uid="prj_exact", version_uid="ver_exact",
        norms_snapshot_id="ns_exact", norm_retrieval_set_id="nrs_exact",
        run_state="published", findings=(),
    )
    seen = {}

    def _certified(session, **kwargs):
        seen.update(kwargs)
        return expected

    monkeypatch.setattr(
        "auditmanager.findings.citation_report.read_verified_citations", _certified,
    )
    read_verified_citation_report(
        _Session(*_facts()), run_id="run_exact", version_uid="ver_exact", profile_id="ap_v3",
    )
    assert seen["cite_stage_id"] == "norm_verification"


def test_the_ar_v3_stage_certifies_when_named_and_the_v1_stage_row_does_not_stand_in(monkeypatch):
    facts = _facts()
    facts[2][0]["stage_id"] = "ar_v3_citation_review"
    report = _read(monkeypatch, facts, cite_stage_id="ar_v3_citation_review")
    assert (report.status, report.error_code) == ("complete", None)
    # The same rows read for the default stage are refused: exactly one succeeded certifying stage.
    with pytest.raises(CitationReportRefused, match="report_stage_status_invalid"):
        _read(monkeypatch, _facts_with_stage("ar_v3_citation_review"), cite_stage_id="norm_verification")
    with pytest.raises(CitationReportRefused, match="report_stage_status_invalid"):
        _read(monkeypatch, _facts_with_stage("norm_verification"), cite_stage_id="ar_v3_citation_review")


def _facts_with_stage(stage_id):
    facts = _facts()
    facts[2][0]["stage_id"] = stage_id
    return facts


def test_partial_stage_reports_its_typed_error(monkeypatch):
    facts = _facts()
    facts[0][0]["run_state"] = "partial"
    facts[2][1].update(status="partial", error={"code": "analysis_failed"})
    expected = VerifiedCitationRead(
        run_id="run_exact", project_uid="prj_exact", version_uid="ver_exact",
        norms_snapshot_id="ns_exact", norm_retrieval_set_id="nrs_exact",
        run_state="partial", findings=(),
    )
    monkeypatch.setattr(
        "auditmanager.findings.citation_report.read_verified_citations",
        lambda *_args, **_kwargs: expected,
    )
    report = read_verified_citation_report(
        _Session(*facts), run_id="run_exact", version_uid="ver_exact",
        profile_id="ap_v3",
    )
    assert (report.status, report.error_code) == ("partial", "analysis_failed")


@pytest.mark.parametrize("group,key,value", [
    (0, "norm_retrieval_set_id", "nrs_foreign"),
    (0, "textless_pages", None),
    (0, "textless_pages", [4, 2]),
    (1, "run_id", "run_foreign"),
    (1, "finding_uid", "fnd_published"),
    (1, "ungrounded_reason", "unknown_reason"),
    (2, "status", "failed"),
])
def test_foreign_or_uncertified_context_refuses(monkeypatch, group, key, value):
    facts = deepcopy(_facts())
    facts[group][0][key] = value
    with pytest.raises(CitationReportRefused):
        _read(monkeypatch, facts)


def test_empty_diagnostic_query_is_zero_only_after_citation_certification(monkeypatch):
    facts = _facts()
    facts[1].clear()
    assert _read(monkeypatch, facts).withheld_by_reason == ()
    def _refuse(*_args, **_kwargs):
        raise ValueError("citation_certificate_missing")
    monkeypatch.setattr(
        "auditmanager.findings.citation_report.read_verified_citations", _refuse,
    )
    session = _Session(*facts)
    with pytest.raises(ValueError, match="citation_certificate_missing"):
        read_verified_citation_report(
            session, run_id="run_exact", version_uid="ver_exact", profile_id="ap_v3",
        )
    assert session.calls == 0


def test_two_different_partial_errors_refuse_an_arbitrary_report_code(monkeypatch):
    facts = _facts()
    facts[0][0]["run_state"] = "partial"
    facts[2][1].update(status="partial", error={"code": "analysis_failed"})
    facts[2].append({
        "stage_id": "finding_merge", "status": "partial",
        "error": {"code": "dependency_unavailable"},
    })
    expected = VerifiedCitationRead(
        run_id="run_exact", project_uid="prj_exact", version_uid="ver_exact",
        norms_snapshot_id="ns_exact", norm_retrieval_set_id="nrs_exact",
        run_state="partial", findings=(),
    )
    monkeypatch.setattr(
        "auditmanager.findings.citation_report.read_verified_citations",
        lambda *_args, **_kwargs: expected,
    )
    with pytest.raises(CitationReportRefused, match="partial_stage_error_ambiguous"):
        read_verified_citation_report(
            _Session(*facts), run_id="run_exact", version_uid="ver_exact",
            profile_id="ap_v3",
        )
