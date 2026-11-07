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
import { EMPTY_TALLY, tallyOfCounts } from '@/entities/document-version';
import { PROJECT_SECTIONS } from '@/entities/project';

export const UNCLASSIFIED_FIGURES = 'unclassified';

export type SectionFigures = ReadonlyMap<string, AuditTally>;

export function sectionFigures(rows: readonly SectionDocumentCount[]): SectionFigures {
  const figures = new Map<string, AuditTally>();
  for (const row of rows) {
    figures.set(row.section ?? UNCLASSIFIED_FIGURES, { ...tallyOfCounts(row.audit_counts), findings: row.finding_count });
  }
  return figures;
}

/**
 * `UI-A-36`: the original's «Σ Итого» -- the column sums of the fifteen sections' rows, by the arithmetic the dashboard's
 * total row does (`summarizeSectionBreakdown`): the sum of what the rows show, so «Не классифицировано» (a row of its own,
 * never folded into a section) is not in it. It exists only when the server's figures hold every one of the fifteen
 * sections: one section without its entry makes the total absent, not a smaller number, and a page's own count is never
 * summed into it.
 */
export function totalFigures(figures: SectionFigures): AuditTally | undefined {
  let total: AuditTally = EMPTY_TALLY;
  for (const section of PROJECT_SECTIONS) {
    const row = figures.get(section.code);
    if (row === undefined) return undefined;
    total = {
      documents: total.documents + row.documents,
      notRun: total.notRun + row.notRun,
      awaitingDecision: total.awaitingDecision + row.awaitingDecision,
      checked: total.checked + row.checked,
      clean: total.clean + row.clean,
      findings: total.findings === null || row.findings === null ? null : total.findings + row.findings,
    };
  }
  return total;
}
