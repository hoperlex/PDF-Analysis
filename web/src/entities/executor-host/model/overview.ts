/**
 * The strip of five numbers on the tab «Обзор» of «Диспетчер» (`UIP-S15-04`, `Г12-B`, `Г4-B`), as a pure function of plain values.
 *
 * ```
 * На связи 2 из 3 · Выполняется 3 · В очереди 4 · Ошибки 2 · Свободно мест 3 из 7
 * ```
 *
 * The servers' two numbers come from the list of servers; the three of the queue come from the queue's own overview, which the
 * widget reads and sums (`running` and `leased` are «Выполняется», `queued` and `retry_wait` are «В очереди», `live_failure_count` is
 * «Ошибки» — the number on the red badge of the menu's «Очередь»). This function does no reading: a queue that could not be read is
 * `null` here, and a number that is not known is a dash, never a zero.
 */

export type OverviewFigureKey = 'online' | 'running' | 'queued' | 'errors' | 'slots';

export interface OverviewFigure {
  readonly key: OverviewFigureKey;
  /** «На связи». */
  readonly label: string;
  /** «2 из 3», «3», or `—` when the number is not known. */
  readonly value: string;
  /** Errors are drawn as a warning when there is one; nothing else is. */
  readonly warning: boolean;
}

export interface OverviewInput {
  readonly online: number;
  readonly total: number;
  readonly slotsFree: number;
  readonly slotsTotal: number;
  /** The jobs running or leased; `null` when the queue is not read. */
  readonly running: number | null;
  /** The jobs queued or waiting to retry; `null` when the queue is not read. */
  readonly queued: number | null;
  /** The failures nothing has answered yet; `null` when the queue is not read or says none. */
  readonly failures: number | null;
}

/** What is shown for a number that is not known. */
export const UNKNOWN_FIGURE = '—';

export const OVERVIEW_LABELS: Readonly<Record<OverviewFigureKey, string>> = {
  online: 'На связи',
  running: 'Выполняется',
  queued: 'В очереди',
  errors: 'Ошибки',
  slots: 'Свободно мест',
};

/** The sentence the queue's failure is said in under the strip, when the three numbers of the queue are dashes because of it. */
export const OVERVIEW_QUEUE_NOT_READ = 'Очередь не прочитана: числа очереди не показаны.';

const count = (value: number | null): string => (value === null ? UNKNOWN_FIGURE : String(value));

export function overviewFigures(input: OverviewInput): readonly OverviewFigure[] {
  return [
    { key: 'online', label: OVERVIEW_LABELS.online, value: `${input.online} из ${input.total}`, warning: false },
    { key: 'running', label: OVERVIEW_LABELS.running, value: count(input.running), warning: false },
    { key: 'queued', label: OVERVIEW_LABELS.queued, value: count(input.queued), warning: false },
    { key: 'errors', label: OVERVIEW_LABELS.errors, value: count(input.failures), warning: input.failures !== null && input.failures > 0 },
    { key: 'slots', label: OVERVIEW_LABELS.slots, value: `${input.slotsFree} из ${input.slotsTotal}`, warning: false },
  ];
}
