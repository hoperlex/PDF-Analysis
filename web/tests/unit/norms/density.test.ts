/**
 * Lane N1 — «Нормы» as a dense screen: the two views and the snapshot they read on one line, a search whose help is
 * folded, a result with its way into the PDF on its first line, a catalogue whose filters can be reset, and the empty
 * states that carry the action that helps. Rendered in one static pass over seeded caches, as `norms-screen.test.ts` does.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { NormDocumentPage, NormsPage } from '@/_pages/norms';
import { NORM_CATALOGUE_PAGE_LIMIT, NORM_EVENT_PAGE_LIMIT, NORM_SNAPSHOT_LIMIT } from '@/entities/norms';
import { NormCatalogueTable } from '@/widgets/norm-catalogue';
import { NormDocumentFacts, NormParagraphList } from '@/widgets/norm-document';
import { NormSearchResults } from '@/widgets/norm-search';
import { NormSnapshotHistory, NormSnapshotList, shortSnapshotKey } from '@/widgets/norm-snapshots';

import { newClient, renderScreen } from '../screens/harness';
import {
  NORM_CATALOGUE_ITEMS, NORM_CATALOGUE_PAGE, NORM_DOCUMENT_ID, NORM_EVENTS, NORM_HITS, NORM_PARAGRAPHS, NORM_SNAPSHOTS,
  normDocument,
} from './fixtures';

const SNAPSHOTS = queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT);
const EVENTS = queryKeys.norms.events(undefined, NORM_EVENT_PAGE_LIMIT);
const LAST = { next_cursor: null };

function page(options: {
  readonly roles?: readonly string[];
  readonly query?: string | null;
  readonly catalogue?: { q: string | null; kind: string | null } | null;
  readonly seed?: (client: ReturnType<typeof newClient>) => void;
}): string {
  const client = newClient();
  client.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
  client.setQueryData(EVENTS, { items: [], page: LAST });
  options.seed?.(client);
  return renderScreen(client, createElement(NormsPage, {
    roles: options.roles ?? ['expert'], query: options.query ?? null, catalogue: options.catalogue ?? null,
  }));
}

/** The line over the screen: from its label to the end of its section. */
function barOf(markup: string): string {
  const start = markup.indexOf('aria-label="Текущий снимок норм"');
  return markup.slice(start, markup.indexOf('</section>', start));
}

describe('the line over «Нормы»: the views and the snapshot they read', () => {
  it('holds the views and the snapshot status in one section, the key shortened with the whole key in its title', () => {
    const bar = barOf(page({}));
    expect(bar).toContain('data-norm-view="search"');
    expect(bar).toContain('data-norm-current="current"');
    const key = NORM_SNAPSHOTS[0]?.content_key ?? '';
    expect(bar).toContain(`title="${key}"`);
    expect(bar).toContain(`>${shortSnapshotKey(key)}<`);
    expect(bar).not.toContain(`>${key}<`);
    expect(shortSnapshotKey(key)).toHaveLength(13);
    expect(shortSnapshotKey('abc')).toBe('abc');
  });

  it('can fail: the status is not drawn as a note block any more, and no second panel carries it', () => {
    const markup = page({});
    expect(markup).not.toMatch(/<p[^>]*class="am-note"[^>]*data-norm-current/);
    expect(markup.match(/data-norm-current=/g)).toHaveLength(1);
  });

  it('says the refusal before a snapshot is current once, in the line, on the catalogue view too', () => {
    const none = (c: ReturnType<typeof newClient>) => c.setQueryData(SNAPSHOTS, { items: [], page: LAST });
    for (const catalogue of [null, { q: null, kind: null }]) {
      const markup = page({ seed: none, catalogue });
      expect(markup.match(/data-norms-refusal="no_current_snapshot"/g)).toHaveLength(1);
      expect(barOf(markup)).toContain('data-norms-refusal="no_current_snapshot"');
    }
  });
});

