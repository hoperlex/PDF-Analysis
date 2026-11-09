/**
 * `UI-B-14`: «Перенести решения из V#» on a pass's proposals, and «↩ Перенесено из V#» on a carried decision.
 *
 * The control is rendered, not read from source (`D-53`): which earlier versions it offers and which it does not, the
 * confirmation that comes before anything is sent, the report in which every source decision is counted once, each
 * refusal in words. The hook is exercised through its configuration, as `import-proposal-decisions.test.ts` does: one
 * `Idempotency-Key` per intent, the same press in flight sends nothing twice, a stored report ends the intent, and what a
 * carried decision moves is re-read -- nothing when nothing was carried.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
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
  return { ...actual, carryOverProposalDecisions: vi.fn() };
});

import * as react from 'react';

import type { OptimisationPass, ProposalDecisionCarryoverReport } from '@/shared/api';
import { ApiError, carryOverProposalDecisions, queryKeys } from '@/shared/api';
import {
  CARRYOVER_REFUSAL_TEXT,
  carriedFromLabel,
  carrySources,
  carryOverFailureMessage,
  decidedCount,
  describeCarryover,
} from '@/entities/optimisation-proposal';
import {
  CarryOverProposalDecisionsView,
  carryOverSignature,
  useCarryOverProposalDecisions,
} from '@/features/carry-over-proposal-decisions';
import { ExportProposalsView, ProposalDecisionLine, ProposalHistoryView } from '@/widgets/optimisation-proposals';

import { OLDER_PASS_ID, PASS_ID, decision, pass } from './fixtures';

const noop = (): void => undefined;
const rewind = (): void => (react as unknown as { __rewind: () => void }).__rewind();
const forget = (): void => (react as unknown as { __forget: () => void }).__forget();

const V1_PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9A';
const V1_NEWER_PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9B';
const FOREIGN_PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9C';

const decided = { pending: 1, accept: 3, reject: 1, revise: 1 };
const undecided = { pending: 5, accept: 0, reject: 0, revise: 0 };

/** The open pass is over version 3; the set also has passes over versions 2 and 1 (two of them), and a foreign set's pass. */
const open: OptimisationPass = pass({ optimisation_pass_id: PASS_ID, version_ordinal: 3 });
const passes: readonly OptimisationPass[] = [
  open,
  pass({ optimisation_pass_id: OLDER_PASS_ID, version_ordinal: 2, decision_counts: decided }),
  pass({ optimisation_pass_id: V1_NEWER_PASS_ID, version_ordinal: 1, decision_counts: undecided }),
  pass({ optimisation_pass_id: V1_PASS_ID, version_ordinal: 1, decision_counts: decided }),
  pass({
    optimisation_pass_id: FOREIGN_PASS_ID,
    document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q9D',
    version_ordinal: 1,
    decision_counts: decided,
  }),
];

function report(over: Partial<ProposalDecisionCarryoverReport> = {}): ProposalDecisionCarryoverReport {
  return {
    optimisation_pass_id: PASS_ID,
    source_optimisation_pass_id: OLDER_PASS_ID,
    source_version_ordinal: 2,
    source_decided: 8,
    carried: 5,
    target_decided: 1,
    ambiguous: 1,
    unmatched: 1,
    ...over,
  };
}

function view(
  over: Partial<Parameters<typeof CarryOverProposalDecisionsView>[0]> = {},
): string {
  return renderToStaticMarkup(
    createElement(CarryOverProposalDecisionsView, {
      sources: carrySources(passes, open),
      confirming: null,
      pending: false,
      report: null,
      failure: null,
      onAsk: noop,
      onConfirm: noop,
      onCancel: noop,
      ...over,
    }),
  );
}

describe('the sources', () => {
  it('are the earlier versions of the same set, newest version first, each with the pass to carry from', () => {
    const sources = carrySources(passes, open);
    expect(sources.map((source) => [source.versionOrdinal, source.pass.optimisation_pass_id])).toEqual([
      [2, OLDER_PASS_ID],
      // Two passes over version 1: the newer holds no decision, so the one that does is offered.
      [1, V1_PASS_ID],
    ]);
  });

  it('offer the newest pass of a version when none holds a decision, and nothing for a version that is not earlier', () => {
    const none = passes.map((candidate) => ({ ...candidate, decision_counts: undecided }));
    expect(carrySources(none, open).map((source) => source.pass.optimisation_pass_id)).toEqual([OLDER_PASS_ID, V1_NEWER_PASS_ID]);
    const first = pass({ optimisation_pass_id: V1_PASS_ID, version_ordinal: 1 });
    expect(carrySources(passes, first)).toEqual([]);
    expect(carrySources([first], first)).toEqual([]);
    expect(carrySources([], open)).toEqual([]);
  });

  it('count the decisions in force and not the pending ones', () => {
    expect(decidedCount(pass({ decision_counts: decided }))).toBe(5);
    expect(decidedCount(pass({ decision_counts: undecided }))).toBe(0);
  });
});

