/**
 * Optimisation on the document (`R-151r`).
 *
 * The owner ruled that the original's place wins: passes and proposals live on one document's «Оптимизация» tab,
 * with the document already chosen; the project keeps a summary that links each document there. The widget given
 * a document offers no «Комплект» choice and works on that document only.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { routes } from '@/shared/lib';
import { documentTabOf } from '@/_pages/document-detail';
import { OptimisationByDocument, OptimisationProposals } from '@/widgets/optimisation-proposals';

import { newClient, renderScreen } from '../screens/harness';
import { AR_DOCUMENT_UID, OTHER_DOCUMENT_UID, PROPOSALS_PROJECT_UID, seedLoadedProposals } from './fixtures';

describe('the document’s optimisation tab', () => {
  it('reads its tab from the address, «Версии» by default', () => {
    expect(documentTabOf('optimisation')).toBe('optimisation');
    expect(documentTabOf(null)).toBe('versions');
    expect(documentTabOf('anything')).toBe('versions');
  });

  it('works on the document it is given and offers no «Комплект» choice', () => {
    const client = newClient();
    seedLoadedProposals(client);
    const markup = renderScreen(client, createElement(OptimisationProposals, {
      projectUid: PROPOSALS_PROJECT_UID, documentUid: AR_DOCUMENT_UID, roles: ['expert'],
    }));
    expect(markup).toContain('data-optimisation-proposals');
    expect(markup).not.toMatch(/>\s*Комплект\s/);
  });

  it('keeps the «Комплект» choice where no document is given', () => {
    const client = newClient();
    seedLoadedProposals(client);
    const markup = renderScreen(client, createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, roles: ['expert'] }));
    expect(markup).toContain('Комплект');
  });
});

describe('the project’s summary', () => {
  it('links each classified document to its own optimisation tab', () => {
    const client = newClient();
    seedLoadedProposals(client);
    const markup = renderScreen(client, createElement(OptimisationByDocument, { projectUid: PROPOSALS_PROJECT_UID }));
    expect(markup).toContain(routes.documentOptimisation(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID));
    expect(markup).toContain(routes.documentOptimisation(PROPOSALS_PROJECT_UID, OTHER_DOCUMENT_UID));
  });
});