describe('the search: help folded, the way into the PDF on the first line of a result', () => {
  it('folds the help into a details element and keeps the field and its button', () => {
    const markup = page({});
    expect(markup).toMatch(/<details[^>]*><summary>Что ищется<\/summary>/);
    expect(markup).toContain('абзацы с ненадёжно распознанным текстом в поиск не');
    expect(markup).toContain('id="norms-query"');
    expect(markup).toContain('>Найти</button>');
  });

  it('counts the results of the page, and says more are behind «Дальше» only when they are', () => {
    const more = renderScreen(newClient(), createElement(NormSearchResults, { items: NORM_HITS, onFirst: null, onNext: () => {} }));
    expect(more).toContain('data-norm-hits-count="2"');
    expect(more).toContain('Найдено на этой странице: 2; следующие — по кнопке «Дальше».');
    const last = renderScreen(newClient(), createElement(NormSearchResults, { items: NORM_HITS, onFirst: null, onNext: null }));
    expect(last).toContain('Найдено на этой странице: 2.');
    expect(last).not.toContain('«Дальше»');
  });

  it('puts «Открыть» in the head of the result, before its fragment', () => {
    const markup = renderScreen(newClient(), createElement(NormSearchResults, { items: NORM_HITS, onFirst: null, onNext: null }));
    const hit = markup.slice(markup.indexOf('data-norm-hit='), markup.indexOf('</li>'));
    expect(hit.indexOf('>Открыть<')).toBeGreaterThan(-1);
    expect(hit.indexOf('>Открыть<')).toBeLessThan(hit.indexOf('<blockquote'));
  });

  it('an empty first page says nothing was found and offers to clear the search; a page with results offers no such thing', () => {
    const none = renderScreen(newClient(), createElement(NormSearchResults, { items: [], onFirst: null, onNext: null }));
    expect(none).toContain('Ничего не найдено');
    const tag = /<a[^>]*data-norm-search-reset=""[^>]*>/.exec(none)?.[0] ?? '';
    expect(tag).toContain('href="/norms"');
    expect(none).toContain('>Сбросить поиск</a>');
    const found = renderScreen(newClient(), createElement(NormSearchResults, { items: NORM_HITS, onFirst: null, onNext: null }));
    expect(found).not.toContain('data-norm-search-reset');
  });

  it('an empty later page names the way back inside the state, once', () => {
    const markup = renderScreen(newClient(), createElement(NormSearchResults, { items: [], onFirst: () => {}, onNext: null }));
    expect(markup).toContain('На этой странице результатов нет');
    expect(markup.match(/В начало/g)).toHaveLength(1);
    expect(markup).not.toContain('data-norm-hits-count');
  });
});

