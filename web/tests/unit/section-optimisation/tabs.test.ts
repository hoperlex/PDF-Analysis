/**
 * `UI-B-22`, `UI-B-27`: «Оптимизация разделов» has two tabs, «Спецификация» and «Принято»; only the open one is mounted.
 *
 * Rendered, not read from source (`D-53`): the tablist a reviewer would see and the reads the screen starts.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SECTION_OPTIMISATION_TABS, SECTION_OPTIMISATION_TAB_LABELS, SectionOptimisationPage } from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';

describe('the tabs of «Оптимизация разделов»', () => {
  const client = newClient();
  const markup = renderScreen(client, createElement(SectionOptimisationPage));

  it('are «Спецификация» and «Принято», the specification open', () => {
    expect([...SECTION_OPTIMISATION_TABS]).toEqual(['specification', 'accepted']);
    expect(SECTION_OPTIMISATION_TAB_LABELS).toEqual({ specification: 'Спецификация', accepted: 'Принято' });
    expect(markup).toContain('role="tablist"');
    expect(markup).toMatch(/aria-selected="true"[^>]*data-section-optimisation-tab="specification"/);
    expect(markup).toMatch(/aria-selected="false"[^>]*data-section-optimisation-tab="accepted"/);
    expect(markup).toContain('data-section-optimisation-panel="specification"');
  });

  it('mount nothing of the closed tab, so it reads nothing', () => {
    expect(markup).toContain('data-section-specification');
    expect(markup).not.toContain('data-section-accepted');
    const keys = client.getQueryCache().getAll().map((query) => query.queryKey as readonly unknown[]);
    expect(keys.filter((key) => key[1] === 'accepted')).toEqual([]);
    expect(keys.some((key) => key[1] === 'section-specification')).toBe(true);
  });

  it('only one tab is in the tab order', () => {
    expect(markup.match(/tabindex="0"/g)?.length).toBeGreaterThanOrEqual(2); // the open tab and its panel
    expect(markup).toMatch(/tabindex="-1"[^>]*>|data-section-optimisation-tab="accepted"[^>]*tabindex="-1"|tabindex="-1"[^>]*data-section-optimisation-tab="accepted"/);
  });
});