describe('the control', () => {
  it('offers one button for each earlier version, and nothing at all when there is none', () => {
    const markup = view();
    expect(markup).toContain('data-proposal-decision-carryover');
    expect(markup).toContain('Перенести решения из V2');
    expect(markup).toContain('Перенести решения из V1');
    expect(markup).toContain('data-carryover-source="2"');
    expect(markup).not.toContain('disabled=""');
    expect(markup).not.toContain('data-carryover-confirm');
    expect(view({ sources: [] })).toBe('');
  });

  it('asks before anything is sent: what is carried, where from, and on whose name', () => {
    const source = carrySources(passes, open)[0]!;
    const markup = view({ confirming: source });
    expect(markup).toContain('data-carryover-confirm');
    expect(markup).toContain('принято — 3, отклонено — 1, на доработку — 1');
    expect(markup).toContain('от вашего имени');
    expect(markup).toContain('по содержанию');
    expect(markup).toContain('Если подходящих предложений несколько, ничего не переносится');
    expect(markup).toContain('Перенести из V2');
    expect(markup).toContain('Отмена');
    // While a confirmation is open the version buttons wait.
    expect(markup).toContain('disabled=""');
  });

  it('says plainly that the source holds no decision, and cannot be pressed twice while it works', () => {
    const empty = carrySources(passes.map((candidate) => ({ ...candidate, decision_counts: undecided })), open)[0]!;
    expect(view({ confirming: empty })).toContain('В V2 нет решений для переноса');
    const working = view({ confirming: carrySources(passes, open)[0]!, pending: true });
    expect(working).toContain('Переношу решения…');
    expect(working.match(/disabled=""/g)?.length).toBeGreaterThanOrEqual(3);
  });

  it('reports every source decision once, and each refusal in a role=alert line', () => {
    const markup = view({ report: report() });
    expect(markup).toContain('data-carryover-carried="5"');
    expect(markup).toContain('Перенесено 5 из 8 решений V2.');
    expect(markup).toContain('Уже решено в этом проходе, оставлено как есть: 1.');
    expect(markup).toContain('одинаковых предложений несколько: 1.');
    expect(markup).toContain('такого предложения в этом проходе нет: 1.');
    expect(view({ failure: 'Нельзя.' })).toMatch(/role="alert"[^>]*>Нельзя\./);
  });
});

describe('the report in words', () => {
  it('adds up: only the outcomes that occurred are said, and a source without decisions says so', () => {
    const lines = describeCarryover(report({ target_decided: 0, ambiguous: 0, unmatched: 0, source_decided: 5 }));
    expect(lines).toEqual(['Перенесено 5 из 5 решений V2.']);
    expect(describeCarryover(report({ source_decided: 0, carried: 0, target_decided: 0, ambiguous: 0, unmatched: 0 }))).toEqual([
      'В V2 нет решений для переноса.',
    ]);
    const all = describeCarryover(report());
    expect(all).toHaveLength(4);
    for (const line of all) expect(line).not.toMatch(/[a-z_]/); // the version's «V2» is the only Latin letter
  });

  it('give every refusal of the contract a Russian sentence, and fall back to the catalogue for the rest', () => {
    expect(Object.keys(CARRYOVER_REFUSAL_TEXT).sort()).toEqual([
      'carryover_source_is_target',
      'carryover_source_not_earlier',
      'carryover_source_other_document',
      'carryover_source_unknown',
    ]);
    for (const sentence of Object.values(CARRYOVER_REFUSAL_TEXT)) expect(sentence).not.toMatch(/[A-Za-z_]/);
    const refuse = (reason: string) =>
      new ApiError(
        409,
        {
          contract_version: '1.45.0', error_code: 'conflict', message: 'x', correlation_id: 'cid-1', retryable: false,
          details: { aggregate_type: 'OptimisationPass', conflict_reason: reason },
        },
        'cid-1',
      );
    expect(carryOverFailureMessage(refuse('carryover_source_not_earlier')).detail).toBe(CARRYOVER_REFUSAL_TEXT['carryover_source_not_earlier']);
    expect(carryOverFailureMessage(refuse('something_new')).detail).not.toBe('');
  });
});

