/**
 * The decided severity on an accept (`REVIEW-V2-UI-01`).
 *
 * The decision ledger takes `severity` on an `accept` only, and for the optional v2 path it
 * requires the observation to carry a proposed severity (`W56A-INT-DECIDED-SEVERITY-01`).
 * Four rules keep the browser on the right side of that, and each is pinned below by a case
 * that goes red under a named mutation (the mutations are quoted in
 * `docs/program/REVIEW-V2-UI-01.md`):
 *
 *   1. a finding WITHOUT a proposed severity sends the request it always sent, with no
 *      `severity` key at all, whatever the caller offers;
 *   2. a finding WITH one sends the severity the EXPERT chose, never the model's proposal;
 *   3. an accept of such a finding with no choice is REFUSED and nothing is sent;
 *   4. a reject never carries a severity.
 *
 * Plus the idempotency rule that follows from them: a retry of the same accept reuses its
 * key, and an accept with another severity is another command with another key.
 *
 * The hook is exercised through its configuration, as `carry-over-command.test.ts` does:
 * `useMutation` hands back the configuration it was given plus a recording `mutate`, and
 * `useRef`/`useState` are plain holders, so the test holds the very `mutationFn` the browser
 * runs and the very `mutate` call a press makes.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const hold = vi.hoisted(() => ({
  config: null as null | { mutationFn: (request: unknown) => Promise<unknown> },
  mutate: null as null | ((request: unknown) => void),
  state: { value: undefined as unknown, set: false },
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: { mutationFn: (request: unknown) => Promise<unknown> }) => {
    hold.config = configuration;
    return {
      mutate: (request: unknown) => hold.mutate?.(request),
      isPending: false,
      error: null,
      data: undefined,
      reset: () => {},
    };
  },
  useQueryClient: () => ({ invalidateQueries: () => Promise.resolve() }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useRef: (value: unknown) => ({ current: value }),
    // One cell, read back on the next call of the hook: enough to see the refusal a press
    // filed, which is all this suite asks of state.
    useState: (initial: unknown) => [
      hold.state.set ? hold.state.value : initial,
      (next: unknown) => {
        hold.state.value = next;
        hold.state.set = true;
      },
    ],
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, appendDecision: vi.fn() };
});

import type { AppendDecisionRequest, FindingUid, RunId, Severity } from '@/shared/api';
import { SEVERITY_VALUES, appendDecision } from '@/shared/api';
import { intentSignature, resolveIntentKey } from '@/entities/expert-decision';
import {
  VERDICT_REFUSALS,
  buildVerdictRequest,
  useRecordVerdict,
  verdictRefusalMessage,
} from '@/features/record-verdict';

import { FINDING_UID, OBSERVATION_ID, RUN_ID } from '../review/fixtures';

const OTHER_FINDING = `${FINDING_UID.slice(0, -1)}Z` as FindingUid;

function hook(findingUid: FindingUid = FINDING_UID as FindingUid) {
  return useRecordVerdict({ findingUid, runId: RUN_ID as RunId });
}

const sent: unknown[] = [];

beforeEach(() => {
  sent.length = 0;
  hold.config = null;
  hold.mutate = (request) => {
    sent.push(request);
  };
  hold.state.value = undefined;
  hold.state.set = false;
  vi.clearAllMocks();
});

// ------------------------------------------------------------------ the pure request

describe('a finding without a proposed severity sends the request it always sent', () => {
  it('carries no severity key at all on an accept', () => {
    const checked = buildVerdictRequest({ intent: 'accept', observationId: OBSERVATION_ID });
    expect(checked).toEqual({
      kind: 'ok',
      request: { event_type: 'accept', finding_observation_id: OBSERVATION_ID },
    });
    // `toEqual` treats an undefined property as absent; the wire does not.
    expect(Object.keys((checked as { request: object }).request).sort()).toEqual([
      'event_type',
      'finding_observation_id',
    ]);
  });

  it('does not send a stray choice either: no proposal, no severity', () => {
    const checked = buildVerdictRequest({
      intent: 'accept',
      observationId: OBSERVATION_ID,
      decidedSeverity: 'critical',
    });
    expect(checked.kind).toBe('ok');
    expect('severity' in (checked as { request: object }).request).toBe(false);
  });
});

describe('a finding with a proposed severity is accepted with the severity the expert chose', () => {
  for (const decided of SEVERITY_VALUES) {
    it(`sends «${decided}» when that is what was chosen`, () => {
      const checked = buildVerdictRequest({
        intent: 'accept',
        observationId: OBSERVATION_ID,
        proposedSeverity: 'critical',
        decidedSeverity: decided,
      });
      expect(checked).toEqual({
        kind: 'ok',
        request: { event_type: 'accept', finding_observation_id: OBSERVATION_ID, severity: decided },
      });
    });
  }

  it('sends the choice and not the proposal when they differ', () => {
    const checked = buildVerdictRequest({
      intent: 'accept',
      observationId: OBSERVATION_ID,
      proposedSeverity: 'critical',
      decidedSeverity: 'recommendation',
    });
    expect((checked as { request: AppendDecisionRequest }).request.severity).toBe('recommendation');
  });

  it('refuses an accept with no choice, and does not fall back to the proposal', () => {
    for (const proposed of SEVERITY_VALUES) {
      expect(
        buildVerdictRequest({
          intent: 'accept',
          observationId: OBSERVATION_ID,
          proposedSeverity: proposed,
        }),
      ).toEqual({ kind: 'refused', refusal: 'severity_required' });
    }
  });

  it('refuses a choice outside the contract’s closed set', () => {
    expect(
      buildVerdictRequest({
        intent: 'accept',
        observationId: OBSERVATION_ID,
        proposedSeverity: 'critical',
        decidedSeverity: 'urgent' as Severity,
      }),
    ).toEqual({ kind: 'refused', refusal: 'severity_required' });
  });
});

describe('a reject never carries a severity', () => {
  it('drops one the caller offers, with a proposal and without', () => {
    for (const proposedSeverity of [undefined, 'critical' as const]) {
      const checked = buildVerdictRequest({
        intent: 'reject',
        observationId: OBSERVATION_ID,
        proposedSeverity,
        decidedSeverity: 'economic',
      });
      expect(checked).toEqual({
        kind: 'ok',
        request: { event_type: 'reject', finding_observation_id: OBSERVATION_ID },
      });
      expect('severity' in (checked as { request: object }).request).toBe(false);
    }
  });
});

describe('the refusal has words, in Russian, for every member', () => {
  it('names each reason in Cyrillic with no Latin word', () => {
    expect(VERDICT_REFUSALS.length).toBeGreaterThan(0);
    for (const refusal of VERDICT_REFUSALS) {
      const message = verdictRefusalMessage(refusal);
      expect(message).toMatch(/[А-Яа-яЁё]{4,}/);
      expect(message).not.toMatch(/[A-Za-z]/);
      expect(message).not.toContain(refusal);
    }
  });
});

// ------------------------------------------------------------------ the idempotency rule

describe('the intent signature follows the severity', () => {
  const ACCEPT: AppendDecisionRequest = {
    event_type: 'accept',
    finding_observation_id: OBSERVATION_ID,
  };

  it('keeps the signature of a request without a severity exactly what it was', () => {
    const legacy = ['accept', OBSERVATION_ID, '0:'].map((part) => `${part.length}|${part}`).join('');
    expect(intentSignature(ACCEPT)).toBe(legacy);
  });

  it('tells an accept with a severity from one without, and one severity from another', () => {
    const signatures = [
      intentSignature(ACCEPT),
      ...SEVERITY_VALUES.map((severity) => intentSignature({ ...ACCEPT, severity })),
    ];
    expect(new Set(signatures).size).toBe(signatures.length);
  });

  it('reuses the key for the same accept and mints another for another severity', () => {
    let n = 0;
    const mint = () => `idem-${(n += 1)}`;
    const first = resolveIntentKey(null, { ...ACCEPT, severity: 'critical' }, mint);
    const retry = resolveIntentKey(first, { ...ACCEPT, severity: 'critical' }, mint);
    const changed = resolveIntentKey(retry, { ...ACCEPT, severity: 'economic' }, mint);
    expect(retry.idempotencyKey).toBe(first.idempotencyKey);
    expect(changed.idempotencyKey).not.toBe(first.idempotencyKey);
    expect(n).toBe(2);
  });
});

// ------------------------------------------------------------------ the hook

describe('pressing Accept and Reject through the hook', () => {
  it('sends the chosen severity once, on an accept of a finding with a proposal', () => {
    hook().record('accept', OBSERVATION_ID as never, { proposed: 'critical', decided: 'economic' });
    expect(sent).toEqual([
      { event_type: 'accept', finding_observation_id: OBSERVATION_ID, severity: 'economic' },
    ]);
    expect(hook().refusal).toBeNull();
  });

  it('sends nothing and says so when the expert has not chosen', () => {
    hook().record('accept', OBSERVATION_ID as never, { proposed: 'critical' });
    expect(sent).toEqual([]);
    expect(hook().refusal).toBe('severity_required');
  });

  it('keeps that refusal on the finding it was raised for', () => {
    hook().record('accept', OBSERVATION_ID as never, { proposed: 'critical' });
    expect(hook().refusal).toBe('severity_required');
    expect(hook(OTHER_FINDING).refusal).toBeNull();
  });

  it('clears the refusal when the next press goes out', () => {
    hook().record('accept', OBSERVATION_ID as never, { proposed: 'critical' });
    expect(hook().refusal).toBe('severity_required');
    hook().record('accept', OBSERVATION_ID as never, { proposed: 'critical', decided: 'critical' });
    expect(sent).toHaveLength(1);
    expect(hook().refusal).toBeNull();
  });

  it('sends the legacy request on an accept of a finding with no proposal', () => {
    hook().record('accept', OBSERVATION_ID as never);
    expect(sent).toEqual([{ event_type: 'accept', finding_observation_id: OBSERVATION_ID }]);
    expect(Object.keys(sent[0] as object)).toHaveLength(2);
  });

  it('never sends a severity on a reject, whatever the finding carries', () => {
    hook().record('reject', OBSERVATION_ID as never, { proposed: 'critical', decided: 'critical' });
    expect(sent).toEqual([{ event_type: 'reject', finding_observation_id: OBSERVATION_ID }]);
    expect(hook().refusal).toBeNull();
  });
});

describe('the request the hook’s mutation puts on the wire', () => {
  it('reuses one idempotency key across a retry of the same accept, and mints another for a new severity', async () => {
    vi.mocked(appendDecision).mockRejectedValueOnce(new Error('connection closed'));
    vi.mocked(appendDecision).mockResolvedValue({ data: { current_verdict: 'accepted' } } as never);
    hook();
    const mutationFn = (hold.config as { mutationFn: (request: unknown) => Promise<unknown> })
      .mutationFn;
    const accept = {
      event_type: 'accept',
      finding_observation_id: OBSERVATION_ID,
      severity: 'critical',
    };

    await expect(mutationFn(accept)).rejects.toThrow('connection closed');
    await mutationFn(accept);
    await mutationFn({ ...accept, severity: 'economic' });

    const calls = vi.mocked(appendDecision).mock.calls as unknown as [
      { body: AppendDecisionRequest; idempotencyKey: string },
    ][];
    expect(calls.map(([call]) => call.body.severity)).toEqual(['critical', 'critical', 'economic']);
    expect(calls[0]?.[0].idempotencyKey).toBe(calls[1]?.[0].idempotencyKey);
    expect(calls[2]?.[0].idempotencyKey).not.toBe(calls[1]?.[0].idempotencyKey);
  });
});
