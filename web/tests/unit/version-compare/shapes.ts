/**
 * Every state of the «Сравнение версий» screens that one static pass can reach, as screen cases (`CMP-VC-UI-01`).
 *
 * Two instruments judge them: `tests/guards/rendered-language.guard.test.ts` renders each in every cache state of its matrix (no
 * Latin word a contract did not put there, no member of a translated schema unseen) and `tests/unit/styles/screens.ts` renders
 * each for the contrast census (every colour-bearing rule of the lane's stylesheets reached). One list, so the two cannot
 * disagree about which states exist.
 *
 * A case is a component and the cache it needs; the states that a click would reach (a draft, an opened pair, a stopped
 * transfer) are props of the views, because the harness fires no event.
 */

import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';

import type { ComparisonSeriesState, ComparisonUploadState } from '@/shared/api';
import { ApiError } from '@/shared/api';
import {
  COMPARISON_AI_JOB_STATE_VALUES,
  COMPARISON_AI_PAUSE_REASON_VALUES,
  COMPARISON_AI_SHEET_STATE_VALUES,
  COMPARISON_LAUNCH_QUEUE_STATE_VALUES,
  COMPARISON_REPORT_STAGE_VALUES,
  COMPARISON_SERIES_STATE_VALUES,
  COMPARISON_SPEC_PHASE_VALUES,
  COMPARISON_UPLOAD_STATE_VALUES,
} from '@/shared/api';
import { ChangesPanelView, ComparisonViewer, EvidenceBanner } from '@/widgets/comparison-viewer';
import { ReportWindow, ReportWindowView } from '@/widgets/comparison-report';
import type { ReportWindowViewProps } from '@/widgets/comparison-report';
import { ComparisonAiQueueBlock, ComparisonAiQueueBlockView, ComparisonQueueBlock, ComparisonQueueBlockView } from '@/widgets/execution-queue';
import {
  AiChangesBlock,
  AiChangesBlockView,
  AiQueueStrip,
  LaunchQueueStrip,
  SelectionDialog,
  SpecificationChanges,
  SpecificationChangesView,
  SpecificationsBlock,
  SpecificationsBlockView,
  SummaryReportBlock,
  SummaryReportBlockView,
} from '@/widgets/version-series';
import type { AiChangesBlockViewProps, SpecificationsBlockViewProps, SummaryReportBlockViewProps } from '@/widgets/version-series';
import { AiStartDialog, ReportDraftDialog } from '@/widgets/version-series';
import { EstimatePanel, evidenceOf } from '@/entities/version-series';
import type { EstimatePanelProps } from '@/entities/version-series';
import { ComparisonResult } from '@/widgets/version-comparison';
import { UploadDialogView } from '@/widgets/comparison-upload';
import type { UploadDialogViewProps } from '@/widgets/comparison-upload';
import { PairViewerSlot, ProjectsAndStagesView, SheetsTabView, VersionOrderDialogView } from '@/widgets/version-series';
import type { ProjectsAndStagesViewProps, SheetsTabViewProps } from '@/widgets/version-series';
import { VersionComparePage } from '@/_pages/version-compare';
import {
  COMPARISON_KEYS,
  EMPTY_DRAFT,
  INITIAL_VIEW,
  addEdit,
  columnNames,
  comparisonFailure,
} from '@/entities/version-series';
import type { Draft } from '@/entities/version-series';

import { comparedPair } from '../comparison/viewer/viewer-fixtures';
import { seedError } from '../screens/harness';

import {
  DOCUMENT_UID,
  MATRIX_ID,
  PROJECT_UID,
  V1,
  V2,
  V3,
  edits,
  matrix,
  overview,
  page,
  pairs,
  proposalSets,
  queueSummary,
  series,
  transition,
  upload,
  uid,
} from './fixtures';
import { READER, refusal, seedComparison } from './seed';
import {
  DIGEST,
  DIGEST_NEW,
  PAIR_ID as AI_PAIR_ID,
  aiQueue,
  description,
  estimate,
  job,
  launchQueue,
  report,
  reportsInEveryShape,
  reviewSheets,
  sheetChanges,
  specChanges,
  specification,
  specificationsInEveryState,
} from './ai-fixtures';

export interface ComparisonShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
}

const noop = (): void => undefined;
const SHEETS_AT = { projectUid: PROJECT_UID, tab: 'sheets', documentUid: DOCUMENT_UID } as const;
const PROJECT_AT = { projectUid: PROJECT_UID } as const;

const page_ = (initial: Parameters<typeof VersionComparePage>[0]['initial']): (() => ReactElement) => () =>
  createElement(VersionComparePage, initial === undefined ? {} : { initial });

const REVISION = { matrix_id: MATRIX_ID, edit_no: 3 };
const DRAFT: Draft = addEdit(
  addEdit(EMPTY_DRAFT, REVISION, { kind: 'link', page: page(V1, 6), otherPage: page(V3, 7) }) as Draft,
  REVISION,
  { kind: 'mark_absent', page: page(V1, 6), absentVersionUid: V3 },
) as Draft;

export function projectsProps(over: Partial<ProjectsAndStagesViewProps> = {}): ProjectsAndStagesViewProps {
  return {
    projectUid: PROJECT_UID, overview: overview(), view: INITIAL_VIEW, onView: noop, mayAct: true, busy: false, confirming: null, failure: null,
    onRefresh: noop, onOpen: noop, onAct: noop, onConfirmRestart: noop, onCancelRestart: noop,
    selected: new Set<string>(), onSelect: noop, onSelectColumn: noop, onClearSelection: noop, onRunSelected: noop,
    selectableAi: new Set<string>(), onSelectable: noop, launchQueue: undefined, queueOpen: false, queueBusy: false, queueFailure: null,
    onQueueToggle: noop, onQueueAct: noop, onQueueRemove: noop, onQueueConfirm: noop, aiQueue: undefined, onAiAct: noop, onSummary: noop, dialog: null,
    ...over,
  };
}

