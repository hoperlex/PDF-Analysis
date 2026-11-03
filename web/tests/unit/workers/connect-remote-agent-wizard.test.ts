/**
 * `EXEC2-WEB-WIZARD-01` — the wizard: «Добавить подключение», the two equal choices, the two equal
 * ways to install, and the command that is shown once (B2 §11 test 6).
 *
 * The harness renders one static pass and fires no event, so a screen that is reached by pressing a
 * button is rendered as the view the button opens, in the state under test; the rule behind a press
 * (the box that holds the command, the reading of the install form) is a pure function called
 * directly. Written under `R-149d`: not run in EXEC-2. None of these needs a database.
 */

import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  AgentSetup,
  ConnectWizard,
  ConnectWizardLauncher,
  EMPTY_COMMAND_BOX,
  EnrollmentCommandControl,
  EnrollmentCommandView,
  INSTALL_FAILURE_SENTENCES,
  INSTALL_STATE_LABELS,
  KIND_CHOICES,
  KindChoiceView,
  PATH_CHOICES,
  PathChoiceView,
  SshInstallForm,
  SshInstallSessionView,
  commandBoxReducer,
  installSignature,
  readInstall,
} from '@/features/connect-remote-agent';
import {
  EXECUTOR_AGENT_INSTALL_FAILURE_VALUES,
  EXECUTOR_AGENT_INSTALL_STATE_VALUES,
} from '@/shared/api';

import { WEB_ROOT, readText, walkFiles } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';
import { connectionId } from './executor-fixtures';
import { FINGERPRINT, PINNED, SECRET, install, issued } from './connect-remote-agent-fixtures';

const CID = connectionId(62);
const noop = () => undefined;

function render(element: Parameters<typeof renderScreen>[1]): string {
  return renderScreen(newClient(), element);
}

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(entries)) data.set(name, value);
  return data;
}

/** The cards of one pair, with the one attribute that names them taken out, so they can be compared. */
function cardsOf(markup: string, attribute: string): string[] {
  const cards = markup.match(new RegExp(`<div[^>]*${attribute}="[a-z]+"[\\s\\S]*?</div>`, 'g')) ?? [];
  return cards.map((card) => card.replace(new RegExp(` ${attribute}="[a-z]+"`), '').replace(/>[^<]+</g, '><'));
}

describe('«Добавить подключение» is closed until it is asked for', () => {
  it('draws the button and nothing of the wizard', () => {
    const markup = render(createElement(ConnectWizardLauncher, { pinnedModels: PINNED }));
    expect(markup).toContain('Добавить подключение');
    expect(markup).toContain('data-executor-create');
    expect(markup).toContain('aria-expanded="false"');
    for (const absent of ['data-connect-wizard', 'Удалённый Ubuntu-агент', 'API-провайдер', 'data-wizard-step']) {
      expect(markup, absent).not.toContain(absent);
    }
  });
});

describe('the first screen: two equal choices', () => {
  const markup = render(createElement(ConnectWizard, { pinnedModels: PINNED }));

  it('offers «Удалённый Ubuntu-агент» and «API-провайдер», and the older form one quiet button below', () => {
    expect(markup).toContain('data-connect-wizard="kind"');
    expect(markup).toContain('data-wizard-kind="agent"');
    expect(markup).toContain('data-wizard-kind="api"');
    expect(markup).toContain('>Удалённый Ubuntu-агент<');
    expect(markup).toContain('>API-провайдер<');
    expect(KIND_CHOICES.agent.title).toBe('Удалённый Ubuntu-агент');
    expect(KIND_CHOICES.api.title).toBe('API-провайдер');
    expect(markup).toContain('data-wizard-manual');
    expect(markup).toContain('Настроить подключение вручную');
  });

  it('draws the two choices as the same panel with the same button, so neither is the main one', () => {
    const cards = cardsOf(markup, 'data-wizard-kind');
    expect(cards).toHaveLength(2);
    expect(cards[0]).toBe(cards[1]);
    expect(cards[0]).toContain('<button class="am-button" type="button">');
    expect(cards[0]).not.toContain('am-button--quiet');
  });

  it('is a view driven by props: it sends nothing and holds nothing', () => {
    const view = render(createElement(KindChoiceView, { onChoose: noop, onManual: noop }));
    expect(view).toBe(render(createElement(KindChoiceView, { onChoose: noop, onManual: noop })));
    expect(view).not.toContain('<form');
    expect(view).not.toContain('<input');
  });
});

