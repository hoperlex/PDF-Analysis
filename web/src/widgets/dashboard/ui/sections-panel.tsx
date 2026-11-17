'use client';

/**
 * Panel 4 — per-section breakdown.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `section_breakdown` rows. This is the one panel `W46-DASH` could
 * not drive against real data — the aggregate that answers it is `W46-SPEND`'s own
 * hotspot and arrived only at merge.
 *
 * **What the numbers are, and where the sentence that says it stands (`WEB-SECTION-COPY-01`, `UIP-S01-02`).**
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
 * Since `UIP-S01-02` it is no longer a paragraph over the table (the original has none): it is the definition of the heading
 * «Раздел», and its second half is the hint of the row «Без раздела». Every other heading has a definition of its own («документов,
 * у которых …», `model/section-breakdown.ts`), shown as the heading's tooltip and said in the text a screen reader reads, so the
 * header is no longer hidden from assistive technology.
 *
 * **The badge of a row wears the section's colour (`UIP-S01-03`, `UIP-G-17`).** `sectionColourVar(code)` is the one list the menu's
 * dot and the section's heading read, so the table carries no colour of its own: the badge's outline is that token, set inline as
 * `border-color` (the stylesheet's own outline is the neutral inert token, which is what the total row and «Без раздела» keep). It is
 * not set through the custom property `sectionColourStyle` offers (the dot's way): the fake DOM of the live-mount instrument
 * (`tests/unit/analysis-settings/live-render.ts`) has no `style.setProperty`, which React calls for a custom property, so a section
 * row set that way could not be mounted by the tests that mount this panel with the dashboard.
 *
 * **Every row carries the route that analyses its section.** `data-analysed-by` is
 * `PROJECT_SECTIONS`' `analysedBy` — the section's own text profile for all fifteen sections.
 * It is data, not
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

import { useState } from 'react';
import Link from 'next/link';

import { ErrorState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { PROJECT_SECTIONS, sectionColourVar } from '@/entities/project';
import type { ProjectSectionCode } from '@/entities/project';
import { withNotRunFilter } from '@/entities/document-version';
import type { SectionDocumentCount } from '@/shared/api';

import { incompleteBreakdownFailure } from '../model/dashboard-failure';
import {
  SECTION_METRIC_COLUMNS,
  SECTION_NAME_COLUMN,
  SECTION_TOTAL_LABEL,
  SECTION_UNCLASSIFIED_HINT,
  summarizeSectionBreakdown,
} from '../model/section-breakdown';
import type { SectionAuditFigures, SectionColumn } from '../model/section-breakdown';
import styles from './sections-panel.module.css';

export interface SectionsPanelProps {
  readonly rows: readonly SectionDocumentCount[];
  /**
   * `R-151l`: the project the dashboard follows (`?project=`), or `null` for «Все проекты». With a project, a
   * chosen section opens that project's section page; across all projects there is no one section page to open.
   */
  readonly projectUid?: string | null | undefined;
}


/**
 * `UI-A-35`: the five numbers of a section row; without `audit_counts` only the document count is shown.
 *
 * `UI-A-38` (`UI-PARITY-DOC-AUDIT`): «Не запускались» is a link to the section page narrowed to those documents
 * (`?filter=not_run`) when the dashboard follows one project and the section has some; across all projects there is no one
 * section page to open, and a zero has nothing to show, so both stay plain numbers.
 */
function SectionMetrics({
  documents,
  audit,
  notRunHref,
}: {
  readonly documents: number;
  readonly audit: SectionAuditFigures | undefined;
  readonly notRunHref: string | null;
}) {
  const { notRun, noExpertDecision, checked, total, findings } = SECTION_METRIC_COLUMNS;
  return (
    <span className={styles.metrics}>
      <span className={`${styles.metric} ${styles.notRun}`} title={notRun.label} data-metric="not-run">
        {audit !== undefined && notRunHref !== null && audit.notRun > 0 ? (
          <Link
            className={styles.metricLink}
            href={notRunHref}
            aria-label={`${notRun.label}: ${audit.notRun}. Открыть список`}
            data-not-run-link=""
          >
            {audit.notRun}
          </Link>
        ) : (
          (audit?.notRun ?? '—')
        )}
      </span>
      <span className={`${styles.metric} ${styles.awaiting}`} title={noExpertDecision.label} data-attention={audit !== undefined && audit.noExpertDecision > 0 ? 'true' : 'false'}>
        {audit?.noExpertDecision ?? '—'}
      </span>
      <span className={`${styles.metric} ${styles.checked}`} title={checked.label}>{audit?.checked ?? '—'}</span>
      <span className={`${styles.metric} ${styles.total}`} title={total.label}><strong>{documents}</strong></span>
      <span className={`${styles.metric} ${styles.remarks}`} title={findings.label}>{audit?.findings ?? '—'}</span>
    </span>
  );
}

/**
 * One heading of the header (`UIP-S01-02`): its words, its definition as the tooltip, and the same definition as text a screen
 * reader reads after the words (a tooltip alone is not read reliably, and is out of reach of the keyboard; a shared tooltip with
 * keyboard control is `UIP-G-04`'s, in `shared/ui`). The words stay a plain `<span>`: the definition is not part of what is drawn.
 */
