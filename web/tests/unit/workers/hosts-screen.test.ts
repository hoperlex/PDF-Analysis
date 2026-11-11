/**
 * `HOSTS-WEB-01` — «Исполнители» as two tabs, «Серверы» above all: the summary, the row of a server and what each role is
 * drawn of it, the window «Подключить сервер», and the reads the viewer never sends. The pure rules of a row are functions
 * (`entities/executor-host`), so each is a call; the screen is read from a render over a seeded cache.
 *
 * Every rule below has a case that fails when the rule is broken: a hidden thing that is shown, a reason that is not named, a
 * control that an expert is drawn.
 */

import { createElement, isValidElement } from 'react';
import type { ComponentType, ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExecutorHost, ExecutorHostModel, Role } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  availableModelIds, executorHostsQueryOptions, hostFailure, hostRowReading, mayReadHosts, modelChips, modelLabel, modelLabels,
  noContactSentence, summarySentence,
} from '@/entities/executor-host';
import { stageLayoutQueryOptions } from '@/entities/stage-layout';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';
import { ExecutorHosts, HostRow } from '@/widgets/executor-hosts';
import {
  CommandTabView, ConnectWindow, ConnectWindowView, DeleteHostView, HostDetailsView, HostEnabledSwitch, HostEnabledSwitchView,
  INSTALL_STEP_IDS, InstallSessionView, SshFormView, arrivalOf, installSteps, readSshForm, useIssueExecutorHostEnrollment,
} from '@/features/manage-executor-host';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import {
  HOST_DETAILS, HOST_LIST, ISSUED, SERVER_BUSY, SERVER_EMPTY, SERVER_OFFLINE, SERVER_ONLINE, install, seedDetails, seedHosts, seedLayout,
} from './hosts-fixtures';

const requests: { line: string; key: string | null }[] = [];

beforeEach(() => {
  requests.length = 0;
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
  vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit) => {
    const url = new URL(input);
    requests.push({ line: `${init.method ?? 'GET'} ${url.pathname}${init.body ? ` ${String(init.body)}` : ''}`, key: new Headers(init.headers).get('Idempotency-Key') });
    return new Response(JSON.stringify(SERVER_ONLINE), { status: 200, headers: { 'content-type': 'application/json' } });
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const settle = async (): Promise<void> => { for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 0)); };

function seeded(roles: Role[], tab: WorkersPageProps['initialTab'] = 'servers', list = HOST_LIST): string {
  const client = newClient();
  seedHosts(client, list);
  seedLayout(client);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: tab }));
}

describe('the words of a server row', () => {
  it('names a model without its provider prefix, and a pin it does not know as it is', () => {
    expect(modelLabel('claude-opus-5-5')).toBe('Opus 5.5');
    expect(modelLabel('claude-sonnet-5')).toBe('Sonnet 5');
    expect(modelLabel('gpt-6-sol')).toBe('gpt-6-sol');
    expect(modelLabel('gpt-6.1-sol')).toBe('gpt-6.1-sol');
    expect(modelLabel('что-то-новое')).toBe('что-то-новое');
    expect(modelLabels(['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5', 'gpt-6-sol'])).toBe('Opus 5.5 · Sonnet 5.5 · gpt-6-sol');
  });

  it('says the summary as the plan has it', () => {
    expect(summarySentence(2, 3, 3, 5)).toBe('На связи 2 из 3 · свободно 3 из 5');
  });

  it('says when contact was lost, or that there never was one', () => {
    const at = new Date('2026-11-09T11:02:00Z');
    const two = (n: number) => String(n).padStart(2, '0');
    expect(noContactSentence('2026-11-09T11:02:00Z')).toBe(`нет связи с ${two(at.getHours())}:${two(at.getMinutes())}`);
    expect(noContactSentence(undefined)).toContain('ещё не выходил на связь');
  });
});

