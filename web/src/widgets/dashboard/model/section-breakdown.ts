/**
 * Per-section document counts, computed over `getDashboardSummary`'s `section_breakdown`.
 *
 * `R-40`/`D-56`: the server counts published documents for each of the fifteen
 * sections plus an unclassified bucket, zeros included (`SectionDocumentCount`'s own doc comment in
 * `shared/api/generated/types.gen.ts`: "Every one of the fifteen current codes is present
 * even at `document_count: 0`").
 *
 * **This module no longer fills a gap it did not compute.** It used to seed all
 * section codes at zero and overwrite from the wire, calling the result "its true zero" — but a
 * row the response omits is the server not saying, not the server saying zero, and
 * defaulting it is exactly the invented number `R-23`'s addendum names and the silent
 * fallback `AGENTS.md` §4 forbids (`docs/program/reviews/W46-JUDGE-Y.md` §5, `Y5-a`;
 * `docs/program/reviews/W46-JUDGE-X.md` §`X2-a`). It also used to drop, with no signal, a
 * row whose section the frozen codes do not recognise.
 *
 * So this function checks the closed vocabulary instead of filling it: the fifteen section
 * codes, once each, plus the unclassified bucket, once — anything short of exactly that (a
 * missing member, a repeated one, or one this module does not recognise) is reported as
 * `{ ok: false }`, and it is the caller's job to show that as a fault rather than as a
 * number. Only a response that carries the whole vocabulary, no more and no less, is
 * summarised at all.
 *
 * **The unclassified bucket is never folded into a section.** A
 * row with no `section` is a document with no section recorded, not a fifteenth code —
 * `entities/project`'s `PROJECT_SECTIONS` stays the fifteen sections, and this module keeps
 * the unclassified count beside it rather than inside it.
 */

import type { SectionDocumentCount } from '@/shared/api';
import type { ProjectSectionCode } from '@/entities/project';
import { PROJECT_SECTIONS } from '@/entities/project';

/**
 * `UI-A-35`, `R-150n`…`R-150u` (`UI-PARITY-METRICS.md`): the original's five numbers of a section row —
 * never run, without expert decisions, checked, all, findings — read from the server's `audit_counts`.
 * «Нет решений эксперта» is `no_expert_decision` (never run plus awaiting a decision; a clean run is not in
 * it). Absent counts stay absent: the screen shows no number rather than a zero it was not given.
 */
export interface SectionAuditFigures {
  readonly notRun: number;
  readonly noExpertDecision: number;
  readonly checked: number;
  readonly findings: number;
}

export interface SectionBreakdownSummary {
  readonly byCode: Readonly<Record<ProjectSectionCode, number>>;
  readonly auditByCode: Readonly<Partial<Record<ProjectSectionCode, SectionAuditFigures>>>;
  /** Documents with no section at all. Never merged into any of the section codes. */
  readonly unclassifiedCount: number;
}

export type SectionBreakdownResult =
  | { readonly ok: true; readonly summary: SectionBreakdownSummary }
  /** The response did not carry exactly the closed vocabulary: a member missing, repeated, or unrecognised. */
  | { readonly ok: false };

const KNOWN_CODES: ReadonlySet<ProjectSectionCode> = new Set(
  PROJECT_SECTIONS.map((section) => section.code),
);

export function summarizeSectionBreakdown(
  rows: readonly SectionDocumentCount[],
): SectionBreakdownResult {
  const counts = new Map<ProjectSectionCode, number>();
  const audits: Partial<Record<ProjectSectionCode, SectionAuditFigures>> = {};
  let unclassifiedCount: number | null = null;

  for (const row of rows) {
    if (row.section === undefined) {
      if (unclassifiedCount !== null) return { ok: false }; // the unclassified bucket, twice
      unclassifiedCount = row.document_count;
      continue;
    }
    if (!KNOWN_CODES.has(row.section) || counts.has(row.section)) return { ok: false };
    counts.set(row.section, row.document_count);
    if (row.audit_counts !== undefined) {
      audits[row.section] = {
        notRun: row.audit_counts.not_run,
        noExpertDecision: row.audit_counts.no_expert_decision,
        checked: row.audit_counts.checked,
        findings: row.finding_count,
      };
    }
  }

  if (unclassifiedCount === null || counts.size !== PROJECT_SECTIONS.length) return { ok: false };

  const byCode = Object.fromEntries(counts) as Record<ProjectSectionCode, number>;
  return { ok: true, summary: { byCode, auditByCode: audits, unclassifiedCount } };
}
