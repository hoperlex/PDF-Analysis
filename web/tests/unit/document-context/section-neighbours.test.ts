/**
 * `UI-A-28`: «‹ Предыдущий · N из M · Следующий ›» between the documents of one section.
 *
 * Three instruments, each on what it can see. The walk and the position are pure functions, read as data. The
 * strip's markup is one static pass. The cursor being followed to its end is an effect and a chain of requests, so
 * it is read off a live mount over a mocked `listDocuments`: the requests it makes, in order, are the claim.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listDocuments: vi.fn() };
});

import { DocumentDetailPage } from '@/_pages/document-detail';
import { listDocuments, queryKeys } from '@/shared/api';
import type { ApiResponse, DocumentVersion, DocumentVersionPage, ProjectUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  DOCUMENT_PAGE_LIMIT,
  advanceSectionWalk,
  sectionListingAudit,
  sectionPosition,
} from '@/entities/document-version';
import { SectionNeighbours, SectionNeighboursView } from '@/widgets/document-context';
import { findProjectSection } from '@/entities/project';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID, apiError, classification, otherVersion, page, version } from '../sections/fixtures';

// Five documents of one section, in the order the server answers (`order=audit`): A, B, C, D, E.
const DOCS = ['A', 'B', 'C', 'D', 'E'].map((suffix) =>
  otherVersion(suffix, { classification: classification({ section_code: 'AR' }) }));
const [A, B, C, D, E] = DOCS as [DocumentVersion, DocumentVersion, DocumentVersion, DocumentVersion, DocumentVersion];

const AR = findProjectSection('AR') as NonNullable<ReturnType<typeof findProjectSection>>;

describe('advanceSectionWalk — following the cursor to its end', () => {
  it('asks for the first page first, and reads nothing from a page it has not got', () => {
    expect(advanceSectionWalk([undefined], [undefined])).toEqual({ kind: 'reading', cursors: [undefined], items: [] });
  });

  it('names the next cursor the server gave, and keeps reading until it says there is none', () => {
    expect(advanceSectionWalk([undefined], [page([A, B], 'c2')])).toEqual({
      kind: 'reading', cursors: [undefined, 'c2'], items: [A, B],
    });
    expect(advanceSectionWalk([undefined, 'c2'], [page([A, B], 'c2'), page([C, D], 'c3')])).toEqual({
      kind: 'reading', cursors: [undefined, 'c2', 'c3'], items: [A, B, C, D],
    });
  });

  it('is complete only at a page without a next cursor, with every page\'s items in the order read', () => {
    const step = advanceSectionWalk([undefined, 'c2', 'c3'], [page([A, B], 'c2'), page([C, D], 'c3'), page([E], null)]);
    expect(step.kind).toBe('complete');
    expect(step.kind === 'complete' ? step.items : []).toEqual([A, B, C, D, E]);
  });

  it('can fail: one page short of the end is reading, never complete', () => {
    expect(advanceSectionWalk([undefined, 'c2'], [page([A, B], 'c2'), undefined]).kind).toBe('reading');
  });

  it('drops a page read under a cursor the first page no longer names (a refetch moved the chain)', () => {
    const step = advanceSectionWalk([undefined, 'old'], [page([A, B], 'new'), page([C, D], null)]);
    expect(step).toEqual({ kind: 'reading', cursors: [undefined, 'new'], items: [A, B] });
  });

  it('reports a cursor it has already followed as a fault of the listing, and does not follow it again', () => {
    expect(advanceSectionWalk([undefined, 'c2'], [page([A], 'c2'), page([B], 'c2')]).kind).toBe('cycle');
    expect(advanceSectionWalk([undefined], [page([A], 'c2')]).kind).toBe('reading');
  });
});

describe('sectionPosition — where a document stands in the section', () => {
  it('is its place, the length of the listing, and its two neighbours', () => {
    expect(sectionPosition(DOCS, C.document_uid)).toEqual({ position: 3, total: 5, previous: B, next: D });
  });

  it('has no previous at the first document and no next at the last', () => {
    expect(sectionPosition(DOCS, A.document_uid)).toEqual({ position: 1, total: 5, previous: null, next: B });
    expect(sectionPosition(DOCS, E.document_uid)).toEqual({ position: 5, total: 5, previous: D, next: null });
  });

  it('is nothing for a document the listing does not hold — no N from a list it is not in', () => {
    expect(sectionPosition(DOCS, 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z')).toBeNull();
    expect(sectionPosition([], A.document_uid)).toBeNull();
  });
});

describe('the strip', () => {
  const draw = (index: number): string =>
    renderToStaticMarkup(createElement(SectionNeighboursView, {
      projectUid: PROJECT_UID,
      section: AR,
      place: sectionPosition(DOCS, (DOCS[index] as DocumentVersion).document_uid) as NonNullable<ReturnType<typeof sectionPosition>>,
    }));

  const text = (markup: string): string => markup.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();

  it('says «‹ Предыдущий · N из M · Следующий ›», in a named navigation of the section', () => {
    const markup = draw(2);
    expect(text(markup)).toBe('‹ Предыдущий · 3 из 5 · Следующий ›');
    expect(markup).toContain('aria-label="Документы раздела АР"');
    expect(markup).toContain('data-neighbour-position="3"');
    expect(markup).toContain('data-neighbour-total="5"');
  });

  /** The attributes of the link carrying `rel`, whatever their order. */
  const linkOf = (markup: string, rel: string): { href?: string; title?: string; text: string } | null => {
    const found = [...markup.matchAll(/<a\b([^>]*)>(.*?)<\/a>/g)].find((m) => (m[1] as string).includes(`rel="${rel}"`));
    if (found === undefined) return null;
    const attributes = found[1] as string;
    return {
      href: /\bhref="([^"]*)"/.exec(attributes)?.[1] ?? '',
      title: /\btitle="([^"]*)"/.exec(attributes)?.[1] ?? '',
      text: found[2] as string,
    };
  };

  it('links to the neighbours\' own document pages, titled by the neighbour', () => {
    const markup = draw(2);
    expect(linkOf(markup, 'prev')).toEqual({ href: routes.document(PROJECT_UID, B.document_uid), title: 'Документ B', text: '‹ Предыдущий' });
    expect(linkOf(markup, 'next')).toEqual({ href: routes.document(PROJECT_UID, D.document_uid), title: 'Документ D', text: 'Следующий ›' });
  });

  it('draws no link where there is no neighbour: the first has no previous, the last no next', () => {
    const first = draw(0);
    expect(first).not.toContain('rel="prev"');
    expect(first).toContain('data-neighbour="prev" data-neighbour-end=""');
    expect(first).toContain('rel="next"');
    const last = draw(4);
    expect(last).not.toContain('rel="next"');
    expect(last).toContain('rel="prev"');
    expect(text(last)).toBe('‹ Предыдущий · 5 из 5 · Следующий ›');
  });
});

