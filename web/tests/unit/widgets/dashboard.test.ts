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

import type {
  DashboardSummary,
  RunActivity,
  RunStateCount,
  SectionDocumentCount,
  VerdictCount,
} from '@/shared/api';
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
 * an explicit `spend: undefined` a different type from an absent key, and the absent key
 * is the shape `W46-SPEND`'s reseal actually produces when nothing has called a provider,
 * so the fixture is built without the key at all.
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
    { verdict: 'pending', count: 16 },
    { verdict: 'accepted', count: 17 },
    { verdict: 'rejected', count: 18 },
    { verdict: 'needs_manual_review', count: 19 },
  ],
  run_activity: {
    by_state: ZERO_BY_STATE.map((row, index) => ({ ...row, count: 31 + index })),
    spend: { model_call_count: 9, cost_micros: 1_500_000, cost_basis: 'measured' },
  },
  section_breakdown: [
    ...PROJECT_SECTIONS.map((section, index) => ({
      section: section.code,
      document_count: index + 1,
    })),
    { document_count: PROJECT_SECTIONS.length + 1 },
  ],
};

/** `SUMMARY`, with `run_activity.spend` absent — no provider call made at all. */
const SUMMARY_NO_SPEND: DashboardSummary = {
  ...SUMMARY,
  run_activity: runActivityWithoutSpend(SUMMARY.run_activity.by_state),
};

// ============================================================================
// C1 — an omitted or unrecognised row is a fault, never a zero. Fixtures below
// mutate the DATA a response could arrive with; the code under test is unmutated.
// ============================================================================

/** `SUMMARY.section_breakdown` with one frozen code's row deleted outright. */
const SUMMARY_SECTION_MISSING: DashboardSummary = {
  ...SUMMARY,
  section_breakdown: SUMMARY.section_breakdown.filter((row) => row.section !== 'KM'),
};

/** `SUMMARY.section_breakdown` with one row's section outside the fourteen frozen codes. */
const SUMMARY_SECTION_UNKNOWN: DashboardSummary = {
  ...SUMMARY,
  section_breakdown: [
    ...SUMMARY.section_breakdown.filter((row) => row.section !== 'GP'),
    { section: 'ZZ', document_count: 5 } as unknown as SectionDocumentCount,
  ],
};

/** `SUMMARY.findings_by_verdict` with one of the four members deleted outright. */
const SUMMARY_VERDICT_MISSING: DashboardSummary = {
  ...SUMMARY,
  findings_by_verdict: SUMMARY.findings_by_verdict.filter((row) => row.verdict !== 'rejected'),
};

/** `SUMMARY.findings_by_verdict` with a verdict outside the closed set — `X2-a`'s own case. */
const SUMMARY_VERDICT_UNKNOWN: DashboardSummary = {
  ...SUMMARY,
  findings_by_verdict: [
    ...SUMMARY.findings_by_verdict.filter((row) => row.verdict !== 'needs_manual_review'),
    { verdict: 'escalated', count: 9 } as unknown as VerdictCount,
  ],
};

/**
 * `SUMMARY.run_activity` with only one of the eight `RunState` rows present — the shape
 * the coordinator's narrowing named: the old code hid the other seven behind `?? 0` and a
 * `> 0` filter rather than showing a fault, indistinguishable on screen from "the rest are
 * genuinely zero".
 */
const SUMMARY_RUN_STATE_PARTIAL: DashboardSummary = {
  ...SUMMARY,
  run_activity: {
    by_state: SUMMARY.run_activity.by_state.filter((row) => row.state === 'published'),
    ...(SUMMARY.run_activity.spend !== undefined ? { spend: SUMMARY.run_activity.spend } : {}),
  },
};

