/**
 * The data of the AI layer of «Сравнение версий», for the tests and the contrast census (`CMP-VC-UI-02`).
 *
 * Invented, in the contract's shape; Cyrillic wherever the server's own words appear (a model name, a sentence a model wrote),
 * like every seed of the language guard. Each builder takes the fields a test varies; `*_VALUES` of the generated client drive
 * the "one of each state" lists so a member the contract adds is a shape the guard asks for.
 */

import type {
  ComparisonAiEstimate,
  ComparisonAiJob,
  ComparisonAiPairHint,
  ComparisonAiQueue,
  ComparisonAiQueueItem,
  ComparisonAiSheetChanges,
  ComparisonLaunchEntry,
  ComparisonLaunchQueue,
  ComparisonReport,
  ComparisonReportPart,
  ComparisonReviewSheet,
  ComparisonSheetDescription,
  ComparisonSpecChange,
  ComparisonSpecification,
} from '@/shared/api';
import {
  COMPARISON_AI_JOB_STATE_VALUES,
  COMPARISON_AI_METHOD_VALUES,
  COMPARISON_AI_PAIR_DECISION_VALUES,
  COMPARISON_LAUNCH_ENTRY_STATE_VALUES,
} from '@/shared/api';

import { DOCUMENT_UID, MATRIX_ID, NOW, PROJECT_UID, SERIES_ID, TRANSITION_12, TRANSITION_23, V1, V2, V3, matrix, page, uid } from './fixtures';
import { referencePage } from '@/entities/version-series';

export const DIGEST = 'a1'.repeat(32);
export const DIGEST_NEW = 'b2'.repeat(32);
export const MODEL = 'Модель-эксперт-1';
export const USER = uid('usr', 1);
export const JOB_ID = uid('cai', 1);
export const REPORT_ID = uid('crt', 1);
export const PAIR_ID = uid('ctp', 2);

export function estimate(over: Partial<ComparisonAiEstimate> = {}): ComparisonAiEstimate {
  return {
    method: 'sheet_changes',
    estimate_digest: DIGEST,
    route: {
      connection_id: uid('exc', 1),
      revision_id: uid('exr', 1),
      pinned_model: MODEL,
      billing: 'metered',
      provider_mode: 'live',
    },
    units: 12,
    reused: 3,
    sheets: 12,
    transitions: 2,
    calls: 9,
    images: 18,
    image_bytes: 5_452_595,
    prompt_chars: 48_210,
    input_tokens: 61_000,
    output_tokens: 9_500,
    estimate_micros: 3_450_000,
    ceiling_micros: 10_000_000,
    day_remaining_micros: 46_000_000,
    ...over,
  };
}

export function job(over: Partial<ComparisonAiJob> = {}): ComparisonAiJob {
  return {
    job_id: JOB_ID,
    method: 'sheet_changes',
    project_uid: PROJECT_UID,
    document_uid: DOCUMENT_UID,
    state: 'running',
    estimate: estimate(),
    consented_by: USER,
    consented_at: NOW,
    spend: { spent_micros: 1_200_000, reserved_micros: 300_000, calls: 4, unknown_calls: 0, input_tokens: 20_000, output_tokens: 3_000 },
    counts: { total: 12, done: 5, failed: 0, unknown: 0 },
    created_at: NOW,
    updated_at: NOW,
    series_id: SERIES_ID,
    ...over,
  };
}

export function sheetChanges(over: Partial<ComparisonAiSheetChanges> = {}): ComparisonAiSheetChanges {
  return {
    series_id: SERIES_ID,
    job: job(),
    transitions: [
      { transition_id: TRANSITION_12, sheets: 8, done: 6, changed: 4, questions: 2, errors: 1, to_review: 2, calls: 9, input_tokens: 41_000, output_tokens: 6_000, seconds: 185 },
      { transition_id: TRANSITION_23, sheets: 4, done: 4, changed: 0, questions: 0, errors: 0, to_review: 0, calls: 4, input_tokens: 9_000, output_tokens: 1_000, seconds: 42 },
    ],
    ...over,
  };
}