describe('the mark on a carried decision', () => {
  const carried = decision({
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q9E',
    carried_from: {
      proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8V',
      optimisation_pass_id: OLDER_PASS_ID,
      version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q9F',
      version_ordinal: 2,
    },
  });

  it('says where it came from, and a decision made directly says nothing of the kind', () => {
    expect(carriedFromLabel(carried)).toBe('↩ Перенесено из V2');
    expect(carriedFromLabel(decision())).toBeNull();
    const line = renderToStaticMarkup(createElement(ProposalDecisionLine, { decision: carried }));
    expect(line).toContain('↩ Перенесено из V2');
    expect(line).toContain('data-carried-from="2"');
    const direct = renderToStaticMarkup(createElement(ProposalDecisionLine, { decision: decision() }));
    expect(direct).not.toContain('Перенесено');
    expect(direct).not.toContain('data-carried-from');
  });

  it('is in the history, beside the verdict it marks', () => {
    const markup = renderToStaticMarkup(createElement(ProposalHistoryView, { items: [decision(), carried] }));
    expect(markup.match(/Перенесено из V2/g)).toHaveLength(1);
  });

  it('shows no mark for a decision that is not there', () => {
    expect(renderToStaticMarkup(createElement(ProposalDecisionLine, { decision: null }))).not.toContain('Перенесено');
  });
});

describe('the export beside it', () => {
  it('carries the control only when given', () => {
    const plain = renderToStaticMarkup(createElement(ExportProposalsView, { pending: false, failure: null, onDownload: noop }));
    expect(plain).not.toContain('data-proposal-decision-carryover');
    const both = renderToStaticMarkup(
      createElement(ExportProposalsView, {
        pending: false, failure: null, onDownload: noop,
        carryOverControl: createElement(CarryOverProposalDecisionsView, {
          sources: carrySources(passes, open), confirming: null, pending: false, report: null, failure: null,
          onAsk: noop, onConfirm: noop, onCancel: noop,
        }),
      }),
    );
    expect(both).toContain('data-proposal-decision-carryover');
  });
});

describe('the command', () => {
  type Command = { passId: string; sourcePassId: string };
  type Captured = {
    mutationFn: (command: Command) => Promise<ProposalDecisionCarryoverReport>;
    onSuccess?: (result: ProposalDecisionCarryoverReport, command: Command) => void;
    retry?: boolean;
  };
  const hook = (): Captured => {
    rewind();
    return useCarryOverProposalDecisions() as unknown as Captured;
  };
  const command = (sourcePassId = OLDER_PASS_ID): Command => ({ passId: PASS_ID, sourcePassId });
  const keyOf = (call: number): string =>
    (vi.mocked(carryOverProposalDecisions).mock.calls[call]?.[0] as { idempotencyKey: string }).idempotencyKey;

  beforeEach(() => {
    calls.invalidations.length = 0;
    vi.clearAllMocks();
    forget();
  });

  it('sends the source to the pass under a key, and the intent is the two passes', async () => {
    vi.mocked(carryOverProposalDecisions).mockResolvedValue({ data: report() } as never);
    expect(hook().retry).toBe(false);
    await hook().mutationFn(command());
    expect(vi.mocked(carryOverProposalDecisions).mock.calls[0]?.[0]).toMatchObject({
      path: { optimisation_pass_id: PASS_ID },
      body: { source_optimisation_pass_id: OLDER_PASS_ID },
    });
    expect(carryOverSignature(command())).not.toBe(carryOverSignature(command(V1_PASS_ID)));
  });

  it('keeps the key of a failed press for its retry, and takes a new one for another source or once a report is stored', async () => {
    vi.mocked(carryOverProposalDecisions)
      .mockRejectedValueOnce(new Error('lost'))
      .mockResolvedValue({ data: report() } as never);
    await expect(hook().mutationFn(command())).rejects.toThrow('lost');
    await hook().mutationFn(command());
    expect(keyOf(1)).toBe(keyOf(0)); // a retry of the lost press: the same key, so the server appends once
    hook().onSuccess?.(report(), command()); // the report is stored: the intent is over
    await hook().mutationFn(command());
    expect(keyOf(2)).not.toBe(keyOf(0)); // pressing again later repeats the matching on purpose
    await hook().mutationFn(command(V1_PASS_ID));
    expect(keyOf(3)).not.toBe(keyOf(2));
  });

  it('joins a press that finds its intent in flight and sends nothing twice', async () => {
    let release: (value: unknown) => void = noop;
    vi.mocked(carryOverProposalDecisions).mockReturnValue(new Promise((resolve) => (release = resolve)) as never);
    const first = hook().mutationFn(command());
    const second = hook().mutationFn(command());
    expect(vi.mocked(carryOverProposalDecisions)).toHaveBeenCalledTimes(1);
    release({ data: report() });
    await expect(Promise.all([first, second])).resolves.toEqual([report(), report()]);
  });

  it('re-reads what a decision moves when something was carried, and nothing when nothing was', () => {
    hook().onSuccess?.(report({ carried: 0 }), command());
    expect(calls.invalidations).toEqual([]);
    hook().onSuccess?.(report(), command());
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.optimisation.proposalsOf(PASS_ID) }],
      [{ queryKey: queryKeys.optimisation.allPasses() }],
      [{ queryKey: queryKeys.optimisation.allAccepted() }],
      [{ queryKey: queryKeys.optimisation.allProposalDecisions() }],
    ]);
  });
});
