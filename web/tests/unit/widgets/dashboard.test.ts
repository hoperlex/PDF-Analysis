/**
 * The dashboard's pure aggregation logic — `W46-DASH`.
 *
 * Three modules, three ways `R-23`'s addendum's rule ("no invented numbers… a zero that
 * nothing computed is an invented number too") can be broken by an aggregate specifically,
 * as opposed to a single reading: folding an absent value into a sum as zero, and counting
 * the same underlying thing more than once because the wire repeats it. Each `it` below is
 * paired with a comment naming the one-line mutation that would defeat it and was run by
 * hand to confirm the test reds — `OPERATING_CONSTRAINTS.md` §12's rule that an assertion
 * nobody has seen fail is not evidence of anything.
 */

import { describe, expect, it } from 'vitest';

import type { DecisionRecord, Project } from '@/shared/api';
import { summarizeDocumentTotals, summarizeRunActivity, tallyVerdicts } from '@/widgets/dashboard';
import { runStatus } from '../review/fixtures';

function project(overrides: Partial<Project> = {}): Project {
  return {
    project_uid: `prj_${'0'.repeat(26)}`,
    name: 'Проект',
    created_at: '2026-09-10T08:00:00.000Z',
    ...overrides,
  };
}

function decisionRecord(overrides: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_${'0'.repeat(26)}`,
    finding_uid: `fnd_${'0'.repeat(26)}`,
    finding_observation_id: `fobs_${'0'.repeat(26)}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: null,
    author_label: 'проверяющий',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: `prj_${'0'.repeat(26)}`,
    run_id: `run_${'0'.repeat(26)}`,
    category: 'internal_contradiction',
    finding_text: 'Срок поставки указан дважды и по-разному.',
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...overrides,
  };
}

// ============================================================== documents-per-project

describe('summarizeDocumentTotals', () => {
  it('sums only the projects that carried a count, and counts the rest separately', () => {
    const summary = summarizeDocumentTotals([
      project({ project_uid: 'prj_a', document_count: 3 }),
      project({ project_uid: 'prj_b', document_count: 5 }),
      // No `document_count` at all — the server did not say, not "zero".
      project({ project_uid: 'prj_c' }),
    ]);
    expect(summary.knownTotal).toBe(8);
    expect(summary.knownProjectCount).toBe(2);
    expect(summary.unknownProjectCount).toBe(1);
    expect(summary.rows.find((row) => row.project.project_uid === 'prj_c')?.count).toBeNull();
    /*
     * Mutation run by hand and confirmed red: treating an absent count as a real zero
     * (`knownTotal += row.count ?? 0; knownProjectCount += 1;` unconditionally, dropping
     * the `unknownProjectCount` branch) — `knownProjectCount` becomes 3, `unknownProjectCount`
     * becomes 0, and `knownTotal` stays 8 by coincidence (0 contributes nothing to a sum
     * either way, which is exactly why the *count*, not the total, is the assertion that
     * catches it).
     */
  });

  it('is zero and empty over no projects, which is a real answer and not a placeholder', () => {
    const summary = summarizeDocumentTotals([]);
    expect(summary).toEqual({ rows: [], knownTotal: 0, knownProjectCount: 0, unknownProjectCount: 0 });
  });
});

// ==================================================================== findings-by-verdict