describe('the agent screen: a name and a model, then two equal ways to install', () => {
  const markup = render(createElement(AgentSetup, { pinnedModels: PINNED, onBack: noop }));

  it('asks for the name, the pinned model and the name the client answers under — and nothing is created yet', () => {
    expect(markup).toContain('data-wizard-step="agent"');
    expect(markup).toContain('name="display_name"');
    expect(markup).toContain('name="pin_id"');
    for (const model of PINNED) expect(markup).toContain(`>${model.pin_id}</option>`);
    expect(markup).toContain('name="gateway_model"');
    expect(markup).toContain('без тарификации');
    expect(markup).not.toContain('name="ssh_host"');
    expect(markup).not.toContain('data-agent-command-shown');
  });

  it('offers «Установить по SSH» and «Выполнить команду на Ubuntu» as the same panel with the same button', () => {
    expect(PATH_CHOICES.ssh.title).toBe('Установить по SSH');
    expect(PATH_CHOICES.command.title).toBe('Выполнить команду на Ubuntu');
    expect(markup).toContain('>Установить по SSH<');
    expect(markup).toContain('>Выполнить команду на Ubuntu<');
    const cards = cardsOf(markup, 'data-agent-path');
    expect(cards).toHaveLength(2);
    expect(cards[0]).toBe(cards[1]);
    expect(markup.indexOf('data-agent-path="ssh"')).toBeLessThan(markup.indexOf('data-agent-path="command"'));
  });

  it('says the command is one-time and the SSH way takes no password, in the cards themselves', () => {
    expect(PATH_CHOICES.ssh.text).toContain('Пароли не принимаются');
    expect(PATH_CHOICES.command.text).toContain('показывается один раз');
    expect(PATH_CHOICES.command.text).toContain('15 минут');
  });

  it('refuses to start with no pinned model, and offers no path', () => {
    const empty = render(createElement(AgentSetup, { pinnedModels: [], onBack: noop }));
    expect(empty).toContain('data-agent-no-models');
    expect(empty).toContain('Список закреплённых моделей пуст');
    expect(empty).not.toContain('data-agent-path');
  });

  it('draws the path pair on its own too, for moving an agent', () => {
    const pair = render(createElement(PathChoiceView, { onChoose: noop }));
    expect(cardsOf(pair, 'data-agent-path')).toHaveLength(2);
  });
});

