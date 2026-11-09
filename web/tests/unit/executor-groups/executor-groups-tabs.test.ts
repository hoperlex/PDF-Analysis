/**
 * `EXEC2-WEB-GROUPS-01` — the tabs of «Исполнители» after «Группы» and «Правила», and what each of the
 * new ones draws on the page. Written under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL.
 *
 * The enumerator is `WORKERS_TABS`. «Назначения» stays the last tab: it is the legacy Primary/Standby
 * editor while the routing mode is `legacy` and the history of the routes once rules are in force
 * (ADR-0026 decision 17), so the page tests below also hold that it is an editor in the one mode and
 * history in the other.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  DEFAULT_WORKERS_TAB, WORKERS_TABS, WORKERS_TAB_LABELS, WORKERS_TAB_PARAM, WorkersPage, isWorkersTab, tabAfterKey,
} from '@/_pages/workers';
import type { WorkersPageProps, WorkersTab } from '@/_pages/workers';
import { WorkersTabs } from '@/_pages/workers/ui/workers-tabs';

import { newClient, renderScreen } from '../screens/harness';
import { MAIN_GROUP, ROUTED_GROUP, ruleOf, seedGroups, seedRules } from './executor-groups-fixtures';

describe('the tabs', () => {
  it('are «Обзор», «Подключения», «Процессы», «Группы», «Правила», «Назначения», in that order', () => {
    expect([...WORKERS_TABS]).toEqual(['overview', 'connections', 'processes', 'groups', 'rules', 'routes']);
    expect(WORKERS_TABS.map((tab) => WORKERS_TAB_LABELS[tab])).toEqual([
      'Обзор', 'Подключения', 'Процессы', 'Группы', 'Правила', 'Назначения',
    ]);
    expect(DEFAULT_WORKERS_TAB).toBe('overview');
    expect(WORKERS_TAB_PARAM).toBe('tab');
  });

  it('are recognised by exact name only, and the new two are recognised', () => {
    for (const tab of WORKERS_TABS) expect(isWorkersTab(tab)).toBe(true);
    for (const other of ['', 'Groups', 'group', 'rule', 'Rules', null, undefined, 3]) {
      expect(isWorkersTab(other)).toBe(false);
    }
  });

  it('move with the arrow keys through the two new tabs, wrapping at the ends', () => {
    expect(tabAfterKey('processes', 'ArrowRight')).toBe('groups');
    expect(tabAfterKey('groups', 'ArrowRight')).toBe('rules');
    expect(tabAfterKey('rules', 'ArrowRight')).toBe('routes');
    expect(tabAfterKey('routes', 'ArrowRight')).toBe('overview');
    expect(tabAfterKey('overview', 'ArrowLeft')).toBe('routes');
    expect(tabAfterKey('connections', 'ArrowLeft')).toBe('overview');
    expect(tabAfterKey('groups', 'ArrowLeft')).toBe('processes');
    expect(tabAfterKey('routes', 'Home')).toBe('overview');
    expect(tabAfterKey('connections', 'End')).toBe('routes');
    expect(tabAfterKey('groups', 'Enter')).toBeNull();
  });

  it('render as a tablist of six, one selected, one in the tab order, one labelled panel', () => {
    const markup = renderToStaticMarkup(
      createElement(WorkersTabs, { active: 'rules', onSelect: () => {}, children: 'содержимое' }),
    );
    expect(markup.match(/role="tab"/g)).toHaveLength(6);
    expect(markup.match(/aria-selected="true"/g)).toHaveLength(1);
    expect(markup.match(/tabindex="-1"/g)).toHaveLength(5);
    expect(markup).toContain('data-workers-panel="rules"');
    for (const label of ['Обзор', 'Группы', 'Правила', 'Назначения']) expect(markup).toContain(`>${label}<`);
  });
});

describe('the page', () => {
  function page(props: WorkersPageProps, roles: Role[] = ['admin'], mode: 'legacy' | 'rules' | null = null): string {
    const client = newClient();
    seedGroups(client);
    client.setQueryData(queryKeys.account.me(), { roles });
    if (mode !== null) seedRules(client, mode, mode === 'rules' ? [ruleOf('text_analysis', ROUTED_GROUP, 1)] : []);
    return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, props));
  }

  const tab = (name: WorkersTab): WorkersPageProps => ({ initialTab: name });

  it('draws «Группы» and nothing of the other tabs', () => {
    const markup = page(tab('groups'));
    expect(markup).toContain('data-workers-panel="groups"');
    expect(markup).toContain('data-executor-groups');
    expect(markup).not.toContain('data-executor-rules');
    expect(markup).not.toContain('data-executor-routes');
    expect(markup).not.toContain('data-executor-connections');
  });

  it('draws «Правила» with the legacy routes inside it while the mode is the legacy one', () => {
    const markup = page(tab('rules'), ['admin'], 'legacy');
    expect(markup).toContain('data-workers-panel="rules"');
    expect(markup).toContain('data-executor-rules');
    expect(markup).toContain('data-rules-legacy-routes');
    // The routes there are history: their summaries, never their editors.
    expect(markup).toContain('data-executor-routes');
    expect(markup).not.toContain('data-executor-route-form');
    expect(markup).not.toContain('data-executor-routes-history');
  });

  it('draws «Назначения» as the editor under the legacy mode and as history under rules', () => {
    const legacy = page(tab('routes'), ['admin'], 'legacy');
    expect(legacy).toContain('data-executor-route-form');
    expect(legacy).not.toContain('data-executor-routes-history');

    const ruled = page(tab('routes'), ['admin'], 'rules');
    expect(ruled).toContain('data-executor-routes-history');
    expect(ruled).toContain('data-executor-route="text_analysis"');
    expect(ruled).not.toContain('data-executor-route-form');
    expect(ruled).not.toContain('Сохранить назначение');
  });

  it('keeps «Назначения» an editor while the mode has not been read: the server enforces the mode', () => {
    const markup = page(tab('routes'), ['admin'], null);
    expect(markup).toContain('data-executor-route-form');
    expect(markup).not.toContain('data-executor-routes-history');
  });

  it('marks exactly the open tab as selected', () => {
    for (const name of WORKERS_TABS) {
      const markup = page(tab(name), ['admin'], 'legacy');
      expect(markup.match(/aria-selected="true"/g)).toHaveLength(1);
      expect(markup).toMatch(new RegExp(`aria-selected="true"[^>]*data-workers-tab="${name}"|data-workers-tab="${name}"[^>]*aria-selected="true"`));
    }
  });

  it('shows the groups to every role and the controls to an administrator only', () => {
    const group = MAIN_GROUP.display_name;
    const admin = page(tab('groups'), ['admin']);
    const reader = page(tab('groups'), ['expert']);
    expect(admin).toContain(group);
    expect(reader).toContain(group);
    expect(admin).toContain('data-executor-group-create');
    expect(reader).not.toContain('data-executor-group-create');
    expect(reader).not.toContain('data-group-revise');
  });
});
