/**
 * The dashboard summary is filed per project, and every invalidation still reaches all of them.
 *
 * `UI-PARITY-P0A` / `UI-PARITY-01` «Project context»: `project_uid` is in every optional screen's
 * cache key. The dashboard's twelve mutation hooks invalidate `queryKeys.dashboard.summary()` and
 * are not edited by this change, so that call has to stay the PREFIX of every project's entry as
 * well as the entry «Все проекты» is filed under. These tests hold both halves, and each can fail:
 * a key built without the project collides two projects; a key that is not a prefix is skipped by
 * the invalidation.
 */

import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

describe('the dashboard summary key carries the project', () => {
  it('files «Все проекты» under the bare prefix and a project under the prefix plus the project', () => {
    expect(queryKeys.dashboard.summary()).toEqual(['dashboard', 'summary']);
    expect(queryKeys.dashboard.summary(A)).toEqual(['dashboard', 'summary', { project: A }]);
  });

  it('gives two projects two keys, and neither is the key of «Все проекты»', () => {
    const keys = [queryKeys.dashboard.summary(), queryKeys.dashboard.summary(A), queryKeys.dashboard.summary(B)].map((key) =>
      JSON.stringify(key),
    );
    expect(new Set(keys).size).toBe(3);
  });

  it('spells «Все проекты» one way: null, undefined and an empty string name no project', () => {
    expect(queryKeys.dashboard.summary(null)).toEqual(queryKeys.dashboard.summary());
    expect(queryKeys.dashboard.summary(undefined)).toEqual(queryKeys.dashboard.summary());
    expect(queryKeys.dashboard.summary('')).toEqual(queryKeys.dashboard.summary());
  });

  it('keeps the dashboard root, so the key-shape contract that the first segment is a namespace holds', () => {
    expect(queryKeys.dashboard.summary(A)[0]).toBe('dashboard');
  });
});

describe('the invalidation every mutation makes reaches every project', () => {
  function filled(): QueryClient {
    const client = new QueryClient();
    client.setQueryData(queryKeys.dashboard.summary(), { scope: 'all' });
    client.setQueryData(queryKeys.dashboard.summary(A), { scope: A });
    client.setQueryData(queryKeys.dashboard.summary(B), { scope: B });
    client.setQueryData(queryKeys.projects.all(), { not: 'the dashboard' });
    return client;
  }

  it('marks «Все проекты» and both projects stale with the call the twelve hooks already make', async () => {
    const client = filled();
    await client.invalidateQueries({ queryKey: queryKeys.dashboard.summary(), refetchType: 'none' });
    for (const key of [queryKeys.dashboard.summary(), queryKeys.dashboard.summary(A), queryKeys.dashboard.summary(B)]) {
      expect(client.getQueryState(key)?.isInvalidated, JSON.stringify(key)).toBe(true);
    }
    expect(client.getQueryState(queryKeys.projects.all())?.isInvalidated).toBe(false);
  });

  it('can fail: invalidating ONE project does not touch the other or «Все проекты»', async () => {
    const client = filled();
    await client.invalidateQueries({ queryKey: queryKeys.dashboard.summary(A), refetchType: 'none' });
    expect(client.getQueryState(queryKeys.dashboard.summary(A))?.isInvalidated).toBe(true);
    expect(client.getQueryState(queryKeys.dashboard.summary(B))?.isInvalidated).toBe(false);
    expect(client.getQueryState(queryKeys.dashboard.summary())?.isInvalidated).toBe(false);
  });

  it('reads each project back its own entry, never the neighbour’s', () => {
    const client = filled();
    expect(client.getQueryData(queryKeys.dashboard.summary(A))).toEqual({ scope: A });
    expect(client.getQueryData(queryKeys.dashboard.summary(B))).toEqual({ scope: B });
    expect(client.getQueryData(queryKeys.dashboard.summary())).toEqual({ scope: 'all' });
  });
});

describe('the decision journal key carries the project among its filters', () => {
  it('gives the same filters under two projects two keys, and the prefix reaches both', async () => {
    const withA = queryKeys.findings.journal({ project_uid: A, limit: 50 });
    const withB = queryKeys.findings.journal({ project_uid: B, limit: 50 });
    const without = queryKeys.findings.journal({ limit: 50 });
    expect(new Set([withA, withB, without].map((key) => JSON.stringify(key))).size).toBe(3);

    const client = new QueryClient();
    for (const key of [withA, withB, without]) client.setQueryData(key, { items: [] });
    await client.invalidateQueries({ queryKey: queryKeys.findings.journal(), refetchType: 'none' });
    for (const key of [withA, withB, without]) {
      expect(client.getQueryState(key)?.isInvalidated, JSON.stringify(key)).toBe(true);
    }
  });
});
