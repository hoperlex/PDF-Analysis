/**
 * `UI-A-35`: a section row carries the original's five numbers, read from the server's `audit_counts`.
 * «Нет решений эксперта» is `no_expert_decision`; absent counts stay absent.
 */
import { describe, expect, it } from 'vitest';

import type { SectionDocumentCount } from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { summarizeSectionBreakdown } from '@/widgets/dashboard/model/section-breakdown';

import { auditCounts } from './audit-counts';

function rows(withCounts: boolean): SectionDocumentCount[] {
  const sectioned = PROJECT_SECTIONS.map((section, i) => ({
    section: section.code,
    document_count: i,
    finding_count: i * 2,
    ...(withCounts ? { audit_counts: auditCounts(i, { not_run: 1, awaiting_decision: 2, checked: 3, no_expert_decision: 3 }) } : {}),
  })) as unknown as SectionDocumentCount[];
  return [...sectioned, { document_count: 4, finding_count: 0, ...(withCounts ? { audit_counts: auditCounts(4) } : {}) } as unknown as SectionDocumentCount];
}

describe('the five numbers of a section row', () => {
  it('reads not run, no expert decision, checked and findings from the server', () => {
    const result = summarizeSectionBreakdown(rows(true));
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const first = PROJECT_SECTIONS[1]!.code;
    expect(result.summary.auditByCode[first]).toEqual({ notRun: 1, noExpertDecision: 3, checked: 3, findings: 2 });
  });

  it('shows no number where the server sent no counts', () => {
    const result = summarizeSectionBreakdown(rows(false));
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.summary.auditByCode[PROJECT_SECTIONS[0]!.code]).toBeUndefined();
  });
});

describe('the total row (UI-A-36)', () => {
  it('is the column sums of the fifteen section rows, and leaves the unclassified row out', () => {
    const result = summarizeSectionBreakdown(rows(true));
    if (!result.ok) throw new Error('the fixture is a whole breakdown');
    const count = PROJECT_SECTIONS.length;
    const indexes = Array.from({ length: count }, (_, i) => i);
    const sum = (read: (i: number) => number): number => indexes.reduce((acc, i) => acc + read(i), 0);
    expect(result.summary.totals).toEqual({
      documents: sum((i) => i),
      audit: { notRun: count, noExpertDecision: 3 * count, checked: 3 * count, findings: sum((i) => i * 2) },
    });
    // The unclassified row's own four documents are not in it.
    expect(result.summary.unclassifiedCount).toBe(4);
  });

  it('has no audit sums where the server sent no counts, and still sums the documents', () => {
    const result = summarizeSectionBreakdown(rows(false));
    if (!result.ok) throw new Error('the fixture is a whole breakdown');
    expect(result.summary.totals.audit).toBeUndefined();
    expect(result.summary.totals.documents).toBe(PROJECT_SECTIONS.reduce((acc, _, i) => acc + i, 0));
  });

  it('has no audit sums where one row lacks them: a missing row is not a smaller sum', () => {
    const all = rows(true);
    const lacking = all.map((row, i) => (i === 3 ? ({ ...row, audit_counts: undefined } as unknown as SectionDocumentCount) : row));
    const result = summarizeSectionBreakdown(lacking);
    if (!result.ok) throw new Error('the fixture is a whole breakdown');
    expect(result.summary.totals.audit).toBeUndefined();
  });
});
