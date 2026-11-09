/**
 * The words of the window «Подключить сервер» and of the commands on a server (`HOSTS-WEB-01`, plan 2026-11-09 §7.3).
 *
 * The window never asks for a model: a server brings its models itself, and the stand learns them from the agent's report.
 */

import type { ExecutorAgentInstallState } from '@/shared/api';

export const CONNECT_LABEL = 'Подключить сервер';
export const CONNECT_TITLE = 'Подключить сервер';
export const CONNECT_CLOSE_LABEL = 'Закрыть';

export const TAB_COMMAND = 'Командой в терминале';
export const TAB_SSH = 'По SSH';
export const CONNECT_TABS_LABEL = 'Как подключить сервер';

export const NAME_LABEL = 'Название сервера';
export const NAME_HINT = 'Под этим названием сервер виден в списке. Модели сервер сообщит сам.';
export const COMMAND_GET_LABEL = 'Получить команду';
export const COMMAND_FIELD = 'Команда для терминала сервера';
export const COMMAND_INTRO = 'Выполните эту строку в терминале сервера: Ubuntu, под пользователем, который будет запускать клиентов.';
export const COMMAND_ONCE =
  'Команда показана один раз: скопируйте её сейчас, повторно её показать нельзя. Она действует 15 минут и один раз.';
export const COMMAND_NEW_LABEL = 'Новая команда';
export const COMMAND_NEW_NOTE = 'Новая команда отменяет прежнюю: действует только последняя.';
export const COMMAND_SECRET_NOTE = 'Секрет регистрации передаётся установщику через окружение, а не через аргументы команды.';

export const WAITING_STATUS = 'ждём сервер…';
export const FOUND_NO_MODELS = 'сервер на связи, моделей пока нет: агент ещё проверяет клиентов';
export function foundStatus(models: string): string {
  return `найдено: ${models}`;
}

export const SSH_INTRO = 'Стенд сам зайдёт на сервер и поставит агента. Пароли не принимаются.';
export const SSH_HOST_LABEL = 'Узел SSH';
export const SSH_USER_LABEL = 'Пользователь SSH';
export const SSH_PORT_LABEL = 'Порт SSH';
export const SSH_ADVANCED = 'Дополнительно';
export const SSH_KEY_NOTE =
  'Ключ создаст стенд: закрытая часть остаётся на стенде и удаляется после установки. Свой закрытый ключ в это окно не вводится.';
export const SSH_START_LABEL = 'Начать установку';
export const SSH_NEEDS_HOST = 'Укажите узел и пользователя SSH.';
export const SSH_PORT_PROBLEM = 'Порт — число от 1 до 65535.';

export const KEY_LINE_TITLE = 'Строка для authorized_keys';
export const KEY_LINE_HINT =
  'Добавьте эту строку в файл authorized_keys указанного пользователя на сервере. После установки стенд удалит её сам.';
export const FINGERPRINT_TITLE = 'Отпечаток ключа сервера';
export const FINGERPRINT_HINT =
  'Сравните его с тем, что показывает сам сервер. Без сверки установку может перехватить тот, кто подменил ключ.';
export const FINGERPRINT_WAITING = 'Отпечаток ещё не получен: окно обновится само.';
export const FINGERPRINT_CHECK = 'Я сверил отпечаток с сервером';
export const FINGERPRINT_CONFIRM = 'Подтвердить отпечаток';
export const INSTALL_RETRY = 'Попробовать снова';
export const INSTALL_FAILED_FALLBACK = 'Установка не удалась, причина не названа.';

/** The three steps of the install, in the order the person meets them. */
export const INSTALL_STEP_IDS = ['fingerprint', 'confirm', 'install'] as const;
export type InstallStepId = (typeof INSTALL_STEP_IDS)[number];

export const INSTALL_STEP_LABELS: Readonly<Record<InstallStepId, string>> = {
  fingerprint: 'Читаем отпечаток сервера',
  confirm: 'Подтвердите отпечаток',
  install: 'Ставим агента',
};

export type InstallStepState = 'done' | 'current' | 'todo' | 'failed';

/**
 * Where the three steps stand for an install session in `state`. `requested` and `scanning` are the first step (the worker
 * reads the host key); `awaiting_host_key` is the person's, the second; `installing` is the third; `succeeded` has all three
 * done. A failed session marks the step it stopped at, which the failure reason cannot say, so it marks the last one reached
 * from the observed fingerprint: no fingerprint, the first; a fingerprint not yet confirmed, the second; otherwise the third.
 */
export function installSteps(
  state: ExecutorAgentInstallState,
  progress: { readonly fingerprintSeen: boolean; readonly confirmed: boolean },
): Readonly<Record<InstallStepId, InstallStepState>> {
  switch (state) {
    case 'requested':
    case 'scanning':
      return { fingerprint: 'current', confirm: 'todo', install: 'todo' };
    case 'awaiting_host_key':
      return { fingerprint: 'done', confirm: 'current', install: 'todo' };
    case 'installing':
      return { fingerprint: 'done', confirm: 'done', install: 'current' };
    case 'succeeded':
      return { fingerprint: 'done', confirm: 'done', install: 'done' };
    case 'failed':
      return !progress.fingerprintSeen
        ? { fingerprint: 'failed', confirm: 'todo', install: 'todo' }
        : !progress.confirmed
          ? { fingerprint: 'done', confirm: 'failed', install: 'todo' }
          : { fingerprint: 'done', confirm: 'done', install: 'failed' };
  }
}

export const STEP_STATE_MARKS: Readonly<Record<InstallStepState, string>> = {
  done: '✓',
  current: '…',
  todo: '·',
  failed: '✗',
};

export const STEP_STATE_WORDS: Readonly<Record<InstallStepState, string>> = {
  done: 'готово',
  current: 'сейчас',
  todo: 'впереди',
  failed: 'не удалось',
};

// ------------------------------------------------------------------------------ the server row

export const DELETE_CONFIRM_LABEL = 'Удалить сервер';
export const DELETE_CANCEL_LABEL = 'Отмена';
export function deleteQuestion(name: string): string {
  return `Удалить сервер «${name}»? Это необратимо: его ключ отзывается, а прогоны, уже привязанные к нему, доходят до конца.`;
}

export const DETAILS_TITLE = 'Подробнее';
export const DETAILS_RECHECK = 'Проверить сейчас';
export const DETAILS_RECHECK_HINT = 'Читает состояние сервера заново; агент сам проверяет модели при изменениях и раз в несколько часов.';
export const DETAILS_SLOTS_TITLE = 'Места';
export const DETAILS_SLOTS_SAVE = 'Сохранить места';
export const DETAILS_SLOTS_HINT = 'Сколько вызовов клиента сервер ведёт одновременно: от 1 до 16.';
export const DETAILS_PROVIDERS_TITLE = 'Клиенты и модели';
export const DETAILS_TASKS_TITLE = 'Сейчас на сервере';
export const DETAILS_NO_TASKS = 'Сейчас на сервере ничего не выполняется.';
export const DETAILS_NO_PROVIDERS = 'Клиентов на сервере пока не найдено.';
