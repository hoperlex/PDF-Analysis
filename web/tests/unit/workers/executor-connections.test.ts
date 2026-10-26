/**
 * `EXEC-HTTP-01` — the «Подключения» and «Назначения» tabs of «Исполнители», as a person reads
 * them: what an administrator is shown and an expert is not, the sentence for every probe
 * outcome, the key as a fact and never a value, the notice of recent changes, and which
 * connections a route may name.
 *
 * Rendered, not read from source: the static render keeps every `useState` at its start, so
 * what is asserted here is the screen before anything is pressed.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutorProbeOutcome, ExecutorRoute, Role } from '@/shared/api';
import { EXECUTOR_PROBE_OUTCOME_VALUES, ApiError, queryKeys } from '@/shared/api';
import {
  PROBE_OUTCOME_SENTENCES,
  ROUTE_BLOCKER_SENTENCES,
  CHANGE_WINDOW_DAYS,
  connectionFailure,
  probeOutcomeSentence,
  recentChanges,
  kindIsServed,
  routeBlocker,
  requiredPurposes,
  secretOfPurpose,
} from '@/entities/executor-connection';
import { canExecute } from '@/entities/execution';
import { ExecutorConnections } from '@/widgets/executor-connections';
import type { ExecutorConnectionsProps } from '@/widgets/executor-connections';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';

import { newClient, renderScreen } from '../screens/harness';
import {
  ADMIN_UID, ALL_CASES, OUTCOME_CASES, READY, ROUTE, SPARE, ago, executorCase, seedExecutors,
} from './executor-fixtures';

const ENVELOPE = (code: 'validation_failed' | 'conflict' | 'dependency_unavailable', details: Record<string, string>) => ({
  contract_version: '1.7.0', error_code: code, message: 'Safe.', correlation_id: 'cid-executor-1', retryable: false, details,
}) as const;

function connections(roles: Role[], cases = ALL_CASES, extra: Partial<ExecutorConnectionsProps> = {}): string {
  const client = newClient();
  seedExecutors(client, cases);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(ExecutorConnections, { roles, ...extra }));
}

function routes(roles: Role[], cases = ALL_CASES): string {
  const client = newClient();
  seedExecutors(client, cases);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(ExecutorRoutes, { roles }));
}

describe('who is shown the controls', () => {
  it('gives the administrator the commands and the expert the list alone', () => {
    expect(canExecute(['admin'], 'connections')).toBe(true);
    expect(canExecute(['expert'], 'connections')).toBe(false);
    expect(canExecute([], 'connections')).toBe(false);
    const admin = connections(['admin']);
    for (const text of ['Добавить подключение', '>Изменить настройки<', '>Проверить<', '>Архивировать<', 'Заменить ключ']) {
      expect(admin).toContain(text);
    }
    const expert = connections(['expert']);
    expect(expert).toContain(READY.connection.display_name);
    for (const text of ['Добавить подключение', 'Изменить настройки', '>Проверить<', 'Архивировать', 'ключ</a>', 'data-executor-create']) {
      expect(expert, text).not.toContain(text);
    }
  });

  it('draws no command before the roles are read, as the worker list does', () => {
    const none = connections([]);
    expect(none).toContain(READY.connection.display_name);
    expect(none).not.toContain('>Проверить<');
  });

  it('lets only an administrator edit a route', () => {
    expect(routes(['admin'])).toContain('data-executor-route-form="text_analysis"');
    const expert = routes(['expert']);
    expect(expert).not.toContain('data-executor-route-form');
    expect(expert).toContain('data-executor-routes-readonly');
    expect(expert).toContain(READY.connection.display_name);
  });
});

describe('what a card says without ever holding the key', () => {
  it('names every probe outcome in Russian, with the outcome beside it as data', () => {
    const markup = connections(['admin']);
    for (const [outcome, one] of OUTCOME_CASES) {
      expect(markup, outcome).toContain(`data-executor-probe-outcome="${outcome}"`);
      expect(markup).toContain(probeOutcomeSentence(outcome));
      expect(one.connection.display_name.length).toBeGreaterThan(0);
    }
    // The owner's own words for the common ones.
    for (const sentence of ['готово', 'IP стенда не допущен', 'ключ отклонён', 'отвечает другая модель', 'нет ответа', 'адрес недоступен', 'ключ нужно ввести заново']) {
      expect(markup, sentence).toContain(sentence);
    }
  });

  it('has a sentence for every outcome the contract has, and none the contract lacks', () => {
    expect(Object.keys(PROBE_OUTCOME_SENTENCES).sort()).toEqual([...EXECUTOR_PROBE_OUTCOME_VALUES].sort());
    expect(new Set(Object.values(PROBE_OUTCOME_SENTENCES)).size).toBe(EXECUTOR_PROBE_OUTCOME_VALUES.length);
    for (const outcome of EXECUTOR_PROBE_OUTCOME_VALUES as readonly ExecutorProbeOutcome[]) {
      expect(PROBE_OUTCOME_SENTENCES[outcome]).toMatch(/[А-Яа-я]{3}/);
    }
  });

  it('shows the key as its last four characters, when and by whom, and never anything more', () => {
    const markup = connections(['admin'], [READY]);
    expect(markup).toContain('…4417');
    expect(markup).toContain(ADMIN_UID);
    expect(markup).toContain('data-executor-secret="api_key"');
    expect(markup).not.toMatch(/type="password"/);
    expect(markup).not.toContain('<textarea');
  });

  it('says a key entered for another address must be entered again', () => {
    const markup = connections(['admin'], [OUTCOME_CASES.find(([outcome]) => outcome === 'secret_unreadable')![1]]);
    expect(markup).toContain('data-executor-secret-readable="no"');
    expect(markup).toContain('Ключ нужно ввести заново');
    expect(markup).toContain('data-executor-blocker="secret_unreadable"');
  });

  it('shows a generated SSH key by its public half only', () => {
    const ssh = OUTCOME_CASES.find(([outcome]) => outcome === 'host_key_unpinned')![1];
    const markup = connections(['admin'], [ssh]);
    expect(markup).toContain('Открытый ключ');
    expect(markup).toContain('открытый-ключ-для-проверки');
    expect(markup).toContain('data-executor-ssh-key=');
    // The observed host key is offered to be pinned, with the warning in words.
    expect(markup).toContain('data-executor-host-key="unpinned"');
    expect(markup).toContain('Закрепить этот отпечаток');
  });

  it('offers the key form link for a connection with settings, and not for a command or a client kind', () => {
    const markup = connections(['admin'], [READY]);
    expect(markup).toContain(`href="/workers?tab=connections&amp;connection=${READY.connection.connection_id}"`);
    const ssh = OUTCOME_CASES.find(([outcome]) => outcome === 'host_key_changed')![1];
    expect(connections(['admin'], [ssh])).not.toContain('data-executor-key-link');
    const bare = executorCase({ n: 40, name: 'Без настроек', revision: null });
    expect(connections(['admin'], [bare])).not.toContain('data-executor-key-link');
    expect(connections(['admin'], [bare])).toContain('Настройки ещё не заданы');
  });

  it('says a connection is ready to be routed, or why it is not', () => {
    const markup = connections(['expert']);
    expect(markup).toContain('data-executor-ready="yes"');
    // `kind_not_served` is drawn only for a kind this release does not know (see the test below):
    // no case of the three served kinds carries it.
    for (const blocker of ['secret_unreadable', 'probe_failed', 'probe_pending', 'not_probed', 'secret_missing', 'no_revision', 'archived']) {
      expect(markup, blocker).toContain(blocker === 'archived' ? 'data-executor-archived="yes"' : `data-executor-blocker="${blocker}"`);
    }
  });

  it('names a revision that moved to the archive, not routed, with no controls', () => {
    const archived = ALL_CASES.find((one) => one.connection.archived_at !== undefined)!;
    const markup = connections(['admin'], [archived]);
    expect(markup).toContain('в архиве');
    expect(markup).not.toContain('>Проверить<');
    expect(markup).not.toContain('>Изменить настройки<');
  });
});

describe('readiness is the probe on the current key, and nothing else', () => {
  const ready = (one = READY) => routeBlocker(one.connection, one.detail.revisions[0]);

  it('is ready only with a finished ok probe taken on the key that is current now', () => {
    expect(ready()).toBeNull();
    const rotated = executorCase({ n: 41, name: 'Ключ заменён после проверки', secrets: [{}], probe: { outcome: 'ok', secret_id: 'exs_01J9ZQ8K7NHVXW3T2R5M6P4QZZ' } });
    expect(routeBlocker(rotated.connection, rotated.detail.revisions[0])).toBe('not_probed');
  });

  it('refuses a key bound to the previous destination even after an ok probe', () => {
    const moved = executorCase({ n: 42, name: 'Адрес сменён', secrets: [{ bound_to_current_revision: false }], probe: { outcome: 'ok' } });
    expect(routeBlocker(moved.connection, moved.detail.revisions[0])).toBe('secret_unreadable');
  });

  it('needs both keys for a tunnelled connection, and none for a client', () => {
    const tunnel = ALL_CASES.find((one) => one.detail.revisions[0]?.transport === 'ssh_tunnel')!;
    expect(requiredPurposes(tunnel.connection, tunnel.detail.revisions[0])).toEqual(['api_key', 'ssh_private_key']);
    const withoutSshKey = { ...tunnel.connection, secrets: tunnel.connection.secrets.filter((item) => item.purpose === 'api_key') };
    expect(routeBlocker(withoutSshKey, tunnel.detail.revisions[0])).toBe('secret_missing');
    const client = OUTCOME_CASES.find(([outcome]) => outcome === 'no_runner_online')![1];
    expect(requiredPurposes(client.connection, client.detail.revisions[0])).toEqual([]);
    // `EXEC-PULL-01` is served: a client whose probe found no runner is blocked by that probe,
    // not by its kind. So is a command over SSH (`EXEC-SSH-01`): this one is blocked by its probe,
    // because its host key is not pinned yet.
    expect(routeBlocker(client.connection, client.detail.revisions[0])).toBe('probe_failed');
    const ssh = OUTCOME_CASES.find(([outcome]) => outcome === 'host_key_unpinned')![1];
    expect(routeBlocker(ssh.connection, ssh.detail.revisions[0])).toBe('probe_failed');
  });

  it('routes a command over SSH on its key and its probe, and blocks only a kind it does not know', () => {
    expect(['http_api', 'pull', 'ssh_command'].map((kind) => kindIsServed(kind as never))).toEqual([true, true, true]);
    const probeOk = { outcome: 'ok', reported_model: 'заявленная-модель', identity_basis: 'reported', latency_ms: 900, rate_check: 'not_metered' } as const;
    const withKey = executorCase({ n: 60, kind: 'ssh_command', name: 'Команда по SSH', secrets: [{ purpose: 'ssh_private_key' }], probe: probeOk });
    expect(routeBlocker(withKey.connection, withKey.detail.revisions[0])).toBeNull();
    expect(connections(['expert'], [withKey])).toContain('data-executor-ready="yes"');
    const withoutKey = executorCase({ n: 61, kind: 'ssh_command', name: 'Команда без ключа', probe: probeOk });
    expect(routeBlocker(withoutKey.connection, withoutKey.detail.revisions[0])).toBe('secret_missing');
    const unknown = executorCase({ n: 62, kind: 'future_kind' as never, name: 'Вид из будущего', secrets: [{}], probe: probeOk });
    expect(kindIsServed('future_kind' as never)).toBe(false);
    expect(routeBlocker(unknown.connection, unknown.detail.revisions[0])).toBe('kind_not_served');
    expect(connections(['expert'], [unknown])).toContain('data-executor-blocker="kind_not_served"');
  });

  it('keeps a sentence for every blocker', () => {
    expect(Object.keys(ROUTE_BLOCKER_SENTENCES).sort()).toEqual(
      ['archived', 'kind_not_served', 'no_revision', 'not_probed', 'probe_failed', 'probe_pending', 'secret_missing', 'secret_unreadable'],
    );
    expect(secretOfPurpose(READY.connection, 'api_key')?.last4).toBe('4417');
    expect(secretOfPurpose(READY.connection, 'ssh_private_key')).toBeNull();
  });
});

describe('«Назначения»: only a connection that can serve is selectable', () => {
  it('disables every other connection and says why beside each', () => {
    const markup = routes(['admin']);
    const options = [...markup.matchAll(/<option[^>]*value="(exc_[^"]+)"[^>]*>([^<]*)</g)];
    expect(options.length).toBeGreaterThan(10);
    const enabled = new Set<string>();
    for (const match of markup.matchAll(/<option(?![^>]*disabled)[^>]*value="(exc_[^"]+)"/g)) enabled.add(match[1] as string);
    expect(enabled.has(READY.connection.connection_id)).toBe(true);
    expect(enabled.has(SPARE.connection.connection_id)).toBe(true);
    for (const one of ALL_CASES) {
      const blocker = routeBlocker(one.connection, one.detail.revisions[0]);
      const archived = one.connection.archived_at !== undefined;
      if (archived) continue; // not offered at all
      expect(enabled.has(one.connection.connection_id), one.connection.display_name).toBe(blocker === null);
    }
    expect(markup).toContain('недоступно: ключ введён для прежнего адреса, введите его заново');
    expect(markup).toContain('data-executor-blocked=');
    expect(markup).toContain('успешной проверкой на текущем ключе');
  });

  it('does not offer an archived connection at all', () => {
    const archived = ALL_CASES.find((one) => one.connection.archived_at !== undefined)!;
    expect(routes(['admin'])).not.toContain(`value="${archived.connection.connection_id}"`);
  });

  it('shows the standby only when one is configured, and says it is not a retry', () => {
    const withStandby = routes(['admin']);
    expect(withStandby).toContain('data-executor-standby');
    expect(withStandby).toContain('только при старте прогона');
    expect(withStandby).toContain('резервное подключение');
    const client = newClient();
    const noStandby: ExecutorRoute = {
      work_kind: ROUTE.work_kind, primary_connection_id: ROUTE.primary_connection_id,
      set_at: ROUTE.set_at, set_by: ROUTE.set_by,
    };
    seedExecutors(client, ALL_CASES, [noStandby]);
    const without = renderScreen(client, createElement(ExecutorRoutes, { roles: ['admin'] }));
    expect(without).not.toContain('data-executor-standby');
    expect(without).toContain('Задать резервное подключение');
  });

  it('says so when nothing is assigned', () => {
    const client = newClient();
    seedExecutors(client, ALL_CASES, []);
    expect(renderScreen(client, createElement(ExecutorRoutes, { roles: ['admin'] }))).toContain('data-executor-route="none"');
  });
});

describe('the notice of changes in the last seven days', () => {
  const label = () => 'Анализ текста';
  const now = Date.now();

  it('names what changed, by whom and when, and leaves out what is older', () => {
    const old = executorCase({ n: 50, name: 'Давнее', secrets: [{ set_at: ago(30 * 24 * 3_600_000) }], probe: null, createdAt: ago(40 * 24 * 3_600_000), revision: { created_at: ago(35 * 24 * 3_600_000) } });
    const recent = executorCase({ n: 51, name: 'Недавнее', secrets: [{}], probe: null, createdAt: ago(3_600_000), revision: { created_at: ago(1_800_000) } });
    const details = new Map([old, recent].map((one) => [one.connection.connection_id, one.detail]));
    const changes = recentChanges([old.connection, recent.connection], details, [ROUTE], now, label);
    expect(changes.map((change) => change.kind).sort()).toEqual(['created', 'revised', 'route_set', 'secret_set']);
    expect(changes.every((change) => change.subject !== 'Давнее' || change.kind === 'route_set')).toBe(true);
    expect(changes[0]!.at >= changes[changes.length - 1]!.at).toBe(true);
    expect(CHANGE_WINDOW_DAYS).toBe(7);
  });

  it('is exactly a week wide, and counts nothing in the future', () => {
    const edge = executorCase({ n: 52, name: 'На границе', probe: null, createdAt: new Date(now - 7 * 24 * 3_600_000 + 1000).toISOString(), revision: null });
    const outside = executorCase({ n: 53, name: 'За границей', probe: null, createdAt: new Date(now - 7 * 24 * 3_600_000 - 1000).toISOString(), revision: null });
    const future = executorCase({ n: 54, name: 'Из будущего', probe: null, createdAt: new Date(now + 3_600_000).toISOString(), revision: null });
    const changes = recentChanges([edge.connection, outside.connection, future.connection], new Map(), [], now, label);
    expect(changes.map((change) => change.subject)).toEqual(['На границе']);
  });

  it('is on the tab: a count and a list when something changed, a plain sentence when not', () => {
    const markup = connections(['expert']);
    expect(markup).toContain('data-executor-changes=');
    expect(markup).toContain('менялись');
    expect(markup).not.toContain('data-executor-changes="0"');
    const quietClient = newClient();
    seedExecutors(quietClient, [SHAPE_OLD()], []);
    quietClient.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    const quiet = renderScreen(quietClient, createElement(ExecutorConnections, { roles: ['expert'] }));
    expect(quiet).toContain('data-executor-changes="0"');
    expect(quiet).toContain('не менялись');
  });
});

function SHAPE_OLD() {
  return executorCase({
    n: 60, name: 'Старое', secrets: [{ set_at: ago(20 * 24 * 3_600_000) }], probe: null,
    createdAt: ago(30 * 24 * 3_600_000), revision: { created_at: ago(25 * 24 * 3_600_000) },
  });
}

describe('the key form is a slot the route fills', () => {
  const form = createElement('form', { 'data-slot-form': '' }, 'форма ключа');

  it('puts the form on the tab for the connection named, and only for an administrator', () => {
    const id = READY.connection.connection_id;
    const admin = connections(['admin'], ALL_CASES, { secretConnectionId: id, secretForm: form });
    expect(admin).toContain('data-slot-form');
    expect(admin).toContain(`data-executor-secret-section="${id}"`);
    expect(admin).toContain('Ключ подключения «Основной шлюз»');
    expect(connections(['expert'], ALL_CASES, { secretConnectionId: id, secretForm: form })).not.toContain('data-slot-form');
  });

  it('explains instead of drawing the form for a kind that takes no typed key', () => {
    const ssh = OUTCOME_CASES.find(([outcome]) => outcome === 'host_key_unpinned')![1].connection.connection_id;
    const markup = connections(['admin'], ALL_CASES, { secretConnectionId: ssh, secretForm: form });
    expect(markup).not.toContain('data-slot-form');
    expect(markup).toContain('data-executor-secret-target="none"');
  });

  it('says so when the connection is not in the list', () => {
    const markup = connections(['admin'], ALL_CASES, { secretConnectionId: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4QZZ', secretForm: form });
    expect(markup).toContain('data-executor-secret-target="missing"');
    expect(markup).not.toContain('data-slot-form');
  });
});

describe('the page', () => {
  function page(props: WorkersPageProps, roles: Role[] = ['admin']): string {
    const client = newClient();
    seedExecutors(client);
    client.setQueryData(queryKeys.account.me(), { roles });
    return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, props));
  }

  it('opens on «Процессы» unless the address names a tab, with the three tabs in their order', () => {
    const markup = page({});
    expect(markup).toContain('data-workers-panel="processes"');
    const order = ['connections', 'processes', 'routes'].map((tab) => markup.indexOf(`data-workers-tab="${tab}"`));
    expect(order.every((at) => at >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    for (const label of ['Подключения', 'Процессы', 'Назначения']) expect(markup).toContain(`>${label}<`);
  });

  it('opens the tab the address names, and draws nothing of the others', () => {
    const connectionsTab = page({ initialTab: 'connections' });
    expect(connectionsTab).toContain('data-workers-panel="connections"');
    expect(connectionsTab).toContain('data-executor-connections');
    expect(connectionsTab).not.toContain('data-worker-group');
    expect(page({ initialTab: 'routes' })).toContain('data-executor-routes');
    expect(page({ initialTab: 'processes' })).not.toContain('data-executor-connections');
  });

  it('marks exactly the open tab as selected', () => {
    const markup = page({ initialTab: 'routes' });
    expect(markup.match(/aria-selected="true"/g)?.length).toBe(1);
    expect(markup).toMatch(/aria-selected="true"[^>]*data-workers-tab="routes"|data-workers-tab="routes"[^>]*aria-selected="true"/);
  });
});

describe('a refusal is said in Russian, from the safe detail keys', () => {
  const refusal = (code: 'validation_failed' | 'conflict' | 'dependency_unavailable', details: Record<string, string>) =>
    connectionFailure(new ApiError(code === 'conflict' ? 409 : code === 'validation_failed' ? 422 : 503, ENVELOPE(code, details), null), true);

  it('names the field and the constraint', () => {
    expect(refusal('validation_failed', { field: 'pin_id', constraint: 'model_not_pinned' }).detail).toBe(
      'Модель: эта модель не закреплена в замке провайдера, выберите модель из списка.');
    expect(refusal('validation_failed', { field: 'base_url', constraint: 'base_url_invalid' }).detail).toMatch(/^Адрес: /);
    expect(refusal('validation_failed', { field: 'standby_connection_id', constraint: 'standby_equals_primary' }).detail).toContain('должно отличаться');
  });

  it('names the conflict and the missing dependency', () => {
    expect(refusal('conflict', { conflict_reason: 'connection_routed' }).detail).toContain('назначено на работу');
    expect(refusal('conflict', { conflict_reason: 'no_revision' }).detail).toContain('ещё нет настроек');
    const missing = refusal('dependency_unavailable', { dependency: 'secrets_public_key_missing' });
    expect(missing.detail).toContain('открытый ключ');
    // Named before anything is written, so it is a refusal and not an unknown outcome.
    expect(missing.kind).toBe('refusal');
    expect(refusal('dependency_unavailable', { dependency: 'something_new' }).kind).toBe('unknown_outcome');
  });

  it('falls back to the catalogue sentence, never to the English message, for a value it does not know', () => {
    const unknown = refusal('validation_failed', { field: 'pin_id', constraint: 'something_new' });
    expect(unknown.detail).not.toContain('Safe.');
    expect(unknown.detail.length).toBeGreaterThan(10);
  });
});