describe('the catalogue: filters that can be reset, a table Tab reaches', () => {
  const FILTERED = queryKeys.norms.catalogue('СП 54', 'СП', undefined, NORM_CATALOGUE_PAGE_LIMIT);
  const PLAIN = queryKeys.norms.catalogue(undefined, undefined, undefined, NORM_CATALOGUE_PAGE_LIMIT);

  it('offers «Сбросить фильтры» in the form only while a filter is applied', () => {
    const filtered = page({
      catalogue: { q: 'СП 54', kind: 'СП' },
      seed: (c) => c.setQueryData(FILTERED, { ...NORM_CATALOGUE_PAGE, items: [NORM_CATALOGUE_ITEMS[1]], total: 1, page: LAST }),
    });
    expect(filtered).toContain('data-norm-catalogue-reset=""');
    expect(filtered).toContain('Сбросить фильтры');
    const plain = page({ catalogue: { q: null, kind: null }, seed: (c) => c.setQueryData(PLAIN, NORM_CATALOGUE_PAGE) });
    expect(plain).not.toContain('data-norm-catalogue-reset');
  });

  it('an empty answer under a filter says so and offers the reset; an empty snapshot offers none', () => {
    const narrowed = renderScreen(newClient(), createElement(NormCatalogueTable, { items: [], total: 0, filtered: true, onFirst: null, onNext: null }));
    expect(narrowed).toContain('Под этот отбор документов нет');
    expect(narrowed).toContain('data-norm-catalogue-reset=""');
    expect(narrowed).toContain('href="/norms?view=catalogue"');
    const empty = renderScreen(newClient(), createElement(NormCatalogueTable, { items: [], total: 0, filtered: false, onFirst: null, onNext: null }));
    expect(empty).toContain('В текущем снимке нет документов');
    expect(empty).not.toContain('data-norm-catalogue-reset');
  });

  it('draws the table in a named, focusable region, and says how many rows the page holds of the total', () => {
    const markup = renderScreen(newClient(), createElement(NormCatalogueTable, {
      items: NORM_CATALOGUE_ITEMS, total: 3, filtered: false, onFirst: null, onNext: () => {},
    }));
    expect(markup).toMatch(/<div[^>]*role="region"[^>]*aria-label="Каталог нормативных документов, таблица"[^>]*tabindex="0"/);
    expect(markup).toContain('Документов в текущем снимке: 3. На странице: 2.');
    const whole = renderScreen(newClient(), createElement(NormCatalogueTable, {
      items: NORM_CATALOGUE_ITEMS, total: 2, filtered: false, onFirst: null, onNext: null,
    }));
    expect(whole).toContain('Документов в текущем снимке: 2.');
    expect(whole).not.toContain('На странице:');
  });
});

describe('the snapshots and their history: a row is a line or two, not six paragraphs', () => {
  const list = () => renderScreen(newClient(), createElement(NormSnapshotList, {
    items: NORM_SNAPSHOTS, current: { kind: 'current', snapshot: NORM_SNAPSHOTS[0]! }, canDesignate: true, busy: false, onDesignate: () => {},
  }));
  const rows = (markup: string) => markup.split('<li ').slice(1).map((row) => `<li ${row.slice(0, row.indexOf('</li>'))}`);

  it('keeps the attributes the journey addresses and puts the control on the first line, before the counts', () => {
    const [current = '', qualified = '', incomplete = ''] = rows(list());
    expect(current).toContain('data-norm-snapshot-current="true"');
    expect(current).not.toContain('<button');
    expect(qualified).toContain('data-norm-snapshot-qualified="true"');
    expect(qualified.indexOf('>Сделать текущим<')).toBeGreaterThan(-1);
    expect(qualified.indexOf('>Сделать текущим<')).toBeLessThan(qualified.indexOf('Документов:'));
    expect(qualified).toContain('Может стать текущим.');
    expect(incomplete).toContain('data-norm-snapshot-qualified="false"');
    expect(incomplete).toContain('Нельзя сделать текущим: поисковый индекс построен не полностью.');
    expect(incomplete).not.toContain('<button');
  });

  it('counts the paragraphs, names the index and shortens the content key, keeping the whole key in the title', () => {
    const [current = ''] = rows(list());
    const key = NORM_SNAPSHOTS[0]?.content_key ?? '';
    expect(current).toContain('Документов: 674. Абзацев: 191204, из них с ненадёжно распознанным текстом: 312.');
    expect(current).toContain('Поисковый индекс:');
    expect(current).toContain(`title="${key}"`);
    expect(current).not.toContain(`>${key}<`);
    // Six paragraphs became two.
    expect(current.match(/<p[ >]/g)).toHaveLength(2);
  });

  it('draws a designation on one line: when, what changed, who did it', () => {
    const markup = renderScreen(newClient(), createElement(NormSnapshotHistory, { items: NORM_EVENTS, onFirst: null, onNext: null }));
    const [first = '', second = ''] = rows(markup);
    expect(first).toContain('Вместо <code>');
    expect(first).toContain('Назначил <code>');
    expect(second).toContain('Назначен первый текущий снимок ');
    expect(first).not.toContain('<p');
    expect(markup.match(/data-norm-event=/g)).toHaveLength(2);
  });
});

