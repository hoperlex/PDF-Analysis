/**
 * Fixtures of the decision memory's answers (`D-495`): a case summary, a whole case, the counts. Shaped as the contract's
 * schemas, Cyrillic where the server would send the expert's words.
 */

import type {
  DecisionMemoryCase,
  DecisionMemoryCaseSummary,
  DecisionMemoryStatus,
} from '@/shared/api';

const ULID = '01M2545JSD15ETSNNV904X991F';

export const CASE_A = `dmc_${ULID}`;
export const CASE_B = 'dmc_01M2545JSD15ETSNNV904X992A';
export const CASE_C = 'dmc_01M2545JSD15ETSNNV904X993B';
export const PROJECT = `prj_${ULID}`;

export function summary(over: Partial<DecisionMemoryCaseSummary> = {}): DecisionMemoryCaseSummary {
  return {
    case_id: CASE_A,
    category: 'internal_contradiction',
    section_code: 'AR',
    data_class: 'test',
    crop_state: 'referenced',
    origin_project_uid: PROJECT,
    captured_at: '2026-11-09T09:00:00Z',
    status: 'active',
    status_reason_code: null,
    status_changed_at: null,
    current_verdict: 'accepted',
    current_severity: 'critical',
    current_origin_kind: 'direct',
    current_decided_at: '2026-11-09T09:00:00Z',
    decision_count: 1,
    ...over,
  };
}

export function wholeCase(over: Partial<DecisionMemoryCase> = {}, summaryOver: Partial<DecisionMemoryCaseSummary> = {}): DecisionMemoryCase {
  return {
    summary: summary(summaryOver),
    content: {
      finding_text: 'Отметка пола в плане не совпадает с отметкой на разрезе.',
      recommendation_text: 'Привести отметки к одному значению.',
      proposed_severity: 'critical',
      required_value: '+0,150',
      stated_value: '+0,300',
      stage_id: 'document_context_build',
      analysis_profile_id: 'ap_01M2545JSD15ETSNNV904X991F',
      provider_mode: 'recorded',
    },
    decisions: [
      {
        memory_decision_id: 'dmd_01M2545JSD15ETSNNV904X994C',
        event_type: 'accept',
        verdict: 'accepted',
        severity: 'critical',
        origin_kind: 'direct',
        decided_at: '2026-11-09T09:00:00Z',
        comment: 'Подтверждаю: отметки расходятся.',
      },
    ],
    evidence: [
      {
        ordinal: 0,
        page_number: 3,
        quote: 'Отметка пола +0,300',
        char_start: 10,
        char_end: 30,
        block_ref: 'b_000012',
        bbox: [72, 120.4567, 300, 140],
        bbox_unit: 'pt',
        bbox_origin: 'top_left',
      },
    ],
    norm_refs: [
      {
        ordinal: 1,
        norm_document_id: 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as never,
        norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as never,
        designation: 'СП 54.13330.2022',
        clause_number: '5.2',
        page_label: 7,
        quote: 'Отметки пола должны быть указаны на планах и разрезах согласованно.',
        citation_state: 'verified',
      },
    ],
    crops: [
      {
        crop_id: 'dmx_01M2545JSD15ETSNNV904X995D',
        crop_ordinal: 1,
        evidence_ordinal: 0,
        selection_rule: 'page_images/1',
        page_number: 3,
        bbox: [0.1, 0.2, 0.6, 0.7],
        media_type: 'image/png',
        sha256: 'a'.repeat(64),
        size_bytes: 20480,
        width_px: 640,
        height_px: 480,
        portal_description: 'Фрагмент плана первого этажа',
      },
    ],
    status_events: [],
    ...over,
  };
}

export const COUNTS: DecisionMemoryStatus = {
  data_class: 'test',
  training_use: 'off',
  cases: 5,
  decisions: 7,
  by_status_and_class: [
    { status: 'active', data_class: 'test', cases: 4 },
    { status: 'withdrawn', data_class: 'test', cases: 1 },
  ],
};
