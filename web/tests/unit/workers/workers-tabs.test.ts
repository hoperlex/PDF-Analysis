/**
 * `HOSTS-WEB-01`, `UIP-S15-06` — the tabs of «Диспетчер» (two since the six moved to `/workers/advanced`, four again with «Обзор»
 * and «Задачи»): their order, the one the screen opens on, the address that keeps them, and the keyboard contract of the WAI-ARIA tabs
 * pattern, stated as a function because the static render this suite has cannot fire a key. `EXEC-HTTP-01` wrote the first version
 * of this file for the six.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import {
  ADVANCED_SECTIONS, ADVANCED_SECTION_LABELS, DEFAULT_WORKERS_TAB, WORKERS_ADVANCED_ADDRESS, WORKERS_TABS, WORKERS_TAB_LABELS,
  WORKERS_TAB_PARAM, isAdvancedSection, isWorkersTab, legacyAdvancedTab, tabAfterKey,
} from '@/_pages/workers';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';
import { WorkersTabs } from '@/_pages/workers/ui/workers-tabs';
import { queryKeys } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import { JOB_RUNNING, queuePage, seedHosts, seedLayout, seedQueue } from './hosts-fixtures';

describe('the tabs', () => {
  it('are «Обзор», «Серверы», «Задачи» and «Модели по этапам», in that order, and open on «Обзор»', () => {
    expect([...WORKERS_TABS]).toEqual(['overview', 'servers', 'tasks', 'models']);
    expect(WORKERS_TABS.map((tab) => WORKERS_TAB_LABELS[tab])).toEqual(['Обзор', 'Серверы', 'Задачи', 'Модели по этапам']);
    expect(DEFAULT_WORKERS_TAB).toBe('overview');
    expect(WORKERS_TAB_PARAM).toBe('tab');
  });

  it('are recognised by exact name only: the four of the address, and none of the six old names or of the tabs the stand has no data for', () => {
    for (const tab of ['overview', 'servers', 'tasks', 'models']) expect(isWorkersTab(tab), tab).toBe(true);
    for (const other of ['', 'Servers', 'server', 'workers', 'Overview', 'queue', 'limits', 'diagnostics', 'connections', 'processes', 'groups', 'rules', 'routes', null, undefined, 3]) {
      expect(isWorkersTab(other), String(other)).toBe(false);
    }
  });

  it('move with the arrow keys, wrapping at the ends, and with Home and End', () => {
    expect(tabAfterKey('overview', 'ArrowRight')).toBe('servers');
    expect(tabAfterKey('servers', 'ArrowRight')).toBe('tasks');
    expect(tabAfterKey('tasks', 'ArrowRight')).toBe('models');
    expect(tabAfterKey('models', 'ArrowRight')).toBe('overview');
    expect(tabAfterKey('overview', 'ArrowLeft')).toBe('models');
    expect(tabAfterKey('models', 'ArrowLeft')).toBe('tasks');
    expect(tabAfterKey('servers', 'ArrowLeft')).toBe('overview');
    expect(tabAfterKey('tasks', 'Home')).toBe('overview');
    expect(tabAfterKey('servers', 'End')).toBe('models');
    expect(tabAfterKey('servers', 'Enter')).toBeNull();
    expect(tabAfterKey('models', 'a')).toBeNull();
  });

  it('render as a tablist with one selected tab, one tab in the tab order, and one labelled panel', () => {
    const markup = renderToStaticMarkup(createElement(WorkersTabs, { active: 'models', onSelect: () => {}, children: 'содержимое' }));
    expect(markup.match(/role="tab"/g)).toHaveLength(4);
    expect(markup.match(/aria-selected="true"/g)).toHaveLength(1);
    // The selected tab and the panel are in the tab order; the other three tabs are not.
    expect(markup.match(/tabindex="0"/g)).toHaveLength(2);
    expect(markup.match(/tabindex="-1"/g)).toHaveLength(3);
    expect(markup).toContain('role="tabpanel"');
    expect(markup).toContain('data-workers-panel="models"');
    expect(markup).toContain('содержимое');
    const panel = markup.match(/aria-controls="([^"]+)"/)?.[1];
    expect(panel).toBeDefined();
    expect(markup).toContain(`id="${panel}"`);
    expect([...markup.matchAll(/data-workers-tab="([^"]+)"/g)].map((match) => match[1])).toEqual(['overview', 'servers', 'tasks', 'models']);
  });
});

describe('the page opens on the tab the address names', () => {
  const page = (initialTab?: WorkersPageProps['initialTab']): string => {
    const client = newClient();
    seedHosts(client);
    seedQueue(client, queuePage([]));
    seedQueue(client, queuePage([JOB_RUNNING]), { stateGroup: 'active' });
    seedLayout(client);
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, initialTab === undefined ? {} : { initialTab }));
  };
  const panels = ['data-hosts-overview', 'data-executor-hosts', 'data-hosts-tasks', 'data-layout-cell'];

  it('opens on «Обзор» when the address names no tab, and on the tab it names otherwise', () => {
    expect(page()).toContain('data-workers-panel="overview"');
    for (const [tab, mark] of [['overview', 'data-hosts-overview'], ['servers', 'data-executor-hosts'], ['tasks', 'data-hosts-tasks'], ['models', 'data-layout-cell']] as const) {
      const markup = page(tab);
      expect(markup, tab).toContain(`data-workers-panel="${tab}"`);
      expect(markup, tab).toContain(mark);
    }
  });

  it('can fail: a closed tab mounts nothing, so it reads nothing', () => {
    for (const [tab, mark] of [['overview', 'data-hosts-overview'], ['servers', 'data-executor-hosts'], ['tasks', 'data-hosts-tasks'], ['models', 'data-layout-cell']] as const) {
      const markup = page(tab);
      for (const other of panels.filter((candidate) => candidate !== mark)) expect(markup, `${tab} ${other}`).not.toContain(other);
    }
  });

  it('draws four tabs in the order of the strip, the selected one marked, and keeps «Расширенные ▸» and «Обновить» in the head', () => {
    const markup = page('tasks');
    expect([...markup.matchAll(/<button[^>]*role="tab"[^>]*>([^<]*)</g)].map((match) => match[1])).toEqual(['Обзор', 'Серверы', 'Задачи', 'Модели по этапам']);
    expect(markup).toMatch(/aria-selected="true"[^>]*data-workers-tab="tasks"/);
    expect(markup).toContain('>Обновить<');
  });

  it('says the page in one plain sentence: the servers, what runs on them, and the model of each stage', () => {
    const subtitle = /<p class="am-page__subtitle">([^<]*)<\/p>/.exec(page())?.[1] ?? '';
    expect(subtitle).toBe('Серверы, что на них сейчас идёт и какая модель у каждого этапа.');
  });
});

describe('the advanced page keeps the former tabs, folded', () => {
  it('has a section for each of the five former tabs, the presets and the layout switch', () => {
    expect([...ADVANCED_SECTIONS]).toEqual(['connections', 'groups', 'rules', 'routes', 'processes', 'presets', 'layout', 'precedents']);
    expect(ADVANCED_SECTIONS.map((section) => ADVANCED_SECTION_LABELS[section])).toEqual([
      'Подключения', 'Группы', 'Правила', 'Назначения', 'Процессы', 'Пресеты анализа', 'Модели по этапам', 'Прецеденты и векторы',
    ]);
    expect(WORKERS_ADVANCED_ADDRESS).toBe('/workers/advanced');
  });

  it('knows its sections by exact name only', () => {
    for (const section of ADVANCED_SECTIONS) expect(isAdvancedSection(section)).toBe(true);
    for (const other of ['', 'Groups', 'overview', 'servers', null, undefined, 3]) expect(isAdvancedSection(other)).toBe(false);
  });

  it('sends an old tab of «Диспетчер» to the section that took it over, and the four tabs of the screen to none', () => {
    for (const tab of ['connections', 'processes', 'groups', 'rules', 'routes']) expect(legacyAdvancedTab(tab)).toBe(tab);
    for (const other of ['overview', 'servers', 'tasks', 'models', 'presets', 'layout', 'precedents', '', undefined]) expect(legacyAdvancedTab(other)).toBeNull();
  });
});
