'use client';

/**
 * The header of «Оптимизация раздела» (`UIP-S11-01`): the original's one line in our words and on our controls.
 *
 *   «←» · the section's badge · «Уровень раздела» · «Оптимизация раздела» · the list of sections
 *
 * and under it one line that says what the screen holds, with a «ⓘ» that opens the longer paragraph. The way back is where
 * the reader came from: the object's section page when the screen follows an object, the dashboard (the table of sections)
 * when it follows none. The badge is the section's abbreviation with the section's dot (`UIP-G-17`): the colour is one mark
 * more and never the only one. The colours and the violet theme of the original are not taken (`Г1-C`).
 *
 * Presentational over what the page already holds: the section, the object and the way to choose another section come in as
 * props; the only state here is whether the paragraph is open.
 */

import Link from 'next/link';
import { useId, useState } from 'react';

import type { ProjectSection as SectionCode, ProjectUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { SectionDot, findProjectSection } from '@/entities/project';

import { SectionFilterBar } from './section-filter-bar';
import styles from './section-optimisation-page.module.css';

export interface SectionHeaderProps {
  readonly sectionCode: SectionCode;
  /** The object the screen follows; `null` is «Все объекты». */
  readonly projectUid: ProjectUid | null;
  readonly onSection: (code: SectionCode) => void;
}

/** What the arrow says and where it leads: the object's section page, or the dashboard when no object is followed. */
export function sectionBackTarget(
  projectUid: ProjectUid | null,
  sectionCode: SectionCode,
): { readonly kind: 'section' | 'dashboard'; readonly href: string; readonly label: string } {
  return projectUid === null
    ? { kind: 'dashboard', href: '/dashboard', label: 'К дашборду' }
    : { kind: 'section', href: routes.projectSection(projectUid, sectionCode), label: 'К разделу объекта' };
}

/** The line under the heading: the section's name and what it is read over. */
export function sectionLeadLine(sectionName: string, projectUid: ProjectUid | null): string {
  return projectUid === null
    ? `${sectionName} · документы раздела по всем объектам`
    : `${sectionName} · документы выбранного объекта`;
}

export const SECTION_ABOUT_TEXT =
  'Сводная спецификация раздела по текущим версиям документов и принятые экспертами оптимизации. ' +
  'Экран только показывает данные: переносить решения между объектами здесь пока нельзя.';

export function SectionHeader({ sectionCode, projectUid, onSection }: SectionHeaderProps) {
  const [open, setOpen] = useState(false);
  const aboutId = useId();
  const section = findProjectSection(sectionCode);
  const back = sectionBackTarget(projectUid, sectionCode);
  return (
    <header className={styles.header} data-section-optimisation-header="">
      <Link className={styles.back} href={back.href} title={back.label} aria-label={back.label} data-section-optimisation-back={back.kind}>
        ←
      </Link>
      {section === null ? null : (
        <span className={`am-badge am-badge--inert ${styles.badge}`} data-section-badge={section.code}>
          <SectionDot code={section.code} />
          {section.abbr}
        </span>
      )}
      <span className={styles.level}>Уровень раздела</span>
      <h1 className={styles.title}>Оптимизация раздела</h1>
      <SectionFilterBar sectionCode={sectionCode} onSection={onSection} />
      <button
        type="button"
        className={styles.info}
        aria-expanded={open}
        aria-controls={aboutId}
        aria-label="Что показывает экран"
        title="Что показывает экран"
        data-section-about-toggle=""
        onClick={() => setOpen((held) => !held)}
      >
        ⓘ
      </button>
      {section === null ? null : <p className={styles.lead} data-section-lead="">{sectionLeadLine(section.name, projectUid)}</p>}
      <p id={aboutId} className={styles.about} hidden={!open} data-section-about="">
        {SECTION_ABOUT_TEXT}
      </p>
    </header>
  );
}