describe('one norm document: facts on a line, paragraphs with their page beside them', () => {
  it('prints the facts of the document in one paragraph and keeps what the journey reads', () => {
    const markup = renderScreen(newClient(), createElement(NormDocumentFacts, { document: normDocument() }));
    expect(markup).toContain(`data-norm-document="${NORM_DOCUMENT_ID}"`);
    expect(markup).toContain('Страниц в PDF: 48. Абзацев: 412.');
    expect(markup).toContain('Вид документа: СП');
    expect(markup).toContain('Редакция от <time datetime="2022-05-13">2022-05-13</time>');
    expect(markup.match(/<p[ >]/g)).toHaveLength(4);
    const undated = renderScreen(newClient(), createElement(NormDocumentFacts, { document: normDocument({ drawn_on: null, unreliable_paragraph_count: 0 }) }));
    expect(undated).not.toContain('Редакция от');
    expect(undated).not.toContain('data-norm-unreliable-count');
  });

  it('counts the paragraphs of the page, and stands the pager over a long list as well as under it', () => {
    const many = Array.from({ length: 12 }, (_, index) => ({ ...NORM_PARAGRAPHS[1]!, norm_paragraph_id: `npar_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(index).padStart(2, '0')}` }));
    const long = renderScreen(newClient(), createElement(NormParagraphList, { normDocumentId: NORM_DOCUMENT_ID, items: many, onFirst: () => {}, onNext: () => {} }));
    expect(long).toContain('Абзацев на этой странице: 12; дальше — по кнопке «Дальше».');
    expect(long.match(/>Дальше</g)).toHaveLength(2);
    const short = renderScreen(newClient(), createElement(NormParagraphList, { normDocumentId: NORM_DOCUMENT_ID, items: NORM_PARAGRAPHS, onFirst: null, onNext: () => {} }));
    expect(short).toContain('Абзацев на этой странице: 3; дальше');
    expect(short.match(/>Дальше</g)).toHaveLength(1);
  });

  it('an empty later page carries the way back inside its state', () => {
    const markup = renderScreen(newClient(), createElement(NormParagraphList, { normDocumentId: NORM_DOCUMENT_ID, items: [], onFirst: () => {}, onNext: null }));
    expect(markup).toContain('На этой странице абзацев нет');
    expect(markup.match(/В начало/g)).toHaveLength(1);
    expect(markup).not.toContain('data-norm-paragraphs-count');
  });

  it('draws the closed PDF as one line under the facts, and an opened page as a panel of its own', () => {
    const seeded = newClient();
    seeded.setQueryData(queryKeys.norms.document(NORM_DOCUMENT_ID), normDocument());
    seeded.setQueryData(queryKeys.norms.paragraphs(NORM_DOCUMENT_ID, undefined, 200), {
      items: NORM_PARAGRAPHS, page: LAST, source_attribution: 'consultant_plus',
    });
    const closed = renderScreen(seeded, createElement(NormDocumentPage, { normDocumentId: NORM_DOCUMENT_ID, page: null }));
    expect(closed).toContain('data-norm-pdf="closed"');
    expect(closed).not.toContain('data-norm-pdf-page');
    expect(closed.match(/aria-label="PDF документа"/g)).toHaveLength(1);
    const opened = renderScreen(seeded, createElement(NormDocumentPage, { normDocumentId: NORM_DOCUMENT_ID, page: 49 }));
    expect(opened).toContain('data-norm-pdf-page="49"');
    expect(opened.match(/aria-label="PDF документа"/g)).toHaveLength(1);
    expect(opened).toContain('Такой страницы в документе нет');
    // Both addresses back are on the page.
    expect(closed).toContain('К поиску по нормам');
    expect(closed).toContain('К каталогу норм');
  });
});
