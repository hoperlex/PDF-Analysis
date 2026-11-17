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

/**
 * `UI-A-36`: the original's «Σ Итого» row -- the column sums of the fifteen section rows above it, the same arithmetic the
 * documents and verdicts panels already do over their rows. It is the sum of what the table shows, so «Без раздела» (a
 * row of its own, never folded into a section) is not in it. The audit sums exist only when all fifteen rows carry
 * `audit_counts`: one absent row makes them absent, not a smaller number.
 */
export interface SectionTotals {
  readonly documents: number;
  readonly audit: SectionAuditFigures | undefined;
}

/**
 * `UIP-S01-02` (Г4-B, Г3-B): the words of the section table's header, each with its definition.
 *
 * The labels are the original's («Не запускались на проверку», «Нет решений эксперта», «Проверено экспертом», «Всего», «Замечаний»).
 * A definition says what the column counts in the words of `UI-PARITY-METRICS.md` (§1 the counted document and its current version,
 * §2 the result run, §3 the figures on the wire; the draft's M-01 … M-06): «документов, у которых …». It is shown as the heading's
 * tooltip and is in the text a screen reader reads, so the table needs no paragraph above it. A definition names no digit and no
 * word the dictionary does not have, so every number on the panel is still a count the server sent.
 *
 * The «Раздел» definition is the sentence the panel used to carry above its rows: where a document stands (`SECTION-READ-MODEL-01`,
 * `D-180`) and who confirms it. It is the same sentence, word for word, and it still blames nothing for the unclassified row.
 */
export interface SectionColumn {
  readonly key: 'section' | 'not_run' | 'no_expert_decision' | 'checked' | 'total' | 'findings';
  /** What the heading says, and the title of the figure under it. */
  readonly label: string;
  /** The definition: the heading's tooltip and its text for a screen reader. */
  readonly definition: string;
}

export const SECTION_NAME_COLUMN: SectionColumn = {
  key: 'section',
  label: 'Раздел',
  definition:
    'Документ учитывается в том разделе, который эксперт подтвердил для его текущей версии. ' +
    'Пока раздел не подтверждён, документ попадает в строку «Без раздела». Раздел подтверждает эксперт на экране версии.',
};

/** The five figures of a row, in the table's order: not run, without an expert decision, checked, all, remarks. */
export const SECTION_METRIC_COLUMNS = {
  notRun: {
    key: 'not_run',
    label: 'Не запускались на проверку',
    definition:
      'Документов, у которых на текущей версии нет результата проверки: она не запускалась, ещё идёт, отменена или не удалась.',
  },
  noExpertDecision: {
    key: 'no_expert_decision',
    label: 'Нет решений эксперта',
    definition:
      'Документов, у которых на текущей версии проверка не запускалась или остались замечания, по которым эксперт ещё не принял решения.',
  },
  checked: {
    key: 'checked',
    label: 'Проверено экспертом',
    definition:
      'Документов, у которых на текущей версии есть результат проверки с замечаниями и эксперт принял решение по каждому из них: принял или отклонил.',
  },
  total: {
    key: 'total',
    label: 'Всего',
    definition:
      'Документов, у которых текущая версия отнесена к этому разделу; версии одного документа считаются один раз.',
  },
  findings: {
    key: 'findings',
    label: 'Замечаний',
    definition:
      'Замечаний в результатах проверки текущих версий документов раздела, независимо от решения эксперта.',
  },
} as const satisfies Record<string, SectionColumn>;

/** The total row's name (`UI-A-36`): the original's «Σ Итого». */
export const SECTION_TOTAL_LABEL = 'Итого';

/**
 * The tooltip of the row «Без раздела» (and its text for a screen reader): who stands in it and how a document leaves it. Its
 * meaning is the second half of the sentence the panel used to carry above its rows; the other half is the «Раздел» definition.
 */
export const SECTION_UNCLASSIFIED_HINT =
  'Документы, у которых эксперт ещё не подтвердил раздел текущей версии. Раздел подтверждает эксперт на экране версии.';

export interface SectionBreakdownSummary {
  readonly byCode: Readonly<Record<ProjectSectionCode, number>>;
  readonly totals: SectionTotals;
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
  const figures = Object.values(audits);
  const totals: SectionTotals = {
    documents: [...counts.values()].reduce((sum, count) => sum + count, 0),
    audit:
      figures.length === PROJECT_SECTIONS.length
        ? {
            notRun: figures.reduce((sum, row) => sum + row.notRun, 0),
            noExpertDecision: figures.reduce((sum, row) => sum + row.noExpertDecision, 0),
            checked: figures.reduce((sum, row) => sum + row.checked, 0),
            findings: figures.reduce((sum, row) => sum + row.findings, 0),
          }
        : undefined,
  };
  return { ok: true, summary: { byCode, totals, auditByCode: audits, unclassifiedCount } };
}
