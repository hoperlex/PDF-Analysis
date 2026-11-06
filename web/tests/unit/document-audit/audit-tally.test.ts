/**
 * `UI-A-35`: the original's row of numbers for a set of documents -- documents, not started, awaiting a decision,
 * checked, findings -- counted over what the screen already holds.
 *
 * What is held: the figures are read off each document's `audit` (never derived from a title or a label), a
 * document without an `audit` is in the total only, the project's counters give the same row without findings, a
 * state at zero is left out so the row says only what is there, and a page of a longer list says so in words.
 * The screens: the section page's subtitle, the project's structure (one row per section) and the project page.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentAudit } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT } from '@/entities/document-version';
import {
  AuditTallyLine, EMPTY_TALLY, auditTally, tallyOfCounts, tallyParts,
} from '@/entities/document-version';
import { SectionDetailPage } from '@/_pages/section-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import {
  ProjectSections, ProjectStructureView, UNCLASSIFIED_FIGURES, sectionFigures,
} from '@/widgets/project-sections';

import { auditCounts, sectionAudit } from '../dashboard/audit-counts';
import { newClient, renderScreen, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from '../sections/fixtures';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function audit(overrides: Partial<DocumentAudit>): DocumentAudit {
  return { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0, ...overrides };
}

const AR = classification({ section_code: 'AR' });
const DOCS = [
  version({ classification: AR, audit: audit({ state: 'checked', result_run_id: RUN, finding_count: 4 }) }),
  otherVersion('B', { classification: AR, audit: audit({ state: 'awaiting_decision', result_run_id: RUN, finding_count: 3, undecided_finding_count: 2 }) }),
  otherVersion('C', { classification: AR, audit: audit({ state: 'not_run' }) }),
  otherVersion('D', { classification: AR, audit: audit({ state: 'not_run' }) }),
  otherVersion('E', { classification: AR, audit: audit({ state: 'clean', result_run_id: RUN }) }),
  otherVersion('F', { classification: AR }),
];

describe('auditTally — the figures of a page of documents', () => {
  it('counts each state from the document’s own audit and sums the findings of the result runs', () => {
    expect(auditTally(DOCS)).toEqual({
      documents: 6, notRun: 2, awaitingDecision: 1, checked: 1, clean: 1, findings: 7,
    });
  });

  it('puts a document with no audit in the total and in no state', () => {
    const tally = auditTally(DOCS);
    expect(tally.notRun + tally.awaitingDecision + tally.checked + tally.clean).toBe(tally.documents - 1);
  });

  it('is zero for no documents', () => {
    expect(auditTally([])).toEqual(EMPTY_TALLY);
  });

  it('takes the project’s counters as they are and carries no findings', () => {
    const counts = auditCounts(6, { not_run: 2, awaiting_decision: 1, checked: 2, clean: 1, no_expert_decision: 3 });
    expect(tallyOfCounts(counts)).toEqual({ documents: 6, notRun: 2, awaitingDecision: 1, checked: 2, clean: 1, findings: null });
  });
});

describe('tallyParts — the words of the row', () => {
  it('starts with the total, then each state that is not zero, in the original’s column order', () => {
    expect(tallyParts(auditTally(DOCS)).map((part) => `${part.label}:${part.count}`)).toEqual([
      'документов:6', 'не запускались:2', 'ждут решения:1', 'проверено:1', 'без замечаний:1', 'замечаний:7',
    ]);
  });

  it('leaves out a state that is zero and the findings when the source does not count them', () => {
    const parts = tallyParts(tallyOfCounts(auditCounts(1, { not_run: 1, no_expert_decision: 1 })));
    expect(parts.map((part) => part.key)).toEqual(['documents', 'notRun']);
  });

  it('agrees the nouns with the number', () => {
    expect(tallyParts({ ...EMPTY_TALLY, documents: 1 })[0]?.label).toBe('документ');
    expect(tallyParts({ ...EMPTY_TALLY, documents: 3 })[0]?.label).toBe('документа');
    expect(tallyParts({ ...EMPTY_TALLY, documents: 12, findings: 21 }).at(-1)?.label).toBe('замечание');
    expect(tallyParts({ ...EMPTY_TALLY, documents: 12, findings: 22 }).at(-1)?.label).toBe('замечания');
  });
});

describe('AuditTallyLine', () => {
  it('draws the row as a labelled group with a badge per state', () => {
    const markup = renderWith(newClient(), createElement(AuditTallyLine, { tally: auditTally(DOCS), label: 'АР' }));
    expect(markup).toContain('role="group"');
    expect(markup).toContain('aria-label="Состояние проверки: АР"');
    expect(markup).toContain('data-tally="notRun"');
    expect(markup).toContain('am-badge--failed');
    expect(markup).not.toContain('по документам этой страницы');
  });

  it('says in words that a page of a longer list was counted', () => {
    const markup = renderWith(newClient(), createElement(AuditTallyLine, { tally: auditTally(DOCS), partial: true }));
    expect(markup).toContain('data-audit-tally-partial="true"');
    expect(markup).toContain('по документам этой страницы');
  });
});

describe('where the row is drawn', () => {
  it('under the section page’s title, from the documents the page holds', () => {
    const client = newClient();
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit'),
      page(DOCS, 'next'),
    );
    const markup = renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('data-audit-tally="6"');
    expect(markup).toContain('data-audit-tally-partial="true"');
  });

  it('on each section of the project’s structure that holds documents, and on none that is empty', () => {
    const markup = renderWith(
      newClient(),
      createElement(ProjectStructureView, { projectUid: PROJECT_UID, items: DOCS, hasNextPage: false }),
    );
    expect((markup.match(/data-audit-tally="/g) ?? [])).toHaveLength(1);
    expect(markup).toContain('data-audit-tally="6"');
  });

  it('above the project page’s tabs, from the counters the project carries and with no findings', () => {
    const client = newClient();
    client.setQueryData(queryKeys.projects.detail(PROJECT_UID), {
      project_uid: PROJECT_UID, name: 'Школа', created_at: '2026-09-10T08:00:00.000Z',
      audit_counts: auditCounts(5, { not_run: 2, awaiting_decision: 1, checked: 2, no_expert_decision: 3 }),
    });
    const markup = renderScreen(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
    expect(markup).toContain('data-audit-tally="5"');
    expect(markup).toContain('aria-label="Состояние проверки: Школа"');
    expect(markup).not.toContain('data-tally="findings"');
  });
});

// ------------------------------------------------------------------ the server's own count per section

describe('sectionFigures — the section panel as exact figures', () => {
  const rows = [
    { section: 'AR' as const, document_count: 80, ...sectionAudit(80, { not_run: 30, awaiting_decision: 10, checked: 40, no_expert_decision: 40 }, 123) },
    { section: 'KJ' as const, document_count: 5, ...sectionAudit(5, { not_run: 5, no_expert_decision: 5 }) },
    { document_count: 2, ...sectionAudit(2, { not_run: 2, no_expert_decision: 2 }) },
  ];

  it('files each row under its section code, the unclassified documents under their own key, with the findings', () => {
    const figures = sectionFigures(rows);
    expect(figures.get('AR')).toEqual({ documents: 80, notRun: 30, awaitingDecision: 10, checked: 40, clean: 0, findings: 123 });
    expect(figures.get('KJ')?.documents).toBe(5);
    expect(figures.get(UNCLASSIFIED_FIGURES)?.documents).toBe(2);
    expect(figures.has('OV')).toBe(false);
  });

  const client = () => {
    const seeded = newClient();
    seeded.setQueryData(queryKeys.dashboard.summary(PROJECT_UID), { section_breakdown: rows });
    return seeded;
  };

  it('state a section the page does not hold as it is, not as empty, and drop the page caveat', () => {
    const seeded = client();
    seeded.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
      page([DOCS[0] as (typeof DOCS)[number]], 'next'),
    );
    const markup = renderWith(seeded, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    const from = markup.indexOf('data-section-group="KJ"');
    const kj = markup.slice(from, markup.indexOf('data-section-group=', from + 1));
    expect(kj).toContain('data-audit-tally="5"');
    expect(kj).not.toContain('документов нет');
    expect(kj).toContain('Открыть раздел');
    expect(markup).toContain('data-audit-tally="80"');
    expect(markup).not.toContain('по документам этой страницы');
  });

  it('reads the project’s summary under the key the dashboard uses, so a warm dashboard costs no request', () => {
    expect(queryKeys.dashboard.summary(PROJECT_UID)).toEqual(['dashboard', 'summary', { project: PROJECT_UID }]);
  });

  it('counts the page and says so while the server’s figures are not at hand', () => {
    const empty = newClient();
    empty.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
      page(DOCS, 'next'),
    );
    const markup = renderWith(empty, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    expect(markup).toContain('data-audit-tally="6"');
    expect(markup).toContain('по документам этой страницы');
  });

  it('gives the section page the server’s count of its section, with no page caveat', () => {
    const seeded = client();
    seeded.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit'),
      page(DOCS, 'next'),
    );
    const markup = renderWith(seeded, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('data-audit-tally="80"');
    expect(markup).toContain('data-audit-tally-partial="false"');
  });
});
