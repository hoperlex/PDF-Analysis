/**
 * The severity plates of «Разбор» (`R-151j`, `UIP-S06-06`).
 *
 * A plate counts and selects a finding by the severity the expert decided and, for a finding nobody has decided, by the one the
 * model proposed. The plate's tooltip splits its number into «решено экспертом» and «предложено моделью», and the two fields stay
 * apart in the data: counting them under one plate never turns a proposal into a decision (AGENTS §4). A finding with neither is
 * «Не определена», whose plate is drawn only while there is one. A press selects the severity and a second press lifts it. The
 * counts cover the whole run, as the list does; a legacy run with no severity draws no plates.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it } from 'vitest';

import { groupByCategory } from '@/entities/finding';
import {
  FindingList, FindingToolbar, filterBySeverity, plateOf, plateTotal, severityFilterOf, severityPlates, tallySeverity,
} from '@/widgets/finding-list';
import type { SeverityFilter } from '@/widgets/finding-list';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { findingDetail, observation } from './fixtures';

const A1 = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA1';
const A2 = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA2';
const A3 = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA3';
const A4 = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA4';
const A5 = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA5';

const FINDINGS = [
  // Decided «Экономическое» over a proposed «Критическое»: the decision is the severity, the proposal stays on the observation.
  findingDetail({ finding_uid: A1, observation: observation({ proposed_severity: 'critical' }), decided_severity: 'economic' }),
  // Only proposed.
  findingDetail({ finding_uid: A2, observation: observation({ proposed_severity: 'critical' }) }),
  // Decided, never proposed.
  findingDetail({ finding_uid: A3, observation: observation({}), decided_severity: 'critical' }),
  // Neither.
  findingDetail({ finding_uid: A4, observation: observation({}) }),
  findingDetail({ finding_uid: A5, observation: observation({ proposed_severity: 'operational' }) }),
];
const GROUPS = groupByCategory(FINDINGS);

const toolbar = (over: Partial<Parameters<typeof FindingToolbar>[0]> = {}, groups = GROUPS) => createElement(FindingToolbar, {
  groups, verdictFilter: 'all', onVerdictFilterChange: () => {}, severityFilter: 'all', onSeverityFilterChange: () => {},
  view: 'table', onViewChange: () => {}, ...over,
});

/** The opening tag of a plate and its text, as the markup draws them. */
function plate(markup: string, value: string): { readonly tag: string; readonly text: string } {
  const found = new RegExp(`(<button[^>]*data-severity-filter="${value}"[^>]*>)(.*?)</button>`).exec(markup);
  if (found === null) throw new Error(`no plate «${value}» in ${markup}`);
  return { tag: found[1] as string, text: (found[2] as string).replace(/<[^>]*>/g, '') };
}

const uids = (filter: SeverityFilter) => filterBySeverity(GROUPS, filter).flatMap((group) => group.findings.map((f) => f.finding_uid));

let live: LiveRender | null = null;
afterEach(async () => {
  await live?.unmount();
  live = null;
});

