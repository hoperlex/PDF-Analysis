/**
 * `WEB-FOLLOWUPS-02` / `D-195`: a second press of «Назначить текущим» while the first is in
 * flight sends no second `POST`.
 *
 * The designation is a compare-and-set without a key; a repeat was answered as a replay (the
 * target is already current) or as `stale_current_snapshot`, and the screen showed the later
 * answer over a designation the administrator had just made. A press that finds the same intent
 * (the target and the current snapshot the screen believed) in flight now joins the request
 * already sent. The gate reopens when it settles: a deliberate press afterwards, of another
 * target or against a newly read current, is a new request.
 *
 * Exercised through the hook's configuration on ONE instance, as `designation-command.test.ts`
 * does.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({ invalidateQueries: () => Promise.resolve() }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, useRef: (value: unknown) => ({ current: value }) };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, setCurrentNormSnapshot: vi.fn() };
});

import type { NormCurrentSnapshot } from '@/shared/api';
import { setCurrentNormSnapshot } from '@/shared/api';
import type { SetCurrentSnapshotCommand } from '@/features/set-current-snapshot';
import { designationIntent, useSetCurrentSnapshot } from '@/features/set-current-snapshot';

import { CURRENT_SNAPSHOT_ID, QUALIFIED_SNAPSHOT_ID } from './fixtures';

type Captured = { mutationFn: (input: SetCurrentSnapshotCommand) => Promise<NormCurrentSnapshot> };

const DESIGNATE: SetCurrentSnapshotCommand = {
  normsSnapshotId: QUALIFIED_SNAPSHOT_ID,
  expectedCurrent: CURRENT_SNAPSHOT_ID,
};

const post = vi.mocked(setCurrentNormSnapshot);

function holdOpen() {
  const handle = { settle: (_value: unknown) => {}, fail: (_error: unknown) => {} };
  post.mockImplementation(
    () =>
      new Promise((resolve, reject) => {
        handle.settle = resolve;
        handle.fail = reject;
      }) as never,
  );
  return handle;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('a double press of «Назначить текущим»', () => {
  it('sends ONE request, and both presses get its answer', async () => {
    const open = holdOpen();
    const hook = useSetCurrentSnapshot() as unknown as Captured;
    const first = hook.mutationFn(DESIGNATE);
    const second = hook.mutationFn(DESIGNATE);
    expect(post).toHaveBeenCalledTimes(1);
    const stored = { norms_snapshot_id: QUALIFIED_SNAPSHOT_ID };
    open.settle({ data: stored });
    await expect(first).resolves.toBe(stored);
    await expect(second).resolves.toBe(stored);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('gives both presses the same refusal', async () => {
    const open = holdOpen();
    const hook = useSetCurrentSnapshot() as unknown as Captured;
    const first = hook.mutationFn(DESIGNATE);
    const second = hook.mutationFn(DESIGNATE);
    const refusal = new Error('stale_current_snapshot');
    open.fail(refusal);
    await expect(first).rejects.toBe(refusal);
    await expect(second).rejects.toBe(refusal);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('sends a new request for a press after the first settled', async () => {
    post.mockResolvedValue({ data: { norms_snapshot_id: QUALIFIED_SNAPSHOT_ID } } as never);
    const hook = useSetCurrentSnapshot() as unknown as Captured;
    await hook.mutationFn(DESIGNATE);
    await hook.mutationFn(DESIGNATE);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('reopens after a refusal', async () => {
    post.mockRejectedValueOnce(new Error('stale_current_snapshot'));
    post.mockResolvedValue({ data: {} } as never);
    const hook = useSetCurrentSnapshot() as unknown as Captured;
    await expect(hook.mutationFn(DESIGNATE)).rejects.toThrow('stale_current_snapshot');
    await hook.mutationFn(DESIGNATE);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('does not join a request for another target, nor one against another believed current', () => {
    holdOpen();
    const hook = useSetCurrentSnapshot() as unknown as Captured;
    void hook.mutationFn(DESIGNATE);
    void hook.mutationFn({ ...DESIGNATE, normsSnapshotId: CURRENT_SNAPSHOT_ID });
    void hook.mutationFn({ ...DESIGNATE, expectedCurrent: null });
    expect(post).toHaveBeenCalledTimes(3);
  });

  it('tells the target and the believed current apart, and none from a missing one', () => {
    const intents = [
      DESIGNATE,
      { ...DESIGNATE, normsSnapshotId: CURRENT_SNAPSHOT_ID },
      { ...DESIGNATE, expectedCurrent: null },
    ].map(designationIntent);
    expect(new Set(intents).size).toBe(intents.length);
  });
});