// --------------------------------------------------------------------------------- the whole listing

describe('the document page walks the section it is in', () => {
  const read = vi.mocked(listDocuments);
  let live: LiveRender | null = null;

  function answer(data: DocumentVersionPage): ApiResponse<DocumentVersionPage> {
    return { data, status: 200, correlationId: 'cid-section' };
  }

  /** The server: two documents a page, the cursor an opaque word. */
  let PAGES: Record<string, DocumentVersionPage> = {};

  beforeEach(() => {
    PAGES = {
      first: page([A, B], 'c2'),
      c2: page([C, D], 'c3'),
      c3: page([E], null),
    };
    read.mockReset();
    read.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      const cursor = input.query?.cursor ?? 'first';
      const found = PAGES[cursor];
      if (found === undefined) throw new Error(`no page ${cursor}`);
      return answer(found);
    }) as unknown as typeof listDocuments);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  const strip = (client: QueryClient, documentUid: string, sectionCode: string | undefined): ReactElement =>
    createElement(QueryClientProvider, { client }, createElement(SectionNeighbours, { projectUid: PROJECT_UID, documentUid, sectionCode }));

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 8; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  const cursors = (): (string | undefined)[] =>
    read.mock.calls.map(([input]) => (input as { query?: { cursor?: string } }).query?.cursor);

  it('reads every page of the section, in order, with the section filter and the section page\'s order, then says N of M', async () => {
    live = await mountLive(strip(freshClient(), C.document_uid, 'AR'));
    await settled(live);
    expect(cursors()).toEqual([undefined, 'c2', 'c3']);
    for (const [input] of read.mock.calls) {
      expect(input).toMatchObject({
        path: { project_uid: PROJECT_UID },
        query: { section_code: 'AR', order: 'audit', limit: DOCUMENT_PAGE_LIMIT },
      });
      expect((input as { query: Record<string, unknown> }).query).not.toHaveProperty('include_archived');
      expect((input as { query: Record<string, unknown> }).query).not.toHaveProperty('audit_state');
    }
    const markup = live.markup();
    expect(markup).toContain('3 из 5');
    expect(markup).toContain(`href="${routes.document(PROJECT_UID, B.document_uid)}"`);
    expect(markup).toContain(`href="${routes.document(PROJECT_UID, D.document_uid)}"`);
  });

  it('counts a document on the last page by the whole listing: 5 of 5, with no next', async () => {
    live = await mountLive(strip(freshClient(), E.document_uid, 'AR'));
    await settled(live);
    expect(live.markup()).toContain('5 из 5');
    expect(live.markup()).not.toContain('rel="next"');
  });

  it('reuses the first page the section page already holds, under the section page\'s own cache key', async () => {
    const client = freshClient();
    // The key the section page reads its first page under (`section-page.test.ts` pins the same spelling).
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID as ProjectUid, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit'),
      PAGES.first,
    );
    live = await mountLive(strip(client, C.document_uid, 'AR'));
    await settled(live);
    expect(cursors()).toEqual(['c2', 'c3']);
    expect(live.markup()).toContain('3 из 5');
  });

  it('the listing is the section page\'s: order=audit, and the audit filter only where the section page narrows', () => {
    expect(sectionListingAudit(null)).toEqual({ order: 'audit' });
    expect(sectionListingAudit('not_run')).toEqual({ state: 'not_run', order: 'audit' });
  });

  it('draws nothing for a section of one document', async () => {
    PAGES.first = page([A], null);
    live = await mountLive(strip(freshClient(), A.document_uid, 'AR'));
    await settled(live);
    expect(cursors()).toEqual([undefined]);
    expect(live.markup()).not.toContain('data-section-neighbours');
  });

  it('draws nothing for a document the listing does not hold (archived, or confirmed for another section)', async () => {
    live = await mountLive(strip(freshClient(), 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z', 'AR'));
    await settled(live);
    expect(cursors()).toEqual([undefined, 'c2', 'c3']);
    expect(live.markup()).not.toContain('data-section-neighbours');
  });

  it('draws nothing, and asks nothing, while the version has no confirmed section', async () => {
    live = await mountLive(strip(freshClient(), A.document_uid, undefined));
    await settled(live);
    expect(read).not.toHaveBeenCalled();
    expect(live.markup()).not.toContain('data-section-neighbours');
  });

  it('draws nothing for a section code this build does not know, and asks nothing', async () => {
    live = await mountLive(strip(freshClient(), A.document_uid, 'ZZ'));
    await settled(live);
    expect(read).not.toHaveBeenCalled();
    expect(live.markup()).not.toContain('data-section-neighbours');
  });

  it('draws nothing when a later page fails — never an N or an M from part of the listing', async () => {
    read.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      const cursor = input.query?.cursor ?? 'first';
      if (cursor === 'c2') throw apiError(500, 'internal_error');
      return answer(PAGES[cursor] as DocumentVersionPage);
    }) as unknown as typeof listDocuments);
    live = await mountLive(strip(freshClient(), A.document_uid, 'AR'));
    await settled(live);
    expect(cursors()).toEqual([undefined, 'c2']);
    expect(live.markup()).not.toContain('data-section-neighbours');
    expect(live.markup()).not.toMatch(/из \d/);
  });

  it('draws nothing when the listing names a cursor it has already given, and does not loop', async () => {
    PAGES.c2 = page([C, D], 'c2');
    live = await mountLive(strip(freshClient(), A.document_uid, 'AR'));
    await settled(live);
    expect(cursors()).toEqual([undefined, 'c2']);
    expect(live.markup()).not.toContain('data-section-neighbours');
  });
});

describe('the document page', () => {
  const VERSIONS_KEY = queryKeys.versions.list(A.document_uid as never, undefined, 50);

  it('puts the strip under the context strip only for a version confirmed for a section, and asks the section\'s listing', () => {
    const withSection = newClient();
    withSection.setQueryData(VERSIONS_KEY, page([A]));
    renderScreen(withSection, createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: A.document_uid }));
    const asked = withSection.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    expect(asked.some((key) => key.includes('"section":"AR"') && key.includes('"order":"audit"'))).toBe(true);

    const without = newClient();
    without.setQueryData(VERSIONS_KEY, page([version({ document_uid: A.document_uid })]));
    renderScreen(without, createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: A.document_uid }));
    expect(without.getQueryCache().getAll().some((query) => JSON.stringify(query.queryKey).includes('"section"'))).toBe(false);
  });
});
