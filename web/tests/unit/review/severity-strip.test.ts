/**
 * The severity strip of «Разбор» (`R-151j`).
 *
 * The canonical severity is the expert's decision: the strip counts `decided_severity`, a finding without one is
 * «Не определена», and the filter selects by it. The model's proposal is counted on its own labelled row and never
 * becomes an expert decision (AGENTS §4). Explicit proposed filters use their own URL values. The counts cover the whole run, as the list does; a legacy run with no severity
 * draws no strip.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { groupByCategory } from '@/entities/finding';
import { FindingList, filterBySeverity, severityFilterOf, tallySeverity } from '@/widgets/finding-list';

import { findingDetail, observation } from './fixtures';

const FINDINGS = [
  findingDetail({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA1', observation: observation({ proposed_severity: 'critical' }), decided_severity: 'economic' }),
  findingDetail({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA2', observation: observation({ proposed_severity: 'critical' }) }),
  findingDetail({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA3', observation: observation({}), decided_severity: 'critical' }),
];
const GROUPS = groupByCategory(FINDINGS);

describe('the severity strip', () => {
  it('counts the expert’s decision, and the model’s proposal apart', () => {
    const tally = tallySeverity(GROUPS);
    expect(tally.decided).toEqual({ critical: 1, economic: 1, operational: 0, recommendation: 0, check_adjacent: 0, undetermined: 1 });
    expect(tally.proposed).toEqual({ critical: 2, economic: 0, operational: 0, recommendation: 0, check_adjacent: 0 });
  });

  it('filters by the decided severity, «Не определена» included, never by the proposal', () => {
    const uids = (filter: Parameters<typeof filterBySeverity>[1]) =>
      filterBySeverity(GROUPS, filter).flatMap((group) => group.findings.map((finding) => finding.finding_uid));
    expect(uids('critical')).toEqual(['fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA3']);
    expect(uids('undetermined')).toEqual(['fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA2']);
    expect(uids('all')).toHaveLength(3);
  });

  it('reads the filter from the address, an unknown value as «Все»', () => {
    expect(severityFilterOf('critical')).toBe('critical');
    expect(severityFilterOf('undetermined')).toBe('undetermined');
    expect(severityFilterOf('proposed')).toBe('all');
    expect(severityFilterOf(null)).toBe('all');
    expect(severityFilterOf('proposed:critical')).toBe('proposed:critical');
    expect(severityFilterOf('proposed:unknown')).toBe('all');
  });

  it('offers an explicit proposal filter while keeping the decided filter independent', () => {
    const proposals = filterBySeverity(GROUPS, 'proposed:critical').flatMap((group) => group.findings);
    expect(proposals.map((finding) => finding.finding_uid)).toEqual(FINDINGS.slice(0, 2).map((finding) => finding.finding_uid));
    expect(proposals.map((finding) => finding.decided_severity)).toEqual(['economic', undefined]);
  });

  it('draws the decided row as a filter and labels the model’s row as not a decision', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {} }));
    expect(markup).toContain('data-severity-strip');
    expect(markup).toContain('data-severity-filter="undetermined"');
    expect(markup).toContain('Предложено моделью (не решение эксперта):');
  });

  it('draws no strip for a run without any severity', () => {
    const legacy = groupByCategory([findingDetail({ observation: observation({}) })]);
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: legacy, selectedFindingUid: null, onSelect: () => {} }));
    expect(markup).not.toContain('data-severity-strip');
  });
});
