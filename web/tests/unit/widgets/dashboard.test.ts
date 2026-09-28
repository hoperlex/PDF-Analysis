/**
 * The dashboard, rendered from ONE fixture `DashboardSummary` — `W46-WIRE`, `F-5b`.
 *
 * The judge (`docs/program/reviews/W46-JUDGE-A.md` §5) appended `': 0'` to every section
 * row on the merged tree and the whole frontend suite stayed green: `dashboard.test.ts`
 * guarded three client-side aggregators, and none of its cases rendered a panel or
 * asserted the absence of an invented number. Those three aggregators are gone — the
 * aggregate now computes everything server-side — and this file replaces them with a
 * render test over the widget itself: seed one `DashboardSummary` fixture, render
 * `Dashboard`, and check two things together, the way `R-23`'s addendum states the rule:
 * **every number on screen is the fixture's own, and nothing on screen is a number the
 * fixture did not send.**
 *
 * `expectedNumberTokens` derives the second half — the closed set a correct render may
 * use — straight from the fixture object, with the same arithmetic the panels do (a sum,
 * `formatCostMicros`), rather than a second hand-copied list that could quietly drift from
 * the fixture. `renderedNumberTokens` reads the rendered markup's visible text the same
 * way `stage-comparison.test.ts`'s own `visible()` does — tags stripped, so `data-*`
 * attributes (a project's uid, `data-section-count`) never count as a rendered number.
 *
 * Three mutations were run by hand against this test and confirmed red, then reverted —
 * `AGENTS.md` §5's "every new guard is shown failing under a quoted mutation":
 *
 *   1. a fabricated number appended to `verdicts-panel.tsx`'s total (`+ ' (42)'`) —
 *      caught by `renders exactly the fixture's numbers, nothing invented`:
 *      `rendered numbers not in the fixture: 42`.
 *   2. the unclassified `<li>` deleted from `sections-panel.tsx` — caught by
 *      `always shows the unclassified section row, never folded into the fourteen`:
 *      both the `data-section="unclassified"` assertion and the digit assertion failed.
 *   3. `run-activity-panel.tsx`'s absent-spend branch replaced with
 *      `spend?.cost_micros ?? 0` / `spend?.cost_basis ?? 'measured'` — caught by
 *      `never renders absent spend as 0 labelled measured`: the honest sentence was gone
 *      and `data-cost-basis="measured"` appeared over a deployment that made no call.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DashboardSummary, RunActivity, RunStateCount } from '@/shared/api';
import { RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { formatCostMicros } from '@/entities/audit-run';
import { PROJECT_SECTIONS } from '@/entities/project';
import { Dashboard } from '@/widgets/dashboard';

import { newClient, renderWith } from '../screens/harness';

const ULID_A = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const ULID_B = '01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

/** Every `RunState`, at zero, the base a fixture's `by_state` starts from. */
const ZERO_BY_STATE: readonly RunStateCount[] = RUN_STATE_VALUES.map((state) => ({
  state,
  count: 0,
}));

/**
 * `run_activity` with `spend` REMOVED rather than typed away — the same move
 * `rendered-language.guard.test.ts`'s own `runActivityWithoutSpend` makes, for the same
 * reason `without()` there removes `RunStatus` fields: `exactOptionalPropertyTypes` makes
 * an explicit `spend: undefined` a different type from an absent key, and today's
 * generated client still types `spend` required, so the only way to seed the shape
 * `W46-SPEND`'s reseal produces is to build the object without the key and cast.
 */
function runActivityWithoutSpend(byState: readonly RunStateCount[]): RunActivity {
  return { by_state: byState } as unknown as RunActivity;
}

/**
 * A fixture rich enough to reach every non-empty branch of all four panels at once, with
 * numbers chosen to be individually recognisable rather than a repeated round figure.
 */
const SUMMARY: DashboardSummary = {
  documents_by_project: [
    { project_uid: `prj_${ULID_A}`, name: 'Проект Альфа', document_count: 3 },
    { project_uid: `prj_${ULID_B}`, name: 'Проект Бета', document_count: 5 },
  ],
  findings_by_verdict: [
    { verdict: 'pending', count: 4 },
    { verdict: 'accepted', count: 2 },
    { verdict: 'rejected', count: 1 },
    { verdict: 'needs_manual_review', count: 0 },
  ],
  run_activity: {
    by_state: ZERO_BY_STATE.map((row) =>
      row.state === 'published' ? { ...row, count: 6 } : row.state === 'failed' ? { ...row, count: 1 } : row,
    ),
    spend: { model_call_count: 9, cost_micros: 1_500_000, cost_basis: 'measured' },
  },
  section_breakdown: [
    ...PROJECT_SECTIONS.map((section) => ({
      section: section.code,
      document_count: section.code === 'KM' ? 4 : section.code === 'PB' ? 2 : 0,
    })),
    { document_count: 11 },
  ],
};

/** `SUMMARY`, with `run_activity.spend` absent — no provider call made at all. */
const SUMMARY_NO_SPEND: DashboardSummary = {
  ...SUMMARY,
  run_activity: runActivityWithoutSpend(SUMMARY.run_activity.by_state),
};

