/**
 * `W55A-WEB-NORMS` — one norm document: its unreliable paragraphs MARKED (F-4), its PDF read
 * only when a page is asked for and a confirmed binding serves it, and opened at that page.
 * Read off one static render and the query cache, as `norms-screen.test.ts` does.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { NormDocumentPage } from '@/_pages/norms';
import { NORM_PARAGRAPH_PAGE_LIMIT } from '@/entities/norms';
import { NormPdf } from '@/widgets/norm-document';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { NORM_DOCUMENT_ID, NORM_PARAGRAPHS, normDocument } from './fixtures';

const DOCUMENT = queryKeys.norms.document(NORM_DOCUMENT_ID);
const PARAGRAPHS = queryKeys.norms.paragraphs(NORM_DOCUMENT_ID, undefined, NORM_PARAGRAPH_PAGE_LIMIT);

function client(document = normDocument()) {
  const seeded = newClient();
  seeded.setQueryData(DOCUMENT, document);
  seeded.setQueryData(PARAGRAPHS, { items: NORM_PARAGRAPHS, page: { next_cursor: null }, source_attribution: 'consultant_plus' });
  return seeded;
}

function asked(seeded: ReturnType<typeof newClient>): string[] {
  return seeded.getQueryCache().getAll().map((query) => String(query.queryKey[1])).sort();
}

function render(seeded: ReturnType<typeof newClient>, page: number | null, id: string | null = NORM_DOCUMENT_ID): string {
  return renderScreen(seeded, createElement(NormDocumentPage, { normDocumentId: id, page }));
}

/** The `<li>` of one paragraph, by its identity. */
function row(markup: string, paragraphId: string): string {
  const start = markup.lastIndexOf('<li', markup.indexOf(`data-norm-paragraph="${paragraphId}"`));
  return markup.slice(start, markup.indexOf('</li>', start));
}

describe('F-4: an unreliable paragraph is shown, and marked', () => {
  it('marks the unreliable paragraph with the page to check it against, and only that one', () => {
    const markup = render(client(), null);
    const rows = NORM_PARAGRAPHS.map((paragraph) => row(markup, paragraph.norm_paragraph_id));
    expect(rows).toHaveLength(3);
    const [heading = '', body = '', unreliable = ''] = rows;
    expect(unreliable).toContain('data-norm-reliability="unreliable"');
    expect(unreliable).toContain('Текст распознан ненадёжно');
    expect(unreliable).toContain('сверьте его с PDF на странице');
    expect(unreliable).toContain(String(NORM_PARAGRAPHS[2]?.text));
    for (const reliable of [heading, body]) {
      expect(reliable).toContain('data-norm-reliability="reliable"');
      expect(reliable).not.toContain('Текст распознан ненадёжно');
    }
    // The marker is a style of its own too, not only a sentence: one class more than a reliable row.
    const classes = (li: string) => (/class="([^"]*)"/.exec(li)?.[1] ?? '').split(' ').filter(Boolean);
    expect(classes(body)).toHaveLength(1);
    expect(classes(unreliable)).toEqual([...classes(body), expect.stringMatching(/unreliable/)]);
    // The document says how many it has, and a heading reads as one.
    expect(markup).toContain('data-norm-unreliable-count="1"');
    expect(heading).toContain('<strong>Требования к помещениям</strong>');
    expect(body).toContain('<strong>п. 5.1 </strong>');
  });

  it('every paragraph links its own PDF page', () => {
    const markup = render(client(), null);
    expect(row(markup, NORM_PARAGRAPHS[2]?.norm_paragraph_id ?? '')).toContain(`href="/norms/document?id=${NORM_DOCUMENT_ID}&amp;page=14"`);
  });
});

describe('the PDF is read only when it is wanted', () => {
  it('no page asked: two reads, no bytes, and a way to open the PDF', () => {
    const seeded = client();
    const markup = render(seeded, null);
    expect(asked(seeded)).toEqual(['document', 'paragraphs']);
    expect(markup).toContain('data-norm-pdf="closed"');
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOCUMENT_ID}&amp;page=1"`);
  });

  it('a page asked of a bound document reads the bytes and waits for them', () => {
    const seeded = client();
    const markup = render(seeded, 12);
    expect(asked(seeded)).toEqual(['content', 'document', 'paragraphs']);
    expect(markup).toContain('Загрузка: PDF документа…');
    expect(markup).toContain('data-norm-pdf-page="12"');
  });

  it('a document with no confirmed binding reads no bytes and says the PDF is unavailable', () => {
    const seeded = client(normDocument({ content_available: false }));
    const markup = render(seeded, 12);
    expect(asked(seeded)).toEqual(['document', 'paragraphs']);
    expect(markup).toContain('PDF этого документа недоступен');
  });

  it('a page past the end reads no bytes and says the page does not exist', () => {
    const seeded = client();
    const markup = render(seeded, 49);
    expect(asked(seeded)).toEqual(['document', 'paragraphs']);
    expect(markup).toContain('Такой страницы в документе нет');
  });

  it('the bytes are opened at the asked page, in the browser’s own viewer', () => {
    const markup = renderScreen(newClient(), createElement(NormPdf, {
      document: normDocument(), page: 12, documentUrl: 'blob:http://web.test/abc', isLoading: false, error: null,
    }));
    expect(markup).toContain('<object');
    expect(markup).toContain('data="blob:http://web.test/abc#page=12"');
    expect(markup).toContain('type="application/pdf"');
  });
});

describe('what the view says when it cannot show a document', () => {
  function refusal(status: number, code: ErrorCode): ApiError {
    const envelope: ErrorEnvelope = {
      contract_version: '1.0.0-draft.1', error_code: code, message: 'English the client never prints.',
      correlation_id: 'cid-norms-3', retryable: code === 'dependency_unavailable',
    };
    return new ApiError(status, envelope, 'cid-norms-3');
  }

  it('an address with no document names none, and reads nothing', () => {
    const seeded = newClient();
    const markup = render(seeded, null, null);
    expect(markup).toContain('Документ не выбран');
    expect(markup).toContain('href="/norms"');
    expect(asked(seeded)).toEqual([]);
  });

  it('a document the server does not have is a failed read, not an empty document', () => {
    const seeded = newClient();
    seedError(seeded, DOCUMENT, refusal(404, 'not_found'));
    seedError(seeded, PARAGRAPHS, refusal(404, 'not_found'));
    const markup = render(seeded, 12);
    expect(markup).toContain('data-norm-document-failure="not_found"');
    expect(markup).toContain('Такого нормативного документа или снимка нет.');
    expect(markup).not.toContain('В документе нет абзацев');
    expect(asked(seeded)).toEqual(['document', 'paragraphs']);
  });
});
