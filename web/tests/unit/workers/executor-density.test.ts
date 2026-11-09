/**
 * Lane N1 — the executors' tabs as dense screens: the changes notice with its tail folded, row actions at the small
 * height, the routes as a line each with the editor folded and the empty and read-only states said once, groups with the
 * binding notice folded and their controls in one row, the rule editor as one line, the rules table in a region Tab reaches,
 * and the connection forms in two columns. Rendered in one static pass over seeded caches.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorGroups } from '@/widgets/executor-groups';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { ExecutorRules } from '@/widgets/executor-rules';
import { CreateConnectionForm, ReviseConnectionForm } from '@/features/manage-executor-connection';
import { RuleEditor } from '@/features/manage-executor-group';
import { SetExecutorSecretForm } from '@/features/set-executor-secret';
import { CLIENT_DOCUMENTS_NOTICE } from '@/entities/executor-connection';

import { newClient, renderScreen } from '../screens/harness';
import { MAIN_GROUP, ROUTED_GROUP, ruleOf, seedGroups, seedRules } from '../executor-groups/executor-groups-fixtures';
import { ALL_CASES, PINNED, READY, executorCase, seedExecutors, ago } from './executor-fixtures';

function seeded(roles: Role[], cases = ALL_CASES, routesToSeed?: Parameters<typeof seedExecutors>[2]) {
  const client = newClient();
  seedExecutors(client, cases, routesToSeed);
  client.setQueryData(queryKeys.account.me(), { roles });
  return client;
}

const connections = (roles: Role[], cases = ALL_CASES, items?: Parameters<typeof seedExecutors>[2]): string =>
  renderScreen(seeded(roles, cases, items), createElement(ExecutorConnections, { roles }));
const routes = (roles: Role[], cases = ALL_CASES, items?: Parameters<typeof seedExecutors>[2]): string =>
  renderScreen(seeded(roles, cases, items), createElement(ExecutorRoutes, { roles }));

/** The tags of every button and every link styled as one, as written. */
function controls(markup: string): string[] {
  return [...markup.matchAll(/<(?:button|a)\b[^>]*class="[^"]*am-button[^"]*"[^>]*>/g)].map((match) => match[0]);
}

describe('«Подключения»: the notice of changes keeps the newest three open and folds the rest', () => {
  const recent = (n: number) => executorCase({
    n, name: `Новое ${n}`, secrets: [{}], probe: null, createdAt: ago(3_600_000), revision: { created_at: ago(1_800_000) },
  });

  it('folds the tail under a count when more than three changed, and still says the whole count', () => {
    const markup = connections(['expert'], [recent(90), recent(91), recent(92)]);
    const total = Number(/data-executor-changes="(\d+)"/.exec(markup)?.[1]);
    expect(total).toBeGreaterThan(3);
    const shown = Math.min(total, 10) - 3;
    expect(markup).toContain(`Ещё изменений: ${shown}`);
    expect(markup).toContain(`data-executor-changes-more="${shown}"`);
    expect(markup).toContain(`подключения менялись: ${total}.`);
    const section = markup.slice(markup.indexOf('data-executor-changes='), markup.indexOf('data-executor-list-notice'));
    const open = section.slice(0, section.indexOf('<details'));
    expect(open.match(/<li>/g)).toHaveLength(3);
    expect(section.slice(section.indexOf('<details')).match(/<li>/g)).toHaveLength(shown);
  });

  it('can fail: three changes or fewer fold nothing', () => {
    const markup = connections(['expert'], [recent(93)], []);
    expect(Number(/data-executor-changes="(\d+)"/.exec(markup)?.[1])).toBeLessThanOrEqual(3);
    expect(markup).not.toContain('data-executor-changes-more');
  });

  it('keeps the client documents notice as one visible line, exactly as the register words it', () => {
    expect(connections(['expert'])).toContain(`<p class="am-note" data-executor-list-notice="client-documents">${CLIENT_DOCUMENTS_NOTICE}</p>`);
  });
});

