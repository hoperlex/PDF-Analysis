"""W57a's independent citation and certified-zero contract pins; no services needed."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from auditmanager.api.schemas import models
from auditmanager.api.schemas.findings import (
    EvidenceView, FindingView, ObservationView, ProvenanceView, finding_body,
    observation_body,
)
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.findings.grounding import UNGROUNDED_REASONS

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / 'contracts/api/v1/openapi.json').read_text())
CATEGORIES_0023 = (
    'internal_contradiction', 'explicit_placeholder', 'dimensions', 'layout', 'facade',
    'roof', 'documentation', 'evacuation', 'fire_safety', 'accessibility', 'insulation', 'sound',
)
#: `CRIT-SEAL-50` (contract 1.51.0, migration 0064): the two categories of the groups of candidates.
#: `CRIT-SEAL-53` (contract 1.53.0, migration 0066) adds the category of a parameter stated differently in two documents.
CATEGORIES = (*CATEGORIES_0023, 'drawing_discrepancy', 'cross_source', 'parameter_mismatch')
REASONS_0023 = (
    'quotation_absent', 'quotation_on_different_page', 'span_outside_page',
    'span_outside_block', 'span_length_mismatch', 'quote_in_recognised_text',
    'norm_label_unknown', 'norm_quote_too_short', 'norm_quote_ambiguous',
    'norm_quote_absent', 'norm_value_not_in_quote', 'stated_value_not_in_evidence',
)
#: `CRIT-SEAL-50`: the three refusals of the gate of block evidence, in `ck_finding_observation_ungrounded_reason` since `0064`. The contract carries
#: no `UngroundedReason` (the AR v3 removal took it); the gate's own vocabulary (`findings.grounding.UNGROUNDED_REASONS`) takes the three since
#: `F8-GATE` wrote the gate of block evidence.
REASONS = (*REASONS_0023, 'block_not_in_run_geometry', 'block_crop_mismatch', 'block_quote_not_in_recognised')


def test_closed_vocabularies_match_0023() -> None:
    schemas = CONTRACT['components']['schemas']
    assert schemas['FindingCategory']['enum'] == list(CATEGORIES)
    assert {item.value for item in models.FindingCategory} == set(CATEGORIES)
    assert UNGROUNDED_REASONS == set(REASONS)  # F8-GATE: the gate's vocabulary takes the three refusals of block evidence
    source = (ROOT / 'db/migrations/versions/20261016_0023_norm_citations.py').read_text()
    for value in CATEGORIES_0023[7:] + REASONS_0023[6:]:
        assert f'"{value}"' in source
    # the two vocabularies 0064 adds are in the migration that adds them
    later = (ROOT / 'db/migrations/versions/20261110_0064_precedents_seal.py').read_text()
    for value in CATEGORIES[12:] + REASONS[12:]:
        assert f'"{value}"' in later


def test_citation_schema_rejects_short_quote_and_bad_identity() -> None:
    citation = {
        'norms_snapshot_id': 'ns_01M2545JSD15ETSNNV904X991N',
        'norm_document_id': 'ndoc_01M2545JSD15ETSNNV904X991V',
        'norm_paragraph_id': 'npar_01M2545JSD15ETSNNV904X991W',
        'designation': 'СП 54', 'title': 'Title', 'clause_number': None,
        'page_label': 1, 'quote': 'Достаточно длинная цитата нормы',
        'state': 'verified', 'source_attribution': 'consultant_plus',
    }
    assert models.NormCitation.model_validate(citation).quote == citation['quote']
    with pytest.raises(ValidationError):
        models.NormCitation.model_validate({**citation, 'quote': 'коротко'})
    with pytest.raises(ValidationError):
        models.NormCitation.model_validate({**citation, 'norm_paragraph_id': 'filename.pdf'})


def _observation(*, citations=None, certified=False) -> ObservationView:
    return ObservationView(
        finding_observation_id='fobs_01M2545JSD15ETSNNV904X991Q',
        run_id='run_01M2545JSD15ETSNNV904X991K',
        category='documentation', finding_text='Finding', recommendation_text='Fix',
        evidence=(EvidenceView(0, 1, 'Quote', 0, 5),),
        provenance=ProvenanceView(
            stage_id='text_analysis', analysis_profile_id='ap_01M2545JSD15ETSNNV904X991P',
            prompt_bundle_id='pb_01M2545JSD15ETSNNV904X991B', provider_mode='recorded',
        ),
        norm_citations=() if certified else citations,
    )


def test_legacy_omits_new_properties_and_certified_zero_is_array() -> None:
    legacy = observation_body(_observation())
    certified = observation_body(_observation(certified=True))
    assert {'norm_citations', 'required_value', 'stated_value'}.isdisjoint(legacy)
    assert certified['norm_citations'] == []
    finding = FindingView(
        finding_uid='fnd_01M2545JSD15ETSNNV904X991M',
        project_uid='prj_01M2545JSD15ETSNNV904X991F',
        version_uid='ver_01M2545JSD15ETSNNV904X991J',
        run_id='run_01M2545JSD15ETSNNV904X991K', category='documentation',
        observation=_observation(certified=True), current_verdict='pending',
    )
    body = finding_body(finding)
    assert body['norm_citations'] == body['observation']['norm_citations'] == []
    assert 'norm_citations' not in finding_body(
        FindingView(
            finding_uid=finding.finding_uid, project_uid=finding.project_uid,
            version_uid=finding.version_uid, run_id=finding.run_id,
            category=finding.category, observation=_observation(), current_verdict='pending',
        )
    )


def test_run_pin_is_absent_on_legacy_and_explicit_when_present() -> None:
    view = RunStatusView(
        run_id='run_01M2545JSD15ETSNNV904X991K',
        project_uid='prj_01M2545JSD15ETSNNV904X991F',
        version_uid='ver_01M2545JSD15ETSNNV904X991J',
        state='queued', provider_mode='recorded', created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
    )
    assert 'norm_retrieval_set_id' not in run_status_body(view)
    from dataclasses import replace
    pinned = replace(view, norm_retrieval_set_id='nrs_01M2545JSD15ETSNNV904X991N')
    assert run_status_body(pinned)['norm_retrieval_set_id'] == pinned.norm_retrieval_set_id


def test_stage_registry_has_one_norm_verification_and_optional_v3_input() -> None:
    registry = json.loads((ROOT / 'contracts/analysis/v1/stage-registry.json').read_text())
    stages = registry['stages']
    assert sum(stage['stage_id'] == 'norm_verification' for stage in stages) == 1
    text = next(stage for stage in stages if stage['stage_id'] == 'text_analysis')
    assert text['stage_version'] == '1.1.0'
    assert [input_ for input_ in text['required_inputs'] if input_['role'] == 'norms.snapshot'] == [{
        'role': 'norms.snapshot', 'media_type': 'application/json', 'required': False,
        'description': 'Optional pinned qualified norms snapshot and verified retrieval set; no current text profile consumes it. An absent verified set never silently falls back.',
    }]
