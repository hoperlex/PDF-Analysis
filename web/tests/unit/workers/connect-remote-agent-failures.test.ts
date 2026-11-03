/**
 * `EXEC2-WEB-WIZARD-01` — the Russian messages of the wizard, and how each refusal of the new
 * operations maps to one (ADR-0026 decision 18: EXEC-2 adds no error code, so every refusal is an
 * existing code with a typed detail).
 *
 * The messages the task names: an expired or redeemed command, an offline agent, a missing client, a
 * login that is needed, an unsupported model, each way an install fails, and a stand without a package
 * or a public address. Written under `R-149d`: not run in EXEC-2. None of these needs a database.
 */

import { describe, expect, it } from 'vitest';

import {
  CONFLICT_SENTENCES,
  COMMAND_UNKNOWN_OUTCOME,
  DEPENDENCY_SENTENCES,
  INSTALL_FAILURE_SENTENCES,
  VALIDATION_SENTENCES,
  agentFailure,
  agentLifecycle,
  agentRefusalSentence,
  stepSentence,
} from '@/features/connect-remote-agent';
import { ApiError, CONTRACT_VERSION } from '@/shared/api';
import type { ErrorCode } from '@/shared/api';

import { connectionId } from './executor-fixtures';
import { MINUTE, NOW, agentCase, agentToken, at, claude } from './connect-remote-agent-fixtures';

const CID = connectionId(65);

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  return new ApiError(status, {
    contract_version: CONTRACT_VERSION, error_code: code, message: 'Safe.', correlation_id: 'cid-agent-1', retryable: false, details,
  }, null);
}

const conflict = (reason: string) => refusal(409, 'conflict', { conflict_reason: reason });
const invalid = (field: string, constraint: string) => refusal(422, 'validation_failed', { field, constraint });
const missing = (dependency: string) => refusal(503, 'dependency_unavailable', { dependency });

const sentenceOf = (error: ApiError, secretOnce = false) => agentFailure(error, true, secretOnce);

describe('a command that was shown once cannot be shown again, and a used one cannot be used again', () => {
  it('words a repeat of a shown command, and sends the person to «Новая команда»', () => {
    const failure = sentenceOf(conflict('enrollment_shown_once'), true);
    expect(failure.kind).toBe('conflict');
    expect(failure.detail).toBe(CONFLICT_SENTENCES.enrollment_shown_once);
    expect(failure.detail).toContain('повторно показана быть не может');
    expect(failure.detail).toContain('Новая команда');
  });

  it('words a command that was already redeemed', () => {
    const failure = sentenceOf(conflict('enrollment_redeemed'));
    expect(failure.detail).toBe(CONFLICT_SENTENCES.enrollment_redeemed);
    expect(failure.detail).toContain('уже использована');
  });

  it('words an expired command as the lifecycle’s «Команда устарела», for the server’s word and the clock’s', () => {
    for (const grant of [{ state: 'expired' as const, expires_at: at(MINUTE) }, { state: 'pending' as const, expires_at: at(1) }]) {
      const c = agentCase({ n: 65, enrollments: [grant] });
      const sentence = stepSentence(agentLifecycle(c.connection, c.detail, NOW), 'registration');
      expect(sentence).toContain('Команда устарела');
      expect(sentence).toContain('Получите новую команду');
    }
  });

  it('tells a person who lost the answer that the command may exist and a new one cancels it', () => {
    const lost = agentFailure(new Error('сеть'), true, true);
    expect(lost.kind).toBe('unknown_outcome');
    expect(lost.detail).toBe(COMMAND_UNKNOWN_OUTCOME);
    expect(lost.detail).toContain('Новая команда');
    expect(lost.detail).toContain('перестанет действовать');
    // Another command says what every command says.
    expect(agentFailure(new Error('сеть'), true).detail).not.toBe(COMMAND_UNKNOWN_OUTCOME);
    // The same key still running is an unknown outcome too.
    const running = agentFailure(refusal(409, 'idempotency_key_in_progress'), true, true);
    expect(running.kind).toBe('unknown_outcome');
    expect(running.detail).toBe(COMMAND_UNKNOWN_OUTCOME);
  });

  it('keeps a definite refusal’s own sentence even for the command that shows a secret once', () => {
    const failure = sentenceOf(conflict('enrollment_shown_once'), true);
    expect(failure.detail).not.toBe(COMMAND_UNKNOWN_OUTCOME);
  });
});

