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

import type { Finding, FindingCategory, PrecedentFindingLabel, Severity } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import type { FindingGroup } from '@/entities/finding';
import { EXECUTION_STATUS_LABELS, EvidenceLimitation, OriginChip, SEVERITY_LABELS, SeverityBadge, countGrouped, findingOriginOf, severityTone } from '@/entities/finding';
import { CATEGORY_LABELS, CarriedMark, VerdictBadge } from '@/entities/expert-decision';
import { findingPages } from '@/entities/finding-observation';
import { PrecedentMark, isCancelSuggested } from '@/entities/decision-memory';

import { SEVERITY_ORDER, findingNumbers, findingsAsShown, groupsInVerdictOrder, pagesLabel, plateOf, plateTotal, severityPlates, verdictBucket } from '../model/presentation';
import type { PlateSeverity, VerdictFilter } from '../model/presentation';
import { CancelQueue, cancelQueueOf } from './cancel-queue';
import { FindingTable } from './finding-table';
import styles from './finding-list.module.css';

export { findingsAsShown, groupsInVerdictOrder, inVerdictOrder, pagesLabel, verdictBucket } from '../model/presentation';
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
  /** Coverage-aware wording supplied by the page for an empty partial result. */
  readonly emptyDetail?: ReactNode | undefined;
  /** The verdict filter, when the page keeps it (in the address). Absent, the list keeps its own («Все»). */
  readonly verdictFilter?: VerdictFilter | undefined;
  readonly onVerdictFilterChange?: ((filter: VerdictFilter) => void) | undefined;
  /**
   * `R-151n`: the quick ✓/✕ of a finding, drawn beside its row and in the table's «Решение» column. The page
   * passes it only to a session that may decide; without it the list draws no action at all.
   */
  readonly renderRowActions?: ((finding: Finding) => ReactNode) | undefined;
  /** `UI-PARITY-P0O`: the drawing sheet of a PDF page, when the version's portal geometry names one. */
  readonly sheetOf?: ((page: number) => number | undefined) | undefined;
  /** `UI-A-74`: the table's count of the portal blocks that hold a finding's evidence; the page reads it from the run's block links. */
  readonly blockCountOf?: ((findingUid: string) => number | undefined) | undefined;
  /** The run's `unlinked_pages`: a finding that cites one has a block count that is partial, and the table says so. */
  readonly unlinkedPages?: ReadonlySet<number> | undefined;
  /** `R-151j`: the severity filter, when the page keeps it (in the address). Absent, the list keeps its own («Все»). */
  readonly severityFilter?: SeverityFilter | undefined;
  readonly onSeverityFilterChange?: ((filter: SeverityFilter) => void) | undefined;
  /** The way the findings are drawn, when the page keeps it (in the address, `?view=`). Absent, the list keeps its own (the table). */
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
  /**
   * `PREC-WEB`: what the «Прецеденты» say of a finding: its label, or nothing. The row and the table's cell draw the neutral mark from it, and the
   * queue «Рекомендовано снять» is made of the shown, still undecided findings whose label is `cancel_suggested`. Absent (a viewer, or no read yet),
   * the list draws no mark and no queue.
   */
  readonly precedentOf?: ((findingUid: string) => PrecedentFindingLabel | undefined) | undefined;
  /** Where a press on an item of the queue goes; absent, `onSelect`. The table's `onSelect` closes an open row, which a link must not do. */
  readonly onOpenQueued?: ((findingUid: string) => void) | undefined;
}

/** The two ways to read the findings: the full-width table of the original (the default), or the list beside the open finding. */
export type FindingView = 'list' | 'table';

/** A view read from the address (`UIP-S06-06`): the table opens in every run; only `list` opens the list. */
export function findingViewOf(value: string | null): FindingView {
  return value === 'list' ? 'list' : 'table';
}

/**
 * `R-151j`, `UIP-S06-06`: the severity plates. A plate counts and selects a finding by its decided severity and, for a finding
 * nobody has decided, by the model's proposal (`plateOf`); a finding with neither is «Не определена», and its plate is drawn only
 * while there is one. The plate's tooltip splits its number into «решено экспертом» and «предложено моделью», and the two stay
 * apart in the data (`decided_severity`, `observation.proposed_severity`): neither becomes the other (AGENTS §4). Counts and
 * filter share one scope: the whole run, which the page loads entirely (`R-150i`). A press on the pressed plate lifts the filter.
 */
export type SeverityFilter = 'all' | PlateSeverity;

/**
 * The two counts kept apart, decided and proposed, as the run page's tile «Замечания» reads them (it shows only what the expert
 * decided). The plates of «Разбор» count both together and say the split in a tooltip: `severityPlates`.
 */
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

