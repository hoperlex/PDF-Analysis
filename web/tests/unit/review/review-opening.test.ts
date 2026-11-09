/**
 * `D-401`: «Разбор» opens, before the reader chooses a finding, the first finding the screen SHOWS -- the first one still waiting for a
 * decision (`UI-A-71`: pending, then accepted, then rejected) -- and keeps it open when a decision re-sorts the list.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the pure rule (`resolveSelection`): the opening finding is the caller's, a selection still in the run beats it, a stale one does not,
 *     and a caller with no order of its own still gets the run's first;
 *   - the live page: on a half-decided run the waiting finding opens (it used to be the run's first, an accepted row), the address says so
 *     with `null` as the state (`D-341`), a decision that moves the opened finding to the accepted rows does not move the selection, a
 *     finding named by the address is left alone, a link to a finding the run does not have falls back to the waiting one and replaces
 *     the stale address, and the table (which opens a row only when asked) writes nothing.
 *
 * Mounted live under `routed-review-address.ts`, which gives the page an address that follows what it writes; the evidence viewer is
 * stubbed (it draws a PDF page, which a node DOM cannot) and the transport answers nothing.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { Finding, Verdict } from '@/shared/api';
import { EvidenceViewerEagerSeam, ReviewPage, resolveSelection, selectFinding } from '@/_pages/review';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { PROJECT_UID, RUN_ID, finding, findingDetail, runStatus } from './fixtures';
import { RoutedReviewAddress, currentSearch, resetRoutedAddress, writtenAddresses, writtenHow, writtenStates } from './routed-review-address';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q';
const ACCEPTED = `fnd_${ULID}A1`;
const REJECTED = `fnd_${ULID}A2`;
const WAITING = `fnd_${ULID}A3`;
const ALSO_WAITING = `fnd_${ULID}A4`;
const ABSENT = `fnd_${ULID}A9`;

const withVerdict = (uid: string, verdict: Verdict): Finding => finding({ finding_uid: uid, current_verdict: verdict });

/** The run's own order is accepted, rejected, waiting, waiting: the first of it is the one the screen must NOT open. */
const HALF_DECIDED = (): Finding[] => [
  withVerdict(ACCEPTED, 'accepted'),
  withVerdict(REJECTED, 'rejected'),
  withVerdict(WAITING, 'pending'),
  withVerdict(ALSO_WAITING, 'pending'),
];

const ALL = [ACCEPTED, REJECTED, WAITING, ALSO_WAITING] as const;

function seed(client: QueryClient, items: Finding[]): void {
  const envelope = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID }));
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items, page: envelope } });
  for (const uid of ALL) {
    client.setQueryData(queryKeys.findings.detail(uid), { data: findingDetail({ finding_uid: uid }) });
    client.setQueryData(queryKeys.findings.decisions(uid), { data: { items: [], page: envelope } });
  }
}

let live: LiveRender | null = null;

async function open(query: string, items: Finding[]): Promise<{ client: QueryClient; element: (search: string) => ReturnType<typeof createElement> }> {
  const client = newClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, staleTime: Infinity } });
  seed(client, items);
  const element = (search: string) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        EvidenceViewerEagerSeam.Provider,
        { value: () => null },
        createElement(
          RoutedReviewAddress,
          { pathname: `/projects/${PROJECT_UID}/runs/${RUN_ID}/review`, query: search },
          createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
        ),
      ),
    );
  live = await mountLive(element(query));
  return { client, element };
}

/** The finding the page has open beside the list: `data-finding-uid` on the article of the open finding. */
const opened = (markup: string): string | null => /<article[^>]*data-finding-uid="([^"]+)"/.exec(markup)?.[1] ?? null;

