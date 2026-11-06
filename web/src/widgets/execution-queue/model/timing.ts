/**
 * The queue row's timing line, as the original's queue prints it (`app.js` 3786-3797): «ЧЧ:ММ → ЧЧ:ММ · длительность»,
 * with the day added when it is not the same day. Presentation only: both instants come from the job
 * (`started_at`, `finished_at`) and the duration is their difference; a job still running is measured to the moment of
 * the last successful read, so the line never claims a time the data does not describe.
 *
 * The clock is UTC like every instant on the screen (`formatInstant`), so a server render and a browser render agree.
 */

import type { ExecutionQueueItem } from '@/shared/api';

export interface QueueTiming {
  /** The start as `ДД.ММ ЧЧ:ММ`, or `null` for a job that never started. */
  readonly start: string | null;
  /** The end as `ЧЧ:ММ` (`ДД.ММ ЧЧ:ММ` on another day), `null` while the job is not finished. */
  readonly end: string | null;
  /** `8 мин 30 с`, `null` when no span is known. */
  readonly duration: string | null;
}

function two(value: number): string {
  return String(value).padStart(2, '0');
}

function dayOf(moment: Date): string {
  return `${two(moment.getUTCDate())}.${two(moment.getUTCMonth() + 1)}`;
}

function clockOf(moment: Date): string {
  return `${two(moment.getUTCHours())}:${two(moment.getUTCMinutes())}`;
}

/** `45 с`, `8 мин 30 с`, `2 ч 5 мин`: the two largest units that are not zero. */
export function durationLabel(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  if (seconds < 60) return `${seconds} с`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return seconds % 60 === 0 ? `${minutes} мин` : `${minutes} мин ${seconds % 60} с`;
  const hours = Math.floor(minutes / 60);
  return minutes % 60 === 0 ? `${hours} ч` : `${hours} ч ${minutes % 60} мин`;
}

/**
 * The parts of the timing line, or `null` for a job that has neither started nor finished (the row then says nothing
 * about time beyond «Принята»). `asOf` is the last successful read; without it a running job has no duration.
 */
export function queueTiming(
  item: Pick<ExecutionQueueItem, 'started_at' | 'finished_at'>,
  asOf: number | null,
): QueueTiming | null {
  const started = item.started_at === undefined ? null : new Date(item.started_at);
  const finished = item.finished_at === undefined ? null : new Date(item.finished_at);
  const startOk = started !== null && !Number.isNaN(started.getTime());
  const finishOk = finished !== null && !Number.isNaN(finished.getTime());
  if (!startOk && !finishOk) return null;
  const start = startOk ? `${dayOf(started)} ${clockOf(started)}` : null;
  let end: string | null = null;
  if (finishOk) {
    end = startOk && dayOf(started) === dayOf(finished) ? clockOf(finished) : `${dayOf(finished)} ${clockOf(finished)}`;
  }
  let duration: string | null = null;
  if (startOk && finishOk) duration = durationLabel(finished.getTime() - started.getTime());
  else if (startOk && asOf !== null) duration = durationLabel(asOf - started.getTime());
  return { start, end, duration };
}
