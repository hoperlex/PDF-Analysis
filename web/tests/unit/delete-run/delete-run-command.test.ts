/**
 * `RUN-DELETE-01`: the command behind «Удалить прогон» (`useDeleteRun`) and the sentences under its confirmation.
 *
 * The hook is read through the configuration it hands to `useMutation`, as `execution-commands.test.ts` reads the cancel command: what is
 * sent, under which key, and which reads are asked for again.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as { queryKey?: readonly unknown[]; predicate?: (query: { queryHash: string }) => boolean; refetchType?: string }[] }));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) => configuration,
    useQueryClient: () => ({
      invalidateQueries: (filters: (typeof calls.invalidations)[number]) => { calls.invalidations.push(filters); return Promise.resolve(); },
    }),
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, deleteRun: vi.fn() };
});

import { hashKey } from '@tanstack/react-query';

import type { ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError, deleteRun, queryKeys } from '@/shared/api';
import {
  DELETE_RUN_GONE,
  DELETE_RUN_NOT_DELETABLE,
  deleteFailureText,
  useDeleteRun,
} from '@/features/delete-run';

import { RUN_ID, VERSION_UID } from '../review/fixtures';

const OTHER_RUN_ID = `${RUN_ID.slice(0, -1)}9`;
const KEY = 'ik-one-intent';
const RUN = { run_id: RUN_ID, project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', version_uid: VERSION_UID, state: 'failed' };

type Captured = {
  mutationFn: (input: { runId: string; idempotencyKey: string }) => Promise<typeof RUN>;
  onSuccess: (result: typeof RUN) => void;
  onError: (error: unknown, input: { runId: string; idempotencyKey: string }) => void;
  retry: boolean;
};

function refusal(status: number, code: ErrorEnvelope['error_code']): ApiError {
  return new ApiError(status, {
    contract_version: '1.52.0' as ErrorEnvelope['contract_version'],
    error_code: code,
    message: 'Refused',
    correlation_id: 'cid-delete-1',
    retryable: false,
  }, 'cid-delete-1');
}

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('the delete command', () => {
  it('sends deleteRun under the caller key, the same key on an explicit repeat, and never retries by itself', async () => {
    vi.mocked(deleteRun).mockResolvedValue({ data: RUN } as never);
    const command = useDeleteRun() as unknown as Captured;
    expect(command.retry).toBe(false);
    const intent = { runId: RUN_ID, idempotencyKey: KEY };
    const answer = await command.mutationFn(intent);
    await command.mutationFn(intent);
    expect(answer).toEqual(RUN);
    expect(vi.mocked(deleteRun).mock.calls).toEqual([
      [{ path: { run_id: RUN_ID }, idempotencyKey: KEY }],
      [{ path: { run_id: RUN_ID }, idempotencyKey: KEY }],
    ]);
  });

  it('on success reads the lists, the queue and the dashboard again, but not the status of the run it deleted', () => {
    const command = useDeleteRun() as unknown as Captured;
    command.onSuccess(RUN);
    // The deleted run's own status is only marked stale: the run page is still open while it leaves, and a read would answer 404 into it.
    expect(calls.invalidations).toContainEqual({ queryKey: queryKeys.runs.detail(RUN_ID as never), refetchType: 'none' });
    expect(calls.invalidations).toContainEqual({ queryKey: queryKeys.execution.all() });
    expect(calls.invalidations).toContainEqual({ queryKey: queryKeys.dashboard.summary() });
    const runs = calls.invalidations.filter((filters) => JSON.stringify(filters.queryKey) === JSON.stringify(queryKeys.runs.all()));
    expect(runs).toHaveLength(1);
    const predicate = runs[0]?.predicate as (query: { queryHash: string }) => boolean;
    const hash = (key: readonly unknown[]) => ({ queryHash: hashKey(key) });
    // A page of the run list is read again; the list of every version, the findings of the run and another run's status too.
    expect(predicate(hash(queryKeys.runs.list(VERSION_UID as never, undefined, 50)))).toBe(true);
    expect(predicate(hash(queryKeys.runs.findings(RUN_ID as never)))).toBe(true);
    expect(predicate(hash(queryKeys.runs.detail(OTHER_RUN_ID as never)))).toBe(true);
    expect(predicate(hash(queryKeys.runs.detail(RUN_ID as never)))).toBe(false);
  });

  it('on a 404 (someone deleted the run first) reads the lists again, and on any other refusal reads nothing', () => {
    const command = useDeleteRun() as unknown as Captured;
    command.onError(refusal(409, 'state_transition_not_allowed'), { runId: RUN_ID, idempotencyKey: KEY });
    command.onError(new TransportError('The request produced no answer.'), { runId: RUN_ID, idempotencyKey: KEY });
    expect(calls.invalidations).toEqual([]);
    command.onError(refusal(404, 'not_found'), { runId: RUN_ID, idempotencyKey: KEY });
    expect(calls.invalidations.map((filters) => filters.queryKey)).toEqual([
      queryKeys.runs.all(), queryKeys.execution.all(), queryKeys.dashboard.summary(),
    ]);
  });
});

describe('the sentence under the confirmation', () => {
  it('says a run that is not partial, failed or cancelled cannot be deleted, in the owner\'s words', () => {
    expect(deleteFailureText(refusal(409, 'state_transition_not_allowed'))).toBe(
      'Этот прогон удалить нельзя: он не частичный, не с ошибкой и не отменён.',
    );
    expect(DELETE_RUN_NOT_DELETABLE).toBe('Этот прогон удалить нельзя: он не частичный, не с ошибкой и не отменён.');
  });

  it('says a run that is gone is gone', () => {
    expect(deleteFailureText(refusal(404, 'not_found'))).toBe(DELETE_RUN_GONE);
  });

  it('puts every other failure behind «Прогон не удалён:» in the shared reading, never a thrown value\'s own text', () => {
    const forbidden = deleteFailureText(refusal(403, 'permission_denied'));
    expect(forbidden.startsWith('Прогон не удалён: ')).toBe(true);
    expect(forbidden).not.toContain('Refused');
    expect(deleteFailureText(new Error('SELECT secret'))).toContain('Прогон не удалён: Непредвиденная ошибка');
    expect(deleteFailureText(new Error('SELECT secret'))).not.toContain('secret');
  });
});
