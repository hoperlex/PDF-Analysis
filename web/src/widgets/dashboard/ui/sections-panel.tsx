'use client';

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
import { PROJECT_SECTIONS } from '@/entities/project';
import type { ProjectSectionCode } from '@/entities/project';
import { withNotRunFilter } from '@/entities/document-version';
import type { SectionDocumentCount } from '@/shared/api';

import { incompleteBreakdownFailure } from '../model/dashboard-failure';
import { summarizeSectionBreakdown } from '../model/section-breakdown';
import type { SectionAuditFigures } from '../model/section-breakdown';
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
  return (
    <span className={styles.metrics}>
      <span className={`${styles.metric} ${styles.notRun}`} title="Не запускались" data-metric="not-run">
        {audit !== undefined && notRunHref !== null && audit.notRun > 0 ? (
          <Link
            className={styles.metricLink}
            href={notRunHref}
            aria-label={`Не запускались: ${audit.notRun}. Открыть список`}
            data-not-run-link=""
          >
            {audit.notRun}
          </Link>
        ) : (
          (audit?.notRun ?? '—')
        )}
      </span>
      <span className={`${styles.metric} ${styles.awaiting}`} title="Нет решений эксперта" data-attention={audit !== undefined && audit.noExpertDecision > 0 ? 'true' : 'false'}>
        {audit?.noExpertDecision ?? '—'}
      </span>
      <span className={`${styles.metric} ${styles.checked}`} title="Проверено экспертом">{audit?.checked ?? '—'}</span>
      <span className={`${styles.metric} ${styles.total}`} title="Документы"><strong>{documents}</strong></span>
      <span className={`${styles.metric} ${styles.remarks}`} title="Находок">{audit?.findings ?? '—'}</span>
    </span>
  );
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
      <p className="am-state__correlation">
        Документ учитывается в том разделе, который эксперт подтвердил для его текущей версии.
        Пока раздел не подтверждён, документ попадает в строку «Без раздела». Раздел
        подтверждает эксперт на экране версии.
      </p>
      <div className={styles.header} aria-hidden="true">
        <span>Раздел</span>
        <span className={styles.metrics}>
          <span>Не запускались</span>
          <span>Нет решений эксперта</span>
          <span>Проверено</span>
          <span>Документы</span>
          <span>Находок</span>
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
                <span className={styles.badge}>{section.code}</span>
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
                <span className={styles.badge}>{section.code}</span>
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
            <span className={styles.name}>Итого по разделам</span>
          </span>
          <SectionMetrics documents={summary.totals.documents} audit={summary.totals.audit} notRunHref={null} />
          <span className={styles.arrow} aria-hidden="true" />
        </li>
        <li className={`${styles.row} ${styles.unclassified}`} data-section="unclassified">
          <span className={styles.badge}>—</span>
          <span className={styles.name}>Без раздела:</span>
          <strong>{summary.unclassifiedCount}</strong>
        </li>
      </ul>
      {selected === null ? null : (
        <div className={styles.selection} data-selected-section={selected}>
          <strong>{PROJECT_SECTIONS.find((section) => section.code === selected)?.name}</strong>
          <span>Документов в разделе: {summary.byCode[selected]}.</span>
          {projectUid === null ? (
            <Link href={routes.projects()}>Открыть проекты</Link>
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
