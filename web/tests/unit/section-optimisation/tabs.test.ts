/**
 * `UI-B-22`, `UI-B-27`: «Оптимизация разделов» has two tabs, «Спецификация» and «Принято»; only the open one is mounted.
 * Each tab carries the server's number for the section and project chosen, as the original's «Форма 7 · Спецификация N» and
 * «Принято N», read without opening the tab.
 *
 * Rendered, not read from source (`D-53`): the tablist a reviewer would see and the reads the screen starts.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectSection, SectionSpecification } from '@/shared/api';
import {
  SECTION_OPTIMISATION_TABS,
  SECTION_OPTIMISATION_TAB_LABELS,
  SectionOptimisationPage,
  readSectionOptimisationAddress,
  sectionOptimisationTabText,
} from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { sectionAnswer } from '../section-specification/fixtures';
import { acceptedKey, acceptedPage, specificationKey } from './fixtures';

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

  it('mount nothing of the closed tab; its number is the only thing read for it, and it is the tab own first page', () => {
    expect(markup).toContain('data-section-specification');
    expect(markup).not.toContain('data-section-accepted');
    const keys = client.getQueryCache().getAll().map((query) => query.queryKey as readonly unknown[]);
    expect(keys.filter((key) => key[1] === 'accepted')).toEqual([acceptedKey({ sectionCode: 'AR' })]);
    expect(keys.some((key) => key[1] === 'section-specification')).toBe(true);
  });

  it('only one tab is in the tab order', () => {
    expect(markup.match(/tabindex="0"/g)?.length).toBeGreaterThanOrEqual(2); // the open tab and its panel
    expect(markup).toMatch(/tabindex="-1"[^>]*>|data-section-optimisation-tab="accepted"[^>]*tabindex="-1"|tabindex="-1"[^>]*data-section-optimisation-tab="accepted"/);
  });
});

function tabTexts(markup: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const match of markup.matchAll(/<button[^>]*data-section-optimisation-tab="(\w+)"[^>]*>([^<]*)<\/button>/g)) {
    found[match[1]!] = match[2]!;
  }
  return found;
}

describe('the number on each tab', () => {
  const ready: SectionSpecification = { ...sectionAnswer(), state: 'ready', section_code: 'AR', project_filter: null, row_count: 128 };

  it('is the specification row count and the accepted total the server answered, read without opening the tab', () => {
    const client = newClient();
    client.setQueryData(specificationKey('AR', null), ready);
    client.setQueryData(acceptedKey({ sectionCode: 'AR' }), acceptedPage({ total: 7 }));
    const texts = tabTexts(renderScreen(client, createElement(SectionOptimisationPage)));
    expect(texts).toEqual({ specification: 'Форма 7 · Спецификация 128', accepted: 'Принято 7' });
  });

  it('is the same pair when the other tab is the open one, and follows the project the address names', () => {
    const client = newClient();
    client.setQueryData(specificationKey('KJ', null), { ...ready, section_code: 'KJ', row_count: 9 });
    client.setQueryData(acceptedKey({ sectionCode: 'KJ' }), acceptedPage({ total: 0 }));
    const markup = renderScreen(
      client,
      createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress({ section: 'KJ', tab: 'accepted' }) }),
    );
    expect(markup).toContain('data-section-optimisation-panel="accepted"');
    expect(tabTexts(markup)).toEqual({ specification: 'Форма 7 · Спецификация 9', accepted: 'Принято 0' });
  });

  it('is left off while the read has not answered, and for a specification the server stopped at a bound', () => {
    expect(tabTexts(renderScreen(newClient(), createElement(SectionOptimisationPage)))).toEqual({
      specification: 'Форма 7 · Спецификация',
      accepted: 'Принято',
    });
    const client = newClient();
    client.setQueryData(specificationKey('AR', null), { ...ready, state: 'section_too_large', limit_reason: 'rows', row_count: 0, rows: null });
    client.setQueryData(acceptedKey({ sectionCode: 'AR' }), acceptedPage({ total: 3 }));
    expect(tabTexts(renderScreen(client, createElement(SectionOptimisationPage)))).toEqual({
      specification: 'Форма 7 · Спецификация',
      accepted: 'Принято 3',
    });
  });

  it('never takes the number from another section than the one chosen', () => {
    const client = newClient();
    client.setQueryData(specificationKey('AR', null), ready);
    const markup = renderScreen(client, createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress({ section: 'KJ' }) }));
    expect(tabTexts(markup).specification).toBe('Форма 7 · Спецификация');
  });

  it('says the text from the tab and the figure alone', () => {
    const counts = { specification: 4, accepted: null } as const;
    expect(sectionOptimisationTabText('specification', counts)).toBe('Форма 7 · Спецификация 4');
    expect(sectionOptimisationTabText('accepted', counts)).toBe('Принято');
    const section: ProjectSection = 'AR';
    expect(section).toBe('AR');
  });
});
