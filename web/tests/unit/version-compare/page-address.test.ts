/**
 * «Сравнение версий» reads its object (`UIP-S17-01`: the top strip's, `?project=`), its open set and tab from the address (`UI-B-102`)
 * and draws the installation's AI queue above the tabs (`version-comparison.js:76-79`). The static render cannot press a tab, so the
 * address is a query in the provider.
 */

import { SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { VersionComparePage } from '@/_pages/version-compare';

import { newClient, renderScreen } from '../screens/harness';

import { DOCUMENT_UID, PROJECT_UID, uid } from './fixtures';
import { seedComparison } from './seed';

/** The object is in the address, as the top strip puts it there, unless the case is about an address that names none. */
function bare(query: string, seed: Parameters<typeof seedComparison>[1] = { sheets: true }): string {
  const client = newClient();
  seedComparison(client, seed);
  return renderScreen(client, createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, createElement(VersionComparePage)));
}

function at(query: string, seed: Parameters<typeof seedComparison>[1] = { sheets: true }): string {
  return bare(query === '' ? `project=${PROJECT_UID}` : `project=${PROJECT_UID}&${query}`, seed);
}

describe('«Сравнение версий» and its address', () => {
  it('works in the object of the address, and asks for one in the top strip where the address names none or «Все объекты»', () => {
    expect(at('')).toContain('data-comparison-overview');
    for (const query of ['', 'project=all', `set=${DOCUMENT_UID}&tab=sheets`]) {
      const markup = bare(query);
      expect(markup, query).toContain('Выберите объект в верхней строке');
      expect(markup, query).not.toContain('data-comparison-overview');
      expect(markup, query).not.toContain('data-comparison-sheets');
    }
  });

  it('opens the table with no set in the address', () => {
    const markup = at('');
    expect(markup).toContain('data-comparison-overview');
    expect(markup).not.toContain('data-comparison-sheets');
  });

  it('opens the set and the tab of the address', () => {
    const markup = at(`set=${DOCUMENT_UID}&tab=sheets`);
    expect(markup).toContain('data-comparison-sheets');
    expect(markup).not.toContain('data-comparison-overview');
    expect(markup).toMatch(/data-compare-tab="sheets"[^>]*aria-selected="true"|aria-selected="true"[^>]*data-compare-tab="sheets"/);
  });

  it('keeps the set but shows the table when the address names the table', () => {
    const markup = at(`set=${DOCUMENT_UID}`);
    expect(markup).toContain('data-comparison-overview');
    expect(markup).not.toMatch(/data-compare-tab="sheets"[^>]*disabled/);
  });

  it('says so, and shows the table, when the set of the address is not in the project', () => {
    const markup = at(`set=${uid('doc', 77)}&tab=sheets`);
    expect(markup).toContain('data-compare-unknown-set');
    expect(markup).toContain('Комплект из адреса не найден в этом объекте.');
    expect(markup).toContain('data-comparison-overview');
  });

  it('draws the AI queue strip above the tabs, once', () => {
    const markup = at('');
    const queue = markup.indexOf('data-ai-queue');
    expect(queue).toBeGreaterThan(-1);
    expect(queue).toBeLessThan(markup.indexOf('role="tablist"'));
    expect(markup.split('data-ai-queue').length - 1).toBe(1);
  });
});
