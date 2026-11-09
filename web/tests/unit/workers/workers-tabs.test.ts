/**
 * `HOSTS-WEB-01` — the tabs of «Исполнители» (two since the six moved to `/workers/advanced`): their order, the one the screen
 * opens on, and the keyboard contract of the WAI-ARIA tabs pattern, stated as a function because the static render this suite
 * has cannot fire a key. `EXEC-HTTP-01` wrote the first version of this file for the six.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  ADVANCED_SECTIONS, ADVANCED_SECTION_LABELS, DEFAULT_WORKERS_TAB, WORKERS_ADVANCED_ADDRESS, WORKERS_TABS, WORKERS_TAB_LABELS,
  WORKERS_TAB_PARAM, isAdvancedSection, isWorkersTab, legacyAdvancedTab, tabAfterKey,
} from '@/_pages/workers';
import { WorkersTabs } from '@/_pages/workers/ui/workers-tabs';

describe('the tabs', () => {
  it('are «Серверы» and «Модели по этапам», in that order, and open on «Серверы»', () => {
    expect([...WORKERS_TABS]).toEqual(['servers', 'models']);
    expect(WORKERS_TABS.map((tab) => WORKERS_TAB_LABELS[tab])).toEqual(['Серверы', 'Модели по этапам']);
    expect(DEFAULT_WORKERS_TAB).toBe('servers');
    expect(WORKERS_TAB_PARAM).toBe('tab');
  });

  it('are recognised by exact name only, and the six old names are not tabs any more', () => {
    expect(isWorkersTab('servers')).toBe(true);
    expect(isWorkersTab('models')).toBe(true);
    for (const other of ['', 'Servers', 'server', 'workers', 'overview', 'connections', 'processes', 'groups', 'rules', 'routes', null, undefined, 3]) {
      expect(isWorkersTab(other)).toBe(false);
    }
  });

  it('move with the arrow keys, wrapping at the ends, and with Home and End', () => {
    expect(tabAfterKey('servers', 'ArrowRight')).toBe('models');
    expect(tabAfterKey('models', 'ArrowRight')).toBe('servers');
    expect(tabAfterKey('servers', 'ArrowLeft')).toBe('models');
    expect(tabAfterKey('models', 'ArrowLeft')).toBe('servers');
    expect(tabAfterKey('models', 'Home')).toBe('servers');
    expect(tabAfterKey('servers', 'End')).toBe('models');
    expect(tabAfterKey('servers', 'Enter')).toBeNull();
    expect(tabAfterKey('models', 'a')).toBeNull();
  });

  it('render as a tablist with one selected tab, one tab in the tab order, and one labelled panel', () => {
    const markup = renderToStaticMarkup(createElement(WorkersTabs, { active: 'models', onSelect: () => {}, children: 'содержимое' }));
    expect(markup.match(/role="tab"/g)).toHaveLength(2);
    expect(markup.match(/aria-selected="true"/g)).toHaveLength(1);
    expect(markup.match(/tabindex="0"/g)).toHaveLength(2);
    expect(markup.match(/tabindex="-1"/g)).toHaveLength(1);
    expect(markup).toContain('role="tabpanel"');
    expect(markup).toContain('data-workers-panel="models"');
    expect(markup).toContain('содержимое');
    const panel = markup.match(/aria-controls="([^"]+)"/)?.[1];
    expect(panel).toBeDefined();
    expect(markup).toContain(`id="${panel}"`);
  });
});

describe('the advanced page keeps the former tabs, folded', () => {
  it('has a section for each of the five former tabs, the presets and the layout switch', () => {
    expect([...ADVANCED_SECTIONS]).toEqual(['connections', 'groups', 'rules', 'routes', 'processes', 'presets', 'layout']);
    expect(ADVANCED_SECTIONS.map((section) => ADVANCED_SECTION_LABELS[section])).toEqual([
      'Подключения', 'Группы', 'Правила', 'Назначения', 'Процессы', 'Пресеты анализа', 'Модели по этапам',
    ]);
    expect(WORKERS_ADVANCED_ADDRESS).toBe('/workers/advanced');
  });

  it('knows its sections by exact name only', () => {
    for (const section of ADVANCED_SECTIONS) expect(isAdvancedSection(section)).toBe(true);
    for (const other of ['', 'Groups', 'overview', 'servers', null, undefined, 3]) expect(isAdvancedSection(other)).toBe(false);
  });

  it('sends an old tab of «Исполнители» to the section that took it over, and «Обзор» to none', () => {
    for (const tab of ['connections', 'processes', 'groups', 'rules', 'routes']) expect(legacyAdvancedTab(tab)).toBe(tab);
    for (const other of ['overview', 'servers', 'models', 'presets', 'layout', '', undefined]) expect(legacyAdvancedTab(other)).toBeNull();
  });
});
