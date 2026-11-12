/**
 * ✓/✕ on a block finding writes a decision (`F8-WEB`, `D-683`, contract 1.52.0).
 *
 * A finding that stands on portal blocks has no text span, so nothing about a decision may depend on one: the row's ✓ and ✕ are the same
 * commands as for a text finding, filed under the block finding's uid and its canonical observation. The press goes through the real
 * `ReviewRowActions` and the real `useRecordVerdict` over React Query's own mutation observer (`../decisions/mutation-model.ts`);
 * the only thing mocked is the transport, `appendDecision`, so each case fails for the reason a reviewer would see it fail.
 */

import type * as Query from '@tanstack/react-query';
import { isValidElement } from 'react';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MutationModel } from '../decisions/mutation-model';

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

import { ReviewRowActions } from '@/_pages/review';
import type { AppendDecisionRequest, AppendDecisionResponse, FindingObservationId, RunId } from '@/shared/api';
import { appendDecision } from '@/shared/api';
import type { FindingRowActionsProps } from '@/widgets/finding-list';

import { RUN_ID, blockFinding, decisionEvent, observation } from './fixtures';

const BLOCK_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';
const BLOCK_OBSERVATION = 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8D' as FindingObservationId;
const RUN = RUN_ID as RunId;

/** One render of the row's actions: the element is `FindingRowActions` with the two commands the buttons call. */
function rowActions(finding: ReturnType<typeof blockFinding>) {
  world.refIndex = 0;
  world.cellIndex = 0;
  (world.model as MutationModel).rewind();
  const element = ReviewRowActions({ finding, runId: RUN, onOpen: () => {} }) as ReactElement<FindingRowActionsProps>;
  expect(isValidElement(element)).toBe(true);
  return element.props;
}

const sent: { findingUid: string; body: AppendDecisionRequest }[] = [];

async function flush(): Promise<void> {
  await new Promise((done) => setTimeout(done, 0));
}

beforeEach(async () => {
  const { createMutationModel } = await import('../decisions/mutation-model');
  world.model = createMutationModel(world.actual as NonNullable<typeof world.actual>);
  world.refs = [];
  world.cells = [];
  world.refIndex = 0;
  world.cellIndex = 0;
  sent.length = 0;
  vi.clearAllMocks();
  vi.mocked(appendDecision).mockImplementation((input) => {
    const { path, body } = input as unknown as { path: { finding_uid: string }; body: AppendDecisionRequest };
    sent.push({ findingUid: path.finding_uid, body });
    const verdict = body.event_type === 'accept' ? 'accepted' : 'rejected';
    const answer: AppendDecisionResponse = {
      current_verdict: verdict,
      event: decisionEvent({ finding_uid: path.finding_uid, event_type: body.event_type, verdict }),
    };
    return Promise.resolve({ data: answer } as never);
  });
});

describe('✓/✕ on a block finding', () => {
  const block = () => blockFinding({ finding_uid: BLOCK_UID, observation: observation({ ...blockFinding().observation, finding_observation_id: BLOCK_OBSERVATION }) });

  it('records an accept against the block finding and its canonical observation', async () => {
    expect(block().observation.evidence).toEqual([]);

    rowActions(block()).onAccept();
    await flush();

    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'accept', finding_observation_id: BLOCK_OBSERVATION } }]);
  });

  it('records a reject against the block finding and its canonical observation', async () => {
    rowActions(block()).onReject();
    await flush();

    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'reject', finding_observation_id: BLOCK_OBSERVATION } }]);
  });

  it('shows the verdict the server answered with, so the pressed button reads as pressed', async () => {
    expect(rowActions(block()).verdict).toBe('pending');

    rowActions(block()).onAccept();
    await flush();

    expect(rowActions(block()).verdict).toBe('accepted');
    expect(vi.mocked(appendDecision)).toHaveBeenCalledTimes(1);
  });

  it('still refuses ✓ without a chosen severity when the model proposed one, and sends nothing', async () => {
    const proposed = blockFinding({
      finding_uid: BLOCK_UID,
      observation: observation({ ...blockFinding().observation, finding_observation_id: BLOCK_OBSERVATION, proposed_severity: 'critical' }),
    });

    rowActions(proposed).onAccept();
    await flush();

    expect(sent).toEqual([]);
    expect(rowActions(proposed).note?.tone).toBe('fail');
  });
});
