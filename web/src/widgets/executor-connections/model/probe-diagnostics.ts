/**
 * The text «Скопировать диагностику» puts on the clipboard for a connection (`UI-B-68`): the last
 * probe's outcome, in the words the card already prints.
 *
 * **Only what the card shows, and nothing the card hides.** The lines are the connection's name and
 * identity, its kind, the number of the current settings, and the probe: its state or outcome in
 * Russian, when, the model the answer named, how long it took, the cost check, the hint and the
 * scrubbed detail the contract guarantees is never a response body. Nothing that is a key or leads
 * to one is here: not the last characters of a secret, not a public key, not the host key a probe
 * observed, not a secret's or a probe's identifier, not who set anything. It is a pure function of
 * the models the card already holds, so nothing is requested and no second reading of the
 * connection can disagree with the screen.
 */

import type { ExecutorConnection, ExecutorRevision } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  IDENTITY_BASIS_LABELS,
  KIND_LABELS,
  PROBE_OUTCOME_HINTS,
  PROBE_STATE_LABELS,
  RATE_CHECK_LABELS,
  probeIsOnCurrentSecret,
  probeOutcomeSentence,
} from '@/entities/executor-connection';

export function probeDiagnosticText(connection: ExecutorConnection, revision: ExecutorRevision): string {
  const probe = revision.latest_probe;
  const lines = [
    'Диагностика подключения',
    `Подключение: ${connection.display_name} (${connection.connection_id})`,
    `Вид: ${KIND_LABELS[connection.kind]}`,
    `Настройки: версия ${revision.revision_no}`,
  ];
  if (probe === undefined) {
    lines.push('Проверка: текущие настройки ещё не проверяли.');
  } else if (probe.state !== 'finished' || probe.outcome === undefined) {
    // As the card says it: «<state>; запрошена <time>.»
    lines.push(`${PROBE_STATE_LABELS[probe.state]}; запрошена ${formatInstant(probe.requested_at)}.`);
  } else {
    lines.push(`Проверка: ${probeOutcomeSentence(probe.outcome)}`);
    if (probe.finished_at !== undefined) lines.push(`Проверено: ${formatInstant(probe.finished_at)}`);
    if (probe.reported_model !== undefined) {
      const basis = probe.identity_basis === undefined ? '' : ` (${IDENTITY_BASIS_LABELS[probe.identity_basis]})`;
      lines.push(`Модель в ответе: ${probe.reported_model}${basis}`);
    }
    if (probe.latency_ms !== undefined) lines.push(`Ответ за ${probe.latency_ms} мс`);
    if (probe.rate_check !== undefined) lines.push(`Сверка стоимости: ${RATE_CHECK_LABELS[probe.rate_check]}`);
    const hint = PROBE_OUTCOME_HINTS[probe.outcome];
    if (hint !== undefined) lines.push(`Подсказка: ${hint}`);
    if (probe.detail !== undefined && probe.detail !== '') lines.push(`Подробности: ${probe.detail}`);
    if (probe.outcome === 'ok' && !probeIsOnCurrentSecret(probe, connection, revision)) {
      lines.push('Проверка прошла на прежнем ключе: проверьте подключение ещё раз.');
    }
  }
  return lines.join('\n');
}
