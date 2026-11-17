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
  const element = ReviewRowActions({ finding, runId: RUN }) as ReactElement<FindingRowActionsProps>;
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
  const proposedBlock = (over: Partial<ReturnType<typeof blockFinding>> = {}) => blockFinding({
    finding_uid: BLOCK_UID,
    observation: observation({ ...blockFinding().observation, finding_observation_id: BLOCK_OBSERVATION, proposed_severity: 'critical' }),
    ...over,
  });

  it('records an accept against the block finding and its canonical observation', async () => {
    expect(block().observation.evidence).toEqual([]);

    rowActions(block()).onAccept('');
    await flush();

    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'accept', finding_observation_id: BLOCK_OBSERVATION } }]);
  });

  it('records a reject against the block finding and its canonical observation', async () => {
    rowActions(block()).onReject('');
    await flush();

    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'reject', finding_observation_id: BLOCK_OBSERVATION } }]);
  });

  it('records the reason typed beside ✓ and ✕ as the comment of the same event, and none when the field is empty (`UIP-S06-02`)', async () => {
    rowActions(block()).onAccept(' Размер проёма подтверждён по чертежу ');
    await flush();
    rowActions(block()).onReject('');
    await flush();

    expect(sent).toEqual([
      { findingUid: BLOCK_UID, body: { event_type: 'accept', finding_observation_id: BLOCK_OBSERVATION, comment: 'Размер проёма подтверждён по чертежу' } },
      { findingUid: BLOCK_UID, body: { event_type: 'reject', finding_observation_id: BLOCK_OBSERVATION } },
    ]);
  });

  it('shows the verdict the server answered with, so the pressed button reads as pressed', async () => {
    expect(rowActions(block()).verdict).toBe('pending');

    rowActions(block()).onAccept('');
    await flush();

    expect(rowActions(block()).verdict).toBe('accepted');
    expect(vi.mocked(appendDecision)).toHaveBeenCalledTimes(1);
  });

  it('still refuses ✓ without a chosen severity when the model proposed one, and sends nothing', async () => {
    const proposed = proposedBlock();

    rowActions(proposed).onAccept('');
    await flush();

    expect(sent).toEqual([]);
    expect(rowActions(proposed).note?.tone).toBe('fail');
  });
});

/**
 * The choice «Критичность» beside ✓ in the row (`UIP-S06-08`, `R-151j`). The row hands the request builder what the expert chose and
 * nothing else; the rules (the refusal, a severity only on an accept) are `features/record-verdict`'s and are read here only through
 * what the row sends and says. The cells of the stub `useState` stand for one mounted row, so a second finding handed to the same row
 * is the full-screen view stepping to the neighbour.
 */
describe('the choice of severity in the row', () => {
  const proposed = (uid = BLOCK_UID, over: Record<string, unknown> = {}) => blockFinding({
    finding_uid: uid,
    observation: observation({ ...blockFinding().observation, finding_observation_id: BLOCK_OBSERVATION, proposed_severity: 'critical' }),
    ...over,
  });

  it('offers none for a finding the model proposed no severity for, and the one that has a proposal starts empty', () => {
    expect(rowActions(blockFinding({ finding_uid: BLOCK_UID })).severity).toBeUndefined();
    const choice = rowActions(proposed()).severity;
    expect(choice?.value).toBe('');
    expect(choice?.required).toBe(true);
    expect(choice?.invalid).toBe(false);
  });

  it('never puts the proposal into the choice, whichever severity the model proposed', async () => {
    for (const value of ['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'] as const) {
      const finding = blockFinding({
        finding_uid: BLOCK_UID,
        observation: observation({ ...blockFinding().observation, finding_observation_id: BLOCK_OBSERVATION, proposed_severity: value }),
      });
      expect(rowActions(finding).severity?.value).toBe('');
    }
    rowActions(proposed()).onAccept('');
    await flush();
    expect(sent).toEqual([]);
  });

  it('sends one accept with the severity the expert chose and the reason, in the same event', async () => {
    rowActions(proposed()).severity?.onChange('economic');
    expect(rowActions(proposed()).severity?.value).toBe('economic');

    rowActions(proposed()).onAccept(' Размер подтверждён по листу 3 ');
    await flush();

    expect(sent).toEqual([
      { findingUid: BLOCK_UID, body: { event_type: 'accept', finding_observation_id: BLOCK_OBSERVATION, comment: 'Размер подтверждён по листу 3', severity: 'economic' } },
    ]);
    expect(vi.mocked(appendDecision)).toHaveBeenCalledTimes(1);
  });

  it('refuses ✓ without a choice in the row itself, with the panel’s sentence, sends nothing and says the select is invalid', async () => {
    rowActions(proposed()).onAccept('Причина');
    await flush();

    expect(sent).toEqual([]);
    const after = rowActions(proposed());
    expect(after.note).toEqual({ tone: 'fail', text: 'Перед принятием выберите критичность. Ничего не отправлено.' });
    expect(after.severity?.invalid).toBe(true);
  });

  it('lifts the refusal when the choice it asked for is made, and then ✓ goes', async () => {
    rowActions(proposed()).onAccept('');
    await flush();
    expect(rowActions(proposed()).note?.tone).toBe('fail');

    rowActions(proposed()).severity?.onChange('operational');
    expect(rowActions(proposed()).note).toBeNull();
    expect(rowActions(proposed()).severity?.invalid).toBe(false);

    rowActions(proposed()).onAccept('');
    await flush();
    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'accept', finding_observation_id: BLOCK_OBSERVATION, severity: 'operational' } }]);
  });

  it('empties the choice when the expert picks the empty item, and ✓ is refused again', async () => {
    rowActions(proposed()).severity?.onChange('economic');
    rowActions(proposed()).severity?.onChange('');
    expect(rowActions(proposed()).severity?.value).toBe('');

    rowActions(proposed()).onAccept('');
    await flush();
    expect(sent).toEqual([]);
  });

  it('does not follow the reader to another finding: the same row handed the neighbour reads empty', async () => {
    const NEXT_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';
    rowActions(proposed()).severity?.onChange('economic');
    expect(rowActions(proposed()).severity?.value).toBe('economic');

    expect(rowActions(proposed(NEXT_UID)).severity?.value).toBe('');
    rowActions(proposed(NEXT_UID)).onAccept('');
    await flush();
    expect(sent).toEqual([]);

    // Back on the first finding the choice made there is as it was left.
    expect(rowActions(proposed()).severity?.value).toBe('economic');
  });

  it('reads the severity the expert already decided, and the proposal never', () => {
    expect(rowActions(proposed(BLOCK_UID, { decided_severity: 'recommendation' })).severity?.value).toBe('recommendation');
    expect(rowActions(proposed(BLOCK_UID, { decided_severity: 'recommendation' })).severity?.required).toBe(false);
  });

  it('sends no severity for a reject, whatever is chosen', async () => {
    rowActions(proposed()).severity?.onChange('economic');
    rowActions(proposed()).onReject('Не относится к разделу');
    await flush();
    expect(sent).toEqual([{ findingUid: BLOCK_UID, body: { event_type: 'reject', finding_observation_id: BLOCK_OBSERVATION, comment: 'Не относится к разделу' } }]);
  });
});