/** One job per state of the contract, the paused one with each pause reason in turn. */
export function jobsInEveryState(): ComparisonAiJob[] {
  return COMPARISON_AI_JOB_STATE_VALUES.map((state, index) =>
    job({
      job_id: uid('cai', 10 + index),
      state,
      method: COMPARISON_AI_METHOD_VALUES[index % COMPARISON_AI_METHOD_VALUES.length] ?? 'sheet_changes',
      ...(state === 'queued' ? { queue_position: 2 } : {}),
      ...(state === 'paused' ? { pause_reason: 'quota' as const } : {}),
      ...(state === 'completed' ? { finished_at: NOW } : {}),
    }),
  );
}

export function aiQueue(): ComparisonAiQueue {
  const items: ComparisonAiQueueItem[] = jobsInEveryState().map((item, index) => ({
    job_id: item.job_id,
    method: item.method,
    state: item.state,
    project_uid: PROJECT_UID,
    document_uid: uid('doc', index === 0 ? 99 : (index % 4) + 1),
    counts: item.counts,
    created_at: item.created_at,
    series_id: SERIES_ID,
    ...(item.queue_position === undefined ? {} : { queue_position: item.queue_position }),
  }));
  return { items, queued: 1, running: 1, paused: 1 };
}

export function description(over: Partial<ComparisonSheetDescription> = {}): ComparisonSheetDescription {
  return {
    sheet_pair_id: PAIR_ID,
    state: 'done',
    history_count: 3,
    description_id: uid('csd', 1),
    source: 'sheet',
    model: MODEL,
    prompt_version: 'описание-3',
    created_at: NOW,
    recorded: false,
    changes: [
      {
        change_id: 'c1', object_name: 'Кабель питания щита', certainty: 'confirmed', place: 'ось 3, ряд Б', was: 'ВВГнг 3х2,5', now: 'ВВГнг 3х4',
        was_tier: 'from_text', now_tier: 'from_image', side: 'b', box: { x: 120, y: 80, width: 60, height: 20 },
      },
      {
        change_id: 'c2', object_name: 'Светильник аварийного освещения', certainty: 'unclear', place: 'коридор', now: 'Св-4', now_tier: 'unverified',
        limitation: 'марка на изображении читается плохо', side: 'a', box: { x: 300, y: 200, width: 40, height: 40 },
      },
      { change_id: 'c3', object_name: 'Примечание к узлу', certainty: 'confirmed', was: 'узел 3', was_tier: 'from_text' },
    ],
    unresolved: [{ question: 'Какая марка у выключателя на оси 7?', side: 'b', box: { x: 10, y: 10, width: 20, height: 20 } }],
    declared: [{ text: 'замена кабеля на сечение 4 мм²', reference: 'Изм. 2' }],
    excluded: [
      { reason: 'service', text: 'штамп' }, { reason: 'formatting', text: 'толщина линий' }, { reason: 'label_move', text: 'сдвиг надписи' },
      { reason: 'revision_mark', text: 'облако изменения' }, { reason: 'duplicate', text: 'повтор пункта' }, { reason: 'not_construction' },
    ],
    coverage: { candidates: 9, in_changes: 6, not_reviewed: 1 },
    diagnostics: { issues: ['PACKET_TRIMMED'], excluded_by_program: 6, candidates: 9 },
    ...over,
  };
}

export function reviewSheets(): ComparisonReviewSheet[] {
  return [
    { sheet_pair_id: uid('ctp', 3), kind: 'to_check', state: 'no_construction_changes', page_a: { page: page(V1, 3), title: 'Схема электроснабжения' }, page_b: { page: page(V2, 3), title: 'Схема электроснабжения' } },
    { sheet_pair_id: uid('ctp', 4), kind: 'added', state: 'done', page_b: { page: page(V2, 8), title: 'Узел 3' } },
    { sheet_pair_id: uid('ctp', 5), kind: 'removed', state: 'not_processed', page_a: { page: page(V1, 6), title: 'Разрез 1-1' } },
  ];
}

export function specification(over: Partial<ComparisonSpecification> = {}): ComparisonSpecification {
  return {
    transition_id: TRANSITION_12,
    method: 'whole',
    state: 'completed',
    sheets_a: 3,
    sheets_b: 4,
    coverage_a: { blocks_total: 10, blocks_covered: 9, rows_total: 40, rows_unresolved: 1 },
    coverage_b: { blocks_total: 12, blocks_covered: 12, rows_total: 52, rows_unresolved: 0 },
    totals: { changed: 3, added: 1, removed: 2, unclear: 1, renumbered: 1, moved: 0 },
    job_id: JOB_ID,
    ...over,
  };
}

