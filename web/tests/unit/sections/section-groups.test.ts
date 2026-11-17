/**
 * `UIP-S02-06` (owner rulings Г11, Г12-B, Г1-C): the section's cards by group.
 *
 * A group is a value of the document, not an entity. When at least one document of the section has one, the cards stand by group — a compact
 * heading with the name and the number, «Без группы» last — and the groups are made of the WHOLE listing (read to its end like «Выбрать
 * все»), so a heading's number is the group's own; until the listing is read the page says so, and when a page failed it says that with
 * «Повторить» and draws no group. With no group at all the grid is the plain one, with no heading.
 *
 * Rendered, not read from source (`D-53`): the page over a seeded cache, through the shared harness (`D-97`). The order of the groups
 * is one function; the last test reads the source to hold that, and shows the reading can fail.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { DocumentVersion } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT } from '@/entities/document-version';
import { NO_GROUP_LABEL, SectionDetailPage, groupDocuments, groupOf, orderGroupNames } from '@/_pages/section-detail';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderWith, seedError } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page } from './fixtures';

const key = (cursor: string | undefined) =>
  queryKeys.projects.documents(PROJECT_UID, cursor, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit');

const doc = (suffix: string, group?: string, title = `Документ ${suffix}`): DocumentVersion =>
  otherVersion(suffix, {
    display_title: title,
    classification: classification({ section_code: 'AR' }),
    ...(group === undefined ? {} : { group }),
  });

const render = (client = newClient()) =>
  renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));

const seeded = (items: DocumentVersion[]) => {
  const client = newClient();
  client.setQueryData(key(undefined), page(items, null));
  return client;
};

/** The headings of the groups as the page draws them, in order: the name and the number. */
function headings(markup: string): readonly (readonly [string, number])[] {
  return [...markup.matchAll(/<h2[^>]*><span[^>]*>([^<]*)<\/span><span[^>]*>\((\d+)\)<\/span><\/h2>/g)]
    .map((match) => [match[1] ?? '', Number(match[2])] as const);
}

describe('the groups of a list of documents', () => {
  it('are none while no document has a group', () => {
    expect(groupDocuments([doc('A'), doc('B')])).toBeNull();
    expect(groupDocuments([])).toBeNull();
  });

  it('read a value that is empty or only spaces as no group', () => {
    expect(groupOf(doc('A'))).toBeNull();
    expect(groupOf(doc('A', ''))).toBeNull();
    expect(groupOf(doc('A', '   '))).toBeNull();
    expect(groupOf(doc('A', ' Корпус А '))).toBe('Корпус А');
    expect(groupDocuments([doc('A', '  '), doc('B')])).toBeNull();
  });

  it('stand in alphabetical order, numbers by value, and «Без группы» last and only when a document is in it', () => {
    const groups = groupDocuments([
      doc('A', 'Корпус 10'), doc('B'), doc('C', 'корпус 2'), doc('D', 'Территория'), doc('E', 'Корпус 2 А'), doc('F', 'Благоустройство'),
    ]);
    expect(groups?.map((group) => group.name)).toEqual(['Благоустройство', 'корпус 2', 'Корпус 2 А', 'Корпус 10', 'Территория', null]);
    const grouped = groupDocuments([doc('A', 'Б'), doc('B', 'А')]);
    expect(grouped?.map((group) => group.name)).toEqual(['А', 'Б']);
  });

  it('count their own documents and keep the listing\'s order inside a group', () => {
    const groups = groupDocuments([doc('A', 'Корпус А'), doc('B', 'Корпус Б'), doc('C', 'Корпус А'), doc('D'), doc('E', 'Корпус А')]);
    expect(groups?.map((group) => [group.name, group.documents.length])).toEqual([['Корпус А', 3], ['Корпус Б', 1], [null, 1]]);
    expect(groups?.[0]?.documents.map((version) => version.display_title)).toEqual(['Документ A', 'Документ C', 'Документ E']);
  });

  it('order the names by one function', () => {
    // the Russian collation: Cyrillic names by the alphabet, case no difference, Latin after
    expect(orderGroupNames(['б', 'А', 'a', 'В'])).toEqual(['А', 'б', 'В', 'a']);
  });
});

