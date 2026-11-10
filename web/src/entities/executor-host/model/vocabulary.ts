/**
 * The words of «Серверы» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §6 and §7).
 *
 * Every table is a `Record` over the contract's own value set, so a value the contract adds is a type error here until it has a
 * Russian sentence. The reasons a model cannot be used are worded here and shown only where an action is blocked, where a run
 * waits and, for an administrator, in «Подробнее» of a server (plan §6): a list of servers or models never draws what is
 * unavailable.
 */

import type {
  ExecutorHostState,
  ExecutorModelAccess,
  ExecutorProvider,
  ModelUnavailableReason,
  ProviderAuthState,
} from '@/shared/api';

export const SERVERS_TITLE = 'Серверы';

/**
 * The `D-291` warning, one line, while the debt is open: the stand does not check whether a server may receive a client's
 * documents, so servers are for test data (`R-149a`). It stays in the list and in the window that connects a server.
 */
export const CLIENT_DOCUMENTS_LINE =
  'Не для клиентских документов: допуск таких документов к серверу стенд не проверяет.';

export const SERVERS_EMPTY = 'Серверов пока нет.';
export const SERVERS_EMPTY_ADMIN = 'Серверов пока нет. Подключите первый кнопкой «Подключить сервер».';

export const USE_LABEL = 'Использовать';
export const USE_HINT = 'Выключенный сервер не берёт новые прогоны; начатые он доведёт до конца.';
export const NO_MODELS = 'нет доступных моделей';
export const API_MARK = 'API';
export const API_MARK_HINT = 'Платная модель: вызовы оплачиваются по ключу API.';

export const MENU_LABEL = 'Действия сервера';
export const MENU_DETAILS = 'Подробнее';
export const MENU_DELETE = 'Удалить';

/** «нет связи с 14:02», or that the server has never been in touch. */
export function noContactSentence(lastSeen: string | undefined): string {
  if (lastSeen === undefined) return 'нет связи: сервер ещё не выходил на связь';
  const moment = new Date(lastSeen);
  if (Number.isNaN(moment.getTime())) return 'нет связи';
  const hours = String(moment.getHours()).padStart(2, '0');
  const minutes = String(moment.getMinutes()).padStart(2, '0');
  return `нет связи с ${hours}:${minutes}`;
}

/** «На связи 2 из 3 · свободно 3 из 5». */
export function summarySentence(online: number, total: number, slotsFree: number, slotsTotal: number): string {
  return `На связи ${online} из ${total} · свободно ${slotsFree} из ${slotsTotal}`;
}

export const HOST_STATE_LABELS: Readonly<Record<ExecutorHostState, string>> = {
  online: 'на связи',
  busy: 'все места заняты',
  offline: 'нет связи',
};

export const PROVIDER_LABELS: Readonly<Record<ExecutorProvider, string>> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  anthropic_api: 'Claude по ключу API',
  openai_api: 'Codex по ключу API',
  openrouter_api: 'OpenRouter',
};

export const ACCESS_LABELS: Readonly<Record<ExecutorModelAccess, string>> = {
  subscription: 'по подписке',
  api: 'по ключу API',
};

export const AUTH_STATE_LABELS: Readonly<Record<ProviderAuthState, string>> = {
  valid: 'вход выполнен',
  login_required: 'нужно войти на сервере',
  unknown: 'вход не определён',
};

/** Why a model cannot be used on a server now. */
export const UNAVAILABLE_REASON_SENTENCES: Readonly<Record<ModelUnavailableReason, string>> = {
  host_disabled: 'сервер выключен переключателем «Использовать»',
  host_offline: 'сервер не на связи',
  login_required: 'на сервере нужно войти в клиент',
  model_not_verified: 'агент сервера ещё не подтвердил эту модель',
  model_cooling_down: 'сервер временно снял модель после отказа',
  not_on_any_server: 'модели нет ни на одном сервере',
};

export const MODEL_STATE_LABELS = {
  available: 'доступна',
  busy: 'все места заняты',
  unavailable: 'недоступна',
} as const;
