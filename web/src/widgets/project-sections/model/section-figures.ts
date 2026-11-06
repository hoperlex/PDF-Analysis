/**
 * The exact audit figures of each section of one project, from the server's own section panel (`UI-A-35`, `UI-PARITY-P0B`).
 *
 * The project page and the section page count what the page of `listDocuments` holds, and say so when it is a page of a
 * longer list. The dashboard's section panel is the server's count over the whole project, so where it is at hand the
 * figures are exact and the caveat goes away. A section with no row (a server that did not send it) has no entry and the
 * screen falls back to its page; the unclassified documents are their own entry.
 */

import type { SectionDocumentCount } from '@/shared/api';
import type { AuditTally } from '@/entities/document-version';
import { tallyOfCounts } from '@/entities/document-version';

export const UNCLASSIFIED_FIGURES = 'unclassified';

export type SectionFigures = ReadonlyMap<string, AuditTally>;

export function sectionFigures(rows: readonly SectionDocumentCount[]): SectionFigures {
  const figures = new Map<string, AuditTally>();
  for (const row of rows) {
    figures.set(row.section ?? UNCLASSIFIED_FIGURES, { ...tallyOfCounts(row.audit_counts), findings: row.finding_count });
  }
  return figures;
}
