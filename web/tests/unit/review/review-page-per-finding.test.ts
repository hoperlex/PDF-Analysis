/**
 * What the review screen tells the reviewer about a press, after the reviewer moves to another
 * finding (`WEB-HOOKS-PER-FINDING-01`, `D-201`).
 *
 * The hooks are bound to the selected finding but live in the page, so a request pressed on
 * finding A is still the page's last request when the reviewer opens finding B. The page used
 * to read `error` and `isPending` straight from the hooks: B showed A's «Вердикт не записан»,
 * said «Принимаю…» for a press made elsewhere and had its three buttons disabled.
 *
 * Here the page is the real page with the real hooks and the real decision panel. What is
 * replaced is the two ends: the mutation is React Query's own observer kept across renders
 * (`../decisions/mutation-model.ts`), and the server is `appendDecision` behind a gate the test
 * opens. A press is made the way the reviewer makes it -- through the panel's own handler,
 * taken from the props of a render -- and "moving to B" is another render of the page with B
 * first in the list (the page opens the first finding when nothing is selected), so the cases
 * read what the second screen shows, not what a hook returns.
 *
 * Each case goes red under a quoted mutation (`docs/program/WEB-HOOKS-PER-FINDING-01.md`).
 */

import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MutationModel } from '../decisions/mutation-model';

const world = vi.hoisted(() => ({
  actual: null as null | Pick<
    typeof import('@tanstack/react-query'),
    'MutationObserver' | 'QueryClient'
  >,
  model: null as null | MutationModel,
  panelProps: null as null | Record<string, unknown>,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  world.actual = actual;
  return {
    ...actual,
    useMutation: (options: never) => (world.model as MutationModel).useMutation(options),
  };
});

vi.mock('@/widgets/decision-panel', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    DecisionPanel: (props: Record<string, unknown>) => {
      world.panelProps = props;
      return createElement(actual.DecisionPanel as never, props);
    },
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, appendDecision: vi.fn() };
});

import { ReviewPage } from '@/_pages/review';
import type {
  AppendDecisionRequest,
  FindingDetail,
  FindingObservationId,
} from '@/shared/api';
import { appendDecision, queryKeys } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import {
  FINDING_UID,
  OBSERVATION_ID,
  PROJECT_UID,
  RUN_ID,
  decisionEvent,
  findingDetail,
  observation,
  runStatus,
} from './fixtures';

const OBS_A = OBSERVATION_ID as FindingObservationId;
const OBS_B = `${OBSERVATION_ID.slice(0, -1)}Z` as FindingObservationId;

const FINDING_A = findingDetail();
const FINDING_B = findingDetail({
  finding_uid: `${FINDING_UID.slice(0, -1)}Z`,
  observation: observation({ finding_observation_id: OBS_B }),
});

/** The screen as the reviewer sees it with `first` open (the page opens the first finding). */
function screenOpenOn(first: FindingDetail, second: FindingDetail): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  client.setQueryData(queryKeys.runs.findings(RUN_ID), {
    data: { items: [first, second], page: { next_cursor: null } },
  });
  for (const detail of [first, second]) {
    client.setQueryData(queryKeys.findings.detail(detail.finding_uid), { data: detail });
    client.setQueryData(queryKeys.findings.decisions(detail.finding_uid), {
      data: { items: [], page: { next_cursor: null } },
    });
  }
  (world.model as MutationModel).rewind();
  return renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

const onA = (): string => screenOpenOn(FINDING_A, FINDING_B);
const onB = (): string => screenOpenOn(FINDING_B, FINDING_A);

interface Held {
  readonly body: AppendDecisionRequest;
  readonly settle: (outcome: 'ok' | Error) => void;
}

const held: Held[] = [];

async function flush(): Promise<void> {
  await new Promise((done) => setTimeout(done, 0));
}

function press(action: (props: Record<string, (...args: never[]) => void>) => void): void {
  action(world.panelProps as unknown as Record<string, (...args: never[]) => void>);
}

