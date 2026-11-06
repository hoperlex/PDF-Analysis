'use client';

/** @jsxRuntime automatic */

/**
 * The findings of a run, grouped by category.
 *
 * A pure widget: contract models and callbacks in, markup out, per seam §3.4. It holds no
 * query and no mutation, which is what lets it be rendered in a test with no DOM, no
 * `jsdom` and no provider.
 *
 * Every row here is a **published** finding. `P02_SEAMS.md` §5.1 keeps an ungrounded item
 * out of the finding query entirely, and `entities/finding`'s admission gate keeps it out
 * of `groups` on this side too — so this component has no branch for one, and adding a
 * row that bypassed admission would mean writing a new code path rather than relaxing a
 * condition.
 *
 * A row whose finding carries a decided severity (`REVIEW-V2-UI-01`) shows it beside the
 * verdict, from the server's projection and never from the model's proposal. A row without
 * one is the row it always was.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { Finding, FindingCategory, Severity } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import type { FindingGroup } from '@/entities/finding';
import { EXECUTION_STATUS_LABELS, SEVERITY_LABELS, SeverityBadge, countGrouped } from '@/entities/finding';
import { CATEGORY_LABELS, VerdictBadge } from '@/entities/expert-decision';
import { declaredPages } from '@/entities/finding-observation';

import { findingNumbers, pagesLabel, verdictBucket } from '../model/presentation';
import type { VerdictFilter } from '../model/presentation';
import { FindingTable } from './finding-table';
import styles from './finding-list.module.css';

export { pagesLabel, verdictBucket } from '../model/presentation';
export type { VerdictFilter } from '../model/presentation';

/** A finding that was admitted and then found structurally impossible. */
export interface FindingIntegrityFault {
  readonly findingUid: string;
  readonly refusal: string;
}

export interface FindingListProps {
  readonly groups: readonly FindingGroup<Finding>[];
  readonly selectedFindingUid: string | null;
  readonly onSelect: (findingUid: string) => void;
  readonly isLoading?: boolean | undefined;
  /** Already presented as `ErrorState` props by the page, so `retryable` is decided once. */
  readonly error?: ErrorStateProps | null | undefined;
  readonly integrityFaults?: readonly FindingIntegrityFault[] | undefined;
  /** The verdict filter, when the page keeps it (in the address). Absent, the list keeps its own. */
  readonly verdictFilter?: VerdictFilter | undefined;
  readonly onVerdictFilterChange?: ((filter: VerdictFilter) => void) | undefined;
  /**
   * `R-151n`: the quick ✓/✕ of a finding, drawn beside its row and in the table's «Решение» column. The page
   * passes it only to a session that may decide; without it the list draws no action at all.
   */
  readonly renderRowActions?: ((finding: Finding) => ReactNode) | undefined;
  /** `UI-PARITY-P0O`: the drawing sheet of a PDF page, when the version's portal geometry names one. */
  readonly sheetOf?: ((page: number) => number | undefined) | undefined;
  /** `R-151j`: the severity filter, when the page keeps it (in the address). Absent, the list keeps its own. */
  readonly severityFilter?: SeverityFilter | undefined;
  readonly onSeverityFilterChange?: ((filter: SeverityFilter) => void) | undefined;
  /** The way the findings are drawn, when the page keeps it (in the address, `?view=`). Absent, the list keeps its own. */
  readonly view?: FindingView | undefined;
  readonly onViewChange?: ((view: FindingView) => void) | undefined;
  /**
   * What opens under the selected row of the table: the finding itself, as the original opens a strip under its
   * row. In the list the finding is read beside it, so the list ignores this.
   */
  readonly renderExpansion?: ((finding: Finding) => ReactNode) | undefined;
  /**
   * Where the toolbar stands: `inside` (the default) at the head of the list; `outside` when the page draws
   * `FindingToolbar` itself, across the whole width over the list and the open finding.
   */
  readonly toolbar?: 'inside' | 'outside' | undefined;
}

/** The two ways to read the findings: the list beside the open finding, or the full-width table of the original. */
export type FindingView = 'list' | 'table';

/** A view read from the address: an absent or unknown value is the list. */
export function findingViewOf(value: string | null): FindingView {
  return value === 'table' ? 'table' : 'list';
}

/**
 * `R-151j`: the severity strip. The canonical severity is the expert's decision (`decided_severity`); a finding
 * without one is «Не определена». The model's proposal (`observation.proposed_severity`) is counted on its own,
 * labelled row and never filters or decides (AGENTS §4). Counts and filter share one scope: the whole run, which
 * the page loads entirely (`R-150i`).
 */
