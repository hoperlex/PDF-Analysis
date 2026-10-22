/**
 * What the verdict feature tells the screen about the press in flight and the answer to it
 * (`WEB-REVIEW-FOLLOWUPS-01`, items 2, 3 and 4).
 *
 *   2. `pendingIntent` — which verdict is in flight, read from the pending REQUEST. The
 *      review page used to say `'accept'` for any pending verdict, so a pending reject read
 *      «Принимаю…». TanStack keeps `variables` after a mutation settles, so the intent is
 *      reported only while the mutation is pending.
 *   3. `result` — the answer to the press, kept for the finding it answers. The hook lives at
 *      page level and survives a change of selected finding, and `mutation.data` is the last
 *      answer whatever finding is on screen; the page prefers it over the finding's own
 *      verdict, so finding A's answer was shown on finding B.
 *   4. `clearRefusal` — the refusal sentence («Перед принятием выберите важность…») is the
 *      answer to the PREVIOUS press; once the expert picks a severity it is no longer true,
 *      and it must go without sending anything and without touching the mutation.
 *
 * Each case goes red under a quoted mutation (`docs/program/WEB-REVIEW-FOLLOWUPS-01.md`).
 *
 * The hook is exercised through its configuration, as `verdict-severity.test.ts` does:
 * `useMutation` hands back whatever mutation state the test sets, `useRef` is a plain holder,
 * and `useState` is one cell read back on the next call of the hook.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const hold = vi.hoisted(() => ({
  mutation: {
    isPending: false,
    variables: undefined as unknown,
    data: undefined as unknown,
    error: null as unknown,
  },
  mutate: vi.fn(),
  reset: vi.fn(),
  state: { value: undefined as unknown, set: false },
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: () => ({
    mutate: hold.mutate,
    isPending: hold.mutation.isPending,
    variables: hold.mutation.variables,
    error: hold.mutation.error,
    data: hold.mutation.data,
    reset: hold.reset,
  }),
  useQueryClient: () => ({ invalidateQueries: () => Promise.resolve() }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useRef: (value: unknown) => ({ current: value }),
    useState: (initial: unknown) => [
      hold.state.set ? hold.state.value : initial,
      (next: unknown) => {
        hold.state.value = next;
        hold.state.set = true;
      },
    ],
  };
});

import type {
  AppendDecisionRequest,
  AppendDecisionResponse,
  FindingUid,
  RunId,
} from '@/shared/api';
import { verdictIntentOf } from '@/features/record-verdict/model/verdict-request';
import { useRecordVerdict } from '@/features/record-verdict';

import { FINDING_UID, OBSERVATION_ID, RUN_ID, decisionEvent } from '../review/fixtures';

const OTHER_FINDING = `${FINDING_UID.slice(0, -1)}Z` as FindingUid;

function hook(findingUid: FindingUid = FINDING_UID as FindingUid) {
  return useRecordVerdict({ findingUid, runId: RUN_ID as RunId });
}

function request(eventType: AppendDecisionRequest['event_type']): AppendDecisionRequest {
  return { event_type: eventType, finding_observation_id: OBSERVATION_ID };
}

/**
 * What the mutation holds as its variables: the press, the finding it was raised for and the
 * request together (`WEB-HOOKS-PER-FINDING-01`; `per-finding-feedback.test.ts` runs the real
 * observer, this file sets the state the hook reads).
 */
function press(
  eventType: AppendDecisionRequest['event_type'],
  findingUid: string = FINDING_UID,
): unknown {
  return { findingUid, request: request(eventType) };
}

function answer(findingUid: string, current: AppendDecisionResponse['current_verdict']): AppendDecisionResponse {
  return {
    current_verdict: current,
    event: decisionEvent({ finding_uid: findingUid, verdict: current === 'pending' ? null : current }),
  };
}

beforeEach(() => {
  hold.mutation.isPending = false;
  hold.mutation.variables = undefined;
  hold.mutation.data = undefined;
  hold.mutation.error = null;
  hold.state.value = undefined;
  hold.state.set = false;
  vi.clearAllMocks();
});

// ------------------------------------------------------------------ item 2

