'use client';

/**
 * The cells of steps 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений» and 7 «Сводка и отчёт»
 * (`frontend/static/js/version-comparison-projects.js:65-115`, `:176-208`, `:460-530`).
 *
 * A row reads, once, what the three cells need — the newest pair-check job, the newest series, the AI description's progress, the
 * newest report — and {@link aiStepCell} turns it into a word, a note, a tone and the buttons the server would accept. A read the
 * module does not serve yet (`503 dependency_unavailable`) is the module's state in that cell («ещё недоступно», the sentence in
 * its `title`), never a red error and never a crash; any other failed read says so in words.
 */

import type { ReactNode } from 'react';

import type { ComparisonOverviewSet, ComparisonSeriesId, ComparisonStepId } from '@/shared/api';
import type { AiStepAction, AiStepCell, AiStepId, ComparisonFailure, QueueBadge } from '@/entities/version-series';
import {
  TONE_BADGES,
  aiStepCell,
  canSelect,
  comparisonFailure,
  selectionKey,
  ROW_SELECT_TITLE,
  STEP_LABELS,
  useAiPairCheck,
  useAiSheetChanges,
  useLatestSeries,
  useReports,
} from '@/entities/version-series';

import styles from './ai-steps.module.css';
import ownStyles from './version-series.module.css';

export const UNAVAILABLE_CELL = 'ещё недоступно';
export const UNREAD_CELL = 'не прочиталось';

export interface AiRowCell {
  readonly cell: AiStepCell;
  readonly failure: ComparisonFailure | null;
}

export interface AiRow {
  readonly seriesId: ComparisonSeriesId | null;
  /** The «Сводка изменений (MD)» exists: step 6 is done or partial. */
  readonly summaryReady: boolean;
  readonly cells: Readonly<Record<AiStepId, AiRowCell>>;
}

function overviewOf(set: ComparisonOverviewSet, step: ComparisonStepId) {
  return set.steps.find((entry) => entry.step === step);
}

/** What the three cells of a row need, read from the AI layer (and the overview's own word where it has one). */
export function useAiRow(projectUid: Parameters<typeof useAiPairCheck>[0], set: ComparisonOverviewSet): AiRow {
  const matrixState = overviewOf(set, 'matrix')?.state;
  const matrixReady = matrixState === 'done' || matrixState === 'attention';
  const seriesStep = overviewOf(set, 'series');
  const seriesExists = seriesStep !== undefined && !['not_started', 'blocked', 'not_applicable'].includes(seriesStep.state);
  const versions = set.version_count;
  const pair = useAiPairCheck(projectUid, set.document_uid, matrixReady && versions >= 2);
  const latest = useLatestSeries(projectUid, seriesExists ? set.document_uid : null);
  const seriesId = latest.data?.series_id ?? null;
  const sheets = useAiSheetChanges(seriesId);
  const reports = useReports(seriesId, seriesId !== null);

  const started = (reports.data ?? []).find((report) => report.state !== 'draft');
  const changesCell = aiStepCell({
    step: 'ai_changes',
    overviewState: overviewOf(set, 'ai_changes')?.state ?? 'not_applicable',
    versions,
    matrixReady,
    seriesKnown: seriesId !== null,
    seriesChanged: seriesStep?.counts?.with_changes,
    job: sheets.data?.job,
    sheets: sheets.data?.transitions,
    summaryReady: false,
    aiChangesBusy: false,
  });
  const summaryReady = changesCell.state === 'done' || changesCell.state === 'partial';
  const aiChangesBusy = changesCell.state === 'running' || changesCell.state === 'queued' || changesCell.state === 'pausing';
  const pairCell = aiStepCell({
    step: 'ai_pairs',
    overviewState: overviewOf(set, 'ai_pairs')?.state ?? 'not_applicable',
    versions,
    matrixReady,
    seriesKnown: seriesId !== null,
    job: pair.data?.job,
    pairCounts: pair.data?.counts,
    summaryReady: false,
    aiChangesBusy: false,
  });
  const reportCell = aiStepCell({
    step: 'report',
    overviewState: overviewOf(set, 'report')?.state ?? 'not_applicable',
    versions,
    matrixReady,
    seriesKnown: seriesId !== null,
    summaryReady,
    aiChangesBusy,
    report: started,
  });
  const failure = (error: unknown): ComparisonFailure | null => (error === null || error === undefined ? null : comparisonFailure(error));
  return {
    seriesId,
    summaryReady,
    cells: {
      ai_pairs: { cell: pairCell, failure: failure(pair.error) },
      ai_changes: { cell: changesCell, failure: failure(sheets.error) },
      report: { cell: reportCell, failure: failure(reports.error) },
    },
  };
}

