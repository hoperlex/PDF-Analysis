/**
 * `carryOverDecision` as the feature sends it (`W59-DECISION-CARRYOVER-01`): one `POST` at the
 * older version's address with the pair, the mode and the decision the expert was shown, under
 * one idempotency key per intent; and the reads it tells afterwards — every comparison answer,
 * the newer finding's ledger and detail, its run's finding list, the knowledge base and the
 * dashboard on success; every comparison answer on a refusal.
 *
 * The mutation hook is exercised through its configuration, the way the classification
 * command's suite does: `useMutation` is replaced by the identity and `useRef` by a plain
 * holder, so the test holds the very `mutationFn`, `onSuccess` and `onError` the browser runs.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    invalidateQueries: (...args: unknown[]) => {
      calls.invalidations.push(args);
      return Promise.resolve();
    },
  }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, useRef: (value: unknown) => ({ current: value }) };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, carryOverDecision: vi.fn() };
});

import type { CarryOverDecisionResponse } from '@/shared/api';
import { carryOverDecision, queryKeys } from '@/shared/api';
import { decisionCacheKeys } from '@/entities/expert-decision';
import type { CarryOverDecisionCommand } from '@/features/carry-over-decision';
import { carryoverSignature, useCarryOverDecision } from '@/features/carry-over-decision';

type Captured = {
  mutationFn: (input: CarryOverDecisionCommand) => Promise<CarryOverDecisionResponse>;
  onSuccess: (result: CarryOverDecisionResponse, input: CarryOverDecisionCommand) => void;
  onError: (error: unknown, input: CarryOverDecisionCommand) => void;
  retry: boolean;
};

const ULID = '01M2545JSD15ETSNNV904X991J';
const TARGET = 'fnd_01M2545JSD15ETSNNV904X9912';
const RUN = 'run_01M2545JSD15ETSNNV904X991K';

const COMMAND: CarryOverDecisionCommand = {
  projectUid: `prj_${ULID}`,
  documentUid: `doc_${ULID}`,
  sourceVersionUid: `ver_${ULID}`,
  targetVersionUid: 'ver_01M2545JSD15ETSNNV904X991K',
  mode: 'version',
  targetRunId: RUN,
  candidate: {
    proposal_sha256: 'a'.repeat(64),
    source_finding_uid: 'fnd_01M2545JSD15ETSNNV904X9911',
    target_finding_uid: TARGET,
    source_decision: {
      decision_id: `dec_${ULID}`, verdict: 'rejected', severity: null, comment: null,
      author_label: 'Иванова Е. В.', recorded_at: '2026-10-20T08:00:00Z',
    },
  },
};

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('the carryover command', () => {
  it('sends one POST at the older version with the pair, the mode and the decision shown, never retried', async () => {
    vi.mocked(carryOverDecision).mockResolvedValue({ data: { replayed: false } } as never);
    const command = useCarryOverDecision() as unknown as Captured;
    expect(command.retry).toBe(false);
    await command.mutationFn(COMMAND);
    const [[sent]] = vi.mocked(carryOverDecision).mock.calls as unknown as [[Record<string, unknown>]];
    expect(sent.path).toEqual({
      project_uid: COMMAND.projectUid, document_uid: COMMAND.documentUid, version_uid: COMMAND.sourceVersionUid,
    });
    expect(sent.body).toEqual({
      target_version_uid: COMMAND.targetVersionUid,
      mode: 'version',
      source_finding_uid: COMMAND.candidate.source_finding_uid,
      target_finding_uid: TARGET,
      source_decision_id: COMMAND.candidate.source_decision.decision_id,
    });
    expect(typeof sent.idempotencyKey).toBe('string');
  });

  it('reuses one key for a retry of the same intent and mints a new one for another', async () => {
    vi.mocked(carryOverDecision).mockRejectedValueOnce(new Error('connection closed'));
    vi.mocked(carryOverDecision).mockResolvedValue({ data: { replayed: false } } as never);
    const command = useCarryOverDecision() as unknown as Captured;
    await expect(command.mutationFn(COMMAND)).rejects.toThrow('connection closed');
    await command.mutationFn(COMMAND);
    const other = { ...COMMAND, mode: 'stage' as const };
    await command.mutationFn(other);
    const keys = vi.mocked(carryOverDecision).mock.calls.map(([input]) => input.idempotencyKey);
    expect(keys[0]).toBe(keys[1]);
    expect(keys[2]).not.toBe(keys[1]);
    expect(carryoverSignature(other)).not.toBe(carryoverSignature(COMMAND));
  });

  it('sends ONE request when the same intent is pressed twice before the first answer (BETA-LIVE-JOURNEY-01)', async () => {
    // The live journey measured two POSTs for a double press, the second answered
    // `replayed: true`; the screen shows the latest answer, so it said "already carried
    // earlier" over a carry the expert had just made. Both presses must get the SAME answer.
    let settle: (value: unknown) => void = () => undefined;
    vi.mocked(carryOverDecision).mockImplementation(
      () => new Promise((resolve) => { settle = resolve; }) as never,
    );
    const command = useCarryOverDecision() as unknown as Captured;
    const first = command.mutationFn(COMMAND);
    const second = command.mutationFn(COMMAND);
    expect(carryOverDecision).toHaveBeenCalledTimes(1);
    settle({ data: { replayed: false, marker: 'first' } });
    await expect(first).resolves.toMatchObject({ replayed: false, marker: 'first' });
    await expect(second).resolves.toMatchObject({ replayed: false, marker: 'first' });
    // The gate reopens when the request settles: a later press is a new request.
    vi.mocked(carryOverDecision).mockResolvedValue({ data: { replayed: true } } as never);
    await command.mutationFn(COMMAND);
    expect(carryOverDecision).toHaveBeenCalledTimes(2);
  });

  it('does not join a request for another intent', async () => {
    vi.mocked(carryOverDecision).mockImplementation(
      () => new Promise(() => undefined) as never,
    );
    const command = useCarryOverDecision() as unknown as Captured;
    void command.mutationFn(COMMAND);
    void command.mutationFn({ ...COMMAND, mode: 'stage' as const });
    expect(carryOverDecision).toHaveBeenCalledTimes(2);
  });

  it('tells every comparison and the newer finding’s reads after a carryover', () => {
    const command = useCarryOverDecision() as unknown as Captured;
    command.onSuccess({ replayed: false } as CarryOverDecisionResponse, COMMAND);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.versions.comparisons() }],
      ...decisionCacheKeys(TARGET, RUN).map((queryKey) => [{ queryKey }]),
    ]);
  });

  it('reads the comparison again after a refusal, and nothing else', () => {
    const command = useCarryOverDecision() as unknown as Captured;
    command.onError(new Error('refused'), COMMAND);
    expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.versions.comparisons() }]]);
  });

  it('reaches every page and mode of the comparison with its prefix', () => {
    const key = queryKeys.versions.comparison(COMMAND.sourceVersionUid, COMMAND.targetVersionUid, 'stage', 10, 10);
    expect(key.slice(0, 2)).toEqual([...queryKeys.versions.comparisons()]);
  });
});