/** `SUMMARY.run_activity` with a state outside `RunState` — `X2-a`'s own case, run-side. */
const SUMMARY_RUN_STATE_UNKNOWN: DashboardSummary = {
  ...SUMMARY,
  run_activity: {
    by_state: [
      ...SUMMARY.run_activity.by_state.filter((row) => row.state !== 'cancelled'),
      { state: 'escalated', count: 5 } as unknown as RunStateCount,
    ],
    ...(SUMMARY.run_activity.spend !== undefined ? { spend: SUMMARY.run_activity.spend } : {}),
  },
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
 * The markup of one `<section aria-labelledby="…">` — sections never nest in this widget,
 * so matching up to the next `</section>` is exact even though the panel inside carries
 * its own nested `<div>`s (`ErrorState`'s wrapper among them).
 */
function sectionMarkup(markup: string, headingId: string): string {
  const match = markup.match(
    new RegExp(`<section[^>]*aria-labelledby="${headingId}"[^>]*>([\\s\\S]*?)</section>`),
  );
  if (match === null) throw new Error(`no <section aria-labelledby="${headingId}"> in the markup`);
  return match[1]!;
}

/**
 * The number keyed to one row, read from `<${tag} data-${attr}="${value}">…</${tag}>`
 * rather than from anywhere on the page — `toContain('4')` is satisfied by any panel's
 * `4`; this is not (`Y5 M5/M6`, `docs/program/reviews/W46-JUDGE-Y.md` §5). `li` and `tr`
 * are siblings in every panel here, never nested, so the non-greedy match to the next
 * closing tag of the same name stops at this row's own close.
 */
function rowNumber(markup: string, tag: 'li' | 'tr', attr: string, value: string): number {
  const match = markup.match(
    new RegExp(`<${tag}[^>]*data-${attr}="${value}"[^>]*>([\\s\\S]*?)</${tag}>`),
  );
  if (match === null) throw new Error(`no <${tag} data-${attr}="${value}"> row in the markup`);
  const numberMatch = match[1]!.match(/<(?:strong|td)>(\d+)<\/(?:strong|td)>/);
  if (numberMatch === null) {
    throw new Error(`row data-${attr}="${value}" carries no number: ${match[1]}`);
  }
  return Number(numberMatch[1]);
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
    expect(text).toContain('Находок: 70');
  });

  it('renders the run count and the reported spend, with its cost basis', () => {
    const markup = render(SUMMARY);
    const text = visible(markup);
    expect(text).toContain('Прогонов: 276');
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
    expect(visible(markup)).toContain('Без раздела: 15');
    // The mutation this catches, run by hand and confirmed red: deleting the
    // `<li data-section="unclassified">` block from `sections-panel.tsx` drops both
    // assertions above — the count moves nowhere, it simply stops being on screen, which
    // is exactly `F-3b`'s warning: fourteen true zeros with this row hidden read as "no
    // documents" even when the deployment holds plenty, all of them unclassified.
    expect(markup).toContain('data-section="KM"');
    expect(rowNumber(markup, 'li', 'section', 'KM')).toBe(3);
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

/**
 * `C1` (`X-3`, `Y5-a`, `X2-a`): a response that omits a member of a closed vocabulary, or
 * carries one the vocabulary does not have, is broken — the panel says so and renders no
 * numbers, rather than filling the gap with a zero nobody computed. Each case here mutates
 * the FIXTURE data a response could arrive with; `section-breakdown.ts`,
 * `verdict-breakdown.ts` and `run-state-breakdown.ts` are unmutated.
 *
 * Before this guard existed, every one of these six fixtures rendered a full table of
 * zeros and true counts mixed together, indistinguishable from an honest answer — that
 * was run by hand against the pre-repair panels and confirmed red for exactly this reason,
 * then reverted; see `docs/program/W46-CLIENT.md`.
 */
describe('an omitted or unrecognised row is a fault, never a zero', () => {
  it('sections panel: a missing frozen code shows the fault, not fourteen numbers', () => {
    const panel = sectionMarkup(render(SUMMARY_SECTION_MISSING), 'dashboard-sections-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });

  it('sections panel: a code outside the fourteen shows the fault, not a silently dropped row', () => {
    const panel = sectionMarkup(render(SUMMARY_SECTION_UNKNOWN), 'dashboard-sections-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });

  it('verdicts panel: a missing verdict shows the fault, not four numbers with a gap', () => {
    const panel = sectionMarkup(render(SUMMARY_VERDICT_MISSING), 'dashboard-verdicts-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });

  it('verdicts panel: a verdict outside the closed set shows the fault, not a silently dropped row', () => {
    const panel = sectionMarkup(render(SUMMARY_VERDICT_UNKNOWN), 'dashboard-verdicts-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });

  it('run-state panel: a partial by_state shows the fault, not the states it happened to carry', () => {
    // The coordinator's narrowing: the pre-repair panel hid the seven missing states
    // behind `?? 0` fed into a `> 0` filter and rendered `published: 2` alone, with no
    // sign that seven members were never said at all.
    const panel = sectionMarkup(render(SUMMARY_RUN_STATE_PARTIAL), 'dashboard-runs-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });

  it('run-state panel: a state outside RunState shows the fault, not a silently dropped row', () => {
    const panel = sectionMarkup(render(SUMMARY_RUN_STATE_UNKNOWN), 'dashboard-runs-heading');
    expect(panel).toContain('data-panel-fault="incomplete"');
    expect(renderedNumberTokens(panel)).toEqual([]);
  });
});

/**
 * `C2` (`Y5 M5/M6`): the render guard above proves no number is invented; it does not by
 * itself prove any number is in its own row. `toContain('4')` anywhere on the page is
 * satisfied by any panel's `4` — these cases key each assertion to the row's own
 * `data-section`/`data-verdict`/`data-run-state` attribute instead.
 *
 * Two of Y's mutations, plus one of mine, were run by hand against these cases and
 * confirmed red, then reverted — recorded with their output in
 * `docs/program/W46-CLIENT.md`:
 *
 *   1. Y's M5 — `sections-panel.tsx` reading `PROJECT_SECTIONS[(i + 1) % length]`'s code
 *      for row `i`'s count (every section shows its neighbour's).
 *   2. Y's M6 — `verdicts-panel.tsx` rendering `accepted`'s cell from `rejected`'s count
 *      and back.
 *   3. Mine — `run-activity-panel.tsx` rendering `published`'s cell from `failed`'s count
 *      and back.
 */
describe('every row is keyed to its own data attribute, not to membership on the page', () => {
  it('uses pairwise-distinct values in every closed breakdown fixture', () => {
    const sectionCounts = SUMMARY.section_breakdown.map((row) => row.document_count);
    const verdictCounts = SUMMARY.findings_by_verdict.map((row) => row.count);
    const runCounts = SUMMARY.run_activity.by_state.map((row) => row.count);
    expect(new Set(sectionCounts).size).toBe(sectionCounts.length);
    expect(new Set(verdictCounts).size).toBe(verdictCounts.length);
    expect(new Set(runCounts).size).toBe(runCounts.length);
  });

  it('every section row carries its own section’s count, never a neighbour’s', () => {
    const markup = render(SUMMARY);
    for (const row of SUMMARY.section_breakdown) {
      if (row.section === undefined) continue;
      expect(rowNumber(markup, 'li', 'section', row.section), row.section).toBe(
        row.document_count,
      );
    }
  });

  it('every verdict row carries its own verdict’s count, never a swapped one', () => {
    const markup = render(SUMMARY);
    for (const row of SUMMARY.findings_by_verdict) {
      expect(rowNumber(markup, 'tr', 'verdict', row.verdict), row.verdict).toBe(row.count);
    }
  });

  it('every rendered run-state row carries its own state’s count, never a swapped one', () => {
    const markup = render(SUMMARY);
    for (const row of SUMMARY.run_activity.by_state) {
      if (row.count === 0) continue; // filtered off the table; not this case's subject
      expect(rowNumber(markup, 'tr', 'run-state', row.state), row.state).toBe(row.count);
    }
  });
});
