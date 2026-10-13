/**
 * The two tabs of «Блоки» (`W55B-WEB-BLOCKS`): the WAI-ARIA tabs pattern in the markup, and
 * the keyboard contract as the pure function the buttons call.
 *
 * This suite cannot fire a key event (no DOM), so the keyboard half is asserted on
 * `tabAfterKey`, which is the whole of what a key press decides; the markup half is asserted
 * on the rendered tabs in each of the two states.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { BLOCK_TABS, BLOCK_TAB_LABELS, DEFAULT_BLOCK_TAB, VersionBlockViews, tabAfterKey } from '@/_pages/blocks';
import type { BlockTab } from '@/_pages/blocks';
import { portalBlocksQueryOptions } from '@/entities/block';
import { queryKeys } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import { BLOCKS_VERSION_UID, blocksVersion, notProducedPage } from './fixtures';

function tabs(tab: BlockTab): string {
  const client = newClient();
  client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, { pages: [notProducedPage()], pageParams: [undefined] });
  client.setQueryData(queryKeys.versions.blocks(BLOCKS_VERSION_UID), {
    version_uid: BLOCKS_VERSION_UID, status: 'not_produced', produced_by_run_id: null, block_count: 0, blocks: [],
  });
  return renderScreen(client, createElement(VersionBlockViews, { version: blocksVersion(true), tab, onTab: () => {} }));
}

/** Every `<tag ...>` opening tag carrying `attribute`, as attribute maps. */
function elements(markup: string, attribute: string): Map<string, string>[] {
  return [...markup.matchAll(new RegExp(`<[a-z]+\\b[^>]*\\s${attribute}="[^"]*"[^>]*>`, 'g'))].map((m) => {
    const attrs = new Map<string, string>();
    for (const a of m[0].matchAll(/\s([a-zA-Z-]+)(?:="([^"]*)")?/g)) attrs.set(a[1] as string, a[2] ?? '');
    return attrs;
  });
}

describe('the keyboard moves between the two tabs', () => {
  it('opens on «Блоки портала»', () => {
    expect(DEFAULT_BLOCK_TAB).toBe('portal');
    expect(BLOCK_TABS[0]).toBe('portal');
    expect(BLOCK_TAB_LABELS).toEqual({ portal: 'Блоки портала', lines: 'Строки текста' });
  });

  it('wraps on the arrows, jumps on Home and End, and ignores every other key', () => {
    expect(tabAfterKey('portal', 'ArrowRight')).toBe('lines');
    expect(tabAfterKey('lines', 'ArrowRight')).toBe('portal');
    expect(tabAfterKey('portal', 'ArrowLeft')).toBe('lines');
    expect(tabAfterKey('lines', 'ArrowLeft')).toBe('portal');
    expect(tabAfterKey('lines', 'Home')).toBe('portal');
    expect(tabAfterKey('portal', 'End')).toBe('lines');
    for (const key of ['Enter', ' ', 'Tab', 'ArrowDown', 'ArrowUp', 'a']) {
      expect(tabAfterKey('portal', key)).toBeNull();
    }
  });
});

describe('the tabs carry the WAI-ARIA tabs pattern', () => {
  for (const active of BLOCK_TABS) {
    it(`marks «${BLOCK_TAB_LABELS[active]}» as the open tab, and only it`, () => {
      const markup = tabs(active);
      expect(markup).toContain('role="tablist"');
      const tabList = elements(markup, 'role').filter((a) => a.get('role') === 'tab');
      const panels = elements(markup, 'role').filter((a) => a.get('role') === 'tabpanel');
      expect(tabList).toHaveLength(2);
      expect(panels).toHaveLength(2);

      for (const tab of tabList) {
        const which = tab.get('data-block-tab') as BlockTab;
        const open = which === active;
        expect(tab.get('aria-selected')).toBe(open ? 'true' : 'false');
        expect(tab.get('tabindex')).toBe(open ? '0' : '-1');
        const panel = panels.find((p) => p.get('id') === tab.get('aria-controls'));
        expect(panel, `${which} controls no panel`).toBeDefined();
        expect(panel?.get('aria-labelledby')).toBe(tab.get('id'));
        expect(panel?.get('data-block-panel')).toBe(which);
        expect(panel?.has('hidden')).toBe(!open);
      }
      expect(markup).toContain(`>${BLOCK_TAB_LABELS.portal}<`);
      expect(markup).toContain(`>${BLOCK_TAB_LABELS.lines}<`);
    });
  }

  it('mounts only the open tab’s content', () => {
    const portal = tabs('portal');
    expect(portal).toContain('Блоки портала появятся после первого запуска анализа этой версии.');
    expect(portal).not.toContain('Разметка блоков для этой версии ещё не построена.');

    const lines = tabs('lines');
    expect(lines).toContain('Разметка блоков для этой версии ещё не построена.');
    expect(lines).toContain('Векторный граф блока здесь пока не строится');
    expect(lines).not.toContain('Блоки портала появятся после первого запуска');
  });
});
