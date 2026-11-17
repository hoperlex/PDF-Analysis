/**
 * The document's page (`UI-A-22`, `UI-A-28`, `R-151a`, `R-151e`, `R-151r`, `UIP-G-09`): the same frame as on every page of the
 * document — the row «раздел › документ», the tabs and the version bar with the section's neighbours — then the document's own
 * controls in one row. The page keeps no tab row of its own: «Оптимизация» is the frame's tab, and the list of versions is the page
 * the document's name in the frame leads to.
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

  it('puts rename and archive and the tags in one row, between the frame and the versions', () => {
    const strip = markup.indexOf('data-context-level="document"');
    const lifecycle = markup.indexOf('data-document-lifecycle');
    const tags = markup.indexOf('data-document-tags');
    const versions = markup.indexOf('id="document-versions-title"');
    expect(strip).toBeGreaterThan(-1);
    expect(strip).toBeLessThan(lifecycle);
    expect(lifecycle).toBeLessThan(tags);
    expect(tags).toBeLessThan(versions);
    // nothing but the two controls between them: no heading, no navigation
    expect(markup.slice(lifecycle, tags)).not.toMatch(/<h[1-6]|<nav/);
  });

  it('draws the frame with the newest version in view, ahead of the document’s own controls', () => {
    expect(markup.indexOf('data-version-tabs')).toBeGreaterThan(markup.indexOf('data-context-level="document"'));
    expect(markup.indexOf('data-version-bar')).toBeGreaterThan(markup.indexOf('data-version-tabs'));
    expect(markup.indexOf('data-version-bar')).toBeLessThan(markup.indexOf('data-document-lifecycle'));
    // the document is the current step, and the section a link to its page
    expect(markup).toMatch(/aria-current="page"[^>]*>Комплект АР</);
    expect(markup).toContain('data-context-step="section"');
  });

  it('draws no tab row of its own: «Оптимизация» is the frame’s tab, a link to the document’s optimisation', () => {
    expect(markup).not.toContain('data-document-tabs');
    expect(markup).not.toContain('aria-label="Разделы документа"');
    expect(markup).not.toMatch(/<button[^>]*aria-pressed="[a-z]+"[^>]*>(Версии|Оптимизация)<\/button>/);
    expect(markup).toMatch(/<a [^>]*data-version-tab="optimisation"[^>]*href="[^"]*\?tab=optimisation"/);
    // on the versions the frame opens none of its tabs
    expect(markup).not.toMatch(/aria-current="page"[^>]*data-version-tab=/);
  });

  it('puts the version bar’s button on the document too: a link to the newest version with its window open', () => {
    expect(markup).toContain('data-version-pdf-link');
    expect(markup).toContain('?pdf=1');
  });
});