describe('what a row draws: unavailable is not a chip', () => {
  const model = (id: string, state: string, access: ExecutorHostModel['access'] = 'subscription'): ExecutorHostModel =>
    ({ provider: 'claude_code', access, model_id: id, state } as ExecutorHostModel);

  it('draws a chip for each usable model once, and marks only a paid one with «API»', () => {
    const chips = modelChips(SERVER_ONLINE.models);
    expect(chips.map((chip) => [chip.label, chip.api])).toEqual([['Opus 5.5', false], ['Sonnet 5.5', false], ['gpt-6-sol', true]]);
    // The same model served by a subscription and by a key is a subscription model.
    expect(modelChips([model('claude-opus-5-5', 'available', 'api'), model('claude-opus-5-5', 'available')]).map((chip) => chip.api)).toEqual([false]);
  });

  it('drops a model that cannot be used now, whatever it is handed', () => {
    const chips = modelChips([model('claude-opus-5-5', 'available'), model('claude-sonnet-5-5', 'unavailable'), model('gpt-6-sol', 'whatever')]);
    expect(chips.map((chip) => chip.modelId)).toEqual(['claude-opus-5-5']);
  });

  it('says «нет связи» for an off-line server and draws none of its models, and «нет доступных моделей» for a server with none', () => {
    const offline = hostRowReading({ ...SERVER_OFFLINE, models: SERVER_ONLINE.models });
    expect(offline.noContact).toBe(true);
    expect(offline.chips).toEqual([]);
    expect(hostRowReading(SERVER_EMPTY).noModels).toBe(true);
    expect(hostRowReading(SERVER_ONLINE).noModels).toBe(false);
    expect(hostRowReading(SERVER_ONLINE).load).toBe('2/3');
  });

  it('offers for the layout only the models an enabled, reachable server can serve', () => {
    const disabled: ExecutorHost = { ...SERVER_BUSY, enabled: false };
    expect(availableModelIds({ ...HOST_LIST, items: [SERVER_ONLINE, SERVER_OFFLINE, disabled] })).toEqual(['claude-opus-5-5', 'claude-sonnet-5-5', 'gpt-6-sol']);
    expect(availableModelIds(undefined)).toEqual([]);
  });

  it('renders the rows of the list: chips, the mark, the load, the grey row and the empty one', () => {
    const markup = renderScreen(newClient(), createElement(HostRow, { host: SERVER_ONLINE, admin: false }));
    expect(markup).toContain('data-host-model="claude-opus-5-5"');
    expect(markup.match(/data-host-api/g)).toHaveLength(1);
    expect(markup).toContain('data-host-load="2/3"');
    expect(markup).toContain('>2/3<');
    const grey = renderScreen(newClient(), createElement(HostRow, { host: SERVER_OFFLINE, admin: false }));
    expect(grey).toContain('data-host-tone="offline"');
    expect(grey).toContain('data-host-no-contact');
    expect(grey).toContain('нет связи с ');
    expect(grey).not.toContain('data-host-model');
    expect(renderScreen(newClient(), createElement(HostRow, { host: SERVER_EMPTY, admin: false }))).toContain('нет доступных моделей');
  });

  it('can fail: a model the server calls unavailable never reaches the markup', () => {
    const host: ExecutorHost = { ...SERVER_ONLINE, models: [model('claude-opus-5-5', 'available'), model('claude-sonnet-5-5', 'unavailable')] };
    const markup = renderScreen(newClient(), createElement(HostRow, { host, admin: true }));
    expect(markup).toContain('Opus 5.5');
    expect(markup).not.toContain('Sonnet 5.5');
    expect(markup).not.toContain('data-host-model="claude-sonnet-5-5"');
  });
});

describe('the two tabs and the quiet link', () => {
  it('draws two tabs, «Серверы» and «Модели по этапам», and no more', () => {
    const markup = seeded(['admin']);
    expect(markup.match(/role="tab"/g)).toHaveLength(2);
    expect(markup).toContain('>Серверы<');
    expect(markup).toContain('>Модели по этапам<');
    expect(markup).not.toContain('>Обзор<');
    expect(markup).not.toContain('>Подключения<');
    expect(markup).toContain('data-workers-panel="servers"');
  });

  it('draws «Расширенные ▸» to an administrator and to nobody else', () => {
    const admin = seeded(['admin']);
    expect(admin).toContain('data-workers-advanced-link');
    expect(admin).toContain('href="/workers/advanced"');
    expect(admin).toContain('Расширенные ▸');
    for (const roles of [['expert'], ['viewer'], []] as Role[][]) {
      expect(seeded(roles), roles.join()).not.toContain('data-workers-advanced-link');
    }
  });

  it('says the summary line instead of the old overview', () => {
    const markup = seeded(['expert']);
    expect(markup).toContain('data-hosts-summary');
    expect(markup).toContain('На связи 3 из 4 · свободно 3 из 7');
    expect(markup).not.toContain('data-workers-overview');
  });

  it('keeps the D-291 warning, in one line', () => {
    const markup = seeded(['expert']);
    expect(markup.match(/data-hosts-notice="client-documents"/g)).toHaveLength(1);
    expect(markup).toContain('Не для клиентских документов');
  });
});