describe('path A: install over SSH', () => {
  const markup = render(createElement(SshInstallForm, { pending: false, problem: null, failure: null, onSubmit: noop, onBack: noop }));

  it('asks for host, port (22) and user, and for nothing else', () => {
    expect(markup).toContain('name="ssh_host"');
    expect(markup).toContain('name="ssh_port"');
    expect(markup).toMatch(/name="ssh_port"[^>]*value="22"/);
    expect(markup).toContain('name="ssh_user"');
    const names = (markup.match(/<input[^>]*>/g) ?? []).map((tag) => /name="([^"]+)"/.exec(tag)?.[1]);
    expect(names).toEqual(['ssh_host', 'ssh_port', 'ssh_user']);
  });

  it('prints the one way in, a key the stand makes, instead of offering a choice', () => {
    expect(markup).toContain('data-agent-access="generated_key"');
    expect(markup).toContain('Ключ создаст стенд');
    expect(markup).toContain('Закрытая часть остаётся на стенде');
    expect(markup).toContain('authorized_keys');
    expect(markup).not.toContain('type="radio"');
    expect(markup).not.toContain('name="access"');
  });

  it('has no password field of any kind, and says passwords are not accepted', () => {
    expect(markup).not.toContain('type="password"');
    expect(markup).not.toMatch(/name="[^"]*pass[^"]*"/i);
    expect(markup).toContain('Пароли не принимаются');
  });

  it('has no private-key input of any kind: no text area, no file field, no word offering to paste one', () => {
    expect(markup).not.toContain('<textarea');
    expect(markup).not.toContain('type="file"');
    expect(markup).not.toMatch(/private[_-]?key/i);
    expect(markup).not.toContain('Вставить закрытый ключ');
    expect(markup).not.toContain('Закрытый ключ<');
    expect(markup).toContain('Закрытые ключи и пароли в это приложение не вводятся');
  });

  it('warns that a LAN address is refused, before anyone types one', () => {
    expect(markup).toContain('data-agent-private-range-hint');
    expect(markup).toContain('частных сетей');
    expect(markup).toContain('завершится отказом');
    expect(markup).toContain('выберите путь с командой');
  });

  it('shows a problem with what was typed, and a refusal of the command, apart', () => {
    const problem = render(createElement(SshInstallForm, {
      pending: false, problem: 'Порт SSH: целое число от 1 до 65535.', failure: null, onSubmit: noop, onBack: noop,
    }));
    expect(problem).toContain('data-agent-problem');
    expect(problem).toContain('Порт SSH');
    const refused = render(createElement(SshInstallForm, {
      pending: false, problem: null, onSubmit: noop, onBack: noop,
      failure: { kind: 'conflict', detail: INSTALL_FAILURE_SENTENCES.ssh_refused, correlationId: null },
    }));
    expect(refused).toContain('data-executor-failure="conflict"');
  });

  it('disables the buttons while the command is in flight', () => {
    const busy = render(createElement(SshInstallForm, { pending: true, problem: null, failure: null, onSubmit: noop, onBack: noop }));
    expect(busy).toMatch(/<button[^>]*disabled[^>]*data-agent-ssh-submit/);
  });
});

describe('reading the install form', () => {
  const base = { ssh_host: 'host.example', ssh_port: '22', ssh_user: 'installer' };
  const GENERATED = { ssh_host: 'host.example', ssh_port: 22, ssh_user: 'installer', access: 'generated_key' };

  it('builds the request from host, port and user, always asking for the key the stand makes', () => {
    expect(readInstall(form(base))).toEqual({ ok: true, body: GENERATED });
  });

  it('sends no password and no private key it was handed, and lets no field change the access', () => {
    const handed = form({
      ...base, password: 'пароль', ssh_password: 'пароль', private_key: 'ЗАКРЫТЫЙ-КЛЮЧ', access: 'pasted_key',
    });
    const reading = readInstall(handed);
    expect(reading).toEqual({ ok: true, body: GENERATED });
    if (reading.ok) {
      const sent = JSON.stringify(reading.body);
      for (const forbidden of ['пароль', 'ЗАКРЫТЫЙ-КЛЮЧ', 'private_key', 'pasted_key']) expect(sent).not.toContain(forbidden);
    }
  });

  it('judges host, port and user by the revision form’s own patterns', () => {
    const problem = (over: Record<string, string>) => {
      const reading = readInstall(form({ ...base, ...over }));
      return reading.ok ? null : reading.problem;
    };
    expect(problem({ ssh_host: 'хост с пробелом' })).toContain('Узел SSH');
    expect(problem({ ssh_port: '70000' })).toContain('Порт SSH');
    expect(problem({ ssh_user: 'пользователь' })).toContain('Пользователь SSH');
    expect(problem({})).toBeNull();
  });

  it('makes one signature for one intent and another for another, with nothing secret in it', () => {
    const one = readInstall(form(base));
    const other = readInstall(form({ ...base, ssh_host: 'other.example' }));
    if (!one.ok || !other.ok) throw new Error('both forms read');
    expect(installSignature(CID, one.body)).toBe(installSignature(CID, one.body));
    expect(installSignature(CID, one.body)).not.toBe(installSignature(CID, other.body));
    expect(installSignature(CID, one.body)).toBe(JSON.stringify([CID, 'host.example', 22, 'installer', 'generated_key']));
  });
});