describe('a stand that cannot build the command', () => {
  it('words a missing agent package and a missing public address as definite refusals, not as an unknown outcome', () => {
    for (const dependency of ['agent_package', 'public_origin'] as const) {
      const failure = sentenceOf(missing(dependency), true);
      expect(failure.kind, dependency).toBe('refusal');
      expect(failure.detail, dependency).toBe(DEPENDENCY_SENTENCES[dependency]);
      expect(failure.detail, dependency).toContain('тому, кто разворачивал стенд');
    }
    expect(DEPENDENCY_SENTENCES.agent_package).toContain('пакета агента');
    expect(DEPENDENCY_SENTENCES.public_origin).toContain('публичный адрес');
  });

  it('leaves the dependency the connection commands already word to their own sentence', () => {
    const failure = sentenceOf(missing('secrets_public_key_missing'));
    expect(failure.kind).toBe('refusal');
    expect(failure.detail).toContain('открытый ключ для запечатывания секретов');
  });

  it('words an unknown dependency by the catalogue, never by the server’s English message', () => {
    const failure = sentenceOf(missing('something_new'));
    expect(failure.detail).not.toContain('Safe.');
    expect(failure.detail).toMatch(/[А-Яа-я]{4}/);
  });
});

describe('the install over SSH', () => {
  it('words an install already under way, a confirmation that came too late and a fingerprint that did not match', () => {
    expect(sentenceOf(conflict('install_in_progress')).detail).toBe(CONFLICT_SENTENCES.install_in_progress);
    expect(sentenceOf(conflict('install_not_awaiting_host_key')).detail).toBe(CONFLICT_SENTENCES.install_not_awaiting_host_key);
    const changed = sentenceOf(conflict('host_key_changed'));
    expect(changed.detail).toBe(CONFLICT_SENTENCES.host_key_changed);
    expect(changed.detail).toContain('не совпал');
  });

  it('leaves an archived connection and a missing revision to the connection commands’ sentences', () => {
    expect(sentenceOf(conflict('connection_archived')).detail).toBe('Подключение в архиве, команда не выполнена.');
    expect(sentenceOf(conflict('no_revision')).detail).toContain('сначала сохраните их');
  });

  it('words every refused field of the install request (host, port, user, fingerprint, kind)', () => {
    const cases: [string, string, string][] = [
      ['ssh_host', 'format', 'Узел SSH'],
      ['ssh_port', 'range', 'Порт SSH'],
      ['ssh_user', 'format', 'Пользователь SSH'],
      ['host_key_fingerprint', 'pattern', 'Отпечаток не разобран'],
      ['kind', 'kind_not_pull', 'Клиент забирает задания'],
    ];
    for (const [field, constraint, phrase] of cases) {
      const failure = sentenceOf(invalid(field, constraint));
      expect(failure.kind, `${field}/${constraint}`).toBe('refusal');
      expect(failure.detail, `${field}/${constraint}`).toContain(phrase);
      expect(VALIDATION_SENTENCES[`${field}/${constraint}`], `${field}/${constraint}`).toBeDefined();
    }
  });

  it('has a Russian sentence for every sanitised reason an install can fail, and no two alike', () => {
    const sentences = Object.values(INSTALL_FAILURE_SENTENCES);
    expect(sentences.length).toBe(12);
    for (const sentence of sentences) expect(sentence).toMatch(/[А-Яа-я]{4}/);
    expect(new Set(sentences).size).toBe(sentences.length);
  });

  it('names what each reason asks the administrator to do', () => {
    expect(INSTALL_FAILURE_SENTENCES.ssh_refused).toContain('authorized_keys');
    expect(INSTALL_FAILURE_SENTENCES.host_key_changed).toContain('начните заново и сверьте отпечаток');
    expect(INSTALL_FAILURE_SENTENCES.host_key_not_confirmed).toContain('подтвердите отпечаток');
    expect(INSTALL_FAILURE_SENTENCES.sudo_password_required).toContain('без пароля');
    expect(INSTALL_FAILURE_SENTENCES.unsupported_platform).toContain('Ubuntu LTS');
    expect(INSTALL_FAILURE_SENTENCES.package_unavailable).toContain('тому, кто разворачивал стенд');
    expect(INSTALL_FAILURE_SENTENCES.enrollment_failed).toContain('получите новую команду');
    expect(INSTALL_FAILURE_SENTENCES.no_worker).toContain('«Процессы»');
    expect(INSTALL_FAILURE_SENTENCES.timed_out).toContain('Повторите');
  });

  it('says a LAN address is refused by the stand’s rules unless its administrator allowed it, and not merely down (R-149g)', () => {
    const sentence = INSTALL_FAILURE_SENTENCES.host_unreachable;
    expect(sentence).toContain('частных сетей');
    expect(sentence).toContain('только тогда, когда это разрешено в его настройках администратором');
    expect(sentence).toContain('отклоняется, а не просто не отвечает');
    // The service addresses and the loopback are closed whatever the setting says.
    expect(sentence).toContain('служебные адреса стенда и петлю не принимает никогда');
    expect(sentence).toContain('Если разрешения нет');
    // It no longer says that path A refuses private ranges outright.
    expect(sentence).not.toContain('установка по SSH не принимает адреса частных сетей');
    // …and it still says the other cause, and what to do in each case.
    expect(sentence).toContain('Либо сервер недоступен');
    expect(sentence).toContain('«Выполнить команду на Ubuntu»');
  });
});