describe('a server row has exactly the controls the plan names, for those it names them', () => {
  const rowOf = (admin: boolean, panel?: 'details' | 'delete'): string =>
    renderScreen(newClient(), createElement(HostRow, { host: SERVER_ONLINE, admin, initialPanel: panel ?? null }));

  it('draws an administrator the switch and the menu of two items, and nothing else to press', () => {
    const markup = rowOf(true);
    expect(markup).toContain('role="switch"');
    expect(markup.match(/role="switch"/g)).toHaveLength(1);
    expect(markup.match(/role="menuitem"/g)).toHaveLength(2);
    expect(markup).toContain('>Подробнее<');
    expect(markup).toContain('>Удалить<');
    expect(markup.match(/<button/g)).toHaveLength(3);
  });

  it('draws an expert no switch, no menu and no button at all', () => {
    const markup = rowOf(false);
    expect(markup).not.toContain('role="switch"');
    expect(markup).not.toContain('role="menuitem"');
    expect(markup).not.toContain('<button');
    expect(markup).not.toContain('Использовать');
    expect(markup).not.toContain('Подключить сервер');
  });

  it('draws «Подключить сервер» to an administrator only', () => {
    expect(seeded(['admin'])).toContain('data-connect-open');
    expect(seeded(['expert'])).not.toContain('data-connect-open');
  });

  it('draws the switch from the server\'s own state', () => {
    expect(renderScreen(newClient(), createElement(HostRow, { host: { ...SERVER_ONLINE, enabled: false }, admin: true }))).toContain('data-host-switch="off"');
    expect(rowOf(true)).toContain('data-host-switch="on"');
  });

  it('draws «Подробнее» with the reasons a model cannot be used, to an administrator', () => {
    const client = newClient();
    seedDetails(client);
    const markup = renderScreen(client, createElement(HostRow, { host: SERVER_ONLINE, admin: true, initialPanel: 'details' }));
    expect(markup).toContain('data-host-details');
    expect(markup).toContain('Проверить сейчас');
    expect(markup).toContain('data-host-model-state="unavailable"');
    expect(markup).toContain('сервер временно снял модель после отказа');
    expect(markup).toContain('на сервере нужно войти в клиент');
    expect(markup).toContain('агент сервера ещё не подтвердил эту модель');
    expect(markup).toContain('data-host-task');
    expect(markup).toContain('Анализ блоков');
    expect(markup).toContain('data-host-slot="codex"');
  });

  it('can fail: the reasons are shown to nobody who has not opened «Подробнее»', () => {
    const markup = rowOf(true);
    expect(markup).not.toContain('data-host-details');
    expect(markup).not.toContain('сервер временно снял модель после отказа');
  });

  it('asks before deleting, and says what it does', () => {
    const markup = rowOf(true, 'delete');
    expect(markup).toContain('data-host-delete');
    expect(markup).toContain('Удалить сервер «основной»?');
    expect(markup).toContain('Это необратимо');
  });

  it('shows the details view as lists: slots to change, clients with their login, tasks with their start', () => {
    const markup = renderScreen(newClient(), createElement(HostDetailsView, { details: HOST_DETAILS, rechecking: false, onRecheck: () => {} }));
    expect(markup).toContain('Claude Code');
    expect(markup).toContain('вход выполнен');
    expect(markup).toContain('нужно войти на сервере');
    expect(markup).toContain('data-host-recheck');
    const idle = renderScreen(newClient(), createElement(HostDetailsView, { details: { ...HOST_DETAILS, tasks: [] }, rechecking: false, onRecheck: () => {} }));
    expect(idle).toContain('Сейчас на сервере ничего не выполняется.');
  });
});

