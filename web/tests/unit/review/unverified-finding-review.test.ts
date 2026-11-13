import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { Finding } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ReviewPage } from '@/_pages/review';
import { admitFinding, groupByCategory, unverifiedReason } from '@/entities/finding';
import { FindingList, filterGroups, pagesParts, verdictFilterOf } from '@/widgets/finding-list';
import { FindingBasis } from '@/widgets/evidence-viewer/ui/finding-basis';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, RUN_ID, finding, findingDetail, observation, render, runStatus } from './fixtures';

function unverified(): Finding {
  return finding({ observation: observation({ evidence: [], grounding_kind: 'unverified', unverified_reason: 'source_binding_unverified' }) });
}

describe('human review of a meaningful issue with incomplete evidence', () => {
  it('admits the explicit variant with a reason, and keeps diagnostic and legacy evidence guards', () => {
    const item = unverified();
    expect(admitFinding(item)).toEqual({ kind: 'admitted', finding: item });
    expect(admitFinding({ ...item, finding_uid: '' })).toEqual({ kind: 'refused', refusal: 'not_a_finding' });
    expect(admitFinding({ ...item, grounded: false } as unknown as Finding)).toEqual({ kind: 'refused', refusal: 'ungrounded_diagnostic' });
    expect(admitFinding(finding({ observation: observation({ evidence: [] }) }))).toEqual({ kind: 'refused', refusal: 'no_evidence' });
    expect(admitFinding(finding({ observation: observation({ evidence: [], grounding_kind: 'unverified', unverified_reason: '' }) })))
      .toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });

  it('shows its limitation and an honest page label in both table and list', () => {
    for (const view of ['list', 'table'] as const) {
      const markup = render(createElement(FindingList, { groups: groupByCategory([unverified()]), view, selectedFindingUid: null, onSelect: () => {} }));
      expect(markup).toContain('data-evidence-limitation="unverified"');
      expect(markup).toContain('Страница не подтверждена');
      expect(markup).not.toContain('стр. 1');
    }
    expect(pagesParts([])).toEqual({ sheet: null, pages: 'Страница не подтверждена' });
  });

  it('keeps the limitation of a merged unverified member beside a grounded canonical member', () => {
    const uncertain = unverified().observation;
    const mixed = finding({ merged_observations: [uncertain] });
    expect(unverifiedReason(mixed)).toBe('source_binding_unverified');
    const markup = render(createElement(FindingList, { groups: groupByCategory([mixed]), view: 'table', selectedFindingUid: null, onSelect: () => {} }));
    expect(markup).toContain('data-evidence-limitation="unverified"');
    const basis = render(createElement(FindingBasis, { observation: mixed.observation, mergedObservations: [uncertain] }));
    expect(basis).toContain('data-evidence-limitation="unverified"');
    expect(admitFinding(finding({ observation: observation({ evidence: [], grounding_kind: 'unverified', unverified_reason: '' }), merged_observations: [uncertain] })))
      .toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });

  it('opens the real decision panel without inventing a quotation viewer or PDF page', () => {
    const item = unverified();
    const client = newClient();
    const page = { next_cursor: null };
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: [item], page } });
    client.setQueryData(queryKeys.findings.detail(item.finding_uid), { data: findingDetail({ ...item }) });
    client.setQueryData(queryKeys.findings.decisions(item.finding_uid), { data: { items: [], page } });
    const markup = renderWith(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
    expect(markup).toContain('data-unverified-review');
    expect(markup).toContain('data-no-evidence-page');
    expect(markup).toContain('data-intent="accept"');
    expect(markup).toContain('data-intent="reject"');
    expect(markup).not.toContain('data-evidence-quote');
    expect(markup).not.toContain('data-block-evidence');
    expect(markup).toContain('data-export-scope="active"');
  });

  it('keeps uncertain issues active and retains rejected human decisions in explicit history', () => {
    const item = unverified();
    const rejected = { ...item, finding_uid: 'rejected', current_verdict: 'rejected' as const };
    const groups = groupByCategory([item, rejected]);
    expect(verdictFilterOf(null)).toBe('active');
    expect(filterGroups(groups, 'active').flatMap((group) => group.findings)).toEqual([item]);
    expect(filterGroups(groups, 'all').flatMap((group) => group.findings)).toEqual([item, rejected]);
    const active = render(createElement(FindingList, { groups, selectedFindingUid: null, onSelect: () => {} }));
    expect(active).toContain('data-finding-visible-count="1"');
    expect(active).not.toContain('data-finding-uid="rejected"');
    const history = render(createElement(FindingList, { groups, verdictFilter: 'all', selectedFindingUid: null, onSelect: () => {} }));
    expect(history).toContain('data-finding-uid="rejected"');
    const restored = groupByCategory([item, { ...rejected, current_verdict: 'accepted' }]);
    expect(filterGroups(restored, 'active').flatMap((group) => group.findings)).toHaveLength(2);
  });
});
