/**
 * Why a queued Run is not running, in words (`EXEC2-WEB-CAP-01`, over `RunStatus.queue_reason`).
 *
 * The server derives the reason at read time and says it only for a `queued` Run that is waiting
 * for its executor connection (ADR-0026 decisions 1 and 5): `executor_at_capacity` when every unit
 * of the connection is in use, `runner_offline` when it is a `pull` connection and no runner of it
 * is online, `needs_reconsent` (`EXEC2-SEAL-2`) when a Run routed to an executor group needs a
 * fresh cost consent before it may be dispatched. For any other Run the member is `null` or absent.
 *
 * A reason is drawn only beside the state it explains. A Run that is not `queued` carries no
 * waiting label even if a stale reading still holds a reason, and a reason this table does not know
 * (a value the contract gains later) draws nothing, so the screen keeps the label it already has
 * rather than guess one.
 */

import type { RunQueueReason, RunStatus } from '@/shared/api';
import { RUN_QUEUE_REASON_VALUES } from '@/shared/api';

/** The words of each reason; a `Record` over the contract's own set, so a new value is a type error here. */
export const QUEUE_REASON_LABELS: Readonly<Record<RunQueueReason, string>> = {
  executor_at_capacity: 'В очереди: исполнитель занят',
  runner_offline: 'В очереди: раннер не в сети',
  needs_reconsent: 'В очереди: нужно новое согласие на стоимость',
  model_unavailable: 'В очереди: нужной модели сейчас нет на серверах',
};

/**
 * The reason a queued Run waits, or `null` when it is not queued or carries none this screen knows.
 *
 * `EXEC2-WEB-GROUPS-01`: a Run admitted by a rule or a group (`binding_state` `pending`) carries its
 * stored `wait_reason` and no `queue_reason`; the words are the same. `queue_reason` is read first,
 * so a Run that carries both keeps the reason the server derived at read time.
 */
export function runQueueReason(
  run: Pick<RunStatus, 'state' | 'queue_reason' | 'wait_reason'>,
): RunQueueReason | null {
  if (run.state !== 'queued') return null;
  return knownQueueReason(run.queue_reason) ?? knownQueueReason(run.wait_reason);
}

/** A reason this screen knows the word for, or `null` for an absent one and for a value it does not know. */
export function knownQueueReason(reason: string | null | undefined): RunQueueReason | null {
  if (reason === undefined || reason === null) return null;
  return (RUN_QUEUE_REASON_VALUES as readonly string[]).includes(reason) ? (reason as RunQueueReason) : null;
}

/** «В очереди: исполнитель занят» — or `null` when there is nothing more specific than the state's own label. */
export function runQueueReasonLabel(
  run: Pick<RunStatus, 'state' | 'queue_reason' | 'wait_reason'>,
): string | null {
  const reason = runQueueReason(run);
  return reason === null ? null : QUEUE_REASON_LABELS[reason];
}
