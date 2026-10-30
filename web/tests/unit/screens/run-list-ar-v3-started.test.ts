/**
 * Old AR v3 group addresses remain readable, while the owner restored an ordinary AR start.
 *
 * The real control holds a mutation a static render cannot settle, and what is under test is what
 * a recorder checks that installing the old pack cannot mount the removed default six-check
 * control. Ordinary start preflight/approval behavior is covered by the cost-flow tests.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress, looksLikeArV3GroupId } from '@/entities/audit-run';

const captured = vi.hoisted(() => ({ props: null as null | { onStarted?: (group: unknown) => void } }));
const navigation = vi.hoisted(() => ({ pushed: [] as string[] }));

// The harness mounts a router whose `push` is a no-op; the address the run list pushes is the
// subject here, so `useRouter` answers with a recorder instead.
vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useRouter: () => ({ push: (href: string) => navigation.pushed.push(href) }),
}));

vi.mock('@/features/start-ar-v3-group', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    StartArV3GroupControl: (props: { onStarted?: (group: unknown) => void }) => {
      captured.props = props;
      return null;
    },
  };
});

import { RunList } from '@/widgets/run-list';

import { GROUP_ID } from '../analysis-settings/ar-v3-beta-review-fixtures';
import { NOT_INSTALLED_PACK, installedPackFixture } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient, renderScreen } from './harness';

const PACK = queryKeys.runs.arV3PackStatus();

function listMarkup(pack: unknown): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
    items: [], page: { next_cursor: null },
  });
  client.setQueryData(PACK, pack);
  return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, sectionCode: 'AR' }));
}

describe('old group review addresses and the restored ordinary AR start', () => {
  it('builds the address the settings route reads, and only for the group it was given', () => {
    const address = arV3GroupReviewAddress(GROUP_ID);
    expect(address).toBe(`/analysis-settings?group_id=${GROUP_ID}`);
    const url = new URL(address, 'http://stand.invalid');
    expect(url.pathname).toBe('/analysis-settings');
    expect(looksLikeArV3GroupId(url.searchParams.get('group_id'))).toBe(true);
    expect(url.searchParams.get('group_id')).toBe(GROUP_ID);
  });

  it('keeps ordinary AR preflight available with an installed pack and requires cost approval before start', () => {
    navigation.pushed.length = 0;
    captured.props = null;
    const markup = listMarkup(installedPackFixture());
    expect(captured.props, 'an installed old pack must not mount the default six-check start').toBeNull();
    expect(markup).toContain('data-start-run-control="true"');
    expect(markup).toContain('>Оценить стоимость</button>');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Запустить прогон<\/button>/);
    expect(markup).not.toContain('data-cost-approval');
    expect(markup).not.toContain('data-ar-v3-group-start');
    expect(navigation.pushed).toEqual([]);
  });

  it('mounts no six-check control when the pack is not installed', () => {
    captured.props = null;
    listMarkup(NOT_INSTALLED_PACK);
    expect(captured.props).toBeNull();
  });
});
