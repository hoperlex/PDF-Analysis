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