describe('what a plate counts', () => {
  it('puts a finding under the severity the expert decided, else the one the model proposed, else «Не определена»', () => {
    expect(FINDINGS.map(plateOf)).toEqual(['economic', 'critical', 'critical', 'undetermined', 'operational']);
  });

  it('counts the decided and the proposed apart under each plate, and each finding once', () => {
    const plates = severityPlates(GROUPS);
    expect(plates.bySeverity).toEqual({
      critical: { decided: 1, proposed: 1 },
      economic: { decided: 1, proposed: 0 },
      operational: { decided: 0, proposed: 1 },
      recommendation: { decided: 0, proposed: 0 },
      check_adjacent: { decided: 0, proposed: 0 },
    });
    expect(plates.undetermined).toBe(1);
    const sum = (Object.values(plates.bySeverity) as { decided: number; proposed: number }[]).reduce((all, count) => all + plateTotal(count), 0);
    expect(sum + plates.undetermined).toBe(FINDINGS.length);
  });

  it('keeps the run page’s tile as it was: the tally still reads only the decision, and the proposal on its own', () => {
    const tally = tallySeverity(GROUPS);
    expect(tally.decided).toEqual({ critical: 1, economic: 1, operational: 0, recommendation: 0, check_adjacent: 0, undetermined: 3 });
    expect(tally.proposed).toEqual({ critical: 2, economic: 0, operational: 1, recommendation: 0, check_adjacent: 0 });
  });

  it('does not write the proposal into the finding: the two fields are the ones the server sent', () => {
    for (const group of GROUPS) {
      for (const finding of group.findings) {
        const source = FINDINGS.find((one) => one.finding_uid === finding.finding_uid);
        expect(finding.decided_severity).toBe(source?.decided_severity);
        expect(finding.observation.proposed_severity).toBe(source?.observation.proposed_severity);
      }
    }
    expect(FINDINGS[1]?.decided_severity).toBeUndefined();
  });
});

describe('what a plate selects', () => {
  it('selects by the same severity it counts: a proposal is found under its plate, a decision over a proposal', () => {
    expect(uids('critical')).toEqual([A2, A3]);
    expect(uids('economic')).toEqual([A1]);
    expect(uids('operational')).toEqual([A5]);
    expect(uids('recommendation')).toEqual([]);
    expect(uids('undetermined')).toEqual([A4]);
    expect(uids('all')).toHaveLength(FINDINGS.length);
  });

  it('selects exactly as many findings as the plate says', () => {
    const plates = severityPlates(GROUPS);
    for (const value of ['critical', 'economic', 'operational'] as const) {
      expect(uids(value)).toHaveLength(plateTotal(plates.bySeverity[value]));
    }
  });

  it('reads the filter from the address, an unknown value as «Все», and an address of the proposals’ own plates as the plate it names', () => {
    expect(severityFilterOf('critical')).toBe('critical');
    expect(severityFilterOf('undetermined')).toBe('undetermined');
    expect(severityFilterOf(null)).toBe('all');
    expect(severityFilterOf('')).toBe('all');
    expect(severityFilterOf('proposed')).toBe('all');
    expect(severityFilterOf('urgent')).toBe('all');
    expect(severityFilterOf('proposed:critical')).toBe('critical');
    expect(severityFilterOf('proposed:check_adjacent')).toBe('check_adjacent');
    expect(severityFilterOf('proposed:unknown')).toBe('all');
    expect(severityFilterOf('proposed:undetermined')).toBe('all');
  });
});

