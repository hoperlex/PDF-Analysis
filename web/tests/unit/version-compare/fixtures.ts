/**
 * The data of the version comparison screens, for the tests and the contrast census (`CMP-VC-UI-01`).
 *
 * One project, one document set of three versions whose matrix holds every kind of cell the screen draws, a series whose
 * transitions carry every verdict code, the sheet pairs of one transition in every status, the edit history in every
 * kind, status and source, an overview with a set in every step state, and the uploads in every state. The values are
 * invented; the identities are in the contract's shape (`<prefix>_<ULID>`) and differ by their last two digits.
 */

import type {
  ComparisonMatrix,
  ComparisonMatrixCell,
  ComparisonMatrixEdit,
  ComparisonMatrixRow,
  ComparisonOverview,
  ComparisonOverviewSet,
  ComparisonOverviewStep,
  ComparisonPageRef,
  ComparisonProposalSet,
  ComparisonQueueSummary,
  ComparisonSeries,
  ComparisonSheetPair,
  ComparisonStepId,
  ComparisonStepState,
  ComparisonTransition,
  ComparisonUpload,
  ComparisonUploadProposal,
} from '@/shared/api';
import { COMPARISON_STEP_STATE_VALUES } from '@/shared/api';

const BASE = '01J9ZQ8K7NHVXW3T2R5M6P4Q';
export const uid = (prefix: string, n: number): string => `${prefix}_${BASE}${String(n).padStart(2, '0')}`;

export const PROJECT_UID = uid('prj', 1);
export const DOCUMENT_UID = uid('doc', 1);
export const V1 = uid('ver', 1);
export const V2 = uid('ver', 2);
export const V3 = uid('ver', 3);
export const MATRIX_ID = uid('cmx', 1);
export const SERIES_ID = uid('cser', 1);
export const TRANSITION_12 = uid('ctn', 1);
export const TRANSITION_23 = uid('ctn', 2);
export const UPLOAD_ID = uid('cbt', 1);
export const NOW = '2026-10-28T10:15:30Z';

export function page(version: string, number: number): ComparisonPageRef {
  return { version_uid: version, page_number: number, page_profile_id: uid('cpr', Number(version.slice(-2)) * 10 + number) };
}

const matched = (v: string, n: number, extra: Partial<ComparisonMatrixCell> = {}): ComparisonMatrixCell => ({
  state: 'matched',
  version_uid: v,
  page: page(v, n),
  ...extra,
});
const unmatched = (v: string, extra: Partial<ComparisonMatrixCell> = {}): ComparisonMatrixCell => ({
  state: 'unmatched',
  version_uid: v,
  ...extra,
});
const absent = (v: string, extra: Partial<ComparisonMatrixCell> = {}): ComparisonMatrixCell => ({
  state: 'absent',
  version_uid: v,
  ...extra,
});

const row = (n: number, title: string, number: string | undefined, cells: ComparisonMatrixCell[]): ComparisonMatrixRow => ({
  row_id: uid('cpr', 90 + n),
  title,
  ...(number === undefined ? {} : { sheet_number: number }),
  cells,
});

/**
 * Seven rows. R1 an ordinary sheet; R2 a medium and a group match; R3 a manual link and an AI link; R4 a duplicate, a scan and a
 * sheet marked absent by hand; R5 a split sheet with a bridge; R6 a sheet whose newer cell is unmatched, with candidates, and
 * one with none; R7 a new sheet (no confidence on its first appearance).
 */