describe('path A: the session', () => {
  const view = (over: Parameters<typeof install>[1], extra: { confirming?: boolean } = {}) =>
    render(createElement(SshInstallSessionView, {
      install: install(CID, over), confirming: extra.confirming ?? false, confirmFailure: null, onConfirm: noop, onRetry: noop,
    }));

  it('names every state of the session in Russian, and has a label for exactly the states the contract has', () => {
    expect(Object.keys(INSTALL_STATE_LABELS).sort()).toEqual([...EXECUTOR_AGENT_INSTALL_STATE_VALUES].sort());
    for (const state of EXECUTOR_AGENT_INSTALL_STATE_VALUES) {
      const markup = view({ state, ...(state === 'failed' ? { failure_reason: 'install_failed' as const } : {}) });
      expect(markup, state).toContain(`data-agent-install="${state}"`);
      expect(markup, state).toContain(INSTALL_STATE_LABELS[state]);
    }
  });

  it('shows the line for authorized_keys while the stand needs the key, and not after the install ends or the key is removed', () => {
    for (const state of ['requested', 'scanning', 'awaiting_host_key', 'installing'] as const) {
      expect(view({ state }), state).toContain('data-agent-authorized-keys');
    }
    expect(view({ state: 'requested' })).toContain('строка-ключа-для-файла');
    expect(view({ state: 'succeeded' })).not.toContain('data-agent-authorized-keys');
    expect(view({ state: 'failed', failure_reason: 'ssh_refused' })).not.toContain('data-agent-authorized-keys');
    expect(view({ state: 'installing', key_removed_at: '2026-11-02T11:59:00Z' })).not.toContain('data-agent-authorized-keys');
    expect(view({ state: 'requested', access: 'pasted_key' })).not.toContain('data-agent-authorized-keys');
  });

  it('shows the access a session has, including one made over the API with a key the wizard never offers', () => {
    const generated = view({ state: 'requested' });
    expect(generated).toContain('data-agent-install-access="generated_key"');
    expect(generated).toContain('Доступ: ключ создал стенд.');
    const pasted = view({ state: 'installing', access: 'pasted_key' });
    expect(pasted).toContain('data-agent-install-access="pasted_key"');
    expect(pasted).toContain('Доступ: закрытый ключ передан через API.');
    expect(pasted).not.toContain('data-agent-authorized-keys');
  });

  it('asks the administrator to confirm the fingerprint, with the button off until it was compared', () => {
    const markup = view({ state: 'awaiting_host_key', observed_host_key_fingerprint: FINGERPRINT });
    expect(markup).toContain('data-agent-fingerprint');
    expect(markup).toContain(FINGERPRINT);
    expect(markup).toContain('Я сверил отпечаток с сервером');
    expect(markup).toMatch(/<input[^>]*type="checkbox"[^>]*data-agent-fingerprint-check/);
    expect(markup).not.toMatch(/<input[^>]*type="checkbox"[^>]*checked/);
    expect(markup).toMatch(/<button[^>]*disabled[^>]*data-agent-fingerprint-confirm/);
    expect(markup).toContain('Сравните его с отпечатком, который показывает сам сервер');
  });

  it('asks for no confirmation in any other state, and none before a fingerprint was observed', () => {
    for (const state of ['requested', 'scanning', 'installing', 'succeeded'] as const) {
      expect(view({ state, observed_host_key_fingerprint: FINGERPRINT }), state).not.toContain('data-agent-fingerprint-confirm');
    }
    const early = view({ state: 'awaiting_host_key' });
    expect(early).toContain('Отпечаток ещё не получен');
    expect(early).not.toContain('data-agent-fingerprint-confirm');
  });

  it('says whether the stand’s key was removed from the server once the install succeeded', () => {
    expect(view({ state: 'succeeded', key_removed_at: '2026-11-02T11:59:00Z' })).toContain('data-agent-key-removed="yes"');
    const kept = view({ state: 'succeeded' });
    expect(kept).toContain('data-agent-key-removed="no"');
    expect(kept).toContain('удалите его строку из authorized_keys вручную');
  });

  it('gives every failure reason its own sentence and offers to try again on the same connection', () => {
    expect(Object.keys(INSTALL_FAILURE_SENTENCES).sort()).toEqual([...EXECUTOR_AGENT_INSTALL_FAILURE_VALUES].sort());
    const seen = new Set<string>();
    for (const reason of EXECUTOR_AGENT_INSTALL_FAILURE_VALUES) {
      const markup = view({ state: 'failed', failure_reason: reason });
      expect(markup, reason).toContain(`data-agent-install-failure="${reason}"`);
      expect(markup, reason).toContain('data-agent-install-retry');
      expect(INSTALL_FAILURE_SENTENCES[reason], reason).toMatch(/[А-Яа-я]{4}/);
      seen.add(INSTALL_FAILURE_SENTENCES[reason]);
    }
    expect(seen.size).toBe(EXECUTOR_AGENT_INSTALL_FAILURE_VALUES.length);
  });

  it('says a refused LAN address is refused and not merely down, and points at the path that works', () => {
    const sentence = INSTALL_FAILURE_SENTENCES.host_unreachable;
    expect(sentence).toContain('адреса частных сетей');
    expect(sentence).toContain('отклоняется, а не просто не отвечает');
    expect(sentence).toContain('Выполнить команду на Ubuntu');
    expect(sentence).toContain('сервер недоступен');
    expect(view({ state: 'failed', failure_reason: 'host_unreachable' })).toContain('частных сетей');
  });

  it('shows the progress of the agent’s registration under a finished install, and only then', () => {
    const withChild = render(createElement(SshInstallSessionView, {
      install: install(CID, { state: 'succeeded' }), confirming: false, confirmFailure: null, onConfirm: noop, onRetry: noop,
    }, createElement('p', null, 'ход регистрации')));
    expect(withChild).toContain('ход регистрации');
    const failed = render(createElement(SshInstallSessionView, {
      install: install(CID, { state: 'failed', failure_reason: 'timed_out' }), confirming: false, confirmFailure: null,
      onConfirm: noop, onRetry: noop,
    }, createElement('p', null, 'ход регистрации')));
    expect(failed).not.toContain('ход регистрации');
  });
});