export function specificationsInEveryState(): ComparisonSpecification[] {
  return [
    specification({ transition_id: uid('ctn', 21), state: 'not_applicable', method: 'sheet_ai', sheets_a: 0, sheets_b: 0, totals: undefined as never, coverage_a: undefined as never, coverage_b: undefined as never }),
    specification({ transition_id: uid('ctn', 22), state: 'not_started', totals: undefined as never, coverage_a: undefined as never, coverage_b: undefined as never }),
    specification({ transition_id: uid('ctn', 23), state: 'running', phase: 'comparing' }),
    specification({ transition_id: uid('ctn', 24), state: 'paused', phase: 'preparing' }),
    specification({ transition_id: uid('ctn', 25), state: 'completed' }),
    specification({ transition_id: uid('ctn', 26), state: 'incomplete', reason: 'coverage_incomplete' }),
    specification({ transition_id: uid('ctn', 27), state: 'failed', reason: 'unknown_reason_code' }),
    specification({ transition_id: uid('ctn', 28), state: 'cancelled', method: 'sheet_ai', phase: 'done' }),
  ];
}

export function specChanges(): ComparisonSpecChange[] {
  const pos = { name: 'Кабель ВВГнг 3х2,5', pos: '12', quantity: '120' };
  return [
    { change_id: 'k1', kind: 'changed', fields: [{ field: 'quantity', was: '120', now: '150' }, { field: 'unknown_field', was: 'а', now: 'б' }], old: pos, new: { ...pos, quantity: '150' }, text: 'Количество кабеля выросло' },
    { change_id: 'k2', kind: 'added', fields: [], new: { name: 'Светильник Св-4' } },
    { change_id: 'k3', kind: 'removed', fields: [], old: { name: 'Лоток 100х50' } },
    { change_id: 'k4', kind: 'unclear', fields: [], old: { name: 'Хомут', ambiguous: true } },
    { change_id: 'k5', kind: 'renumbered', fields: [{ field: 'pos', was: '12', now: '14' }], old: pos, new: { ...pos, pos: '14' } },
    { change_id: 'k6', kind: 'moved', fields: [], old: { name: 'Труба ПНД', section: 'Трубы' }, new: { name: 'Труба ПНД', section: 'Кабельные трассы' } },
  ];
}

function parts(kind: 'client' | 'analytic'): ComparisonReportPart[] {
  return kind === 'client'
    ? [
        { transition_id: TRANSITION_12, selection: 'done', points: 7, questions: 2 },
        { transition_id: TRANSITION_23, selection: 'pending' },
        { transition_id: uid('ctn', 3), selection: 'running' },
        { transition_id: uid('ctn', 4), selection: 'failed' },
      ]
    : [
        { transition_id: TRANSITION_12, analysis: 'done', verification: 'running', facts: { found: 9, confirmed: 7, contradicted: 1, unconfirmed: 1 }, warnings: 2 },
        { transition_id: TRANSITION_23, analysis: 'failed', verification: 'pending' },
      ];
}

export function report(over: Partial<ComparisonReport> = {}): ComparisonReport {
  return {
    report_id: REPORT_ID,
    series_id: SERIES_ID,
    project_uid: PROJECT_UID,
    document_uid: DOCUMENT_UID,
    kind: 'client',
    source: 'series_summary',
    state: 'completed',
    reuse: true,
    parts: parts('client'),
    artifacts: [
      { kind: 'report_pdf', size_bytes: 412_000, sha256: DIGEST, created_at: NOW },
      { kind: 'source_md', size_bytes: 88_000, sha256: DIGEST_NEW, created_at: NOW },
    ],
    created_at: NOW,
    updated_at: NOW,
    job: job({ method: 'report' }),
    ...over,
  };
}

export function draftReport(over: Partial<ComparisonReport> = {}): ComparisonReport {
  return report({ report_id: uid('crt', 2), state: 'draft', parts: [], artifacts: [], job: undefined as never, estimate: estimate({ method: 'report', transitions: 4, units: 4 }), ...over });
}