describe('the section page of a section with groups', () => {
  const items = [doc('A', 'Корпус Б'), doc('B', 'Корпус А'), doc('C'), doc('D', 'Корпус А'), doc('E', 'Корпус Б'), doc('F', 'Корпус А')];

  it('draws a heading with the name and the number over each group\'s cards, «Без группы» last', () => {
    const markup = render(seeded(items));
    expect(headings(markup)).toEqual([['Корпус А', 3], ['Корпус Б', 2], [NO_GROUP_LABEL, 1]]);
    expect(markup).toContain('data-section-groups="3"');
    expect(markup.match(/data-group-count="3"/g)).toHaveLength(1);
    expect(markup).toContain('data-group-kind="none"');
    expect(markup).toContain('data-group-name="Корпус А"');
    // a grid of cards under each heading, with the cards of that group
    expect([...markup.matchAll(/data-document-cards="(\d+)"/g)].map((match) => match[1])).toEqual(['3', '2', '1']);
    expect(markup.indexOf('data-group-name="Корпус А"')).toBeLessThan(markup.indexOf('data-group-name="Корпус Б"'));
    expect(markup.indexOf('data-group-name="Корпус Б"')).toBeLessThan(markup.indexOf('data-group-kind="none"'));
  });

  it('names each group by its heading, for a reader who does not see the frame', () => {
    const markup = render(seeded(items));
    const sections = [...markup.matchAll(/<section[^>]*aria-labelledby="([^"]+)"[^>]*data-group-kind/g)].map((match) => match[1]);
    expect(sections).toHaveLength(3);
    for (const id of sections) expect(markup).toMatch(new RegExp(`<h2[^>]*id="${id}"`));
  });

  it('keeps the Σ card as the first cell of the first group only, and the cards of the group in their own list', () => {
    const markup = render(seeded(items));
    expect(markup.match(/data-grid-leading/g)).toHaveLength(1);
    expect(markup.indexOf('data-grid-leading')).toBeGreaterThan(markup.indexOf('data-group-name="Корпус А"'));
    expect(markup.indexOf('data-grid-leading')).toBeLessThan(markup.indexOf('data-group-name="Корпус Б"'));
    // every document is drawn once
    expect(markup.match(/data-document-uid=/g)).toHaveLength(6);
  });

  it('draws the filters above the groups, and no page to turn', () => {
    const markup = render(seeded(items));
    expect(markup.indexOf('Показать архивные')).toBeGreaterThan(-1);
    expect(markup.indexOf('Показать архивные')).toBeLessThan(markup.indexOf('data-section-groups'));
    expect(markup).not.toContain('am-pager"><button');
    expect(markup).not.toContain('>Далее<');
  });

  it('draws one group, and no «Без группы», when every document is in it', () => {
    const markup = render(seeded([doc('A', 'Корпус А')]));
    expect(headings(markup)).toEqual([['Корпус А', 1]]);
    expect(markup).not.toContain('data-group-kind="none"');
  });

  it('draws a plain grid with no heading while no document has a group', () => {
    const markup = render(seeded([doc('A'), doc('B')]));
    expect(markup).not.toContain('data-section-groups');
    expect(markup).not.toContain('data-group-kind');
    expect(headings(markup)).toEqual([]);
    expect(markup).toContain('data-document-cards="2"');
    expect(markup).not.toContain('data-listing-walk');
  });

  it('is the same to a session that cannot act as an expert', () => {
    const client = seeded(items);
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    expect(headings(render(client))).toEqual([['Корпус А', 3], ['Корпус Б', 2], [NO_GROUP_LABEL, 1]]);
  });
});

