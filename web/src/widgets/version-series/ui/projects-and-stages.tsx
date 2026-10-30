'use client';

/**
 * Tab «Проекты и этапы» (plan §1.1; `frontend/static/js/version-comparison-projects.js`): the counters, the
 * totals, the search, the filters, the sort, «Обновить», the legend, the strip of uploads that are not yet in the
 * list, and the table of document sets with their steps.
 *
 * One row per document set of the chosen project, known by its «шифр» (a designation is metadata, never an
 * identity: the row's identity is the document). The columns are the original's seven steps; the cells of steps 4, 6
 * and 7 are drawn by `ai-step-cell.tsx` from the AI layer, with their dialogs (`ai-dialogs.tsx`: every AI start shows the
 * estimate and the consent line). A row click opens the second tab for that set. The buttons of a step are the commands of
 * `entities/version-series` and are offered to an expert only; «Заново» asks first, as the original does. Above the table:
 * the strips «Очередь запуска» and «Очередь «ИИ-описание изменений»» and the selection bar «Запустить выбранные по очереди».
 *
 * {@link ProjectsAndStagesView} is the whole markup, driven by props, so every state can be rendered by the static
 * harness; {@link ProjectsAndStages} adds the query, the view state and the commands.
 */

import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import type {
  ComparisonAiQueue,
  ComparisonLaunchEntry,
  ComparisonLaunchQueue,
  ComparisonOverview,
  ComparisonOverviewSet,
  ComparisonOverviewStep,
  ComparisonAiJobId,
  ComparisonReportId,
  ComparisonSeriesId,
  ComparisonStepId,
  DocumentUid,
  ProjectUid,
} from '@/shared/api';
import { EmptyState, LoadingState } from '@/shared/ui';
import type { ComparisonFailure, EstimateScope, OverviewView, SelectionItem, SortKey, StepActionId } from '@/entities/version-series';
import {
  AI_METHOD_LABELS,
  AI_PAUSE_ADVICE,
  AI_STEP_IDS,
  CONFIRM_LABELS,
  RESTART_CONFIRM_LABELS,
  useReportCommand,
  COLUMN_SELECT_TITLE,
  INITIAL_VIEW,
  OVERVIEW_FILTERS,
  SELECTABLE_STEPS,
  SELECTION_CLEAR_LABEL,
  SELECTION_RUN_LABEL,
  SELECTION_RUN_TITLE,
  canSelect,
  columnState,
  queueBadge,
  selectionKey,
  useAiJobAct,
  useAiQueue,
  useDownload,
  useLaunchQueue,
  useQueueCommand,
  RESTART_CONFIRM_ACTION,
  RESTART_CONFIRM_TEXT,
  RESTART_CONFIRM_TITLE,
  SHOWN_STEPS,
  SORT_PRESETS,
  STEP_HINTS,
  STEP_LABELS,
  STEP_NUMBERS,
  TONE_BADGES,
  UPLOAD_STATE_LABELS,
  codeOf,
  comparisonFailure,
  countsOf,
  groupOf,
  inScope,
  marksOf,
  nextSort,
  nextStepSentence,
  parseSort,
  sortValue,
  stepActions,
  stepView,
  useComparisonOverview,
  usePrepareMatrix,
  useSeriesAct,
  useStartSeries,
  visibleSets,
} from '@/entities/version-series';

import type { AiActRequest, AiRow } from './ai-step-cell';
import { AiStepCellView, SelectBox, useAiRow } from './ai-step-cell';
import type { AiStartDialogProps } from './ai-dialogs';
import { AiStartDialog, ReportDraftDialog, SelectionDialog } from './ai-dialogs';
import { AiQueueStrip, LaunchQueueStrip } from './queue-strips';
import { SpecificationPanel } from './specification-panel';
import type { LaunchAct } from './queue-strips';
import { CommandRefusal, FailureState } from './module-state';
import aiStyles from './ai-steps.module.css';
import styles from './version-series.module.css';

/** «обновлено HH:MM:SS», in UTC like every stamp of this application (`formatInstant`). */
export function clockOf(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : `${parsed.toISOString().slice(11, 19)} UTC`;
}

const GROUP_BADGES = { waiting: 'pending', running: 'active', failed: 'failed', ready: 'ok' } as const;

const LEGEND: readonly { readonly icon: string; readonly text: string }[] = [
  { icon: '✓', text: 'готово' },
  { icon: '!', text: 'есть что проверить' },
  { icon: '⟳', text: 'идёт' },
  { icon: '○', text: 'не запускалось' },
  { icon: '✕', text: 'ошибка' },
];

