/**
 * `RUN-STAGE-PROGRESS-01`: the code stages the execution journal says are under way, and the pages they have read.
 *
 * A stage's result reaches the run reading only when the stage ends, so a stage at work had no status and its row read
 * «не начинался» -- on a large drawing set for a quarter of an hour. The journal says more: `stage.started` when a stage
 * begins, `stage.finished` when it ends, and page progress while it reads the document (`stage.pdf_precheck` of the
 * preparation, `stage.progress` of the geometry). The journal is read newest first, one page of it, so a stage's start may
 * already be off that page while its progress is on it: a stage is under way when its newest event on the page is not
 * `stage.finished`, and its start is named only when the page still holds it.
 *
 * Pure: entries in, a map out. A count that is not a whole number from 0 to the total is not shown.
 */

import type { ExecutionJournalEntry } from '@/shared/api';

export interface StageActivity {
  /** `stage.started`'s instant, when the read page of the journal still holds it. */
  readonly startedAt: string | null;
  /** Pages read and pages in all, from the newest progress event; `null` when the stage reports none. */
  readonly completed: number | null;
  readonly total: number | null;
}

const STAGE_EVENTS: ReadonlySet<string> = new Set(['stage.started', 'stage.finished', 'stage.progress', 'stage.pdf_precheck']);
const PROGRESS_EVENTS: ReadonlySet<string> = new Set(['stage.progress', 'stage.pdf_precheck']);

function pages(entry: ExecutionJournalEntry): { completed: number; total: number } | null {
  const completed = entry.payload['completed_pages'];
  const total = entry.payload['total_pages'];
  if (typeof completed !== 'number' || typeof total !== 'number') return null;
  if (!Number.isSafeInteger(completed) || !Number.isSafeInteger(total)) return null;
  if (completed < 0 || total <= 0 || completed > total) return null;
  return { completed, total };
}

/** The stages under way, by stage id. */
export function stageActivity(entries: readonly ExecutionJournalEntry[], runId: string): ReadonlyMap<string, StageActivity> {
  const own = entries
    .filter((entry) => entry.run_id === runId && entry.aggregate_type === 'AuditRun' && entry.aggregate_id === runId
      && STAGE_EVENTS.has(entry.event_type))
    .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at) || right.event_id.localeCompare(left.event_id));
  const active = new Map<string, { startedAt: string | null; completed: number | null; total: number | null; done: boolean }>();
  const ended = new Set<string>();
  for (const entry of own) {
    const stage = entry.payload['stage_id'];
    if (typeof stage !== 'string' || ended.has(stage)) continue;
    const seen = active.get(stage);
    if (seen === undefined) {
      if (entry.event_type === 'stage.finished') {
        ended.add(stage);
        continue;
      }
      const counted = PROGRESS_EVENTS.has(entry.event_type) ? pages(entry) : null;
      active.set(stage, {
        startedAt: entry.event_type === 'stage.started' ? entry.occurred_at : null,
        completed: counted?.completed ?? null,
        total: counted?.total ?? null,
        done: entry.event_type === 'stage.started',
      });
      continue;
    }
    if (seen.done) continue;
    if (entry.event_type === 'stage.finished') {
      // An earlier Attempt's end: this one's start is not on the page.
      seen.done = true;
    } else if (entry.event_type === 'stage.started') {
      seen.startedAt = entry.occurred_at;
      seen.done = true;
    } else if (seen.total === null) {
      const counted = pages(entry);
      if (counted !== null) {
        seen.completed = counted.completed;
        seen.total = counted.total;
      }
    }
  }
  return new Map([...active].map(([stage, { startedAt, completed, total }]) => [stage, { startedAt, completed, total }]));
}

/** «идёт», or «идёт · 120 из 500 стр.» when the stage reports its pages. */
export function stageActivityText(activity: StageActivity): string {
  return activity.total === null || activity.completed === null
    ? 'идёт'
    : `идёт · ${activity.completed} из ${activity.total} стр.`;
}

/** The pages of the first stage under way among `stageIds`, as the rail's short «120/500 стр.»; `null` when none reports. */
export function chipPagesText(activity: ReadonlyMap<string, StageActivity>, stageIds: readonly string[]): string | null {
  for (const stageId of stageIds) {
    const found = activity.get(stageId);
    if (found !== undefined && found.total !== null && found.completed !== null) return `${found.completed}/${found.total} стр.`;
  }
  return null;
}