describe('path B: the command is shown once', () => {
  it('shows the command in a box that can be copied, once, with when it stops working', () => {
    const grant = issued(CID);
    const markup = render(createElement(EnrollmentCommandView, {
      issued: grant, replaced: false, pending: false, failure: null, onNewCommand: noop, onClose: noop,
    }));
    expect(markup).toContain('data-agent-command-shown');
    expect(markup).toContain('data-agent-copy="enrollment-command"');
    expect(markup).toContain('data-agent-copy-button="enrollment-command"');
    expect(markup).toContain(grant.command);
    expect(markup.split(SECRET).length - 1).toBe(1);
    expect(markup).toContain('Команда показана один раз и больше показана не будет');
    expect(markup).toContain('после закрытия этого окна увидеть её снова нельзя');
    expect(markup).toContain(grant.enrollment.expires_at);
    expect(markup).toMatch(/<time[^>]*date[Tt]ime=/);
    expect(markup).toContain('1.2.3');
    expect(markup).toContain(grant.package_sha256);
    expect(markup).toContain('Новая команда');
    expect(markup).toContain('Я скопировал команду, закрыть');
  });

  it('says a new command cancels the old one, and says so on the box that replaced it', () => {
    const first = render(createElement(EnrollmentCommandView, {
      issued: issued(CID), replaced: false, pending: false, failure: null, onNewCommand: noop, onClose: noop,
    }));
    expect(first).toContain('Новая команда отменяет прежнюю');
    expect(first).toContain('data-agent-command-replaced="no"');
    expect(first).not.toContain('data-agent-command-new-note');
    const second = render(createElement(EnrollmentCommandView, {
      issued: issued(CID), replaced: true, pending: false, failure: null, onNewCommand: noop, onClose: noop,
    }));
    expect(second).toContain('data-agent-command-replaced="yes"');
    expect(second).toContain('Прежняя команда больше не действует');
  });

  it('never prints the secret anywhere but inside the command, and sends it through the environment', () => {
    const markup = render(createElement(EnrollmentCommandView, {
      issued: issued(CID), replaced: false, pending: false, failure: null, onNewCommand: noop, onClose: noop,
    }));
    expect(markup.split(SECRET).length - 1).toBe(1);
    expect(markup).toContain('через переменную окружения, а не через аргументы команды');
  });

  it('shows no command before one is asked for: the button, and nothing to copy', () => {
    const markup = render(createElement(EnrollmentCommandControl, {
      resolveConnection: async () => CID, startLabel: 'Получить команду',
    }));
    expect(markup).toContain('data-agent-command-start');
    expect(markup).toContain('Получить команду');
    expect(markup).not.toContain('data-agent-command-shown');
    expect(markup).not.toContain('<textarea');
  });

  it('holds a command in one box that a new one replaces and a close empties, leaving no trace of either', () => {
    const one = issued(CID, { secret: 'ПЕРВЫЙ-СЕКРЕТ', command: 'команда ПЕРВЫЙ-СЕКРЕТ' });
    const two = issued(CID, { secret: 'ВТОРОЙ-СЕКРЕТ', command: 'команда ВТОРОЙ-СЕКРЕТ' });

    const shown = commandBoxReducer(EMPTY_COMMAND_BOX, { type: 'issued', issued: one });
    expect(shown).toMatchObject({ replaced: false, everShown: true });
    expect(shown.issued?.command).toBe(one.command);

    const replaced = commandBoxReducer(shown, { type: 'issued', issued: two });
    expect(replaced.replaced).toBe(true);
    expect(replaced.issued?.command).toBe(two.command);
    expect(JSON.stringify(replaced)).not.toContain('ПЕРВЫЙ-СЕКРЕТ');

    const closed = commandBoxReducer(replaced, { type: 'closed' });
    expect(closed).toEqual({ issued: null, replaced: false, everShown: true });
    expect(JSON.stringify(closed)).not.toContain('СЕКРЕТ');
    expect(JSON.stringify(closed)).not.toContain('команда');

    // A command after a close is a first one again: nothing is replaced, because nothing is shown.
    const again = commandBoxReducer(closed, { type: 'issued', issued: one });
    expect(again.replaced).toBe(false);
  });

  it('starts empty, and a fresh box has shown nothing', () => {
    expect(EMPTY_COMMAND_BOX).toEqual({ issued: null, replaced: false, everShown: false });
  });
});