export function matrix(over: Partial<ComparisonMatrix> = {}): ComparisonMatrix {
  return {
    project_uid: PROJECT_UID,
    document_uid: DOCUMENT_UID,
    state: 'ready',
    progress: { ready: 24, total: 24, failed: 0 },
    revision: { matrix_id: MATRIX_ID, edit_no: 3 },
    built_at: NOW,
    columns: [
      { version_uid: V1, page_count: 7 },
      { version_uid: V2, page_count: 8 },
      { version_uid: V3, page_count: 10 },
    ],
    rows: [
      row(1, 'Общие данные', '1', [matched(V1, 1, { confidence: 'high' }), matched(V2, 1, { confidence: 'high' }), matched(V3, 1, { confidence: 'high' })]),
      row(2, 'План этажа 1', '2', [matched(V1, 2, { confidence: 'high' }), matched(V2, 2, { confidence: 'medium' }), matched(V3, 2, { confidence: 'group' })]),
      row(3, 'Схема электроснабжения', '3', [
        matched(V1, 3, { confidence: 'high' }),
        matched(V2, 3, { confidence: 'manual', edit_id: uid('cme', 1) }),
        matched(V3, 3, { confidence: 'ai', ai_link_id: uid('cak', 1) }),
      ]),
      row(4, 'Спецификация оборудования', '4', [
        matched(V1, 4, { confidence: 'high', flags: ['duplicate'] }),
        matched(V2, 4, { confidence: 'high', flags: ['scan'] }),
        absent(V3, { reason: 'marked_absent', edit_id: uid('cme', 2) }),
      ]),
      row(5, 'План кровли', '5', [
        matched(V1, 5, { confidence: 'high', flags: ['split'] }),
        matched(V2, 5, { confidence: 'high', flags: ['split'] }),
        matched(V3, 5, { confidence: 'medium', flags: ['split', 'bridge'] }),
      ]),
      row(6, 'Разрез 1-1', '6', [
        matched(V1, 6, { confidence: 'high' }),
        matched(V2, 6, { confidence: 'high' }),
        unmatched(V3, { reason: 'weak', candidates: [{ page: page(V3, 7), score: 0.41 }, { page: page(V3, 8), score: 0.33 }] }),
      ]),
      row(7, 'Узел 3', undefined, [
        absent(V1, { reason: 'no_candidates' }),
        unmatched(V2, { reason: 'below_pair' }),
        matched(V3, 9),
      ]),
      // The second part of the split sheet of row 5: its own row, no older sheet in it (the older sheet stands in row 5).
      row(8, 'План кровли, часть 2', '5', [
        absent(V1, { reason: 'no_candidates' }),
        absent(V2, { reason: 'no_candidates' }),
        matched(V3, 10, { confidence: 'high', flags: ['split'] }),
      ]),
    ],
    unassigned_pages: [page(V2, 8)],
    counts: { rows: 8, unmatched: 2, manual: 1, ai: 1, groups: 1, duplicates: 1 },
    orphaned_edit_ids: [uid('cme', 3)],
    ...over,
  };
}

/** The edit history in every kind, status and source. */
export function edits(): ComparisonMatrixEdit[] {
  const base = { created_at: NOW, created_by: uid('usr', 1), document_uid: DOCUMENT_UID };
  return [
    { ...base, edit_id: uid('cme', 1), edit_no: 1, kind: 'link', source: 'expert', status: 'applied', page: page(V2, 3), other_page: page(V1, 3) },
    { ...base, edit_id: uid('cme', 2), edit_no: 2, kind: 'mark_absent', source: 'expert', status: 'applied', page: page(V1, 4), absent_version_uid: V3 },
    { ...base, edit_id: uid('cme', 3), edit_no: 3, kind: 'unlink', source: 'expert', status: 'orphaned', page: page(V2, 8) },
    { ...base, edit_id: uid('cme', 4), edit_no: 4, kind: 'undo', source: 'expert', status: 'applied', undoes_edit_id: uid('cme', 3) },
    {
      ...base,
      edit_id: uid('cme', 5),
      edit_no: 5,
      kind: 'link',
      source: 'migrated_sheet_link',
      status: 'undone',
      page: page(V2, 2),
      other_page: page(V1, 2),
      provenance: { comparison_id: uid('cmp', 1), link_revision: 1, sheet_link_id: 'lnk_1' },
    },
  ];
}

