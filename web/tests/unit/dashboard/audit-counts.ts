/**
 * Fixture helper (`UI-PARITY-P0B`, contract 1.19.0): the `DocumentAuditCounts` of a section or a project whose
 * documents were never run, and the rows of `section_breakdown` that carry them. A fixture that only needs the
 * required fields to type-check says "nothing has been run" and nothing else.
 */

import type { DocumentAuditCounts } from '@/shared/api';

/** `documents` documents, none of them run: `not_run` is all of them and `no_expert_decision` with it. */
export function auditCounts(documents: number, over: Partial<DocumentAuditCounts> = {}): DocumentAuditCounts {
  return {
    document_count: documents,
    not_run: documents,
    clean: 0,
    awaiting_decision: 0,
    checked: 0,
    partial: 0,
    no_expert_decision: documents,
    ...over,
  };
}

/** The two fields every `SectionDocumentCount` now carries beside its `document_count`. */
export function sectionAudit(
  documents: number,
  over: Partial<DocumentAuditCounts> = {},
  findings = 0,
): { audit_counts: DocumentAuditCounts; finding_count: number } {
  return { audit_counts: auditCounts(documents, over), finding_count: findings };
}
