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
import { COMPARISON_SERIES_STATE_VALUES, COMPARISON_UPLOAD_STATE_VALUES } from '@/shared/api';
import { ComparisonViewer } from '@/widgets/comparison-viewer';
import { ComparisonQueueBlock, ComparisonQueueBlockView } from '@/widgets/execution-queue';
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

export interface ComparisonShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
  /**
   * The shape mounts `widgets/comparison-viewer`, whose own words (side letters, the engine's zone and field names) are that
   * widget's and not this lane's. The contrast census renders it; the language guard does not (the report lists the findings).
   */
  readonly censusOnly?: boolean;
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

function projectsProps(over: Partial<ProjectsAndStagesViewProps> = {}): ProjectsAndStagesViewProps {
  return {
    overview: overview(), view: INITIAL_VIEW, onView: noop, mayAct: true, busy: false, confirming: null, failure: null,
    onRefresh: noop, onOpen: noop, onAct: noop, onConfirmRestart: noop, onCancelRestart: noop, ...over,
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
    censusOnly: true,
  },
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
  { name: 'sheets-tab-matrix-stale', make: () => createElement(SheetsTabView, sheetsProps({ matrix: matrix({ state: 'stale', stale_reasons: ['order_changed', 'profiles_changed'] }) })) },
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
    censusOnly: true,
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