const summaryOf = (over: Partial<ComparisonTransition['summary']> = {}): ComparisonTransition['summary'] => ({
  sheets: 7, compared: 7, same: 3, zones_only: 1, different: 2, style_only: 0, needs_review: 1, added: 0, removed: 0, failed: 0, ...over,
});

export function transition(over: Partial<ComparisonTransition> & Pick<ComparisonTransition, 'transition_id' | 'source_version_uid' | 'target_version_uid'>): ComparisonTransition {
  return { series_id: SERIES_ID, state: 'completed', items_done: 7, items_total: 7, summary: summaryOf(), verdict: ['different', 'needs_review'], ...over };
}

export function series(over: Partial<ComparisonSeries> = {}): ComparisonSeries {
  return {
    series_id: SERIES_ID,
    project_uid: PROJECT_UID,
    document_uid: DOCUMENT_UID,
    state: 'completed',
    created_at: NOW,
    updated_at: NOW,
    transitions_done: 2,
    transitions_total: 2,
    matrix_revision: { matrix_id: MATRIX_ID, edit_no: 3 },
    transitions: [
      transition({ transition_id: TRANSITION_12, source_version_uid: V1, target_version_uid: V2, summary: summaryOf({ different: 3, style_only: 1, added: 1, removed: 2, failed: 1, ai_dependent: 2 }), verdict: ['different', 'composition_changed', 'needs_review', 'calculation_failed'] }),
      transition({ transition_id: TRANSITION_23, source_version_uid: V2, target_version_uid: V3, summary: summaryOf({ different: 0, needs_review: 0, same: 6, zones_only: 1 }), verdict: ['content_same', 'zones_only'] }),
    ],
    ...over,
  };
}

/** The sheet pairs of №2 → №3, one in each of the seven statuses, matched to the rows of {@link matrix}, and the second part of the split sheet. */
export function pairs(): ComparisonSheetPair[] {
  const make = (n: number, over: Partial<ComparisonSheetPair>): ComparisonSheetPair => ({
    sheet_pair_id: uid('ctp', n),
    transition_id: TRANSITION_23,
    state: 'done',
    ...over,
  });
  return [
    make(1, { status: 'same', page_a: { page: page(V2, 1) }, page_b: { page: page(V3, 1) }, permit: { state: 'declared_and_found', items: [{ state: 'declared_and_found', text: 'Лист 1: изменён штамп' }] } }),
    make(2, { status: 'different', page_a: { page: page(V2, 2) }, page_b: { page: page(V3, 2) }, reasons: ['MATCH_LOW_CONFIDENCE', 'UNCHECKED_CHANNEL_TEXT_COVERAGE'], permit: { state: 'declared_no_diff' } }),
    make(3, { status: 'same_zones_changed', page_a: { page: page(V2, 3) }, page_b: { page: page(V3, 3) }, ai_dependent: true, permit: { state: 'diff_not_declared', items: [{ state: 'diff_not_declared', text: 'Лист 3: изменена схема' }] } }),
    make(4, { status: 'removed', page_a: { page: page(V2, 4) } }),
    make(5, { status: 'needs_review', page_a: { page: page(V2, 5) }, page_b: { page: page(V3, 5) }, reasons: ['SPLIT_SHEET', 'DUPLICATE_SHEET', 'AI_MATCH', 'NO_TEXT_LAYER', 'A_CODE_FROM_THE_FUTURE'], permit: { state: 'needs_review' }, parts: { role: 'whole', covered_percent: 100, parts: [page(V3, 5), page(V3, 10)] } }),
    make(6, { status: 'unmatched', page_a: { page: page(V2, 6) }, state: 'failed', failure_reason: 'post_phase_x' }),
    make(7, { status: 'added', page_b: { page: page(V3, 9) } }),
    make(8, { status: 'needs_review', page_a: { page: page(V2, 5) }, page_b: { page: page(V3, 10) }, reasons: ['SPLIT_SHEET'], parts: { role: 'part', covered_percent: 61.5, parts: [page(V3, 5), page(V3, 10)] } }),
  ];
}

