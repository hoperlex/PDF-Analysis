/**
 * The words of a series of transitions: the state of the series, of one transition, the progress and the
 * order it ran on (`version-comparison.js:1044-1046` `pairStateLabel`, `:1145-1151` `runStateLabel`,
 * `:1145`, `:127`).
 */

import type {
  ComparisonSeries,
  ComparisonSeriesStaleReason,
  ComparisonSeriesState,
  ComparisonTransition,
  ComparisonTransitionState,
} from '@/shared/api';

export const SERIES_STATE_LABELS: Readonly<Record<ComparisonSeriesState, string>> = {
  queued: 'в очереди',
  running: 'идёт сравнение',
  paused: 'на паузе (можно продолжить)',
  completed: 'готово',
  failed: 'ошибка (можно досчитать)',
  cancelled: 'отменено (можно досчитать)',
};

export const TRANSITION_STATE_LABELS: Readonly<Record<ComparisonTransitionState, string>> = {
  queued: 'в очереди',
  running: 'считается…',
  completed: 'готово',
  failed: 'ошибка',
  cancelled: 'отменено',
};

export const SERIES_STALE_LABELS: Readonly<Record<ComparisonSeriesStaleReason, string>> = {
  order_changed: 'порядок версий изменился',
  matrix_changed: 'сопоставление листов изменилось',
  profiles_changed: 'страницы версий прочитаны заново',
};

/** The sentence over a series whose stored input no longer matches (`:127`), with the reasons. */
export const STALE_SERIES_NOTE = 'Сохранённая сводка для прежнего порядка версий.';

export function staleReasonsLine(reasons: readonly ComparisonSeriesStaleReason[] | undefined): string {
  const words = (reasons ?? []).map((reason) => SERIES_STALE_LABELS[reason]);
  return words.length === 0 ? '' : `Что изменилось: ${words.join('; ')}.`;
}

/** Whether a series may still be stopped (`['queued','running']`, `:128`). */
export function canCancelSeries(state: ComparisonSeriesState): boolean {
  return state === 'queued' || state === 'running' || state === 'paused';
}

/** «Продолжить» continues a paused series; «Досчитать» finishes one that stopped (CMP-SEAL-C1 decision 8). */
export type SeriesContinue = 'resume' | 'finish' | null;

/**
 * Something is left to compute in a series that has ended: a transition that did not complete (queued, running, failed or
 * cancelled) or one with a pair that failed (`CMP-SERIES-01` section 5 decision 4: «Досчитать» queues exactly those again).
 */
export function hasLeftovers(series: Pick<ComparisonSeries, 'transitions'>): boolean {
  return (series.transitions ?? []).some(
    (item) => item.state !== 'completed' || item.summary.failed > 0,
  );
}

export function continueOf(series: Pick<ComparisonSeries, 'state' | 'transitions'>): SeriesContinue {
  if (series.state === 'paused') return 'resume';
  if (series.state === 'failed' || series.state === 'cancelled') return 'finish';
  if (series.state === 'completed' && hasLeftovers(series)) return 'finish';
  return null;
}

/** «Заново» replaces a series that is not live; a queued, running or paused one is `comparison_series_active`. */
export function canRestart(state: ComparisonSeriesState): boolean {
  return state === 'completed' || state === 'failed' || state === 'cancelled';
}

export function progressPercent(done: number, total: number): number {
  return total > 0 ? Math.round((100 * done) / total) : 0;
}

/** The newest series, which is the one the screen shows (`listComparisonSeries` answers newest first). */
export function latestSeries(items: readonly ComparisonSeries[]): ComparisonSeries | null {
  return items[0] ?? null;
}

export function transitionOf(
  transitions: readonly ComparisonTransition[] | undefined,
  sourceVersionUid: string,
  targetVersionUid: string,
): ComparisonTransition | null {
  return (
    transitions?.find(
      (item) => item.source_version_uid === sourceVersionUid && item.target_version_uid === targetVersionUid,
    ) ?? null
  );
}
