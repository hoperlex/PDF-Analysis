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
  documentFilterOptions,
  documentOptionLabel,
  readSectionOptimisationAddress,
  sectionBackTarget,
  sectionLeadLine,
  withSelectedDocument,
} from '@/_pages/section-optimisation';

import { newClient, renderScreen } from '../screens/harness';
import { SECTION_DOCUMENT_A, SECTION_DOCUMENT_B, SECTION_PROJECT_B, sectionAnswer } from '../section-specification/fixtures';
import { ACCEPTED_PROJECT_B, acceptedKey, acceptedPage, specificationKey } from './fixtures';

function selected(markup: string, value: string): boolean {
  const options = markup.match(/<option[^>]*>/g) ?? [];
  return options.some((tag) => tag.includes(`value="${value}"`) && tag.includes('selected=""'));
}

function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

function page(query: { section?: string; project?: string; tab?: string; document?: string }, client = newClient()): { markup: string; client: ReturnType<typeof newClient> } {
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

describe('the filter «Документ» in the row of the tabs (`UIP-S11-06`)', () => {
  const answer = sectionAnswer();
  const seeded = (query: { section?: string; project?: string; tab?: string; document?: string } = {}, answerFor = answer) => {
    const client = newClient();
    client.setQueryData(specificationKey('AR', (query.project ?? null) as string | null), answerFor);
    return page(query, client);
  };
  const filter = (markup: string): string => {
    const from = markup.indexOf('data-section-document-filter');
    return from === -1 ? '' : markup.slice(from, markup.indexOf('</form>', from));
  };

  it('stands in the row of the tabs, after them and before the panel, once, and offers every document of the scope', () => {
    const { markup } = seeded();
    const at = markup.indexOf('data-section-document-filter');
    expect(at).toBeGreaterThan(markup.indexOf('role="tablist"'));
    expect(at).toBeLessThan(markup.indexOf('role="tabpanel"'));
    expect((markup.match(/data-section-document-filter/g) ?? []).length).toBe(1);
    const html = filter(markup);
    expect(html).toContain('data-section-document-filter="5"');
    expect(html).toContain('<label for="section-specification-document">Документ</label>');
    expect(html).toMatch(/<option value="" selected="">Все документы раздела<\/option>|<option value="">Все документы раздела<\/option>/);
    // «АР-1 · v2»: the document's title and the version of its current one, and the identity is the value.
    expect(html).toContain(`<option value="${SECTION_DOCUMENT_A}">Архитектурные решения · v2</option>`);
    expect(html).toContain(`<option value="${SECTION_DOCUMENT_B}">Архитектурные решения · v1</option>`);
    expect(documentOptionLabel('АР-1', 2)).toBe('АР-1 · v2');
  });

  it('groups the documents under their object while the list holds more than one, so the same title is told apart', () => {
    const html = filter(seeded().markup);
    expect((html.match(/<optgroup/g) ?? []).length).toBe(2);
    expect(html).toContain('<optgroup label="Школа на пятьсот мест">');
    expect(html).toContain('<optgroup label="Детский сад">');
    expect(html.indexOf(`value="${SECTION_DOCUMENT_B}"`)).toBeGreaterThan(html.indexOf('<optgroup label="Детский сад">'));
    // Narrowed to one object the list is that object's, and needs no group.
    const only = sectionAnswer({ project_filter: ACCEPTED_PROJECT_B as never, projects: answer.projects.slice(1) });
    const narrowed = filter(seeded({ project: ACCEPTED_PROJECT_B }, only).markup);
    expect(narrowed).toContain('data-section-document-filter="1"');
    expect(narrowed).not.toContain('<optgroup');
  });

  it('is not drawn where the scope lists no document and none is chosen: nothing to choose, no element', () => {
    expect(page({}).markup).not.toContain('data-section-document-filter');
    const none = sectionAnswer({ projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0 });
    expect(seeded({}, none).markup).not.toContain('data-section-document-filter');
  });

  it('has no list of projects beside it: the label is «Документ», the first option «Все документы раздела»', () => {
    const markup = seeded().markup;
    expect(markup).not.toContain('Все объекты раздела');
    expect(text(filter(markup))).toContain('Документ Все документы раздела');
    expect(text(filter(markup))).not.toContain('Проект');
  });

  it('reads the document of the address into both tabs: their reads carry it, and the document is the one selected', () => {
    const { markup, client } = page({ section: 'AR', project: ACCEPTED_PROJECT_B, document: SECTION_DOCUMENT_B });
    expect(selected(markup, SECTION_DOCUMENT_B)).toBe(true);
    expect(keys(client)).toContainEqual(specificationKey('AR', ACCEPTED_PROJECT_B, SECTION_DOCUMENT_B));
    expect(keys(client)).toContainEqual(acceptedKey({ sectionCode: 'AR', projectUid: ACCEPTED_PROJECT_B, documentUid: SECTION_DOCUMENT_B }));
    // The list is read apart, unnarrowed, so a reader who chose one can choose another.
    expect(keys(client)).toContainEqual(specificationKey('AR', ACCEPTED_PROJECT_B));
    expect(keys(client).filter((key) => (key as string[])[1] === 'accepted')).toHaveLength(1);
  });

  it('with no document chosen asks nothing more: the list is the tabs’ own first read', () => {
    const { client } = page({ section: 'AR', project: ACCEPTED_PROJECT_B });
    expect(keys(client).filter((key) => (key as string[])[1] === 'section-specification')).toHaveLength(1);
    expect(keys(client).filter((key) => (key as string[])[1] === 'accepted')).toEqual([
      acceptedKey({ sectionCode: 'AR', projectUid: ACCEPTED_PROJECT_B }),
    ]);
  });

  it('offers a chosen document before the list is in hand — by its identity, or named by the narrowed answer — and never drops it', () => {
    const byIdentity = filter(page({ document: SECTION_DOCUMENT_B }).markup);
    expect(byIdentity).toContain('data-section-document-filter="1"');
    expect(byIdentity).toContain(`<option value="${SECTION_DOCUMENT_B}" selected="">${SECTION_DOCUMENT_B}</option>`);
    const client = newClient();
    client.setQueryData(specificationKey('AR', null, SECTION_DOCUMENT_B), sectionAnswer({ projects: answer.projects.slice(1) }));
    const named = filter(page({ document: SECTION_DOCUMENT_B }, client).markup);
    expect(named).toContain(`<option value="${SECTION_DOCUMENT_B}" selected="">Архитектурные решения · v1</option>`);
  });

  it('narrows the numbers on the tabs with it: they are the server’s figures for the document', () => {
    const client = newClient();
    client.setQueryData(specificationKey('AR', null, SECTION_DOCUMENT_B), { ...answer, row_count: 2 });
    client.setQueryData(acceptedKey({ sectionCode: 'AR', documentUid: SECTION_DOCUMENT_B }), acceptedPage({ total: 1 }));
    const markup = page({ document: SECTION_DOCUMENT_B }, client).markup;
    const tabs = Object.fromEntries(
      [...markup.matchAll(/<button[^>]*data-section-optimisation-tab="(\w+)"[^>]*>([^<]*)<\/button>/g)].map((match) => [match[1], match[2]]),
    );
    expect(tabs).toEqual({ specification: 'Форма 7 · Спецификация 2', accepted: 'Принято 1' });
  });

  it('opens on the accepted tab narrowed the same way', () => {
    const { markup, client } = page({ section: 'AR', tab: 'accepted', document: SECTION_DOCUMENT_A });
    expect(markup).toContain('data-section-optimisation-panel="accepted"');
    expect(selected(markup, SECTION_DOCUMENT_A)).toBe(true);
    expect(keys(client)).toContainEqual(acceptedKey({ sectionCode: 'AR', documentUid: SECTION_DOCUMENT_A }));
  });

  it('says it set aside a document it cannot read, and opens on every document', () => {
    const { markup } = page({ document: 'doc_nope' });
    expect(markup).toContain('data-address-ignored="document"');
    expect(text(markup)).toContain('Из адреса не прочитано: документ.');
    expect(markup).not.toContain('data-section-document-filter');
  });

  it('keeps the rows of one document the rows of that document: the filter is a read, not a merge', () => {
    // The groups are the document's own, whatever the filter asked for.
    const one = sectionAnswer({ projects: answer.projects.slice(1), rows: { ...answer.rows!, items: answer.rows!.items.slice(4), total: 2 } });
    const client = newClient();
    client.setQueryData(specificationKey('AR', SECTION_PROJECT_B, SECTION_DOCUMENT_B), one);
    const { markup } = page({ project: SECTION_PROJECT_B, document: SECTION_DOCUMENT_B }, client);
    expect(markup).toContain(`data-section-group-row="${SECTION_DOCUMENT_B}"`);
    expect(markup).not.toContain(`data-section-group-row="${SECTION_DOCUMENT_A}"`);
    expect(markup).toContain(`data-section-row-project="${SECTION_PROJECT_B}"`);
  });

  describe('the list, from the answer', () => {
    it('lists the sources of an answer of this section, project by project, and nothing of another section’s answer', () => {
      expect(documentFilterOptions(answer, 'AR').map((option) => [option.documentUid, option.objectName])).toEqual([
        [SECTION_DOCUMENT_A, 'Школа на пятьсот мест'],
        [expect.stringMatching(/^doc_/), 'Школа на пятьсот мест'],
        [expect.stringMatching(/^doc_/), 'Школа на пятьсот мест'],
        [expect.stringMatching(/^doc_/), 'Школа на пятьсот мест'],
        [SECTION_DOCUMENT_B, 'Детский сад'],
      ]);
      expect(documentFilterOptions(answer, 'KJ')).toEqual([]);
      expect(documentFilterOptions(undefined, 'AR')).toEqual([]);
    });

    it('adds the chosen document only when the list lacks it, and names it where it can', () => {
      const all = documentFilterOptions(answer, 'AR');
      expect(withSelectedDocument(all, null, [])).toBe(all);
      expect(withSelectedDocument(all, SECTION_DOCUMENT_A as never, [])).toBe(all);
      const stray = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';
      expect(withSelectedDocument(all, stray as never, [])).toEqual([...all, { documentUid: stray, label: stray, objectName: '' }]);
      const named = [{ documentUid: stray as never, label: 'КЖ-3 · v1', objectName: 'Детский сад' }];
      expect(withSelectedDocument(all, stray as never, named).at(-1)).toEqual(named[0]);
    });
  });
});