/**
 * A severity filter read from the address: an absent or unknown value is «Все». An address written before the proposals had
 * their own plates (`?severity=proposed:critical`) opens as the plate it names (`?severity=critical`): the plate counts both.
 */
export function severityFilterOf(value: string | null): SeverityFilter {
  if (value?.startsWith('proposed:') === true) {
    const named = value.slice('proposed:'.length) as Severity;
    return SEVERITY_ORDER.includes(named) ? named : 'all';
  }
  return value === 'undetermined' || SEVERITY_ORDER.includes(value as Severity) ? (value as SeverityFilter) : 'all';
}

export function filterBySeverity(
  groups: readonly FindingGroup<Finding>[],
  filter: SeverityFilter,
): readonly FindingGroup<Finding>[] {
  if (filter === 'all') return groups;
  return groups
    .map((group) => ({ ...group, findings: group.findings.filter((f) => plateOf(f) === filter) }))
    .filter((group) => group.findings.length > 0);
}

/** A missing or unknown filter is «Все»; the address of the earlier default, `?verdict=active`, opens as «Все» too. */
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

/** `UIP-S06-06`: the one choice «Показывать», in the order the table stands: waiting, accepted, rejected. */
const FILTERS: readonly { readonly value: VerdictFilter; readonly label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'waiting', label: 'Ждут' },
  { value: 'accepted', label: 'Приняты' },
  { value: 'rejected', label: 'Отклонены' },
];

/** The tooltip of a plate: how many of its findings the expert decided and how many only the model proposed. */
function plateTitle(severity: PlateSeverity, plates: ReturnType<typeof severityPlates>): string {
  if (severity === 'undetermined') return 'Критичность не решена экспертом и не предложена моделью';
  const count = plates.bySeverity[severity];
  return `решено экспертом: ${count.decided} · предложено моделью: ${count.proposed}`;
}


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

