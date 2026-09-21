/**
 * Ungrounded observations must never appear.
 *
 * `P02_SEAMS.md` §5.1: an item whose quotation does not resolve at its declared anchor is
 * rejected from the finding list and retained only as a diagnostic — `grounded = false`, a
 * non-null `ungrounded_reason`, and **no** `finding_uid`. It appears in no finding query
 * and in no CSV row.
 *
 * So the server does not send one. These tests are about the other half of the property:
 * that this UI has no path to display one even if it received one. That is the difference
 * between "the server currently does not send it" and "this UI cannot show it", and only
 * the second survives a fixture, a future endpoint, or a bug.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { admitFinding, admitFindings, groupByCategory, isRenderableFinding } from '@/entities/finding';
import { FindingList } from '@/widgets/finding-list';
import type { Finding } from '@/shared/api';

import { FINDING_UID, finding, observation, render } from './fixtures';

/** A diagnostic row, shaped the way §5.1 describes one, cast in past the closed type. */
function ungroundedDiagnostic(overrides: Record<string, unknown> = {}): Finding {
  return {
    ...finding(),
    finding_uid: '',
    grounded: false,
    ungrounded_reason: 'quotation_absent',
    ...overrides,
  } as unknown as Finding;
}

describe('the admission gate', () => {
  it('admits an ordinary published finding', () => {
    const admitted = admitFinding(finding());
    expect(admitted.kind).toBe('admitted');
    expect(isRenderableFinding(finding())).toBe(true);
  });

  it('refuses a diagnostic row carrying no finding_uid', () => {
    const admitted = admitFinding({ ...finding(), finding_uid: '' } as Finding);
    expect(admitted).toEqual({ kind: 'refused', refusal: 'not_a_finding' });
  });

  it('refuses anything carrying the grounding-diagnostic fields', () => {
    expect(admitFinding(ungroundedDiagnostic())).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('refuses a diagnostic even when it carries a finding_uid and grounded: true', () => {
    // The presence of the key is the signal, not its value. `Finding` is a closed schema
    // and declares neither field, so either one arriving means this payload came from the
    // diagnostic side of the grounding gate and is not a finding whatever else it says.
    const disguised = ungroundedDiagnostic({
      finding_uid: FINDING_UID,
      grounded: true,
      ungrounded_reason: null,
    });
    expect(admitFinding(disguised)).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('separates a zero-evidence finding from an ungrounded one', () => {
    // Distinct refusals on purpose. An item with no `finding_uid` is simply not a finding
    // and belongs in no list. A finding that passed the grounding gate and then arrived
    // with no evidence is impossible under the P02 evidence gate, so it is a fault to
    // report rather than a row to hide.
    const empty = finding({ observation: observation({ evidence: [] }) });
    expect(admitFinding(empty)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });
});

describe('admitting a page of findings', () => {
  it('keeps the findings, counts the refusals and reports only the integrity faults', () => {
    const good = finding();
    const empty = finding({
      finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E',
      observation: observation({ evidence: [] }),
    });

    const admitted = admitFindings([good, ungroundedDiagnostic(), empty]);

    expect(admitted.findings).toEqual([good]);
    expect(admitted.refusedCount).toBe(2);
    // The ungrounded item is not reported to the reviewer: it is not a finding, and the
    // run's `diagnostic_observation_count` is where that fact belongs.
    expect(admitted.integrityFaults).toEqual([
      { findingUid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', refusal: 'no_evidence' },
    ]);
  });
});

describe('the finding list', () => {
  it('renders no row for an ungrounded item', () => {
    const good = finding();
    const admitted = admitFindings([good, ungroundedDiagnostic()]);
    const markup = render(
      createElement(FindingList, {
        groups: groupByCategory(admitted.findings),
        selectedFindingUid: null,
        onSelect: () => {},
      }),
    );

    expect(markup).toContain(`data-finding-uid="${good.finding_uid}"`);
    expect(markup).toContain('data-finding-count="1"');
    expect(markup).not.toContain('quotation_absent');
    expect(markup).not.toContain('ungrounded');
    // One row, and it is the grounded one.
    expect(markup.match(/data-finding-uid=/g)).toHaveLength(1);
  });

  it('groups by the contract order, not the order the server returned', () => {
    const placeholder = finding({
      finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      category: 'explicit_placeholder',
      observation: observation({ category: 'explicit_placeholder' }),
    });
    const contradiction = finding();

    // Server order is placeholder-first; `FINDING_CATEGORY_VALUES` declares
    // internal_contradiction first, and that is the order a reviewer should always find.
    const groups = groupByCategory([placeholder, contradiction]);
    expect(groups.map((group) => group.category)).toEqual([
      'internal_contradiction',
      'explicit_placeholder',
    ]);

    const markup = render(
      createElement(FindingList, {
        groups,
        selectedFindingUid: null,
        onSelect: () => {},
      }),
    );
    expect(markup.indexOf('data-category="internal_contradiction"')).toBeLessThan(
      markup.indexOf('data-category="explicit_placeholder"'),
    );
  });

  it('omits a category with no findings rather than rendering an empty heading', () => {
    expect(groupByCategory([finding()]).map((group) => group.category)).toEqual([
      'internal_contradiction',
    ]);
  });

  it('reports a zero-evidence finding as a data integrity fault, not an empty pane', () => {
    const markup = render(
      createElement(FindingList, {
        groups: [],
        selectedFindingUid: null,
        onSelect: () => {},
        integrityFaults: [{ findingUid: FINDING_UID, refusal: 'no_evidence' }],
      }),
    );
    expect(markup).toContain('Нарушение целостности данных');
    expect(markup).toContain(FINDING_UID);
    expect(markup).not.toContain('Находок нет');
  });

  it('renders the empty state when the run genuinely published nothing', () => {
    const markup = render(
      createElement(FindingList, {
        groups: [],
        selectedFindingUid: null,
        onSelect: () => {},
      }),
    );
    expect(markup).toContain('Находок нет');
    expect(markup).not.toContain('Нарушение целостности данных');
  });
});
