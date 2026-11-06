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
import {
  AR_DOCUMENT_UID,
  OLDER_PASS_ID,
  OTHER_DOCUMENT_UID,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  seedLoadedProposals,
  seedOlderPassProposals,
} from './fixtures';

const noop = (): void => undefined;
const UNKNOWN_PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9Z';

function tabMarkup(props: { readonly passId?: string | null; readonly onPassChange?: () => void }): string {
  const client = newClient();
  seedLoadedProposals(client);
  seedOlderPassProposals(client);
  return renderScreen(client, createElement(OptimisationProposals, {
    projectUid: PROPOSALS_PROJECT_UID, documentUid: AR_DOCUMENT_UID, roles: ['expert'], ...props,
  }));
}

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

describe('the pass in the address (`UI-B-02`)', () => {
  it('builds the tab’s address with and without a pass', () => {
    expect(routes.documentOptimisation(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID)).toBe(
      `/projects/${PROPOSALS_PROJECT_UID}/documents/${AR_DOCUMENT_UID}?tab=optimisation`,
    );
    expect(routes.documentOptimisation(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID, OLDER_PASS_ID)).toBe(
      `/projects/${PROPOSALS_PROJECT_UID}/documents/${AR_DOCUMENT_UID}?tab=optimisation&pass=${OLDER_PASS_ID}`,
    );
    expect(routes.projectOptimisation(PROPOSALS_PROJECT_UID)).toBe(`/projects/${PROPOSALS_PROJECT_UID}?tab=optimisation`);
  });

  it('opens the newest pass when the address names none', () => {
    const markup = tabMarkup({ passId: null, onPassChange: noop });
    expect(markup).toContain(`data-optimisation-pass="${PASS_ID}"`);
    expect(markup).not.toContain('data-pass-not-found');
  });

  it('opens the pass the address names, not the newest', () => {
    const markup = tabMarkup({ passId: OLDER_PASS_ID, onPassChange: noop });
    expect(markup).toContain(`data-optimisation-pass="${OLDER_PASS_ID}"`);
    expect(markup).not.toContain(`data-optimisation-pass="${PASS_ID}"`);
    expect(markup).not.toContain('data-pass-not-found');
  });

  it('says a pass the set does not have, and opens the newest instead', () => {
    const markup = tabMarkup({ passId: UNKNOWN_PASS_ID, onPassChange: noop });
    expect(markup).toContain(`data-pass-not-found="${UNKNOWN_PASS_ID}"`);
    expect(markup).toContain('Проход из адреса не найден среди проходов этого комплекта: открыт последний.');
    expect(markup).toContain(`data-optimisation-pass="${PASS_ID}"`);
  });

  it('opens the pass it is given even where no page layer writes the address', () => {
    expect(tabMarkup({ passId: OLDER_PASS_ID })).toContain(`data-optimisation-pass="${OLDER_PASS_ID}"`);
  });
});