function sheetsProps(over: Partial<SheetsTabViewProps> = {}): SheetsTabViewProps {
  const m = matrix();
  return {
    heading: '133/23-ГК-ЭМ1', matrix: m, edits: edits(), names: columnNames(m.columns ?? []),
    titles: new Map([[V1, 'ЭМ-изм0.pdf'], [V2, 'ЭМ-изм1.pdf'], [V3, 'ЭМ-изм2.pdf']]), series: series(), seriesFailure: null, seriesBusy: false,
    pairs: pairs(), openTransitionId: uid('ctn', 2), sides: { a: V2, b: V3 }, onSide: noop, onlyChanged: false, onOnlyChanged: noop,
    draft: EMPTY_DRAFT, notice: null, dropped: [], draftFailure: null, applying: false, mayEdit: true, prepareBusy: false,
    orderDialog: null, viewer: null, clickNote: null, onPrepare: noop, onApply: noop, onUndo: noop, onRemoveDraft: noop,
    onOpenOrder: noop, onGesture: noop, onSheet: noop, onOpenPair: noop, onOpenTransition: noop, onSeriesAct: noop, onStartSeries: noop,
    confirmingRestart: false, onAskRestart: noop, onConfirmRestart: noop, onCancelRestart: noop,
    ...over,
  };
}

function dialogProps(over: Partial<UploadDialogViewProps> = {}): UploadDialogViewProps {
  return {
    mode: 'single', phase: 'pick', groups: [], skipped: 0, problem: null, compare: false, hashing: null, upload: undefined, loading: false,
    sets: [], drafts: {}, fileNames: new Map(), progress: new Map(), fileFailures: new Map(), missing: [], failure: null, unfinished: [],
    notice: null, mayAct: true, busy: false, onPick: noop, onRemoveGroup: noop, onCompare: noop, onSend: noop, onStop: noop,
    onContinue: noop, onOpenUnfinished: noop, onDraft: noop, onConfirm: noop, onConfirmAll: noop, onProposedAll: noop, onExclude: noop,
    onRetry: noop, onPause: noop, onResume: noop, onDelete: noop, onSwitch: noop, onClose: noop, ...over,
  };
}

const NAMES = new Map((upload().files ?? []).map((file) => [file.file_id, file.display_name] as const));
const STALE_FAILURE = comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_matrix_stale' }));
const PAIR_ID = uid('ctp', 2);

const seriesOf = (state: ComparisonSeriesState): ComparisonShape => ({
  name: `version-compare-series-${state}`,
  make: () => createElement(SheetsTabView, sheetsProps({ series: series({ state }) })),
});

const uploadOf = (state: ComparisonUploadState): ComparisonShape => ({
  name: `comparison-upload-${state}`,
  make: () =>
    createElement(UploadDialogView, dialogProps({ mode: 'batch', phase: 'watching', upload: upload({ state }), sets: state === 'proposed' ? proposalSets() : [], fileNames: NAMES })),
});

// ====================================================================================== `CMP-VC-UI-02`

const SERIES = series();
const SET_NAMES = new Map<string, string>([[V1, '№1'], [V2, '№2'], [V3, '№3']]);

function estimateProps(over: Partial<EstimatePanelProps> = {}): EstimatePanelProps {
  return {
    title: 'ИИ-описание изменений · 133/23-ГК-ЭМ1', consentKind: 'sheet_changes', confirmLabel: 'Запустить', estimate: estimate(), loading: false,
    failure: null, agreedDigest: DIGEST, busy: false, onAgree: noop, onConfirm: noop, onCancel: noop, ...over,
  };
}

function changesBlockProps(over: Partial<AiChangesBlockViewProps> = {}): AiChangesBlockViewProps {
  return {
    changes: sheetChanges(), series: SERIES, names: SET_NAMES, mayAct: true, busy: false, failure: null, folds: new Set<string>(),
    review: new Map(), onFold: noop, onAct: noop, onOpenTransition: noop, onOpenReviewSheet: noop, dialog: null, ...over,
  };
}

function specsBlockProps(over: Partial<SpecificationsBlockViewProps> = {}): SpecificationsBlockViewProps {
  return {
    specs: [specification(), specification({ transition_id: uid('ctn', 2), method: 'sheet_ai' })], transitions: SERIES.transitions ?? [], names: SET_NAMES,
    mayAct: true, busy: false, failure: null, openChanges: null, changes: null, onOpenChanges: noop, onStart: noop, onCancel: noop,
    onOpenTransition: noop, dialog: null, ...over,
  };
}

function summaryProps(over: Partial<SummaryReportBlockViewProps> = {}): SummaryReportBlockViewProps {
  return {
    report: report(), summaryReady: true, transitions: SERIES.transitions ?? [], names: SET_NAMES, mayAct: true, busy: false, failure: null,
    onPdf: noop, onMd: noop, onContinue: noop, ...over,
  };
}

function windowProps(over: Partial<ReportWindowViewProps> = {}): ReportWindowViewProps {
  return {
    reports: reportsInEveryShape(), transitions: SERIES.transitions ?? [], names: SET_NAMES, summaryReady: true, mayAct: true, busy: false, failure: null,
    source: 'series_summary', onSource: noop, kind: 'client', onKind: noop, reuse: true, onReuse: noop, fileName: null, onFile: noop,
    onPrepareEstimate: noop, onAct: noop, onClose: noop, dialog: null, ...over,
  };
}

function panelProps(over: Partial<Parameters<typeof ChangesPanelView>[0]> = {}): Parameters<typeof ChangesPanelView>[0] {
  return {
    sheetTitle: 'л. 3 · Схема электроснабжения', description: description(), loading: false, failure: null, mayAct: true, busy: false, copied: false,
    history: { items: [
      { description_id: uid('csd', 1), state: 'done', changes_count: 3, unresolved_count: 1, recorded: false, created_at: '2026-10-28T10:15:30Z', model: 'Модель-эксперт-1' },
      { description_id: uid('csd', 2), state: 'stale', changes_count: 2, unresolved_count: 0, recorded: true, created_at: '2026-10-27T10:15:30Z' },
    ], page: { next_cursor: null } },
    estimate: null, onDescribe: noop, onCancelJob: noop, onShow: noop, onCopy: noop, onMd: noop, ...over,
  };
}

const NOT_WIRED = refusal('dependency_unavailable', { dependency: 'comparison_ai_sheets' });

