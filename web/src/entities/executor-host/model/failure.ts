/**
 * Refusals of the commands on a server, worded (`HOSTS-WEB-01`).
 *
 * `HOSTS-SEAL-1` adds no error code: the host commands refuse through `conflict` (a `conflict_reason`), `validation_failed`
 * (a `field` and a `constraint`) and `dependency_unavailable`, the safe detail keys the connection commands use. This module
 * words the ones that are new and leaves every other refusal to `executionFailure`, whose catalogue sentence is never the
 * server's English message.
 */

import { ApiError } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { executionFailure } from '@/entities/execution';

const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  host_archived: 'Сервер удалён: изменить его уже нельзя.',
  enrollment_shown_once:
    'Команда для этого запроса уже была показана, повторно её показать нельзя. Запросите новую команду.',
};

const DEPENDENCY_SENTENCES: Readonly<Record<string, string>> = {
  agent_package: 'Пакет агента на стенде сейчас недоступен: команду выпустить нельзя, попробуйте позже.',
  public_origin: 'Публичный адрес стенда не задан: команду для сервера выпустить нельзя.',
};

const UNKNOWN_OUTCOME_ISSUE =
  'Ответ не получен, и неизвестно, выпущена ли команда. Запросите новую: прежняя тогда перестанет действовать.';

function detail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refusal this module words; `null` for any other. */
export function hostRefusalSentence(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.errorCode === 'conflict') {
    const reason = detail(error, 'conflict_reason');
    return reason === null ? null : (CONFLICT_SENTENCES[reason] ?? null);
  }
  if (error.errorCode === 'dependency_unavailable') {
    const dependency = detail(error, 'dependency');
    return dependency === null ? null : (DEPENDENCY_SENTENCES[dependency] ?? null);
  }
  if (error.errorCode === 'validation_failed') {
    const field = detail(error, 'field');
    if (field === 'display_name') return 'Сервер с таким названием уже есть: выберите другое название.';
    if (field === 'ssh_host') return 'Адрес сервера не принят: проверьте его написание.';
    if (field === 'ssh_user') return 'Пользователь не принят: проверьте его написание.';
    if (field === 'slots') return 'Число мест — от 1 до 16 для каждого клиента, который есть на сервере.';
  }
  return null;
}

/**
 * The failure of a command or a read on a server. A definite refusal gets its sentence; an unknown outcome keeps the shared
 * one, except for the command that shows a secret once (`issueExecutorHostEnrollment`), where a repeat is a new grant.
 */
export function hostFailure(error: unknown, write: boolean, showsSecretOnce = false): ExecutionFailure {
  const base = executionFailure(error, write);
  const sentence = hostRefusalSentence(error);
  if (sentence !== null) {
    const definite = base.kind !== 'unknown_outcome'
      || (error instanceof ApiError && error.errorCode === 'dependency_unavailable');
    if (definite) return { ...base, kind: base.kind === 'unknown_outcome' ? 'refusal' : base.kind, detail: sentence };
  }
  if (showsSecretOnce && base.kind === 'unknown_outcome') return { ...base, detail: UNKNOWN_OUTCOME_ISSUE };
  return base;
}
