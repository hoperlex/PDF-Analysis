/**
 * Per-section document counts, computed over `getDashboardSummary`'s `section_breakdown`.
 *
 * `R-40`/`D-56`: the server counts published documents per section, fourteen frozen codes
 * plus an unclassified bucket, zeros included (`SectionDocumentCount`'s own doc comment in
 * `shared/api/generated/types.gen.ts`). This module never trusts that every one of the
 * fifteen rows actually arrived — it merges the wire array onto the fixed vocabulary the
 * same way the backend's own repository does (`docs/program/reviews/W46-JUDGE-A.md` §3's
 * quoted mutation, `[(member, counted.get(member, 0)) for member in vocabulary]`), so a
 * row a future response happens to omit reads as its true zero rather than as `undefined`
 * propagating into a rendered `NaN`.
 *
 * **The unclassified bucket is never folded into a fourteenth or fifteenth section.** A
 * row with no `section` is a document with no section recorded, not a fifteenth code —
 * `entities/project`'s `PROJECT_SECTIONS` stays the frozen fourteen, and this module keeps
 * the unclassified count beside it rather than inside it.
 */

import type { SectionDocumentCount } from '@/shared/api';
import type { ProjectSectionCode } from '@/entities/project';
import { PROJECT_SECTIONS } from '@/entities/project';

export interface SectionBreakdownSummary {
  readonly byCode: Readonly<Record<ProjectSectionCode, number>>;
  /** Documents with no section at all. Never merged into any of the fourteen codes. */
  readonly unclassifiedCount: number;
}

export function summarizeSectionBreakdown(
  rows: readonly SectionDocumentCount[],
): SectionBreakdownSummary {
  // A `Map`, not a `Record`, while accumulating: `noUncheckedIndexedAccess` makes every
  // `Record` read `T | undefined`, and a running total needs a definite starting value.
  // `PROJECT_SECTIONS` seeds every one of the fourteen codes at zero up front, which is
  // the merge this module's own header describes — a code the wire never mentions still
  // reads as its true zero, never as `undefined`.
  const counts = new Map<ProjectSectionCode, number>(
    PROJECT_SECTIONS.map((section) => [section.code, 0]),
  );
  let unclassifiedCount = 0;

  for (const row of rows) {
    if (row.section === undefined) {
      unclassifiedCount += row.document_count;
      continue;
    }
    const known = counts.get(row.section);
    if (known !== undefined) counts.set(row.section, known + row.document_count);
  }

  const byCode = Object.fromEntries(counts) as Record<ProjectSectionCode, number>;
  return { byCode, unclassifiedCount };
}
