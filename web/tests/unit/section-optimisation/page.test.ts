/**
 * `UI-B-20`, `UI-B-22`, `UIP-S11-01`: «Оптимизация раздела» opens on the section, the project and the tab its address names, with
 * the section's header: «←», the badge, «Уровень раздела», the heading and the list of sections, one line of what the screen holds
 * and the long paragraph behind «ⓘ». There is no list of projects: the object is the top strip's (see `object-scope.test.ts`).
 *
 * Rendered, not read from source (`D-53`): the header and the list a reviewer would see and the reads the screen starts.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectUid } from '@/shared/api';
import {
  SECTION_ABOUT_TEXT,
  SectionOptimisationPage,
  readSectionOptimisationAddress,
  sectionBackTarget,
  sectionLeadLine,
} from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { ACCEPTED_PROJECT_B, acceptedKey, specificationKey } from './fixtures';

function selected(markup: string, value: string): boolean {
  const options = markup.match(/<option[^>]*>/g) ?? [];
  return options.some((tag) => tag.includes(`value="${value}"`) && tag.includes('selected=""'));
}

function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

function page(query: { section?: string; project?: string; tab?: string }, client = newClient()): { markup: string; client: ReturnType<typeof newClient> } {
  const markup = renderScreen(
    client,
    createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress(query) }),
  );
  return { markup, client };
}

const keys = (client: ReturnType<typeof newClient>): readonly unknown[] =>
  client.getQueryCache().getAll().map((query) => query.queryKey);

describe('opening on the address', () => {
  it('opens on the section and the project the address names, and reads exactly that', () => {
    const { markup, client } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B });
    expect(selected(markup, 'KJ')).toBe(true);
    expect(selected(markup, 'AR')).toBe(false);
    expect(keys(client)).toContainEqual(specificationKey('KJ', ACCEPTED_PROJECT_B));
    expect(keys(client)).not.toContainEqual(specificationKey('AR', null));
  });

  it('has no list of projects, whatever the address names, and reads no project to fill one', () => {
    for (const query of [{}, { project: ACCEPTED_PROJECT_B }, { section: 'KJ', project: 'all' }]) {
      const { markup, client } = page(query);
      expect(markup).not.toContain('data-section-project-filter');
      expect(markup).not.toContain('section-specification-project');
      expect(markup).not.toContain('Все объекты раздела');
      // The reads of the screen are the two tabs' own, and the account's: not the project's (`getProject`) nor the list of projects.
      expect(keys(client).filter((key) => (key as string[])[0] === 'projects')).toEqual([]);
    }
  });

  it('keeps the old behaviour without an address: АР, every project', () => {
    const { markup, client } = page({});
    expect(selected(markup, 'AR')).toBe(true);
    expect(keys(client)).toContainEqual(specificationKey('AR', null));
    expect(markup).not.toContain('data-address-ignored');
  });

  it('sets aside what it cannot read and says so', () => {
    const { markup } = page({ section: 'ZZ', project: 'nope', tab: 'history' });
    expect(markup).toContain('data-address-ignored="section project tab"');
    expect(text(markup)).toContain('Из адреса не прочитано: раздел, объект, вкладка.');
    expect(selected(markup, 'AR')).toBe(true);
  });
});

describe('the header (`UIP-S11-01`)', () => {
  const { markup } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B });
  const header = markup.slice(markup.indexOf('<header'), markup.indexOf('</header>'));

  it('is «←», the section\u2019s badge, «Уровень раздела» and «Оптимизация раздела», in that order, over the tabs', () => {
    expect(header).toContain('data-section-optimisation-header');
    const at = ['←', 'data-section-badge="KJ"', 'Уровень раздела', '<h1', 'Оптимизация раздела</h1>'].map((part) => header.indexOf(part));
    expect(at.every((index) => index > -1)).toBe(true);
    expect([...at].sort((a, b) => a - b)).toEqual(at);
    expect(text(header)).toContain('КЖ');
    expect(markup.indexOf('</header>')).toBeLessThan(markup.indexOf('role="tablist"'));
    expect((markup.match(/<h1/g) ?? []).length).toBe(1);
  });

  it('holds the list of sections, once, and nothing else to choose by', () => {
    expect(header).toContain('data-section-filter-bar');
    expect((markup.match(/data-section-picker=/g) ?? []).length).toBe(1);
    expect((header.match(/<select/g) ?? []).length).toBe(1);
  });

  it('says what the screen holds in one line, and keeps the long paragraph behind «ⓘ», closed', () => {
    const lead = /<p[^>]*data-section-lead[^>]*>([^<]*)<\/p>/.exec(header)?.[1] ?? '';
    expect(lead).toBe('Конструкции железобетонные · документы выбранного объекта');
    expect(lead).not.toContain('Экран только показывает данные');
    expect(header).toMatch(/<button[^>]*aria-expanded="false"[^>]*data-section-about-toggle[^>]*>ⓘ<\/button>/);
    expect(header).toContain('aria-label="Что показывает экран"');
    // The paragraph is in the markup, hidden, and the button names it.
    const about = /<p id="([^"]+)"[^>]*hidden=""[^>]*data-section-about[^>]*>([^<]*)<\/p>/.exec(header);
    expect(about).not.toBeNull();
    expect(about?.[2]).toBe(SECTION_ABOUT_TEXT);
    expect(header).toContain(`aria-controls="${about?.[1]}"`);
    expect(SECTION_ABOUT_TEXT).toContain('Экран только показывает данные');
  });

  it('says every object in the line when the screen follows none', () => {
    expect(sectionLeadLine('Архитектурные решения', null)).toBe('Архитектурные решения · документы раздела по всем объектам');
    expect(text(page({ section: 'AR', project: 'all' }).markup)).toContain('Архитектурные решения · документы раздела по всем объектам');
  });

  it('has the way back where the reader came from, in the arrow', () => {
    expect(sectionBackTarget(ACCEPTED_PROJECT_B as ProjectUid, 'KJ')).toEqual({
      kind: 'section',
      href: `/projects/${ACCEPTED_PROJECT_B}/sections/KJ`,
      label: 'К разделу объекта',
    });
    expect(sectionBackTarget(null, 'KJ')).toEqual({ kind: 'dashboard', href: '/dashboard', label: 'К дашборду' });
  });
});

describe('the section is chosen in the header, the object in the top strip', () => {
  it('has the list of sections before the tabs and none of its own in either tab', () => {
    for (const tab of ['specification', 'accepted'] as const) {
      const { markup } = page({ tab });
      const bar = markup.indexOf('data-section-filter-bar');
      expect(bar).toBeGreaterThan(markup.indexOf('<header'));
      expect(bar).toBeLessThan(markup.indexOf('role="tablist"'));
      expect((markup.match(/data-section-filter-bar/g) ?? []).length).toBe(1);
      expect((markup.match(/data-section-picker=/g) ?? []).length).toBe(1);
      expect(markup.slice(markup.indexOf('role="tabpanel"'))).not.toContain('<select');
    }
  });

  it('is the same choice for both tabs: the section of the address is selected on either', () => {
    for (const tab of ['specification', 'accepted'] as const) {
      const { markup } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B, tab });
      expect(selected(markup, 'KJ')).toBe(true);
    }
  });
});

describe('the tabs', () => {
  it('opens «Спецификация» by default and mounts nothing of «Принято», whose number is the only thing read for it', () => {
    const { markup, client } = page({});
    expect(markup).toContain('data-section-optimisation-panel="specification"');
    expect(markup).toMatch(/aria-selected="true"[^>]*data-section-optimisation-tab="specification"/);
    expect(markup).toContain('data-section-specification');
    expect(markup).not.toContain('data-section-accepted');
    // The tab's number (`UI-B-22`) is the accepted list's own first page: the key the open tab would read.
    expect(keys(client).filter((key) => (key as string[])[1] === 'accepted')).toEqual([acceptedKey({ sectionCode: 'AR' })]);
  });

  it('opens «Принято» on the section and project of the address; the specification is read for its number only', () => {
    const { markup, client } = page({ section: 'KJ', project: ACCEPTED_PROJECT_B, tab: 'accepted' });
    expect(markup).toContain('data-section-optimisation-panel="accepted"');
    expect(markup).toContain('data-section-accepted');
    expect(markup).not.toContain('data-section-specification');
    expect(selected(markup, 'KJ')).toBe(true);
    expect(keys(client)).toContainEqual(acceptedKey({ sectionCode: 'KJ', projectUid: ACCEPTED_PROJECT_B }));
    // The specification tab is not mounted, but its number is read under the key the tab itself would use (once, whichever
    // tab is open), for the section and project chosen and for no other.
    expect(keys(client)).toContainEqual(specificationKey('KJ', ACCEPTED_PROJECT_B));
    expect(keys(client).filter((key) => (key as string[])[1] === 'section-specification')).toHaveLength(1);
  });

  it('names both tabs', () => {
    const said = text(page({}).markup);
    expect(said).toContain('Спецификация');
    expect(said).toContain('Принято');
  });
});
