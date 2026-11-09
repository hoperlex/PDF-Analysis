/**
 * The document's page (`UI-A-22`, `UI-A-28`, `R-151a`, `R-151e`, `R-151r`): the strip with the section's neighbours at its
 * end, the document's own controls in one row, the tabs as an underlined row, and the empty project's pointer to the upload.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { DocumentDetailPage } from '@/_pages/document-detail';

import { newClient, renderScreen } from '../screens/harness';
import { DOCUMENT_UID, PROJECT_UID, classification, page, version } from '../sections/fixtures';

describe('the document page', () => {
  const client = newClient();
  client.setQueryData(
    queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT),
    page([version({ tags: ['Корпус 1'], classification: classification() })]),
  );
  const markup = renderScreen(client, createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, roles: ['expert'] }));

  it('puts rename and archive and the tags in one row, between the strip and the tabs', () => {
    const strip = markup.indexOf('data-context-level="document"');
    const lifecycle = markup.indexOf('data-document-lifecycle');
    const tags = markup.indexOf('data-document-tags');
    const tabs = markup.indexOf('data-document-tabs');
    expect(strip).toBeGreaterThan(-1);
    expect(strip).toBeLessThan(lifecycle);
    expect(lifecycle).toBeLessThan(tags);
    expect(tags).toBeLessThan(tabs);
    // nothing but the two controls between them: no heading, no navigation
    expect(markup.slice(lifecycle, tags)).not.toMatch(/<h[1-6]|<nav/);
  });

  it('keeps the tabs as buttons that say which is open', () => {
    expect(markup).toMatch(/<button[^>]*aria-pressed="true"[^>]*>Версии<\/button>/);
    expect(markup).toMatch(/<button[^>]*aria-pressed="false"[^>]*>Оптимизация<\/button>/);
  });
});