describe('the intent in flight is read from the pending request', () => {
  it('is «reject» while a reject is pending', () => {
    hold.mutation.isPending = true;
    hold.mutation.variables = press('reject');
    expect(hook().pendingIntent).toBe('reject');
  });

  it('is «accept» while an accept is pending', () => {
    hold.mutation.isPending = true;
    hold.mutation.variables = press('accept');
    expect(hook().pendingIntent).toBe('accept');
  });

  it('is nothing once the mutation has settled, though its variables are still held', () => {
    hold.mutation.isPending = false;
    hold.mutation.variables = press('reject');
    expect(hook().pendingIntent).toBeNull();
    expect(hook().isPending).toBe(false);
  });

  it('is nothing when nothing was ever pressed', () => {
    expect(hook().pendingIntent).toBeNull();
  });

  it('still says a verdict is pending through isPending, whatever the intent', () => {
    hold.mutation.isPending = true;
    hold.mutation.variables = press('reject');
    expect(hook().isPending).toBe(true);
  });
});

describe('verdictIntentOf names only a verdict', () => {
  it('maps an accept and a reject to themselves', () => {
    expect(verdictIntentOf(request('accept'))).toBe('accept');
    expect(verdictIntentOf(request('reject'))).toBe('reject');
  });

  it('has no verdict intent for a comment, a revoke or no request', () => {
    expect(verdictIntentOf(request('comment'))).toBeNull();
    expect(verdictIntentOf(request('revoke'))).toBeNull();
    expect(verdictIntentOf(undefined)).toBeNull();
  });
});

// ------------------------------------------------------------------ item 3

describe('the answer belongs to the finding it answers', () => {
  it('is the result of the hook bound to that finding', () => {
    const data = answer(FINDING_UID, 'accepted');
    hold.mutation.data = data;
    expect(hook(FINDING_UID as FindingUid).result).toBe(data);
  });

  it('is not the result of the same hook once another finding is selected', () => {
    hold.mutation.data = answer(FINDING_UID, 'accepted');
    expect(hook(OTHER_FINDING).result).toBeNull();
  });

  it('comes back when the reviewer returns to the finding it answers', () => {
    const data = answer(FINDING_UID, 'rejected');
    hold.mutation.data = data;
    expect(hook(OTHER_FINDING).result).toBeNull();
    expect(hook(FINDING_UID as FindingUid).result).toBe(data);
  });

  it('is nothing before any press', () => {
    expect(hook().result).toBeNull();
  });

  it('is told by the finding the SERVER recorded the event against, not by the verdict', () => {
    // Same verdict, another finding: the verdict alone cannot say whose answer this is.
    hold.mutation.data = answer(OTHER_FINDING, 'accepted');
    expect(hook(FINDING_UID as FindingUid).result).toBeNull();
    expect(hook(OTHER_FINDING).result).not.toBeNull();
  });
});

// ------------------------------------------------------------------ item 4

describe('the refusal goes when the expert picks a severity', () => {
  function refuse(): void {
    hook().record('accept', OBSERVATION_ID, { proposed: 'critical' });
  }

  it('is on the hook after a refused accept, and gone after clearRefusal', () => {
    refuse();
    expect(hook().refusal).toBe('severity_required');
    hook().clearRefusal();
    expect(hook().refusal).toBeNull();
  });

  it('sends nothing, and does not touch the mutation or its error', () => {
    refuse();
    hold.mutate.mockClear();
    hold.mutation.variables = press('accept');
    hold.mutation.error = new Error('сервер отказал');
    hook().clearRefusal();
    expect(hold.mutate).not.toHaveBeenCalled();
    expect(hold.reset).not.toHaveBeenCalled();
    expect(hook().error).toBe(hold.mutation.error);
  });

  it('is filed again by the next refused press', () => {
    refuse();
    hook().clearRefusal();
    refuse();
    expect(hook().refusal).toBe('severity_required');
  });

  it('is harmless when there is no refusal to clear', () => {
    hook().clearRefusal();
    expect(hook().refusal).toBeNull();
    expect(hold.mutate).not.toHaveBeenCalled();
  });
});
