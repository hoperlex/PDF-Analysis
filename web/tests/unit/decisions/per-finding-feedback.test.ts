/**
 * A verdict or a comment that failed, or is still going out, belongs to the finding it was
 * pressed on (`WEB-HOOKS-PER-FINDING-01`, `D-201`).
 *
 * `useRecordVerdict` and `useAppendComment` are bound to one finding but live at page level, so
 * they outlive a change of selection. `WEB-REVIEW-FOLLOWUPS-01` filed `result` and the refusal
 * under the finding; `error`, `isPending` and `pendingIntent` still came straight from the one
 * mutation, so after a press on finding A and a change to finding B, B's panel showed A's
 * «Вердикт не записан» and had its three buttons disabled until A's request settled.
 *
 * The reproduction presses on A, lets the request fail (or hang), re-renders the hook bound to
 * B and reads what B is told. Nothing here is a recording of what the test sets: the mutation is
 * React Query's own observer (`mutation-model.ts`), and the server is `appendDecision` with a
 * gate the test opens, so the cases fail for the reason a reviewer would see them fail.
 *
 * The second half is what widening the buttons' availability costs. Once B can be pressed while
 * A is in flight, two requests share the hook, and the idempotency key's holder must not be
 * clobbered by the other finding's press or wiped by the other finding's success; the cache
 * entries a success refreshes must be the ones of the finding it was sent for, not of the finding
 * the hook happens to be bound to when the answer arrives.
 *
 * Each case goes red under a quoted mutation (`docs/program/WEB-HOOKS-PER-FINDING-01.md`).
 */

import type * as Query from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MutationModel } from './mutation-model';

const world = vi.hoisted(() => ({
  actual: null as null | Pick<typeof Query, 'MutationObserver' | 'QueryClient'>,
  model: null as null | MutationModel,
  refs: [] as { current: unknown }[],
  refIndex: 0,
  cells: [] as unknown[],
  cellIndex: 0,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof Query>();
  world.actual = actual;
  return {
    ...actual,
    useMutation: (options: never) => (world.model as MutationModel).useMutation(options),
    useQueryClient: () => (world.model as MutationModel).client,
  };
});

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useRef: (initial: unknown) => {
      const at = world.refIndex;
      world.refIndex += 1;
      if (!(at in world.refs)) world.refs[at] = { current: initial };
      return world.refs[at];
    },
    useState: (initial: unknown) => {
      const at = world.cellIndex;
      world.cellIndex += 1;
      if (!(at in world.cells)) world.cells[at] = typeof initial === 'function' ? (initial as () => unknown)() : initial;
      return [
        world.cells[at],
        (next: unknown) => {
          world.cells[at] = typeof next === 'function' ? (next as (v: unknown) => unknown)(world.cells[at]) : next;
        },
      ];
    },
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, appendDecision: vi.fn() };
});

import { decisionCacheKeys } from '@/entities/expert-decision';
import { useAppendComment } from '@/features/append-comment';
import { useRecordVerdict } from '@/features/record-verdict';
import type {
  AppendDecisionRequest,
  AppendDecisionResponse,
  FindingObservationId,
  FindingUid,
  RunId,
} from '@/shared/api';
import { appendDecision } from '@/shared/api';

import { FINDING_UID, OBSERVATION_ID, RUN_ID, decisionEvent } from '../review/fixtures';

const A = FINDING_UID as FindingUid;
const B = `${FINDING_UID.slice(0, -1)}Z` as FindingUid;
const OBS_A = OBSERVATION_ID as FindingObservationId;
const OBS_B = `${OBSERVATION_ID.slice(0, -1)}Z` as FindingObservationId;
const RUN = RUN_ID as RunId;

/** One render of the page's two hooks, both bound to the selected finding. */
function render(findingUid: FindingUid) {
  world.refIndex = 0;
  world.cellIndex = 0;
  (world.model as MutationModel).rewind();
  const verdict = useRecordVerdict({ findingUid, runId: RUN });
  const comment = useAppendComment({ findingUid, runId: RUN });
  return { verdict, comment };
}

interface Call {
  readonly findingUid: string;
  readonly body: AppendDecisionRequest;
  readonly idempotencyKey: string;
  readonly settle: (outcome: 'ok' | Error) => void;
}

const calls: Call[] = [];

function answer(findingUid: string, request: AppendDecisionRequest): AppendDecisionResponse {
  const verdict = request.event_type === 'accept' ? 'accepted' : request.event_type === 'reject' ? 'rejected' : null;
  return {
    current_verdict: verdict ?? 'pending',
    event: decisionEvent({ finding_uid: findingUid, event_type: request.event_type, verdict }),
  };
}

