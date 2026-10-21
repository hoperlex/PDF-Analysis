/**
 * What the decision panel does when a button is pressed (`REVIEW-V2-UI-01`).
 *
 * Static markup cannot press anything, so this suite calls the panel as a function with
 * `useState` replaced by indexed cells, reads the element tree it returns, and calls the
 * handlers it finds there: the `<select>`'s `onChange` and the Accept and Reject buttons'
 * `onClick`. That is the panel's own code, run on the browser's own call path, with nothing
 * but the state hook stood in for.
 *
 * What it pins:
 *   - Accept hands up the severity the expert picked in the select, and nothing when they
 *     picked none — never the model's proposal;
 *   - a pick made for one observation is not handed up for another (the panel instance
 *     survives a change of selected finding);
 *   - the select's «not chosen» option clears a pick;
 *   - Reject hands up no severity;
 *   - a finding with no proposal has no select to pick from.
 */

import type { ReactElement, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const cells = vi.hoisted(() => ({ values: [] as unknown[], index: 0 }));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useState: (initial: unknown) => {
      const at = cells.index;
      cells.index += 1;
      if (!(at in cells.values)) cells.values[at] = initial;
      return [
        cells.values[at],
        (next: unknown) => {
          cells.values[at] = typeof next === 'function' ? (next as (v: unknown) => unknown)(cells.values[at]) : next;
        },
      ];
    },
  };
});

import { DecisionPanel } from '@/widgets/decision-panel';
import type { DecisionPanelProps } from '@/widgets/decision-panel';
import { SEVERITY_VALUES } from '@/shared/api';

import { OBSERVATION_ID } from './fixtures';

const OTHER_OBSERVATION = 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

type Props = Record<string, unknown> & {
  children?: ReactNode;
  onChange?: (event: unknown) => void;
  onClick?: () => void;
};

/** Every host element of the tree whose props satisfy `match`. */
function findAll(node: ReactNode, match: (type: unknown, props: Props) => boolean): ReactElement<Props>[] {
  if (node === null || node === undefined || typeof node === 'boolean') return [];
  if (Array.isArray(node)) return node.flatMap((child) => findAll(child as ReactNode, match));
  if (typeof node !== 'object' || !('props' in node)) return [];
  const element = node as ReactElement<Props>;
  const own = match(element.type, element.props) ? [element] : [];
  return [...own, ...findAll(element.props.children, match)];
}

interface Spies {
  readonly onAccept: ReturnType<typeof vi.fn>;
  readonly onReject: ReturnType<typeof vi.fn>;
}

function props(spies: Spies, overrides: Partial<DecisionPanelProps> = {}): DecisionPanelProps {
  return {
    currentVerdict: 'pending',
    observationId: OBSERVATION_ID,
    onAccept: spies.onAccept as DecisionPanelProps['onAccept'],
    onReject: spies.onReject as DecisionPanelProps['onReject'],
    onComment: () => {},
    ...overrides,
  };
}

/** Run the panel once, as React would on a render, with the cells as they now stand. */
function tree(p: DecisionPanelProps): ReactElement<Props> {
  cells.index = 0;
  return DecisionPanel(p) as ReactElement<Props>;
}

function pressAccept(p: DecisionPanelProps): void {
  const [button] = findAll(tree(p), (type, pr) => type === 'button' && pr['data-intent'] === 'accept');
  button?.props.onClick?.();
}

function pressReject(p: DecisionPanelProps): void {
  const [button] = findAll(tree(p), (type, pr) => type === 'button' && pr['data-intent'] === 'reject');
  button?.props.onClick?.();
}

function pick(p: DecisionPanelProps, value: string): void {
  const [select] = findAll(tree(p), (type) => type === 'select');
  select?.props.onChange?.({ target: { value } });
}

let spies: Spies;

beforeEach(() => {
  cells.values = [];
  cells.index = 0;
  spies = { onAccept: vi.fn(), onReject: vi.fn() };
});

describe('Accept hands up the severity the expert picked', () => {
  for (const value of SEVERITY_VALUES) {
    it(`hands up «${value}» after picking it, whatever the model proposed`, () => {
      const p = props(spies, { proposedSeverity: value === 'critical' ? 'economic' : 'critical' });
      pick(p, value);
      pressAccept(p);
      expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID, value);
    });
  }

  it('hands up nothing when nothing was picked, and does not borrow the proposal', () => {
    pressAccept(props(spies, { proposedSeverity: 'critical' }));
    expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID, undefined);
  });

  it('hands up nothing after the pick is taken back with the placeholder option', () => {
    const p = props(spies, { proposedSeverity: 'critical' });
    pick(p, 'economic');
    pick(p, '');
    pressAccept(p);
    expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID, undefined);
  });

  it('hands up nothing for a select value outside the contract’s set', () => {
    const p = props(spies, { proposedSeverity: 'critical' });
    pick(p, 'urgent');
    pressAccept(p);
    expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID, undefined);
  });
});

describe('a pick belongs to the observation it was made for', () => {
  it('is not handed up for the next finding the same panel instance is shown', () => {
    pick(props(spies, { proposedSeverity: 'critical' }), 'economic');
    pressAccept(props(spies, { proposedSeverity: 'critical', observationId: OTHER_OBSERVATION }));
    expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OTHER_OBSERVATION, undefined);
  });

  it('is shown in the select only for the observation it was made for', () => {
    pick(props(spies, { proposedSeverity: 'critical' }), 'economic');
    const own = findAll(tree(props(spies, { proposedSeverity: 'critical' })), (t) => t === 'select')[0];
    const other = findAll(
      tree(props(spies, { proposedSeverity: 'critical', observationId: OTHER_OBSERVATION })),
      (t) => t === 'select',
    )[0];
    expect(own?.props.value).toBe('economic');
    expect(other?.props.value).toBe('');
  });
});

describe('Reject and a finding without a proposal', () => {
  it('Reject hands up no severity, even after one was picked', () => {
    const p = props(spies, { proposedSeverity: 'critical' });
    pick(p, 'economic');
    pressReject(p);
    expect(spies.onReject).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID);
    expect(spies.onAccept).not.toHaveBeenCalled();
  });

  it('a finding without a proposal has no select, so an accept hands up no severity', () => {
    const p = props(spies);
    expect(findAll(tree(p), (t) => t === 'select')).toEqual([]);
    pressAccept(p);
    expect(spies.onAccept).toHaveBeenCalledExactlyOnceWith(OBSERVATION_ID, undefined);
  });
});