describe('the plates drawn', () => {
  const markup = renderToStaticMarkup(toolbar());

  it('draws five plates with their numbers, and «Не определена» because one finding has none', () => {
    expect(markup).toContain('data-severity-strip');
    expect(plate(markup, 'critical').text).toBe('Критическое 2');
    expect(plate(markup, 'economic').text).toBe('Экономическое 1');
    expect(plate(markup, 'operational').text).toBe('Эксплуатационное 1');
    expect(plate(markup, 'recommendation').text).toBe('Рекомендация 0');
    expect(plate(markup, 'check_adjacent').text).toBe('Проверить смежный раздел 0');
    expect(plate(markup, 'undetermined').text).toBe('Не определена 1');
    expect((markup.match(/data-severity-filter=/g) ?? []).length).toBe(6);
  });

  it('says in the tooltip how many of the number the expert decided and how many only the model proposed', () => {
    expect(plate(markup, 'critical').tag).toContain('title="решено экспертом: 1 · предложено моделью: 1"');
    expect(plate(markup, 'economic').tag).toContain('title="решено экспертом: 1 · предложено моделью: 0"');
    expect(plate(markup, 'operational').tag).toContain('title="решено экспертом: 0 · предложено моделью: 1"');
  });

  it('wears the tone of the severity, five apart, and the neutral one for «Не определена»', () => {
    expect(plate(markup, 'critical').tag).toContain('am-badge--failed');
    expect(plate(markup, 'economic').tag).toContain('am-badge--degraded');
    expect(plate(markup, 'operational').tag).toContain('am-badge--active');
    expect(plate(markup, 'recommendation').tag).toContain('am-badge--ok');
    expect(plate(markup, 'check_adjacent').tag).toContain('am-badge--inert');
    expect(plate(markup, 'undetermined').tag).toContain('am-badge--inert');
  });

  it('has no row of the model’s own, no «Все» plate and no proposal marker: the proposal is a count under the same plate', () => {
    expect(markup).not.toContain('Предложено моделью (не решение эксперта)');
    expect(markup).not.toContain('data-proposed-severity');
    expect(markup).not.toContain('data-severity-filter="all"');
    expect(markup).not.toContain('data-severity-filter="proposed:');
  });

  it('hides «Не определена» while no finding is without a severity', () => {
    const decidedOnly = groupByCategory(FINDINGS.filter((finding) => finding.finding_uid !== A4));
    const bare = renderToStaticMarkup(toolbar({}, decidedOnly));
    expect(bare).toContain('data-severity-strip');
    expect(bare).not.toContain('data-severity-filter="undetermined"');
    expect(bare).not.toContain('Не определена');
    expect((bare.match(/data-severity-filter=/g) ?? []).length).toBe(5);
  });

  it('marks the pressed plate and no other', () => {
    const pressed = renderToStaticMarkup(toolbar({ severityFilter: 'economic' }));
    expect(plate(pressed, 'economic').tag).toContain('aria-pressed="true"');
    for (const other of ['critical', 'operational', 'recommendation', 'check_adjacent', 'undetermined']) {
      expect(plate(pressed, other).tag).toContain('aria-pressed="false"');
    }
    expect(plate(markup, 'economic').tag).toContain('aria-pressed="false"');
  });

  it('stands in the first row, before the totals, and the totals before the choice «Показывать»', () => {
    const at = (needle: string) => markup.indexOf(needle);
    expect(at('data-severity-strip')).toBeGreaterThan(-1);
    expect(at('data-severity-strip')).toBeLessThan(at('data-finding-total'));
    expect(at('data-finding-total')).toBeLessThan(at('data-verdict-filter'));
  });

  it('draws no plates for a run without any severity, and still its totals', () => {
    const legacy = groupByCategory([findingDetail({ observation: observation({}) })]);
    const bare = renderToStaticMarkup(createElement(FindingList, { groups: legacy, selectedFindingUid: null, onSelect: () => {} }));
    expect(bare).not.toContain('data-severity-strip');
    expect(bare).not.toContain('data-severity-filter');
    expect(bare).toContain('Всего: 1');
  });
});

describe('a press on a plate', () => {
  async function mount(severityFilter: SeverityFilter): Promise<SeverityFilter[]> {
    const calls: SeverityFilter[] = [];
    live = await mountLive(toolbar({ severityFilter, onSeverityFilterChange: (next: SeverityFilter) => { calls.push(next); } }));
    return calls;
  }

  it('selects the severity', async () => {
    const calls = await mount('all');
    expect(await (live as LiveRender).pressMarked('data-severity-filter', 'critical')).toBe(true);
    expect(calls).toEqual(['critical']);
  });

  it('lifts it on a second press of the same plate, and moves it to another plate on a press of that', async () => {
    const calls = await mount('critical');
    await (live as LiveRender).pressMarked('data-severity-filter', 'critical');
    await (live as LiveRender).pressMarked('data-severity-filter', 'economic');
    await (live as LiveRender).pressMarked('data-severity-filter', 'undetermined');
    expect(calls).toEqual(['all', 'economic', 'undetermined']);
  });
});