/** Every request waits at the "server" until the test settles it. */
function serverHoldsRequests(): void {
  vi.mocked(appendDecision).mockImplementation((input) => {
    const { path, body, idempotencyKey } = input as unknown as {
      path: { finding_uid: string };
      body: AppendDecisionRequest;
      idempotencyKey: string;
    };
    return new Promise((resolve, reject) => {
      calls.push({
        findingUid: path.finding_uid,
        body,
        idempotencyKey,
        settle: (outcome) => {
          if (outcome === 'ok') resolve({ data: answer(path.finding_uid, body) } as never);
          else reject(outcome);
        },
      });
    });
  });
}

/** Let the observer and the retryer run to the end of what the last settle started. */
async function flush(): Promise<void> {
  await new Promise((done) => setTimeout(done, 0));
}

const REFUSED = new Error('Сервер недоступен');

beforeEach(async () => {
  const { createMutationModel } = await import('./mutation-model');
  world.model = createMutationModel(world.actual as NonNullable<typeof world.actual>);
  world.refs = [];
  world.cells = [];
  world.refIndex = 0;
  world.cellIndex = 0;
  calls.length = 0;
  vi.clearAllMocks();
  serverHoldsRequests();
});

// ------------------------------------------------------------------ the verdict

describe('a verdict that failed belongs to the finding it was pressed on', () => {
  it('is not shown on another finding, and is still shown when the reviewer comes back', async () => {
    render(A).verdict.record('reject', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    expect(render(A).verdict.error).toBe(REFUSED);
    expect(render(B).verdict.error).toBeNull();
    expect(render(A).verdict.error).toBe(REFUSED);
  });

  it('leaves the other finding enabled and not busy while it is in flight', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();

    const onA = render(A).verdict;
    expect(onA.isPending).toBe(true);
    expect(onA.pendingIntent).toBe('accept');

    const onB = render(B).verdict;
    expect(onB.isPending).toBe(false);
    expect(onB.pendingIntent).toBeNull();
  });

  it('hands the answer to the finding it answers, and only to it', async () => {
    render(A).verdict.record('reject', OBS_A);
    await flush();
    calls[0]?.settle('ok');
    await flush();

    expect(render(A).verdict.result?.event.finding_uid).toBe(A);
    expect(render(B).verdict.result).toBeNull();
    expect(render(A).verdict.error).toBeNull();
    expect(render(A).verdict.isPending).toBe(false);
  });

  it('shows nothing of a press that was never made', () => {
    const api = render(A).verdict;
    expect(api.error).toBeNull();
    expect(api.isPending).toBe(false);
    expect(api.pendingIntent).toBeNull();
  });

  it('shows the failure of the finding that was pressed last, not of the one pressed before', async () => {
    render(A).verdict.record('reject', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    const other = new Error('Другой отказ');
    render(B).verdict.record('accept', OBS_B);
    await flush();
    calls[1]?.settle(other);
    await flush();

    expect(render(B).verdict.error).toBe(other);
    expect(render(A).verdict.error).toBeNull();
  });

  it('is forgotten by a reset on the finding it was pressed on, and by no other', async () => {
    render(A).verdict.record('reject', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).verdict.reset();
    expect(render(A).verdict.error).toBe(REFUSED);

    render(A).verdict.reset();
    expect(render(A).verdict.error).toBeNull();
  });
});

// ------------------------------------------------------------------ the comment

describe('a comment that failed belongs to the finding it was written on', () => {
  it('is not shown on another finding, and is still shown when the reviewer comes back', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    expect(render(A).comment.error).toBe(REFUSED);
    expect(render(B).comment.error).toBeNull();
    expect(render(A).comment.error).toBe(REFUSED);
  });

  it('leaves the other finding not busy while it is in flight', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();

    expect(render(A).comment.isPending).toBe(true);
    expect(render(B).comment.isPending).toBe(false);
  });

  it('hands the answer to the finding it answers, and only to it', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    calls[0]?.settle('ok');
    await flush();

    expect(render(A).comment.result?.event.finding_uid).toBe(A);
    expect(render(B).comment.result).toBeNull();
  });

  it('is forgotten by a reset on the finding it was written on, and by no other', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).comment.reset();
    expect(render(A).comment.error).toBe(REFUSED);

    render(A).comment.reset();
    expect(render(A).comment.error).toBeNull();
  });
});

// ------------------------------------------------------------------ the idempotency key

