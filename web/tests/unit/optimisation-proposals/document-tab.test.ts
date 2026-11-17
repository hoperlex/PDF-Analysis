/**
 * Optimisation on the document (`R-151r`).
 *
 * The owner ruled that the original's place wins: passes and proposals live on one document's «Оптимизация» tab,
 * with the document already chosen; the project keeps a summary that links each document there. The widget given
 * a document offers no «Комплект» choice and works on that document only.
 *
 * `UIP-S09-01`: the tab opens on the table of proposals (fifty to a page), and «Показать карточками» (`?layout=cards`) and
 * «Показать таблицей» are the one link each way; the live cases below press them under an address that follows what the tab writes.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { PROPOSAL_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import { documentTabOf } from '@/_pages/document-detail';
import { OptimisationByDocument, OptimisationProposals, TABLE_PAGE_LIMIT } from '@/widgets/optimisation-proposals';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { RoutedReviewAddress, currentSearch, resetRoutedAddress, writtenAddresses, writtenHow, writtenStates } from '../review/routed-review-address';
import { newClient, renderScreen } from '../screens/harness';
import {
  AR_DOCUMENT_UID,
  OLDER_PASS_ID,
  OTHER_DOCUMENT_UID,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  arVersion,
  pass,
  proposalPage,
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

describe('the proposals’ layout on the tab (`UIP-S09-01`)', () => {
  let live: LiveRender | null = null;

  /** Both pages of the first pass, the table's fifty and the cards' own twenty, so either layout is drawn from the cache. */
  function seededBoth(): QueryClient {
    const client = newClient();
    // A seeded page stays fresh: a query whose key CHANGES fetches when its data is stale, and the transport answers nothing.
    client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, staleTime: Infinity } });
    client.setQueryData(queryKeys.projects.documents(PROPOSALS_PROJECT_UID, undefined, 50), {
      items: [arVersion()],
      page: { next_cursor: null } as never,
    });
    client.setQueryData(queryKeys.optimisation.passes(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID), { items: [pass()] });
    for (const limit of [TABLE_PAGE_LIMIT, PROPOSAL_PAGE_LIMIT]) {
      client.setQueryData(queryKeys.optimisation.proposals(PASS_ID, null, 0, limit), proposalPage({ limit }));
    }
    return client;
  }

  const tab = (client: QueryClient, query: string) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        RoutedReviewAddress,
        { pathname: '/projects/prj/documents/doc', query },
        createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, documentUid: AR_DOCUMENT_UID, roles: ['expert'] }),
      ),
    );

  const drawn = (markup: string) => ({
    table: markup.includes('data-proposal-table'),
    cards: markup.includes('<article'),
    layout: /data-proposal-layout="([^"]+)"/.exec(markup)?.[1] ?? null,
  });

  beforeEach(() => {
    resetRoutedAddress();
    vi.stubGlobal('fetch', async () => {
      throw new TypeError('offline');
    });
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
    vi.unstubAllGlobals();
    resetRoutedAddress();
  });

  it('opens on the table with no layout in the address, and writes nothing', async () => {
    live = await mountLive(tab(seededBoth(), `tab=optimisation&pass=${PASS_ID}`));
    expect(drawn(live.markup())).toEqual({ table: true, cards: false, layout: 'table' });
    expect(live.markup()).toContain('Показать карточками');
    expect(writtenAddresses()).toEqual([]);
  });

  it('opens the table for the earlier ?layout=table too', async () => {
    live = await mountLive(tab(seededBoth(), `tab=optimisation&pass=${PASS_ID}&layout=table`));
    expect(drawn(live.markup())).toEqual({ table: true, cards: false, layout: 'table' });
  });

  it('opens the cards for ?layout=cards, with the link back to the table', async () => {
    live = await mountLive(tab(seededBoth(), `tab=optimisation&pass=${PASS_ID}&layout=cards`));
    expect(drawn(live.markup())).toEqual({ table: false, cards: true, layout: 'cards' });
    expect(live.markup()).toContain('Показать таблицей');
    expect(live.markup()).not.toContain('Показать карточками');
  });

  it('writes ?layout=cards, replacing the entry, when «Показать карточками» is pressed, and the table’s link takes its place', async () => {
    live = await mountLive(tab(seededBoth(), `tab=optimisation&pass=${PASS_ID}`));
    expect(await live.press('Показать карточками')).toBe(true);
    expect(currentSearch()).toBe(`tab=optimisation&pass=${PASS_ID}&layout=cards`);
    expect(writtenHow).toEqual(['replace']);
    expect(writtenStates).toEqual([null]);
    expect(drawn(live.markup())).toEqual({ table: false, cards: true, layout: 'cards' });
  });

  it('removes the parameter when «Показать таблицей» is pressed, and keeps the tab and the pass', async () => {
    live = await mountLive(tab(seededBoth(), `tab=optimisation&pass=${PASS_ID}&layout=cards`));
    expect(await live.press('Показать таблицей')).toBe(true);
    expect(currentSearch()).toBe(`tab=optimisation&pass=${PASS_ID}`);
    expect(writtenHow).toEqual(['replace']);
    expect(drawn(live.markup())).toEqual({ table: true, cards: false, layout: 'table' });
  });
});