describe('the states of an agent, in words', () => {
  const sentenceFor = (c: ReturnType<typeof agentCase>, id: Parameters<typeof stepSentence>[1]) =>
    stepSentence(agentLifecycle(c.connection, c.detail, NOW), id);

  it('says an offline agent is offline, when it was last seen, and what to check', () => {
    const c = agentCase({ n: 65, tokens: [agentToken(1, CID, { online: false, last_seen_at: at(10 * MINUTE) })] });
    const sentence = sentenceFor(c, 'online');
    expect(sentence).toContain('Агент не в сети');
    expect(sentence).toContain('Последнее обращение');
    expect(sentence).toContain('служба агента запущена');
  });

  it('says a missing client is missing', () => {
    const c = agentCase({ n: 65, tokens: [agentToken(1, CID, { clis: [] })] });
    expect(sentenceFor(c, 'installed')).toContain('не найден');
  });

  it('says a login is needed, and what the stand cannot tell', () => {
    const needed = agentCase({ n: 65, tokens: [agentToken(1, CID, { clis: [claude('login_required')] })] });
    expect(sentenceFor(needed, 'login')).toContain('Нужен вход');
    const unknown = agentCase({ n: 65, tokens: [agentToken(1, CID, { clis: [claude('unknown')] })] });
    expect(sentenceFor(unknown, 'login')).toContain('Состояние входа неизвестно');
  });

  it('says a model the client does not answer under is unsupported', () => {
    const c = agentCase({ n: 65, tokens: [agentToken(1, CID)], probe: { outcome: 'model_mismatch' } });
    expect(sentenceFor(c, 'probe')).toContain('Неподдерживаемая модель');
  });

  it('draws every sentence in Russian apart from named products', () => {
    const named = /^(?:SSH|Ubuntu|LTS|Claude|Code|codex|authorized_keys|OpenRouter|API|SHA)$/;
    const all = [
      ...Object.values(CONFLICT_SENTENCES), ...Object.values(DEPENDENCY_SENTENCES), ...Object.values(VALIDATION_SENTENCES),
      ...Object.values(INSTALL_FAILURE_SENTENCES), COMMAND_UNKNOWN_OUTCOME,
    ];
    for (const sentence of all) {
      const foreign = (sentence.match(/[A-Za-z_]+/g) ?? []).filter((word) => !named.test(word));
      expect(foreign, sentence).toEqual([]);
    }
  });

  it('has no sentence for a refusal it does not word: those fall to the connection commands and the catalogue', () => {
    expect(agentRefusalSentence(conflict('connection_archived'))).toBeNull();
    expect(agentRefusalSentence(invalid('pin_id', 'model_not_pinned'))).toBeNull();
    expect(agentRefusalSentence(refusal(403, 'permission_denied'))).toBeNull();
    expect(agentFailure(refusal(403, 'permission_denied'), true).kind).toBe('permission');
  });
});