describe('the idempotency key follows the intent, whatever else is pressed meanwhile', () => {
  it('keeps the key of a failed press on retry when nothing else was pressed', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();
    render(A).verdict.record('accept', OBS_A);
    await flush();

    expect(calls).toHaveLength(2);
    expect(calls[1]?.idempotencyKey).toBe(calls[0]?.idempotencyKey);
  });

  it('keeps the key of A’s retry after B was pressed in between', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).verdict.record('reject', OBS_B);

    await flush();
    calls[1]?.settle('ok');
    await flush();

    render(A).verdict.record('accept', OBS_A);

    await flush();
    expect(calls).toHaveLength(3);
    expect(calls[2]?.idempotencyKey).toBe(calls[0]?.idempotencyKey);
  });

  it('keeps the key of A’s retry after B was pressed and failed in between', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).verdict.record('reject', OBS_B);
    await flush();
    calls[1]?.settle(REFUSED);
    await flush();

    render(A).verdict.record('accept', OBS_A);
    await flush();
    expect(calls).toHaveLength(3);
    expect(calls[2]?.idempotencyKey).toBe(calls[0]?.idempotencyKey);
  });

  it('keeps the key of a comment’s retry after another finding’s comment failed in between', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).comment.append('Другой срок.', OBS_B);
    await flush();
    calls[1]?.settle(REFUSED);
    await flush();

    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    expect(calls[2]?.idempotencyKey).toBe(calls[0]?.idempotencyKey);
  });

  it('keeps B’s key when A’s success arrives while B is in flight', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    render(B).verdict.record('reject', OBS_B);
    await flush();
    expect(calls).toHaveLength(2);

    calls[0]?.settle('ok');
    await flush();
    calls[1]?.settle(REFUSED);
    await flush();

    render(B).verdict.record('reject', OBS_B);

    await flush();
    expect(calls).toHaveLength(3);
    expect(calls[2]?.idempotencyKey).toBe(calls[1]?.idempotencyKey);
  });

  it('mints a new key for the next press of an intent that succeeded', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    calls[0]?.settle('ok');
    await flush();
    render(A).verdict.record('accept', OBS_A);
    await flush();

    expect(calls[1]?.idempotencyKey).not.toBe(calls[0]?.idempotencyKey);
  });

  it('keeps a comment’s key for A across a comment on B', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    calls[0]?.settle(REFUSED);
    await flush();

    render(B).comment.append('Другой срок.', OBS_B);

    await flush();
    calls[1]?.settle('ok');
    await flush();

    render(A).comment.append('Срок согласован.', OBS_A);

    await flush();
    expect(calls[2]?.idempotencyKey).toBe(calls[0]?.idempotencyKey);
  });

  it('keeps the key of the intent that is still out when an earlier intent of the same finding completes', async () => {
    render(A).verdict.record('accept', OBS_A);
    await flush();
    render(A).verdict.record('reject', OBS_A);
    await flush();
    expect(calls).toHaveLength(2);

    calls[0]?.settle('ok');
    await flush();
    calls[1]?.settle(REFUSED);
    await flush();

    render(A).verdict.record('reject', OBS_A);
    await flush();
    expect(calls).toHaveLength(3);
    expect(calls[2]?.idempotencyKey).toBe(calls[1]?.idempotencyKey);
  });

  it('keeps a comment’s key when an earlier comment of the same finding completes', async () => {
    render(A).comment.append('Первый.', OBS_A);
    await flush();
    render(A).comment.append('Второй.', OBS_A);
    await flush();

    calls[0]?.settle('ok');
    await flush();
    calls[1]?.settle(REFUSED);
    await flush();

    render(A).comment.append('Второй.', OBS_A);
    await flush();
    expect(calls[2]?.idempotencyKey).toBe(calls[1]?.idempotencyKey);
  });

  it('sends a verdict to the finding it was pressed on, not to the one the hook is bound to by then', async () => {
    render(A).verdict.record('accept', OBS_A);
    render(B);
    await flush();
    expect(calls[0]?.findingUid).toBe(A);
  });

  it('sends a comment to the finding it was written on, not to the one the hook is bound to by then', async () => {
    render(A).comment.append('Срок согласован.', OBS_A);
    render(B);
    await flush();
    expect(calls[0]?.findingUid).toBe(A);
  });
});

// ------------------------------------------------------------------ the caches

describe('the caches a success refreshes are the ones of the finding it was sent for', () => {
  it('refreshes A’s entries when A’s answer arrives after the hook was re-bound to B', async () => {
    const spy = vi.spyOn((world.model as MutationModel).client, 'invalidateQueries');
    render(A).verdict.record('accept', OBS_A);
    await flush();
    render(B);
    calls[0]?.settle('ok');
    await flush();

    const keys = spy.mock.calls.map(([filters]) => JSON.stringify((filters as { queryKey: unknown }).queryKey));
    expect(keys.sort()).toEqual(decisionCacheKeys(A, RUN).map((key) => JSON.stringify(key)).sort());
  });

  it('refreshes A’s entries for a comment as well', async () => {
    const spy = vi.spyOn((world.model as MutationModel).client, 'invalidateQueries');
    render(A).comment.append('Срок согласован.', OBS_A);
    await flush();
    render(B);
    calls[0]?.settle('ok');
    await flush();

    const keys = spy.mock.calls.map(([filters]) => JSON.stringify((filters as { queryKey: unknown }).queryKey));
    expect(keys.sort()).toEqual(decisionCacheKeys(A, RUN).map((key) => JSON.stringify(key)).sort());
  });
});
