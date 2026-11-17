import type { ReactNode } from 'react';

import type { ExecutionJournalEntry, StageId } from '@/shared/api';
import { formatClock, formatInstant, formatInstantUtc, routes } from '@/shared/lib';
import { JobStateBadge, UNKNOWN_STAGE_LABEL, journalPagesText, visibleJournal } from '@/entities/execution';
import type { VisibleJournal } from '@/entities/execution';
import { EmptyState, RunStateBadge, STAGE_LABELS } from '@/shared/ui';

import styles from './execution-journal.module.css';

/**
 * What the journal is a journal of. `all` is the journal of every run (`/logs`): one flat table of events, each with the run it
 * belongs to. `run` is the «Лог» of one run (`UIP-S08-02`): the events in groups by stage, no «Прогон» column, since it would
 * name the same run on every line.
 */
export type ExecutionJournalScope = 'all' | 'run';

export interface ExecutionJournalProps {
  readonly entries: readonly ExecutionJournalEntry[];
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
  /** Default `all`. */
  readonly scope?: ExecutionJournalScope;
}

/** The key of a group of the run's log: a stage of the contract's list, or one of the three groups that are not a stage. */
export type JournalGroupKey = StageId | 'other_stage' | 'misc' | 'execution';

export interface JournalGroup {
  readonly key: JournalGroupKey;
  readonly title: string;
  /** Whether the group starts unfolded. The group of the executor's own events starts folded. */
  readonly open: boolean;
  /** The group's events, in the order they were given. */
  readonly entries: readonly ExecutionJournalEntry[];
}

const OTHER_STAGE_TITLE = UNKNOWN_STAGE_LABEL;
const MISC_TITLE = 'Прочее';
const EXECUTION_TITLE = 'Выполнение';

/** The stages in the order of the pipeline, as `STAGE_LABELS` lists them (a test holds the order). */
const STAGE_ORDER = Object.keys(STAGE_LABELS) as readonly StageId[];

/** The events of a job, of an attempt and of a call to a model: the executor's own record, not the audit's. */
const EXECUTION_EVENT_PREFIXES: readonly string[] = ['job.', 'attempt.', 'provider.'];

function groupKeyOf(entry: ExecutionJournalEntry): JournalGroupKey {
  const stage = visibleJournal(entry).stage;
  if (stage !== undefined) return stage.id ?? 'other_stage';
  return EXECUTION_EVENT_PREFIXES.some((prefix) => entry.event_type.startsWith(prefix)) ? 'execution' : 'misc';
}

/**
 * The events of one run in groups (`UIP-S08-02`): one group per stage the events name, in the order of the pipeline, then
 * «Другой этап» (a stage the contract's list does not hold), then «Прочее» (events that name no stage: the run's own states),
 * then «Выполнение» (the events of the job, the attempt and the calls to a model), which starts folded. A group with no events
 * is not made. Nothing is dropped: every event is in exactly one group, a folded one included.
 */
export function journalGroups(entries: readonly ExecutionJournalEntry[]): readonly JournalGroup[] {
  const byKey = new Map<JournalGroupKey, ExecutionJournalEntry[]>();
  for (const entry of entries) {
    const key = groupKeyOf(entry);
    const group = byKey.get(key);
    if (group === undefined) byKey.set(key, [entry]);
    else group.push(entry);
  }
  const order: readonly JournalGroupKey[] = [...STAGE_ORDER, 'other_stage', 'misc', 'execution'];
  const groups: JournalGroup[] = [];
  for (const key of order) {
    const own = byKey.get(key);
    if (own === undefined) continue;
    const title = key === 'other_stage' ? OTHER_STAGE_TITLE
      : key === 'misc' ? MISC_TITLE
        : key === 'execution' ? EXECUTION_TITLE
          : STAGE_LABELS[key];
    groups.push({ key, title, open: key !== 'execution', entries: own });
  }
  return groups;
}

/** `ДД.ММ.ГГГГ` of the reader's day of an event; `null` for an instant that is not one. */
function dayOf(entry: ExecutionJournalEntry): string | null {
  return Number.isNaN(Date.parse(entry.occurred_at)) ? null : formatInstant(entry.occurred_at).slice(0, 10);
}

/**
 * The day a row opens, when the day is worth saying: a group whose events fall on more than one day says the date before the
 * first event of each day, since a row's own time is only «ЧЧ:ММ:СС». A group of one day says none (the date is in the tooltip).
 */
function dayHeadings(entries: readonly ExecutionJournalEntry[]): ReadonlyMap<string, string> {
  const days = entries.map(dayOf);
  if (new Set(days.filter((day) => day !== null)).size < 2) return new Map();
  const headings = new Map<string, string>();
  entries.forEach((entry, index) => {
    const day = days[index];
    if (day !== null && day !== undefined && (index === 0 || day !== days[index - 1])) headings.set(entry.event_id, day);
  });
  return headings;
}

function TimeCell({ entry }: { readonly entry: ExecutionJournalEntry }) {
  return (
    <time dateTime={entry.occurred_at} title={`${formatInstant(entry.occurred_at)} · ${formatInstantUtc(entry.occurred_at)}`}>
      {formatClock(entry.occurred_at)}
    </time>
  );
}

