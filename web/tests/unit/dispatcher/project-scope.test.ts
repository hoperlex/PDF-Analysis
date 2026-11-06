/**
 * «Диспетчер» follows the header's project (`R-151m`).
 *
 * The screen is of the class that follows the header: with `?project=` the assignment list is the server's list for
 * that project (`listAssignments` `project_uid`), without it the screen says «Все проекты» and filters nothing. The
 * project lives in the address only.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SCREEN_REGISTRY } from '@/shared/config';
import { DispatcherPage } from '@/_pages/dispatcher';
import { AssignmentBoard } from '@/widgets/assignment-board';

import { newClient, renderWith } from '../screens/harness';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

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

  it('filters nothing without a project, and says «Все проекты»', () => {
    const client = newClient();
    renderWith(client, createElement(AssignmentBoard, { roles: ['admin'], viewerUid: null, experts: [] }));
    expect(listFilters(client)).toEqual([expect.not.objectContaining({ project_uid: expect.anything() })]);
    const markup = renderWith(newClient(), createElement(DispatcherPage, { roles: ['expert'] }));
    expect(markup).toContain('data-dispatcher-scope="all"');
    expect(markup).toContain('Все проекты');
  });
});
