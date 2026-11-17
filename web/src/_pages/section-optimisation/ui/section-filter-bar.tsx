'use client';

/**
 * The section list of «Оптимизация раздела», in the page's header (`UI-B-24`, `UIP-S11-01`).
 *
 * The original has no list of sections on this screen: the section is the one the reader came in by. Ours is one screen for
 * all fifteen, so the list stays, and stands in the header beside the section's badge, where the section is named. The
 * object is not chosen here: it is the one of the top strip (`UIP-G-06`), and there is no second list of projects.
 */

import type { ProjectSection } from '@/shared/api';
import { projectSectionTitle, sectionsInStructureOrder } from '@/entities/project';

import styles from './section-optimisation-page.module.css';

export interface SectionFilterBarProps {
  readonly sectionCode: ProjectSection;
  readonly onSection: (code: ProjectSection) => void;
}

export function SectionFilterBar({ sectionCode, onSection }: SectionFilterBarProps) {
  return (
    <form className={styles.filterBar} aria-label="Раздел" onSubmit={(event) => event.preventDefault()} data-section-filter-bar="">
      <div className={styles.filterField}>
        <label htmlFor="section-specification-section">Раздел</label>
        {/* The literal id is what the PC-01 journey's write half addresses (`section-form7-without-members`), and its
            conformance test finds the handle by this text in web/src; `SECTION_SELECT_ID` names the same value. */}
        <select
          id="section-specification-section"
          value={sectionCode}
          onChange={(event) => onSection(event.target.value as ProjectSection)}
          data-section-picker={sectionsInStructureOrder().length}
        >
          {sectionsInStructureOrder().map((section) => (
            <option key={section.code} value={section.code}>
              {projectSectionTitle(section)}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}
