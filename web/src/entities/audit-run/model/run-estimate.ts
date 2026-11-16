/**
 * `UI-B-45` / `UI-A-65` (contract 1.40.0): the run's estimated finish, as the run page words it.
 *
 * The estimate is the server's (`RunStatus.estimated_finish_at`, the same value the execution queue shows for the run's
 * job: the median duration of similar recent runs added to the job's first attempt). This file only presents it; it
 * computes no duration and invents none -- a run without the field has no estimate, and says so by showing nothing.
 *
 * The clock time is the reader's own (the original's «≈ до ЧЧ:ММ»), so it is formatted after mount, from the same
 * browser reading that stamps «идёт …»: a server render and the first client render both show no estimate, and the
 * text appears with the clock (`RunLiveLine`). The instant itself stays on the `<time>` element, and the exact UTC stamp
 * (`formatInstantUtc`, the stamp a log carries) is its title.
 */

import type { RunStatus } from '@/shared/api';
import { formatTime } from '@/shared/lib';

export interface RunFinishEstimate {
  /** The server's instant, as sent. */
  readonly iso: string;
  /** «ЧЧ:ММ» on a 24-hour clock in the reader's time zone. */
  readonly clock: string;
  /** The instant is already behind the clock reading: the run is taking longer than the usual one. */
  readonly late: boolean;
}

/** «ЧЧ:ММ» of an instant on a 24-hour clock (`formatTime`); the zone is the reader's unless one is named. `null` for an unreadable instant. */
export function formatClockTime(iso: string, timeZone?: string): string | null {
  if (Number.isNaN(new Date(iso).getTime())) return null;
  return formatTime(iso, timeZone);
}

/**
 * The estimate to show, or `null`: the reading carries none, the clock has not been read yet (`nowMs` is `null`), or the
 * instant cannot be read. Nothing is shown in place of a missing estimate.
 */
export function runFinishEstimate(
  status: Pick<RunStatus, 'estimated_finish_at'>,
  nowMs: number | null,
  timeZone?: string,
): RunFinishEstimate | null {
  const iso = status.estimated_finish_at;
  if (iso === undefined || nowMs === null) return null;
  const clock = formatClockTime(iso, timeZone);
  if (clock === null) return null;
  return { iso, clock, late: Date.parse(iso) < nowMs };
}