const STEP_IDS: readonly ComparisonStepId[] = ['upload', 'profile', 'matrix', 'ai_pairs', 'series', 'ai_changes', 'report'];

function step(id: ComparisonStepId, state: ComparisonStepState, counts?: ComparisonOverviewStep['counts']): ComparisonOverviewStep {
  return counts === undefined ? { step: id, state } : { step: id, state, counts };
}

/** A set whose seven steps all have the same state, and the figures the shown ones quote. */
function setOf(n: number, designation: string | undefined, state: ComparisonStepState, over: Partial<ComparisonOverviewSet> = {}): ComparisonOverviewSet {
  return {
    document_uid: uid('doc', n),
    ...(designation === undefined ? {} : { designation }),
    version_count: 3 + n,
    updated_at: '2026-10-2' + (n % 10) + 'T09:00:00Z',
    steps: STEP_IDS.map((id) => {
      if (id === 'profile') return step(id, state, { ready: 20, total: 24, failed: state === 'failed' ? 2 : 0 });
      if (id === 'matrix') return step(id, state, { rows: 31, unmatched: 4, manual_edits: 2 });
      if (id === 'series') return step(id, state, { done: 2, total: 3, with_changes: 1 });
      if (id === 'upload') return step(id, state, { total: 3 + n });
      return step(id, state);
    }),
    ...over,
  };
}

/**
 * The step each set of {@link overview} proposes, by the state its steps all have (`next_step` of the contract). Every
 * step id is proposed once or more (the language guard needs the seven markers), and the proposed step has the state of
 * the whole set, so the group of a row (OVERVIEW section 6.3) is read off this table:
 *
 *   waiting: not_started, paused, interrupted, partial, stale, attention (6) · running: queued, running, pausing (3)
 *   failed: failed, whose proposed step is the profile (1) · ready: done, blocked, not_applicable (3)
 */
const NEXT_STEP_BY_STATE: Readonly<Partial<Record<ComparisonStepState, ComparisonStepId>>> = {
  not_started: 'upload',
  queued: 'profile',
  running: 'matrix',
  pausing: 'ai_pairs',
  paused: 'series',
  interrupted: 'ai_changes',
  partial: 'report',
  stale: 'series',
  attention: 'matrix',
  failed: 'profile',
};

/**
 * An overview holding a set in each of the thirteen step states (the same state in all seven steps of the set), so every state word
 * of the table and every next-step chip is on a screen, and the totals and counters the server would send: the counters are
 * written out for the table above, not computed from the rows.
 */
export function overview(over: Partial<ComparisonOverview> = {}): ComparisonOverview {
  const sets = COMPARISON_STEP_STATE_VALUES.map((state, index) => {
    const next = NEXT_STEP_BY_STATE[state];
    return setOf(index + 1, index === 12 ? undefined : `133/23-ГК-${['ЭМ', 'ТХ', 'АР', 'ОВ', 'ВК'][index % 5]}${index + 1}`, state, {
      ...(next === undefined ? {} : { next_step: next }),
      ...(index === 12 ? { title: 'Комплект без шифра', version_count: 1 } : {}),
    });
  });
  return {
    project_uid: PROJECT_UID,
    generated_at: NOW,
    sets,
    totals: { versions: 120, transitions: 90 },
    counters: { all: 13, waiting: 6, running: 3, failed: 1, ready: 3 },
    pending_uploads: [{ upload_id: UPLOAD_ID, state: 'uploading', declared_files: 12, sets_done: 1, sets_total: 4 }],
    ...over,
  };
}

