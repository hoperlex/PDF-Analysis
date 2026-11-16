/**
 * «Назначения» follows the header's project (`R-151m`).
 *
 * The screen is of the class that follows the header: with `?project=` the assignment list is the server's list for
 * that project (`listAssignments` `project_uid`), without it the screen opens on the object the account chose last
 * (`UIP-G-06`: `getMe`'s `last_project_uid`), and where there is none, or `?project=all` chose it, it says «Все объекты» and
 * filters nothing.
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { Account } from '@/shared/api';
import { SCREEN_REGISTRY } from '@/shared/config';
import { DispatcherPage } from '@/_pages/dispatcher';
import { AssignmentBoard } from '@/widgets/assignment-board';

import { newClient, renderWith } from '../screens/harness';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OTHER = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

/** The element under the address a router would have mounted: a pathname and a query string. */
function atAddress(query: string, element: ReactElement): ReactElement {
  return createElement(
    PathnameContext.Provider,
    { value: '/dispatcher' },
    createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, element),
  );
}

/** A client that knows the account and what it chose last (`null`: nothing). */
function clientWithLast(lastProject: string | null) {
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles: ['expert'], last_project_uid: lastProject } as unknown as Account);
  return client;
}

function listFilters(client: ReturnType<typeof newClient>): unknown[] {
  return client.getQueryCache().getAll()
    .filter((query) => query.queryKey[0] === 'assignments' && query.queryKey[1] === 'list')
    .map((query) => query.queryKey[2]);
}

describe('the dispatcher and the header’s project', () => {
  it('is registered as a screen that follows the header', () => {
    expect(SCREEN_REGISTRY.find((row) => row.address === '/dispatcher')?.projectScope).toBe('optional');
  });

  it('asks the server for one project’s assignments when a project is chosen', () => {
    const client = newClient();
    renderWith(client, createElement(AssignmentBoard, { roles: ['admin'], viewerUid: null, experts: [], projectUid: PROJECT }));
    expect(listFilters(client)).toEqual([expect.objectContaining({ project_uid: PROJECT })]);
  });

  it('filters nothing without a project, and says «Все объекты»', () => {
    const client = newClient();
    renderWith(client, createElement(AssignmentBoard, { roles: ['admin'], viewerUid: null, experts: [] }));
    expect(listFilters(client)).toEqual([expect.not.objectContaining({ project_uid: expect.anything() })]);
    const markup = renderWith(newClient(), createElement(DispatcherPage, { roles: ['expert'] }));
    expect(markup).toContain('data-dispatcher-scope="all"');
    expect(markup).toContain('Все объекты');
  });

  it('opens on the account’s last object for a silent address, and asks the server for that object’s assignments', () => {
    const client = clientWithLast(PROJECT);
    const markup = renderWith(client, atAddress('', createElement(DispatcherPage, { roles: ['expert'] })));
    expect(markup).toContain('data-dispatcher-scope="project"');
    expect(listFilters(client)).toEqual([expect.objectContaining({ project_uid: PROJECT })]);
  });

  it('?project=<uid> beats the last object, and ?project=all beats it into «Все объекты»', () => {
    const chosen = clientWithLast(PROJECT);
    renderWith(chosen, atAddress(`project=${OTHER}`, createElement(DispatcherPage, { roles: ['expert'] })));
    expect(listFilters(chosen)).toEqual([expect.objectContaining({ project_uid: OTHER })]);

    const all = clientWithLast(PROJECT);
    const markup = renderWith(all, atAddress('project=all', createElement(DispatcherPage, { roles: ['expert'] })));
    expect(markup).toContain('data-dispatcher-scope="all"');
    expect(listFilters(all)).toEqual([expect.not.objectContaining({ project_uid: expect.anything() })]);
  });

  it('keeps «Все объекты» when the account chose none, and the way out of the last object is ?project=all', () => {
    const markup = renderWith(clientWithLast(null), atAddress('', createElement(DispatcherPage, { roles: ['expert'] })));
    expect(markup).toContain('data-dispatcher-scope="all"');
    const out = renderWith(clientWithLast(PROJECT), atAddress('x=1', createElement(DispatcherPage, { roles: ['expert'] })));
    expect(out).toMatch(/<a [^>]*href="\/dispatcher\?x=1&(?:amp;)?project=all"[^>]*>Все объекты<\/a>/);
  });
});