describe('tallyVerdicts', () => {
  it('counts a finding once no matter how many decision events it has on the wire', () => {
    // Mutation this catches: tallying `records.length` (or iterating `records` directly
    // without the `Map` dedup) instead of `byFinding.size` — that mutation makes this
    // count 3, and it is the mutation `widgets/knowledge-base`'s own header names: "a
    // finding the reviewer returned to carries two rows".
    const tally = tallyVerdicts([
      decisionRecord({ decision_id: 'dec_a', finding_uid: 'fnd_returned', current_verdict: 'accepted' }),
      decisionRecord({
        decision_id: 'dec_b',
        finding_uid: 'fnd_returned',
        event_type: 'comment',
        verdict: null,
        current_verdict: 'accepted',
      }),
      decisionRecord({ decision_id: 'dec_c', finding_uid: 'fnd_returned', current_verdict: 'accepted' }),
      decisionRecord({ decision_id: 'dec_d', finding_uid: 'fnd_other', current_verdict: 'rejected' }),
    ]);
    expect(tally.findingCount).toBe(2);
    expect(tally.byVerdict.accepted).toBe(1);
    expect(tally.byVerdict.rejected).toBe(1);
    expect(tally.byVerdict.pending).toBe(0);
    expect(tally.byVerdict.needs_manual_review).toBe(0);
  });

  it('carries every verdict and every category at zero when nothing reached them', () => {
    const tally = tallyVerdicts([]);
    expect(tally.byVerdict).toEqual({
      pending: 0,
      accepted: 0,
      rejected: 0,
      needs_manual_review: 0,
    });
    expect(tally.byCategory).toEqual({ internal_contradiction: 0, explicit_placeholder: 0 });
  });

  it('tallies by category alongside verdict, from the same dedup', () => {
    const tally = tallyVerdicts([
      decisionRecord({ decision_id: 'dec_a', finding_uid: 'fnd_1', category: 'explicit_placeholder' }),
      decisionRecord({ decision_id: 'dec_b', finding_uid: 'fnd_2', category: 'internal_contradiction' }),
    ]);
    expect(tally.byCategory.explicit_placeholder).toBe(1);
    expect(tally.byCategory.internal_contradiction).toBe(1);
  });
});

// ================================================================== run activity and spend

describe('summarizeRunActivity', () => {
  it('sums cost only over runs that reported one, and counts an absent cost separately', () => {
    const runs = [
      // No provider call at all: `runCost` reads this as `absent`, not as a `0` spend.
      runStatus({ run_id: 'run_a', state: 'published' }),
      runStatus({
        run_id: 'run_b',
        state: 'published',
        cost_micros: 1_000_000,
        cost_basis: 'measured',
        model_call_count: 1,
      }),
    ];
    const summary = summarizeRunActivity(runs);
    // Mutation this catches: summing `run.cost_micros ?? 0` over every run instead of
    // switching on `runCost(run).kind === 'reported'` — both give `reportedCostMicros`
    // 1_000_000 here (the absent run contributes 0 either way), which is exactly why the
    // assertion that matters is `runsWithAbsentCost`, not the sum.
    expect(summary.reportedCostMicros).toBe(1_000_000);
    expect(summary.runsWithReportedCost).toBe(1);
    expect(summary.runsWithAbsentCost).toBe(1);
    expect(summary.runCount).toBe(2);
  });

  it('grades the aggregate `estimated` the moment one contributing run is', () => {
    const summary = summarizeRunActivity([
      runStatus({
        run_id: 'run_a',
        cost_micros: 500_000,
        cost_basis: 'measured',
        model_call_count: 1,
      }),
      runStatus({
        run_id: 'run_b',
        cost_micros: 250_000,
        cost_basis: 'estimated',
        model_call_count: 2,
      }),
    ]);
    // `R-14`'s own rule, applied across runs instead of within one: `estimated` wins.
    expect(summary.costBasis).toBe('estimated');
    expect(summary.modelCallCount).toBe(3);
  });

  it('grades the aggregate `measured` only when every contributing run was', () => {
    const summary = summarizeRunActivity([
      runStatus({ run_id: 'run_a', cost_micros: 500_000, cost_basis: 'measured', model_call_count: 1 }),
    ]);
    expect(summary.costBasis).toBe('measured');
  });

  it('reports `null` basis, not a fabricated one, when nothing in scope reported a cost', () => {
    const summary = summarizeRunActivity([runStatus({ run_id: 'run_a' })]);
    expect(summary.costBasis).toBeNull();
    expect(summary.runsWithReportedCost).toBe(0);
    expect(summary.reportedCostMicros).toBe(0);
  });

  it('tallies every run state, including the ones this fixture set does not use', () => {
    const summary = summarizeRunActivity([
      runStatus({ run_id: 'run_a', state: 'failed' }),
      runStatus({ run_id: 'run_b', state: 'failed' }),
      runStatus({ run_id: 'run_c', state: 'published' }),
    ]);
    expect(summary.byState.failed).toBe(2);
    expect(summary.byState.published).toBe(1);
    expect(summary.byState.cancelled).toBe(0);
  });
});