export interface ProjectsAndStagesViewProps {
  readonly projectUid: ProjectUid;
  readonly overview: ComparisonOverview;
  readonly view: OverviewView;
  readonly onView: (view: OverviewView) => void;
  /** An expert on a module that is on: the buttons of the steps are drawn. */
  readonly mayAct: boolean;
  readonly busy: boolean;
  /** The set whose «Заново» waits for the reader's word. */
  readonly confirming: ComparisonOverviewSet | null;
  readonly failure: ComparisonFailure | null;
  readonly onRefresh: () => void;
  readonly onOpen: (documentUid: DocumentUid) => void;
  readonly onAct: (set: ComparisonOverviewSet, action: StepActionId) => void;
  readonly onConfirmRestart: () => void;
  readonly onCancelRestart: () => void;
  // ---- wave C2: selection, the queues, the AI steps and their dialogs
  /** The keys (`document|step`) of the ticked cells. */
  readonly selected: ReadonlySet<string>;
  readonly onSelect: (key: string, on: boolean) => void;
  readonly onSelectColumn: (keys: readonly string[], on: boolean) => void;
  readonly onClearSelection: () => void;
  readonly onRunSelected: () => void;
  /** The cells of steps 4, 6 and 7 that a tick can reach, reported by the rows (a row knows its own AI state). */
  readonly selectableAi: ReadonlySet<string>;
  readonly onSelectable: (key: string, on: boolean) => void;
  readonly launchQueue: ComparisonLaunchQueue | undefined;
  readonly queueOpen: boolean;
  readonly queueBusy: boolean;
  readonly queueFailure: ComparisonFailure | null;
  readonly onQueueToggle: () => void;
  readonly onQueueAct: (act: LaunchAct) => void;
  readonly onQueueRemove: (entry: ComparisonLaunchEntry) => void;
  readonly onQueueConfirm: (entry: ComparisonLaunchEntry) => void;
  readonly aiQueue: ComparisonAiQueue | undefined;
  readonly onAiAct: (request: AiActRequest) => void;
  readonly onSummary: (seriesId: string) => void;
  /** The open estimate dialog, or `null`. */
  readonly dialog: ReactNode;
}

function Chip({ set }: { readonly set: ComparisonOverviewSet }) {
  const group = groupOf(set);
  return (
    <span
      className={`am-badge am-badge--${GROUP_BADGES[group]}`}
      data-overview-group={group}
      {...(set.next_step === undefined ? {} : { 'data-next-step': set.next_step })}
    >
      {nextStepSentence(set)}
    </span>
  );
}

function StepCell({
  set,
  entry,
  mayAct,
  busy,
  onAct,
  selected,
  onSelect,
  badge,
}: {
  readonly set: ComparisonOverviewSet;
  readonly entry: ComparisonOverviewStep | undefined;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly onAct: (set: ComparisonOverviewSet, action: StepActionId) => void;
  readonly selected: ReadonlySet<string>;
  readonly onSelect: (key: string, on: boolean) => void;
  readonly badge: ReturnType<typeof queueBadge>;
}) {
  if (entry === undefined) return <span className={styles.muted}>—</span>;
  const shown = stepView(entry.step, entry.state, entry.counts);
  const actions = mayAct ? stepActions(entry.step, entry.state, entry.counts) : [];
  const selectable =
    entry.step === 'series' &&
    canSelect('series', { mayAct, versions: set.version_count, state: entry.state, queued: badge !== null });
  return (
    <div className={styles.step} data-step={entry.step}>
      {selectable ? (
        <SelectBox set={set} step="series" selected={selected.has(selectionKey(set.document_uid, 'series'))} onSelect={onSelect} />
      ) : entry.step === 'series' && badge !== null ? (
        <span className={aiStyles.queueBadge} title={`Очередь запуска: ${badge.title}`} data-queue-badge="">{badge.short}</span>
      ) : null}
      <span
        className={`am-badge am-badge--${TONE_BADGES[shown.tone]}`}
        data-step-state={entry.state}
        title={shown.title === '' ? undefined : shown.title}
      >
        {shown.icon} {shown.text}
      </span>
      {shown.note === '' ? null : <span className={styles.note}>{shown.note}</span>}
      {actions.length === 0 ? null : (
        <span className={styles.actions}>
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              className="am-button am-button--small am-button--quiet"
              disabled={busy}
              data-step-action={action.id}
              onClick={(event) => {
                event.stopPropagation();
                onAct(set, action.id);
              }}
            >
              {action.label}
            </button>
          ))}
        </span>
      )}
    </div>
  );
}

