/**
 * The words of a run's `interrupted_reason` (`OD-10`), for the reasons a reader can act on.
 *
 * `interrupted_reason` is a free string of the contract (a run left open by a crash is reconciled to `failed` with it); the screens printed
 * it raw. `RUN-RESTART-01` (`R-155c`) adds the silence watchdog: an Attempt with no sign of life for the named time (30 minutes) is ended
 * as `failed` with `attempt_stalled`, and says so in a sentence. A reason that has no words here is still printed as the server wrote it.
 *
 * It sits in `shared/ui` beside `STATE_LABELS` for the reason `stage-label.ts` gives: the run page and the queue row both print it, and
 * a label is presentation, not a domain rule. The stage the silence was on (`terminal_detail.stage_id`) is named by the caller, which
 * has the stage dictionary.
 */

export const INTERRUPTED_REASON_LABELS: Readonly<Record<string, string>> = {
  attempt_stalled: 'Прогон остановлен: нет признаков работы 30 минут',
};

/** The sentence for a reason, without its closing full stop, or `null` for a reason with no words of its own. */
export function interruptedReasonLabel(reason: string): string | null {
  return Object.prototype.hasOwnProperty.call(INTERRUPTED_REASON_LABELS, reason) ? (INTERRUPTED_REASON_LABELS[reason] ?? null) : null;
}
