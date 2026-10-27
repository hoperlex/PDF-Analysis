/**
 * Refusals of the preset commands, worded (`ANALYSIS-PRESETS-01`).
 *
 * As for the connection commands, a refusal reaches the browser through the catalogue's existing
 * codes and their existing detail keys: `validation_failed` names a `field` and a `constraint`,
 * `conflict` a `conflict_reason`. Each value the preset commands choose has a Russian sentence
 * here, and a value this table does not know falls back to the code's own catalogue sentence —
 * never to the English message of the server.
 */

import { ApiError } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';

const CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  required: 'Название нужно заполнить.',
  type: 'Название должно быть текстом.',
  max_length: 'Название длиннее 120 знаков.',
  printable: 'В названии не должно быть управляющих знаков и переносов строк.',
  unknown_connection: 'Такого исполнителя на стенде нет. Выберите исполнителя из списка.',
  differs_from_current: 'Ничего не изменилось: название и исполнитель те же. Измените хотя бы одно из двух.',
  pattern: 'Значение не подходит по написанию.',
};

const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  preset_name_in_use:
    'Пресет с таким названием уже есть. У действующих пресетов названия разные, регистр букв не важен.',
  preset_limit_reached: 'Пресетов уже сто, больше сохранить нельзя. Архивные тоже считаются.',
  preset_archived: 'Пресет в архиве: его нельзя ни изменить, ни выбрать для прогона.',
  connection_archived: 'Исполнитель в архиве. Выберите другого.',
};

function stringDetail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refusal this table can explain; `null` for any other. */
export function presetRefusalSentence(error: ApiError): string | null {
  if (error.errorCode === 'validation_failed') {
    const constraint = stringDetail(error, 'constraint');
    return constraint === null ? null : (CONSTRAINT_SENTENCES[constraint] ?? null);
  }
  if (error.errorCode === 'conflict') {
    const reason = stringDetail(error, 'conflict_reason');
    return reason === null ? null : (CONFLICT_SENTENCES[reason] ?? null);
  }
  return null;
}

/**
 * The failure of a preset read or command. An unknown outcome keeps the shared sentence (nothing
 * may be said about what the server did); every definite refusal gets the specific sentence.
 */
export function presetFailure(error: unknown, write: boolean): ExecutionFailure {
  const base = executionFailure(error, write);
  if (!(error instanceof ApiError)) return base;
  const sentence = presetRefusalSentence(error);
  if (sentence === null || base.kind === 'unknown_outcome') return base;
  return { ...base, detail: sentence };
}
