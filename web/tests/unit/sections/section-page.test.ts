/**
 * «Раздел» — one section of one project (`R-151l`), its documents as cards (`R-151s`).
 *
 * The page reads `listDocuments` with `section_code` (contract 1.20.0): its cache entry is keyed by the section,
 * so it never shows another section's or the whole project's page. It refuses a malformed address itself, without
 * a request, and names where the reader is in the context strip.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { DOCUMENT_PAGE_LIMIT, documentListQueryOptions } from '@/entities/document-version';
import { SectionDetailPage } from '@/_pages/section-detail';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

// `UI-PARITY-DOC-AUDIT`: the page reads the listing in the server's audit order, a listing of its own in the cache.
const SECTION_KEY = queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit');

function seeded(items: ReturnType<typeof version>[], nextCursor: string | null = null) {
  const client = newClient();
  client.setQueryData(SECTION_KEY, page(items, nextCursor));
  return client;
}

const AR_ONE = version({ classification: classification({ section_code: 'AR' }) });
const AR_TWO = otherVersion('B', { version_ordinal: 3, classification: classification({ section_code: 'AR' }) });

describe('the section page', () => {
  it('keys its read by the section, apart from the project page’s own list', () => {
    const options = documentListQueryOptions(PROJECT_UID, undefined, 'AR', false, undefined, { order: 'audit' });
    expect(options.queryKey).toEqual(SECTION_KEY);
    expect(options.queryKey).not.toEqual(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT));
  });

  it('draws each document of the section as a card: number, title, version link and history', () => {
    const markup = renderWith(seeded([AR_ONE, AR_TWO]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('data-document-cards="2"');
    expect(markup).toContain('>V1<');
    expect(markup).toContain('>V3<');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/versions/${AR_ONE.version_uid}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/documents/${AR_TWO.document_uid}"`);
    expect((markup.match(/>все версии</g) ?? []).length).toBe(2);
  });

  it('names the section in the title and as the current step of the context strip', () => {
    const markup = renderWith(seeded([AR_ONE]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('data-context-level="section"');
    expect(markup).toMatch(/aria-current="page"[^>]*>АР /);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}"`);
  });

  it('says an empty section is empty, and offers the way back to the project', () => {
    const markup = renderWith(seeded([]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('В этом разделе пока нет документов.');
    expect(markup).toContain('К разделам проекта');
  });

  it('pages forward when the server has more', () => {
    const markup = renderWith(seeded([AR_ONE], 'next'), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('>Далее<');
    expect(markup).not.toContain('>Назад<');
  });

  it('refuses a malformed project or an unknown section without a request', () => {
    for (const props of [
      { projectUid: 'это-не-идентификатор', sectionCode: 'AR' },
      { projectUid: PROJECT_UID, sectionCode: 'ZZ' },
    ]) {
      const client = newClient();
      const markup = renderWith(client, createElement(SectionDetailPage, props));
      expect(markup).toContain('Это не адрес раздела.');
      expect(client.getQueryCache().getAll()).toHaveLength(0);
    }
  });
});

// ------------------------------------------------------------------ the original's section page, in full

describe('the section page keeps the original’s controls', () => {
  const render = (items = [AR_ONE, AR_TWO]) =>
    renderWith(seeded(items), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));

  it('opens the grid with the Σ card «Оптимизация раздела», a control of the section and not a document', () => {
    const markup = render();
    expect(markup).toContain('data-grid-leading');
    expect(markup).toContain('Оптимизация раздела');
    const escaped = routes.sectionOptimisation('AR', PROJECT_UID).replace(/&/g, '&amp;');
    expect(markup).toContain(`href="${escaped}"`);
    // two documents, two document cards: the Σ card is counted in no figure
    expect(markup).toContain('data-document-cards="2"');
    expect(markup.indexOf('data-grid-leading')).toBeLessThan(markup.indexOf('data-document-uid'));
  });

  it('offers a box on each startable card, «Выбрать все» over the page and the start only once something is chosen', () => {
    const markup = render();
    expect((markup.match(/type="checkbox"/g) ?? []).length).toBe(2 + 1); // two cards and «Показать архивные»
    expect(markup).toContain('Выбрать все (2)');
    expect(markup).not.toContain('Запустить аудит (');
  });

  it('draws no box for a document whose section is not confirmed, and no «Выбрать все» when none can start', () => {
    const markup = render([version()]);
    expect((markup.match(/type="checkbox"/g) ?? []).length).toBe(1);
    expect(markup).not.toContain('Выбрать все');
  });

  it('offers «Выбрать не запускавшиеся» only when a startable document was never run', () => {
    const idle = version({
      classification: classification({ section_code: 'AR' }),
      audit: { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0 },
    });
    expect(render([idle, AR_TWO])).toContain('Выбрать не запускавшиеся (1)');
    expect(render()).not.toContain('Выбрать не запускавшиеся');
  });

  it('makes «не запускались N» the way to narrow the page to those documents, as the original’s click does', () => {
    const idle = version({
      classification: classification({ section_code: 'AR' }),
      audit: { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0 },
    });
    const markup = render([idle, AR_TWO]);
    const badge = /<a [^>]*data-tally="notRun"[^>]*>/.exec(markup)?.[0] ?? '';
    expect(badge).toContain('filter=not_run');
    expect(badge).toContain('data-tally-link');
  });

  it('carries «Показать архивные» and the way to add a document, which is the project’s upload', () => {
    const markup = render();
    expect(markup).toContain('Показать архивные');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}#upload"`);
    expect(markup).toContain('data-section-add');
  });

  it('says only the stage on a card, the section being the page’s own', () => {
    const markup = render();
    expect(markup).toContain('data-project-stage="P"');
    expect(markup).not.toContain('data-section-code=');
  });

  it('reads its listing with the archive flag and the tag in the key, so a filter is its own listing', () => {
    const options = documentListQueryOptions(PROJECT_UID, undefined, 'AR', true, 'Корпус 1', { order: 'audit' });
    expect(options.queryKey).not.toEqual(SECTION_KEY);
    expect(options.queryKey).toEqual(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', true, 'Корпус 1', undefined, 'audit'),
    );
  });
});
