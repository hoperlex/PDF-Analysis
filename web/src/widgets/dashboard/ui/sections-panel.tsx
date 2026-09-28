/**
 * Panel 4 — per-section breakdown.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `section_breakdown` rows. This is the one panel `W46-DASH` could
 * not drive against real data — the aggregate that answers it is `W46-SPEND`'s own
 * hotspot and arrived only at merge — and it is the one whose caption the merge made
 * false (`F-3`): the section **is** stored (`document.section`, migration `0011`) and
 * **is** checked (the upload refuses `section=""`, `ar` and `ZZ` with `422
 * validation_failed`), so *"раздел нигде не хранится и не проверяется"* stopped being
 * true the moment the reseal landed, independently of this panel being wired.
 *
 * **What is true instead**, in the words of the subject and without naming an operation,
 * a field or a transport (`R-39`): a section is recorded when an upload names one, and the
 * product's own upload form (`widgets/upload-panel`) offers a file and a title and nothing
 * else — no document reaches this deployment through the product with a section attached.
 * So the "without a section" row is not a gap in counting; it is the honest shape of every
 * document this product has ever accepted. Adding a section picker is a feature, not this
 * task (`D-107`).
 *
 * **Always shows the unclassified row, and never folds it into the fourteen.** Fourteen
 * true zeros with the unclassified row hidden would read as *"no documents"* when the
 * product may hold plenty, all of them unclassified — the exact false picture `F-3b`
 * warned the wiring session against.
 *
 * **An omitted or unrecognised row is a fault, never a zero.** `summarizeSectionBreakdown`
 * only returns a summary over the whole closed vocabulary — fourteen codes plus the
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
        Раздел документа сохраняется и проверяется на сервере, когда его называют при
        загрузке. Форма загрузки в этом продукте раздел не предлагает, поэтому документ,
        отправленный через неё, остаётся без раздела — вот откуда строка «Без раздела» ниже,
        а не из пропуска в подсчёте.
      </p>
      <ul data-section-count={PROJECT_SECTIONS.length}>
        {PROJECT_SECTIONS.map((section) => (
          <li key={section.code} data-section={section.code} data-analysed={section.analysed}>
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