export type SeverityFilter = 'all' | Severity | 'undetermined';

const SEVERITY_ORDER: readonly Severity[] = ['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'];

export interface SeverityTally {
  readonly decided: Readonly<Record<Severity | 'undetermined', number>>;
  readonly proposed: Readonly<Record<Severity, number>>;
}

export function tallySeverity(groups: readonly FindingGroup<Finding>[]): SeverityTally {
  const decided: Record<Severity | 'undetermined', number> = {
    critical: 0, economic: 0, operational: 0, recommendation: 0, check_adjacent: 0, undetermined: 0,
  };
  const proposed: Record<Severity, number> = { critical: 0, economic: 0, operational: 0, recommendation: 0, check_adjacent: 0 };
  for (const group of groups) {
    for (const finding of group.findings) {
      decided[finding.decided_severity ?? 'undetermined'] += 1;
      const proposal = finding.observation.proposed_severity;
      if (proposal !== undefined) proposed[proposal] += 1;
    }
  }
  return { decided, proposed };
}

/** A severity filter read from the address: an absent or unknown value is «Все». */
export function severityFilterOf(value: string | null): SeverityFilter {
  return value === 'undetermined' || SEVERITY_ORDER.includes(value as Severity) ? (value as SeverityFilter) : 'all';
}

export function filterBySeverity(
  groups: readonly FindingGroup<Finding>[],
  filter: SeverityFilter,
): readonly FindingGroup<Finding>[] {
  if (filter === 'all') return groups;
  return groups
    .map((group) => ({ ...group, findings: group.findings.filter((f) => (f.decided_severity ?? 'undetermined') === filter) }))
    .filter((group) => group.findings.length > 0);
}

/** Whether a run carries any severity at all; a legacy run has none and draws no strip. */
function hasSeverity(tally: SeverityTally): boolean {
  return SEVERITY_ORDER.some((severity) => tally.decided[severity] > 0 || tally.proposed[severity] > 0);
}

/** A verdict filter read from the address: an absent or unknown value is «Все». */
export function verdictFilterOf(value: string | null): VerdictFilter {
  return value === 'waiting' || value === 'accepted' || value === 'rejected' ? value : 'all';
}

export interface VerdictTally {
  readonly waiting: number;
  readonly accepted: number;
  readonly rejected: number;
}

export function tallyVerdicts(groups: readonly FindingGroup<Finding>[]): VerdictTally {
  const tally = { waiting: 0, accepted: 0, rejected: 0 };
  for (const group of groups) for (const finding of group.findings) tally[verdictBucket(finding.current_verdict)] += 1;
  return tally;
}

export function filterGroups(
  groups: readonly FindingGroup<Finding>[],
  filter: VerdictFilter,
): readonly FindingGroup<Finding>[] {
  if (filter === 'all') return groups;
  return groups
    .map((group) => ({ ...group, findings: group.findings.filter((f) => verdictBucket(f.current_verdict) === filter) }))
    .filter((group) => group.findings.length > 0);
}

const FILTERS: readonly { readonly value: VerdictFilter; readonly label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'waiting', label: 'Ожидают решения' },
  { value: 'accepted', label: 'Приняты' },
  { value: 'rejected', label: 'Отклонены' },
];


/** Category labels. The contract value is what the row carries; this is only the heading. */
function categoryHeading(category: FindingCategory): string {
  return CATEGORY_LABELS[category];
}

/** The props of the toolbar over the findings: the whole run's groups and the three choices the address keeps. */
export interface FindingToolbarProps {
  readonly groups: readonly FindingGroup<Finding>[];
  readonly verdictFilter: VerdictFilter;
  readonly onVerdictFilterChange: (filter: VerdictFilter) => void;
  readonly severityFilter: SeverityFilter;
  readonly onSeverityFilterChange: (filter: SeverityFilter) => void;
  readonly view: FindingView;
  readonly onViewChange: (view: FindingView) => void;
  /** What stands at the right end of the first row: the file actions, in the original. */
  readonly actions?: ReactNode | undefined;
}

/** What the model proposed, by severity, naming only the severities it proposed anything for. */
function proposedSummary(tally: SeverityTally): string | null {
  const parts = SEVERITY_ORDER.filter((value) => tally.proposed[value] > 0).map((value) => `${SEVERITY_LABELS[value]} ${tally.proposed[value]}`);
  return parts.length === 0 ? null : parts.join(' · ');
}