export interface AiActRequest {
  readonly set: ComparisonOverviewSet;
  readonly step: AiStepId;
  readonly action: AiStepAction;
  readonly cell: AiStepCell;
  readonly seriesId: ComparisonSeriesId | null;
}

export interface SelectBoxProps {
  readonly set: ComparisonOverviewSet;
  readonly step: ComparisonStepId;
  readonly selected: boolean;
  readonly onSelect: (key: string, on: boolean) => void;
}

/** The checkbox of a row and a step (`vcp-cellsel`, `:376-396`). */
export function SelectBox({ set, step, selected, onSelect }: SelectBoxProps) {
  return (
    <label className={styles.cellSelect} title={ROW_SELECT_TITLE(STEP_LABELS[step])} onClick={(event) => event.stopPropagation()}>
      <input
        type="checkbox"
        checked={selected}
        data-select-step={step}
        aria-label={`${ROW_SELECT_TITLE(STEP_LABELS[step])}`}
        onChange={(event) => onSelect(selectionKey(set.document_uid, step), event.target.checked)}
      />
    </label>
  );
}

export interface AiStepCellViewProps {
  readonly set: ComparisonOverviewSet;
  readonly step: AiStepId;
  readonly row: AiRow;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly selected: boolean;
  readonly badge: QueueBadge | null;
  readonly onSelect: (key: string, on: boolean) => void;
  readonly onAct: (request: AiActRequest) => void;
}

export function AiStepCellView({ set, step, row, mayAct, busy, selected, badge, onSelect, onAct }: AiStepCellViewProps) {
  const { cell, failure } = row.cells[step];
  const seriesChanged = overviewOf(set, 'series')?.counts?.with_changes;
  const selectable = canSelect(step, { mayAct, versions: set.version_count, state: cell.state, seriesChanged, queued: badge !== null });
  if (failure !== null) {
    // The read is not served (or failed): the cell says so; its sentence is the `title`, and no button is drawn.
    return (
      <div className={ownStyles.step} data-step={step} data-comparison-module={failure.moduleUnavailable ? 'unavailable' : 'failed'}>
        <span className={styles.cellUnavailable} title={failure.detail}>
          {failure.moduleUnavailable ? UNAVAILABLE_CELL : UNREAD_CELL}
        </span>
      </div>
    );
  }
  const shown = cell.view;
  const pausing = cell.pauseReason;
  return (
    <div className={ownStyles.step} data-step={step} data-step-state={cell.state}>
      {selectable ? (
        <SelectBox set={set} step={step} selected={selected} onSelect={onSelect} />
      ) : badge !== null ? (
        <span className={styles.queueBadge} title={`Очередь запуска: ${badge.title}`} data-queue-badge="">
          {badge.short}
        </span>
      ) : null}
      <span
        className={`am-badge am-badge--${TONE_BADGES[shown.tone]}`}
        data-step-state={cell.state}
        {...(pausing === null ? {} : { 'data-ai-pause-reason': pausing })}
        title={shown.title === '' ? undefined : shown.title}
      >
        {shown.icon} {shown.text}
      </span>
      {shown.note === '' ? null : <span className={ownStyles.note}>{shown.note}</span>}
      {cell.progress === null ? null : (
        <progress className={styles.bar} value={cell.progress.done} max={cell.progress.total} aria-label="Ход шага" />
      )}
      {mayAct && cell.actions.length > 0 ? (
        <span className={ownStyles.actions}>
          {cell.actions.map((action): ReactNode => (
            <button
              key={action.id}
              type="button"
              className="am-button am-button--small am-button--quiet"
              disabled={busy || (step === 'report' && action.id === 'start' && cell.state === 'not_started' && row.cells.ai_changes.cell.state === 'running')}
              title={action.title}
              data-step-action={action.id}
              onClick={(event) => {
                event.stopPropagation();
                onAct({ set, step, action, cell, seriesId: row.seriesId });
              }}
            >
              {action.label}
            </button>
          ))}
        </span>
      ) : null}
    </div>
  );
}
