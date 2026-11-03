/**
 * One Russian sentence for every reason of every lifecycle step (`EXEC2-WEB-WIZARD-01`).
 *
 * The reasons are a closed set (`AgentStepReasons`), so each table here is a `Record` over it: a
 * reason added to the lifecycle is a type error until it has a sentence. The sentences that carry a
 * time print it with `formatInstant`; none prints a token, a path or a credential, because the
 * lifecycle holds none.
 */

import type { ExecutorProbeOutcome } from '@/shared/api';
import { PROBE_OUTCOME_HINTS, probeOutcomeSentence } from '@/entities/executor-connection';
import { formatInstant } from '@/shared/lib';

import type { AgentLifecycle, AgentStepId, AgentStepReasons } from './lifecycle';
import { AGENT_PROBE_HINTS } from './words';

const REGISTRATION: Readonly<Record<AgentStepReasons['registration'], string>> = {
  not_started: 'Агент ещё не устанавливали. Получите команду установки или установите агента по SSH.',
  waiting: 'Ожидает регистрации: выполните команду на сервере или дождитесь установки по SSH.',
  expired:
    'Команда устарела: срок её действия истёк, а агент не зарегистрировался. Получите новую команду.',
  replaced:
    'Команда заменена новой или отозвана, а агент не зарегистрировался. Получите новую команду.',
  token_gone:
    'Агент был зарегистрирован, но его токен отозван или истёк. Получите новую команду.',
  registered: 'Агент зарегистрирован на стенде.',
};

const INSTALLED: Readonly<Record<AgentStepReasons['installed'], string>> = {
  no_report: 'Агент ещё не сообщил о клиентах командной строки.',
  missing:
    'Ни один официальный клиент командной строки (Claude Code или codex) на сервере не найден.',
  found: 'Найден официальный клиент командной строки.',
};

const LOGIN: Readonly<Record<AgentStepReasons['login'], string>> = {
  no_client: 'Сначала нужен установленный клиент.',
  unknown:
    'Состояние входа неизвестно: клиент не умеет сообщать его сам. Проба модели покажет, работает ли вход.',
  login_required: 'Нужен вход. Войдите в клиент официальной командой от имени служебного пользователя агента.',
  valid: 'Вход действителен: клиент сообщил об этом своим официальным способом.',
};

const AUTHORISED: Readonly<Record<AgentStepReasons['authorised'], string>> = {
  not_set:
    'Отметка не поставлена. Это отметка администратора: она не следует из входа клиента и не заменяет его.',
  set: 'Администратор отметил, что работа через клиентов командной строки этого сервера для интеграции разрешена.',
};

const READY: Readonly<Record<AgentStepReasons['ready'], string>> = {
  not_ready: 'Не готово: выполните шаги выше, которые ждут действия.',
  ready: 'Агент готов принимать задания.',
};

function lastSeen(lifecycle: AgentLifecycle): string {
  return formatInstant(lifecycle.token?.last_seen_at);
}

function onlineSentence(lifecycle: AgentLifecycle): string {
  switch (lifecycle.steps.online.reason) {
    case 'waiting_registration':
      return 'Станет известно после регистрации агента.';
    case 'never_seen':
      return 'Агент зарегистрирован, но ещё не обращался к стенду.';
    case 'offline':
      return `Агент не в сети. Последнее обращение: ${lastSeen(lifecycle)}. Проверьте, что служба агента запущена на сервере и сервер видит стенд.`;
    case 'online':
      return `Агент в сети. Последнее обращение: ${lastSeen(lifecycle)}.`;
  }
}

function registrationSentence(lifecycle: AgentLifecycle): string {
  if (lifecycle.steps.registration.reason === 'waiting' && lifecycle.pendingEnrollment !== null) {
    return `${REGISTRATION.waiting} Команда действует до ${formatInstant(lifecycle.pendingEnrollment.expires_at)}.`;
  }
  return REGISTRATION[lifecycle.steps.registration.reason];
}

/**
 * What to do about an outcome of a pull agent's probe: the agent wording first, where the gateway
 * wording of the shared table would mislead («Шлюз назвал…»), the shared table after it.
 */
export function agentProbeHint(outcome: ExecutorProbeOutcome): string | undefined {
  return AGENT_PROBE_HINTS[outcome] ?? PROBE_OUTCOME_HINTS[outcome];
}

function probeSentence(lifecycle: AgentLifecycle): string {
  switch (lifecycle.steps.probe.reason) {
    case 'not_requested':
      return 'Проба модели ещё не запускалась. Запустите её кнопкой «Проверить» в этой карточке, когда агент в сети и вход выполнен.';
    case 'open':
      return 'Проба идёт: агент должен взять проверочное задание.';
    case 'stale':
      return 'Проба прошла до регистрации нынешнего агента, то есть на другом сервере. Запустите её снова кнопкой «Проверить».';
    case 'passed':
      return 'Проба модели пройдена.';
    case 'failed': {
      const outcome = lifecycle.probe?.outcome;
      if (outcome === undefined) return 'Проба не пройдена.';
      const hint = agentProbeHint(outcome);
      return `Проба не пройдена: ${probeOutcomeSentence(outcome)}.${hint === undefined ? '' : ` ${hint}`}`;
    }
  }
}

/** The sentence under a step's label. */
export function stepSentence(lifecycle: AgentLifecycle, id: AgentStepId): string {
  switch (id) {
    case 'registration': return registrationSentence(lifecycle);
    case 'online': return onlineSentence(lifecycle);
    case 'installed': return INSTALLED[lifecycle.steps.installed.reason];
    case 'login': return LOGIN[lifecycle.steps.login.reason];
    case 'authorised': return AUTHORISED[lifecycle.steps.authorised.reason];
    case 'probe': return probeSentence(lifecycle);
    case 'ready': return READY[lifecycle.steps.ready.reason];
  }
}
