/**
 * A document's audit state on the screens (`UI-PARITY-DOC-AUDIT`, contract 1.34.0; `UI-A-46`, `UI-A-49`, `UI-A-38`).
 *
 * The model is pure: the server classifies and orders, the screen names. These cases pin the words of the chips, the
 * plural of the figure under a chip, the reading of `?filter=` (only `not_run` is a filter), the sentence over a
 * narrowed list and what the list hook sends.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listDocuments: vi.fn() };
});

import type { DocumentAudit } from '@/shared/api';
import { listDocuments, queryKeys } from '@/shared/api';
import {
  AUDIT_PARTIAL_MARK,
  AUDIT_STATE_CODES,
  DOCUMENT_PAGE_LIMIT,
  auditChip,
  auditStateOf,
  documentListQueryOptions,
  notRunFilterSentence,
  parseSectionAuditFilter,
  pluralRu,
  withNotRunFilter,
} from '@/entities/document-version';

import { PROJECT_UID, page, version } from '../sections/fixtures';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function audit(overrides: Partial<DocumentAudit>): DocumentAudit {
  return { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0, ...overrides };
}

describe('the chip of a document’s audit state', () => {
  it('says each of the four states in its own words and tone', () => {
    const chips = [
      auditChip(audit({ state: 'not_run' })),
      auditChip(audit({ state: 'clean', result_run_id: RUN })),
      auditChip(audit({ state: 'awaiting_decision', result_run_id: RUN, finding_count: 3, undecided_finding_count: 2 })),
      auditChip(audit({ state: 'checked', result_run_id: RUN, finding_count: 3 })),
    ];
    expect(chips.map((chip) => [chip?.state, chip?.text, chip?.tone])).toEqual([
      ['not_run', 'Не запускался', 'inert'],
      ['clean', 'Замечаний нет', 'ok'],
      ['awaiting_decision', 'Ждёт решения: 2', 'failed'],
      ['checked', 'Проверен экспертом', 'ok'],
    ]);
    expect(AUDIT_STATE_CODES).toEqual(['not_run', 'clean', 'awaiting_decision', 'checked']);
  });

  it('draws nothing when the answer carried no audit, and never invents «Не запускался»', () => {
    expect(auditChip(undefined)).toBeNull();
    expect(auditStateOf(version())).toBeNull();
    expect(auditStateOf(version({ audit: audit({ state: 'checked', result_run_id: RUN }) }))).toBe('checked');
  });

  it('names the result run only when there is one, and marks a partial result beside the state', () => {
    expect(auditChip(audit({ state: 'not_run' }))?.resultRunId).toBeNull();
    const partial = auditChip(audit({ state: 'checked', partial: true, result_run_id: RUN, finding_count: 1 }));
    expect([partial?.resultRunId, partial?.partial, partial?.text]).toEqual([RUN, true, 'Решения по находкам приняты']);
    expect(AUDIT_PARTIAL_MARK).toBe('частично');
  });

  it('does not present a partial empty publication as a complete clean audit', () => {
    const partial = auditChip(audit({ state: 'clean', partial: true, result_run_id: RUN }));
    expect(partial?.text).toBe('Находок не опубликовано');
    expect(partial?.tone).toBe('pending');
    expect(partial?.detail).toContain('не означает отсутствие замечаний');
    expect(partial?.resultRunId).toBe(RUN);
  });

  it('shows the figures of the result run as the chip’s detail, with the right plural', () => {
    const detail = (finding_count: number, undecided_finding_count: number) =>
      auditChip(audit({ state: undecided_finding_count > 0 ? 'awaiting_decision' : 'checked', result_run_id: RUN, finding_count, undecided_finding_count }))?.detail;
    expect(detail(1, 0)).toBe('1 замечание');
    expect(detail(3, 2)).toBe('3 замечания, без решения эксперта: 2');
    expect(detail(5, 5)).toBe('5 замечаний, без решения эксперта: 5');
    expect(auditChip(audit({ state: 'not_run' }))?.detail).toBeNull();
  });

  it('inflects a count the Russian way', () => {
    const forms = ['замечание', 'замечания', 'замечаний'] as const;
    expect([0, 1, 2, 4, 5, 11, 12, 14, 21, 22, 25, 101, 111].map((n) => pluralRu(n, forms))).toEqual([
      'замечаний', 'замечание', 'замечания', 'замечания', 'замечаний', 'замечаний', 'замечаний', 'замечаний',
      'замечание', 'замечания', 'замечаний', 'замечание', 'замечаний',
    ]);
  });
});

describe('the «не запускались» filter of the section page', () => {
  it('reads only not_run as a filter', () => {
    expect(parseSectionAuditFilter('not_run')).toBe('not_run');
    for (const other of [undefined, null, '', 'clean', 'NOT_RUN', ['not_run', 'not_run'], ['not_run']]) {
      expect(parseSectionAuditFilter(other as never), JSON.stringify(other)).toBeNull();
    }
  });

  it('builds the address the dashboard links to', () => {
    expect(withNotRunFilter(`/projects/${PROJECT_UID}/sections/AR`)).toBe(`/projects/${PROJECT_UID}/sections/AR?filter=not_run`);
  });

  it('says what the list is, and whose count it is when the list goes on', () => {
    expect(notRunFilterSentence(7, true)).toBe('Показаны документы, которые не анализировались: 7');
    expect(notRunFilterSentence(50, false)).toBe('Показаны документы, которые не анализировались: 50 на этой странице');
  });
});

describe('listDocuments as the screens send it', () => {
  const read = vi.mocked(listDocuments);
  beforeEach(() => {
    read.mockReset();
    read.mockResolvedValue({ data: page([version()]) } as never);
  });

  it('sends the audit state and the order only when asked, and keeps the listing apart in the cache', async () => {
    await documentListQueryOptions(PROJECT_UID, undefined, 'AR').queryFn();
    await documentListQueryOptions(PROJECT_UID, 'c1', 'AR', false, undefined, { state: 'not_run', order: 'audit' }).queryFn();
    expect(read.mock.calls[0]?.[0]).toEqual({
      path: { project_uid: PROJECT_UID },
      query: { limit: DOCUMENT_PAGE_LIMIT, section_code: 'AR' },
    });
    expect(read.mock.calls[1]?.[0]).toEqual({
      path: { project_uid: PROJECT_UID },
      query: { cursor: 'c1', limit: DOCUMENT_PAGE_LIMIT, section_code: 'AR', audit_state: 'not_run', order: 'audit' },
    });
    const keys = [
      documentListQueryOptions(PROJECT_UID, undefined, 'AR').queryKey,
      documentListQueryOptions(PROJECT_UID, undefined, 'AR', false, undefined, { order: 'audit' }).queryKey,
      documentListQueryOptions(PROJECT_UID, undefined, 'AR', false, undefined, { state: 'not_run', order: 'audit' }).queryKey,
    ].map((key) => JSON.stringify(key));
    expect(new Set(keys).size).toBe(3);
    expect(keys[0]).toBe(JSON.stringify(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR')));
  });
});