function render(summary: DashboardSummary): string {
  const client = newClient();
  client.setQueryData(queryKeys.dashboard.summary(), summary);
  return renderWith(client, createElement(Dashboard));
}

/** The text a browser would show: tags stripped, so no `data-*` attribute counts. */
function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

/** Every whole or decimal digit token in a rendered screen's visible text. */
function renderedNumberTokens(markup: string): string[] {
  return [...visible(markup).matchAll(/\d+(?:\.\d+)?/g)].map((match) => match[0]);
}

/**
 * The closed set of numbers a correct render of `summary` may show, computed with the
 * same arithmetic the panels use rather than copied out by hand.
 */
function expectedNumberTokens(summary: DashboardSummary): ReadonlySet<string> {
  const tokens = new Set<string>();
  const add = (n: number): void => void tokens.add(String(n));

  add(summary.documents_by_project.reduce((sum, row) => sum + row.document_count, 0));
  add(summary.documents_by_project.length);
  for (const row of summary.documents_by_project) add(row.document_count);

  add(summary.findings_by_verdict.reduce((sum, row) => sum + row.count, 0));
  for (const row of summary.findings_by_verdict) add(row.count);

  add(summary.run_activity.by_state.reduce((sum, row) => sum + row.count, 0));
  for (const row of summary.run_activity.by_state) add(row.count);
  if (summary.run_activity.spend !== undefined) {
    tokens.add(formatCostMicros(summary.run_activity.spend.cost_micros));
    add(summary.run_activity.spend.model_call_count);
  }

  for (const row of summary.section_breakdown) add(row.document_count);

  return tokens;
}

describe('every number the dashboard renders is the fixture, and nothing else is a number', () => {
  it('renders exactly the fixture’s numbers, nothing invented', () => {
    const markup = render(SUMMARY);
    const expected = expectedNumberTokens(SUMMARY);
    const rendered = renderedNumberTokens(markup);
    const invented = rendered.filter((token) => !expected.has(token));
    expect(invented, `rendered numbers not in the fixture: ${invented.join(', ')}`).toEqual([]);
  });

  it('renders every project’s document count and the total across them', () => {
    const text = visible(render(SUMMARY));
    expect(text).toContain('Документов: 8');
    expect(text).toContain('документов 3');
    expect(text).toContain('документов 5');
  });

  it('renders all four verdict rows, including needs_manual_review at zero', () => {
    const markup = render(SUMMARY);
    expect(markup).toContain('data-verdict="pending"');
    expect(markup).toContain('data-verdict="accepted"');
    expect(markup).toContain('data-verdict="rejected"');
    expect(markup).toContain('data-verdict="needs_manual_review"');
    const text = visible(markup);
    expect(text).toContain('Находок: 7');
  });

  it('renders the run count and the reported spend, with its cost basis', () => {
    const markup = render(SUMMARY);
    const text = visible(markup);
    expect(text).toContain('Прогонов: 7');
    expect(text).toContain(formatCostMicros(1_500_000));
    expect(text).toContain('вызовов модели: 9');
    expect(markup).toContain('data-cost-basis="measured"');
  });

  it('never renders absent spend as 0 labelled measured', () => {
    const markup = render(SUMMARY_NO_SPEND);
    const text = visible(markup);
    expect(text).toContain('Ни один прогон ещё не обращался к провайдеру');
    expect(markup).not.toContain('data-cost-basis=');
    // The mutation this catches, run by hand and confirmed red: replacing the
    // `spend !== undefined` branch in `run-activity-panel.tsx` with
    // `spend?.cost_micros ?? 0` / `spend?.cost_basis ?? 'measured'` renders
    // `data-cost-basis="measured"` and drops the sentence above, over a deployment that
    // made no provider call at all.
    const invented = renderedNumberTokens(markup).filter(
      (token) => !expectedNumberTokens(SUMMARY_NO_SPEND).has(token),
    );
    expect(invented).toEqual([]);
  });

  it('always shows the unclassified section row, never folded into the fourteen', () => {
    const markup = render(SUMMARY);
    expect(markup).toContain('data-section="unclassified"');
    expect(visible(markup)).toContain('Без раздела: 11');
    // The mutation this catches, run by hand and confirmed red: deleting the
    // `<li data-section="unclassified">` block from `sections-panel.tsx` drops both
    // assertions above — the count moves nowhere, it simply stops being on screen, which
    // is exactly `F-3b`'s warning: fourteen true zeros with this row hidden read as "no
    // documents" even when the deployment holds plenty, all of them unclassified.
    expect(markup).toContain('data-section="KM"');
    expect(visible(markup)).toContain('4');
  });

  it('renders every one of the fourteen frozen sections, zeros included', () => {
    const markup = render(SUMMARY);
    for (const section of PROJECT_SECTIONS) {
      expect(markup, `missing data-section="${section.code}"`).toContain(
        `data-section="${section.code}"`,
      );
    }
  });
});