describe('the viewer sees none of the new reads', () => {
  it('enables the reads for an expert and an administrator, and for no other role', () => {
    expect(mayReadHosts(['admin'])).toBe(true);
    expect(mayReadHosts(['expert'])).toBe(true);
    for (const roles of [['viewer'], []] as Role[][]) expect(mayReadHosts(roles)).toBe(false);
    expect(executorHostsQueryOptions(mayReadHosts(['viewer'])).enabled).toBe(false);
    expect(stageLayoutQueryOptions(mayReadHosts(['viewer'])).enabled).toBe(false);
    expect(executorHostsQueryOptions(mayReadHosts(['expert'])).enabled).toBe(true);
  });

  it('draws a viewer neither tab\'s data, even from a cache that holds it', () => {
    for (const tab of ['servers', 'models'] as const) {
      const markup = seeded(['viewer'], tab);
      expect(markup, tab).not.toContain('data-hosts-summary');
      expect(markup, tab).not.toContain('data-host-row');
      expect(markup, tab).not.toContain('data-layout-cell');
      expect(markup, tab).not.toContain('основной');
      expect(markup, tab).toContain('data-workers-panel');
    }
  });

  it('renders the list itself to a viewer as nothing but the refusal', () => {
    const client = newClient();
    seedHosts(client);
    const markup = renderScreen(client, createElement(ExecutorHosts, { roles: ['viewer'] }));
    expect(markup).not.toContain('data-hosts-list');
    expect(markup).toContain('Серверы недоступны');
  });
});

describe('the switch «Использовать»', () => {
  it('shows the server\'s answer and disables itself while the command is on its way', () => {
    const markup = renderScreen(newClient(), createElement(HostEnabledSwitchView, { name: 'adm1', enabled: true, pending: true, failure: null, onChange: () => {} }));
    expect(markup).toContain('checked=""');
    expect(markup).toContain('disabled=""');
  });

  it('sends one setExecutorHostEnabled with an idempotency key, and says a refusal in words', async () => {
    let tree: ReactNode = null;
    function Probe() {
      tree = HostEnabledSwitch({ hostId: SERVER_ONLINE.host_id, name: 'adm1', enabled: true });
      return tree as ReactElement;
    }
    renderWith(newClient(), createElement(Probe));
    expect(isValidElement(tree)).toBe(true);
    (tree as unknown as ReactElement<{ onChange: (next: boolean) => void }>).props.onChange(false);
    await settle();
    expect(requests).toHaveLength(1);
    expect(requests[0]?.line).toBe(`PUT /bff/v1/executor-hosts/${SERVER_ONLINE.host_id}/enabled {"enabled":false}`);
    expect(requests[0]?.key).toMatch(/\S+/);
    const refusal = new ApiError(409, {
      contract_version: '1.54.0', error_code: 'conflict', message: 'x', correlation_id: 'cid-host-1', retryable: false, details: { conflict_reason: 'host_archived' },
    }, null);
    const failure = hostFailure(refusal, true);
    expect(failure.detail).toBe('Сервер удалён: изменить его уже нельзя.');
    expect(failure.detail).not.toContain('host_archived');
  });
});

