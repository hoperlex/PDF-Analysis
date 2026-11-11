"""Offline readback probes for the unserved 0023 citation certificate."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.findings import citation_reader
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
            # The certifying stage is a bind; the default is the norm-verification stage.
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
        "grounding_kind": "text_span", "grounded": True, "category": "evacuation", "analysis_profile_id": "ap_v3",
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


# --- block findings (D-685) ---------------------------------------------------------------------
#
# A candidate finding of a ``one_list`` run stands on portal blocks. ``publish_candidate_groups`` writes its observations with
# ``grounding_kind = 'portal_block'``, ``stage_id`` ``block_analysis`` or ``finding_merge``, category ``drawing_discrepancy`` or
# ``cross_source`` and no norm citation. The reader gives such an observation an empty partition, and refuses what it refused before.

def _block_observation(finding_uid: str = "fnd_block", observation_id: str = "fobs_block", **changes):
    row = {
        "finding_uid": finding_uid, "project_uid": "prj_current",
        "version_uid": "ver_current", "canonical_observation_id": observation_id,
        "finding_observation_id": observation_id, "observation_run_id": "run_current",
        "observation_finding_uid": finding_uid, "stage_id": "block_analysis",
        "grounding_kind": "portal_block", "grounded": True,
        "category": "drawing_discrepancy", "analysis_profile_id": "ap_v3",
        "prompt_bundle_id": "pb_v3", "provider_mode": "recorded",
        "norm_citation_count": None, "required_value": None, "stated_value": None,
    }
    row.update(changes)
    return row


def _with_block(**changes):
    """The certified text finding of ``_fixture`` and one block finding beside it, in one run that pins a norm snapshot."""
    header, observations, citations = deepcopy(_fixture())
    observations.append(_block_observation(**changes))
    return header, observations, citations


@pytest.mark.parametrize("stage,category,count", [
    ("block_analysis", "drawing_discrepancy", None),
    ("finding_merge", "drawing_discrepancy", None),
    ("finding_merge", "cross_source", None),
    ("block_analysis", "drawing_discrepancy", 0),
])
def test_a_block_finding_has_an_empty_partition_beside_a_certified_text_finding(stage, category, count):
    result = _read(_with_block(stage_id=stage, category=category, norm_citation_count=count))
    by_uid = {finding.finding_uid: finding for finding in result.findings}
    assert set(by_uid) == {"fnd_one", "fnd_block"}
    block = by_uid["fnd_block"].canonical
    assert (block.finding_observation_id, block.citation_count, block.citations,
            block.required_value, block.stated_value) == ("fobs_block", 0, (), None, None)
    assert by_uid["fnd_block"].merged_observations == ()
    # the text finding's certified partition is read exactly as before
    assert by_uid["fnd_one"].canonical.citation_count == 1


def test_the_members_of_a_block_finding_each_have_an_empty_partition():
    header, observations, citations = _with_block()
    observations.append(_block_observation(observation_id="fobs_member", canonical_observation_id="fobs_block"))
    block = next(f for f in _read((header, observations, citations)).findings if f.finding_uid == "fnd_block")
    assert block.canonical.finding_observation_id == "fobs_block"
    assert [m.finding_observation_id for m in block.merged_observations] == ["fobs_member"]
    assert block.merged_observations[0].citations == ()


@pytest.mark.parametrize("changes,reason", [
    # a block observation comes from a block stage and no other
    ({"stage_id": "text_analysis"}, "finding_provenance_invalid"),
    ({"stage_id": "comprehensive_analysis"}, "finding_provenance_invalid"),
    ({"stage_id": ""}, "finding_provenance_invalid"),
    ({"grounding_kind": "unknown_kind"}, "finding_provenance_invalid"),
    ({"grounding_kind": None}, "finding_provenance_invalid"),
    # the provenance checks of a text observation hold for a block one
    ({"version_uid": "ver_other"}, "finding_provenance_invalid"),
    ({"project_uid": "prj_other"}, "finding_provenance_invalid"),
    ({"observation_run_id": "run_other"}, "finding_provenance_invalid"),
    ({"observation_finding_uid": "fnd_other"}, "finding_provenance_invalid"),
    ({"analysis_profile_id": "ap_v2"}, "finding_provenance_invalid"),
    ({"prompt_bundle_id": "pb_other"}, "finding_provenance_invalid"),
    ({"provider_mode": "live"}, "finding_provenance_invalid"),
    ({"grounded": False}, "finding_provenance_invalid"),
    # a block observation carries no norm claim
    ({"category": "evacuation"}, "citation_partition_invalid"),
    ({"category": "layout"}, "citation_partition_invalid"),
    ({"category": "unregistered_category"}, "citation_partition_invalid"),
    ({"norm_citation_count": 1}, "citation_partition_invalid"),
    ({"norm_citation_count": True}, "citation_partition_invalid"),
    ({"norm_citation_count": False}, "citation_partition_invalid"),
    ({"required_value": "1,4 м", "stated_value": "1,2 м"}, "citation_partition_invalid"),
    ({"required_value": "1,4 м"}, "citation_partition_invalid"),
])
def test_a_forged_or_stale_block_observation_refuses(changes, reason):
    with pytest.raises(CitationReadRefused, match=reason):
        _read(_with_block(**changes))


def test_a_citation_row_under_a_block_observation_refuses():
    header, observations, citations = deepcopy(_fixture())
    observations.append(_block_observation())
    foreign = deepcopy(citations[0])
    foreign["finding_observation_id"] = "fobs_block"
    with pytest.raises(CitationReadRefused, match="citation_partition_invalid"):
        _read((header, observations, [*citations, foreign]))


def test_the_header_checks_still_bind_a_run_that_has_only_block_findings():
    header, observations, citations = _with_block()
    observations.pop(0)
    citations.clear()
    assert [f.finding_uid for f in _read((header, observations, citations)).findings] == ["fnd_block"]
    for key, value in (("cite_status", "failed"), ("set_state", "rejected"), ("catalogue_binding_count", 0),
                       ("run_state", "validating"), ("snapshot_content_key", "other-corpus-key")):
        refused = deepcopy((header, observations, citations))
        refused[0][0][key] = value
        with pytest.raises(CitationReadRefused, match="verified_run_authority_invalid"):
            _read(refused)


@pytest.mark.parametrize("stage", ["block_analysis", "finding_merge", "comprehensive_analysis", "norm_verification", ""])
def test_a_text_observation_of_another_stage_is_still_refused(stage):
    rows = deepcopy(_fixture())
    rows[1][0]["stage_id"] = stage
    with pytest.raises(CitationReadRefused, match="finding_provenance_invalid"):
        _read(rows)


def test_a_text_observation_still_needs_its_certified_partition():
    rows = deepcopy(_fixture())
    rows[1][0]["norm_citation_count"] = None
    with pytest.raises(CitationReadRefused, match="citation_partition_invalid"):
        _read(rows)


def test_the_stage_guard_of_a_text_observation_is_load_bearing(monkeypatch):
    """The refusal above is the stage table's; widening the text row to a block stage turns it into a read, so it can fail."""
    rows = deepcopy(_fixture())
    rows[1][0]["stage_id"] = "block_analysis"
    with pytest.raises(CitationReadRefused, match="finding_provenance_invalid"):
        _read(deepcopy(rows))
    monkeypatch.setitem(citation_reader._STAGES_BY_GROUNDING, "text_span", frozenset({"text_analysis", "block_analysis"}))
    assert _read(rows).findings[0].canonical.citation_count == 1


def test_the_block_partition_guard_is_load_bearing(monkeypatch):
    """A block row with a norm category is refused by ``_BLOCK_CATEGORIES``; widening it turns the refusal into a read."""
    rows = _with_block(category="evacuation")
    with pytest.raises(CitationReadRefused, match="citation_partition_invalid"):
        _read(deepcopy(rows))
    monkeypatch.setattr(citation_reader, "_BLOCK_CATEGORIES", frozenset({"drawing_discrepancy", "cross_source", "evacuation"}))
    assert _read(rows).findings[1].canonical.citations == ()