describe('a section of more than one page', () => {
  const FIRST = [doc('A', 'Корпус Б'), doc('B', 'Корпус А')];
  const SECOND = [doc('C', 'Корпус А'), doc('D'), doc('E', 'Корпус А')];

  it('draws the groups of the whole listing, with their full numbers, and no page to turn', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST, 'c2'));
    client.setQueryData(key('c2'), page(SECOND, null));
    const markup = render(client);
    // the first page held one of «Корпус А», the whole listing holds three
    expect(headings(markup)).toEqual([['Корпус А', 3], ['Корпус Б', 1], [NO_GROUP_LABEL, 1]]);
    expect(markup).not.toContain('data-listing-walk');
    expect(markup).not.toContain('>Далее<');
    expect(markup.match(/data-document-uid=/g)).toHaveLength(5);
  });

  it('draws the groups for a session that cannot act as an expert as well, and offers it no choice', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    client.setQueryData(key(undefined), page(FIRST, 'c2'));
    client.setQueryData(key('c2'), page(SECOND, null));
    const markup = render(client);
    expect(headings(markup)).toEqual([['Корпус А', 3], ['Корпус Б', 1], [NO_GROUP_LABEL, 1]]);
    expect(markup).not.toContain('data-select-all');
  });

  it('says the pages are being read, and draws no group from a part of the listing', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST, 'c2'));
    const markup = render(client);
    expect(markup).toMatch(/<p[^>]*role="status"[^>]*data-listing-walk="pending"[^>]*><span[^>]*>Читаю все страницы раздела…<\/span><\/p>/);
    // `UIP-DEBT-02`: an expert's page has the choosing waiting for the same walk, and still says it once.
    expect(markup.match(/Читаю все страницы раздела/g)).toHaveLength(1);
    expect(markup).not.toContain('data-section-groups');
    expect(headings(markup)).toEqual([]);
    // the page's own cards stay, plain, with the way to the next page
    expect(markup).toContain('data-document-cards="2"');
    expect(markup).toContain('>Далее<');
  });

  it('says a page it could not read, offers to try again, and draws no group', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST, 'c2'));
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, key('c2'), new ApiError(503, {
      contract_version: '1.59.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = render(client);
    expect(markup).toMatch(/data-listing-walk="failed"[^]*Не удалось прочитать все страницы раздела[^]*>Повторить<\/button>/);
    expect(markup.match(/>Повторить<\/button>/g)).toHaveLength(1);
    expect(markup).not.toContain('data-section-groups');
    expect(headings(markup)).toEqual([]);
    expect(markup).not.toContain('data-listing-walk="pending"');
  });

  it('keeps the narrowing of the page: the groups of «не запускались» are those of that listing', () => {
    const client = newClient();
    const narrowed = (cursor: string | undefined) =>
      queryKeys.projects.documents(PROJECT_UID, cursor, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, 'not_run', 'audit');
    client.setQueryData(narrowed(undefined), page([doc('A', 'Корпус А')], 'c2'));
    client.setQueryData(narrowed('c2'), page([doc('B', 'Корпус А'), doc('C')], null));
    const markup = renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR', filter: 'not_run' }));
    expect(headings(markup)).toEqual([['Корпус А', 2], [NO_GROUP_LABEL, 1]]);
    // the sentence over the list counts the whole listing now, and says it is whole
    expect(markup).toContain('Показаны документы, которые не анализировались: 3');
    expect(markup).not.toContain('на этой странице');
  });
});

describe('the order of the groups is decided in one place', () => {
  const read = (path: string) => readFileSync(join(WEB_ROOT, 'src/_pages/section-detail', path), 'utf8');
  const sorts = (source: string) => source.replace(/\/\*[^]*?\*\//g, '').replace(/\/\/.*$/gm, '').match(/\.sort\(|\.toSorted\(|\.reverse\(/g) ?? [];

  it('is orderGroupNames, and nothing that draws the groups sorts them again', () => {
    expect(sorts(read('model/group-documents.ts'))).toHaveLength(1);
    expect(read('model/group-documents.ts')).toMatch(/export function orderGroupNames/);
    for (const file of ['ui/section-groups.tsx', 'ui/section-detail-page.tsx']) expect(sorts(read(file)), file).toHaveLength(0);
  });

  it('can fail: a second sort in a drawing file is read as one', () => {
    expect(sorts('const x = groups.sort((a, b) => 0);')).toHaveLength(1);
    expect(sorts('// groups.sort()\nconst x = 1;')).toHaveLength(0);
  });
});
