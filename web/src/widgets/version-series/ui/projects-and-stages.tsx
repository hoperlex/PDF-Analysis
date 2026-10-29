'use client';

/**
 * Tab «Проекты и этапы» (plan §1.1; `frontend/static/js/version-comparison-projects.js`): the counters, the
 * totals, the search, the filters, the sort, «Обновить», the legend, the strip of uploads that are not yet in the
 * list, and the table of document sets with their steps.
 *
 * One row per document set of the chosen project, known by its «шифр» (a designation is metadata, never an
 * identity: the row's identity is the document). The columns are the original's steps 1, 2, 3 and 5; steps 4, 6
 * and 7 are wave C2 and have no column — the screen says so under the table. A row click opens the second tab
 * for that set. The buttons of a step are the commands of `entities/version-series` (`stepActions`) and are
 * offered to an expert only; «Заново» asks first, as the original does.
 *
 * {@link ProjectsAndStagesView} is the whole markup, driven by props, so every state can be rendered by the static
 * harness; {@link ProjectsAndStages} adds the query, the view state and the commands.
 */

import { useState } from 'react';

import type { ComparisonOverview, ComparisonOverviewSet, ComparisonOverviewStep, DocumentUid, ProjectUid } from '@/shared/api';
import { EmptyState, LoadingState } from '@/shared/ui';
import type { ComparisonFailure, OverviewView, SortKey, StepActionId } from '@/entities/version-series';
import {
  INITIAL_VIEW,
  LATER_STEPS_NOTE,
  OVERVIEW_FILTERS,
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

import { CommandRefusal, FailureState } from './module-state';
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
}: {
  readonly set: ComparisonOverviewSet;
  readonly entry: ComparisonOverviewStep | undefined;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly onAct: (set: ComparisonOverviewSet, action: StepActionId) => void;
}) {
  if (entry === undefined) return <span className={styles.muted}>—</span>;
  const shown = stepView(entry.step, entry.state, entry.counts);
  const actions = mayAct ? stepActions(entry.step, entry.state, entry.counts) : [];
  return (
    <div className={styles.step} data-step={entry.step}>
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

export function ProjectsAndStagesView({
  overview,
  view,
  onView,
  mayAct,
  busy,
  confirming,
  failure,
  onRefresh,
  onOpen,
  onAct,
  onConfirmRestart,
  onCancelRestart,
}: ProjectsAndStagesViewProps) {
  const scoped = inScope(overview.sets, view);
  const filtered = view.query.trim() !== '' || view.mark !== '';
  // With no search and no mark the counters are the server's; with either, the sets that pass them are counted here.
  const counts = filtered ? countsOf(scoped) : overview.counters;
  const rows = visibleSets(overview.sets, view);
  const marks = marksOf(overview.sets);
  const preset = parseSort(sortValue(view.sort));
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
                  <SortHeader
                    key={step}
                    label={`${STEP_NUMBERS[step]} ${STEP_LABELS[step]}`}
                    hint={STEP_HINTS[step]}
                    sortKey={step}
                    view={view}
                    onView={onView}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((set) => (
                <tr
                  key={set.document_uid}
                  className={styles.row}
                  data-document-uid={set.document_uid}
                  onClick={() => onOpen(set.document_uid)}
                >
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
                  </th>
                  <td>
                    <span>{set.version_count}</span>
                    {set.updated_at === undefined ? null : <span className={styles.note}>{set.updated_at.slice(0, 10)}</span>}
                  </td>
                  {SHOWN_STEPS.map((step) => (
                    <td key={step}>
                      <StepCell
                        set={set}
                        entry={set.steps.find((entry) => entry.step === step)}
                        mayAct={mayAct}
                        busy={busy}
                        onAct={onAct}
                      />
                    </td>
                  ))}
                </tr>
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
      </ul>
      <p className="am-note" data-later-steps="">
        {LATER_STEPS_NOTE}
      </p>
    </div>
  );
}

export interface ProjectsAndStagesProps {
  readonly projectUid: ProjectUid;
  /** An expert; the buttons of the steps are drawn for nobody else. */
  readonly mayAct: boolean;
  readonly onOpen: (documentUid: DocumentUid) => void;
}

export function ProjectsAndStages({ projectUid, mayAct, onOpen }: ProjectsAndStagesProps) {
  const overview = useComparisonOverview(projectUid);
  const [view, setView] = useState<OverviewView>(INITIAL_VIEW);
  const [confirming, setConfirming] = useState<ComparisonOverviewSet | null>(null);
  const prepare = usePrepareMatrix();
  const start = useStartSeries();
  const act = useSeriesAct();
  const busy = prepare.isPending || start.isPending || act.isPending;
  const error = prepare.error ?? start.error ?? act.error ?? null;
  const failure = error === null ? null : comparisonFailure(error);

  if (overview.isPending) return <LoadingState what="сводку по комплектам" />;
  if (overview.isError) {
    return <FailureState error={overview.error} title="Сводка по комплектам не открылась" onRetry={() => void overview.refetch()} />;
  }

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

  return (
    <ProjectsAndStagesView
      overview={overview.data}
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
    />
  );
}
