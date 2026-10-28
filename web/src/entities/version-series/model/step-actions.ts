/**
 * The buttons of a step's cell and when each is offered (`version-comparison-projects.js:460-530` `stageActs`;
 * `CMP-VC-OVERVIEW-01` section 6.4). A button is offered only where the server accepts its command
 * (`src/auditmanager/comparison/series/service.py`):
 *
 * * «2 Разбор версий»: «Повторить» when the step failed — it is `prepareComparisonMatrix`, which queues the
 *   profiles that are missing or failed (CMP-SEAL-C1 decision 7: there is no separate profile retry). A step that
 *   is running with a stored failure is a retry in progress and offers nothing.
 * * «3 Сопоставление листов»: «Подготовить» when the matrix is not built or stale, «Повторить» when its build failed;
 *   both are `prepareComparisonMatrix`.
 * * «5 Сравнение соседних»: «Запустить» (never started; `startComparisonSeries`), «Пауза» (queued or running;
 *   `pauseComparisonSeries`), «Продолжить» (a paused series only; `resumeComparisonSeries`), «Досчитать» (a failed or
 *   interrupted series with a transition left, `done` below `total`; `finishComparisonSeries`, refused with nothing
 *   left) and «Заново» (a finished, failed, interrupted or stale one: `startComparisonSeries` with `restart`, refused
 *   with `comparison_series_active` while a series is queued, running or paused).
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
    return state === 'failed' ? [{ id: 'prepare', label: 'Повторить' }] : [];
  }
  if (step === 'matrix') {
    if (state === 'failed') return [{ id: 'prepare', label: 'Повторить' }];
    return state === 'not_started' || state === 'stale' ? [{ id: 'prepare', label: 'Подготовить' }] : [];
  }
  if (step === 'series') {
    switch (state) {
      case 'not_started': return [{ id: 'start', label: 'Запустить' }];
      case 'queued':
      case 'running': return [{ id: 'pause', label: 'Пауза' }];
      case 'paused': return [{ id: 'resume', label: 'Продолжить' }];
      case 'interrupted':
      case 'failed': {
        // `finishComparisonSeries` is refused unless a transition is left; both figures must be known to say there is one.
        const left = counts?.done !== undefined && counts.total !== undefined && counts.done < counts.total;
        return left
          ? [{ id: 'finish', label: 'Досчитать' }, { id: 'restart', label: 'Заново' }]
          : [{ id: 'restart', label: 'Заново' }];
      }
      case 'done':
      case 'stale': return [{ id: 'restart', label: 'Заново' }];
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
