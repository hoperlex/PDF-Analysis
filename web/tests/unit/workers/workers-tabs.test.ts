/**
 * `EXEC-HTTP-01` — the tabs of «Исполнители»: their order, the one the screen opens on, and the
 * keyboard contract of the WAI-ARIA tabs pattern, stated as a function because the static
 * render this suite has cannot fire a key.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_WORKERS_TAB, WORKERS_TABS, WORKERS_TAB_LABELS, WORKERS_TAB_PARAM, isWorkersTab, tabAfterKey,
} from '@/_pages/workers';
import { WorkersTabs } from '@/_pages/workers/ui/workers-tabs';

describe('the tabs', () => {
  it('are «Обзор», «Подключения», «Процессы», «Группы», «Правила», «Назначения», in that order, and open on «Обзор»', () => {
    // `EXEC2-WEB-GROUPS-01` adds «Группы» and «Правила»; «Назначения» stays last as the legacy editor and history.
    // UI-B-63 puts «Обзор» first; the second UX pass (2026-11-07) makes it the one the screen opens on, as the original's dispatcher does.
    expect([...WORKERS_TABS]).toEqual(['overview', 'connections', 'processes', 'groups', 'rules', 'routes']);
    expect(WORKERS_TABS.map((tab) => WORKERS_TAB_LABELS[tab])).toEqual(['Обзор', 'Подключения', 'Процессы', 'Группы', 'Правила', 'Назначения']);
    expect(DEFAULT_WORKERS_TAB).toBe('overview');
    expect(WORKERS_TAB_PARAM).toBe('tab');
  });

  it('are recognised by exact name only', () => {
    expect(isWorkersTab('routes')).toBe(true);
    expect(isWorkersTab('overview')).toBe(true);
    for (const other of ['', 'Routes', 'route', 'workers', null, undefined, 3]) expect(isWorkersTab(other)).toBe(false);
  });

  it('move with the arrow keys, wrapping at the ends, and with Home and End', () => {
    expect(tabAfterKey('connections', 'ArrowRight')).toBe('processes');
    expect(tabAfterKey('routes', 'ArrowRight')).toBe('overview');
    expect(tabAfterKey('overview', 'ArrowLeft')).toBe('routes');
    expect(tabAfterKey('connections', 'ArrowLeft')).toBe('overview');
    expect(tabAfterKey('processes', 'Home')).toBe('overview');
    expect(tabAfterKey('processes', 'End')).toBe('routes');
    expect(tabAfterKey('processes', 'Enter')).toBeNull();
    expect(tabAfterKey('processes', 'a')).toBeNull();
  });

  it('render as a tablist with one selected tab, one tab in the tab order, and one labelled panel', () => {
    const markup = renderToStaticMarkup(createElement(WorkersTabs, { active: 'routes', onSelect: () => {}, children: 'содержимое' }));
    expect(markup.match(/role="tab"/g)).toHaveLength(WORKERS_TABS.length);
    expect(markup.match(/aria-selected="true"/g)).toHaveLength(1);
    expect(markup.match(/tabindex="0"/g)).toHaveLength(2);
    expect(markup.match(/tabindex="-1"/g)).toHaveLength(WORKERS_TABS.length - 1);
    expect(markup).toContain('role="tabpanel"');
    expect(markup).toContain('data-workers-panel="routes"');
    expect(markup).toContain('содержимое');
    const panel = markup.match(/aria-controls="([^"]+)"/)?.[1];
    expect(panel).toBeDefined();
    expect(markup).toContain(`id="${panel}"`);
  });
});
