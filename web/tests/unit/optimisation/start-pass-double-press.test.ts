/**
 * `WEB-FOLLOWUPS-02` / `D-195`: a second press of «Запустить проход» while the first is in
 * flight sends no second `POST`.
 *
 * Before the guard the hook sent the set twice under one idempotency key; the second reached
 * the server while the first was still executing and was answered `idempotency_key_in_progress`.
 * A press that finds its intent in flight now joins the request already sent and gets its
 * answer. The gate reopens when that request settles, so a deliberate press afterwards is a
 * new request, and the key rules of `W60-OPT-PROPOSALS-01` (one key per intent, reused after a
 * failure) are untouched.
 *
 * The hook is exercised through its configuration, as the command suites beside it do:
 * `useMutation` is the identity and `useRef` a plain holder, so the test holds the very
 * `mutationFn` the browser runs, on ONE hook instance, which is what a double press is.
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
  return { ...actual, startOptimisationPass: vi.fn() };
});

import type { OptimisationPass } from '@/shared/api';
import { startOptimisationPass } from '@/shared/api';
import type { StartOptimisationPassCommand } from '@/features/start-optimisation-pass';
import { useStartOptimisationPass } from '@/features/start-optimisation-pass';

type Captured = { mutationFn: (input: StartOptimisationPassCommand) => Promise<OptimisationPass> };

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const SET: StartOptimisationPassCommand = { projectUid: `prj_${ULID}`, documentUid: `doc_${ULID}` };
const OTHER_SET: StartOptimisationPassCommand = {
  projectUid: `prj_${ULID}`,
  documentUid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
};

const post = vi.mocked(startOptimisationPass);

/** A request that stays open until the test settles it. */
function holdOpen(): { settle: (value: unknown) => void; fail: (error: unknown) => void } {
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

describe('a double press of «Запустить проход»', () => {
  it('sends ONE request, and both presses get its answer', async () => {
    const open = holdOpen();
    const hook = useStartOptimisationPass() as unknown as Captured;
    const first = hook.mutationFn(SET);
    const second = hook.mutationFn(SET);
    expect(post).toHaveBeenCalledTimes(1);
    const stored = { optimisation_pass_id: 'optp_1' };
    open.settle({ data: stored });
    await expect(first).resolves.toBe(stored);
    await expect(second).resolves.toBe(stored);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('gives both presses the same refusal when the one request is refused', async () => {
    const open = holdOpen();
    const hook = useStartOptimisationPass() as unknown as Captured;
    const first = hook.mutationFn(SET);
    const second = hook.mutationFn(SET);
    expect(post).toHaveBeenCalledTimes(1);
    const refusal = new Error('conflict');
    open.fail(refusal);
    await expect(first).rejects.toBe(refusal);
    await expect(second).rejects.toBe(refusal);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('sends a new request for a press after the first settled', async () => {
    post.mockResolvedValue({ data: { optimisation_pass_id: 'optp_1' } } as never);
    const hook = useStartOptimisationPass() as unknown as Captured;
    await hook.mutationFn(SET);
    await hook.mutationFn(SET);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('reopens after a failure, and the retry carries the same key as the attempt that failed', async () => {
    post.mockRejectedValueOnce(new Error('connection closed'));
    post.mockResolvedValue({ data: { optimisation_pass_id: 'optp_1' } } as never);
    const hook = useStartOptimisationPass() as unknown as Captured;
    await expect(hook.mutationFn(SET)).rejects.toThrow('connection closed');
    await hook.mutationFn(SET);
    const keys = post.mock.calls.map(([call]) => (call as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(2);
    expect(keys[1]).toBe(keys[0]);
  });

  it('does not join a request for another document set', () => {
    holdOpen();
    const hook = useStartOptimisationPass() as unknown as Captured;
    void hook.mutationFn(SET);
    void hook.mutationFn(OTHER_SET);
    expect(post).toHaveBeenCalledTimes(2);
  });
});
