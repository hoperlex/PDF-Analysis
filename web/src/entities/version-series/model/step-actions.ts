/**
 * The buttons of a step's cell and when each is offered (`version-comparison-projects.js:460-530` `stageActs`).
 *
 * * «2 Разбор версий»: «Повторить» when a version failed — it is `prepareComparisonMatrix`, which queues the
 *   profiles that are missing or failed (CMP-SEAL-C1 decision 7: there is no separate profile retry).
 * * «3 Сопоставление листов»: «Подготовить» when the matrix is not built, stale or failed.
 * * «5 Сравнение соседних»: «Запустить» (never started), «Пауза» (queued or running), «Продолжить» (paused: the
 *   series resumes; interrupted or failed: the series is finished — `finishComparisonSeries`, which the
 *   transitions block calls «Досчитать»), «Заново» (a finished or stale one: a new series that replaces it).
 *
 * Steps 1, 4, 6 and 7 offer none here. A `blocked` step waits for the one before it and offers nothing.
 */

import type { ComparisonStepCounts, ComparisonStepId, ComparisonStepState } from '@/shared/api';

export type StepActionId = 'prepare' | 'start' | 'pause' | 'resume' | 'finish' | 'restart';

export interface StepAction {
  readonly id: StepActionId;
  readonly label: string;
}

export function stepActions(
  step: ComparisonStepId,
  state: ComparisonStepState,
  counts?: ComparisonStepCounts,
): readonly StepAction[] {
  if (step === 'profile') {
    return state === 'failed' || (counts?.failed ?? 0) > 0 ? [{ id: 'prepare', label: 'Повторить' }] : [];
  }
  if (step === 'matrix') {
    return state === 'not_started' || state === 'stale' || state === 'failed'
      ? [{ id: 'prepare', label: 'Подготовить' }]
      : [];
  }
  if (step === 'series') {
    switch (state) {
      case 'not_started': return [{ id: 'start', label: 'Запустить' }];
      case 'queued':
      case 'running': return [{ id: 'pause', label: 'Пауза' }];
      case 'paused': return [{ id: 'resume', label: 'Продолжить' }, { id: 'restart', label: 'Заново' }];
      case 'interrupted':
      case 'failed': return [{ id: 'finish', label: 'Продолжить' }, { id: 'restart', label: 'Заново' }];
      case 'done':
      case 'stale':
      case 'partial':
      case 'attention': return [{ id: 'restart', label: 'Заново' }];
      default: return [];
    }
  }
  return [];
}

/** The confirmation «Заново» asks for (`:~498`): every transition is computed again. */
export const RESTART_CONFIRM_TITLE = 'Сравнение соседних заново';
export const RESTART_CONFIRM_TEXT =
  'Все переходы будут пересчитаны по текущему порядку и составу версий. Пары листов, которые не менялись, берутся из кэша.';
export const RESTART_CONFIRM_ACTION = 'Пересчитать';
