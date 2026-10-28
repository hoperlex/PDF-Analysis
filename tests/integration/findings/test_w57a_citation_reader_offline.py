"""Offline readback probes for the unserved 0023 citation certificate."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.findings.citation_reader import (
    CitationReadRefused, read_verified_citations,
)


QUOTE = "Минимальная ширина прохода составляет 1,4 м"
PARAGRAPH = "Введение. " + QUOTE + ". Следующий пункт."


class _Mappings:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None


class _Session:
    def __init__(self, header, observations, citations):
        self.rows = [header, observations, citations]
        self.calls = 0

    def execute(self, statement, params):
        assert params == ({
            "run_id": "run_current", "version_uid": "ver_current", "profile_id": "ap_v3",
            # `AR-V3-DECISIONS-01`: the certifying stage is a bind; the default is the v1/v2 stage.
            "cite_stage_id": "norm_verification",
        } if self.calls == 0 else {"run_id": "run_current"})
        assert "INSERT" not in str(statement).upper()
        result = _Mappings(self.rows[self.calls])
        self.calls += 1
        return result


def _fixture():
    header = [{
        "run_id": "run_current", "project_uid": "prj_current",
        "version_uid": "ver_current", "analysis_profile_id": "ap_v3",
        "prompt_bundle_id": "pb_v3", "provider_mode": "recorded",
        "norms_snapshot_id": "ns_current", "norm_retrieval_set_id": "nrs_current",
        "run_state": "published", "set_state": "verified", "cite_status": "succeeded",
        "reviewed_content_key": "exact-corpus-key", "snapshot_content_key": "exact-corpus-key",
        "expected_set_sha256": "a" * 64, "observed_set_sha256": "a" * 64,
        "expected_catalogue_sha256": "b" * 64,
        "observed_catalogue_sha256": "b" * 64,
        "set_binding_count": 1, "catalogue_binding_count": 1,
    }]
    observations = [{
        "finding_uid": "fnd_one", "project_uid": "prj_current",
        "version_uid": "ver_current", "canonical_observation_id": "fobs_one",
        "finding_observation_id": "fobs_one", "observation_run_id": "run_current",
        "observation_finding_uid": "fnd_one", "stage_id": "text_analysis",
        "grounded": True, "category": "evacuation", "analysis_profile_id": "ap_v3",
        "prompt_bundle_id": "pb_v3", "provider_mode": "recorded",
        "norm_citation_count": 1, "required_value": "1,4 м", "stated_value": "1,2 м",
    }]
    citations = [{
        "finding_observation_id": "fobs_one", "citation_ordinal": 1,
        "run_id": "run_current", "norms_snapshot_id": "ns_current",
        "norm_retrieval_set_id": "nrs_current",
        "norm_document_id": "ndoc_one", "norm_paragraph_id": "npar_one",
        "quote": QUOTE, "char_start": PARAGRAPH.index(QUOTE),
        "char_length": len(QUOTE), "state": "verified",
        "document_snapshot_id": "ns_current", "resolved_document_id": "ndoc_one",
        "slug": "СП_54_2022__Свод_правил", "title": "Свод правил",
        "source_attribution": "consultant_plus", "source_pdf_binding_count": 1,
        "paragraph_snapshot_id": "ns_current", "paragraph_document_pk": 12,
        "document_pk": 12, "resolved_paragraph_id": "npar_one",
        "clause_number": "7.1.4", "page_label": 7,
        "paragraph_text": PARAGRAPH, "text_reliability": "reliable",
    }]
    return header, observations, citations


def _read(rows):
    session = _Session(*rows)
    result = read_verified_citations(
        session, run_id="run_current", version_uid="ver_current",
        profile_id="ap_v3",
    )
    assert session.calls == 3
    return result


def test_exact_persisted_partition_and_source_attribution():
    result = _read(_fixture())
    assert (result.run_id, result.version_uid, result.norms_snapshot_id,
            result.norm_retrieval_set_id) == (
        "run_current", "ver_current", "ns_current", "nrs_current",
    )
    assert len(result.findings) == 1
    partition = result.findings[0].canonical
    assert partition.citation_count == 1
    assert (partition.citations[0].designation, partition.citations[0].quote,
            partition.citations[0].source_attribution) == (
        "СП 54 2022", QUOTE, "consultant_plus",
    )


def test_certified_zero_is_distinct_from_missing_certificate():
    rows = _fixture()
    rows[1][0].update(category="layout", norm_citation_count=0,
                      required_value=None, stated_value=None)
    rows[2].clear()
    assert _read(rows).findings[0].canonical.citations == ()
    rows[1][0]["norm_citation_count"] = None
    with pytest.raises(CitationReadRefused, match="citation_partition_invalid"):
        _read(rows)


@pytest.mark.parametrize("group,key,value", [
    (0, "version_uid", "ver_other"),
    (0, "analysis_profile_id", "ap_v2"),
    (0, "run_state", "validating"),
    (0, "cite_status", "failed"),
    (0, "set_state", "rejected"),
    (0, "snapshot_content_key", "other-corpus-key"),
    (0, "observed_set_sha256", "c" * 64),
    (0, "catalogue_binding_count", 0),
    (0, "set_binding_count", 2),
    (1, "version_uid", "ver_other"),
    (1, "observation_run_id", "run_other"),
    (1, "analysis_profile_id", "ap_v2"),
    (1, "canonical_observation_id", "fobs_other"),
    (1, "norm_citation_count", 2),
    (1, "category", "unregistered_category"),
    (1, "required_value", ""),
    (2, "run_id", "run_other"),
    (2, "norms_snapshot_id", "ns_other"),
    (2, "norm_retrieval_set_id", "nrs_other"),
    (2, "document_snapshot_id", "ns_other"),
    (2, "paragraph_snapshot_id", "ns_other"),
    (2, "paragraph_document_pk", 99),
    (2, "text_reliability", "unreliable"),
    (2, "source_pdf_binding_count", 0),
    (2, "source_attribution", "invented"),
    (2, "quote", "Другая цитата с достаточной длиной"),
    (2, "char_start", 0),
    (2, "citation_ordinal", 2),
])
def test_forged_or_stale_persisted_fact_refuses(group, key, value):
    rows = deepcopy(_fixture())
    rows[group][0][key] = value
    with pytest.raises(CitationReadRefused):
        _read(rows)


def test_missing_run_refuses_before_other_queries():
    rows = _fixture()
    rows[0].clear()
    session = _Session(*rows)
    with pytest.raises(CitationReadRefused, match="run_or_v3_profile_unavailable"):
        read_verified_citations(session, run_id="run_current",
                                version_uid="ver_current", profile_id="ap_v3")
    assert session.calls == 1


def test_foreign_citation_observation_refuses():
    rows = _fixture()
    rows[2][0]["finding_observation_id"] = "fobs_other"
    with pytest.raises(CitationReadRefused, match="orphan_citation_partition"):
        _read(rows)