/** Every AI screen state that one static pass reaches (the cells of steps 4/6/7, the dialogs, the strips, the blocks, the window, the panel). */
function aiShapes(): ComparisonShape[] {
  const doc = (n: number): string => uid('doc', n);
  const out: ComparisonShape[] = [];
  const push = (shape: ComparisonShape): void => void out.push(shape);

  // «Проекты и этапы»: the cells in many states, the selection, the strips and a dialog
  push({
    name: 'projects-and-stages-ai-steps',
    make: () =>
      createElement(ProjectsAndStagesView, projectsProps({
        selected: new Set([`${doc(1)}|ai_pairs`, `${doc(2)}|series`, `${doc(3)}|ai_changes`]),
        selectableAi: new Set([`${doc(1)}|ai_pairs`, `${doc(3)}|ai_changes`, `${doc(4)}|report`, `${doc(5)}|ai_pairs`]),
        launchQueue: launchQueue(), queueOpen: true, aiQueue: aiQueue(),
        dialog: createElement(EstimatePanel, estimateProps()),
      })),
    seedClient: (c) => {
      seedAiRows(c);
    },
  });
  push({
    name: 'projects-and-stages-ai-steps-reader',
    make: () => createElement(ProjectsAndStagesView, projectsProps({ mayAct: false, launchQueue: launchQueue('paused'), queueOpen: false })),
    seedClient: (c) => seedAiRows(c),
  });
  push({
    name: 'projects-and-stages-ai-not-wired',
    make: () => createElement(ProjectsAndStagesView, projectsProps()),
    seedClient: (c) => {
      for (let n = 1; n <= 13; n += 1) {
        seedError(c, COMPARISON_KEYS.aiPair(PROJECT_UID, doc(n)), refusal('dependency_unavailable', { dependency: 'comparison_ai_pairs' }));
        seedError(c, COMPARISON_KEYS.seriesList(PROJECT_UID, doc(n)), refusal('dependency_unavailable', { dependency: 'comparison_series' }));
      }
    },
  });
  push({
    name: 'projects-and-stages-launch-queue-failure',
    make: () => createElement(ProjectsAndStagesView, projectsProps({ launchQueue: launchQueue('failed'), queueOpen: true, queueFailure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_launch_queue_state' })) })),
  });
  for (const state of COMPARISON_LAUNCH_QUEUE_STATE_VALUES) {
    push({
      name: `launch-queue-strip-${state}`,
      make: () =>
        createElement(LaunchQueueStrip, {
          queue: launchQueue(state), sets: overview().sets, mayAct: true, busy: false, open: true, failure: null,
          onToggle: noop, onAct: noop, onRemove: noop, onConfirm: noop,
        }),
    });
  }
  push({ name: 'ai-queue-strip', make: () => createElement(AiQueueStrip, { queue: aiQueue(), sets: overview().sets }) });

  // the estimate and the consent
  push({ name: 'estimate-panel-agreed', make: () => createElement(EstimatePanel, estimateProps()) });
  push({ name: 'estimate-panel-loading', make: () => createElement(EstimatePanel, estimateProps({ estimate: undefined, loading: true, agreedDigest: null })) });
  push({ name: 'estimate-panel-not-metered', make: () => createElement(EstimatePanel, estimateProps({ estimate: estimate({ estimate_micros: 0, ceiling_micros: 0, route: { ...estimate().route, billing: 'not_metered' } }), agreedDigest: null })) });
  push({ name: 'estimate-panel-recorded', make: () => createElement(EstimatePanel, estimateProps({ estimate: estimate({ route: { ...estimate().route, provider_mode: 'recorded' } }), agreedDigest: null })) });
  push({ name: 'estimate-panel-small-spend', make: () => createElement(EstimatePanel, estimateProps({ estimate: estimate({ estimate_micros: 900, day_remaining_micros: undefined as never }), agreedDigest: null })) });
  for (const blocked of ['job', 'day'] as const) {
    push({ name: `estimate-panel-blocked-${blocked}`, make: () => createElement(EstimatePanel, estimateProps({ estimate: estimate({ blocked_by: blocked }), agreedDigest: null })) });
  }
  push({ name: 'estimate-panel-nothing-to-send', make: () => createElement(EstimatePanel, estimateProps({ estimate: estimate({ calls: 0, images: 0, reused: 12, units: 12 }), agreedDigest: null })) });
  push({
    name: 'estimate-panel-stale-asks-again',
    make: () =>
      createElement(EstimatePanel, estimateProps({
        estimate: estimate({ estimate_digest: DIGEST_NEW }), agreedDigest: DIGEST,
        failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_estimate_stale' })),
      })),
  });
  push({ name: 'estimate-panel-unread', make: () => createElement(EstimatePanel, estimateProps({ estimate: undefined, agreedDigest: null, failure: comparisonFailure(refusal('dependency_unavailable', { dependency: 'executor_route_missing' })) })) });
  for (const [name, reason] of [['consent', 'comparison_consent_required'], ['ceiling-day', 'comparison_ceiling_day']] as const) {
    const code = name === 'consent' ? 'validation_failed' : 'conflict';
    push({
      name: `estimate-panel-refused-${name}`,
      make: () => createElement(EstimatePanel, estimateProps({ failure: comparisonFailure(new ApiError(code === 'conflict' ? 409 : 422, { contract_version: '1.11.0', error_code: code, message: 'A caller-safe sentence in English.', correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false, details: code === 'conflict' ? { conflict_reason: reason } : { constraint: reason } }, '0f0e9d8c-7b6a-4948-b726-150413021100')) })),
    });
  }
  push({ name: 'ai-start-dialog-pending', make: () => createElement(AiStartDialog, { title: 'ИИ-проверка сомнительных пар · 133/23-ГК-ЭМ1', scope: { kind: 'pair_check', projectUid: PROJECT_UID, documentUid: DOCUMENT_UID } as never, consentKind: 'pair_check', confirmLabel: 'Проверить', intro: 'ИИ смотрит листы с кандидатами.', onDone: noop, onCancel: noop }) });
  push({ name: 'report-draft-dialog-pending', make: () => createElement(ReportDraftDialog, { title: 'PDF-отчёт · 133/23-ГК-ЭМ1', seriesId: SERIES_ID_, confirmLabel: 'Сформировать', onDone: noop, onCancel: noop }) });
  push({
    name: 'selection-dialog',
    make: () => createElement(SelectionDialog, { projectUid: PROJECT_UID, items: [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => ({ documentUid: doc(n), step: n % 2 === 0 ? 'ai_pairs' as const : 'series' as const, label: `133/23-ГК-ЭМ${n} · шаг` })), restart: false, queueNote: 'Очередь запуска сейчас остановлена — выбранное встанет в неё и начнётся после «Продолжить очередь».', onDone: noop, onCancel: noop }),
    seedClient: (c) => c.setQueryData([...COMPARISON_KEYS.estimate(`selection|${PROJECT_UID}`), [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `${doc(n)}:${n % 2 === 0 ? 'ai_pairs' : 'series'}`).join(',')], [
      { item: { documentUid: doc(2), step: 'ai_pairs' }, estimate: estimate({ method: 'pair_check' }), why: '' },
      { item: { documentUid: doc(4), step: 'ai_pairs' }, estimate: null, why: 'Сравнение соседних версий ещё не посчитано: оценки пока нет.' },
      { item: { documentUid: doc(1), step: 'series' }, estimate: null, why: '' },
    ]),
  });

  // «Сравнение листов»: the three blocks
  push({
    name: 'ai-changes-block-folds',
    make: () => createElement(AiChangesBlockView, changesBlockProps({ folds: new Set([TRANSITION_12_]), review: new Map([[TRANSITION_12_, reviewSheets()]]), dialog: createElement(EstimatePanel, estimateProps({ title: 'ИИ-описание изменений · листы с ошибкой' })) })),
  });
  push({ name: 'ai-changes-block-fold-empty', make: () => createElement(AiChangesBlockView, changesBlockProps({ folds: new Set([TRANSITION_12_]), review: new Map() })) });
  push({ name: 'ai-changes-block-none', make: () => createElement(AiChangesBlockView, changesBlockProps({ changes: sheetChanges({ job: undefined as never, transitions: sheetChanges().transitions.map((row) => ({ ...row, done: 0, errors: 0, to_review: 0, changed: 0 })) }) })) });
  push({ name: 'ai-changes-block-reader', make: () => createElement(AiChangesBlockView, changesBlockProps({ mayAct: false, changes: sheetChanges({ job: job({ state: 'cancelled', counts: { total: 12, done: 5, failed: 1, unknown: 0 } }) }) })) });
  push({ name: 'ai-changes-block-refused', make: () => createElement(AiChangesBlockView, changesBlockProps({ failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_ai_nothing_to_do' })) })) });
  for (const reason of COMPARISON_AI_PAUSE_REASON_VALUES) {
    push({ name: `ai-changes-block-paused-${reason}`, make: () => createElement(AiChangesBlockView, changesBlockProps({ changes: sheetChanges({ job: job({ state: 'paused', pause_reason: reason }) }) })) });
  }
  for (const state of COMPARISON_AI_JOB_STATE_VALUES) {
    push({
      name: `ai-changes-block-${state}`,
      make: () => createElement(AiChangesBlockView, changesBlockProps({ changes: sheetChanges({ job: job({ state, ...(state === 'queued' ? { queue_position: 3 } : {}) }) }) })),
    });
  }
  push({
    name: 'ai-changes-block-not-wired',
    make: () => createElement(AiChangesBlockView, changesBlockProps({ failure: comparisonFailure(NOT_WIRED) })),
  });

  push({ name: 'specifications-block', make: () => createElement(SpecificationsBlockView, specsBlockProps({ specs: specificationsInEveryState(), transitions: [...(SERIES.transitions ?? []), ...specificationsInEveryState().map((spec) => ({ ...(SERIES.transitions ?? [])[0] as NonNullable<typeof SERIES.transitions>[number], transition_id: spec.transition_id }))], openChanges: uid('ctn', 25), changes: createElement(SpecificationChangesView, { items: specChanges() }) })) });
  push({ name: 'specifications-block-reader', make: () => createElement(SpecificationsBlockView, specsBlockProps({ mayAct: false, openChanges: TRANSITION_12_, changes: createElement(SpecificationChangesView, { items: [] }) })) });
  for (const phase of COMPARISON_SPEC_PHASE_VALUES) {
    push({ name: `specifications-block-phase-${phase}`, make: () => createElement(SpecificationsBlockView, specsBlockProps({ specs: [specification({ state: 'running', phase })] })) });
  }
  push({ name: 'summary-report-block-client', make: () => createElement(SummaryReportBlockView, summaryProps()) });
  push({ name: 'summary-report-block-analytic', make: () => createElement(SummaryReportBlockView, summaryProps({ report: report({ kind: 'analytic', state: 'partial', failure_reason: 'model_failed', parts: reportsInEveryShape()[1]?.parts ?? [] }) })) });
  push({ name: 'summary-report-block-none', make: () => createElement(SummaryReportBlockView, summaryProps({ report: undefined, summaryReady: false })) });
  push({ name: 'summary-report-block-refused', make: () => createElement(SummaryReportBlockView, summaryProps({ mayAct: false, failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_summary_unavailable' })) })) });
  for (const stage of COMPARISON_REPORT_STAGE_VALUES) {
    push({ name: `summary-report-block-stage-${stage}`, make: () => createElement(SummaryReportBlockView, summaryProps({ report: report({ state: 'running', stage }) })) });
  }

  // the PDF report window
  push({ name: 'report-window', make: () => createElement(ReportWindowView, windowProps({ dialog: createElement(EstimatePanel, estimateProps({ title: 'PDF-отчёт', consentKind: 'report', confirmLabel: 'Сформировать', estimate: estimate({ method: 'report', transitions: 4, units: 4 }) })) })) });
  push({ name: 'report-window-upload', make: () => createElement(ReportWindowView, windowProps({ source: 'uploaded_md', kind: 'analytic', reuse: false, fileName: 'сводка-изменений.md', summaryReady: false, reports: [] })) });
  push({ name: 'report-window-reader', make: () => createElement(ReportWindowView, windowProps({ mayAct: false, reports: [report(), report({ report_id: uid('crt', 3), kind: 'analytic', parts: [] })] })) });
  push({ name: 'report-window-refused', make: () => createElement(ReportWindowView, windowProps({ failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_report_state' })) })) });
  push({ name: 'report-window-not-wired', make: () => createElement(ReportWindowView, windowProps({ failure: comparisonFailure(refusal('dependency_unavailable', { dependency: 'comparison_reports' })), reports: [] })) });
  for (const stage of COMPARISON_REPORT_STAGE_VALUES) {
    push({ name: `report-window-stage-${stage}`, make: () => createElement(ReportWindowView, windowProps({ reports: [report({ state: 'running', stage })] })) });
  }

  // the side panel and the evidence banner
  for (const state of COMPARISON_AI_SHEET_STATE_VALUES) {
    const withContent = state === 'done' || state === 'needs_clarification' || state === 'partial' || state === 'no_construction_changes' || state === 'stale';
    push({
      name: `changes-panel-${state}`,
      make: () => createElement(ChangesPanelView, panelProps({
        description: withContent ? description({ state }) : description({ state, changes: undefined as never, unresolved: undefined as never, declared: undefined as never, excluded: undefined as never, coverage: undefined as never, diagnostics: undefined as never, model: undefined as never, history_count: 1, ...(state === 'queued' || state === 'running' ? { job_id: JOB_ID_ } : {}) }),
      })),
    });
  }
  push({ name: 'changes-panel-recorded', make: () => createElement(ChangesPanelView, panelProps({ description: description({ recorded: true }), copied: true })) });
  push({ name: 'changes-panel-whole-specification', make: () => createElement(ChangesPanelView, panelProps({ description: description({ source: 'whole_specification' }) })) });
  push({ name: 'changes-panel-estimate', make: () => createElement(ChangesPanelView, panelProps({ description: description({ state: 'not_processed', changes: undefined as never, unresolved: undefined as never, history_count: 1 }), estimate: createElement(EstimatePanel, estimateProps({ title: 'Описать этот лист', consentKind: 'sheet', confirmLabel: 'Передать и описать', estimate: estimate({ units: 1, sheets: 1, calls: 1, images: 2, image_bytes: 600_000, prompt_chars: 8_000 }), agreedDigest: null })) })) });
  push({ name: 'changes-panel-reader', make: () => createElement(ChangesPanelView, panelProps({ mayAct: false, description: description({ state: 'not_processed', changes: undefined as never, unresolved: undefined as never, history_count: 1 }) })) });
  push({ name: 'changes-panel-loading', make: () => createElement(ChangesPanelView, panelProps({ description: undefined, loading: true })) });
  push({ name: 'changes-panel-not-wired', make: () => createElement(ChangesPanelView, panelProps({ description: undefined, failure: comparisonFailure(NOT_WIRED) })) });
  push({ name: 'changes-panel-failed-read', make: () => createElement(ChangesPanelView, panelProps({ description: undefined, failure: comparisonFailure(refusal('internal_error')) })) });
  push({
    name: 'evidence-banner-one',
    make: () => createElement(EvidenceBanner, { evidence: { items: evidenceOf(description()), index: 0, all: false }, onAction: noop }),
  });
  push({
    name: 'evidence-banner-all',
    make: () => createElement(EvidenceBanner, { evidence: { items: evidenceOf(description()), index: 1, all: true }, onAction: noop }),
  });
  push({
    name: 'viewer-with-the-side-panel',
    make: () => createElement(ComparisonViewer, { pair: comparedPair({ sheet_pair_id: AI_PAIR_ID }), changes: { mayAct: true } }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.description(AI_PAIR_ID), description()),
  });
  push({
    name: 'viewer-with-the-side-panel-not-wired',
    make: () => createElement(ComparisonViewer, { pair: comparedPair({ sheet_pair_id: AI_PAIR_ID }), changes: { mayAct: false } }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.description(AI_PAIR_ID), NOT_WIRED),
  });

  // the containers of the blocks and of the window: cold (the reads are on their way), loaded and refused
  const containerProps = { series: SERIES, projectUid: PROJECT_UID, names: SET_NAMES, mayAct: true };
  push({ name: 'ai-changes-block-container-cold', make: () => createElement(AiChangesBlock, { ...containerProps, onOpenTransition: noop, onOpenReviewSheet: noop }) });
  push({
    name: 'ai-changes-block-container-loaded',
    make: () => createElement(AiChangesBlock, { ...containerProps, onOpenTransition: noop, onOpenReviewSheet: noop }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.aiSheets(SERIES_ID), sheetChanges()),
  });
  push({
    name: 'ai-changes-block-container-not-wired',
    make: () => createElement(AiChangesBlock, { ...containerProps, onOpenTransition: noop, onOpenReviewSheet: noop }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.aiSheets(SERIES_ID), NOT_WIRED),
  });
  push({ name: 'specifications-block-container-cold', make: () => createElement(SpecificationsBlock, { series: SERIES, names: SET_NAMES, mayAct: true, onOpenTransition: noop }) });
  push({
    name: 'specifications-block-container-loaded',
    make: () => createElement(SpecificationsBlock, { series: SERIES, names: SET_NAMES, mayAct: true, onOpenTransition: noop }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.specs(SERIES_ID), specificationsInEveryState()),
  });
  push({
    name: 'specifications-block-container-none',
    make: () => createElement(SpecificationsBlock, { series: SERIES, names: SET_NAMES, mayAct: true, onOpenTransition: noop }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.specs(SERIES_ID), [specification({ state: 'not_applicable' })]),
  });
  push({
    name: 'specifications-block-container-not-wired',
    make: () => createElement(SpecificationsBlock, { series: SERIES, names: SET_NAMES, mayAct: true, onOpenTransition: noop }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.specs(SERIES_ID), refusal('dependency_unavailable', { dependency: 'comparison_specification' })),
  });
  push({ name: 'specification-changes-cold', make: () => createElement(SpecificationChanges, { transitionId: TRANSITION_12_ }) });
  push({ name: 'summary-report-block-container-cold', make: () => createElement(SummaryReportBlock, { series: SERIES, names: SET_NAMES, mayAct: true, summaryReady: true }) });
  push({
    name: 'summary-report-block-container-loaded',
    make: () => createElement(SummaryReportBlock, { series: SERIES, names: SET_NAMES, mayAct: true, summaryReady: true }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.reports(SERIES_ID), [report()]),
  });
  push({
    name: 'summary-report-block-container-not-wired',
    make: () => createElement(SummaryReportBlock, { series: SERIES, names: SET_NAMES, mayAct: true, summaryReady: true }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.reports(SERIES_ID), refusal('dependency_unavailable', { dependency: 'comparison_reports' })),
  });
  push({ name: 'report-window-container-cold', make: () => createElement(ReportWindow, { series: SERIES, names: SET_NAMES, mayAct: true, onClose: noop }) });
  push({
    name: 'report-window-container-loaded',
    make: () => createElement(ReportWindow, { series: SERIES, names: SET_NAMES, mayAct: true, onClose: noop }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.reports(SERIES_ID), reportsInEveryShape()),
  });
  push({
    name: 'report-window-container-not-wired',
    make: () => createElement(ReportWindow, { series: SERIES, names: SET_NAMES, mayAct: true, onClose: noop }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.reports(SERIES_ID), refusal('dependency_unavailable', { dependency: 'comparison_reports' })),
  });

  // «Очередь»: the installation's AI queue under the block «Сравнение»
  push({ name: 'comparison-ai-queue-block-view', make: () => createElement(ComparisonAiQueueBlockView, { queue: aiQueue() }) });
  push({ name: 'comparison-ai-queue-block-empty', make: () => createElement(ComparisonAiQueueBlockView, { queue: { items: [], queued: 0, running: 0, paused: 0 } }) });
  push({ name: 'comparison-ai-queue-block-loaded', make: () => createElement(ComparisonAiQueueBlock), seedClient: (c) => c.setQueryData(COMPARISON_KEYS.aiQueue(), aiQueue()) });
  push({ name: 'comparison-ai-queue-block-not-wired', make: () => createElement(ComparisonAiQueueBlock), seedClient: (c) => seedError(c, COMPARISON_KEYS.aiQueue(), refusal('dependency_unavailable', { dependency: 'comparison_launch_queue' })) });
  push({ name: 'comparison-ai-queue-block-failed', make: () => createElement(ComparisonAiQueueBlock), seedClient: (c) => seedError(c, COMPARISON_KEYS.aiQueue(), refusal('internal_error')) });
  push({ name: 'comparison-ai-queue-block-cold', make: () => createElement(ComparisonAiQueueBlock) });
  return out;
}

const SERIES_ID_ = SERIES.series_id;
const SERIES_ID = SERIES_ID_;
const TRANSITION_12_ = uid('ctn', 1);
const JOB_ID_ = job().job_id;

/** The AI caches of each of the thirteen sets of the overview: a job in a different state in each cell. */
function seedAiRows(client: QueryClient): void {
  const states = ['queued', 'running', 'paused', 'completed', 'completed', 'failed', 'cancelled'] as const;
  overview().sets.forEach((set, index) => {
    const seriesId = uid('cser', index + 1);
    const state = states[index % states.length] as (typeof states)[number];
    const failed = index % 7 === 4 ? 2 : 0;
    client.setQueryData(COMPARISON_KEYS.aiPair(PROJECT_UID, set.document_uid), {
      document_uid: set.document_uid,
      job: job({ job_id: uid('cai', 20 + index), method: 'pair_check', state, counts: { total: 6, done: 3, failed, unknown: 0 }, ...(state === 'paused' ? { pause_reason: 'overrun' as const } : {}) }),
      counts: { questions: 6, answered: 5, pairs: 2, hints: 2, against: 1, failed, reused: 1 },
    });
    client.setQueryData(COMPARISON_KEYS.seriesList(PROJECT_UID, set.document_uid), series({ series_id: seriesId, document_uid: set.document_uid }));
    const changesState = states[(index + 3) % states.length] as (typeof states)[number];
    client.setQueryData(COMPARISON_KEYS.aiSheets(seriesId), sheetChanges({
      series_id: seriesId,
      job: job({ job_id: uid('cai', 40 + index), state: changesState, ...(changesState === 'queued' ? { queue_position: index + 1 } : {}), counts: { total: 12, done: 6, failed: index % 7 === 0 ? 1 : 0, unknown: 0 } }),
    }));
    const reportStates = ['running', 'completed', 'paused', 'partial', 'failed', 'cancelled', 'queued'] as const;
    client.setQueryData(COMPARISON_KEYS.reports(seriesId), [report({ report_id: uid('crt', 50 + index), series_id: seriesId, state: reportStates[index % reportStates.length] as (typeof reportStates)[number] })]);
  });
}

export const COMPARISON_SHAPES: readonly ComparisonShape[] = [
  // the page: the project, the tabs, the module
  { name: 'version-compare-projects', make: page_({ projectUid: PROJECT_UID }), seedClient: (c) => seedComparison(c) },
  { name: 'version-compare-module-not-wired', make: page_(PROJECT_AT), seedClient: (c) => seedComparison(c, { overview: 'wired-not' }) },
  { name: 'version-compare-read-failed', make: page_(PROJECT_AT), seedClient: (c) => seedComparison(c, { overview: 'error' }) },
  { name: 'version-compare-projects-read-failed', make: page_(undefined), seedClient: (c) => seedComparison(c, { projects: 'error', overview: 'none' }) },
  { name: 'version-compare-module-off', make: page_(PROJECT_AT), seedClient: (c) => seedComparison(c, { modules: 'none' }) },
  { name: 'version-compare-reader', make: page_(PROJECT_AT), seedClient: (c) => seedComparison(c, { account: READER }) },
  { name: 'version-compare-sheets', make: page_(SHEETS_AT), seedClient: (c) => seedComparison(c, { sheets: true }) },
  {
    name: 'version-compare-sheets-not-wired',
    make: page_(SHEETS_AT),
    seedClient: (c) => {
      seedComparison(c);
      seedError(c, COMPARISON_KEYS.matrix(PROJECT_UID, DOCUMENT_UID), refusal('dependency_unavailable', { dependency: 'comparison_matrix' }));
    },
  },
  { name: 'version-compare-sheets-cold', make: page_(SHEETS_AT), seedClient: (c) => seedComparison(c) },
  { name: 'version-compare-upload-single', make: page_({ ...PROJECT_AT, upload: 'single' }), seedClient: (c) => seedComparison(c) },
  { name: 'version-compare-upload-batch', make: page_({ ...PROJECT_AT, upload: 'batch' }), seedClient: (c) => seedComparison(c) },

  // «Проекты и этапы»
  { name: 'projects-and-stages-filtered', make: () => createElement(ProjectsAndStagesView, projectsProps({ view: { ...INITIAL_VIEW, filter: 'waiting', query: '133' } })) },
  { name: 'projects-and-stages-restart-asked', make: () => createElement(ProjectsAndStagesView, projectsProps({ confirming: overview().sets[5] as never, failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_series_active' })) })) },
  { name: 'projects-and-stages-reader', make: () => createElement(ProjectsAndStagesView, projectsProps({ mayAct: false })) },
  { name: 'projects-and-stages-empty', make: () => createElement(ProjectsAndStagesView, projectsProps({ overview: overview({ sets: [], pending_uploads: [] }) })) },
  { name: 'projects-and-stages-nothing-found', make: () => createElement(ProjectsAndStagesView, projectsProps({ view: { ...INITIAL_VIEW, query: 'нет такого шифра' } })) },

  // «Сравнение листов»
  { name: 'sheets-tab', make: () => createElement(SheetsTabView, sheetsProps()) },
  { name: 'sheets-tab-only-changed', make: () => createElement(SheetsTabView, sheetsProps({ onlyChanged: true, clickNote: 'У листа нет пары в версии №2.' })) },
  {
    name: 'sheets-tab-draft-refused',
    make: () => createElement(SheetsTabView, sheetsProps({ draft: DRAFT, draftFailure: STALE_FAILURE, notice: 'Сопоставление изменилось, пока вы правили.', dropped: [{ kind: 'unlink', page: page(V2, 40) }] })),
  },
  {
    name: 'sheets-tab-with-the-viewer-and-the-order-dialog',
    make: () =>
      createElement(SheetsTabView, sheetsProps({
        viewer: createElement(ComparisonViewer, { pair: comparedPair({ sheet_pair_id: PAIR_ID }) }),
        orderDialog: createElement(VersionOrderDialogView, { heading: '133/23-ГК-ЭМ1', source: 'expert', rows: [{ versionUid: V1, name: '№1', file: 'ЭМ-изм0.pdf', pages: 7 }], changed: true, pending: false, failure: null, onMove: noop, onSave: noop, onCancel: noop }),
      })),
  },
  { name: 'sheets-tab-restart-asked', make: () => createElement(SheetsTabView, sheetsProps({ confirmingRestart: true })) },
  { name: 'sheets-tab-applying', make: () => createElement(SheetsTabView, sheetsProps({ draft: DRAFT, applying: true })) },
  { name: 'sheets-tab-reader', make: () => createElement(SheetsTabView, sheetsProps({ mayEdit: false, series: series({ state: 'paused' }) })) },
  { name: 'sheets-tab-no-series', make: () => createElement(SheetsTabView, sheetsProps({ series: null, pairs: null, sides: { a: V2, b: V2 } })) },
  {
    name: 'sheets-tab-series-stale-all-states',
    make: () =>
      createElement(SheetsTabView, sheetsProps({
        sides: { a: V1, b: V3 },
        series: series({
          state: 'failed', failure_reason: 'some_code', stale_reasons: ['order_changed', 'matrix_changed', 'profiles_changed'],
          transitions: [
            transition({ transition_id: uid('ctn', 11), source_version_uid: V1, target_version_uid: V2, state: 'queued', items_done: 0, items_total: 0, verdict: undefined as never }),
            transition({ transition_id: uid('ctn', 12), source_version_uid: V2, target_version_uid: V3, state: 'running', items_done: 3, items_total: 7, verdict: ['incomplete'] }),
            transition({ transition_id: uid('ctn', 13), source_version_uid: V1, target_version_uid: V2, state: 'failed', failure_reason: 'some_code', verdict: undefined as never }),
            transition({ transition_id: uid('ctn', 14), source_version_uid: V2, target_version_uid: V3, state: 'cancelled', verdict: ['content_same'] }),
            transition({ transition_id: uid('ctn', 16), source_version_uid: V2, target_version_uid: V3, state: 'completed', verdict: ['zones_only', 'different', 'composition_changed', 'needs_review', 'calculation_failed', 'incomplete'] }),
            transition({ transition_id: uid('ctn', 15), source_version_uid: V2, target_version_uid: V3, state: 'completed', summary: { sheets: 3, compared: 3, same: 3, zones_only: 0, different: 0, style_only: 0, needs_review: 0, added: 0, removed: 0, failed: 0 }, verdict: ['content_same'] }),
          ],
        }),
      })),
  },
  { name: 'sheets-tab-matrix-absent', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ state: 'absent', rows: [], progress: { ready: 0, total: 0, failed: 0 } }), series: null, pairs: null })) },
  { name: 'sheets-tab-matrix-building', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ state: 'building', rows: [], progress: { ready: 10, total: 24, failed: 1 } }), series: null, pairs: null })) },
  { name: 'sheets-tab-matrix-stale', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ state: 'stale', stale_reasons: ['order_changed', 'profiles_changed', 'algorithm_changed'] }) })) },
  { name: 'sheets-tab-matrix-failed', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ state: 'failed', failure_reason: 'some_code', rows: [] }), series: null, pairs: null })) },
  { name: 'sheets-tab-matrix-empty', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ rows: [], unassigned_pages: [], orphaned_edit_ids: [] }), edits: [] })) },
  ...COMPARISON_SERIES_STATE_VALUES.map(seriesOf),

  // the order dialog and the opened pair
  { name: 'version-order-dialog-expert', make: () => createElement(VersionOrderDialogView, { heading: '133/23-ГК-ЭМ1', source: 'expert', rows: [{ versionUid: V1, name: '№1', file: 'ЭМ-изм0.pdf', pages: 7 }, { versionUid: V2, name: '№2', file: '', pages: 8 }], changed: true, pending: false, failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_version_order_stale' })), onMove: noop, onSave: noop, onCancel: noop }) },
  { name: 'version-order-dialog-proposal', make: () => createElement(VersionOrderDialogView, { heading: '133/23-ГК-ЭМ1', source: 'proposal', rows: [{ versionUid: V1, name: '№1', file: 'ЭМ-изм0.pdf', pages: 7 }], changed: false, pending: true, failure: null, onMove: noop, onSave: noop, onCancel: noop }) },
  { name: 'version-order-dialog-own-order', make: () => createElement(VersionOrderDialogView, { heading: '133/23-ГК-ЭМ1', rows: [{ versionUid: V1, name: '№1', file: 'ЭМ-изм0.pdf', pages: 7 }], changed: false, pending: false, failure: null, onMove: noop, onSave: noop, onCancel: noop }) },
  {
    name: 'pair-viewer-pending',
    make: () => createElement(PairViewerSlot, { pairId: PAIR_ID, siblings: pairs(), renderViewer: () => null, onOpen: noop, onClose: noop }),
  },
  {
    name: 'pair-viewer-opened',
    make: () =>
      createElement(PairViewerSlot, {
        pairId: PAIR_ID,
        siblings: pairs(),
        renderViewer: ({ pair, rasterSize, navigation }) => createElement(ComparisonViewer, { pair, navigation, ...(rasterSize === undefined ? {} : { rasterSize }) }),
        onOpen: noop,
        onClose: noop,
      }),
    seedClient: (c) => c.setQueryData(COMPARISON_KEYS.pair(PAIR_ID), comparedPair({ sheet_pair_id: PAIR_ID })),
  },
  {
    name: 'pair-viewer-refused',
    make: () => createElement(PairViewerSlot, { pairId: PAIR_ID, siblings: [], renderViewer: () => null, onOpen: noop, onClose: noop }),
    seedClient: (c) => seedError(c, COMPARISON_KEYS.pair(PAIR_ID), refusal('dependency_unavailable', { dependency: 'comparison_series' })),
  },

  // the upload dialogs
  { name: 'comparison-upload-picked', make: () => createElement(UploadDialogView, dialogProps({ mode: 'batch', groups: [{ group: 'Проекты/ЭМ', files: [], bytes: 3 * 1024 * 1024 }], skipped: 2, problem: 'file_too_large', compare: true, unfinished: [upload()] })) },
  { name: 'comparison-upload-single-picked', make: () => createElement(UploadDialogView, dialogProps({ groups: [{ group: '', files: [], bytes: 1024 }], mayAct: false })) },
  { name: 'comparison-upload-hashing', make: () => createElement(UploadDialogView, dialogProps({ phase: 'hashing', hashing: { done: 1, total: 4 } })) },
  { name: 'comparison-upload-loading', make: () => createElement(UploadDialogView, dialogProps({ phase: 'watching', loading: true })) },
  {
    name: 'comparison-upload-sending',
    make: () => createElement(UploadDialogView, dialogProps({ mode: 'batch', phase: 'sending', upload: upload({ state: 'uploading', compare_after_preparation: true }), progress: new Map([[uid('cuf', 2), { done: 5, total: 10 }]]), fileFailures: new Map([[uid('cuf', 3), STALE_FAILURE]]) })),
  },
  { name: 'comparison-upload-stopped', make: () => createElement(UploadDialogView, dialogProps({ phase: 'stopped', upload: upload({ state: 'uploading' }), missing: [uid('cuf', 2)], failure: comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_upload_active' })), notice: 'Загрузка удалена.' })) },
  { name: 'comparison-upload-single-proposal', make: () => createElement(UploadDialogView, dialogProps({ phase: 'watching', upload: upload(), sets: proposalSets(), fileNames: NAMES })) },
  { name: 'comparison-upload-batch-proposal', make: () => createElement(UploadDialogView, dialogProps({ mode: 'batch', phase: 'watching', upload: upload({ state: 'processing' }), sets: proposalSets(), fileNames: NAMES })) },
  { name: 'comparison-upload-reading', make: () => createElement(UploadDialogView, dialogProps({ phase: 'watching', upload: upload({ state: 'uploading' }), sets: [] })) },
  ...COMPARISON_UPLOAD_STATE_VALUES.map(uploadOf),

  // «Очередь»
  { name: 'comparison-queue-block-loaded', make: () => createElement(ComparisonQueueBlock), seedClient: (c) => c.setQueryData(COMPARISON_KEYS.queue(), queueSummary({ paused: true })) },
  ...(['none', 'versions', 'versions,stages'] as const).map(
    (modules): ComparisonShape => ({
      name: `comparison-queue-block-${modules}`,
      make: () => createElement(ComparisonQueueBlockView, { summary: queueSummary({ modules, kinds: [], counts: { cancelled: 0, failed: 0, leased: 0, paused: 0, queued: 0, retry_wait: 0, running: 0, spend_unknown: 0, succeeded: 0 } }) }),
    }),
  ),
  { name: 'comparison-queue-block-cold', make: () => createElement(ComparisonQueueBlock) },
  { name: 'comparison-queue-block-not-wired', make: () => createElement(ComparisonQueueBlock), seedClient: (c) => seedError(c, COMPARISON_KEYS.queue(), refusal('dependency_unavailable', { dependency: 'comparison_overview' })) },
  { name: 'comparison-queue-block-failed', make: () => createElement(ComparisonQueueBlock), seedClient: (c) => seedError(c, COMPARISON_KEYS.queue(), refusal('internal_error')) },

  // ---- `CMP-VC-UI-02`: the AI layer
  ...aiShapes(),

  // A-12: the version-scoped screen once the matrix holds the sheet pairs
  ...([false, true] as const).flatMap((handedOver) =>
    ([false, true] as const).map(
      (approved): ComparisonShape => ({
        name: `version-comparison-${handedOver ? 'handed-over' : 'old-controls'}-${approved ? 'approved' : 'proposed'}`,
        make: () => createElement(ComparisonResult, { comparison: a12Comparison(approved) as never, onPage: noop, carry: null, mayApprove: true, handedOver }),
      }),
    ),
  ),
];

function a12Comparison(approved: boolean): unknown {
  return {
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, source_version_uid: V1, target_version_uid: V2, mode: 'version', outcome: 'compared',
    refusal: null, comparison_sha256: 'e'.repeat(64),
    sheets: [{ status: 'unchanged', source_page_number: 3, target_page_number: 3, suggestion_sha256: 'f'.repeat(64), basis: 'sheet_number' }],
    approved_pairs: {
      evidence_state: approved ? 'sealed' : 'none', link_revision: approved ? 1 : null, raw_evidence_seal_sha256: approved ? 'd'.repeat(64) : null, summary: null,
      items: approved
        ? [{ sheet_link_id: 'lnk_1', source_page_number: 3, target_page_number: 3, approved_by_label: 'Сьютова Е.', approved_at: '2026-10-20T10:00:00Z', state: 'verified', diff: null }]
        : [],
    },
    sheet_diffs: null, findings: null, source: null, target: null,
  };
}