beforeEach(() => {
  resetRoutedAddress();
  // Everything this page reads that the test did not seed (the sheet labels, the block links, the document context ...) fails, which the
  // page shows as a failure of that panel and nothing more.
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

describe('resolveSelection, with the finding the screen opens', () => {
  const run = ['a', 'b', 'c'];

  it('opens the finding the caller names when nothing is chosen', () => {
    expect(resolveSelection(null, run, 'c')).toEqual({ findingUid: 'c', page: null });
  });

  it('keeps a selection that is still in the run, whatever the caller would open', () => {
    expect(resolveSelection({ findingUid: 'b', page: 4 }, run, 'c')).toEqual({ findingUid: 'b', page: 4 });
  });

  it('does not keep a selection the run no longer holds', () => {
    expect(resolveSelection({ findingUid: 'x', page: 4 }, run, 'c')).toEqual({ findingUid: 'c', page: null });
  });

  it('opens nothing when the screen shows nothing to open, and still the run’s first when the caller has no order', () => {
    expect(resolveSelection(null, run, null)).toBeNull();
    expect(resolveSelection(null, run)).toEqual({ findingUid: 'a', page: null });
    expect(resolveSelection(null, run, 'not-in-the-run')).toBeNull();
    expect(resolveSelection(null, [], 'a')).toBeNull();
    expect(selectFinding('a')).toEqual({ findingUid: 'a', page: null });
  });
});

describe('«Разбор» opens the first finding that waits', () => {
  it('opens the waiting finding, not the run’s first, and writes it to the address', async () => {
    await open('', HALF_DECIDED());
    expect(opened(live!.markup())).toBe(WAITING);
    expect(currentSearch()).toBe(`finding=${WAITING}`);
    expect(writtenAddresses()).toEqual([`finding=${WAITING}`]);
    // `D-341`: null as the state, the form Next syncs to `useSearchParams`; and the entry is replaced, not added to.
    expect(writtenStates).toEqual([null]);
    expect(writtenHow).toEqual(['replace']);
  });

  it('keeps the other parameters of the address when it writes the finding', async () => {
    await open('verdict=all&severity=all&foo=bar', HALF_DECIDED());
    expect(currentSearch()).toBe(`verdict=all&severity=all&foo=bar&finding=${WAITING}`);
  });

  it('stays on the opened finding when a decision moves it among the rows', async () => {
    const { client } = await open('', HALF_DECIDED());
    expect(opened(live!.markup())).toBe(WAITING);
    // The reader accepts it: the list re-reads, and the finding now stands among the accepted rows; the next waiting one is first shown.
    await live!.settle(async () => {
      seed(client, [
        withVerdict(ACCEPTED, 'accepted'),
        withVerdict(REJECTED, 'rejected'),
        withVerdict(WAITING, 'accepted'),
        withVerdict(ALSO_WAITING, 'pending'),
      ]);
    });
    expect(opened(live!.markup())).toBe(WAITING);
    expect(currentSearch()).toBe(`finding=${WAITING}`);
    expect(writtenAddresses()).toEqual([`finding=${WAITING}`]);
  });

  it('leaves a finding the address names alone', async () => {
    await open(`finding=${ACCEPTED}`, HALF_DECIDED());
    expect(opened(live!.markup())).toBe(ACCEPTED);
    expect(writtenAddresses()).toEqual([]);
  });

  it('replaces a link to a finding the run does not have by the waiting one', async () => {
    await open(`finding=${ABSENT}`, HALF_DECIDED());
    expect(opened(live!.markup())).toBe(WAITING);
    expect(currentSearch()).toBe(`finding=${WAITING}`);
  });

  it('opens the first row of what a verdict filter shows', async () => {
    await open('verdict=rejected', HALF_DECIDED());
    expect(opened(live!.markup())).toBe(REJECTED);
    expect(currentSearch()).toBe(`verdict=rejected&finding=${REJECTED}`);
  });

  it('opens the run’s first finding when every one of them waits', async () => {
    await open('', [withVerdict(WAITING, 'pending'), withVerdict(ALSO_WAITING, 'pending')]);
    expect(opened(live!.markup())).toBe(WAITING);
  });

  it('opens nothing in the table, and writes nothing', async () => {
    await open('view=table', HALF_DECIDED());
    expect(opened(live!.markup())).toBeNull();
    expect(live!.markup()).not.toContain('data-finding-expansion');
    expect(writtenAddresses()).toEqual([]);
  });

  it('opens the waiting finding when the reader turns from the table to the list', async () => {
    const { element } = await open('view=table', HALF_DECIDED());
    await live!.update(element(''));
    expect(opened(live!.markup())).toBe(WAITING);
    expect(currentSearch()).toBe(`finding=${WAITING}`);
  });
});
