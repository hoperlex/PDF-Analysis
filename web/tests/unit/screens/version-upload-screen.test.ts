/**
 * «Загрузить новую версию» on the document screen (`W59-VERSION-UPLOAD-01`).
 *
 * The form takes the same bundle as the first upload, states the same envelope before the
 * picker and refuses with the same states (`UploadOutcome`), but it has no title field —
 * a further version takes no title and no section — and its intent is this document.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { UPLOAD_ENVELOPE_RULES } from '@/entities/document-version';
import { UploadDocumentForm, UploadDocumentVersionForm } from '@/features/upload-document';
import { UploadPanel, UploadVersionPanel } from '@/widgets/upload-panel';
import { DocumentDetailPage } from '@/_pages/document-detail';

import { DOCUMENT_UID, PROJECT_UID } from '../review/fixtures';
import { newClient, renderScreen, renderWith } from './harness';

/** Escape the way React's static markup does, so a rule with quotes can be found in it. */
function escaped(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
}

describe('the next-version upload form', () => {
  const form = () =>
    renderWith(
      newClient(),
      createElement(UploadDocumentVersionForm, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }),
    );

  it('accepts one ZIP archive, exactly as the first upload does', () => {
    const markup = form();
    const first = renderWith(newClient(), createElement(UploadDocumentForm, { projectUid: PROJECT_UID }));
    const accept = /accept="([^"]*)"/.exec(first)?.[1];
    expect(accept).toBeTruthy();
    expect(markup).toContain(`accept="${accept}"`);
    expect(markup).toContain('type="file"');
  });

  it('names its control «Загрузить новую версию» and cannot be sent before a file is chosen', () => {
    const markup = form();
    expect(markup).toMatch(/<button[^>]*type="submit"[^>]*disabled[^>]*>Загрузить новую версию<\/button>/);
  });

  it('asks for no title and no section', () => {
    const markup = form();
    expect(markup).not.toContain('name="display_title"');
    expect(markup).not.toContain('name="section"');
    expect(markup).not.toContain('Отображаемое название');
  });

  it('states no refusal before a file has been chosen', () => {
    const markup = form();
    expect(markup).not.toContain('data-precheck-problem');
    expect(markup).not.toContain('data-upload-failure');
  });
});

describe('the next-version panel', () => {
  it('states the same envelope before the picker as the first upload’s panel', () => {
    const version = renderWith(
      newClient(),
      createElement(UploadVersionPanel, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }),
    );
    const first = renderWith(newClient(), createElement(UploadPanel, { projectUid: PROJECT_UID }));
    for (const rule of UPLOAD_ENVELOPE_RULES) {
      expect(version).toContain(escaped(rule));
      expect(first).toContain(escaped(rule));
    }
    expect(version).toContain('Что принимается');
    expect(version.indexOf('Что принимается')).toBeLessThan(version.indexOf('type="file"'));
  });

  it('says the new version becomes current and inherits nothing', () => {
    const version = renderWith(
      newClient(),
      createElement(UploadVersionPanel, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }),
    );
    expect(version).toContain('становится текущей версией документа');
    expect(version).toContain('ничего не наследует');
    // The first upload's sentence about a second document is not this panel's to say.
    expect(version).not.toContain('Повторная загрузка публикует второй документ');
  });
});

describe('the document screen', () => {
  it('offers «Загрузить новую версию» under the version list', () => {
    const markup = renderScreen(
      newClient(),
      createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }),
    );
    expect(markup).toContain('Опубликованные версии');
    expect(markup).toContain('>Загрузить новую версию</button>');
    expect(markup.indexOf('Опубликованные версии')).toBeLessThan(markup.indexOf('Загрузить новую версию'));
  });

  it('offers no upload on a malformed address', () => {
    const markup = renderScreen(
      newClient(),
      createElement(DocumentDetailPage, { projectUid: 'не-проект', documentUid: DOCUMENT_UID }),
    );
    expect(markup).not.toContain('Загрузить новую версию');
  });
});
