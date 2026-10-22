/**
 * An empty comment is refused, and the refusal reaches the screen
 * (`WEB-REVIEW-FOLLOWUPS-01`, item 5).
 *
 * `useAppendComment` kept its refusal in a `useRef`. A write to a ref does not schedule a
 * render, and an empty comment sends nothing, so nothing else in the hook schedules one
 * either: the reviewer pressed «Добавить», nothing was sent, and the sentence that says why
 * appeared only when something unrelated happened to render the page. The refusal is state
 * now, filed under the finding it was raised for (the hook lives at page level and survives a
 * change of selected finding, as `useRecordVerdict`'s refusal does).
 *
 * To show the defect rather than argue it, the React hooks are replaced by a small model of
 * what React guarantees: a ref is one holder that persists across renders and schedules
 * nothing; a state cell persists across renders and its setter schedules a render. The test
 * counts the renders the press asked for. The mutation observer is the other thing that
 * schedules renders in the real hook; it is a recorder here, and an empty press never calls it.
 * Each case goes red under a quoted mutation (`docs/program/WEB-REVIEW-FOLLOWUPS-01.md`).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const world = vi.hoisted(() => ({
  refs: [] as { current: unknown }[],
  refIndex: 0,
  cells: [] as unknown[],
  cellIndex: 0,
  /** Renders asked for by a state setter since the last render. */
  scheduled: 0,
  mutate: null as null | ((request: unknown) => void),
  resets: 0,
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: () => ({
    mutate: (request: unknown) => world.mutate?.(request),
    isPending: false,
    error: null,
    data: undefined,
    reset: () => {
      world.resets += 1;
    },
  }),
  useQueryClient: () => ({ invalidateQueries: () => Promise.resolve() }),
}));

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
      if (!(at in world.cells)) world.cells[at] = initial;
      return [
        world.cells[at],
        (next: unknown) => {
          world.scheduled += 1;
          world.cells[at] = typeof next === 'function' ? (next as (v: unknown) => unknown)(world.cells[at]) : next;
        },
      ];
    },
  };
});

import type { FindingUid, RunId } from '@/shared/api';
import { COMMENT_REFUSALS, commentRefusalMessage, useAppendComment } from '@/features/append-comment';

import { FINDING_UID, OBSERVATION_ID, RUN_ID } from '../review/fixtures';

const OTHER_FINDING = `${FINDING_UID.slice(0, -1)}Z` as FindingUid;

/** One render of the hook: indexes rewound, the count of requested renders reset. */
function render(findingUid: FindingUid = FINDING_UID as FindingUid) {
  world.refIndex = 0;
  world.cellIndex = 0;
  world.scheduled = 0;
  return useAppendComment({ findingUid, runId: RUN_ID as RunId });
}

const sent: unknown[] = [];

beforeEach(() => {
  world.refs = [];
  world.cells = [];
  world.refIndex = 0;
  world.cellIndex = 0;
  world.scheduled = 0;
  world.resets = 0;
  sent.length = 0;
  world.mutate = (request) => {
    sent.push(request);
  };
});

describe('an empty comment asks the screen to render the refusal', () => {
  it('asks for a render, because nothing else will', () => {
    const api = render();
    api.append('', OBSERVATION_ID);
    expect(sent).toEqual([]);
    expect(world.scheduled).toBeGreaterThan(0);
  });

  it('hands the refusal to the next render', () => {
    render().append('', OBSERVATION_ID);
    expect(render().refusal).toBe('empty');
  });

  it('refuses a comment of nothing but whitespace the same way', () => {
    const api = render();
    api.append(' \n\t ', OBSERVATION_ID);
    expect(sent).toEqual([]);
    expect(world.scheduled).toBeGreaterThan(0);
    expect(render().refusal).toBe('empty');
  });

  it('has no refusal before any press', () => {
    expect(render().refusal).toBeNull();
  });

  it('says the refusal in Russian, for every member the feature can raise', () => {
    expect(COMMENT_REFUSALS.length).toBeGreaterThan(0);
    for (const refusal of COMMENT_REFUSALS) {
      expect(commentRefusalMessage(refusal)).toMatch(/[А-Яа-яЁё]{4,}/);
    }
  });
});

describe('a comment that goes out takes the refusal back', () => {
  it('sends the trimmed text and clears the refusal of the press before', () => {
    render().append('', OBSERVATION_ID);
    expect(render().refusal).toBe('empty');

    const api = render();
    api.append('  Срок согласован.  ', OBSERVATION_ID);
    expect(sent).toEqual([
      { event_type: 'comment', finding_observation_id: OBSERVATION_ID, comment: 'Срок согласован.' },
    ]);
    expect(render().refusal).toBeNull();
  });
});

describe('the refusal belongs to the finding it was raised for', () => {
  it('is not shown on another finding the same hook instance is bound to', () => {
    render(FINDING_UID as FindingUid).append('', OBSERVATION_ID);
    expect(render(FINDING_UID as FindingUid).refusal).toBe('empty');
    expect(render(OTHER_FINDING).refusal).toBeNull();
  });

  it('is still there when the reviewer returns to that finding', () => {
    render(FINDING_UID as FindingUid).append('', OBSERVATION_ID);
    expect(render(OTHER_FINDING).refusal).toBeNull();
    expect(render(FINDING_UID as FindingUid).refusal).toBe('empty');
  });
});

describe('reset forgets the refusal', () => {
  it('clears it', () => {
    render().append('', OBSERVATION_ID);
    expect(render().refusal).toBe('empty');

    render().reset();
    expect(world.resets).toBe(1);
    expect(render().refusal).toBeNull();
  });
});