function SortHeader({
  label,
  hint,
  sortKey,
  view,
  onView,
}: {
  readonly label: string;
  readonly hint: string;
  readonly sortKey: SortKey;
  readonly view: OverviewView;
  readonly onView: (view: OverviewView) => void;
}) {
  const active = view.sort.key === sortKey;
  const direction = active ? (view.sort.direction === 'asc' ? ' ▲' : ' ▼') : '';
  return (
    <th scope="col" aria-sort={active ? (view.sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button
        type="button"
        className={styles.sortButton}
        title={hint}
        onClick={() => onView({ ...view, sort: nextSort(view.sort, sortKey) })}
      >
        {label}
        {direction}
      </button>
    </th>
  );
}

/** One row of the table: the first columns as before, the cells of steps 4, 6 and 7 from the AI layer. */
function SetRow(props: ProjectsAndStagesViewProps & { readonly set: ComparisonOverviewSet }) {
  const { set, projectUid, mayAct, busy, selected, onSelect, onSelectable, launchQueue, onOpen, onAct, onAiAct, onSummary } = props;
  const row: AiRow = useAiRow(projectUid, set);
  const technical = useDownload();
  const entries = launchQueue?.entries ?? [];
  const badgeOf = (step: ComparisonStepId) => queueBadge(entries, set.document_uid, step);
  const seriesChanged = set.steps.find((entry) => entry.step === 'series')?.counts?.with_changes;
  // A row reports which of its AI cells a tick can reach; the header's «выбрать все» is made of these.
  const reach = AI_STEP_IDS.map((step) =>
    canSelect(step, { mayAct, versions: set.version_count, state: row.cells[step].cell.state, seriesChanged, queued: badgeOf(step) !== null }) &&
    row.cells[step].failure === null
      ? selectionKey(set.document_uid, step)
      : null,
  );
  const reachKey = reach.join(',');
  useEffect(() => {
    AI_STEP_IDS.forEach((step, index) => onSelectable(selectionKey(set.document_uid, step), reach[index] !== null));
  }, [reachKey]);
  return (
    <tr className={styles.row} data-document-uid={set.document_uid} onClick={() => onOpen(set.document_uid)}>
      <th scope="row" className={styles.code}>
        <button
          type="button"
          className={styles.open}
          title="Открыть сравнение листов этого комплекта."
          onClick={(event) => {
            event.stopPropagation();
            onOpen(set.document_uid);
          }}
        >
          {codeOf(set) === '' ? 'Комплект без шифра' : codeOf(set)}
        </button>
        <Chip set={set} />
        {row.summaryReady && row.seriesId !== null ? (
          <button
            type="button"
            className="am-button am-button--small am-button--quiet"
            title="Скачать «Сводку изменений (MD)»: все изменения комплекта от первой версии до последней одним файлом."
            data-summary-md=""
            onClick={(event) => {
              event.stopPropagation();
              onSummary(row.seriesId as string);
            }}
          >
            Сводка изменений (MD)
          </button>
        ) : null}
        {row.seriesId === null ? null : <div onClick={(event) => event.stopPropagation()} data-technical-downloads="">
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={technical.isPending} onClick={() => technical.mutate({ kind: 'technical', seriesId: row.seriesId as ComparisonSeriesId, format: 'xlsx', fileName: 'comparison-technical.xlsx' })}>Технический XLSX</button>
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={technical.isPending} onClick={() => technical.mutate({ kind: 'technical', seriesId: row.seriesId as ComparisonSeriesId, format: 'html', fileName: 'comparison-technical-html.zip' })}>HTML с изображениями (ZIP)</button>
          {technical.error === null ? null : <p role="alert">{comparisonFailure(technical.error).detail}</p>}
        </div>}
      </th>
      <td>
        <span>{set.version_count}</span>
        {set.updated_at === undefined ? null : <span className={styles.note}>{set.updated_at.slice(0, 10)}</span>}
      </td>
      {SHOWN_STEPS.map((step) => (
        <td key={step}>
          {step === 'ai_pairs' || step === 'ai_changes' || step === 'report' ? (
            <AiStepCellView
              set={set}
              step={step}
              row={row}
              mayAct={mayAct}
              busy={busy}
              selected={selected.has(selectionKey(set.document_uid, step))}
              badge={badgeOf(step)}
              onSelect={onSelect}
              onAct={onAiAct}
            />
          ) : (
            <StepCell
              set={set}
              entry={set.steps.find((entry) => entry.step === step)}
              mayAct={mayAct}
              busy={busy}
              onAct={onAct}
              selected={selected}
              onSelect={onSelect}
              badge={badgeOf(step)}
            />
          )}
          {step === 'ai_changes' && row.seriesId !== null ? <SpecificationPanel seriesId={row.seriesId} mayAct={mayAct} /> : null}
        </td>
      ))}
    </tr>
  );
}

export function ProjectsAndStagesView(props: ProjectsAndStagesViewProps) {
  const {
    overview, view, onView, mayAct, busy, confirming, failure, onRefresh, onConfirmRestart, onCancelRestart,
    selected, onSelectColumn, onClearSelection, onRunSelected, selectableAi,
    launchQueue, queueOpen, queueBusy, queueFailure, onQueueToggle, onQueueAct, onQueueRemove, onQueueConfirm, aiQueue, dialog,
  } = props;
  const scoped = inScope(overview.sets, view);
  const filtered = view.query.trim() !== '' || view.mark !== '';
  // With no search and no mark the counters are the server's; with either, the sets that pass them are counted here.
  const counts = filtered ? countsOf(scoped) : overview.counters;
  const rows = visibleSets(overview.sets, view);
  const marks = marksOf(overview.sets);
  const preset = parseSort(sortValue(view.sort));
  const entries = launchQueue?.entries ?? [];
  // The ticks that still reach something (a tick on a cell that has since become unavailable does not count, as in the original).
  const reachable = (step: ComparisonStepId): readonly string[] =>
    rows.flatMap((set) => {
      const key = selectionKey(set.document_uid, step);
      if (step === 'series') {
        const state = set.steps.find((entry) => entry.step === 'series')?.state;
        return state !== undefined &&
          canSelect('series', { mayAct, versions: set.version_count, state, queued: queueBadge(entries, set.document_uid, 'series') !== null })
          ? [key]
          : [];
      }
      return selectableAi.has(key) ? [key] : [];
    });
  const ticked = (step: ComparisonStepId): number => reachable(step).filter((key) => selected.has(key)).length;
  const total = SELECTABLE_STEPS.reduce((sum, step) => sum + ticked(step), 0);
  return (
    <div className={styles.projects} data-comparison-overview="">
      <div className={styles.tiles}>
        {OVERVIEW_FILTERS.map((filter) => (
          <button
            key={filter.key}
            type="button"
            className={styles.tile}
            aria-pressed={view.filter === filter.key}
            title={filter.hint}
            data-overview-filter={filter.key}
            onClick={() => onView({ ...view, filter: filter.key })}
          >
            <span className={styles.tileCount}>{counts[filter.key === 'all' ? 'all' : filter.key]}</span>
            <span className={styles.tileLabel}>{filter.label}</span>
          </button>
        ))}
        <div className={styles.tileInfo} title="Сколько всего версий у комплектов проекта и сколько переходов между соседними версиями.">
          <span className={styles.tileCount}>{overview.totals.versions}</span>
          <span className={styles.tileLabel}>версий · {overview.totals.transitions} переходов</span>
        </div>
      </div>

      <div className={styles.toolbar}>
        <input
          className={styles.search}
          type="search"
          value={view.query}
          placeholder="Поиск по шифру…"
          aria-label="Поиск по шифру"
          onChange={(event) => onView({ ...view, query: event.target.value })}
        />
        <label className={styles.control}>
          Марка
          <select value={view.mark} onChange={(event) => onView({ ...view, mark: event.target.value })}>
            <option value="">все</option>
            {marks.map((mark) => (
              <option key={mark.key} value={mark.key}>
                {mark.key} ({mark.count})
              </option>
            ))}
          </select>
        </label>
        <label className={styles.control}>
          Порядок
          <select
            value={preset === null ? sortValue(view.sort) : sortValue(preset)}
            onChange={(event) => {
              const chosen = parseSort(event.target.value);
              if (chosen !== null) onView({ ...view, sort: chosen });
            }}
          >
            {SORT_PRESETS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
            {preset === null ? <option value={sortValue(view.sort)}>по столбцу</option> : null}
          </select>
        </label>
        <span className={styles.refresh}>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onRefresh}>
            Обновить
          </button>
          <span className={styles.note}>обновлено {clockOf(overview.generated_at)}</span>
        </span>
      </div>

      {overview.pending_uploads.length === 0 ? null : (
        <div className={styles.pending} role="status" data-pending-uploads={overview.pending_uploads.length}>
          <strong>В загрузке, ещё не в списке проектов:</strong>
          <ul className={styles.pendingList}>
            {overview.pending_uploads.map((upload) => (
              <li key={upload.upload_id} data-upload-state={upload.state}>
                {UPLOAD_STATE_LABELS[upload.state]} · файлов {upload.declared_files} · комплектов {upload.sets_done} из{' '}
                {upload.sets_total}
              </li>
            ))}
          </ul>
        </div>
      )}

      {aiQueue !== undefined && aiQueue.items.length > 0 ? <AiQueueStrip queue={aiQueue} sets={overview.sets} /> : null}
      {launchQueue !== undefined && launchQueue.entries.length > 0 ? (
        <LaunchQueueStrip
          queue={launchQueue}
          sets={overview.sets}
          mayAct={mayAct}
          busy={queueBusy}
          open={queueOpen}
          failure={queueFailure}
          onToggle={onQueueToggle}
          onAct={onQueueAct}
          onRemove={onQueueRemove}
          onConfirm={onQueueConfirm}
        />
      ) : null}

      {failure === null ? null : <CommandRefusal failure={failure} />}

      {confirming === null ? null : (
        <div role="group" aria-label="Подтверждение пересчёта" className={styles.confirm} data-restart-confirm="">
          <p>
            <strong>{RESTART_CONFIRM_TITLE}</strong> · {codeOf(confirming)}
          </p>
          <p className="am-note">{RESTART_CONFIRM_TEXT}</p>
          <button type="button" className="am-button am-button--small" disabled={busy} onClick={onConfirmRestart}>
            {RESTART_CONFIRM_ACTION}
          </button>{' '}
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} onClick={onCancelRestart}>
            Отмена
          </button>
        </div>
      )}

      {dialog}

      {total === 0 ? null : (
        <div className={aiStyles.selectionBar} role="group" aria-label="Выбор шагов" data-selection-bar={total}>
          <strong>Выбрано: {total}</strong>
          {SELECTABLE_STEPS.filter((step) => ticked(step) > 0).map((step) => (
            <span key={step} className={styles.note}>
              · {STEP_LABELS[step]}: {ticked(step)}
            </span>
          ))}
          <span className={aiStyles.spacer} />
          <button type="button" className="am-button" title={SELECTION_RUN_TITLE} data-selection-run="" onClick={onRunSelected}>
            ▶ {SELECTION_RUN_LABEL}
          </button>
          <button type="button" className="am-button am-button--quiet" title="Снять все отмеченные галочки." onClick={onClearSelection}>
            {SELECTION_CLEAR_LABEL}
          </button>
        </div>
      )}

      {rows.length === 0 ? (
        <EmptyState
          title={overview.sets.length === 0 ? 'В проекте ещё нет версий для сравнения.' : 'Ни один комплект не подходит под выбранное.'}
          detail={
            overview.sets.length === 0
              ? 'Нажмите «Загрузить проект со всеми версиями» и выберите папку с PDF.'
              : 'Сбросьте поиск, марку или выберите «Все».'
          }
        />
      ) : (
        <div className={styles.scroller}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortHeader label="Проект · следующий шаг" hint="Сортировать по шифру." sortKey="code" view={view} onView={onView} />
                <SortHeader label="Версии" hint="Сортировать по числу версий." sortKey="versions" view={view} onView={onView} />
                {SHOWN_STEPS.map((step) => (
                  <th
                    key={step}
                    scope="col"
                    aria-sort={view.sort.key === step ? (view.sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}
                  >
                    {mayAct && (SELECTABLE_STEPS as readonly ComparisonStepId[]).includes(step) ? (
                      <ColumnSelect
                        step={step}
                        keys={reachable(step)}
                        selected={selected}
                        onSelectColumn={onSelectColumn}
                      />
                    ) : null}
                    <button
                      type="button"
                      className={styles.sortButton}
                      title={STEP_HINTS[step]}
                      onClick={() => onView({ ...view, sort: nextSort(view.sort, step) })}
                    >
                      {`${STEP_NUMBERS[step]} ${STEP_LABELS[step]}`}
                      {view.sort.key === step ? (view.sort.direction === 'asc' ? ' ▲' : ' ▼') : ''}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((set) => (
                <SetRow key={set.document_uid} {...props} set={set} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ul className={styles.legend} aria-label="Обозначения">
        {LEGEND.map((item) => (
          <li key={item.icon}>
            <span aria-hidden="true">{item.icon}</span> {item.text}
          </li>
        ))}
        <li>Щелчок по строке — сравнение листов комплекта.</li>
        {mayAct ? (
          <li>⏸ Пауза — начатое доводится и сохраняется, новое не начинается; ▶ Продолжить — с того же места; Заново — по текущему состоянию комплекта.</li>
        ) : null}
      </ul>
    </div>
  );
}

/** «выбрать все» of a column: ticked when every reachable cell is, mixed when some are, off when none are (`colState`). */
function ColumnSelect({
  step,
  keys,
  selected,
  onSelectColumn,
}: {
  readonly step: ComparisonStepId;
  readonly keys: readonly string[];
  readonly selected: ReadonlySet<string>;
  readonly onSelectColumn: (keys: readonly string[], on: boolean) => void;
}) {
  const state = columnState(keys, selected);
  return (
    <label className={aiStyles.columnSelect} title={COLUMN_SELECT_TITLE(STEP_LABELS[step])}>
      <input
        type="checkbox"
        checked={state === 'all'}
        disabled={state === 'none'}
        data-select-column={step}
        data-column-state={state}
        aria-label={COLUMN_SELECT_TITLE(STEP_LABELS[step])}
        ref={(element) => {
          if (element !== null) element.indeterminate = state === 'some';
        }}
        onChange={(event) => onSelectColumn(keys, event.target.checked)}
      />
    </label>
  );
}

export interface ProjectsAndStagesProps {
  readonly projectUid: ProjectUid;
  /** An expert; the buttons of the steps are drawn for nobody else. */
  readonly mayAct: boolean;
  readonly onOpen: (documentUid: DocumentUid) => void;
}

type OpenDialog =
  | { readonly kind: 'ai'; readonly props: Omit<AiStartDialogProps, 'onDone' | 'onCancel'> }
  | { readonly kind: 'report'; readonly title: string; readonly seriesId: ComparisonSeriesId; readonly confirmLabel: string }
  | { readonly kind: 'selection'; readonly items: readonly (SelectionItem & { readonly label: string })[]; readonly queueNote: string }
  | { readonly kind: 'continue'; readonly title: string; readonly reportId: ComparisonReportId };

const QUEUE_STOPPED_NOTE = 'Очередь запуска сейчас остановлена — выбранное встанет в неё и начнётся после «Продолжить очередь».';
const QUEUE_BUSY_NOTE = 'В очереди запуска уже идут другие шаги — выбранное начнётся после них.';

export function ProjectsAndStages({ projectUid, mayAct, onOpen }: ProjectsAndStagesProps) {
  const overview = useComparisonOverview(projectUid);
  const launch = useLaunchQueue(projectUid);
  const aiQueue = useAiQueue();
  const [view, setView] = useState<OverviewView>(INITIAL_VIEW);
  const [confirming, setConfirming] = useState<ComparisonOverviewSet | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [selectableAi, setSelectableAi] = useState<ReadonlySet<string>>(new Set());
  const [queueOpen, setQueueOpen] = useState(false);
  const [dialog, setDialog] = useState<OpenDialog | null>(null);
  const prepare = usePrepareMatrix();
  const start = useStartSeries();
  const act = useSeriesAct();
  const jobAct = useAiJobAct();
  const reportCommand = useReportCommand();
  const queue = useQueueCommand();
  const download = useDownload();
  const busy = prepare.isPending || start.isPending || act.isPending || jobAct.isPending || reportCommand.isPending;
  const error = prepare.error ?? start.error ?? act.error ?? jobAct.error ?? reportCommand.error ?? download.error ?? null;
  const failure = error === null ? null : comparisonFailure(error);

  if (overview.isPending) return <LoadingState what="сводку по комплектам" />;
  if (overview.isError) {
    return <FailureState error={overview.error} title="Сводка по комплектам не открылась" onRetry={() => void overview.refetch()} />;
  }
  const data = overview.data;

  const run = (set: ComparisonOverviewSet, action: StepActionId, restart: boolean): void => {
    const base = { projectUid, documentUid: set.document_uid };
    prepare.reset();
    start.reset();
    act.reset();
    switch (action) {
      case 'prepare': prepare.mutate(base); break;
      case 'start': start.mutate({ ...base, restart, baseOrderRevisionNo: null }); break;
      case 'restart': start.mutate({ ...base, restart: true, baseOrderRevisionNo: null }, { onSuccess: () => setConfirming(null) }); break;
      case 'pause': act.mutate({ ...base, act: 'pause' }); break;
      case 'resume': act.mutate({ ...base, act: 'resume' }); break;
      case 'finish': act.mutate({ ...base, act: 'finish' }); break;
    }
  };

  const nameOf = (set: ComparisonOverviewSet): string => (codeOf(set) === '' ? 'Комплект без шифра' : codeOf(set));

  const openStep = (set: ComparisonOverviewSet, step: 'ai_pairs' | 'ai_changes' | 'report', seriesId: ComparisonSeriesId | null, restart: boolean): void => {
    const name = nameOf(set);
    if (step === 'ai_pairs') {
      setDialog({
        kind: 'ai',
        props: {
          title: `${AI_METHOD_LABELS.pair_check} · ${name}`,
          scope: { kind: 'pair_check', projectUid, documentUid: set.document_uid },
          consentKind: 'pair_check',
          confirmLabel: CONFIRM_LABELS.pair_check,
          intro: 'ИИ смотрит листы «⁇» с кандидатами и пары, в которых алгоритм не уверен. Пара ставится сама только при уверенном ответе, подтверждённом встречной проверкой; остальное — подсказки. Ручные правки в матрице главнее.',
        },
      });
    } else if (step === 'ai_changes' && seriesId !== null) {
      setDialog({
        kind: 'ai',
        props: {
          title: `${restart ? 'ИИ-описание изменений заново' : AI_METHOD_LABELS.sheet_changes} · ${name}`,
          scope: { kind: 'sheet_changes', seriesId },
          consentKind: 'sheet_changes',
          confirmLabel: restart ? RESTART_CONFIRM_LABELS.sheet_changes : CONFIRM_LABELS.sheet_changes,
          restart,
          intro: restart
            ? 'Новые описания заменят текущие. Листы, которые не менялись, берутся из сохранённых ответов без обращения к ИИ.'
            : 'ИИ опишет изменения на листах и соберёт «Сводку изменений (MD)». Задание встанет в очередь установки.',
        },
      });
    } else if (step === 'report' && seriesId !== null) {
      setDialog({
        kind: 'report',
        title: `${restart ? 'PDF-отчёт заново' : 'PDF-отчёт'} · ${name}`,
        seriesId,
        confirmLabel: restart ? RESTART_CONFIRM_LABELS.report : CONFIRM_LABELS.report,
      });
    }
  };

  const onAiAct = (request: AiActRequest): void => {
    const { set, step, action, cell, seriesId } = request;
    jobAct.reset();
    download.reset();
    const method = step === 'ai_pairs' ? 'pair_check' : 'sheet_changes';
    if (action.id === 'start') return openStep(set, step, seriesId, false);
    if (action.id === 'restart') return openStep(set, step, seriesId, true);
    if (step === 'report') {
      if (cell.reportId === null) return;
      if (action.id === 'cancel') return reportCommand.mutate({ act: 'cancel', reportId: cell.reportId as ComparisonReportId });
      if (action.id === 'continue') {
        if (action.asksConsent) setDialog({ kind: 'continue', title: `Продолжить PDF-отчёт · ${nameOf(set)}`, reportId: cell.reportId as ComparisonReportId });
        else reportCommand.mutate({ act: 'continue', reportId: cell.reportId as ComparisonReportId });
        return;
      }
      if (action.id === 'pdf') download.mutate({ kind: 'report-pdf', reportId: cell.reportId as ComparisonReportId, fileName: 'report.pdf' });
      return;
    }
    if (cell.jobId === null) return;
    const jobId = cell.jobId as ComparisonAiJobId;
    if (action.id === 'resume' && action.asksConsent) {
      const scope: EstimateScope | null =
        step === 'ai_pairs'
          ? { kind: 'pair_check', projectUid, documentUid: set.document_uid }
          : seriesId === null ? null : { kind: 'sheet_changes', seriesId };
      if (scope === null) return;
      setDialog({
        kind: 'ai',
        props: {
          title: `Продолжить · ${AI_METHOD_LABELS[method]} · ${nameOf(set)}`,
          scope,
          consentKind: step === 'ai_pairs' ? 'pair_check' : 'sheet_changes',
          confirmLabel: 'Продолжить',
          resumeJob: { method, jobId },
          intro: cell.pauseReason === null ? '' : AI_PAUSE_ADVICE[cell.pauseReason],
        },
      });
      return;
    }
    const map = { pause: 'pause', resume: 'resume', finish: 'finish', dequeue: 'dequeue' } as const;
    if (action.id === 'pause' || action.id === 'resume' || action.id === 'finish' || action.id === 'dequeue') {
      jobAct.mutate({ method, act: map[action.id], jobId });
    }
  };

  const reachableCheck = (key: string): boolean => selectableAi.has(key);
  const onRunSelected = (): void => {
    const rows = visibleSets(data.sets, view);
    const items: (SelectionItem & { label: string })[] = [];
    for (const set of rows) {
      for (const step of SELECTABLE_STEPS) {
        const key = selectionKey(set.document_uid, step);
        if (!selected.has(key)) continue;
        const reach =
          step === 'series'
            ? canSelect('series', {
                mayAct,
                versions: set.version_count,
                state: set.steps.find((entry) => entry.step === 'series')?.state ?? 'not_applicable',
                queued: queueBadge(launch.data?.entries ?? [], set.document_uid, 'series') !== null,
              })
            : reachableCheck(key);
        if (reach) items.push({ documentUid: set.document_uid, step, label: `${nameOf(set)} · ${STEP_LABELS[step]}` });
      }
    }
    if (items.length === 0) return;
    const q = launch.data;
    const stopped = q !== undefined && (q.state === 'paused' || q.state === 'failed');
    const busyQ = q !== undefined && q.counts.running + q.counts.waiting + q.counts.needs_consent > 0;
    setDialog({ kind: 'selection', items, queueNote: stopped ? QUEUE_STOPPED_NOTE : busyQ ? QUEUE_BUSY_NOTE : '' });
  };

  const close = (): void => setDialog(null);
  const dialogNode: ReactNode =
    dialog === null ? null : dialog.kind === 'ai' ? (
      <AiStartDialog {...dialog.props} onDone={close} onCancel={close} />
    ) : dialog.kind === 'report' ? (
      <ReportDraftDialog title={dialog.title} seriesId={dialog.seriesId} confirmLabel={dialog.confirmLabel} onDone={close} onCancel={close} />
    ) : dialog.kind === 'continue' ? (
      <AiStartDialog
        title={dialog.title}
        scope={{ kind: 'report', reportId: dialog.reportId }}
        consentKind="report"
        confirmLabel="Продолжить"
        continueReportId={dialog.reportId}
        onDone={close}
        onCancel={close}
      />
    ) : (
      <SelectionDialog
        projectUid={projectUid}
        items={dialog.items}
        restart={false}
        queueNote={dialog.queueNote}
        onDone={() => {
          setSelected(new Set());
          setQueueOpen(true);
          close();
        }}
        onCancel={close}
      />
    );

  return (
    <ProjectsAndStagesView
      projectUid={projectUid}
      overview={data}
      view={view}
      onView={setView}
      mayAct={mayAct}
      busy={busy}
      confirming={confirming}
      failure={failure}
      onRefresh={() => void overview.refetch()}
      onOpen={onOpen}
      onAct={(set, action) => (action === 'restart' ? setConfirming(set) : run(set, action, false))}
      onConfirmRestart={() => {
        if (confirming !== null) run(confirming, 'restart', true);
      }}
      onCancelRestart={() => setConfirming(null)}
      selected={selected}
      onSelect={(key, on) =>
        setSelected((held) => {
          const next = new Set(held);
          if (on) next.add(key);
          else next.delete(key);
          return next;
        })
      }
      onSelectColumn={(keys, on) =>
        setSelected((held) => {
          const next = new Set(held);
          for (const key of keys) {
            if (on) next.add(key);
            else next.delete(key);
          }
          return next;
        })
      }
      onClearSelection={() => setSelected(new Set())}
      onRunSelected={onRunSelected}
      selectableAi={selectableAi}
      onSelectable={(key, on) =>
        setSelectableAi((held) => {
          if (held.has(key) === on) return held;
          const next = new Set(held);
          if (on) next.add(key);
          else next.delete(key);
          return next;
        })
      }
      launchQueue={launch.data}
      queueOpen={queueOpen}
      queueBusy={queue.isPending}
      queueFailure={queue.error === null ? null : comparisonFailure(queue.error)}
      onQueueToggle={() => setQueueOpen((open) => !open)}
      onQueueAct={(what) => {
        queue.reset();
        queue.mutate({ act: what, projectUid });
      }}
      onQueueRemove={(entry) => {
        queue.reset();
        queue.mutate({ act: 'remove', entryId: entry.entry_id });
      }}
      onQueueConfirm={(entry) => {
        const set = data.sets.find((item) => item.document_uid === entry.document_uid);
        if (set === undefined) return;
        if (entry.step === 'ai_pairs' || entry.step === 'ai_changes' || entry.step === 'report') {
          openStep(set, entry.step, entry.series_id ?? null, entry.restart);
        }
      }}
      aiQueue={aiQueue.data}
      onAiAct={onAiAct}
      onSummary={(seriesId) =>
        download.mutate({ kind: 'summary-md', seriesId: seriesId as ComparisonSeriesId, fileName: 'svodka-izmeneniy.md' })
      }
      dialog={dialogNode}
    />
  );
}
