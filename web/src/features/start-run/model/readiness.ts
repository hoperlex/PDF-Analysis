/**
 * What the line under «Запустить» says (`READINESS-WEB-01`, plan 2026-11-09 §8): the set, how it is paid, what is missing.
 *
 * Pure: the `getRunStartReadiness` answer in, the words out. This file invents none of them: the set is the layout's own
 * (`STAGE_KIT_LABELS`), the access is the answer's `access`, and a model that no server has is a cell the answer marks
 * `available: false`.
 *
 *   «Набор: Только Claude · по подписке · ⚠ не для клиентских документов · Модели по этапам ▸»
 *   «Набор: Только Claude · часть по API — покажем оценку · ⚠ не для клиентских документов · Модели по этапам ▸»
 *   «Маршрут: прежний»                        the layout is off: the route is the automatic one as before
 *   «Маршрут: автоматически»                  the server answered 503: it has no layout to speak of (the line as it was)
 *
 * **Blocked.** The button is inactive when `ready` is false on the layout's route, and the reason is the models the plan names
 * and no server has: «Нет Opus 5.5 — Анализ блоков · обратитесь к администратору». The reason is never softened into a
 * start that would wait: the server holds such a run `pending` with `model_unavailable` (ADR-0028 decision 15).
 */

import type { RunStartReadiness } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { STAGE_KIT_LABELS, missingModelSentences } from '@/entities/stage-layout';

/** The line while the layout is off: the one automatic route, as before. */
export const LEGACY_ROUTE_NOTE = 'Маршрут: прежний';
/** `D-291`, short, while the debt is open: a server is not checked for client documents (the long sentence is on «Серверы»). */
export const CLIENT_DOCUMENTS_MARK = '⚠ не для клиентских документов';
export const MODELS_BY_STAGE_LABEL = 'Модели по этапам ▸';
export const READINESS_READING = 'Проверяем готовность…';
export const READINESS_NOT_READ = 'Готовность запуска не прочитана; запуск проверит её сам.';
export const CONTACT_ADMIN = 'обратитесь к администратору';
export const CONNECT_SERVER = 'подключите сервер в «Исполнители»';
/** The reason when the answer says `ready: false` and names no cell: said as it is, not hidden. */
export const NOT_READY = 'Запуск сейчас невозможен';

/** How the plan is paid, in the words of the line: the total of the cells. */
export const ACCESS_WORDS: Readonly<Record<NonNullable<RunStartReadiness['access']>, string>> = {
  subscription: 'по подписке',
  api: 'по API — покажем оценку',
  mixed: 'часть по API — покажем оценку',
};

/** The server answered that it has no stage layout to read: a typed 503, which is not an error for the person. */
export function layoutNotAvailable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503;
}

export type ReadinessLine =
  /** The layout is off. */
  | { readonly kind: 'legacy' }
  /** The layout is on: the set (absent before its first revision) and how the plan is paid (absent while a cell has no server). */
  | { readonly kind: 'plan'; readonly kit: string | null; readonly access: string | null };

export function readinessLine(readiness: RunStartReadiness): ReadinessLine {
  if (readiness.route === 'legacy') return { kind: 'legacy' };
  return {
    kind: 'plan',
    kit: readiness.kit === undefined ? null : STAGE_KIT_LABELS[readiness.kit],
    access: readiness.access === undefined ? null : ACCESS_WORDS[readiness.access],
  };
}

/**
 * Why «Запустить» is inactive, or `null` when it is not: «Нет Opus 5.5 — Анализ блоков» (several models: separated by «; »).
 * Only the layout's route can block a start; with the layout off the answer is the estimate as before and holds nothing back.
 */
export function blockedModels(readiness: RunStartReadiness): string | null {
  if (readiness.route !== 'stage_plan' || readiness.ready) return null;
  const missing = missingModelSentences(readiness.cells);
  return missing.length === 0 ? NOT_READY : missing.join('; ');
}
