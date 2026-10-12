/**
 * `W54-WORKERS-WEB` — the intake command hook: its own operation, the caller's key on every
 * send, no automatic retry, and every execution read refreshed after it succeeds.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, setWorkerIntake: vi.fn() };
});

import { queryKeys, setWorkerIntake } from '@/shared/api';
import { useSetWorkerIntake } from '@/features/set-worker-intake';

const WORKER_ID = 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
const KEY = 'ik-one-intake-intent';

type Captured<T, U> = {
  mutationFn: (input: T) => Promise<U>;
  onSuccess: (result: U) => void;
  retry: boolean;
};

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('setWorkerIntake', () => {
  it('sends the intent through its own operation and reuses the caller key on a repeat', async () => {
    const answer = { worker_id: WORKER_ID, intake_enabled: false };
    vi.mocked(setWorkerIntake).mockResolvedValue({ data: answer } as never);
    const command = useSetWorkerIntake() as unknown as Captured<
      { workerId: string; enabled: boolean; idempotencyKey: string }, typeof answer>;
    expect(command.retry).toBe(false);
    const intent = { workerId: WORKER_ID, enabled: false, idempotencyKey: KEY };
    const result = await command.mutationFn(intent);
    await command.mutationFn(intent);
    expect(vi.mocked(setWorkerIntake).mock.calls).toEqual([
      [{ path: { worker_id: WORKER_ID }, body: { enabled: false }, idempotencyKey: KEY }],
      [{ path: { worker_id: WORKER_ID }, body: { enabled: false }, idempotencyKey: KEY }],
    ]);
    expect(result).toEqual(answer);
  });

  it('refreshes every execution read, the worker list and the queue among them', () => {
    const command = useSetWorkerIntake() as unknown as Captured<unknown, unknown>;
    command.onSuccess({});
    expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.execution.all() }]]);
    // The worker keys live under that root, so the invalidation reaches them.
    expect(queryKeys.execution.workers().slice(0, 1)).toEqual(queryKeys.execution.all());
  });
});