describe('«Подключения»: the card’s own actions are at the row height', () => {
  it('draws the probe, the archive, the key link and the edit at the small height, for an administrator', () => {
    const tags = controls(connections(['admin']));
    const named = (marker: string) => tags.filter((tag) => tag.includes(marker));
    expect(named('data-executor-probe=').length).toBeGreaterThan(0);
    for (const tag of [...named('data-executor-probe='), ...named('data-executor-key-link'), ...named('data-executor-ssh-key=')]) {
      expect(tag).toContain('am-button--small');
    }
    const markup = connections(['admin']);
    for (const label of ['Изменить настройки', 'Архивировать']) {
      const at = markup.indexOf(`>${label}<`);
      expect(at, label).toBeGreaterThan(-1);
      expect(markup.slice(markup.lastIndexOf('<', at - 1), at)).toContain('am-button--small');
    }
  });

  it('folds the facts of a version under a line that names its version, model and billing, and keeps every fact in the markup', () => {
    const markup = connections(['expert']);
    const folded = markup.match(/<details[^>]*data-executor-settings=""[^>]*><summary>Настройки: версия \d+ · модель [^<]+ · [^<]+<\/summary><dl[^>]*data-executor-revision=/g) ?? [];
    expect(folded.length).toBeGreaterThan(5);
    // One fold for every connection that has a version: the facts are the same ones as before, only under the line.
    expect(markup.match(/data-executor-revision="/g)?.length).toBe(folded.length);
    expect(markup).toContain('data-executor-billing=');
    expect(markup).toContain('data-executor-active-runs=');
  });

  it('says who made the connection as a muted hint line, not a paragraph of the card’s own weight', () => {
    expect(connections(['expert'])).toMatch(/<p class="am-form__hint [^"]*identity[^"]*">Подключение <code>/);
  });
});

describe('«Назначения»: a line each, the editor folded, the states said once', () => {
  it('draws each kind with its route in one list and the editor in a details element', () => {
    const markup = routes(['admin']);
    expect(markup.match(/data-executor-route-edit=/g)).toHaveLength(6);
    expect(markup).toMatch(/<details[^>]*data-executor-route-edit="text_analysis"/);
    expect(markup).toMatch(/<dl class="[^"]*summary[^"]*" data-executor-route="text_analysis"/);
    expect(markup).toContain('data-executor-route-form="text_analysis"');
  });

  it('opens the editor of a kind with no route and folds the editor of a kind that has one', () => {
    const markup = routes(['admin']);
    const detailsOf = (kind: string) => /<details[^>]*>/.exec(markup.slice(markup.indexOf(`data-executor-route-edit="${kind}"`) - 80))?.[0] ?? '';
    expect(detailsOf('text_analysis')).not.toMatch(/\bopen=""/);
    expect(detailsOf('comparison_spec')).toMatch(/\bopen=""/);
    expect(markup).toContain('>Изменить назначение</summary>');
    expect(markup).toContain('>Назначить подключение</summary>');
  });

  it('says that there is nothing to assign once, not under each of the six kinds', () => {
    const none = routes(['admin'], [], []);
    expect(none.match(/Нет подключений для назначения/g)).toHaveLength(1);
    expect(none).not.toContain('data-executor-route-edit');
  });

  it('says that only an administrator changes routes once, and draws no editor to an expert', () => {
    const expert = routes(['expert']);
    expect(expert.match(/data-executor-routes-readonly/g)).toHaveLength(1);
    expect(expert).not.toContain('data-executor-route-edit');
    expect(routes(['admin']).match(/data-executor-routes-readonly/g)).toBeNull();
  });
});

describe('«Группы»: the binding notice folded, the controls of a group in one row', () => {
  const groups = (roles: Role[]) => {
    const client = newClient();
    seedGroups(client, [MAIN_GROUP, ROUTED_GROUP]);
    client.setQueryData(queryKeys.account.me(), { roles });
    return renderScreen(client, createElement(ExecutorGroups, { roles }));
  };

  it('keeps the client documents notice open and folds how work reaches a group', () => {
    const markup = groups(['admin']);
    expect(markup).toContain(CLIENT_DOCUMENTS_NOTICE);
    expect(markup).toMatch(/<details[^>]*data-executor-groups-notice="binding"[^>]*><summary>Как работа попадает в группу<\/summary>/);
    expect(markup).toContain('Группа фиксируется при приёме работы');
    expect(markup).toContain('наименьшей загрузкой');
  });

  it('puts «Новая версия» and «В архив» of a group in one row, and none for an expert', () => {
    const admin = groups(['admin']);
    expect(admin).toMatch(/<div class="[^"]*actions[^"]*"><details[^>]*data-group-revise/);
    expect(admin).toMatch(/am-button--small[^>]*>В архив</);
    expect(groups(['expert'])).not.toContain('data-group-revise');
    expect(groups(['expert'])).not.toMatch(/>В архив</);
  });
});

describe('«Правила»: a one-line editor, a table Tab reaches', () => {
  const rules = (roles: Role[]) => {
    const client = newClient();
    seedGroups(client, [MAIN_GROUP, ROUTED_GROUP]);
    seedRules(client, 'legacy', [ruleOf('text_analysis', ROUTED_GROUP, 1)]);
    client.setQueryData(queryKeys.account.me(), { roles });
    return renderScreen(client, createElement(ExecutorRules, { roles }));
  };

  it('draws the editor as a form of two fields and a button, its hint under them', () => {
    const markup = renderScreen(newClient(), createElement(RuleEditor, { groups: [MAIN_GROUP], mode: 'legacy' }));
    expect(markup).toMatch(/<form class="am-form [^"]*form[^"]*" data-rule-editor/);
    expect(markup.match(/class="am-form__field [^"]*field/g)).toHaveLength(2);
    expect(markup.indexOf('Правило называет версию группы')).toBeGreaterThan(markup.indexOf('>Назначить группу<'));
    const bare = renderScreen(newClient(), createElement(RuleEditor, { groups: [], mode: 'legacy' }));
    expect(bare).toContain('data-rule-editor-no-groups');
    expect(bare).not.toContain('Правило называет версию группы');
  });

  it('puts the rules table in a named, focusable region and keeps its caption', () => {
    const markup = rules(['expert']);
    expect(markup).toMatch(/<div[^>]*role="region"[^>]*aria-label="Правила по видам работы, таблица"[^>]*tabindex="0"/);
    expect(markup).toContain('<caption>Правила: какая группа принимает работу каждого вида</caption>');
  });
});

describe('the two connection forms stand in two columns', () => {
  it('marks the form for the grid and the long fields as wide, the short ones not', () => {
    const markup = renderScreen(newClient(), createElement(ReviseConnectionForm, {
      connection: READY.connection, revision: READY.detail.revisions[0], pinnedModels: PINNED, holdsKey: true, onClose: () => {},
    }));
    expect(markup).toMatch(/<form class="am-form [^"]*form[^"]*"[^>]*data-executor-revise-form/);
    // The tag of the field that holds the label of `id`: the last `<div` before the label's `for`.
    const field = (id: string) => {
      const at = markup.indexOf(`-${id}"`);
      return markup.slice(markup.lastIndexOf('<div', at), at);
    };
    expect(field('base-url')).toMatch(/am-form__field [^"]*wide/);
    expect(field('gateway')).toMatch(/am-form__field [^"]*wide/);
    expect(field('timeout')).not.toMatch(/wide/);
    expect(field('flavour')).not.toMatch(/wide/);
  });

  it('gives the create form the same grid', () => {
    const markup = renderScreen(newClient(), createElement(CreateConnectionForm, { pinnedModels: PINNED }));
    expect(markup).toMatch(/<form class="am-form [^"]*form[^"]*"[^>]*data-executor-create-form/);
  });
});

describe('the key form: the field and its button on one line, the address note folded', () => {
  const form = () => renderScreen(newClient(), createElement(SetExecutorSecretForm, { connectionId: READY.connection.connection_id }));

  it('puts the password field and «Сохранить ключ» in one row, as the search forms do', () => {
    const markup = form();
    const row = markup.slice(markup.indexOf('<div class="am-form__row">'), markup.indexOf('</div>', markup.indexOf('<div class="am-form__row">')));
    expect(row).toContain('type="password"');
    expect(row).toContain('>Сохранить ключ</button>');
    expect(markup).toContain('<label for="executor-secret-');
  });

  it('says what the key is bound to in the open and folds what a changed address does to it', () => {
    const markup = form();
    expect(markup).toContain('запечатывается при отправке');
    expect(markup).toMatch(/<details[^>]*data-executor-secret-moves=""[^>]*><summary>Если сменить адрес подключения<\/summary>/);
    expect(markup).toContain('Прежний ключ перестанет открываться, и его придётся вставить заново.');
  });
});
