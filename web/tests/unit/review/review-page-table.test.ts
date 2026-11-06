/**
 * `UI-A-68`: «Разбор» in its table view. The address decides (`?view=table`, `?finding=`): the list keeps the
 * open finding beside it as ever; the table is one column, opens a row only when it is asked to (as the original's
 * does), and puts the finding under that row. The export bar stands over the findings in both.
 */

import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const navigation = vi.hoisted(() => ({ search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

import { queryKeys } from '@/shared/api';
import { ReviewPage } from '@/_pages/review';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, RUN_ID, finding, findingDetail, runStatus } from './fixtures';

afterEach(() => {
  navigation.search = '';
});

const FIRST = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QB1';
const SECOND = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QB2';

function page(search: string): string {
  navigation.search = search;
  const client = newClient();
  const envelope = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID }));
  client.setQueryData(queryKeys.runs.findings(RUN_ID), {
    data: { items: [finding({ finding_uid: FIRST }), finding({ finding_uid: SECOND })], page: envelope },
  });
  for (const uid of [FIRST, SECOND]) {
    client.setQueryData(queryKeys.findings.detail(uid), { data: findingDetail({ finding_uid: uid }) });
    client.setQueryData(queryKeys.findings.decisions(uid), { data: { items: [], page: envelope } });
  }
  return renderWith(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

describe('the review page by its address', () => {
  it('keeps the list and the open finding beside it without a view', () => {
    const markup = page('');
    expect(markup).not.toContain('data-finding-table');
    expect(markup).toContain('am-review__detail');
    expect(markup).toContain(`data-finding-uid="${FIRST}"`);
  });

  it('draws the table at full width and opens nothing until a row is chosen', () => {
    const markup = page('view=table');
    expect(markup).toContain('data-finding-table');
    expect(markup).toContain('data-finding-view="table"');
    expect(markup).not.toContain('am-review__detail');
    expect(markup).not.toContain('data-finding-expansion');
    expect(markup).not.toContain('am-review__finding');
  });

  it('opens the finding the address names under its own row', () => {
    const markup = page(`view=table&finding=${SECOND}`);
    expect((markup.match(/data-finding-expansion=/g) ?? []).length).toBe(1);
    expect(markup).toContain(`data-finding-expansion="${SECOND}"`);
    expect(markup.indexOf(`data-row-key="${SECOND}"`)).toBeLessThan(markup.indexOf('data-finding-expansion'));
  });

  it('stands the file actions in the toolbar’s first row, before the verdict tally', () => {
    const markup = page('');
    expect(markup.indexOf('data-exportable')).toBeGreaterThan(markup.indexOf('data-finding-total'));
    expect(markup.indexOf('data-exportable')).toBeLessThan(markup.indexOf('data-verdict-tally'));
  });

  it('puts the file actions over the findings in either view', () => {
    for (const search of ['', 'view=table']) {
      const markup = page(search);
      const bar = markup.indexOf('data-exportable');
      expect(bar).toBeGreaterThan(-1);
      expect(bar).toBeLessThan(markup.indexOf('am-finding-list'));
    }
  });
});
