/**
 * Refusals of the commands on the stage layout, worded (`HOSTS-WEB-01`).
 *
 * `reviseStageModelLayout` refuses a cell that is not a pair of the catalogue, a repeated or missing cell key and a scheme
 * chosen leg by leg through `validation_failed`; `setStageModelLayoutEnabled` refuses through `conflict` with
 * `no_layout_revision` or `provider_source_not_database`. Every other refusal keeps `executionFailure`'s catalogue sentence.
 */

import { ApiError } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { executionFailure } from '@/entities/execution';

const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  no_layout_revision: 'Включить нельзя: набор моделей ещё не сохранён. Сохраните его на вкладке «Модели по этапам».',
  provider_source_not_database:
    'Включить нельзя: стенд берёт исполнителей не из базы данных. Это настройка стенда, её меняет не экран.',
};

const VALIDATION_SENTENCE =
  'Набор не принят: модель и усилие каждой строки должны быть парой из каталога. Выберите их из списков.';

export function layoutRefusalSentence(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.errorCode === 'conflict') {
    const reason = error.details['conflict_reason'];
    return typeof reason === 'string' ? (CONFLICT_SENTENCES[reason] ?? null) : null;
  }
  if (error.errorCode === 'validation_failed') return VALIDATION_SENTENCE;
  return null;
}

export function layoutFailure(error: unknown, write: boolean): ExecutionFailure {
  const base = executionFailure(error, write);
  const sentence = layoutRefusalSentence(error);
  if (sentence !== null && base.kind !== 'unknown_outcome') return { ...base, detail: sentence };
  return base;
}
