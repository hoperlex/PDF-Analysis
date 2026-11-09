/**
 * `D-372`: the decision filter of «Предложения» (the strip's «Все» and one button per decision state) is in the address
 * (`?decision=`), so a saved link, a reload and Back/Forward return to the same filter (`UI-PARITY-01`, completion scenario 5). It was
 * component state.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the address is read and written as a pure pair against the closed set: «Все» is the absent parameter, a value outside the set is
 *     «Все» and is never echoed, a parameter that is not this one (`tab`, `pass`, `layout`) is carried through;
 *   - the live container, mounted under an address that follows what it writes (`review/routed-review-address.ts`): opened on
 *     `?decision=reject` it reads the rejected page and presses that button; a press on a button writes the address REPLACING the entry
 *     with `null` as the state (`D-341`) and keeps the layout and the pass; «Все» removes the parameter; a link to the same pass with another
 *     filter is another filter.
 *
 * The transport answers nothing, so a page that is not seeded is never drawn from the network.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import { PROPOSAL_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import { OptimisationProposals, readProposalDecision, writeProposalDecision } from '@/widgets/optimisation-proposals';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { RoutedReviewAddress, currentSearch, resetRoutedAddress, writtenAddresses, writtenHow, writtenStates } from '../review/routed-review-address';
import { newClient } from '../screens/harness';
import {
  AR_DOCUMENT_UID,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  arVersion,
  pass,
  proposal,
  proposalPage,
} from './fixtures';

const read = (query: string) => readProposalDecision(new URLSearchParams(query));

describe('the decision filter address', () => {
  it('reads each of the four decision states, and anything else as «Все»', () => {
    expect(read('decision=pending')).toBe('pending');
    expect(read('decision=accept')).toBe('accept');
    expect(read('decision=reject')).toBe('reject');
    expect(read('decision=revise')).toBe('revise');
    expect(read('')).toBeNull();
    expect(read('decision=')).toBeNull();
    expect(read('decision=all')).toBeNull();
    expect(read('decision=accepted')).toBeNull();
    expect(read('decision=REJECT')).toBeNull();
  });

  it('writes a state, and «Все» as the absent parameter', () => {
    expect(writeProposalDecision(new URLSearchParams(''), 'reject').toString()).toBe('decision=reject');
    expect(writeProposalDecision(new URLSearchParams('decision=reject'), null).toString()).toBe('');
    expect(writeProposalDecision(new URLSearchParams('decision=reject'), 'accept').toString()).toBe('decision=accept');
  });

  it('carries the parameters of the tab, the pass and the layout through a write', () => {
    expect(writeProposalDecision(new URLSearchParams('tab=optimisation&pass=opp_1&layout=table'), 'revise').toString()).toBe(
      'tab=optimisation&pass=opp_1&layout=table&decision=revise',
    );
    expect(writeProposalDecision(new URLSearchParams('tab=optimisation&decision=revise&pass=opp_1'), null).toString()).toBe(
      'tab=optimisation&pass=opp_1',
    );
  });
});

describe('the container follows the address', () => {
  let live: LiveRender | null = null;

  /** One rejected proposal, so the rejected page is told from the first (both proposals) by its row count. */
  const rejected = () =>
    proposalPage({ decision: 'reject', items: [proposal()], total: 1, optimisation_pass: pass({ decision_counts: { pending: 1, accept: 0, reject: 1, revise: 0 } }) });

  function seeded(): QueryClient {
    const client = newClient();
    // A seeded page stays fresh: a query whose key CHANGES (another filter) fetches when its data is stale, and the transport answers
    // nothing, so the page would turn to its failure instead of the seeded one.
    client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, staleTime: Infinity } });
    client.setQueryData(queryKeys.projects.documents(PROPOSALS_PROJECT_UID, undefined, 50), { items: [arVersion()], page: { next_cursor: null } as never });
    client.setQueryData(queryKeys.optimisation.passes(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID), { items: [pass()] });
    client.setQueryData(queryKeys.optimisation.proposals(PASS_ID, null, 0, PROPOSAL_PAGE_LIMIT), proposalPage());
    client.setQueryData(queryKeys.optimisation.proposals(PASS_ID, 'reject', 0, PROPOSAL_PAGE_LIMIT), rejected());
    client.setQueryData(queryKeys.optimisation.proposals(PASS_ID, 'accept', 0, PROPOSAL_PAGE_LIMIT), proposalPage({ decision: 'accept', items: [], total: 0 }));
    return client;
  }

  const element = (client: QueryClient, query: string) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        RoutedReviewAddress,
        { pathname: '/projects/prj/documents/doc', query },
        createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, documentUid: AR_DOCUMENT_UID, roles: ['expert'] }),
      ),
    );

  /** The filter the strip shows, and how many proposals are drawn. */
  const shown = (markup: string) => ({
    filter: /data-decision-filter="([^"]+)"/.exec(markup)?.[1] ?? null,
    list: /data-proposal-list="(\d+)"/.exec(markup)?.[1] ?? null,
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

  it('shows «Все» with no parameter', async () => {
    live = await mountLive(element(seeded(), ''));
    expect(shown(live.markup())).toEqual({ filter: 'all', list: '2' });
    expect(writtenAddresses()).toEqual([]);
  });

  it('opens on the filter the address names', async () => {
    live = await mountLive(element(seeded(), 'decision=reject'));
    expect(shown(live.markup())).toEqual({ filter: 'reject', list: '1' });
    expect(live.markup()).toMatch(/aria-pressed="true"[^>]*>отклонено \(1\)</);
  });

  it('reads a value outside the set as «Все», and writes nothing', async () => {
    live = await mountLive(element(seeded(), 'decision=everything'));
    expect(shown(live.markup())).toEqual({ filter: 'all', list: '2' });
    expect(writtenAddresses()).toEqual([]);
  });

  it('writes the address when a button is pressed, replacing the entry with null as the state', async () => {
    live = await mountLive(element(seeded(), `tab=optimisation&pass=${PASS_ID}`));
    expect(await live.press('отклонено (0)')).toBe(true);
    expect(currentSearch()).toBe(`tab=optimisation&pass=${PASS_ID}&decision=reject`);
    expect(writtenStates).toEqual([null]);
    expect(writtenHow).toEqual(['replace']);
    expect(shown(live.markup())).toEqual({ filter: 'reject', list: '1' });
  });

  it('removes the parameter when «Все» is pressed', async () => {
    live = await mountLive(element(seeded(), 'decision=reject'));
    expect(await live.press('Все (2)')).toBe(true);
    expect(currentSearch()).toBe('');
    expect(shown(live.markup())).toEqual({ filter: 'all', list: '2' });
  });

  it('follows a link to the same pass with another filter', async () => {
    const client = seeded();
    live = await mountLive(element(client, 'decision=reject'));
    expect(shown(live.markup()).filter).toBe('reject');
    await live.update(element(client, 'decision=accept'));
    expect(shown(live.markup()).filter).toBe('accept');
  });
});