function ColumnHead({ column, className }: { readonly column: SectionColumn; readonly className?: string | undefined }) {
  return (
    <span className={className === undefined ? styles.head : `${styles.head} ${className}`} title={column.definition} data-column={column.key}>
      <span>{column.label}</span>
      <span className={styles.definition}>{`. ${column.definition}`}</span>
    </span>
  );
}

/** The badge of a section row: the section's own colour as the outline (`UIP-S01-03`). */
function badgeStyle(code: ProjectSectionCode): { readonly borderColor: string } {
  return { borderColor: sectionColourVar(code) };
}

export function SectionsPanel({ rows, projectUid = null }: SectionsPanelProps) {
  const [selected, setSelected] = useState<ProjectSectionCode | null>(null);
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
    <div className={styles.overview} data-panel="per-section-breakdown">
      <div className={styles.header} data-sections-head="">
        <ColumnHead column={SECTION_NAME_COLUMN} className={styles.nameHead} />
        <span className={styles.metrics}>
          <ColumnHead column={SECTION_METRIC_COLUMNS.notRun} />
          <ColumnHead column={SECTION_METRIC_COLUMNS.noExpertDecision} />
          <ColumnHead column={SECTION_METRIC_COLUMNS.checked} />
          <ColumnHead column={SECTION_METRIC_COLUMNS.total} />
          <ColumnHead column={SECTION_METRIC_COLUMNS.findings} />
        </span>
      </div>
      <ul className={styles.rows} data-section-count={PROJECT_SECTIONS.length}>
        {PROJECT_SECTIONS.map((section) => (
          <li
            key={section.code}
            className={`${styles.row} ${styles.sectionRow}`}
            data-section={section.code}
            data-analysed-by={section.analysedBy}
            data-open={selected === section.code ? 'true' : 'false'}
          >
            {projectUid === null ? (
              <button
                type="button"
                className={styles.rowButton}
                aria-expanded={selected === section.code}
                onClick={() => setSelected(selected === section.code ? null : section.code)}
              >
                <span className={styles.badge} style={badgeStyle(section.code)}>{section.code}</span>
                <span className={styles.name}>{section.name}</span>
              </button>
            ) : (
              /*
               * `UI-A-37`: the original's row is the link (a click on it opens the section) and has nothing to unfold. With a
               * project to open the section in, the name is that link and its box is stretched over the whole row (`rowLink`),
               * so a click anywhere on the row opens the section; the figure of «Не запускались» and the toggle at the row's
               * end stay targets of their own, above it. The toggle keeps what the row used to do -- the panel under the
               * list with «Открыть раздел» and «Оптимизация раздела» -- reachable.
               */
              <Link
                className={`${styles.rowButton} ${styles.rowLink}`}
                href={routes.projectSection(projectUid, section.code)}
                data-section-open={section.code}
              >
                <span className={styles.badge} style={badgeStyle(section.code)}>{section.code}</span>
                <span className={styles.name}>{section.name}</span>
              </Link>
            )}
            <SectionMetrics
              documents={summary.byCode[section.code]}
              audit={summary.auditByCode[section.code]}
              notRunHref={projectUid === null ? null : withNotRunFilter(routes.projectSection(projectUid, section.code))}
            />
            {projectUid === null ? (
              <span className={styles.arrow} aria-hidden="true">›</span>
            ) : (
              <button
                type="button"
                className={`${styles.arrow} ${styles.toggle}`}
                aria-expanded={selected === section.code}
                aria-label={`Сведения о разделе «${section.name}»`}
                title="Сведения о разделе"
                data-section-toggle={section.code}
                onClick={() => setSelected(selected === section.code ? null : section.code)}
              >
                ›
              </button>
            )}
          </li>
        ))}
        {/* `UI-A-36`: the original's «Σ Итого», the column sums of the rows above; the unclassified row below is not in it. */}
        <li className={`${styles.row} ${styles.totalRow}`} data-section="total">
          <span className={styles.totalLabel}>
            <span className={styles.badge}>Σ</span>
            <span className={styles.name}>{SECTION_TOTAL_LABEL}</span>
          </span>
          <SectionMetrics documents={summary.totals.documents} audit={summary.totals.audit} notRunHref={null} />
          <span className={styles.arrow} aria-hidden="true" />
        </li>
        <li className={`${styles.row} ${styles.unclassified}`} data-section="unclassified" title={SECTION_UNCLASSIFIED_HINT}>
          <span className={styles.badge}>—</span>
          <span className={styles.name}>Без раздела:</span>
          <strong>{summary.unclassifiedCount}</strong>
          <span className={styles.definition}>{`. ${SECTION_UNCLASSIFIED_HINT}`}</span>
        </li>
      </ul>
      {selected === null ? null : (
        <div className={styles.selection} data-selected-section={selected}>
          <strong>{PROJECT_SECTIONS.find((section) => section.code === selected)?.name}</strong>
          <span>Документов в разделе: {summary.byCode[selected]}.</span>
          {projectUid === null ? (
            <Link href={routes.projects()}>Открыть объекты</Link>
          ) : (
            <>
              <Link href={routes.projectSection(projectUid, selected)}>Открыть раздел</Link>
              {/* `UI-A-53`: the section's optimisation, with the project the dashboard follows and the section. */}
              <Link href={routes.sectionOptimisation(selected, projectUid)} data-section-optimisation-link={selected}>
                Оптимизация раздела
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