export function queueSummary(over: Partial<ComparisonQueueSummary> = {}): ComparisonQueueSummary {
  const zero = { cancelled: 0, failed: 0, leased: 0, paused: 0, queued: 0, retry_wait: 0, running: 0, spend_unknown: 0, succeeded: 0 };
  return {
    modules: 'versions',
    paused: false,
    oldest_queued_at: '2026-10-28T08:00:00Z',
    counts: { ...zero, queued: 5, running: 2, failed: 1, succeeded: 40, spend_unknown: 1 },
    kinds: [
      { kind: 'page_profile', module: 'versions', counts: { ...zero, queued: 4, running: 1 } },
      { kind: 'matrix_build', module: 'versions', counts: { ...zero, queued: 1, failed: 1, leased: 1 } },
      { kind: 'stage_pairing', module: 'stages', counts: { ...zero } },
    ],
    ...over,
  };
}

export function upload(over: Partial<ComparisonUpload> = {}): ComparisonUpload {
  return {
    upload_id: UPLOAD_ID,
    project_uid: PROJECT_UID,
    state: 'proposed',
    part_size_bytes: 16 * 1024 * 1024,
    declared_files: 3,
    declared_bytes: 31_457_280,
    created_at: NOW,
    updated_at: NOW,
    files: [
      { file_id: uid('cuf', 1), display_name: 'ЭМ/Изм0.pdf', size_bytes: 10_485_760, sha256: 'a'.repeat(64), state: 'verified', parts_staged: 1, set_id: uid('cus', 1) },
      { file_id: uid('cuf', 2), display_name: 'ЭМ/Изм1.pdf', size_bytes: 10_485_760, sha256: 'b'.repeat(64), state: 'uploading', parts_staged: 0 },
      { file_id: uid('cuf', 3), display_name: 'ЭМ/Изм2.pdf', size_bytes: 10_485_760, sha256: 'c'.repeat(64), state: 'failed', parts_staged: 1, failure_reason: 'comparison_file_sha256' },
      { file_id: uid('cuf', 4), display_name: 'ЭМ/Изм3.pdf', size_bytes: 1_048_576, sha256: 'd'.repeat(64), state: 'declared', parts_staged: 0 },
      { file_id: uid('cuf', 5), display_name: 'ЭМ/скан.pdf', size_bytes: 1_048_576, sha256: 'e'.repeat(64), state: 'failed', parts_staged: 1, failure_reason: 'content_parseable_pdf' },
    ],
    ...over,
  };
}

const ALL_WARNINGS: NonNullable<ComparisonProposalSet['warnings']> = [
  'designations_differ',
  'order_disagrees_with_file_numbers',
  'duplicate_revision_number',
  'no_stamp_found',
  'scan_without_text',
];

/** Eight sets, one in each state, the third with every warning, an offered document, a stage and a section. */
export function proposalSets(): ComparisonProposalSet[] {
  const states = ['uploading', 'reading', 'needs_confirmation', 'ready', 'admitting', 'done', 'failed', 'excluded'] as const;
  return states.map((state, index) => ({
    set_id: uid('cus', index + 1),
    state,
    designation: `133/23-ГК-ЭМ${index + 1}`,
    files: [
      { file_id: uid('cuf', 1), position: 2, version_label: 'Версия 2 Изм.1 12.02.2026' },
      { file_id: uid('cuf', 2), position: 1, version_label: 'Версия 1 Изм.0 15.01.2026' },
    ],
    ...(index === 2
      ? {
          existing_document_uid: DOCUMENT_UID,
          project_stage: 'P' as const,
          section_code: 'EOM' as const,
          warnings: ALL_WARNINGS,
        }
      : {}),
    ...(state === 'failed' ? { failure_reason: 'comparison_sets_limit' } : {}),
  }));
}

export function proposal(over: Partial<ComparisonUploadProposal> = {}): ComparisonUploadProposal {
  return { upload_id: UPLOAD_ID, state: 'proposed', sets: proposalSets(), ...over };
}
