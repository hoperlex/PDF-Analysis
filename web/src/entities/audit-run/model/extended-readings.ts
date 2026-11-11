/**
 * What the run screen reads from the extended review's saved result (`getExtendedRunReview`, `ExtendedRunReview.result`).
 *
 * The result is an opaque record on the wire; the review widget draws it with its own tolerant readers. This file reads only the
 * two things the rail and the live line need: the **procedures** with their statuses (which phases the run planned and how each
 * stands) and the **live position** inside the current phase (the window or the batch that is running). It reads defensively and
 * invents nothing: a member that is missing, of the wrong type or outside the closed status set is left out, never replaced by a
 * default, so a phase the reading does not describe is not drawn as a phase that is waiting.
 */

type RecordValue = Record<string, unknown>;

const object = (value: unknown): RecordValue | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as RecordValue) : null;
const objects = (value: unknown): RecordValue[] =>
  Array.isArray(value) ? value.flatMap((item) => (object(item) === null ? [] : [object(item) as RecordValue])) : [];
const text = (value: unknown): string => (typeof value === 'string' ? value : '');
const whole = (value: unknown): number | null =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;

/** The statuses a procedure, a window or a batch carries (the review widget's `procedureLabels` and `STATUS`). */
export const PROCEDURE_STATUS_VALUES = [
  'queued',
  'running',
  'repairing',
  'completed',
  'partial',
  'failed',
  'unavailable',
  'skipped',
] as const;

export type ProcedureStatus = (typeof PROCEDURE_STATUS_VALUES)[number];

const isStatus = (value: unknown): value is ProcedureStatus =>
  (PROCEDURE_STATUS_VALUES as readonly unknown[]).includes(value);

export interface ProcedureReading {
  /** The procedure's id: the same word as the stage id of the phase it carries out (`block_analysis`, `finding_merge`, …). */
  readonly id: string;
  /** The title the server gave it. */
  readonly title: string;
  readonly status: ProcedureStatus;
  /** The server's reason code when the procedure did not complete, or `null`. */
  readonly reason: string | null;
  /** The procedure the server names as the one this depended on when it did not run, or `null`. */
  readonly dependency: string | null;
  readonly errorCode: string | null;
  /**
   * The server says this procedure called no model (`model_called: false`): under plan v2 the original's critic and corrector
   * (`V2-ORIGINAL-REVIEW-01`). Absent for every other procedure, so a reading made without it is what it was.
   */
  readonly deterministic?: true;
}

/** The planned procedures of an extended review's result, in the server's order; none for a result that carries none. */
export function procedureReadings(result: unknown): readonly ProcedureReading[] {
  return objects(object(result)?.procedures).flatMap((procedure) => {
    const id = text(procedure.id);
    if (id === '' || !isStatus(procedure.status)) return [];
    return [{
      id,
      title: text(procedure.title),
      status: procedure.status,
      reason: text(procedure.reason) || null,
      dependency: text(procedure.dependency) || null,
      errorCode: text(procedure.error_code) || null,
      ...(procedure.model_called === false ? { deterministic: true as const } : {}),
    }];
  });
}

export interface LiveProgress {
  readonly kind: 'window' | 'batch';
  /** The running one's place, from 1. */
  readonly index: number;
  readonly total: number;
}

const ACTIVE: ReadonlySet<string> = new Set(['running', 'repairing']);

/**
 * The window (or, when the result has none, the batch) that is running now, with how many there are.
 *
 * A window is the unit of a v3 section analysis; the batches of a result without windows are the unit of the older plans. The
 * total of windows is the server's (`window_progress.total`) when it says one, else the number of windows listed. `null` when
 * nothing is running or the result does not expose either.
 */
export function extendedLiveProgress(result: unknown): LiveProgress | null {
  const record = object(result);
  if (record === null) return null;

  const windows = objects(record.windows);
  if (windows.length > 0) {
    const progress = object(record.window_progress);
    const current = text(progress?.current);
    const at = windows.findIndex((window) => ACTIVE.has(text(window.status)) || (current !== '' && text(window.window_id) === current));
    if (at >= 0) {
      const index = whole(windows[at]?.index);
      return { kind: 'window', index: (index ?? at) + 1, total: Math.max(whole(progress?.total) ?? 0, windows.length) };
    }
  }

  const batches = objects(record.batches);
  const running = batches.find((batch) => ACTIVE.has(text(batch.status)));
  if (running !== undefined) {
    const sameProcedure = batches.filter((batch) => text(batch.procedure) === text(running.procedure));
    const index = whole(running.index);
    return { kind: 'batch', index: (index ?? sameProcedure.indexOf(running)) + 1, total: sameProcedure.length };
  }
  return null;
}

/** «окно 2 из 5» / «пакет 3 из 12». */
export function liveProgressText(progress: LiveProgress): string {
  return `${progress.kind === 'window' ? 'окно' : 'пакет'} ${progress.index} из ${progress.total}`;
}
