/**
 * The line above a run's «Лог» (`UIP-S08-03`): what the run is doing now, or how it ended -- said from the journal's own events,
 * through the same closed projection the lines are (`visibleJournal`).
 *
 *   an open run         «Сейчас: Анализ текста · стр. 3 из 10»    the stage at work and, when it reports them, its pages;
 *   a run between stages «Сейчас: прогон выполняется»              the run's own state, when no stage is at work;
 *   an ended run        «Прогон завершён: опубликован»            the state the run's last transition reached.
 *
 * It says nothing of a model or a server, of cost or of a heartbeat: the journal's projection holds none of them, and the line is
 * built from nothing else. A journal with no event of the run's own gives no line at all, rather than a guess.
 *
 * Pure: entries in, a value out. The entries are one page of the run's journal, newest first, as the journal is read; the order
 * is not trusted, and the newest event is the one that counts.
 */

import type { ExecutionJournalEntry, RunState } from '@/shared/api';
import { isTerminalRunState } from '@/shared/api';
import { STATE_LABELS } from '@/shared/ui';

import type { JournalPages, JournalStage } from './presentation';
import { journalPagesText, visibleJournal } from './presentation';

/** The events that carry the run's own state: its creation and each transition. */
const RUN_STATE_EVENTS: ReadonlySet<string> = new Set(['audit_run.created', 'audit_run.transition']);

export type JournalStatus =
  /** The journal has no event. */
  | { readonly kind: 'empty'; readonly text: null }
  /** There are events, but none of the run's own states or stages: nothing the line could say without a guess. */
  | { readonly kind: 'unknown'; readonly text: null }
  | {
    readonly kind: 'running';
    readonly text: string;
    /** The stage at work; `null` between stages. */
    readonly stage: JournalStage | null;
    readonly pages: JournalPages | null;
    /** The run's state as the journal last said it; `null` when the page does not hold one. */
    readonly state: RunState | null;
  }
  | { readonly kind: 'ended'; readonly text: string; readonly state: RunState };

/** The newest first: by time, then by the event's own identity, as the journal orders its page. */
function newestFirst(entries: readonly ExecutionJournalEntry[]): ExecutionJournalEntry[] {
  return [...entries].sort((left, right) => right.occurred_at.localeCompare(left.occurred_at) || right.event_id.localeCompare(left.event_id));
}

/**
 * The pages the stage named by `own[at]` has read: those of its newest progress event, looking back from `at` and no further
 * than the stage's own end (an earlier end is an earlier attempt's, whose pages are not these).
 */
function pagesOf(own: readonly ExecutionJournalEntry[], at: number): JournalPages | null {
  const raw = own[at]?.payload.stage_id;
  for (const entry of own.slice(at)) {
    if (entry.payload.stage_id !== raw) continue;
    if (entry.event_type === 'stage.finished') return null;
    const pages = visibleJournal(entry).pages;
    if (pages !== undefined) return pages;
  }
  return null;
}

/** The line a run's journal says: its stage at work, its state between stages, or how it ended. */
export function journalStatus(entries: readonly ExecutionJournalEntry[]): JournalStatus {
  if (entries.length === 0) return { kind: 'empty', text: null };
  // The run's own events: a job's and an attempt's say how the executor goes, not how the audit does.
  const own = newestFirst(entries.filter((entry) => entry.aggregate_type === 'AuditRun'));

  let state: RunState | null = null;
  for (const entry of own) {
    if (!RUN_STATE_EVENTS.has(entry.event_type)) continue;
    const badge = visibleJournal(entry).badge;
    if (badge?.kind === 'run') {
      state = badge.state;
      break;
    }
  }
  if (state !== null && isTerminalRunState(state)) {
    return { kind: 'ended', text: `Прогон завершён: ${STATE_LABELS[state]}`, state };
  }

  // The newest stage event: a stage is at work unless the newest thing said of it is its end.
  const at = own.findIndex((entry) => visibleJournal(entry).stage !== undefined);
  const latest = own[at];
  const stage = latest === undefined ? undefined : visibleJournal(latest).stage;
  if (latest !== undefined && stage !== undefined && latest.event_type !== 'stage.finished') {
    const pages = pagesOf(own, at);
    return {
      kind: 'running',
      text: `Сейчас: ${stage.label}${pages === null ? '' : ` · ${journalPagesText(pages)}`}`,
      stage,
      pages,
      state,
    };
  }

  // No stage at work. The run's state says what it is doing; a stage that has ended says it is still being executed.
  if (state !== null) return { kind: 'running', text: `Сейчас: прогон ${STATE_LABELS[state]}`, stage: null, pages: null, state };
  if (latest !== undefined) return { kind: 'running', text: `Сейчас: прогон ${STATE_LABELS.running}`, stage: null, pages: null, state: null };
  return { kind: 'unknown', text: null };
}
