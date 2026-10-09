import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({
  invalidations: [] as unknown[],
  writes: [] as unknown[],
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    setQueryData: (...args: unknown[]) => calls.writes.push(args),
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    cancelRun: vi.fn(),
    reauditRun: vi.fn(),
    setJobPriority: vi.fn(),
    setExecutionPaused: vi.fn(),
  };
});

import { cancelRun, queryKeys, reauditRun, setExecutionPaused, setJobPriority } from '@/shared/api';
import { useCancelRun } from '@/features/cancel-run';
import { useReauditRun } from '@/features/reaudit-run';
import { useSetJobPriority } from '@/features/set-job-priority';
import { usePauseExecution } from '@/features/pause-execution';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const JOB_ID = 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const KEY = 'ik-one-intent';
const RUN = { run_id: RUN_ID, project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8F' };

type Captured<T, U> = {
  mutationFn: (input: T) => Promise<U>;
  onSuccess: (result: U) => void;
  retry: boolean;
};

beforeEach(() => {
  calls.invalidations.length = 0;
  calls.writes.length = 0;
  vi.clearAllMocks();
});

describe('sealed execution commands', () => {
  it('reuses the caller key on an explicit repeat of cancel and invalidates all affected reads', async () => {
    vi.mocked(cancelRun).mockResolvedValue({ data: RUN } as never);
    const command = useCancelRun() as unknown as Captured<{ runId: string; idempotencyKey: string }, typeof RUN>;
    expect(command.retry).toBe(false);
    const intent = { runId: RUN_ID, idempotencyKey: KEY };
    const answer = await command.mutationFn(intent);
    await command.mutationFn(intent);
    expect(vi.mocked(cancelRun).mock.calls).toEqual([
      [{ path: { run_id: RUN_ID }, idempotencyKey: KEY }],
      [{ path: { run_id: RUN_ID }, idempotencyKey: KEY }],
    ]);
    command.onSuccess(answer);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.execution.all() }]);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.runs.all() }]);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.dashboard.summary() }]);
  });

  it('uses a distinct re-audit operation and the same cache invalidation boundary', async () => {
    vi.mocked(reauditRun).mockResolvedValue({ data: RUN } as never);
    const command = useReauditRun() as unknown as Captured<{ runId: string; idempotencyKey: string }, typeof RUN>;
    const answer = await command.mutationFn({ runId: RUN_ID, idempotencyKey: KEY });
    expect(reauditRun).toHaveBeenCalledWith({ path: { run_id: RUN_ID }, idempotencyKey: KEY });
    command.onSuccess(answer);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.execution.all() }]);
    expect(calls.invalidations).toContainEqual([{ queryKey: queryKeys.dashboard.summary() }]);
  });

  it('sends the queued priority and pause values through their own operations', async () => {
    const item = { job_id: JOB_ID, run_id: RUN_ID, state: 'queued', priority: 7 };
    vi.mocked(setJobPriority).mockResolvedValue({ data: item } as never);
    vi.mocked(setExecutionPaused).mockResolvedValue({ data: { paused: true, changed_at: '2026-10-09T10:00:00Z' } } as never);
    const priority = useSetJobPriority() as unknown as Captured<
      { jobId: string; priority: number; idempotencyKey: string }, typeof item>;
    const pause = usePauseExecution() as unknown as Captured<
      { paused: boolean; idempotencyKey: string }, { paused: boolean; changed_at: string }>;
    const changed = await priority.mutationFn({ jobId: JOB_ID, priority: 7, idempotencyKey: KEY });
    const paused = await pause.mutationFn({ paused: true, idempotencyKey: KEY });
    expect(setJobPriority).toHaveBeenCalledWith({ path: { job_id: JOB_ID }, body: { priority: 7 }, idempotencyKey: KEY });
    expect(setExecutionPaused).toHaveBeenCalledWith({ body: { paused: true }, idempotencyKey: KEY });
    priority.onSuccess(changed);
    pause.onSuccess(paused);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.execution.all() }],
      [{ queryKey: queryKeys.execution.all() }],
    ]);
    expect(priority.retry).toBe(false);
    expect(pause.retry).toBe(false);
  });
});