function StateBadge({ visible }: { readonly visible: VisibleJournal }) {
  if (visible.badge === undefined) return null;
  return visible.badge.kind === 'run' ? <RunStateBadge state={visible.badge.state} /> : <JobStateBadge state={visible.badge.state} />;
}

function GroupTable({ group }: { readonly group: JournalGroup }) {
  const headings = dayHeadings(group.entries);
  return (
    <div className={styles.scroll}>
      <table className={styles.groupTable} data-journal-table="">
        <colgroup>
          <col className={styles.colTime} />
          <col />
          <col className={styles.colPages} />
          <col className={styles.colState} />
        </colgroup>
        <thead className={styles.visuallyHidden}>
          <tr>
            <th scope="col">Время</th>
            <th scope="col">Событие</th>
            <th scope="col">Страницы</th>
            <th scope="col">Состояние</th>
          </tr>
        </thead>
        <tbody>
          {group.entries.map((entry) => {
            const visible = visibleJournal(entry);
            const heading = headings.get(entry.event_id);
            return (
              <RowWithDay key={entry.event_id} heading={heading}>
                <td className={styles.time}><TimeCell entry={entry} /></td>
                <td className={styles.event}>
                  <strong>{visible.event}</strong>
                  {visible.stage === undefined ? null : <> <span className={styles.stage} data-journal-stage={visible.stage.id ?? 'other'}>{visible.stage.label}</span></>}
                </td>
                <td className={styles.pages}>{visible.pages === undefined ? null : <span data-journal-pages="">{journalPagesText(visible.pages)}</span>}</td>
                <td className={styles.state}>
                  <StateBadge visible={visible} />
                  {/* The code of an error is said on the line of the failure and nowhere else. */}
                  {visible.code === null ? null : <> <code>{visible.code}</code></>}
                </td>
              </RowWithDay>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** A row, behind the line that names its day when it opens one. */
function RowWithDay({ heading, children }: { readonly heading: string | undefined; readonly children: ReactNode }) {
  return (
    <>
      {heading === undefined ? null : (
        <tr className={styles.day} data-journal-day={heading}>
          <td colSpan={4}>{heading}</td>
        </tr>
      )}
      <tr>{children}</tr>
    </>
  );
}

function GroupedJournal({ entries }: { readonly entries: readonly ExecutionJournalEntry[] }) {
  return (
    <div className={styles.groups} data-journal-groups="">
      {journalGroups(entries).map((group) => (
        <details key={group.key} className={styles.group} data-journal-group={group.key} {...(group.open ? { open: true } : {})}>
          <summary className={styles.groupHead}>
            <span className={styles.groupTitle}>{group.title}</span>
            <span className={styles.groupCount} aria-label={`строк: ${group.entries.length}`} data-journal-group-count="">{group.entries.length}</span>
          </summary>
          <GroupTable group={group} />
        </details>
      ))}
    </div>
  );
}

function FlatJournal({ entries }: { readonly entries: readonly ExecutionJournalEntry[] }) {
  return (
    <div className={styles.scroll}>
      <table className={styles.table} data-journal-table="">
        <thead>
          <tr>
            <th scope="col">Время</th>
            <th scope="col">Событие</th>
            <th scope="col">Состояние</th>
            <th scope="col">Код</th>
            <th scope="col">Прогон</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const visible = visibleJournal(entry);
            return (
              <tr key={entry.event_id}>
                <td className={styles.time}><TimeCell entry={entry} /></td>
                <td className={styles.event}>
                  <strong>{visible.event}</strong>
                  {/* `UIP-S08-01`: the stage's Russian name (a stage the contract's list does not hold is «Другой этап») and the pages read. */}
                  {visible.stage === undefined ? null : <> · <span data-journal-stage={visible.stage.id ?? 'other'}>{visible.stage.label}</span></>}
                  {visible.pages === undefined ? null : <> · <span data-journal-pages="">{journalPagesText(visible.pages)}</span></>}
                </td>
                <td>{visible.state === null ? null : <strong>{visible.state}</strong>}</td>
                <td>{visible.code === null ? null : <code>{visible.code}</code>}</td>
                <td className={styles.identity}><a href={routes.logs(entry.run_id)}><code>{entry.run_id}</code></a></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ExecutionJournal({ entries, onNext, onPrevious, scope = 'all' }: ExecutionJournalProps) {
  if (entries.length === 0 && onPrevious === null) {
    return <EmptyState title="Записей пока нет" detail="После выполнения прогонов события появятся здесь." />;
  }
  // The log of one run has one page here and nothing to turn: the paging that cannot move is not drawn.
  const paged = scope === 'all' || onPrevious !== null || onNext !== null;
  return (
    <section aria-label="События выполнения" className={styles.list}>
      {entries.length === 0 ? <EmptyState title="На этой странице записей нет" detail="Вернитесь к предыдущей странице." /> : null}
      {/* One line per event, as the original's log: time, what happened, the state and code the closed projection allows; the run's own
          log groups them by stage and says the run once, in its heading, and the journal of every run says it on each line. */}
      {entries.length === 0 ? null : scope === 'run' ? <GroupedJournal entries={entries} /> : <FlatJournal entries={entries} />}
      {paged ? (
        <nav aria-label="Страницы журнала" className={styles.paging}>
          <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
          <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
        </nav>
      ) : null}
    </section>
  );
}
