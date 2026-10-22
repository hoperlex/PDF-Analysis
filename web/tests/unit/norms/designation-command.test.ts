/**
 * `W55A-WEB-NORMS` — the designation command hook: its own operation with the caller's
 * belief about the current snapshot, no automatic retry, and every norms read refreshed when
 * the request settles — after a success, and after a refusal, whose list is out of date.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

// The hook keeps the request in flight in a ref (`WEB-FOLLOWUPS-02`); outside a render there is
// no instance, so a plain holder stands in, as in the other command suites.
vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, useRef: (value: unknown) => ({ current: value }) };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, setCurrentNormSnapshot: vi.fn() };
});

import { queryKeys, setCurrentNormSnapshot } from '@/shared/api';
import { useSetCurrentSnapshot } from '@/features/set-current-snapshot';

import { CURRENT_SNAPSHOT_ID, QUALIFIED_SNAPSHOT_ID } from './fixtures';

type Captured<T, U> = {
  mutationFn: (input: T) => Promise<U>;
  onSettled: () => void;
  onSuccess?: unknown;
  retry: boolean;
};

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('setCurrentNormSnapshot', () => {
  it('sends the target and the expected current snapshot, and never retries on its own', async () => {
    const answer = { norms_snapshot_id: QUALIFIED_SNAPSHOT_ID };
    vi.mocked(setCurrentNormSnapshot).mockResolvedValue({ data: answer } as never);
    const command = useSetCurrentSnapshot() as unknown as Captured<
      { normsSnapshotId: string; expectedCurrent: string | null }, typeof answer>;
    expect(command.retry).toBe(false);
    const result = await command.mutationFn({ normsSnapshotId: QUALIFIED_SNAPSHOT_ID, expectedCurrent: CURRENT_SNAPSHOT_ID });
    await command.mutationFn({ normsSnapshotId: QUALIFIED_SNAPSHOT_ID, expectedCurrent: null });
    expect(vi.mocked(setCurrentNormSnapshot).mock.calls).toEqual([
      [{ body: { norms_snapshot_id: QUALIFIED_SNAPSHOT_ID, expected_current: CURRENT_SNAPSHOT_ID } }],
      [{ body: { norms_snapshot_id: QUALIFIED_SNAPSHOT_ID, expected_current: null } }],
    ]);
    expect(result).toEqual(answer);
  });

  it('re-reads every norms answer when the request settles, success or refusal alike', () => {
    const command = useSetCurrentSnapshot() as unknown as Captured<unknown, unknown>;
    expect(command.onSuccess, 'a success-only refresh would leave a stale refusal on a stale list').toBeUndefined();
    command.onSettled();
    expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.norms.all() }]]);
    // Every norms key lives under that root, so the invalidation reaches the list and history.
    expect(queryKeys.norms.snapshots().slice(0, 1)).toEqual(queryKeys.norms.all());
    expect(queryKeys.norms.events().slice(0, 1)).toEqual(queryKeys.norms.all());
  });
});
