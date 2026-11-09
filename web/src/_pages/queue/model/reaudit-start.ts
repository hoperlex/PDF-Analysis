/**
 * What the queue shows while a repeated Run is being started (`RUN-START-ONE-01b`, plan v3 §8): one click on
 * «Повторный аудит», and then only what the estimate makes necessary.
 *
 * Pure: the step is a function of what has been read and what has happened. `../ui/queue-page.tsx` holds the
 * sequence (read, agree, send) and `../ui/reaudit-start.tsx` draws each step.
 *
 * - `reading`: the source Run and the estimate are being read. A line and «Отмена»; nothing can be sent yet.
 * - `unreadable`: the reading failed. The failure is said and the person can read again or leave; nothing is sent.
 * - `send`: the estimate charges nothing, so the click already was the agreement. The page sends at once.
 * - `ask`: the estimate can charge, or the server said the last one changed. ONE dialog with the figure and the
 *   ceiling; its «Запустить» is the agreement. After a changed estimate the dialog is shown even when the new
 *   estimate charges nothing, because the person agreed to a figure that is no longer the one the server would run.
 * - `failed`: the send was refused or its outcome is unknown. The refusal is said; nothing is sent again without a press.
 */

import { ApiError } from '@/shared/api';

/** `409 conflict` of a start whose digest is no longer the one the server computes. */
export const ESTIMATE_STALE_REASON = 'run_cost_estimate_stale';
/**
 * The model, rate or revision (or, on the stage layout, the access) the estimate was bound to has changed. The Run path answers
 * `422 analysis_input_invalid` with this `reason`; the stage layout's start answers `409 conflict` with this `conflict_reason`.
 * Both are the same answer for the person: read again (the same pair as `features/start-run`'s `estimateChanged`).
 */
export const BINDING_CHANGED_REASON = 'cost_estimate_binding_changed';

export type ReauditStep = 'reading' | 'unreadable' | 'send' | 'ask' | 'failed';

export interface ReauditStepInput {
  /** The source Run or the estimate is being read. */
  readonly pending: boolean;
  /** The reading failed (`null`/`undefined`: it did not). */
  readonly error: unknown;
  /** A fresh estimate and its ceiling are there. */
  readonly ready: boolean;
  /** The estimate charges nothing. */
  readonly unmetered: boolean;
  /** The server said the estimate changed; the person looks at the new one before anything is sent. */
  readonly lookAgain: boolean;
  /** The last send failed. */
  readonly failed: boolean;
}

export function reauditStep({ pending, error, ready, unmetered, lookAgain, failed }: ReauditStepInput): ReauditStep {
  if (pending) return 'reading';
  if (error !== null && error !== undefined) return 'unreadable';
  if (!ready) return 'reading';
  if (failed) return 'failed';
  return unmetered && !lookAgain ? 'send' : 'ask';
}

/** Whether `error` is the server saying that what the person agreed to is not what it would run. */
export function reauditEstimateChanged(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  return (error.errorCode === 'conflict'
      && (error.details.conflict_reason === ESTIMATE_STALE_REASON || error.details.conflict_reason === BINDING_CHANGED_REASON))
    || (error.errorCode === 'analysis_input_invalid' && error.details.reason === BINDING_CHANGED_REASON);
}
