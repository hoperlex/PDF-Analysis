/**
 * `UI-A-35`: a section row carries the original's five numbers, read from the server's `audit_counts`.
 * «Нет решений эксперта» is `no_expert_decision`; absent counts stay absent.
 */
import { describe, expect, it } from 'vitest';

import type { SectionDocumentCount } from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import {
  SECTION_METRIC_COLUMNS,
  SECTION_NAME_COLUMN,
  SECTION_TOTAL_LABEL,
  SECTION_UNCLASSIFIED_HINT,
  summarizeSectionBreakdown,
} from '@/widgets/dashboard/model/section-breakdown';

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

describe('the words of the header and their definitions (UIP-S01-02)', () => {
  const columns = [SECTION_NAME_COLUMN, ...Object.values(SECTION_METRIC_COLUMNS)];

  it('are the original\'s, in its order, with «Итого» for the total row', () => {
    expect(columns.map((column) => column.label)).toEqual([
      'Раздел',
      'Не запускались на проверку',
      'Нет решений эксперта',
      'Проверено экспертом',
      'Всего',
      'Замечаний',
    ]);
    expect(SECTION_TOTAL_LABEL).toBe('Итого');
  });

  it('define each count of documents as «документов, у которых …», in the words of the metrics dictionary, with no digit', () => {
    const counts = [
      SECTION_METRIC_COLUMNS.notRun,
      SECTION_METRIC_COLUMNS.noExpertDecision,
      SECTION_METRIC_COLUMNS.checked,
      SECTION_METRIC_COLUMNS.total,
    ];
    for (const column of counts) expect(column.definition, column.key).toMatch(/^Документов, у которых /u);
    for (const column of [...columns]) expect(column.definition, column.key).not.toMatch(/\d/u);
    expect(SECTION_UNCLASSIFIED_HINT).not.toMatch(/\d/u);
    // The dictionary's terms: the current version, the result of a check, the expert's decision (`UI-PARITY-METRICS.md` §1–§3).
    expect(SECTION_METRIC_COLUMNS.notRun.definition).toContain('на текущей версии нет результата проверки');
    expect(SECTION_METRIC_COLUMNS.noExpertDecision.definition).toContain('остались замечания');
    expect(SECTION_METRIC_COLUMNS.checked.definition).toContain('принял решение по каждому');
  });

  it('give no two headings the same definition, and no heading an empty one', () => {
    const definitions = columns.map((column) => column.definition);
    expect(new Set(definitions).size).toBe(definitions.length);
    for (const definition of definitions) expect(definition.trim().length).toBeGreaterThan(20);
  });

  it('keep the sentence the panel carried over the table: the section an expert confirmed for the current version, and the row «Без раздела»', () => {
    expect(SECTION_NAME_COLUMN.definition).toBe(
      'Документ учитывается в том разделе, который эксперт подтвердил для его текущей версии. ' +
        'Пока раздел не подтверждён, документ попадает в строку «Без раздела». Раздел подтверждает эксперт на экране версии.',
    );
    expect(SECTION_UNCLASSIFIED_HINT).toContain('Раздел подтверждает эксперт на экране версии.');
  });
});