/**
 * The strip over the findings, as the original's top row (`UIP-S06-06`). Its first row: at the left the five severity plates
 * with their numbers (a press selects the severity, a second press lifts it; «Не определена» only while a finding has none) and
 * the run's totals «Всего: N · Принято: n · Отклонено: m»; at the right the file actions. Under it one row: the choice
 * «Показывать: Все / Ждут / Приняты / Отклонены» and the link to the other way of reading the findings. The page may stand it
 * across the whole width above the list and the open finding (`toolbar="outside"` on the list); by default it stands inside the
 * list. Counts and filters are over the whole run (`R-150i`), never over what is on screen.
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
  const plates = severityPlates(groups);
  const drawn: readonly PlateSeverity[] = [...SEVERITY_ORDER, ...(plates.undetermined > 0 ? ['undetermined' as const] : [])];
  const hasSeverity = SEVERITY_ORDER.some((value) => plateTotal(plates.bySeverity[value]) > 0);
  const otherView: FindingView = view === 'table' ? 'list' : 'table';
  return (
    <div className={styles.toolbar} data-finding-toolbar="">
      {/* The original's top row: the plates and the totals at the left, the file actions at the right. */}
      <div className={styles.top}>
        <div className={styles.lead}>
          {hasSeverity ? (
            <div className={styles.plates} role="group" aria-label="Отбор по критичности" data-severity-strip="">
              {drawn.map((value) => {
                const count = value === 'undetermined' ? plates.undetermined : plateTotal(plates.bySeverity[value]);
                return (
                  <button
                    key={value}
                    type="button"
                    className={`am-badge am-badge--${value === 'undetermined' ? 'inert' : severityTone(value)} ${styles.plate}`}
                    aria-pressed={severity === value}
                    title={plateTitle(value, plates)}
                    data-severity-filter={value}
                    data-plate-count={count}
                    onClick={() => setSeverity(severity === value ? 'all' : value)}
                  >
                    <span className="am-badge__label">{value === 'undetermined' ? 'Не определена' : SEVERITY_LABELS[value]}</span>
                    {' '}
                    <span className={styles.count}>{count}</span>
                  </button>
                );
              })}
            </div>
          ) : null}
          <p className={styles.totals} data-verdict-tally={`${tally.waiting}/${tally.accepted}/${tally.rejected}`}>
            <strong className={styles.total} data-finding-total={total}>Всего: {total}</strong>
            {' · '}Принято: {tally.accepted}{' · '}Отклонено: {tally.rejected}
          </p>
        </div>
        {actions === undefined ? null : <div className={styles.actions}>{actions}</div>}
      </div>
      <div className={styles.show}>
        <div className={styles.filter} role="group" aria-label="Показывать">
          <span className={styles.showLabel} aria-hidden="true">Показывать:</span>
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
        <button
          type="button"
          className={styles.viewLink}
          data-finding-view-link={otherView}
          onClick={() => setView(otherView)}
        >
          {otherView === 'list' ? 'Показать списком' : 'Показать таблицей'}
        </button>
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
  emptyDetail,
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
  blockCountOf,
  unlinkedPages,
  precedentOf,
  onOpenQueued,
}: FindingListProps) {
  const [ownFilter, setOwnFilter] = useState<VerdictFilter>('all');
  const [ownSeverity, setOwnSeverity] = useState<SeverityFilter>('all');
  const severity = severityFilter ?? ownSeverity;
  const setSeverity = (next: SeverityFilter) => {
    if (onSeverityFilterChange !== undefined) onSeverityFilterChange(next);
    else setOwnSeverity(next);
  };
  const [ownView, setOwnView] = useState<FindingView>('table');
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
  if (isLoading === true) return <LoadingState what="замечания" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  const total = countGrouped(groups);
  const faults = integrityFaults ?? [];

  if (total === 0 && faults.length === 0) {
    return (
      <EmptyState
        title="Замечаний нет"
        detail={emptyDetail ?? (
          <p>
            Прогон не опубликовал ни одного замечания. Элементы модели, чьи цитаты не
            разрешились по заявленным якорям, замечаниями не являются и сохраняются только
            как диагностика прогона.
          </p>
        )}
      />
    );
  }

  const shown = filterBySeverity(filterGroups(groups, filter), severity);
  // `UI-A-71`: the original's order, pending → accepted → rejected. The numbers stay the run's (`findingNumbers`).
  const shownByVerdict = groupsInVerdictOrder(shown);

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
              Замечаний без свидетельств: {faults.length}. Шлюз свидетельств P02 делает такое
              невозможным, поэтому это сообщаемая неисправность, а не пустая панель:{' '}
              {faults.map((fault) => fault.findingUid).join(', ')}
            </p>
          }
        />
      ) : null}

      <CancelQueue
        items={cancelQueueOf(
          shown.flatMap((group) => group.findings),
          precedentOf,
          (finding) => verdictBucket(finding.current_verdict) === 'waiting',
          isCancelSuggested,
        )}
        onOpen={onOpenQueued ?? onSelect}
      />

      {shown.length === 0 ? (
        <p className="am-note" data-verdict-filter-empty={filter}>
          {severity === 'all' ? 'Замечаний с таким вердиктом нет.' : 'Замечаний с таким отбором нет.'}
        </p>
      ) : null}

      {view === 'table' && shown.length > 0 ? (
        <FindingTable
          findings={findingsAsShown(shown, 'table')}
          numberOf={findingNumbers(groups)}
          selectedFindingUid={selectedFindingUid}
          onSelect={onSelect}
          renderRowActions={renderRowActions}
          renderExpansion={renderExpansion}
          sheetOf={sheetOf}
          blockCountOf={blockCountOf}
          unlinkedPages={unlinkedPages}
          precedentOf={precedentOf}
        />
      ) : null}

      {view === 'table' ? null : shownByVerdict.map((group) => (
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
              const pages = findingPages(finding);
              const origin = findingOriginOf(finding);
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
                    <EvidenceLimitation finding={finding} />
                    {finding.decided_severity === undefined && finding.current_verdict_carried_from === undefined ? (
                      <VerdictBadge verdict={finding.current_verdict} />
                    ) : (
                      <span className={styles.badges} data-decided-severity={finding.decided_severity}>
                        <VerdictBadge verdict={finding.current_verdict} />
                        {finding.decided_severity === undefined ? null : (
                          <SeverityBadge
                            severity={finding.decided_severity}
                            title="Критичность, решённая экспертом"
                          />
                        )}
                        {/* `UI-A-73`: the verdict was carried over from an earlier version. */}
                        <CarriedMark carriedFrom={finding.current_verdict_carried_from} />
                      </span>
                    )}
                    {finding.execution_status === undefined ? null : (
                      // `R-151g`: the original's «Принято · Учтено» -- the designer's execution of an accepted finding.
                      <span className={styles.execution} data-execution-status={finding.execution_status}>
                        {EXECUTION_STATUS_LABELS[finding.execution_status]}
                      </span>
                    )}
                    <span className="am-finding-row__pages" data-pages={pages.join(',')}>
                      {/* `F8-WEB`: the «Источник» of a finding that is not text; a text finding says nothing more than it did. */}
                      {origin === 'text' ? null : (
                        <>
                          <OriginChip origin={origin} />{' '}
                        </>
                      )}
                      {pagesLabel(pages, sheetOf)}
                      {/* `PREC-WEB`: the neutral label of the precedents; nothing for a finding with none, and never a «Недоступно». */}
                      <PrecedentMark label={precedentOf?.(finding.finding_uid)} />
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
