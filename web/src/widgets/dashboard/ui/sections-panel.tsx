/**
 * Panel 4 — per-section breakdown.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `section_breakdown` rows. This is the one panel `W46-DASH` could
 * not drive against real data — the aggregate that answers it is `W46-SPEND`'s own
 * hotspot and arrived only at merge.
 *
 * **What the numbers are, and what the sentence above them says (`WEB-SECTION-COPY-01`).**
 * The server counts a document in the section an expert confirmed for its **current
 * version**, and a document whose current version no expert has classified in the row
 * «Без раздела» (`SECTION-READ-MODEL-01`, `D-180`). The sentence says exactly that, in the
 * words of the subject and without naming an operation, a field or a transport (`R-39`), and
 * it carries no digit, so the «no invented number» render test keeps meaning something. It
 * used to blame the upload form for the unclassified row ("the form offers no section, so a
 * document sent through it stays without one"). That was the cause until `W59-SECTION-UI-01`
 * gave an expert the means to confirm a section on the version screen; since then a document
 * sent through the form leaves «Без раздела» as soon as an expert confirms it, so the old
 * sentence described a state no document stays in. An earlier version of it (`F-3`) had the
 * same defect from the other side: it denied that a section is stored at all.
 *
 * **Every row carries the route that analyses its section.** `data-analysed-by` is
 * `PROJECT_SECTIONS`' `analysedBy` — the section's own text profile for fourteen sections,
 * the group of six AR v3 checks for АР — so an instrument can tell them apart. It is data, not
 * a new line of text on the screen.
 *
 * **Always shows the unclassified row, and never folds it into a section.** Fifteen true
 * zeros with the unclassified row hidden would read as *"no documents"* when the product may
 * hold plenty, all of them unclassified — the exact false picture `F-3b` warned the wiring
 * session against.
 *
 * **An omitted or unrecognised row is a fault, never a zero.** `summarizeSectionBreakdown`
 * only returns a summary over the whole closed vocabulary — the section codes plus the
 * unclassified bucket, each once. Anything short of that renders no numbers at all: the
 * shape `dashboard-failure.ts` already has, not a zero nobody computed
 * (`docs/program/reviews/W46-JUDGE-Y.md` §5, `Y5-a`).
 */

import { ErrorState } from '@/shared/ui';
import { PROJECT_SECTIONS, projectSectionTitle } from '@/entities/project';
import type { SectionDocumentCount } from '@/shared/api';

import { incompleteBreakdownFailure } from '../model/dashboard-failure';
import { summarizeSectionBreakdown } from '../model/section-breakdown';

export interface SectionsPanelProps {
  readonly rows: readonly SectionDocumentCount[];
}

export function SectionsPanel({ rows }: SectionsPanelProps) {
  const result = summarizeSectionBreakdown(rows);

  if (!result.ok) {
    const failure = incompleteBreakdownFailure('Разбивка по разделам пришла неполной.');
    return (
      <div data-panel="per-section-breakdown" data-panel-fault={failure.kind}>
        <ErrorState title={failure.title} detail={failure.detail} />
      </div>
    );
  }

  const { summary } = result;

  return (
    <div data-panel="per-section-breakdown">
      <p className="am-state__correlation">
        Документ учитывается в том разделе, который эксперт подтвердил для его текущей версии.
        Пока раздел не подтверждён, документ попадает в строку «Без раздела». Раздел
        подтверждает эксперт на экране версии.
      </p>
      <ul data-section-count={PROJECT_SECTIONS.length}>
        {PROJECT_SECTIONS.map((section) => (
          <li key={section.code} data-section={section.code} data-analysed-by={section.analysedBy}>
            {projectSectionTitle(section)}
            : <strong>{summary.byCode[section.code]}</strong>
          </li>
        ))}
        <li data-section="unclassified">
          Без раздела: <strong>{summary.unclassifiedCount}</strong>
        </li>
      </ul>
    </div>
  );
}
