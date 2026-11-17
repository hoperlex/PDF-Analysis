/**
 * «Просмотр PDF» on the version page (`UI-A-27`), the second UX pass of 2026-11-07; `UIP-G-09`: the button is the document
 * frame's, in its version bar, and the page hands the frame the drawer; the frame's own tests (`document-context/version-tabs.test.ts`)
 * hold the button on the other pages, as a link to this page with the window open (`?pdf=1`).
 *
 * What is held, each with the reason a screen-wide instrument cannot hold it:
 *
 *   - the page offers the button once the version is read, in the frame's version bar and not in the page's header, and draws NONE of
 *     the drawer before it is pressed: neither the drawer nor a
 *     request for the document's bytes (a one-pass render cannot press, so "closed by default" is read as: the toggle is there, unpressed,
 *     and the drawer's marker and its content request are not);
 *   - the drawer's bar: the document and version it is about, ‹ стр. [N] / M › with the end pages disabled and the number a field
 *     (`UIP-S10-01`: a typed number goes to that page, one outside 1…M leaves the page and the field says the page again), «Открыть PDF ↗»
 *     only when the bytes are here and addressing the page the reader is on, with a hint that says it is the browser's reader in a new
 *     tab, «Закрыть»;
 *   - the drawer asks for the bytes of ITS version, through the one content operation, when it is opened and not before.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import { DocumentViewer, DocumentViewerView } from '@/widgets/evidence-viewer';
import { enteredPage } from '@/widgets/evidence-viewer/ui/document-viewer';
import { VersionDetailPage } from '@/_pages/version-detail';
import { withoutPdfRequest } from '@/_pages/version-detail/ui/version-detail-page';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { PROJECT_UID, VERSION_UID, version } from '../sections/fixtures';

const noop = (): void => undefined;

function view(over: Partial<Parameters<typeof DocumentViewerView>[0]> = {}): string {
  return renderWith(
    newClient(),
    createElement(DocumentViewerView, {
      title: 'АР-1 · Версия 3', page: 2, pageCount: 5, onPage: noop,
      externalHref: 'blob:http://web.test/abc#page=2', onClose: noop,
      children: createElement('div', { 'data-body': '' }),
      ...over,
    }),
  );
}

describe('the version page', () => {
  function seeded() {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ page_count: 7 }));
    return renderScreen(client, createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }));
  }

  it('offers «Просмотр PDF» once the version is read, unpressed, and draws no drawer', () => {
    const markup = seeded();
    expect(markup).toContain('data-version-pdf-toggle=""');
    expect(markup).toContain('Просмотр PDF');
    expect(markup).toMatch(/<button[^>]*aria-pressed="false"[^>]*data-version-pdf-toggle=""/);
    expect(markup).not.toContain('data-version-pdf=""');
    expect(markup).not.toContain('aria-label="Просмотр PDF"');
  });

  it('puts the button in the frame’s version bar, with the hint «Весь документ, снизу», and nothing but the frame in the page’s header', () => {
    const markup = seeded();
    expect(markup.indexOf('data-version-pdf-toggle')).toBeGreaterThan(markup.indexOf('data-version-bar'));
    expect(markup).toContain('title="Весь документ, снизу"');
    expect(markup).not.toContain('Открыть PDF этой версии снизу');
    // the header has no code and no links: the frame names the document, and the code is in «Сведения о версии и файле»
    const header = markup.slice(markup.indexOf('<header'), markup.indexOf('</header>'));
    expect(header).not.toContain('<code');
    expect(header).not.toContain('<a ');
    expect(markup).not.toContain('Все версии документа');
    const facts = markup.slice(markup.indexOf('data-version-facts'));
    expect(facts).toContain(`data-version-uid="${VERSION_UID}"`);
    expect(facts).toContain(`<code>${VERSION_UID}</code>`);
  });

  it('opens its window from another tab’s request and cleans the request from the address', () => {
    expect(withoutPdfRequest('?pdf=1')).toBe('');
    expect(withoutPdfRequest('?foo=bar&pdf=1')).toBe('?foo=bar');
    expect(withoutPdfRequest('')).toBe('');
    expect(withoutPdfRequest('?foo=bar')).toBe('?foo=bar');
  });

  it('offers nothing before the version is read: no button for a document nobody has found', () => {
    const markup = renderScreen(newClient(), createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }));
    expect(markup).not.toContain('data-version-pdf-toggle=""');
  });

  it('can fail: a version page whose drawer is drawn open does contain the marker', () => {
    expect(view()).toContain('data-version-pdf=""');
  });

  it('asks for no bytes before the press: the content of the version is not among the queries', () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version({ page_count: 7 }));
    renderScreen(client, createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }));
    const keys = client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    expect(keys).not.toContain(JSON.stringify(queryKeys.versions.content(VERSION_UID)));
  });
});

describe('the drawer', () => {
  it('names the document and the version, and the page the reader is on', () => {
    const markup = view();
    expect(markup).toContain('PDF — АР-1 · Версия 3');
    expect(markup).toContain('data-version-pdf-page="2"');
    // the position is «стр. [N] / M»: the number is a field (below), the word and the total are text beside it
    expect(visibleText(markup)).toContain('стр. / 5');
    expect(markup).toMatch(/<input[^>]*data-version-pdf-page-field=""[^>]*value="2"|<input[^>]*value="2"[^>]*data-version-pdf-page-field=""/);
    expect(markup).toContain('data-body=""');
  });

  it('lets the reader step both ways in the middle of the document, and not past either end', () => {
    const middle = view({ page: 3 });
    expect(middle).not.toMatch(/disabled[^>]*aria-label="Предыдущая страница"|aria-label="Предыдущая страница"[^>]*disabled/);
    expect(middle).not.toMatch(/disabled[^>]*aria-label="Следующая страница"|aria-label="Следующая страница"[^>]*disabled/);
    const first = view({ page: 1 });
    expect(first).toMatch(/<button[^>]*disabled=""[^>]*aria-label="Предыдущая страница"|<button[^>]*aria-label="Предыдущая страница"[^>]*disabled=""/);
    const last = view({ page: 5 });
    expect(last).toMatch(/<button[^>]*disabled=""[^>]*aria-label="Следующая страница"|<button[^>]*aria-label="Следующая страница"[^>]*disabled=""/);
  });

  it('offers «Открыть PDF ↗» only when the bytes are here, on the page being read', () => {
    const with_ = view();
    expect(with_).toContain('Открыть PDF ↗');
    expect(with_).toContain('href="blob:http://web.test/abc#page=2"');
    expect(with_).toContain('target="_blank"');
    expect(with_).toContain('rel="noopener noreferrer"');
    expect(view({ externalHref: null })).not.toContain('Открыть PDF');
  });

  it('can be closed by a labelled control', () => {
    expect(view()).toContain('aria-label="Закрыть просмотр PDF"');
  });
});

/** The text of a fragment: tags dropped, the comment marks React puts between adjacent text nodes dropped, spaces folded. */
function visibleText(markup: string): string {
  return markup.replace(/<!-- -->/g, '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

describe('the page number is a field between the steps (UIP-S10-01)', () => {
  const field = (markup: string): string => /<input\b[^>]*data-version-pdf-page-field=""[^>]*>/.exec(markup)?.[0] ?? '';

  it('stands between ‹ and › as «стр. [N] / M», showing the page the reader is on', () => {
    const markup = view({ page: 4, pageCount: 12 });
    expect(field(markup)).toContain('value="4"');
    expect(markup.indexOf('aria-label="Предыдущая страница"')).toBeLessThan(markup.indexOf('data-version-pdf-page-field'));
    expect(markup.indexOf('data-version-pdf-page-field')).toBeLessThan(markup.indexOf('aria-label="Следующая страница"'));
    expect(visibleText(markup)).toContain('стр. / 12');
    expect(markup.indexOf('стр.')).toBeLessThan(markup.indexOf('data-version-pdf-page-field'));
    expect(markup.indexOf('data-version-pdf-page-field')).toBeLessThan(markup.indexOf('/ 12'));
  });

  it('is a text field for digits that says what it is and what it takes, with no word of English', () => {
    const input = field(view({ page: 4, pageCount: 12 }));
    expect(input).toContain('type="text"');
    expect(input).toContain('inputMode="numeric"');
    expect(input).toContain('aria-label="Номер страницы, из 12"');
    expect(input).toContain('title="Номер страницы: число от 1 до 12; переход — клавишей ввода"');
    // the words the reader is shown (the name and the hint) carry no Latin letter: «Enter» is «клавиша ввода»
    for (const attribute of ['aria-label', 'title']) expect(new RegExp(String.raw`\s${attribute}="([^"]*)"`).exec(input)?.[1] ?? '').not.toMatch(/[A-Za-z]/);
  });

  it('is as wide as the last page number is long, and never narrower than two digits', () => {
    expect(field(view({ page: 1, pageCount: 5 }))).toContain('size="2"');
    expect(field(view({ page: 1, pageCount: 12 }))).toContain('size="2"');
    expect(field(view({ page: 1, pageCount: 150 }))).toContain('size="3"');
    expect(field(view({ page: 1, pageCount: 1200 }))).toContain('size="4"');
  });

  it('follows the page: the same field shows another page after a step, not the number typed before it', () => {
    expect(field(view({ page: 2 }))).toContain('value="2"');
    expect(field(view({ page: 3 }))).toContain('value="3"');
  });

  it('goes to a typed page inside 1…M, with Enter, and says that page back', () => {
    expect(enteredPage('4', 2, 12)).toEqual({ page: 4, text: '4' });
    expect(enteredPage('1', 5, 12)).toEqual({ page: 1, text: '1' });
    expect(enteredPage('12', 5, 12)).toEqual({ page: 12, text: '12' });
    // a number with spaces or leading zeros is the same number: the field says it in its plain form
    expect(enteredPage(' 7 ', 2, 12)).toEqual({ page: 7, text: '7' });
    expect(enteredPage('007', 2, 12)).toEqual({ page: 7, text: '7' });
    expect(enteredPage('3', 3, 12)).toEqual({ page: 3, text: '3' });
  });

  it('refuses a number outside 1…M: the page does not change and the field returns the page it had', () => {
    for (const refused of ['0', '13', '99', '1000000', '99999999']) {
      expect(enteredPage(refused, 4, 12), refused).toEqual({ page: 4, text: '4' });
    }
    // one past the end and one before the start are the borders
    expect(enteredPage('13', 12, 12)).toEqual({ page: 12, text: '12' });
    expect(enteredPage('0', 1, 12)).toEqual({ page: 1, text: '1' });
  });

  it('refuses what is not a whole number, rather than reading a number out of it', () => {
    for (const refused of ['', '   ', 'abc', '-3', '+3', '2.5', '2,5', '3 4', '1e1', '٣']) {
      expect(enteredPage(refused, 6, 12), JSON.stringify(refused)).toEqual({ page: 6, text: '6' });
    }
  });

  it('never moves a page to the nearest one: 99 in a 12-page document is a slip, not page 12', () => {
    expect(enteredPage('99', 3, 12).page).toBe(3);
    expect(enteredPage('0', 3, 12).page).toBe(3);
  });

  it('can fail: the in-range and the out-of-range entries do not give the same answer', () => {
    expect(enteredPage('5', 2, 12).page).not.toBe(enteredPage('50', 2, 12).page);
  });
});

describe('«Открыть PDF ↗» says what it opens (UIP-S10-01)', () => {
  it('names the browser’s reader, a new tab and the page, in its hint', () => {
    const link = /<a\b[^>]*target="_blank"[^>]*>/.exec(view({ page: 4 }))?.[0] ?? '';
    expect(link).toContain('title="Открыть исходный файл в новой вкладке, в просмотрщике браузера, на странице 4"');
    expect(/<a\b[^>]*target="_blank"[^>]*>/.exec(view({ page: 5 }))?.[0]).toContain('на странице 5');
  });

  it('keeps its words', () => {
    expect(visibleText(view())).toContain('Открыть PDF ↗');
  });
});

describe('the drawer asks for the document when it is mounted', () => {
  it('reads the version’s content through the one content operation', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
    const requested: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string, init: RequestInit) => {
        requested.push(`${init.method ?? 'GET'} ${new URL(input).pathname}`);
        return new Response(new Uint8Array([37, 80, 68, 70]), { status: 200, headers: { 'content-type': 'application/pdf' } });
      }),
    );
    try {
      const client = newClient();
      renderWith(client, createElement(DocumentViewer, { versionUid: VERSION_UID, title: 'АР-1', pageCount: 3, onClose: noop }));
      await Promise.allSettled(client.getQueryCache().getAll().map((query) => query.fetch()));
      expect(requested).toEqual([`GET /bff/v1/versions/${VERSION_UID}/content`]);
    } finally {
      vi.unstubAllGlobals();
      vi.unstubAllEnvs();
    }
  });

  it('shows the loading state while the bytes are on their way', () => {
    const markup = renderWith(newClient(), createElement(DocumentViewer, { versionUid: VERSION_UID, title: 'АР-1', pageCount: 3, onClose: noop }));
    expect(markup).toContain('Загрузка: PDF версии');
    expect(markup).toContain('data-version-pdf=""');
  });
});
