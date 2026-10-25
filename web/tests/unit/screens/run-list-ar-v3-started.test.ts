/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: a group started from the version's run list opens its review.
 *
 * The real control holds a mutation a static render cannot settle, and what is under test is what
 * the run list hands it, so a recorder stands in for it in this file only. The other file renders
 * the real control.
 */

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { ArV3BetaGroup } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT, arV3GroupReviewAddress, looksLikeArV3GroupId } from '@/entities/audit-run';

const captured = vi.hoisted(() => ({ props: null as null | { onStarted?: (group: unknown) => void } }));

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
import { newClient, renderWith } from './harness';

const PACK = queryKeys.runs.arV3PackStatus();

function listMarkup(pack: unknown, push: (href: string) => void): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
    items: [], page: { next_cursor: null },
  });
  client.setQueryData(PACK, pack);
  const router = {
    push, replace: () => {}, back: () => {}, forward: () => {}, refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
  return renderWith(client, createElement(
    AppRouterContext.Provider,
    { value: router },
    createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
  ));
}

describe('a started group opens its review on the settings screen', () => {
  it('builds the address the settings route reads, and only for the group it was given', () => {
    const address = arV3GroupReviewAddress(GROUP_ID);
    expect(address).toBe(`/analysis-settings?group_id=${GROUP_ID}`);
    const url = new URL(address, 'http://stand.invalid');
    expect(url.pathname).toBe('/analysis-settings');
    expect(looksLikeArV3GroupId(url.searchParams.get('group_id'))).toBe(true);
    expect(url.searchParams.get('group_id')).toBe(GROUP_ID);
  });

  it('pushes that address when the control reports a started group', () => {
    const pushed: string[] = [];
    captured.props = null;
    listMarkup(installedPackFixture(), (href) => pushed.push(href));
    expect(captured.props, 'the run list never mounted the six-check control').not.toBeNull();
    captured.props!.onStarted!({ group_id: GROUP_ID } as ArV3BetaGroup);
    expect(pushed).toEqual([`/analysis-settings?group_id=${GROUP_ID}`]);
  });

  it('mounts no control, and so pushes nothing, when the pack is not installed', () => {
    captured.props = null;
    listMarkup(NOT_INSTALLED_PACK, () => {});
    expect(captured.props).toBeNull();
  });
});