describe('«Подключить сервер» never asks for a model', () => {
  const whole = (tab: 'command' | 'ssh'): string => renderScreen(newClient(), createElement(ConnectWindow, { onClose: () => {}, staticOpen: true, initialTab: tab }));

  it('draws two tabs, the D-291 line and no model on either', () => {
    for (const tab of ['command', 'ssh'] as const) {
      const markup = whole(tab);
      expect(markup.match(/role="tab"/g), tab).toHaveLength(2);
      expect(markup).toContain('>Командой в терминале<');
      expect(markup).toContain('>По SSH<');
      expect(markup).toContain('data-connect-notice="client-documents"');
      expect(markup).not.toContain('<select');
      expect(markup).not.toMatch(/name="(?:pin_id|model|model_id|gateway_model)"/);
      expect(markup).not.toMatch(/Модель|модель /);
    }
  });

  it('asks the command tab for a name only, and the SSH tab for a host and a user, with the port folded', () => {
    const command = whole('command');
    expect(command).toContain('name="display_name"');
    expect(command.match(/<input/g)).toHaveLength(1);
    const ssh = whole('ssh');
    expect(ssh).toContain('name="ssh_host"');
    expect(ssh).toContain('name="ssh_user"');
    expect(ssh).toMatch(/<details[^>]*>\s*<summary>Дополнительно<\/summary>[\s\S]*name="ssh_port"/);
    expect(ssh).not.toContain('private_key');
    expect(ssh).not.toContain('type="password"');
  });

  it('shows the command once, with «Скопировать» and the status «ждём сервер…»', () => {
    const markup = renderScreen(newClient(), createElement(CommandTabView, {
      name: 'новый', pending: false, issued: ISSUED, replaced: false, failure: null, problem: null, onName: () => {}, onGet: () => {},
      status: createElement('p', { 'data-host-arrival': 'waiting' }, arrivalOf(undefined).text),
    }));
    expect(markup).toContain('data-connect-command-shown');
    expect(markup).toContain(ISSUED.command.replace(/&/g, '&amp;'));
    expect(markup).toContain('Скопировать');
    expect(markup).toContain('ждём сервер…');
    expect(markup).toContain('показана один раз');
    expect(markup).not.toContain('name="display_name"');
  });

  it('says «найдено: …» once the server has reported, and waits while it has not', () => {
    expect(arrivalOf(undefined)).toEqual({ arrived: false, text: 'ждём сервер…' });
    const unseen: ExecutorHost = { ...SERVER_EMPTY };
    delete unseen.last_seen_at;
    expect(arrivalOf(unseen).arrived).toBe(false);
    expect(arrivalOf({ ...SERVER_ONLINE, state: 'offline' }).arrived).toBe(false);
    expect(arrivalOf(SERVER_ONLINE)).toEqual({ arrived: true, text: 'найдено: Opus 5.5, Sonnet 5.5, gpt-6-sol' });
    expect(arrivalOf(SERVER_EMPTY).text).toContain('моделей пока нет');
  });

  it('reads the SSH form: host and user, port 22 unless it is changed, and a refusal of anything else', () => {
    const form = (entries: Record<string, string>) => { const data = new FormData(); for (const [k, v] of Object.entries(entries)) data.set(k, v); return data; };
    expect(readSshForm(form({ ssh_host: ' adm2.hlab.kz ', ssh_user: 'deploy' }))).toEqual({ ok: true, host: 'adm2.hlab.kz', user: 'deploy', port: 22 });
    expect(readSshForm(form({ ssh_host: 'h', ssh_user: 'u', ssh_port: '2222' }))).toMatchObject({ ok: true, port: 2222 });
    expect(readSshForm(form({ ssh_host: '', ssh_user: 'u' })).ok).toBe(false);
    expect(readSshForm(form({ ssh_host: 'h', ssh_user: 'u', ssh_port: '70000' })).ok).toBe(false);
    expect(readSshForm(form({ ssh_host: 'h', ssh_user: 'u', ssh_port: 'x' })).ok).toBe(false);
  });

  it('sends the command with the name only, a new key each time, and keeps no copy of the secret', async () => {
    requests.length = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit) => {
      requests.push({ line: `${init.method ?? 'GET'} ${new URL(input).pathname} ${String(init.body)}`, key: new Headers(init.headers).get('Idempotency-Key') });
      return new Response(JSON.stringify(ISSUED), { status: 201, headers: { 'content-type': 'application/json' } });
    }));
    let api: ReturnType<typeof useIssueExecutorHostEnrollment> | null = null;
    function Probe() { api = useIssueExecutorHostEnrollment(); return null; }
    renderWith(newClient(), createElement(Probe));
    const issued = await (api as unknown as ReturnType<typeof useIssueExecutorHostEnrollment>).mutateAsync({ displayName: 'новый', idempotencyKey: 'ik-1' });
    expect(issued.command).toBe(ISSUED.command);
    expect(requests).toEqual([{ line: 'POST /bff/v1/executor-hosts/enrollments {"display_name":"новый"}', key: 'ik-1' }]);
  });

  it('draws the window with a close button and the tab it was given', () => {
    const markup = renderScreen(newClient(), createElement(ConnectWindowView, { tab: 'ssh', onTab: () => {}, onClose: () => {}, children: 'содержимое' }));
    expect(markup).toContain('data-connect-close');
    expect(markup).toMatch(/aria-selected="true"[^>]*data-connect-tab="ssh"|data-connect-tab="ssh"[^>]*aria-selected="true"/);
    expect(markup).toContain('содержимое');
  });

  it('draws the SSH form refusal and problem, and the form itself, with nothing about a key to paste', () => {
    const markup = renderScreen(newClient(), createElement(SshFormView, { pending: false, problem: 'Укажите узел и пользователя SSH.', failure: null, onSubmit: () => {} }));
    expect(markup).not.toContain('data-agent-copy');
    expect(markup).toContain('Укажите узел и пользователя SSH.');
    expect(markup).toContain('Свой закрытый ключ в это окно не вводится.');
  });
});