const BUTTON = (intent: string): RegExp =>
  new RegExp(`<button type="button" class="am-button" data-intent="${intent}" disabled=""`);

beforeEach(async () => {
  const { createMutationModel } = await import('../decisions/mutation-model');
  world.model = createMutationModel(world.actual as NonNullable<typeof world.actual>);
  world.panelProps = null;
  held.length = 0;
  vi.clearAllMocks();
  vi.mocked(appendDecision).mockImplementation((input) => {
    const { path, body } = input as unknown as {
      path: { finding_uid: string };
      body: AppendDecisionRequest;
    };
    return new Promise((resolve, reject) => {
      held.push({
        body,
        settle: (outcome) => {
          if (outcome === 'ok') {
            resolve({
              data: {
                current_verdict: body.event_type === 'reject' ? 'rejected' : 'accepted',
                event: decisionEvent({ finding_uid: path.finding_uid, event_type: body.event_type }),
              },
            } as never);
          } else reject(outcome);
        },
      });
    });
  });
});

describe('a verdict that failed is shown on the finding it was pressed on, and only there', () => {
  it('shows «Вердикт не записан» on A, not on B, and again on A', async () => {
    onA();
    press((props) => props.onReject?.(OBS_A as never));
    await flush();
    held[0]?.settle(new Error('Сервер недоступен'));
    await flush();

    expect(onA()).toContain('Вердикт не записан');
    expect(onB()).not.toContain('Вердикт не записан');
    expect(onA()).toContain('Вердикт не записан');
  });
});

describe('a verdict still going out disables and words the finding it was pressed on, and only that', () => {
  it('says «Принимаю…» with the buttons disabled on A, and neither on B', async () => {
    onA();
    press((props) => props.onAccept?.(OBS_A as never, undefined as never));
    await flush();

    const screenA = onA();
    expect(screenA).toContain('Принимаю…');
    for (const intent of ['accept', 'reject', 'comment']) expect(screenA).toMatch(BUTTON(intent));

    const screenB = onB();
    expect(screenB).not.toContain('Принимаю…');
    expect(world.panelProps?.pendingIntent).toBeNull();
    for (const intent of ['accept', 'reject', 'comment']) expect(screenB).not.toMatch(BUTTON(intent));
  });

  it('says «Отклоняю…» on A for a reject, and nothing on B', async () => {
    onA();
    press((props) => props.onReject?.(OBS_A as never));
    await flush();

    expect(onA()).toContain('Отклоняю…');
    expect(onB()).not.toContain('Отклоняю…');
  });
});

describe('a comment is kept to its finding the same way', () => {
  it('shows «Комментарий не добавлен» on A, not on B', async () => {
    onA();
    press((props) => props.onComment?.('Срок согласован.' as never, OBS_A as never));
    await flush();
    held[0]?.settle(new Error('Сервер недоступен'));
    await flush();

    expect(onA()).toContain('Комментарий не добавлен');
    expect(onB()).not.toContain('Комментарий не добавлен');
  });

  it('says «Добавляю…» with the buttons disabled on A, and neither on B', async () => {
    onA();
    press((props) => props.onComment?.('Срок согласован.' as never, OBS_A as never));
    await flush();

    const screenA = onA();
    expect(screenA).toContain('Добавляю…');
    expect(screenA).toMatch(BUTTON('accept'));

    const screenB = onB();
    expect(screenB).not.toContain('Добавляю…');
    expect(screenB).not.toMatch(BUTTON('accept'));
  });
});

describe('the verdict shown on a finding is the answer to a press on that finding', () => {
  it('shows A’s answer on A and the server’s own verdict on B', async () => {
    onA();
    press((props) => props.onReject?.(OBS_A as never));
    await flush();
    held[0]?.settle('ok');
    await flush();

    onA();
    expect(world.panelProps?.currentVerdict).toBe('rejected');
    onB();
    expect(world.panelProps?.currentVerdict).toBe('pending');
  });
});
