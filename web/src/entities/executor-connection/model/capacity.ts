/**
 * The capacity of a connection, in words (`EXEC2-WEB-CAP-01`, ADR-0026 decisions 1, 2 and 19).
 *
 * `max_active_runs` is how many units of one connection may be in use at once; the server counts a
 * Run in `leased`, `running` or `retry_wait` and a comparison model call in `prepared` or `sent`
 * as one unit each (`ExecutorOccupancy`). This module says what the screen prints about that:
 *
 * - the occupancy line of a card, «Занято N из M», where N is runs and calls together and the
 *   calls are named only when there is one;
 * - the hint that sits beside the field, which states the coupled limit of the connection's kind
 *   (decision 2) so a person sees the rule before the server refuses it;
 * - the `R-149a` notice, because client documents are not checked and capacity above one is for
 *   test data until they are (decision 19).
 *
 * **No sentence here says a connection is «свободно».** The occupancy is derived by the server at
 * read time from the database, and a unit held by work whose remote outcome is still unresolved is
 * counted; a screen that printed «свободно» next to it would offer a place that does not exist.
 * A reading that is absent, or whose members are not whole non-negative numbers, is therefore
 * drawn as nothing at all rather than as a guess.
 */

import type { ExecutorConnection, ExecutorKind } from '@/shared/api';

import { SSH_PROFILE_LABELS } from './vocabulary';

/** The label of the field, and the name a refusal of it carries. */
export const CAPACITY_FIELD_LABEL = 'Одновременных прогонов';

/**
 * The `R-149a` notice: the stand does not check whether a connection may receive client
 * documents (`allow_client_documents` is stored and not enforced, `D-291`), so capacity above one
 * and groups are for test data only.
 */
export const CLIENT_DOCUMENTS_NOTICE =
  'Допуск клиентских документов не проверяется: одновременные прогоны и группы — только для тестовых данных.';

/** What the field is, in every kind. */
export const CAPACITY_HINT =
  'От 1 до 16, по умолчанию 1. Столько прогонов подключения могут идти одновременно; место занимает и прогон, и вызов модели при сравнении версий. Меньшее число действует на новые прогоны и не останавливает идущие.';

/**
 * The coupled limit of each kind (ADR-0026 decision 2). The server validates it on the revision
 * and refuses a breach; the hint is what lets a person avoid the refusal.
 */
export const CAPACITY_COUPLING_HINTS: Readonly<Record<ExecutorKind, string>> = {
  http_api:
    'Число «Параллельных вызовов» выше не должно быть меньше числа одновременных прогонов: каждый прогон делает вызовы по одному.',
  pull:
    'Число «Заданий в работе одновременно» выше не должно быть меньше числа одновременных прогонов, иначе лишние прогоны завершатся как не отправленные.',
  ssh_command:
    `Для профиля «${SSH_PROFILE_LABELS.custom_command}» допустимо только значение 1: параллельные запуски своей команды стенд не изолирует.`,
};

/** How full a connection is. */
export type OccupancyState = 'idle' | 'in_use' | 'full' | 'over';

export interface OccupancyReading {
  /** Runs and calls together: the units in use. */
  readonly used: number;
  readonly capacity: number;
  readonly runs: number;
  readonly calls: number;
  /**
   * `idle`: nothing in use. `in_use`: some, with room. `full`: every unit. `over`: more units are
   * in use than the capacity now allows, which happens after the capacity was lowered; work in
   * flight is never stopped (decision 1).
   */
  readonly state: OccupancyState;
}

const isCount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0;

/** The occupancy of a connection, or `null` when it carries none to show. */
export function occupancyReading(connection: Pick<ExecutorConnection, 'occupancy'>): OccupancyReading | null {
  const occupancy = connection.occupancy;
  if (occupancy === undefined) return null;
  const { active_runs: runs, active_calls: calls, capacity } = occupancy;
  if (!isCount(runs) || !isCount(calls) || !isCount(capacity) || capacity < 1) return null;
  const used = runs + calls;
  const state: OccupancyState = used === 0 ? 'idle' : used < capacity ? 'in_use' : used === capacity ? 'full' : 'over';
  return { used, capacity, runs, calls, state };
}

/**
 * «Занято 3 из 4 (прогонов: 2, вызовов модели сравнения: 1).» — the calls are named only when
 * there is one, and a full connection says what happens to new work.
 */
export function occupancySentence(reading: OccupancyReading): string {
  const split = reading.calls > 0
    ? ` (прогонов: ${reading.runs}, вызовов модели сравнения: ${reading.calls})`
    : '';
  const head = `Занято ${reading.used} из ${reading.capacity}${split}`;
  if (reading.state === 'full') return `${head}: новые прогоны ждут в очереди.`;
  if (reading.state === 'over') {
    return `${head}: число одновременных прогонов уменьшили, идущая работа не прерывается, а новая ждёт в очереди.`;
  }
  return `${head}.`;
}