export function reportsInEveryShape(): ComparisonReport[] {
  const states = ['draft', 'queued', 'running', 'paused', 'completed', 'partial', 'failed', 'cancelled'] as const;
  return states.map((state, index) =>
    report({
      report_id: uid('crt', 10 + index),
      state,
      kind: index % 2 === 0 ? 'client' : 'analytic',
      source: index % 3 === 0 ? 'uploaded_md' : 'series_summary',
      parts: parts(index % 2 === 0 ? 'client' : 'analytic'),
      ...(index % 3 === 0 ? { source_name: 'сводка-изменений.md' } : {}),
      ...(state === 'draft' ? { artifacts: [], estimate: estimate({ method: 'report' }) } : {}),
      ...(state === 'running' ? { stage: 'transition_analysis' as const } : {}),
      ...(state === 'failed' ? { failure_reason: 'pdf_failed', stage: 'pdf_writing' as const, artifacts: [{ kind: 'source_md' as const, size_bytes: 88_000, sha256: DIGEST_NEW, created_at: NOW }] } : {}),
      ...(state === 'paused' ? { job: job({ method: 'report', state: 'paused', pause_reason: 'overrun' }) } : {}),
      ...(index === 6 ? { prepared_from_id: uid('crt', 10) } : {}),
    }),
  );
}

export function launchQueue(state: ComparisonLaunchQueue['state'] = 'running'): ComparisonLaunchQueue {
  const entries: ComparisonLaunchEntry[] = COMPARISON_LAUNCH_ENTRY_STATE_VALUES.map((entryState, index) => ({
    entry_id: uid('cle', index + 1),
    document_uid: uid('doc', (index % 4) + 1),
    step: (['profile', 'matrix', 'ai_pairs', 'series', 'ai_changes', 'report'] as const)[index % 6] ?? 'series',
    state: entryState,
    position: index + 1,
    restart: false,
    created_at: NOW,
    updated_at: NOW,
    ...(entryState === 'failed' ? { reason: 'comparison_ceiling_day' } : {}),
  }));
  return {
    project_uid: PROJECT_UID,
    state,
    counts: { total: 6, done: 1, running: 1, waiting: 1, needs_consent: 1, skipped: 1, failed: 1 },
    entries,
    updated_at: NOW,
  };
}

/**
 * The answers of the check of doubtful pairs in all thirteen decisions, each on a cell of the matrix of `fixtures.ts`: the
 * `version_uid` is the cell's and the `page` a matched sheet of the same row in another version.
 */
export function hints(): ComparisonAiPairHint[] {
  const m = matrix();
  const rows = m.rows ?? [];
  const targets: { readonly row: number; readonly version: string }[] = [
    { row: 5, version: V3 }, { row: 6, version: V2 }, { row: 0, version: V1 }, { row: 0, version: V2 }, { row: 0, version: V3 },
    { row: 1, version: V1 }, { row: 1, version: V2 }, { row: 1, version: V3 }, { row: 2, version: V1 }, { row: 2, version: V2 },
    { row: 2, version: V3 }, { row: 4, version: V1 }, { row: 4, version: V2 },
  ];
  const confidences = ['high', 'medium', 'low'] as const;
  return COMPARISON_AI_PAIR_DECISION_VALUES.map((decision, index): ComparisonAiPairHint => {
    const target = targets[index] as { row: number; version: string };
    const row = rows[target.row];
    const reference = row === undefined ? page(V1, 1) : (referencePage(row, target.version) ?? page(V1, 1));
    return {
      question_id: uid('cpq', index + 1),
      job_id: JOB_ID,
      matrix_id: MATRIX_ID,
      kind: decision.startsWith('medium') ? 'medium_pair' : 'no_pair',
      decision,
      page: reference,
      version_uid: target.version,
      candidates: [page(target.version, 7)],
      stale: index === 3,
      created_at: NOW,
      confidence: confidences[index % 3] as 'high' | 'medium' | 'low',
      ...(decision.startsWith('hint_') ? { hint_page: page(target.version, 7), reason: 'похоже на тот же лист по штампу' } : {}),
      ...(decision === 'link_accepted' ? { link_id: uid('cak', 1) } : {}),
    };
  });
}
