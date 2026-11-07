/**
 * «Просмотр PDF» on the version page (`UI-A-27`), the second UX pass of 2026-11-07.
 *
 * What is held, each with the reason a screen-wide instrument cannot hold it:
 *
 *   - the page offers the button once the version is read, and draws NONE of the drawer before it is pressed: neither the drawer nor a
 *     request for the document's bytes (a one-pass render cannot press, so "closed by default" is read as: the toggle is there, unpressed,
 *     and the drawer's marker and its content request are not);
 *   - the drawer's bar: the document and version it is about, ‹ N / M › with the end pages disabled, «Открыть PDF ↗» only when the bytes
 *     are here and addressing the page the reader is on, «Закрыть»;
 *   - the drawer asks for the bytes of ITS version, through the one content operation, when it is opened and not before.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import { DocumentViewer, DocumentViewerView } from '@/widgets/evidence-viewer';
import { VersionDetailPage } from '@/_pages/version-detail';

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
    expect(markup).toContain('2 / 5');
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