describe('a secret is not kept: no storage, no address, no log, no key-setting call in the slice', () => {
  const SLICES = [
    join(WEB_ROOT, 'src', 'features', 'connect-remote-agent'),
  ];
  const files = SLICES.flatMap((root) => walkFiles(root, (path) => /\.(ts|tsx)$/.test(path)));

  it('reads a non-trivial number of files, so a broken walk cannot pass vacuously', () => {
    expect(files.length).toBeGreaterThan(15);
  });

  it('touches no browser storage, writes no log and builds no address out of a command or a key', () => {
    for (const path of files) {
      const code = readText(path).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      for (const forbidden of ['localStorage', 'sessionStorage', 'document.cookie', 'indexedDB', 'console.', 'history.pushState', 'location.href', 'location.search']) {
        expect(code.includes(forbidden), `${path} uses ${forbidden}`).toBe(false);
      }
    }
  });

  it('names no private-key field and builds no request carrying one, in the slice or in the install command', () => {
    const hook = join(WEB_ROOT, 'src', 'features', 'manage-executor-connection', 'model', 'use-manage-executor-connection.ts');
    for (const path of [...files, hook]) {
      const code = readText(path).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      expect(/private_key|privateKey|BEGIN [A-Z ]*PRIVATE KEY/.test(code), path).toBe(false);
    }
  });

  it('never calls setExecutorSecret: a key is typed into the server-rendered form and nowhere else', () => {
    for (const path of files) {
      const code = readText(path).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      expect(/\bsetExecutorSecret\b/.test(code), path).toBe(false);
    }
  });
});