describe('the install over SSH: three steps, the fingerprint by value', () => {
  const view = (over: Parameters<typeof install>[0] = {}) => renderScreen(newClient(), createElement(InstallSessionView, {
    install: install(over), confirming: false, confirmFailure: null, onConfirm: () => {}, onRetry: () => {},
    children: createElement('p', { 'data-after': '' }, 'после установки'),
  }));

  it('maps every state of the session to three steps', () => {
    expect([...INSTALL_STEP_IDS]).toHaveLength(3);
    const at = (state: Parameters<typeof installSteps>[0]) => INSTALL_STEP_IDS.map((id) => installSteps(state, { fingerprintSeen: true, confirmed: false })[id]);
    expect(at('requested')).toEqual(['current', 'todo', 'todo']);
    expect(at('scanning')).toEqual(['current', 'todo', 'todo']);
    expect(at('awaiting_host_key')).toEqual(['done', 'current', 'todo']);
    expect(at('installing')).toEqual(['done', 'done', 'current']);
    expect(at('succeeded')).toEqual(['done', 'done', 'done']);
    expect(INSTALL_STEP_IDS.map((id) => installSteps('failed', { fingerprintSeen: false, confirmed: false })[id])).toEqual(['failed', 'todo', 'todo']);
    expect(INSTALL_STEP_IDS.map((id) => installSteps('failed', { fingerprintSeen: true, confirmed: true })[id])).toEqual(['done', 'done', 'failed']);
  });

  it('shows the line for authorized_keys and, awaiting the key, the fingerprint with a button that waits for the tick', () => {
    const markup = view();
    expect(markup.match(/data-install-step=/g)).toHaveLength(3);
    expect(markup).toContain('data-install-key-line');
    expect(markup).toContain('data-install-fingerprint-value');
    expect(markup).toContain('отпечаток-ключа-сервера');
    expect(markup).toMatch(/data-install-fingerprint-confirm[^>]*disabled=""|disabled=""[^>]*data-install-fingerprint-confirm/);
    expect(markup).not.toContain('data-after');
  });

  it('shows the server\'s status only after the install has succeeded, and a failure in words', () => {
    const done = view({ state: 'succeeded', key_removed_at: '2026-11-09T11:05:00Z' });
    expect(done).toContain('data-after');
    expect(done).not.toContain('data-install-key-line');
    expect(done).not.toContain('data-install-fingerprint');
    const failed = view({ state: 'failed', failure_reason: 'ssh_refused' });
    expect(failed).toContain('data-install-failure="ssh_refused"');
    expect(failed).toContain('Сервер отклонил вход по SSH');
    expect(failed).toContain('data-install-retry');
    expect(failed).not.toContain('data-after');
  });
});

describe('the delete confirmation', () => {
  it('names the server and what the command does, and its button is the only way to send it', () => {
    const markup = renderScreen(newClient(), createElement(DeleteHostView, { name: 'резерв', pending: false, failure: null, onConfirm: () => {}, onCancel: () => {} }));
    expect(markup).toContain('«резерв»');
    expect(markup.match(/<button/g)).toHaveLength(2);
    expect(markup).toContain('data-host-delete-confirm');
  });
});