/**
 * The strip over the findings, as the original's top row: the run's total and the verdicts' tally, the filter by
 * verdict, the way to read the findings, and the severity chips. The page may stand it across the whole width
 * above the list and the open finding (`toolbar="outside"` on the list); by default it stands inside the list.
 * Counts and filters are over the whole run (`R-150i`), never over what is on screen.
 */
export function FindingToolbar({
  groups,
  verdictFilter: filter,
  onVerdictFilterChange: setFilter,
  severityFilter: severity,
  onSeverityFilterChange: setSeverity,
  view,
  onViewChange: setView,
  actions,
}: FindingToolbarProps) {
  const total = countGrouped(groups);
  if (total === 0) return null;
  const tally = tallyVerdicts(groups);
  const severities = tallySeverity(groups);
  const proposedText = proposedSummary(severities);
  return (
    <div className={styles.toolbar}>
      {/* The original's top row: the total and the severity chips on the left, the file actions on the right. */}
      <div className={styles.top}>
        <strong className={styles.total} data-finding-total={total}>Всего: {total}</strong>
        {hasSeverity(severities) ? (
          <div className={styles.severities} data-severity-strip="">
            <div className={styles.filter} role="group" aria-label="Отбор по важности, решённой экспертом">
              <span className={styles.stripLabel}>Важность (решение эксперта):</span>
              <button
                type="button"
                className="am-button am-button--quiet am-button--small"
                aria-pressed={severity === 'all'}
                data-severity-filter="all"
                onClick={() => setSeverity('all')}
              >
                Все
              </button>
              {[...SEVERITY_ORDER, 'undetermined' as const].map((value) => (
                <button
                  key={value}
                  type="button"
                  className="am-button am-button--quiet am-button--small"
                  aria-pressed={severity === value}
                  data-severity-filter={value}
                  onClick={() => setSeverity(value)}
                >
                  {value === 'undetermined' ? 'Не определена' : SEVERITY_LABELS[value]} {severities.decided[value]}
                </button>
              ))}
            </div>
            {proposedText === null ? null : (
              <p className={styles.proposed} data-proposed-severity="">
                Предложено моделью (не решение эксперта):{' '}
                {proposedText}
              </p>
            )}
          </div>
        ) : null}
        {actions === undefined ? null : <div className={styles.actions}>{actions}</div>}
      </div>
      <div className={styles.verdicts} data-finding-toolbar="">
        <p className={styles.tally} data-verdict-tally={`${tally.waiting}/${tally.accepted}/${tally.rejected}`}>
          Ожидают решения: {tally.waiting} · Приняты: {tally.accepted} · Отклонены: {tally.rejected}
        </p>
        <div className={styles.controls}>
          <div className={styles.filter} role="group" aria-label="Отбор по вердикту">
            {FILTERS.map((option) => (
              <button
                key={option.value}
                type="button"
                className="am-button am-button--quiet am-button--small"
                aria-pressed={filter === option.value}
                data-verdict-filter={option.value}
                onClick={() => setFilter(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className={styles.filter} role="group" aria-label="Вид списка находок">
            {(['list', 'table'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                className="am-button am-button--quiet am-button--small"
                aria-pressed={view === mode}
                data-finding-view={mode}
                onClick={() => setView(mode)}
              >
                {mode === 'list' ? 'Список' : 'Таблица'}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function FindingList({
  groups,
  selectedFindingUid,
  onSelect,
  isLoading,
  error,
  integrityFaults,
  verdictFilter,
  onVerdictFilterChange,
  renderRowActions,
  sheetOf,
  severityFilter,
  onSeverityFilterChange,
  view: viewFromPage,
  onViewChange,
  renderExpansion,
  toolbar,
}: FindingListProps) {
  const [ownFilter, setOwnFilter] = useState<VerdictFilter>('all');
  const [ownSeverity, setOwnSeverity] = useState<SeverityFilter>('all');
  const severity = severityFilter ?? ownSeverity;
  const setSeverity = (next: SeverityFilter) => {
    if (onSeverityFilterChange !== undefined) onSeverityFilterChange(next);
    else setOwnSeverity(next);
  };
  const [ownView, setOwnView] = useState<FindingView>('list');
  const view = viewFromPage ?? ownView;
  const setView = (next: FindingView) => {
    if (onViewChange !== undefined) onViewChange(next);
    else setOwnView(next);
  };
  const filter = verdictFilter ?? ownFilter;
  const setFilter = (next: VerdictFilter) => {
    if (onVerdictFilterChange !== undefined) onVerdictFilterChange(next);
    else setOwnFilter(next);
  };
  if (isLoading === true) return <LoadingState what="находки" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  const total = countGrouped(groups);
  const faults = integrityFaults ?? [];

  if (total === 0 && faults.length === 0) {
    return (
      <EmptyState
        title="Находок нет"
        detail={
          <p>
            Прогон не опубликовал ни одной находки. Элементы модели, чьи цитаты не
            разрешились по заявленным якорям, находками не являются и сохраняются только
            как диагностика прогона.
          </p>
        }
      />
    );
  }

  const shown = filterBySeverity(filterGroups(groups, filter), severity);

  return (
    <div className={`am-finding-list ${styles.root}`} data-finding-count={total}>
      {toolbar === 'outside' ? null : (
        <FindingToolbar
          groups={groups}
          verdictFilter={filter}
          onVerdictFilterChange={setFilter}
          severityFilter={severity}
          onSeverityFilterChange={setSeverity}
          view={view}
          onViewChange={setView}
        />
      )}
      {faults.length > 0 ? (
        <ErrorState
          title="Нарушение целостности данных"
          detail={
            <p>
              Находок без свидетельств: {faults.length}. Шлюз свидетельств P02 делает такое
              невозможным, поэтому это сообщаемая неисправность, а не пустая панель:{' '}
              {faults.map((fault) => fault.findingUid).join(', ')}
            </p>
          }
        />
      ) : null}

      {shown.length === 0 ? (
        <p className="am-note" data-verdict-filter-empty={filter}>
          {severity === 'all' ? 'Находок с таким вердиктом нет.' : 'Находок с таким отбором нет.'}
        </p>
      ) : null}

      {view === 'table' && shown.length > 0 ? (
        <FindingTable
          findings={shown.flatMap((group) => group.findings)}
          numberOf={findingNumbers(groups)}
          selectedFindingUid={selectedFindingUid}
          onSelect={onSelect}
          renderRowActions={renderRowActions}
          renderExpansion={renderExpansion}
          sheetOf={sheetOf}
        />
      ) : null}

      {view === 'table' ? null : shown.map((group) => (
        <section
          key={group.category}
          className="am-finding-group"
          data-category={group.category}
        >
          <h3 className="am-finding-group__heading">
            {categoryHeading(group.category)}{' '}
            <span className="am-finding-group__count">{group.findings.length}</span>
          </h3>
          <ul className="am-finding-group__items">
            {group.findings.map((finding) => {
              const pages = declaredPages(finding.observation);
              const selected = finding.finding_uid === selectedFindingUid;
              return (
                <li
                  key={finding.finding_uid}
                  className={renderRowActions === undefined ? styles.item : `${styles.item} ${styles.withActions}`}
                  data-verdict-bucket={verdictBucket(finding.current_verdict)}
                >
                  <button
                    type="button"
                    className="am-finding-row am-button"
                    data-finding-uid={finding.finding_uid}
                    data-selected={selected ? 'true' : 'false'}
                    aria-current={selected ? 'true' : undefined}
                    onClick={() => {
                      onSelect(finding.finding_uid);
                    }}
                  >
                    <span className="am-finding-row__text">
                      {finding.observation.finding_text}
                    </span>
                    {finding.decided_severity === undefined ? (
                      <VerdictBadge verdict={finding.current_verdict} />
                    ) : (
                      <span className={styles.badges} data-decided-severity={finding.decided_severity}>
                        <VerdictBadge verdict={finding.current_verdict} />
                        <SeverityBadge
                          severity={finding.decided_severity}
                          title="Важность, решённая экспертом"
                        />
                      </span>
                    )}
                    {finding.execution_status === undefined ? null : (
                      // `R-151g`: the original's «Принято · Учтено» -- the designer's execution of an accepted finding.
                      <span className={styles.execution} data-execution-status={finding.execution_status}>
                        {EXECUTION_STATUS_LABELS[finding.execution_status]}
                      </span>
                    )}
                    <span className="am-finding-row__pages" data-pages={pages.join(',')}>
                      {pagesLabel(pages, sheetOf)}
                      {(finding.merged_observations?.length ?? 0) > 1 ? (
                        // The original's «×N» on a finding that stands for several observations.
                        <span
                          className={styles.mergedMark}
                          title={`Объединённых наблюдений: ${finding.merged_observations?.length ?? 0}`}
                          data-merged-observations={finding.merged_observations?.length ?? 0}
                        >
                          {' '}×{finding.merged_observations?.length ?? 0}
                        </span>
                      ) : null}
                    </span>
                  </button>
                  {renderRowActions === undefined ? null : renderRowActions(finding)}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
