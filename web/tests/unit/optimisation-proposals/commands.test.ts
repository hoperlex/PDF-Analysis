/**
 * The two commands and the three reads as the features send them (`W60-OPT-PROPOSALS-01`):
 * one `Idempotency-Key` per intent, reused on a retry and dropped once the intent completes,
 * the comment sent only when there is one, and the reads each success tells — never the
 * dashboard or a finding, which neither command changes.
 *
 * The hooks are exercised through their configuration, as `commands.test.ts` of the price
 * lists does: `useMutation` is replaced by the identity, so the test holds the very
 * `mutationFn` and `onSuccess` the browser would run.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) => configuration,
    useQueryClient: () => ({
      invalidateQueries: (...args: unknown[]) => {
        calls.invalidations.push(args);
        return Promise.resolve();
      },
    }),
  };
});

// `useRef` keeps its value between calls of one hook instance; outside a render there is no
// instance, so each test below holds one ref per hook and hands it back on every call.
vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  const refs: { current: unknown }[] = [];
  let cursor = 0;
  return {
    ...actual,
    useRef: (initial: unknown) => {
      const slot = (refs[cursor] ??= { current: initial });
      cursor += 1;
      return slot;
    },
    __rewind: () => {
      cursor = 0;
    },
    __forget: () => {
      refs.length = 0;
      cursor = 0;
    },
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    startOptimisationPass: vi.fn(),
    decideOptimisationProposal: vi.fn(),
  };
});

import * as react from 'react';

import type { OptimisationPass, ProposalDecisionResult } from '@/shared/api';
import { decideOptimisationProposal, queryKeys, startOptimisationPass } from '@/shared/api';
import type { DecideOptimisationProposalCommand } from '@/features/decide-optimisation-proposal';
import { decisionSignature, useDecideOptimisationProposal } from '@/features/decide-optimisation-proposal';
import type { StartOptimisationPassCommand } from '@/features/start-optimisation-pass';
import { useStartOptimisationPass } from '@/features/start-optimisation-pass';

import {
  AR_DOCUMENT_UID,
  DOOR_PROPOSAL,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  decision,
  pass,
  proposal,
} from './fixtures';

type Captured<I, R> = {
  mutationFn: (input: I) => Promise<R>;
  onSuccess?: (result: R, input: I) => void;
  retry?: boolean;
};

const rewind = (): void => (react as unknown as { __rewind: () => void }).__rewind();
const forget = (): void => (react as unknown as { __forget: () => void }).__forget();

function startHook() {
  rewind();
  return useStartOptimisationPass() as unknown as Captured<StartOptimisationPassCommand, OptimisationPass>;
}

function decideHook() {
  rewind();
  return useDecideOptimisationProposal() as unknown as Captured<
    DecideOptimisationProposalCommand,
    ProposalDecisionResult
  >;
}

const START: StartOptimisationPassCommand = { projectUid: PROPOSALS_PROJECT_UID, documentUid: AR_DOCUMENT_UID };
const DECIDE: DecideOptimisationProposalCommand = {
  passId: PASS_ID,
  proposalId: DOOR_PROPOSAL,
  verdict: 'accept',
  comment: null,
};

function keyOf(mock: ReturnType<typeof vi.fn>, call: number): string {
  return (mock.mock.calls[call]?.[0] as { idempotencyKey: string }).idempotencyKey;
}

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
  forget();
});

describe('starting a pass', () => {
  it('sends the set under a key, and never retries by itself', async () => {
    vi.mocked(startOptimisationPass).mockResolvedValue({ data: pass() } as never);
    const hook = startHook();
    await hook.mutationFn(START);
    expect(vi.mocked(startOptimisationPass)).toHaveBeenCalledWith({
      path: { project_uid: PROPOSALS_PROJECT_UID, document_uid: AR_DOCUMENT_UID },
      idempotencyKey: expect.stringMatching(/\S{8,}/),
    });
    expect(hook.retry).toBe(false);
  });

  it('reuses the key on a retry of the same set and mints another once the pass is stored', async () => {
    vi.mocked(startOptimisationPass)
      .mockRejectedValueOnce(new Error('lost answer'))
      .mockResolvedValue({ data: pass() } as never);
    await expect(startHook().mutationFn(START)).rejects.toThrow('lost answer');
    await startHook().mutationFn(START);
    const mock = vi.mocked(startOptimisationPass);
    expect(keyOf(mock, 1)).toBe(keyOf(mock, 0));

    startHook().onSuccess?.(pass(), START);
    await startHook().mutationFn(START);
    expect(keyOf(mock, 2)).not.toBe(keyOf(mock, 0));
  });

  it('is another intent for another set', async () => {
    vi.mocked(startOptimisationPass).mockResolvedValue({ data: pass() } as never);
    await startHook().mutationFn(START);
    await startHook().mutationFn({ ...START, documentUid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8J' });
    const mock = vi.mocked(startOptimisationPass);
    expect(keyOf(mock, 1)).not.toBe(keyOf(mock, 0));
  });

  it('tells the passes and the new pass’s proposals, and not the dashboard or a finding', () => {
    startHook().onSuccess?.(pass(), START);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.optimisation.allPasses() }],
      [{ queryKey: queryKeys.optimisation.proposalsOf(PASS_ID) }],
    ]);
  });
});

describe('deciding a proposal', () => {
  it('sends the verdict alone when there is no comment, and the comment when there is one', async () => {
    vi.mocked(decideOptimisationProposal).mockResolvedValue({ data: {} } as never);
    await decideHook().mutationFn(DECIDE);
    await decideHook().mutationFn({ ...DECIDE, verdict: 'revise', comment: 'Заменить марку.' });
    const sent = vi.mocked(decideOptimisationProposal).mock.calls.map((call) => call[0]);
    expect(sent[0]).toMatchObject({
      path: { optimisation_proposal_id: DOOR_PROPOSAL },
      body: { verdict: 'accept' },
    });
    expect(Object.keys(sent[0]?.body ?? {})).toEqual(['verdict']);
    expect(sent[1]?.body).toEqual({ verdict: 'revise', comment: 'Заменить марку.' });
  });

  it('reuses the key for the same verdict and comment, and mints another for another intent', async () => {
    vi.mocked(decideOptimisationProposal).mockRejectedValueOnce(new Error('lost answer'));
    vi.mocked(decideOptimisationProposal).mockResolvedValue({ data: {} } as never);
    await expect(decideHook().mutationFn(DECIDE)).rejects.toThrow('lost answer');
    await decideHook().mutationFn(DECIDE);
    await decideHook().mutationFn({ ...DECIDE, verdict: 'reject' });
    const mock = vi.mocked(decideOptimisationProposal);
    expect(keyOf(mock, 1)).toBe(keyOf(mock, 0));
    expect(keyOf(mock, 2)).not.toBe(keyOf(mock, 0));
  });

  it('mints a new key for the same decision once the earlier one is stored: decisions are appended', async () => {
    vi.mocked(decideOptimisationProposal).mockResolvedValue({ data: {} } as never);
    await decideHook().mutationFn(DECIDE);
    decideHook().onSuccess?.({ decision: decision(), proposal: proposal() }, DECIDE);
    await decideHook().mutationFn(DECIDE);
    const mock = vi.mocked(decideOptimisationProposal);
    expect(keyOf(mock, 1)).not.toBe(keyOf(mock, 0));
  });

  it('has a signature that a comment containing the separator cannot collide', () => {
    const a = decisionSignature({ ...DECIDE, comment: 'x|accept' });
    const b = decisionSignature({ ...DECIDE, verdict: 'reject', comment: 'x|accept' });
    expect(a).not.toBe(b);
    expect(decisionSignature({ ...DECIDE, comment: 'a","b' })).not.toBe(
      decisionSignature({ ...DECIDE, comment: 'a' }),
    );
  });

  it('tells the pass’s proposals, every pass’s counts and the proposal’s history only', () => {
    decideHook().onSuccess?.({ decision: decision(), proposal: proposal() }, DECIDE);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.optimisation.proposalsOf(PASS_ID) }],
      [{ queryKey: queryKeys.optimisation.allPasses() }],
      [{ queryKey: queryKeys.optimisation.proposalDecisions(DOOR_PROPOSAL) }],
    ]);
    for (const entry of calls.invalidations) {
      const [options] = entry as [{ queryKey: readonly unknown[] }];
      expect(options.queryKey[0]).toBe('optimisation');
    }
  });
});
